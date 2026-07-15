# Promo Code / Discount Engine — Fleshed-Out Spec

## 0. Corrections to your stated understanding

**Issue (a) — negative discount / negative total.**
Real bug. Root cause: nothing clamps a fixed-amount discount to the cart total.
Fix: `discount = min(raw_discount, cart_total)` — always, for every rule type,
as the last step of evaluation. This single line is what "never negative" means
in practice.

**Issue (b) — "$5 off applied to a $3 cart, min spend is $100".**
This isn't actually a contradiction, so nothing is "broken" here — min_spend and
discount value are two independent fields on the same code:

- `min_spend` gates *eligibility* (is the cart even allowed to use this code).
- `value` (the $5) is *how much* comes off once eligible.

If min_spend is $100, a $3 cart never reaches step 2 — it's rejected at
eligibility with "minimum spend not met." A $5-off-min-$100 code applied to a
$120 cart is fine and totally ordinary (Amazon/Flipkart do this constantly).
The only place amount and cart size interact is the clamp in issue (a) — e.g.
a hypothetical `$150 off, min spend $100` code applied to a $100 cart *would*
need clamping to $100 off. So: your instinct that "discount vs cart size" needs
a safety check was right — it just isn't min_spend's job. Keep them separate.

---

## 1. Scope for this build

Session = user (Google OAuth gives you a session; no multi-user modeling
needed). One active cart per session. Focus is entirely the working slice:
percentage off, fixed off, min spend, expiry. Stacking/usage-limit/BXGY are
stretch and structured so they slot in later without a rewrite.

---

## 2. Data model

### Pydantic-style shape (matches FastAPI request/response models directly)

```python
from decimal import Decimal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class PromoType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"

class Promo(BaseModel):
    id: str                          # uuid4, server-generated
    code: str                        # "SAVE10" — stored UPPERCASE, unique
    type: PromoType
    value: Decimal                   # 10 -> 10% ; 5.00 -> $5.00
    min_spend: Decimal | None = None # None = no minimum
    expires_at: datetime | None = None  # tz-aware UTC; None = never expires
    active: bool = True              # admin kill-switch, independent of expiry
    created_at: datetime
    updated_at: datetime

    # --- stretch fields: present in schema now, always None/default for this build ---
    max_uses: int | None = None
    used_count: int = 0
    target_product_id: str | None = None   # for BXGY
    stackable_group: str | None = None     # None = cannot stack with anything

class CartItem(BaseModel):
    product_id: str
    name: str
    unit_price: Decimal
    qty: int = Field(gt=0)

class Cart(BaseModel):
    session_id: str                  # from Google OAuth session, 1:1 for now
    items: list[CartItem] = []
    applied_code: str | None = None  # currently-applied promo code, if any

class EvalResult(BaseModel):
    ok: bool
    code: str | None = None
    cart_total: Decimal              # pre-discount, for display
    discount: Decimal = Decimal("0")
    final_total: Decimal
    reason: str | None = None        # populated only when ok=False
```

### DB schema (SQL, if you're persisting rather than in-memory)

```sql
CREATE TABLE promos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT NOT NULL UNIQUE,        -- store uppercased
    type            TEXT NOT NULL CHECK (type IN ('percent', 'fixed')),
    value           NUMERIC(10,2) NOT NULL CHECK (value > 0),
    min_spend       NUMERIC(10,2),                -- NULL = no minimum
    expires_at      TIMESTAMPTZ,                   -- NULL = never expires
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    max_uses        INTEGER,                       -- NULL for this build
    used_count      INTEGER NOT NULL DEFAULT 0,
    target_product_id TEXT,                        -- NULL for this build
    stackable_group TEXT,                          -- NULL for this build
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (
    session_id      TEXT NOT NULL,   -- Google OAuth session id
    product_id      TEXT NOT NULL,
    name            TEXT NOT NULL,
    unit_price      NUMERIC(10,2) NOT NULL,
    qty             INTEGER NOT NULL CHECK (qty > 0),
    PRIMARY KEY (session_id, product_id)
);

CREATE TABLE cart_state (
    session_id      TEXT PRIMARY KEY,
    applied_code    TEXT REFERENCES promos(code)
);
```

Notes:
- `value`, `min_spend`, `unit_price` are `NUMERIC`/`Decimal` everywhere — never
  float, per §3's rounding note.
- `code` is normalized to uppercase on write, so lookups can do a plain
  equality match instead of `ILIKE` (cheaper, and avoids locale collation
  surprises).
- `cart_state` is a single row per session since this build is one
  cart/session — matches your Google OAuth session model, no user table needed.
- If you'd rather skip a real DB for a first pass, the Pydantic models above
  are the source of truth; back them with an in-memory `dict[str, Promo]`
  keyed by uppercased code, and `dict[session_id, Cart]` for carts. Swapping
  in Postgres later doesn't change the evaluator at all — it only touches the
  repository/lookup layer.

Use `Decimal`, not float, for all money math — floats will eventually produce
a total like `49.999999999` and a wrong negativity check.

---

## 3. The evaluator (the actual "interesting part")

Represent each promo type as a small class implementing one interface, so
adding a 5th type is "add a class + register it," not "add an if-branch
somewhere in a 200-line function."

```python
class DiscountRule(Protocol):
    def eligible(self, promo: Promo, cart_total: Decimal) -> tuple[bool, str | None]:
        """Returns (True, None) or (False, reason)."""
    def compute(self, promo: Promo, cart_total: Decimal, items: list[CartItem]) -> Decimal:
        """Returns raw discount amount, BEFORE clamping."""

class PercentOffRule:
    def eligible(self, promo, cart_total):
        if promo.min_spend and cart_total < promo.min_spend:
            return False, f"Minimum spend of ${promo.min_spend} not met"
        return True, None
    def compute(self, promo, cart_total, items):
        return cart_total * (promo.value / Decimal(100))

class FixedOffRule:
    def eligible(self, promo, cart_total):
        if promo.min_spend and cart_total < promo.min_spend:
            return False, f"Minimum spend of ${promo.min_spend} not met"
        return True, None
    def compute(self, promo, cart_total, items):
        return promo.value

RULES: dict[str, DiscountRule] = {
    "percent": PercentOffRule(),
    "fixed": FixedOffRule(),
}
```

**Evaluation pipeline** (`evaluate(cart, code) -> EvalResult`):

1. Look up code (case-insensitive). Not found → reject: `"Code not recognized"`.
2. `promo.active == False` → reject: `"Code no longer valid"`.
3. Expiry check (see §4 for exact semantics) → reject: `"Code expired"`.
4. `rule = RULES[promo.type]`; `ok, reason = rule.eligible(promo, cart_total)`.
   If not ok → reject with that reason (this is where min-spend rejection happens).
5. `raw = rule.compute(promo, cart_total, items)`.
6. `discount = min(raw, cart_total)` — the negative-total guard. Also
   `discount = max(discount, Decimal(0))` as a floor, in case a future rule
   type ever computes something malformed.
7. `final_total = cart_total - discount`.
8. Return `{discount, final_total, code}`.

Adding a 6th promo type later = write one class satisfying `DiscountRule`,
add one line to `RULES`. No existing code changes.

### Worked example: adding a 3rd type ("free shipping credit", flat $X off, capped)

Say six months from now you want `FREESHIP`: knock $X off, but only up to a
cap (e.g. never more than $15, even if `value` is set higher — protects
against fat-fingering the admin form). Here's the entire diff:

```python
class ShippingCreditRule:
    CAP = Decimal("15.00")

    def eligible(self, promo, cart_total):
        if promo.min_spend and cart_total < promo.min_spend:
            return False, f"Minimum spend of ${promo.min_spend} not met"
        return True, None

    def compute(self, promo, cart_total, items):
        return min(promo.value, self.CAP)   # type-specific cap
```

```python
RULES["shipping_credit"] = ShippingCreditRule()
```

Plus one line in the `PromoType` enum. That's it — no touching `evaluate()`,
no touching `PercentOffRule`/`FixedOffRule`, no touching the API route. The
pipeline's step 6 (`min(raw, cart_total)`) still applies on top of this
class's own cap, so both safety nets stack automatically. This is the
concrete payoff of the Protocol/registry shape: eligibility rules that repeat
across types (like min_spend) get copy-pasted once per class — acceptable at
this scale — while type-specific math (the $15 cap) stays fully isolated.

---

## 4. Edge cases — decided, on purpose

- **Discount larger than cart** → clamped to cart_total (step 6 above).
  Total floors at exactly $0.00, never negative.
- **Cart exactly equals min_spend** ("$50 minimum" on a $50.00 cart) →
  **eligible**. Use `cart_total >= min_spend`, not `>`. "Orders over $50"
  in plain English is usually meant inclusively by shoppers and by every
  major retailer's actual implementation; `>=` also avoids the classic
  off-by-one support ticket.
- **Expiry boundary**: `expires_at` is the last *valid* instant. A code with
  `expires_at = 2026-07-15T23:59:59Z` is usable at `23:59:59` and rejected at
  `00:00:00` the next day. Implement as `now <= expires_at`, always compared
  in UTC (store `expires_at` as timezone-aware UTC; convert any admin-entered
  local date to end-of-day UTC when saving, so "expires July 15" behaves the
  way a shopper expects).
- **Percent-off producing fractional cents** (e.g. 10% of $9.99 = $0.999) →
  round the discount to 2dp using `ROUND_HALF_UP`, applied once at the end
  of `compute()`, not accumulated across items.
- **Empty cart** → reject before even checking the code: `"Cart is empty"`.
- **Code applied twice / re-applied** → re-running `evaluate` is idempotent;
  applying a new code replaces `applied_code` rather than stacking (stacking
  is explicitly opt-in, see §5).
- **Unknown/malformed code string** (empty, whitespace) → same "not
  recognized" path, don't special-case it.

---

## 5. Stretch: stacking order (if you get to it)

Decision: **percentage-off applies first, then fixed-off**, i.e.
`total = (cart_total * (1 - pct/100)) - fixed_amount`, clamped at 0.

Why: this is the more shopper-favorable order for typical carts *and* it's
what most e-commerce platforms default to — it prevents a fixed-off code from
shrinking the base that a percentage is calculated against, which is the
direction that surprises people less. Document this in the admin UI copy
("stacked codes apply % first"), since order is otherwise invisible.

Implementation: `stackable_group` on Promo — two codes may combine only if
they share a non-null group; evaluator sorts applied rules by type
(`percent` before `fixed`) before folding them.

---

## 6. What "done" looks like for the working slice

- POST `/cart/apply-code` with `{code}` → `{discount, final_total}` or
  `{error: reason}`, using the pipeline in §3.
- Four seeded promos covering: percent, fixed, min-spend, expiry — including
  one already-expired and one with unmet min-spend, so both rejection paths
  are demoed live.
- A cart total never renders negative, provably, because the clamp is
  structural (step 6), not a UI-side `Math.max(0, x)` band-aid.
- Deployed, and you can point at `RULES` + `DiscountRule` and say "this is
  why code #5 is a 10-line class, not a new branch."

---

## 7. Implementation plan (for Claude Code)

Hand this section to Claude Code as the task brief. Sequenced so each phase is
independently runnable/testable before moving to the next.

### Phase 0 — Project scaffold
- FastAPI app, `uvicorn` entrypoint.
- Google OAuth session middleware (existing setup — wire it in, session_id
  available on `request.session` or equivalent for every route below).
- Storage: start with in-memory (`dict`-backed repository classes) behind a
  small interface, so swapping to Postgres later is a repository swap, not a
  rewrite. Don't build the SQL layer yet — the in-memory version is enough to
  demo and deploy.
- `Decimal` everywhere for money — enforce via Pydantic models in §2, no raw
  `float` in request/response bodies.

### Phase 1 — Data models
- Implement `Promo`, `CartItem`, `Cart`, `EvalResult` exactly as in §2.
- Stretch fields (`max_uses`, `used_count`, `target_product_id`,
  `stackable_group`) present but always default/`None` — don't build logic
  that reads them yet.
- Seed data: hardcode 4-6 products (name, price) and 4 promos covering:
  1. valid percent-off, no min, no expiry
  2. valid fixed-off, with a min_spend
  3. an already-expired code (any type)
  4. a code with a min_spend that a small test cart won't meet
  This seed set is what proves both rejection paths live.

### Phase 2 — Evaluator core
- Implement `DiscountRule` Protocol, `PercentOffRule`, `FixedOffRule`, and the
  `RULES` registry exactly as in §3.
- Implement `evaluate(cart, code) -> EvalResult` following the 8-step
  pipeline in §3, including:
  - case-insensitive code lookup
  - `active` check
  - expiry check using `now <= expires_at` in UTC (§4)
  - `min_spend` check using `>=` (§4)
  - clamp: `discount = max(min(raw, cart_total), Decimal(0))`
  - rounding: `ROUND_HALF_UP` to 2dp on the final discount
- Unit tests (pytest) for every edge case in §4 individually:
  - discount larger than cart → clamps to cart_total, final_total == 0
  - cart_total exactly equals min_spend → eligible
  - cart_total one cent under min_spend → rejected with correct reason
  - now equals expires_at exactly → still valid
  - now one second past expires_at → rejected
  - percent-off producing a fractional cent → rounds correctly
  - empty cart → rejected before code lookup even runs
  - unknown code string → rejected with "not recognized"
  Write these tests before wiring the HTTP layer — they're the real spec.

### Phase 3 — API routes
- `POST /cart/items` — add/update an item in the session's cart (from the
  hardcoded product list).
- `GET /cart` — current cart contents + running total (no discount applied).
- `POST /cart/apply-code` — body `{code: str}`, runs `evaluate()`, sets
  `cart.applied_code` on success, returns `EvalResult`. On rejection, cart is
  unchanged and the response carries `reason`.
- `DELETE /cart/apply-code` — removes an applied code, back to raw total.
- Return the same `EvalResult` shape whether accepted or rejected — client
  branches on `ok`, not on HTTP status (use 200 for a "clean" rejection like
  expired/min-not-met; reserve 4xx for actual malformed requests, e.g. adding
  a product_id that doesn't exist).

### Phase 4 — Minimal frontend
- Single page: product list with add-to-cart, cart summary, a promo code
  input + apply button, running total that updates in place.
- On rejection, show `reason` inline near the input — no toast/modal needed,
  keep it boring and legible.
- No styling investment beyond "readable" — this isn't the graded part.

### Phase 5 — Deploy
- Deploy to whatever's fastest to stand up publicly (Render/Railway/Fly for
  FastAPI is typical). Confirm Google OAuth redirect URIs are updated for the
  deployed domain, not just localhost.
- Smoke-test all four seeded promos live post-deploy, not just locally.

### Explicitly deferred (don't build in this pass)
- Stacking, usage limits, BXGY — the schema has room (§2) but no logic should
  be written for them. If Claude Code starts implementing `stackable_group`
  matching or `max_uses` decrementing, that's scope creep on this pass — flag
  it and stop.
- Multi-user modeling beyond one cart per OAuth session.
- Real payments, tax, shipping, admin-facing UI for creating promos (seed
  data via code/fixtures is enough).

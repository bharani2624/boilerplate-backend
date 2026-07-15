# Build: A Promo-Code / Discount Engine

## The pitch

Build a simple checkout where an admin defines **promo codes with rules**, and a
shopper applies one to a cart and watches the price update. The fun isn't the
cart — it's modeling the **rules** so they behave sensibly.

## Background

Every shop has promo codes, and they're famously buggy: discounts that go
negative, codes used after they expire, "$5 off" applied to a $3 cart. There's no
library that matches *your* exact rules, so you have to think the logic through
rather than copy it.

## Core requirements (the working slice)

Support an admin-defined set of codes with **at least these types**:

- **Percentage off** the cart (e.g. `SAVE10` = 10% off).
- **Fixed amount off** (e.g. `FIVEOFF` = $5 off) — must **never make the total
negative**.
- **Minimum spend** to qualify (e.g. "$5 off orders over $50").
- **Expiry date** — an expired code is rejected with a clear reason.

A shopper enters a code; the cart shows the discount and new total, or a clear
reason it was rejected (expired / minimum not met). Deployed to a public URL.
 

## If you have time

- **Buy-X-get-Y-free** on a product (the cheapest qualifying item is the free one).
- A **per-code usage limit** ("first 100 uses").
- **Stacking:** allow combining some codes but not others, with a defined order.



## The interesting part (where your thinking shows)

- **Adding the next code should be easy.** Think about how you represent a code so
that introducing a fifth one later isn't a scavenger hunt through the codebase.
- **Edge cases decide correctness.** What happens when a discount is larger than
the cart? When exactly does a code expire? Is a cart that hits the minimum spend
*exactly* eligible or not? Decide these on purpose.
- (If you do stacking) **order matters** — %-off before or after $-off gives
different totals. Pick one and be able to say why.



## Suggested data model (starting point)

- `promos`: code, type, value, min_spend, expires_at  *(+ optional max_uses,
target_product, stackable)*
- `cart_items`: product, price, qty (a hardcoded handful of products is fine)
- An evaluator that takes (cart, code) → discount + final total, or a reason



## Explicitly out of scope

Real payments, a product-catalog UI, tax/shipping, accounts. Skip extras unless
the core works and is deployed.
 

## What good looks like

Apply each rule type and see correct totals; try an expired or under-minimum code
and get a clear rejection; the total never goes negative; deployed — and you can
explain how you represented the codes and why adding another one is easy.
# curl test scripts

Quick manual smoke tests for every endpoint — the same requests used to verify the
backend during development and after each deploy. Handy for a builder-round demo when
you want to prove the API works without going through the frontend.

## Usage

```bash
export BASE_URL=http://localhost:8000        # or the Render URL, e.g. https://boilerplate-backend-7ht2.onrender.com
./scripts/curl/health.sh
```

Everything under `/api/items` and `/api/auth/me` needs a JWT. Get one without going
through the Google OAuth flow (useful for local/CI testing — it mints a real user +
token directly against the DB in `DATABASE_URL`, bypassing Google entirely):

```bash
export TOKEN=$(./scripts/curl/get_test_token.sh test@example.com)
./scripts/curl/items_create.sh "My first item" "some description"
./scripts/curl/items_list.sh
```

To test the *real* Google login path instead, get a Google ID token from the frontend
(open devtools on `/login`, the token is in the request body of the `POST
/api/auth/google` call) and run:

```bash
./scripts/curl/auth_google.sh "<paste id_token here>"
```

## Files

- `health.sh` — GET /api/health, unauthenticated
- `get_test_token.sh <email>` — bypasses Google OAuth; upserts a test user directly via `UserStore` and prints a signed JWT. Requires `DATABASE_URL`/`JWT_SECRET_KEY` to be set the same as the target `BASE_URL`'s environment (run from the backend repo with `.env` loaded, or export them inline).
- `auth_google.sh <id_token>` — POST /api/auth/google with a real Google ID token
- `auth_me.sh` — GET /api/auth/me (needs `$TOKEN`)
- `items_list.sh` — GET /api/items (needs `$TOKEN`)
- `items_create.sh <title> [description]` — POST /api/items (needs `$TOKEN`)
- `items_get.sh <item_id>` — GET /api/items/{id} (needs `$TOKEN`)
- `items_update.sh <item_id> [title] [description]` — PUT /api/items/{id} (needs `$TOKEN`)
- `items_delete.sh <item_id>` — DELETE /api/items/{id} (needs `$TOKEN`)

Add a new one for each new entity you build — copy `items_*.sh` and swap the path/fields.

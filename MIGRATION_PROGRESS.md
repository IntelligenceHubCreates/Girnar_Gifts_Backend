# Girnar Gifts Migration — Progress Log (Backend)

See `MIGRATION_MAP.md` (workspace root, two levels up, in the sibling `final-project`'s parent folder) for the full Phase 0 discovery findings this migration is based on.

## Phase 0 — Discovery
- Completed. Findings in `../../MIGRATION_MAP.md`. Notable backend-specific findings: FastAPI title was `"Silvee API"` (a leftover jewelry-store template identity, unrelated to "Little Loot"), CORS hardcoded to `["*"]` with an unused env-driven line, Alembic ignores `DATABASE_URL` entirely (hardcoded connection string in `alembic.ini`), no seed scripts or bulk-upload route exist, no invoice generator exists.

## Phase 1 — Safety & Fork
- Committed pre-existing WIP (admin, blog, coupons, newsletter, notifications, payments, returns, shipping, store_settings modules + edits to cart/orders/products/ratings/users) that was uncommitted on `fixes/antigravity` before forking, to avoid losing it.
- Pushed that commit + tagged `v1.0-silvee-backend-stable` on the original `Silvee-Backend` repo as a restore point.
- Created local mirror backup: `../../_backups/silvee-backend-backup.git`.
- Renamed local branches: old `main` → `old-main-silvee-backend` (preserved), `fixes/antigravity` → `main` (now the working branch).
- Re-pointed `origin` to `https://github.com/IntelligenceHubCreates/Girnar_Gifts_Backend.git`, pushed `main` + tags.

## Phase 2 — Renaming
- `app/main.py`: FastAPI `title` → `"Girnar Gifts API"`, description text de-jewelry-fied and rebranded, root `GET /` message → `"Welcome to Girnar Gifts API"`.
- Backend package folder (`app/`) is generically named, not literally branded — no folder rename needed.

## Prerequisite fix — Alembic env-var wiring
- `alembic.ini` had a hardcoded dev connection string committed to the repo; `alembic/env.py` ignored the environment entirely. Fixed `env.py` to build the URL from `app.settings` (same `postgres_*` env vars the app itself uses), removed the hardcoded credential from `alembic.ini`.

## Phase 3 — Brand-config layer
- `app/settings.py`: added `brand_name`, `brand_support_email`, `brand_gstin`, `cloudinary_folder` (default `girnar-gifts`), `razorpay_receipt_prefix` (default `girnar_`), `cors_origins` (default Girnar's own domains) — all with sane defaults so existing `.env` files don't break.
- `app/main.py`: CORS was hardcoded to `allow_origins=["*"]` with an unused env-driven line commented out — wired it to actually read `settings.cors_origins`.
- Replaced every "Little Loot" / `littleloot/...` Cloudinary-folder literal across `newsletter`, `blog`, `payments`, `admin`, `notifications`, `products`, `users`, `shipping`, `returns` routers with the new settings fields.

## Phase 4 — DB separation, seed scripts, and two security findings
- Created local `girnar_db` (empty, fresh) via a standalone `compose.girnar-local.yml` + `.env.girnar-local` (both untracked/gitignored — a real Little Loot dev stack was already running on the default ports 8000/6789/4444/9432 from a *different* directory, so this avoids any collision).
- **Caught before running**: `alembic/env.py` only imported `users/products/rating/favorite/orders/cart` models. Autogenerate against the full model set therefore proposed *dropping 19 tables* (notifications, coupons, shipments, returns_*, blog_posts, store_settings, newsletter_subscribers, payment_orders, refunds, courier_partners, etc.) — all real feature tables from the Phase-1 WIP that only existed via `create_all()`, never in migration history. Fixed by adding the missing model imports to `env.py`; regenerated migration then only contained genuine drift (missing columns, a couple of intentional column removals). Applied cleanly to `girnar_db`.
- **Found and fixed a hardcoded admin backdoor**: `app_entrypoint.sh` auto-inserted a real email + baked-in bcrypt password hash as an admin (role=1) user into any database missing a users.id=1 row, on every container start. It fired against `girnar_db` before this was caught; the row was deleted. Removed the insert block entirely — admin provisioning is now only via `app/scripts/seed_admin.py`.
- **Found and fixed a hardcoded JWT secret**: `app/users/utils.py` had `JWT_SECRET_KEY` as a literal string checked into source, completely bypassing `Settings.secret_key` (which was declared but unused). Anyone with repo read access could have forged valid JWTs. Now reads `settings.secret_key`.
- Added `app/scripts/seed_admin.py` (reads `SEED_ADMIN_PASSWORD` from env), `seed_categories.py` (Girnar's 7-category gift taxonomy), `seed_products.py` (bulk-CSV import stub — full fidelity pending Phase 5's new Product columns). All idempotent, verified by running twice.
- Local verification: `girnar_db` has 32 tables, 1 admin user, 7 categories, 0 products.

## Phase 5 — Product schema fields + pagination verification
- Added `sku`, `slug` (both unique/indexed), `gst_percent`, `hsn`, `weight_g`, `dimensions`, `personalisation_options` (JSON list), `seo_title`, `seo_description` to `Product` — model, migration, `ProductBase` response schema, and both create/update endpoint form fields. `stock` intentionally maps to the existing `count` column rather than adding a duplicate field.
- Verified end-to-end: created/serialized/deleted a test product via the ORM+schema layer directly inside the running container.
- Verified the products-list pagination empirically: `GET /api/product/all?limit=777` correctly 422s from query validation (max 100) rather than erroring as an invalid product ID — confirms the route is not being shadowed by `/{id}`, matching Phase 0's static-analysis finding. No fix needed.
- Categories are already fully DB-driven on the admin side; storefront nav/routing flagged separately (see `MANUAL_STEPS.md` §1, frontend progress log).

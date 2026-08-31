-- GET /api/admin/metrics (app/src/app/routes/admin/admin.controller.ts) only
-- reports RateLimitEvent rows from the last 60 SECONDS -- it's a
-- current-window metric, not a historical one. That means a static seed
-- dump committed to git would already be stale by the time anyone restores
-- it, no matter how recently it was captured. This file uses `now()`, so
-- run it right before you curl the endpoint and every row lands inside that
-- window at whatever moment you actually run it.
--
-- Usage (after `npx prisma migrate deploy` has created the table):
--   psql "$DATABASE_URL" -f demo-state/seed-recent-rate-limit-events.sql
--   curl -H "Authorization: Token <a real JWT>" http://localhost:3000/api/admin/metrics

INSERT INTO "RateLimitEvent" ("createdAt", "ip", "endpoint", "userId") VALUES
  (now() - interval '55 seconds', '203.0.113.10', '/api/articles', NULL),
  (now() - interval '48 seconds', '203.0.113.10', '/api/articles', NULL),
  (now() - interval '40 seconds', '203.0.113.10', '/api/articles', NULL),
  (now() - interval '30 seconds', '203.0.113.10', '/api/articles', NULL),
  (now() - interval '22 seconds', '198.51.100.24', '/api/users/login', NULL),
  (now() - interval '15 seconds', '198.51.100.24', '/api/users/login', NULL),
  (now() - interval '8 seconds',  '198.51.100.24', '/api/users/login', NULL),
  (now() - interval '3 seconds',  '203.0.113.10', '/api/articles', NULL);

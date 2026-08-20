# Fork Conventions - read before either agent touches `app/`

Source: `gothinkster/node-express-realworld-example-app` (cloned into `app/`).

**[CORRECTION]** The top-level plan doc describes this fork as "Sequelize
ORM." That's wrong - verified directly against `app/package.json` and
`app/src/prisma/`: this fork uses **Prisma** (`@prisma/client`) against
**PostgreSQL**, not Sequelize. Any prompt or doc referencing Sequelize
should be corrected to Prisma.

## ORM / schema
- Models live in `app/src/prisma/schema.prisma` (declarative Prisma schema,
  not raw SQL DDL by hand).
- Existing models: `Article`, `Comment`, `Tag`, `User`.
- Migrations live in `app/src/prisma/migrations/<timestamp>_<description>/migration.sql`,
  e.g. `20211105153605_api_url/migration.sql`. Each migration folder is
  Prisma-generated (`prisma migrate dev --name <description>`), not hand-authored
  SQL dropped in a flat folder.
- Migration SQL style seen in this repo is plain Postgres DDL, e.g.:
  ```sql
  -- AlterTable
  ALTER TABLE "User" ALTER COLUMN "image" SET DEFAULT E'https://api.realworld.io/images/smiley-cyrus.jpeg';
  ```

## Auth
- `jsonwebtoken` + `express-jwt` (JWT bearer tokens), `bcryptjs` for password
  hashing. No session/cookie auth.

## Structure
- `src/app/routes/{auth,profile,article,tag}` - route handlers by resource.
- `src/app/models/` - request/response models (not ORM models - those are in
  `prisma/schema.prisma`).
- Build/test via `nx` (`nx serve`, `nx build`, `nx test`), not plain `npm run`.

## What this means for the migration/endpoint demo
- Schema Agent's migration should be a **new Prisma model** in `schema.prisma`
  (e.g. `RateLimitEvent`) plus the corresponding generated `migration.sql`
  under `src/prisma/migrations/`, matching the existing naming and DDL style -
  not a hand-rolled `CREATE TABLE` dropped anywhere else.
- API Agent's admin endpoint should follow the existing route-handler pattern
  under `src/app/routes/` and read via `@prisma/client`, consistent with how
  `Article`/`User` etc. are queried elsewhere in this codebase (not yet
  individually inspected - check an existing controller, e.g.
  `src/app/routes/article/article.controller.ts`, before writing the new one).

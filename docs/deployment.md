# Deployment Notes

The intended free-tier POC deployment is:

```text
apps/web -> Vercel
apps/api -> Render
database -> Supabase Postgres with pgvector
```

For the backend, set:

```text
DATABASE_URL=...
MPOST_DEV_USER_EMAIL=...
MPOST_DEV_USER_ROLE=...
```

Do not host sensitive or controlled documents on free commercial tiers.

# Backup & Restore (ALISA)

This project is non-commercial and trust-first; keep backups simple, consistent, and auditable.

## What to back up
- Database (PostgreSQL or SQLite used in dev)
- Media files (user uploads, certificates)
- Configuration secrets (`.env` / environment variables)

## Backup commands (examples)
- SQLite (dev):
  - `python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > backups/data.json`
- PostgreSQL:
  - `pg_dump $DATABASE_URL > backups/db.sql`
- Media:
  - Sync the `media/` directory (or your S3 bucket) to a safe location.

## Restore
- SQLite:
  - `python manage.py loaddata backups/data.json`
- PostgreSQL:
  - `psql $DATABASE_URL < backups/db.sql`
- Media:
  - Restore `media/` (or re-sync from your backup bucket).

## Practices
- Schedule backups (at least daily for prod data).
- Test restores periodically.
- Keep audit logs of backup/restore actions.
- Store secrets securely; do not commit `.env` to VCS.

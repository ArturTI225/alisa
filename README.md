# ALISA - platforma comunitara de ajutor (Django + DRF + Next.js)

Platforma sociala, non-comerciala, pentru cereri de ajutor intre utilizatori si voluntari.
Fluxul principal este `HelpRequest -> VolunteerApplication -> Match -> In Progress -> Done`.

## Ce s-a actualizat
- Flux social principal consolidat pe `HelpRequest` si `VolunteerApplication`.
- Trust & safety extins: verificari, rapoarte, blocare user, audit log.
- Statistici voluntar + badge-uri + certificat de finalizare (PDF).
- Task-uri asincrone cu Celery (certificat), cu fallback sincron (`CELERY_TASK_ALWAYS_EAGER=True` implicit).
- Limite de upload + allowlist MIME + hook antivirus.
- Throttling DRF pe endpoint-uri sensibile (`help-requests`, `volunteer-applications`, `chat`).
- Home role-based (public/client/worker) + pagini separate pentru client/worker.
- Aplicatia `payments` a fost eliminata (fara fluxuri financiare in core).
- Frontend Next.js actualizat (SSR + i18n RO + integrare API v1).

## Principii
- Fara plati, preturi, comisioane sau incentivare financiara in entitatile core.
- Accent pe incredere: verificare, moderare, raportare, auditabilitate.
- Flux social-first; `bookings` ramane in proiect ca flux legacy/de tranzitie.

## Stack tehnic
- Backend: Django 5.2, Django REST Framework.
- Baza de date: SQLite (dev implicit) sau PostgreSQL prin `DATABASE_URL`.
- Async: Celery + Redis.
- Observabilitate: logging structurat + Sentry (optional).
- Frontend optional: Next.js 14 (folder `frontend/`).

## Model de domeniu (curent)
- Utilizatori si profiluri: `User`, `ProviderProfile`, `ClientProfile`.
- Flux principal social:
  - `HelpRequest` (status: `open`, `in_review`, `matched`, `in_progress`, `done`, `cancelled`)
  - `VolunteerApplication` (`pending`, `accepted`, `rejected`, `withdrawn`)
  - `Conversation` / `ChatMessage`
  - `Review`
- Trust & safety:
  - `Verification`
  - `Report`
  - `AuditLog`
  - `is_blocked` + middleware dedicat
- Recunoastere voluntari:
  - `Badge`
  - `ProviderMonthlyStat`
  - `CompletionCertificate`
- Flux legacy:
  - `Booking`, `RescheduleRequest`, `BookingDispute`, `RecurringBookingRule`
  - `Ad`, `Offer`

## Setup backend (local)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Linux/macOS: cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Daca rulezi si frontend-ul local:
- porneste Django pe `8001` (ca sa eviti conflictul cu Next.js):
```bash
python manage.py runserver 127.0.0.1:8001
```

## Variabile de mediu (backend)
Minim:
- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`

Optionale importante:
- `CELERY_BROKER_URL` (default: `redis://localhost:6379/0`)
- `CELERY_TASK_ALWAYS_EAGER` (default: `True`)
- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`
- `DJANGO_LOG_LEVEL`
- `CSRF_TRUSTED_ORIGINS`

## Celery si Redis
In modul implicit de development, task-urile ruleaza sincron (`CELERY_TASK_ALWAYS_EAGER=True`).

Pentru async real:
1. seteaza `CELERY_TASK_ALWAYS_EAGER=False`
2. porneste Redis
3. porneste worker-ul:
```bash
celery -A config worker -l info
```

## Frontend Next.js (optional)
```bash
cd frontend
copy .env.local.example .env.local   # Linux/macOS: cp .env.local.example .env.local
npm install
npm run dev
```

Valoare recomandata:
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api`

Observatie:
- `frontend` ruleaza implicit pe portul `8000`.
- `API_BASE` adauga automat sufixul `/v1` daca lipseste.

## Rute UI utile
- `/` (home role-based: public/client/worker)
- `/help-requests/create/`
- `/help-requests/<id>/apply/`
- `/help-requests/<id>/start/`
- `/applications/<id>/accept/`
- `/services/`
- `/bookings/` (legacy)
- `/bookings/new/` (legacy)
- `/chat/`
- `/accounts/profile/`
- `/accounts/favorites/`
- `/accounts/notifications/`
- `/cum-functioneaza/`
- `/faq/`
- `/devino-membru/`
- `/devino-sot-la-ora/` (redirect permanent catre `/devino-membru/`)

## API DRF
Baza:
- `/api/v1/` (principala)
- `/api/` (ruta de compatibilitate temporara)

Endpoint-uri principale:
- `/api/v1/help-requests/`
- `/api/v1/volunteer-applications/`
- `/api/v1/conversations/`
- `/api/v1/chat-messages/`
- `/api/v1/reviews/`
- `/api/v1/verifications/`
- `/api/v1/reports/`
- `/api/v1/notifications/`
- `/api/v1/notification-preferences/`

Endpoint-uri suplimentare:
- `/api/v1/bookings/` (legacy)
- `/api/v1/ads/` si `/api/v1/offers/` (legacy/compat)
- `/api/v1/services/`
- `/api/v1/service-categories/`
- `/api/v1/providers/`
- `/api/v1/addresses/`
- `/api/v1/favorite-services/`
- `/api/v1/favorite-providers/`

Actiuni custom importante:
- `POST /api/v1/help-requests/{id}/cancel/`
- `POST /api/v1/help-requests/{id}/start/`
- `POST /api/v1/help-requests/{id}/complete/`
- `POST /api/v1/help-requests/{id}/send_to_review/`
- `POST /api/v1/help-requests/{id}/approve/`
- `POST /api/v1/help-requests/{id}/reject/`
- `POST /api/v1/help-requests/{id}/lock/`
- `POST /api/v1/help-requests/{id}/unlock/`
- `GET /api/v1/help-requests/{id}/certificate/`
- `POST /api/v1/volunteer-applications/{id}/accept/`
- `POST /api/v1/volunteer-applications/{id}/reject/`
- `POST /api/v1/volunteer-applications/{id}/withdraw/`

Observatii API:
- Crearea de `help-requests` suporta `Idempotency-Key` in header pentru retry sigur.
- Exista throttling DRF configurat pentru endpoint-uri sensibile.

Schema OpenAPI:
- `/api/v1/schema/`

Healthcheck:
- `/health/`

## Upload-uri si securitate
- Marime maxima upload: `25MB`.
- Tipuri permise: `jpeg`, `png`, `mp4`, `webm`, `mov`, `pdf`.
- Hook antivirus: `VIRUS_SCAN_HANDLER` (optional).
- Utilizatorii blocati sunt opriti din request-uri prin `BlockedUserMiddleware`.

## Testare si verificari
```bash
python manage.py check
python manage.py test
```

## Backup & restore
Vezi:
- `docs/backup_restore.md`

Comenzi utile (dev):
- backup date SQLite:
```bash
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > backups/data.json
```
- restore:
```bash
python manage.py loaddata backups/data.json
```

## Observatii
- `requirements.txt` include dependinte optionale pentru PDF (`weasyprint` etc., comentate).
- `bookings` si `ads/offers` exista pentru compatibilitate, dar directia produsului ramane social-first pe `HelpRequest`.
- Pentru productie configureaza explicit secret-ele, DB, Redis, storage pentru fisiere si Sentry.

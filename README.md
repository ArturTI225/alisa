# La usa ta- platforma comunitara de ajutor (Django + DRF)

Platforma sociala (non-comerciala) pentru conectarea solicitantilor cu voluntari.
Fluxuri active in cod: cereri de ajutor, aplicatii voluntari, chat, notificari, review, verificari, rapoarte si moderare.

Actualizat pe baza codului existent la: **16 martie 2026**.

## 1) Stare reala a proiectului (ce se foloseste efectiv)

| Componenta | Status real | Verificat in cod | Concluzie |
|---|---|---|---|
| Django (apps + template UI) | Activ principal | `config/settings.py`, `config/urls.py`, `templates/**` | Interfata principala rulata azi este cea Django Templates |
| DRF API (`/api/v1/`) | Activ | `config/api_router.py`, ViewSet-urile din apps | API-ul este folosit si de UI intern, si de clienti externi |
| Flux `HelpRequest` + `VolunteerApplication` | Activ | `bookings/models.py`, `bookings/views.py`, `pages/views.py`, `templates/pages/home_client.html`, `templates/pages/home_worker.html` | Fluxul social exista si este functional |
| Flux `Booking` | Activ (inca puternic folosit) | `bookings/urls.py`, `bookings/views.py`, `templates/bookings/**`, link-uri in `templates/base.html` | Nu e "mort"; este in productie in UI curent |
| `ads` / `offers` | Activ partial | `ads/views.py`, context in `pages/views.py` | Folosite pentru anunturi/urgente si compatibilitate |
| Next.js (`frontend/`) | Optional, separat | `frontend/package.json`, lipsa referintelor din `config/urls.py`/`templates` | **Nu este integrat direct in runtime-ul Django** |
| Celery | Activ logic, sync by default | `config/celery.py`, `bookings/tasks.py`, `CELERY_TASK_ALWAYS_EAGER=True` | Task-urile ruleaza implicit sincron in dev |
| Redis | Optional | folosit doar daca rulezi async real cu Celery | Nu e obligatoriu in modul implicit |
| Sentry | Optional | activ doar daca exista `SENTRY_DSN` | by default este dezactivat |
| Channels/WebSocket push | Optional/neactiv implicit | fallback in `accounts/utils.py`, pachetul `channels` nu e in `requirements.txt` | notificarile WS nu sunt obligatorii si nu pornesc implicit |
| `payments` | Eliminat | nu apare in `INSTALLED_APPS`; cautare repo | nu face parte din proiectul curent |

### Verdict pentru Next.js
- `frontend/` exista ca aplicatie separata (client optional).
- Nu este montat in URL-urile Django si nu este necesar pentru functionarea backend + UI principal.
- Daca folosesti doar Django Templates, proiectul functioneaza complet fara Next.js.

## 2) Arhitectura curenta

### Backend principal
- Django 5.2 + DRF
- Apps instalate: `accounts`, `services`, `bookings`, `ads`, `chat`, `reviews`, `pages`
- UI server-rendered: Django Templates (`templates/`) + asset-uri statice (`static/`)
- API versionat: `/api/v1/` (+ compatibilitate temporara `/api/`)

### Persistenta si fisiere
- DB implicita in dev: SQLite (`db.sqlite3`)
- DB alternativa: PostgreSQL via `DATABASE_URL`
- Fisiere media locale in dev (`media/`)
- Upload constraints:
  - max `25MB`
  - allowlist MIME (imagini/video/pdf)
  - hook antivirus optional (`VIRUS_SCAN_HANDLER`)

### Async / observabilitate
- Celery configurat (`config/celery.py`)
- Redis folosit ca broker/backend cand rulezi async real
- Logging structurat in consola
- Sentry optional

## 3) Fluxuri functionale in produs

### A. Flux social (Help Request)
1. Solicitantul creeaza `HelpRequest`
2. Voluntarii trimit `VolunteerApplication`
3. Solicitant/admin accepta o aplicatie
4. Cererea trece `matched -> in_progress -> done`
5. Se pot genera notificari, review, certificat si actualizare statistici voluntar

Statusuri `HelpRequest`:
- `open`, `in_review`, `matched`, `in_progress`, `done`, `cancelled`

Statusuri `VolunteerApplication`:
- `pending`, `accepted`, `rejected`, `withdrawn`

### B. Flux booking (inca activ in UI)
- Creare booking, accept/decline, start/complete
- Reprogramari, dispute, atasamente, reguli recurente, export ICS
- Dashboard voluntar + CSV

Nota: in documentatie interna fluxul social este directia dorita, dar in codul curent fluxul booking este inca intens utilizat in paginile Django.

## 4) Setup local (backend)

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

Verificare rapida:
```bash
python manage.py check
```

## 5) Variabile de mediu

Minim necesare:
- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`

Optionale importante:
- `CELERY_BROKER_URL` (implicit `redis://localhost:6379/0`)
- `CELERY_TASK_ALWAYS_EAGER` (implicit `True`)
- `CSRF_TRUSTED_ORIGINS`
- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`
- `DJANGO_LOG_LEVEL`

## 6) Celery / Redis (cand chiar ai nevoie)

Implicit (dev): task-urile ruleaza sincron.

Pentru async real:
1. setezi `CELERY_TASK_ALWAYS_EAGER=False`
2. pornesti Redis
3. pornesti worker:

```bash
celery -A config worker -l info
```

## 7) Frontend Next.js (status si folosire)

Folderul `frontend/` este un client separat, optional.

### Cand il folosesti
- vrei un frontend React/Next separat de template-urile Django
- vrei SSR in Next pentru pagini publice

### Cand NU ai nevoie de el
- folosesti UI-ul Django existent (`templates/`)
- vrei stack simplu backend+templates

### Rulare Next.js (optional)

```bash
cd frontend
copy .env.local.example .env.local   # Linux/macOS: cp .env.local.example .env.local
npm install
npm run dev
```

Valoare recomandata:
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api`

Daca rulezi si Next.js (port 8000), pornesc backend-ul pe 8001:
```bash
python manage.py runserver 127.0.0.1:8001
```

## 8) Rute UI principale (Django)

- `/` (home role-based: public/client/worker)
- `/services/`
- `/bookings/`
- `/bookings/new/`
- `/chat/`
- `/accounts/profile/`
- `/accounts/favorites/`
- `/accounts/notifications/`
- `/help-requests/create/`
- `/help-requests/<id>/apply/`
- `/help-requests/<id>/start/`
- `/applications/<id>/accept/`

## 9) API DRF

Baza:
- `/api/v1/` (principala)
- `/api/` (compatibilitate temporara)

Resurse principale:
- `/api/v1/help-requests/`
- `/api/v1/volunteer-applications/`
- `/api/v1/bookings/`
- `/api/v1/conversations/`
- `/api/v1/chat-messages/`
- `/api/v1/reviews/`
- `/api/v1/verifications/`
- `/api/v1/reports/`
- `/api/v1/notifications/`
- `/api/v1/notification-preferences/`
- `/api/v1/services/`
- `/api/v1/service-categories/`
- `/api/v1/providers/`
- `/api/v1/ads/`
- `/api/v1/offers/`

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
- Crearea `help-requests` suporta `Idempotency-Key` in header (retry sigur).
- Throttling este activ pe endpoint-uri sensibile.

Schema si health:
- `/api/v1/schema/`
- `/health/`

## 10) Ce NU se foloseste (sau e conditional)

- `payments`: eliminat din proiectul curent
- push WS via Channels: conditional (fallback activ, dar fara dependinta channels in requirements)
- Celery+Redis real async: conditional (doar daca dezactivezi eager mode)
- Sentry: conditional (doar cu DSN)
- Next.js: optional, separat de runtime-ul Django

## 11) Backup / restore

Vezi:
- `docs/backup_restore.md`

Exemplu SQLite:
```bash
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > backups/data.json
python manage.py loaddata backups/data.json
```

## 12) Recomandare practica

Daca vrei o baza stabila si clara acum:
1. trateaza Django Templates + DRF ca produs principal
2. marcheaza explicit `frontend/` ca optional/prototip separat
3. decide ulterior daca migrezi UI complet in Next.js sau mentii frontend-ul Django

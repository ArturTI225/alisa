# LaUsaTa

LaUsaTa este o platforma comunitara pentru cereri de ajutor, voluntariat si servicii locale.
Proiectul este construit in Django 5, cu API REST, WebSockets, dashboard-uri dedicate pentru provideri si fluxuri complete pentru help requests si bookings programate.

## Ce include versiunea curenta

- autentificare si profiluri pe roluri: client, provider, admin
- pagini home diferite in functie de rol
- catalog de servicii si profiluri de provider
- favorite pentru servicii si provideri
- flux complet help request: creare, aplicare, acceptare, start, finalizare, moderare
- flux complet bookings programate: creare, accept/decline, reprogramare, start, finalizare, confirmare/disputa
- booking attachments, reguli recurente, calendar feed ICS, export activitate CSV
- dashboard provider cu statistici si activitate
- chat cu conversatii si mesaje, plus notificari live
- notificari, preferinte de notificare, rapoarte, verificari, audit log
- reviews cu recalcul automat de rating pentru provider
- health endpoints, schema OpenAPI, Django admin

## De ce exista ambele: Help Requests vs Bookings

Pe scurt, nu sunt acelasi lucru. Platforma acopera doua tipuri diferite de nevoie:

- Help Request = cerere de ajutor voluntar, porneste fara provider fix, cu aplicatii de la voluntari si selectie ulterioara.
- Booking = cerere programata de serviciu, orientata pe slot de timp, calendar, reprogramari si flux operational de executie.

Diferente cheie:

- Initiere:
Help Request este publicata de client pentru comunitate; Booking este creat ca o cerere programata cu detalii de executie (service, adresa, interval).
- Potrivire provider:
Help Request foloseste Volunteer Applications si apoi acceptarea unei aplicatii; Booking poate porni direct cu provider atribuit sau gasit de sistem.
- Flux de status:
Help Request: open, in_review, matched, in_progress, done, cancelled.
Booking: pending, confirmed, in_progress, awaiting_client, completed, canceled, declined, disputed, reschedule_requested.
- Functionalitati dedicate:
Help Request are lock/unlock de admin, moderare si certificat de completare; Booking are dispute workflow, recuring rules, calendar ICS si export CSV pentru activitate provider.
- Scop de produs:
Help Request acopera componenta sociala/non-comerciala de voluntariat; Booking acopera livrarea programata a serviciilor.

## Stack tehnic

- Python 3.13
- Django 5.2
- Django REST Framework 3.16
- Channels + Daphne (ASGI)
- Celery (default eager in dezvoltare)
- SQLite implicit, PostgreSQL optional prin DATABASE_URL
- Templates server-side (fara frontend separat React/Next)

Aplicatii Django principale:

- accounts
- services
- bookings
- ads
- chat
- reviews
- pages

## Rute web importante

- /
- /admin/
- /accounts/signup/
- /accounts/login/
- /accounts/profile/
- /accounts/favorites/
- /accounts/notifications/
- /services/
- /bookings/
- /bookings/new/
- /bookings/provider/dashboard/
- /bookings/calendar.ics
- /chat/
- /help-requests/create/
- /help-requests/<id>/apply/
- /help-requests/<id>/start/
- /applications/
- /applications/<id>/accept/
- /health/
- /healthz/

## API

Baza API:

- /api/v1/
- /api/v1/schema/

Resurse principale:

- /api/v1/service-categories/
- /api/v1/services/
- /api/v1/providers/
- /api/v1/bookings/
- /api/v1/help-requests/
- /api/v1/volunteer-applications/
- /api/v1/conversations/
- /api/v1/chat-messages/
- /api/v1/reviews/
- /api/v1/verifications/
- /api/v1/reports/
- /api/v1/notifications/
- /api/v1/notification-preferences/
- /api/v1/favorite-services/
- /api/v1/favorite-providers/
- /api/v1/addresses/
- /api/v1/ads/
- /api/v1/offers/

Actiuni custom importante:

- POST /api/v1/help-requests/{id}/cancel/
- POST /api/v1/help-requests/{id}/start/
- POST /api/v1/help-requests/{id}/complete/
- POST /api/v1/help-requests/{id}/send_to_review/
- POST /api/v1/help-requests/{id}/approve/
- POST /api/v1/help-requests/{id}/reject/
- POST /api/v1/help-requests/{id}/lock/
- POST /api/v1/help-requests/{id}/unlock/
- GET /api/v1/help-requests/{id}/certificate/
- POST /api/v1/volunteer-applications/{id}/accept/
- POST /api/v1/volunteer-applications/{id}/reject/
- POST /api/v1/volunteer-applications/{id}/withdraw/

Compatibilitate temporara:

- /api/ este mapat catre acelasi router (in paralel cu /api/v1/)

## WebSocket endpoints

- ws/notifications/
- ws/chat/<conversation_id>/

## Setup local rapid

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Important:

- fisierul .env.example nu este versionat in repo
- creeaza manual fisierul .env in radacina proiectului

Exemplu minim .env:

```env
SECRET_KEY=dev-secret-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CELERY_TASK_ALWAYS_EAGER=True
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Optional pentru productie

Redis channel layer (mai multe instante ASGI):

```bash
pip install channels-redis
```

PDF rendering real pentru certificate (in loc de fallback):

```bash
pip install weasyprint fonttools tinycss2 cssselect2 pydyf pyphen
```

Celery worker (cand CELERY_TASK_ALWAYS_EAGER=False):

```bash
celery -A config worker -l info
```

## Verificare rapida

```bash
python manage.py check
python manage.py test pages.tests bookings.tests
```

## Note UI

Ghidul de UI pentru template-uri si componente este in docs/UI.md.
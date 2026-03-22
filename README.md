# LaUsaTa

LaUsaTa este o platforma comunitara functionala construita cu Django 5 si DRF. Aplicatia actuala include pagini publice, conturi pe roluri, cereri de ajutor, aplicatii de voluntariat, bookings, chat, notificari, review-uri, moderare si administrare.

## Ce functioneaza in proiect

- Utilizatori pe roluri: client, provider, admin
- Pagini home diferite pentru public, client si worker
- Catalog de servicii si director de provideri
- Favorite pentru servicii si provideri
- Fluxul de help request:
  - creare cerere
  - upload de atasamente
  - aplicare din partea voluntarului
  - acceptarea aplicatiei de catre solicitant
  - tranzitii prin statusurile `open`, `in_review`, `matched`, `in_progress`, `done`, `cancelled`
  - actualizare certificat si statistici pentru voluntar la finalizare
- Fluxul de volunteer application cu statusurile `pending`, `accepted`, `rejected`, `withdrawn`
- Fluxul de booking:
  - creare booking
  - acceptare sau refuz
  - reprogramare
  - start si completare
  - confirmare sau disputa din partea clientului
  - atasamente, booking-uri recurente, calendar feed, provider dashboard, export CSV
- Conversatii si mesaje in chat cu atasamente
- Notificari si preferinte de notificare
- Review-uri cu recalcularea automata a ratingului providerului
- Verificari, rapoarte, moderare si audit log
- Django admin
- API REST, schema endpoint si health check

## Stack-ul proiectului

- Django 5.2
- Django REST Framework 3.16
- Aplicatii: `accounts`, `services`, `bookings`, `ads`, `chat`, `reviews`, `pages`
- Interfata principala: Django Templates din `templates/`
- Asset-uri statice in `static/`
- Baza de date implicita: SQLite
- Baza de date alternativa: PostgreSQL prin `DATABASE_URL`
- Limba implicita: romana

## Fluxuri principale

### Help requests

Clientii pot crea cereri de ajutor din interfata principala, pot adauga fisiere media si le pot publica pentru voluntari. Providerii pot vedea cererile deschise, pot aplica si pot incepe lucrarea dupa acceptare. Solicitantul sau adminul poate accepta o aplicatie, iar voluntarul atribuit poate muta cererea in lucru si apoi o poate finaliza.

### Bookings

Modulul de booking este activ si include creare booking, acceptare, refuz, cereri de reprogramare, dispute, reguli recurente, atasamente, vizualizare invoice, export ICS si pagini de dashboard pentru provider.

### Comunicare si incredere

Utilizatorii potriviti pot comunica prin conversatii si mesaje in chat. Platforma include si review-uri, verificari, rapoarte de abuz, notificari si audit log pentru actiuni sensibile.

## Rute principale

- `/`
- `/admin/`
- `/accounts/signup/`
- `/accounts/login/`
- `/accounts/profile/`
- `/accounts/favorites/`
- `/accounts/notifications/`
- `/services/`
- `/bookings/`
- `/bookings/new/`
- `/chat/`
- `/help-requests/create/`
- `/help-requests/<id>/apply/`
- `/help-requests/<id>/start/`
- `/applications/<id>/accept/`
- `/health/`

## API

Baza API:

- `/api/v1/`
- `/api/v1/schema/`

Resurse principale:

- `/api/v1/service-categories/`
- `/api/v1/services/`
- `/api/v1/providers/`
- `/api/v1/bookings/`
- `/api/v1/help-requests/`
- `/api/v1/volunteer-applications/`
- `/api/v1/conversations/`
- `/api/v1/chat-messages/`
- `/api/v1/reviews/`
- `/api/v1/verifications/`
- `/api/v1/reports/`
- `/api/v1/notifications/`
- `/api/v1/notification-preferences/`
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

## Pornire locala

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Variabile de mediu de baza:

- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`

## Verificare rapida

```bash
python manage.py check
```

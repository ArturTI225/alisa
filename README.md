# Sot la ora – platforma handy-men (Django + DRF)

MVP functional pentru platforma „sot la ora”: Django 5 + DRF, template-uri mobile-first, modele si API pentru clienti, prestatori si admin.

## Cerinte
- Python 3.13+ (venv recomandat)
- PostgreSQL (optional, default SQLite)

## Setup rapid
```bash
python -m venv .venv
.venv\Scripts\activate  # pe Windows (sau `source .venv/bin/activate` pe Linux/Mac)
pip install -r requirements.txt
copy .env.example .env  # setari locale; ajusteaza SECRET_KEY si DATABASE_URL
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Ce e inclus
- **Accounts**: model User custom cu roluri (client/prestator/admin), profil prestator, adrese salvate, signup/login, profil.
- **Servicii**: categorii + servicii cu tip de pret (ora/fix), pagina listare cu filtre.
- **Rezervari**: formular rezervare (cu selectie prestator optional), auto-atribuire prestator disponibil pe slot, lista comenzi, model Booking cu status si pret estimat, disponibilitati prestator.
- **Chat/Reviews**: mesaje pe comanda, review 1:1 pe booking cu rating si poza optionala.
- **Plati**: model Payment gata de legat la Stripe (PaymentIntent id).
- **API** (DRF): servicii, categorii, adrese, bookings, plati, chat, reviews la `/api/`.
- **UI**: landing page, cum functioneaza, FAQ, servicii, rezervare cu stepper, profil, pagina „Devino sot la ora”, profil prestator public; stil modern (turcoaz + accent auriu), mobile-first.

## Structura aplicatii
- `accounts` – user custom, adrese, profiluri client/prestator, signup/profile views.
- `services` – categorii/servicii + API read-only.
- `bookings` – Booking + Availability, formular de rezervare, lista/detaliu, auto-matching prestatori, API CRUD cu permisiuni pe utilizator.
- `payments` – model Payment si API read-only.
- `chat` – mesagerie pe booking.
- `reviews` – review per booking.
- `pages` – landing, cum functioneaza, FAQ, pagina aplicare prestatori.
- `frontend/` – Next.js 14 + TypeScript + Tailwind + Framer Motion/GSAP demo landing (SSR/SPA ready) ce consuma API-ul DRF.

## Endpoints rapide
- UI: `/` landing, `/services/`, `/bookings/new/`, `/bookings/`, `/accounts/signup`, `/accounts/login`, `/devino-sot-la-ora/`.
- API: `/api/services/`, `/api/service-categories/`, `/api/bookings/`, `/api/addresses/`, `/api/chat-messages/`, `/api/reviews/`, `/api/payments/`.

## Pasi urmatori
- Integrare Stripe (PaymentIntent + webhooks) si generare factura PDF.
- Confirmare si editare slot din partea prestatorilor + notificari email/SMS.
- Upload media pe S3/compatibil; antivirus/limitare dimensiune atasamente.
- Rate limiting pe login/reset si audit logging evenimente cheie.

## Frontend Next.js (SSR + animații)
```bash
cd frontend
cp .env.local.example .env.local  # ajustează baza API în funcție de unde rulează Django
npm install
npm run dev  # ascultă pe http://localhost:8000 (0.0.0.0 în Docker)
```
Rulează Django pe alt port (ex: `python manage.py runserver 8001`) și setează:
- pe host: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api`
- din Docker: `NEXT_PUBLIC_API_URL=http://host.docker.internal:8001/api`

Date demo: `python manage.py loaddata services/fixtures/sample_services.json` pentru a popula `/api/services/` și a vedea cardurile în grid.

Landing-ul include:
- Hero animat (Framer Motion, glass card rezervare, parallax ScrollTrigger + Lottie pulse)
- Secțiune „Cum funcționează” cu ScrollTrigger (GSAP)
- Grid servicii din API DRF (SWR fetch)
- Showcase comenzi cu modal layoutId (Framer Motion shared layout)
- Smooth scroll cu Lenis
Pentru auth: DRF poate folosi sesiuni/JWT; fetch-urile includ credențiale (cookies). Configurează login endpoint corespunzător pe backend și setează cookie-urile HttpOnly.

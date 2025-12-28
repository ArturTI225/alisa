# Platforma digitala pentru clienti si mesteri

Document de lucru care raspunde obiectivelor cerute: analiza domeniului, comparatie cu solutii existente, cerinte, arhitectura, plan de executie, costuri si documentare.

## 1. Probleme actuale in piata
- Raspuns lent: nu exista SLA-uri, mesterii raspund selectiv, clientii posteaza anunturi pe mai multe site-uri pentru a primi macar un raspuns.
- Lipsa transparentei: identitatea si istoricul mesterilor nu sunt vizibile; preturile sunt adesea obscure (fara estimari standard).
- Risc de servicii neconforme: fara verificare identitate/competențe, fara mecanism de dispute sau feedback verificat pe job.
- Conversatie fragmentata: comunicare in afara platformei (telefon/WhatsApp) => imposibil de auditat, se pierd atasamente si detalii.
- Management slab al anunturilor: filtrare rudimentara, greu de marcat urgente, nu exista prioritizare in feed.

## 2. Solutii existente si gap-uri
- Site-uri de anunturi generaliste (ex: OLX, Publi24): volum mare, dar fara verificare, fara matching automat, chat simplu, nu gestioneaza programari.
- Platforme internationale (TaskRabbit, Thumbtack, HomeAdvisor): matching si plati integrate, insa nu au adaptare locala (limba, preturi, TVA, metode locale, legislatie).
- Grupuri sociale / recomandari: ridica increderea (prin cunoscuti), dar nu sunt scalabile si nu ofera SLA, filtre sau garantii.
- Aplicatii mobile de nisa (curatenie, instalatori): bune pe verticala, dar limitate ca acoperire de servicii, preturi fixe, greu de extins.
**Necesitatea unei solutii noi**: combinarea verificarii mesterilor, matching rapid (inclusiv urgente), chat securizat si rating bidirectional, cu integrare de plati locale si notificari in timp real.

## 3. Stakeholderi si fluxuri
- Client: cauta/filtreaza, posteaza anunt (normal/urgent), selecteaza mester sau accepta matching automat, comunica, plateste, lasa review.
- Mester: isi completeaza profil/verificare, seteaza disponibilitati, primeste anunturi relevante, accepta/declina, comunica, marcheaza jobul ca finalizat, solicita plata.
- Admin/suport: gestioneaza verificari, disputes, moderare continut, rapoarte de performanta.

## 4. Cerinte functionale (MVP extins)
- Conturi si roluri (client, mester, admin); verificare identitate mester (documente, status pending/verified/rejected).
- Profil mester: bio, competente, tarif orar/fix, oras/raza, disponibilitati + exceptii, portofoliu foto, badge verificat.
- Catalog servicii: categorii, tipuri de pret (ora/fix), descrieri standard, tag-uri (ex: urgenta, garantie).
- Anunturi:
  - creare/editare/anulare; descriere, foto, locatie, buget, fereastra orara.
  - flag de `urgent` care ridica prioritatea in feed si trimite notificari push/SMS targetate.
  - optiune de auto-matching (sugereaza 3-5 mesteri disponibili dupa locatie/skill/recenzie).
- Filtrare si cautare: dupa categorie, oras/raza, disponibilitate, tarif, rating, badge verificat, urgent.
- Booking si programare: alegerea slotului, estimare pret, accept/decline din partea mesterului; reprogramare cu istoric si audit.
- Chat securizat pe booking + atasamente; logare evenimente (schimbare status, oferte, clarificari).
- Notificari in timp real: push/browser + email + SMS (pentru urgente si status critic); preferinte configurabile per utilizator.
- Reviews bidirectionale: client->mester si mester->client, legate de booking finalizat, cu scor si text; agregare rating vizibil pe profil.
- Dispute: deschidere, mesaje, atasamente, escaladare la admin, rezolutie si note.
- Plati: integrare cu procesator (Stripe/Plati.ro), intentie de plata la confirmare, capturare la finalizare; refund partial/total; facturare.
- Admin UI: moderare anunturi/recenzii, onboarding mesteri, rapoarte KPI, management dispute.
- SEO/landing/FAQ + onboarding ghidat.

## 5. Cerinte nefunctionale
- Performanta: TTFB < 200ms pe API pentru liste filtrate (cu cache), latenta chat < 1s; paginare server-side.
- Disponibilitate: 99.5% target initial; backup DB zilnic; strategii de retry pentru trimiteri notificari.
- Securitate: auth cu JWT/sesiune, 2FA optional, rate limiting login/reset, validare fisier atasamente (tip/dimensiune), izolarea fisierelor pe storage S3 compatibil.
- Privacy: minimizarea datelor personale, log-uri de acces, stergere cont si export date (GDPR).
- Observabilitate: metrics (APM), logs structurate, alerte pe erori critice si cozi blocate.
- Accesibilitate: WCAG AA pentru UI; design mobile-first; text clar pentru urgente.

## 6. Arhitectura propusa (adaptata la codul existent)
- Backend: Django + DRF (deja in repo) pentru API; Django Channels/WebSockets pentru chat/notificari live; Celery + Redis pentru joburi (notificari, matching, reminder plati).
- Frontend: Next.js 14 + Tailwind (deja in repo) pentru landing/app; fetch via API; starea auth prin cookies (HttpOnly) sau JWT stocat sigur.
- Baza de date: PostgreSQL (prod), SQLite doar local; modele existente: User/ProviderProfile/Booking/Chat/Review/Payment.
- Cache/queue: Redis pentru rate limiting, cozi notificari si cache filtre.
- Storage: S3 compatibil pentru atasamente si media.
- Notificari: email (SMTP/SendGrid), push web/app, SMS pentru urgente (Twilio/Orange SMS).
- Observabilitate: Sentry (erori), Prometheus/Grafana (metrics), ELK/Opensearch pentru loguri.

## 7. Modelare si extensii cheie
- Anunturi/booking: adauga camp `is_urgent` (boolean) si `urgency_level` (low/normal/high) pe Booking/Request; indexare pe oras + urgent pentru feed rapid.
- Matching: serviciu care verifica disponibilitatea mesterilor (Availability + exceptii), scor combinat: proximity + rating + SLA raspuns + pret.
- Rating: review per booking deja in repo; extinde cu review mester->client si agregare scoring (NPS simplu, medie ponderata).
- Notificari: persistenta deja exista; adauga WebSocket topic pe user + fallback email/SMS; worker care trimite push la eventuri (status booking, urgent, disputa).
- Dispute: model existent; adauga SLA-uri (timp raspuns admin), sabloane de mesaje si scor de risc pentru mesteri.

## 8. Fluxuri principale (succint)
- Creare anunt (normal): client -> formular -> estimare pret -> se posteaza; mesteri potriviti primesc notificare; primul care accepta blocheaza slotul.
- Anunt urgent: client marcheaza `urgent`; sistemul trimite notificari prioritare la mesterii cu disponibilitate in urmatoarele X ore; feed ordonat cu urgent primele.
- Chat pe booking: WebSocket + fallback polling; atasamente limitate (tip/dimensiune); audit trail.
- Review bidirectional: dupa finalizare, ambele parti primesc remindere; rating agregat cu greutate mai mare pentru joburi verificate/platie capturata.
- Reprogramare: request -> aprobare/declinare -> log eveniment + notificari.

## 9. Algoritmi de filtrare si cautare
- Indexare (PostgreSQL): GIN pe full-text (titlu/descriere), BTREE pe oras, categorie, urgent, rating mediu, pret.
- Scor feed: `score = w1*urgent + w2*proximity + w3*rating + w4*recency + w5*match_skill`; parametri ajustabili.
- Debounce + paginare (cursor/offset) pe UI; cache pe combinatii frecvente de filtre 1-5 minute.

## 10. Securitate si compliance
- Validare input server-side; sanitizare HTML pentru descrieri/mesaje.
- Limitare atasamente (<=10MB, tipuri whitelisted) si scan antivirus in worker.
- Rate limiting pe login/reset/mesaje; throttling API.
- Backups automate + criptare at-rest si in-transit (HTTPS obligatoriu).

## 11. Plan de promovare si adoptare
- Lansare soft in 1-2 orase cu mesteri verificati manual; oferte de early adopter pentru clienti (reduceri/credit).
- Parteneriate cu magazine DIY/echipamente, asociatii profesionale; referral program client/mester.
- Continut educativ: ghiduri preturi, checklist verificare mester, studii de caz.
- Campanii performance pe cautari locale (Google/Meta) directionate spre landing cu CTA clar.
- KPI initiali: timp mediu raspuns < 10 minute pentru urgente, rata acceptare > 40%, NPS > 45.

## 12. Estimare costuri (MVP 6-8 luni, echipa 4-6 oameni)
- Infra: ~300-600 EUR/luna (Postgres managed, Redis, S3, 2-3 mici VM/containers); + cost SMS/push/email (0.03-0.06 EUR/SMS).
- Dezvoltare: ~5-7 persoane-luna pentru MVP complet (backend, frontend, mobile optional, QA, product/design).
- Operare: suport 0.5-1 FTE, moderare/verificari mesteri.

## 13. Roadmap propus (iterativ)
1) Hardening fundament: auth, rate limiting, logs, backup, migrari Postgres, storage S3, pipeline CI.
2) Urgente si matching: camp `is_urgent`, ordonare feed, notificari push/SMS prioritare, modul scoring matching.
3) Chat si notificari realtime: Django Channels, topic per user, worker Celery pentru trimiteri; UI chat cu typing/seen.
4) Plati si facturare: integrare Stripe/Plati.ro, capturare la finalizare, facturi PDF, refund-uri.
5) Review bidirectional + reputatie: collectare automata, badge-uri, scor public; penalitati pentru neprezentare.
6) Admin & suport: dashboard verificari, dispute SLA, rapoarte KPI, exporturi.
7) Promovare si growth: landing optimizat, referral, parteneriate locale.

## 14. Taskuri imediate (pentru repo-ul actual)
- Documentare: acest fisier (livrat) + ghid tehnic pentru deploy prod (DB, Redis, Celery, Channels, S3).
- Backlog tehnic:
  - Adauga pe Booking campurile `is_urgent`, `urgency_level`, index pe `(city, is_urgent, created_at)`.
  - API: filtre noi (urgent, city, rating minim), endpoint pentru preferinte notificari SMS/push.
  - Notificari: worker Celery + WebSocket hub; integrare eventuri existente (BookingEvent).
  - Matching: serviciu care cauta mesteri disponibili (Availability/Exceptions) si trimite oferte.
  - UI: badge urgent vizibil in liste/detalii; sortare prioritara; onboarding mester cu verificare.
- QA: adauga teste pentru filtre booking si flux urgent; teste de permisiuni pe chat/reviews.

## 15. Documentare licenta / tehnica
- Structura recomandata pentru raport: Introducere, Analiza domeniu, Studiu comparativ, Cerinte, Arhitectura si model date, Implementare (backend/frontend), Testare, Plan operare si securitate, Estimare costuri, Concluzii.
- Documentatie tehnica: diagrame secventa pentru flux urgent, diagrame componente, specificatii API (OpenAPI), instructiuni de deploy (Docker/compose), playbook incident (backup/restore, rotire chei).

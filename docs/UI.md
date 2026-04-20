# UI Guide

Acest document descrie stratul UI folosit in demo-ul Django Templates.

## Directie

- UI-ul principal traieste in `templates/` si `static/`.
- Nu exista un frontend separat in React sau Next.js in repo-ul curent.
- Shell-ul comun este definit in `templates/base.html`.

## Tokens si CSS

- Token-urile de baza sunt in `static/css/tokens.css`.
- CSS-ul principal ramane in `static/css/style.css`.
- Componentele partajate au stiluri dedicate in `static/css/components/`.

## Componente Template

Partialele reutilizabile sunt in `templates/components/`.

- `_button.html`
- `_card.html`
- `_empty_state.html`
- `_form_field.html`
- `_avatar.html`
- `_badge.html`
- `_toast.html`
- `_breadcrumbs.html`

Regula practica: daca un ecran nou are butoane, empty states sau campuri de formular, reuseaza partialele existente in loc sa dublezi markup-ul.

## Shell UI

`templates/base.html` livreaza comportamentul comun:

- skip link pentru accesibilitate
- navigatie activa cu `aria-current`
- breadcrumbs pe paginile interioare
- command palette cu `Ctrl/Cmd + K`
- regiune live pentru toast-uri
- hook pentru notificari live prin `ws.js`

Datele comune pentru shell vin din `accounts.context_processors.shell_context`.

## Formulare

- Campurile randate manual trebuie sa foloseasca `_form_field.html`.
- Pentru checkbox-uri si toggle-uri, foloseste in continuare acelasi partial; stilurile din `static/css/components/form.css` acopera si aceste cazuri.
- Evita `{{ form.as_p }}` pe ecranele noi.

## Notificari

- Preferintele sunt gestionate prin `NotificationPreference`.
- Sunetul pentru notificari live este opt-in si este expus in shell prin atributul `data-notification-sound-enabled` de pe `<body>`.
- JS-ul din `static/js/app.js` trebuie sa respecte acest flag si sa ramana silent implicit.

## Testare minima

Inainte de demo sau de un refactor vizibil:

- `python manage.py check`
- `python manage.py test accounts.tests pages.tests chat.tests`
- `node --check static/js/app.js`

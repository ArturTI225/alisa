# Guideline landing (RO-first, RU/EN secondary, MDL)

## Paleta de culori (hex)
- Fundal primar: `#F5F7FA` (aproape alb).
- Carduri: `#FFFFFF` cu umbră soft (blur 20, opacitate 10-12%).
- Accent principal: verde proaspăt `#06A04A` sau mentă `#21CA73`.
- Accent urgent: galben/portocaliu `#F6A623` / `#EFA73F` (butoane “Urgent”, “Comandă acum”).
- Text: grafit `#10131A`; secundar `#7A808A`; linii/divideri `#E5E8EF`.

## Tipografie
- Familie: Inter / Poppins / SF Pro (grotesc geometric).
- Dimensiuni: H1 40–48px desktop (28–32px mobile); H2 28–32px; body 14–16px.
- Stil: titluri bold + subtext mic, stil landing SaaS/marketplace.

## Ilustrații & SVG
- Pattern de fundal low-opacity cu unelte (cheie, bormașină, șurubelniță, pensulă) în hero și footer.
- Personaje SVG meșteri (stickers, flat).
- Iconițe categorii în pilule/cerc: curățenie, electric, sanitar, mobilă etc.

## Structură pagină principală (desktop)
1) **Hero 2 coloane**
   - Stânga: H1 “Găsește un meșter verificat în câteva clicuri”, subtext scurt. Căutare combinată: input serviciu (“Ce ai nevoie?”), input locație, buton “Găsește meșter”. Sub bară: pilule rapide (“Am nevoie urgent”, “Rating 4+”, “Meșter lângă mine”).
   - Dreapta: mockup telefon/card cu animație (carduri meșteri care plutesc). Badge-uri plutitoare: “+24 meșteri online”, “Comandă urgentă preluată”, bubble rating “4.9 ★”.
   - Motion: parallax SVG unelte; carduri cu transform; buton hover cu glow.

2) **Categorii servicii**
   - Carduri mari, 3–4 pe rând. Conținut: icon meșter, titlu (“Electrică”, “Sanitară”, “Montaj mobilă”), text “de la 200 MDL/oră, 120 meșteri”.
   - Hover: lift + mic “hop” al iconiței.

3) **Lentă “Anunțuri urgente”**
   - Scroll orizontal tip stories. Badge “URGENT” portocaliu cu puls ușor; titlu task; locație + buget; timer “azi până la 20:00”. Swipe friendly pe mobil.

4) **“Cei mai buni în orașul tău”**
   - Card meșter: avatar rotund într-un oval colorat, nume + badge “Pro/Verified”, rating (4.8 ★ 120), tag-uri servicii, butoane “Scrie” / “Vezi profil”. Hover: card se deschide ușor și arată 1–2 review-uri; icon chat se iluminează.

5) **Cum funcționează (3 pași)**
   - “Descrie task”, “Alege meșter”, “Plătește și lasă review”. SVG/Lottie liniare, micro-animări (checkbox, cursor).

6) **Încredere & review-uri**
   - Carduri cu citat + rating; vizual “Client ↔ Meșter” pentru review bidirecțional. Badge-uri: “Telefon verificat”, “ID verificat”, “Plăți protejate” (shield/lock).

## Animații (guideline)
- Micro-interactions: hover pe carduri/butoane; dropdown-uri cu apariție smooth; skeletons la încărcare listă.
- Motion controlat: 180–240ms, easing `cubic-bezier(0.4,0.0,0.2,1)`, max 1–2 elemente în mișcare per viewport.
- Lottie/SVG: 1–2 piese cheie (hero + “Cum funcționează”), rest doar CSS transitions.

## Localizare și prețuri
- Limbă principală: română (RO). RU/EN doar ca tooltips/footnotes dacă e nevoie.
- Prețuri afișate în MDL (lei moldovenești), ex: “de la 200 MDL/oră”.

## Livrabile pentru front/design
- Copia și textele de mai sus (RO-first).
- Paleta și stilurile de carduri/badge-uri pentru “Urgent”.
- Layout secțiuni: hero cu search, categorii cu iconițe, carusel urgent, top meșteri, flow 3 pași, încredere/review.
- Animații: parallax unelte în hero, float carduri meșteri, puls badge urgent, hover lift pe carduri, glow pe CTA verde.

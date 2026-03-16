"use client";

import { useEffect } from "react";
import Lenis from "lenis";
import { Hero } from "@/components/Hero";
import { ScrollScene } from "@/components/ScrollScene";
import { ServiceGrid } from "@/components/ServiceGrid";
import { BookingShowcase } from "@/components/BookingShowcase";
import { useServices, Service } from "@/hooks/useServices";
import { useUrgentAds, Ad } from "@/hooks/useAds";
import { useProviders, Provider } from "@/hooks/useProviders";
import { useI18n } from "@/app/i18n/useI18n";
import { useReducedMotion } from "@/hooks/useReducedMotion";

type Props = {
  initialServices?: Service[];
  initialAds?: any;
  initialProviders?: any;
};

const statusFlow = [
  { key: "open", label: "open", desc: "Vizibilă voluntarilor; aplicații deschise" },
  { key: "in_review", label: "in_review", desc: "Moderare admin; acces restricționat" },
  { key: "matched", label: "matched", desc: "Voluntar acceptat; pregătire pentru start" },
  { key: "in_progress", label: "in_progress", desc: "Lucrare în curs; chat activ" },
  { key: "done", label: "done", desc: "Finalizată; certificate și recenzie" },
  { key: "cancelled", label: "cancelled", desc: "Anulată cu motiv auditabil" },
];

export function LandingClient({ initialServices, initialAds, initialProviders }: Props) {
  const { services, isLoading, error } = useServices(initialServices);
  const { ads: urgentAds } = useUrgentAds(initialAds);
  const { providers } = useProviders(4, initialProviders);
  const t = useI18n("ro");
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) return;
    const lenis = new Lenis({ lerp: 0.08 });
    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
    return () => lenis.destroy();
  }, [prefersReducedMotion]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-12 px-4 py-10">
      <Hero />

      <section className="grid gap-4 md:grid-cols-2 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-sm">
          <div className="text-xs font-semibold uppercase text-primary">Flux principal</div>
          <h2 className="text-xl font-bold">Request → Match → Accept</h2>
          <ul className="mt-3 space-y-1 text-sm text-slate-700">
            <li>• Cererea este vizibilă voluntarilor.</li>
            <li>• Aplică cu mesaj + disponibilitate.</li>
            <li>• Alegi voluntarul și porniți misiunea.</li>
          </ul>
        </div>
        <div className="rounded-2xl border border-slate/20 bg-white p-4 shadow-sm">
          <div className="text-xs font-semibold uppercase text-slate-600">Instant booking (secundar)</div>
          <h2 className="text-xl font-bold text-slate-800">Direct accept dacă ai deja un voluntar</h2>
          <ul className="mt-3 space-y-1 text-sm text-slate-700">
            <li>• Sari peste aplicații.</li>
            <li>• Confirmi voluntarul direct.</li>
            <li>• Folosește doar când există acord prealabil.</li>
          </ul>
        </div>
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">{t("section.categories.subtitle")}</div>
            <h2 className="text-3xl font-bold">{t("section.categories.title")}</h2>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/services/">
            {t("section.categories.viewAll")}
          </a>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[
            { title: "Electrica", sub: "Voluntari verificați, timp mediu ~60 min", icon: "🔌" },
            { title: "Sanitara", sub: "Ajutor gratuit, intervenții rapide", icon: "🚿" },
            { title: "Montaj mobila", sub: "Sprijin pentru montaj și transport", icon: "🛠️" },
            { title: "Curățenie", sub: "Echipe de voluntari pentru spații curate", icon: "🧽" },
          ].map((c) => (
            <div
              key={c.title}
              className="flex h-full flex-col gap-2 rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="text-3xl">{c.icon}</div>
              <h3 className="text-lg font-semibold">{c.title}</h3>
              <p className="text-sm text-slate-600">{c.sub}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-primary">{t("section.urgent.subtitle")}</div>
            <h2 className="text-3xl font-bold">{t("section.urgent.title")}</h2>
          </div>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700">
            Story swipe
          </span>
        </div>
        <div className="flex snap-x gap-4 overflow-x-auto pb-2">
          {(urgentAds.length
            ? urgentAds.map((ad: Ad) => ({
                title: ad.title,
                city: ad.city,
                timer: ad.preferred_date ? `pana la ${ad.preferred_date}` : "astazi",
              }))
            : [
                { title: "Prize nu funcționeaza", city: "Chișinau, Centru", timer: "azi, 20:00" },
                { title: "Țeava spartă în baie", city: "Chișinau, Rașcani", timer: "azi, 18:30" },
                { title: "Montaj dulap IKEA", city: "Balți", timer: "mâine, 10:00" },
              ]
          ).map((ad) => (
            <div
              key={ad.title}
              className="snap-start min-w-[240px] rounded-2xl border border-amber-200 bg-white/90 p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-amber-500 px-3 py-1 text-xs font-bold uppercase text-white">
                <span className="animate-pulse">⚡</span> Urgent
              </div>
              <h3 className="text-lg font-semibold">{ad.title}</h3>
              <p className="text-sm text-slate-600">{ad.city}</p>
              <div className="mt-2 flex items-center justify-between text-sm font-semibold text-slate-800">
                <span>Ajutor voluntar</span>
                <span className="text-amber-600">{ad.timer}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">{t("section.recommended.subtitle")}</div>
            <h2 className="text-3xl font-bold">{t("section.recommended.title")}</h2>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/services/">
            {t("section.categories.viewAll")}
          </a>
        </div>
        <ServiceGrid
          services={services.map((s) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            infoLabel: s.duration_estimate_minutes ? `~${s.duration_estimate_minutes} min · voluntar` : "Ajutor voluntar",
            category: s.category?.name || "Serviciu",
          }))}
          isLoading={isLoading}
          error={error}
        />
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">{t("section.providers.subtitle")}</div>
            <h2 className="text-3xl font-bold">{t("section.providers.title")}</h2>
            <p className="mt-1 text-xs text-slate-600">
              Legendă verificare: <span className="text-primary">Verificat</span> · <span className="text-amber-700">În verificare</span> · <span className="text-slate-600">Neverificat</span>
            </p>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/providers">
            {t("section.providers.viewAll")}
          </a>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {(providers.length
            ? providers.map((p: Provider) => ({
                name: p.first_name || p.last_name ? `${p.first_name} ${p.last_name}`.trim() : p.username,
                rating: p.rating_avg || "-",
                reviews: p.rating_count || 0,
                city: p.city,
                verification: (p as any).provider_profile?.verification_status || "unverified",
                tags: (p.provider_profile?.skills || []).slice(0, 2).map((s) => s.name),
              }))
            : [
                { name: "Ion Popescu", rating: "4.9", reviews: 120, verification: "approved", tags: ["Electrica", "Smart home"] },
                { name: "Maria Rusu", rating: "4.8", reviews: 98, verification: "approved", tags: ["Curățenie", "Dezinfectare"] },
                { name: "Alexei Cojocaru", rating: "4.7", reviews: 88, verification: "pending", tags: ["Mobila", "Montaj"] },
              ]
          ).map((p) => (
            <div
              className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
              key={p.name}
            >
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-primary/10 text-center text-xl leading-[48px]">{p.name[0]}</div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{p.name}</h3>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                        p.verification === "approved"
                          ? "bg-primary/10 text-primary"
                          : p.verification === "pending"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                      aria-label={`Verificare: ${p.verification}`}
                    >
                      {p.verification === "approved" ? "Verificat" : p.verification === "pending" ? "În verificare" : "Neverificat"}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600">
                    {p.rating} ★ ({p.reviews} recenzii)
                  </div>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-sm text-slate-700">
                {p.tags.map((t) => (
                  <span key={t} className="rounded-full bg-slate-100 px-3 py-1">
                    {t}
                  </span>
                ))}
              </div>
              <div className="mt-3 flex gap-2 text-sm font-semibold">
                <a
                  className="flex-1 rounded-xl bg-primary px-3 py-2 text-center text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                  href="/chat/"
                  aria-label={t("btn.chat")}
                >
                  {t("btn.chat")}
                </a>
                <a
                  className="flex-1 rounded-xl border border-primary px-3 py-2 text-center text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                  href="/accounts/provider"
                  aria-label={t("btn.profile")}
                >
                  {t("btn.profile")}
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">{t("section.status.subtitle")}</div>
            <h2 className="text-3xl font-bold">{t("section.status.title")}</h2>
          </div>
          <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
            {t("section.status.badge")}
          </span>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {statusFlow.map((s) => (
            <div
              key={s.key}
              className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4 shadow-sm"
            >
              <div className="text-xs font-semibold uppercase tracking-wide text-primary">{s.label}</div>
              <p className="mt-2 text-sm text-slate-700">{s.desc}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Tranziții permise: open → in_review → matched → in_progress → done; orice status poate merge în cancelled cu audit.
        </p>
      </section>

      <ScrollScene>
        <section className="space-y-3 rounded-3xl bg-white/70 p-8 shadow-glow">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-primary">3 pași simpli</div>
              <h2 className="text-3xl font-bold">Cum funcționeaza</h2>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { title: "Descrie task-ul", desc: "Scrii ce ai nevoie, atașezi foto/video." },
              { title: "Alegi voluntarul", desc: "Vezi verificarea, distanța și timpul estimat." },
              { title: "Confirmi și lași feedback", desc: "Finalizezi, mulțumești și primești certificat." },
            ].map((step, idx) => (
              <div key={step.title} className="step-card glass rounded-2xl p-4">
                <div className="text-sm font-semibold text-primary">0{idx + 1}</div>
                <h3 className="text-lg font-semibold">{step.title}</h3>
                <p className="text-sm text-slate-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollScene>

      <BookingShowcase />
    </main>
  );
}

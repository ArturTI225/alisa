"use client";

import { Hero } from "@/components/Hero";
import { ScrollScene } from "@/components/ScrollScene";
import { ServiceGrid } from "@/components/ServiceGrid";
import { BookingShowcase } from "@/components/BookingShowcase";
import { useServices } from "@/hooks/useServices";
import { useUrgentAds } from "@/hooks/useAds";
import { useProviders } from "@/hooks/useProviders";
import Lenis from "lenis";
import { useEffect } from "react";

export default function Page() {
  const { services, isLoading } = useServices();
  useEffect(() => {
    const lenis = new Lenis({ lerp: 0.08 });
    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
    return () => lenis.destroy();
  }, []);

  const { ads: urgentAds } = useUrgentAds();
  const { providers } = useProviders();

  return (
    <main className="mx-auto max-w-6xl space-y-12 px-4 py-10">
      <Hero />

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">Categorii populare</div>
            <h2 className="text-3xl font-bold">Alege tipul de serviciu</h2>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/services/">
            Vezi toate
          </a>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[
            { title: "Electrică", sub: "de la 200 MDL/oră · 120 meșteri", icon: "⚡" },
            { title: "Sanitară", sub: "de la 180 MDL/oră · 110 meșteri", icon: "🚿" },
            { title: "Montaj mobilă", sub: "de la 220 MDL/oră · 90 meșteri", icon: "🪚" },
            { title: "Curățenie", sub: "de la 150 MDL/oră · 140 meșteri", icon: "🧹" },
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
            <div className="text-sm font-semibold text-primary">Anunțuri urgente</div>
            <h2 className="text-3xl font-bold">Prinde o lucrare azi</h2>
          </div>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700">Story swipe</span>
        </div>
        <div className="flex snap-x gap-4 overflow-x-auto pb-2">
          {(urgentAds.length
            ? urgentAds.map((ad) => ({
                title: ad.title,
                city: ad.city,
                budget: ad.budget_max || ad.budget_min || "—",
                timer: ad.preferred_date ? `până la ${ad.preferred_date}` : "astăzi",
              }))
            : [
                { title: "Prize nu funcționează", city: "Chișinău, Centru", budget: "800 MDL", timer: "azi, 20:00" },
                { title: "Țeavă spartă în baie", city: "Chișinău, Râșcani", budget: "1200 MDL", timer: "azi, 18:30" },
                { title: "Montaj dulap IKEA", city: "Bălți", budget: "700 MDL", timer: "mâine, 10:00" },
              ]
          ).map((ad) => (
            <div
              key={ad.title}
              className="snap-start min-w-[240px] rounded-2xl border border-amber-200 bg-white/90 p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-amber-500 px-3 py-1 text-xs font-bold uppercase text-white">
                <span className="animate-pulse">●</span> Urgent
              </div>
              <h3 className="text-lg font-semibold">{ad.title}</h3>
              <p className="text-sm text-slate-600">{ad.city}</p>
              <div className="mt-2 flex items-center justify-between text-sm font-semibold text-slate-800">
                <span>Buget ~ {ad.budget}</span>
                <span className="text-amber-600">{ad.timer}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">Servicii recomandate</div>
            <h2 className="text-3xl font-bold">Top cereri</h2>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/services/">
            Vezi toate
          </a>
        </div>
        <ServiceGrid
          services={services.map((s) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            priceLabel: `De la ${s.base_price} MDL (${s.price_type})`,
            category: s.category?.name || "Serviciu",
          }))}
          isLoading={isLoading}
        />
      </section>

      <section className="space-y-4 rounded-3xl bg-white/80 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-primary">Cei mai buni în oraș</div>
            <h2 className="text-3xl font-bold">Meșteri verificați</h2>
          </div>
          <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/providers">
            Vezi toți
          </a>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {(providers.length
            ? providers.map((p) => ({
                name: p.first_name || p.last_name ? `${p.first_name} ${p.last_name}`.trim() : p.username,
                rating: p.rating_avg || "—",
                reviews: p.rating_count || 0,
                city: p.city,
                tags: (p.provider_profile?.skills || []).slice(0, 2).map((s) => s.name),
              }))
            : [
                { name: "Ion Popescu", rating: "4.9", reviews: 120, tags: ["Electrică", "Smart home"] },
                { name: "Maria Rusu", rating: "4.8", reviews: 98, tags: ["Curățenie", "Dezinfectare"] },
                { name: "Alexei Cojocaru", rating: "4.7", reviews: 88, tags: ["Mobilă", "Montaj"] },
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
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                      Verified
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
                <a className="flex-1 rounded-xl bg-primary px-3 py-2 text-center text-white" href="/chat/">
                  Scrie
                </a>
                <a className="flex-1 rounded-xl border border-primary px-3 py-2 text-center text-primary" href="/accounts/provider">
                  Profil
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      <ScrollScene>
        <section className="space-y-3 rounded-3xl bg-white/70 p-8 shadow-glow">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-primary">3 pași simpli</div>
              <h2 className="text-3xl font-bold">Cum funcționează</h2>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { title: "Descrie task-ul", desc: "Scrii ce ai nevoie, atașezi foto/video." },
              { title: "Alegi meșterul", desc: "Vezi rating 4+, distanță și răspuns rapid." },
              { title: "Plătești și lași review", desc: "Plată online, chat și recenzie bidirecțională." },
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

"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { LottiePulse } from "./LottiePulse";
import { useI18n } from "@/app/i18n/useI18n";
import { useReducedMotion } from "@/hooks/useReducedMotion";

gsap.registerPlugin(ScrollTrigger);

const variants = {
  container: {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } },
  },
  item: {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
  },
};

export function Hero() {
  const ref = useRef<HTMLDivElement | null>(null);
  const t = useI18n("ro");
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) return;
    const el = ref.current;
    if (!el) return;
    const tween = gsap.to(el, {
      yPercent: -8,
      ease: "none",
      scrollTrigger: {
        trigger: el,
        start: "top top",
        end: "bottom top",
        scrub: true,
      },
    });
    return () => tween.scrollTrigger?.kill();
  }, [prefersReducedMotion]);

  return (
    <motion.section
      ref={ref}
      className="relative overflow-hidden rounded-3xl bg-white/80 p-8 shadow-glow hero-pattern md:p-12"
      variants={prefersReducedMotion ? undefined : variants.container}
      initial={prefersReducedMotion ? undefined : "hidden"}
      animate={prefersReducedMotion ? undefined : "show"}
    >
      <motion.div className="flex flex-col gap-6 md:flex-row md:items-center">
        <motion.div className="flex-1 space-y-4" variants={prefersReducedMotion ? undefined : variants.item}>
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
            <LottiePulse /> {t("hero.badge")}
          </div>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">{t("hero.title")}</h1>
          <p className="text-slate-600 md:text-lg">{t("hero.subtitle")}</p>
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white/70 p-3 shadow-sm md:flex-row md:items-center">
            <label className="sr-only" htmlFor="need">
              {t("hero.input.need")}
            </label>
            <input
              id="need"
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base focus:border-primary focus:outline-none"
              placeholder={t("hero.input.need")}
              aria-label={t("hero.input.need")}
            />
            <label className="sr-only" htmlFor="city">
              {t("hero.input.city")}
            </label>
            <input
              id="city"
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base focus:border-primary focus:outline-none"
              placeholder={t("hero.input.city")}
              aria-label={t("hero.input.city")}
            />
            <motion.a
              whileHover={{ y: -2, scale: 1.01 }}
              className="flex w-full items-center justify-center rounded-xl bg-primary px-5 py-3 text-white shadow-lg focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary md:w-auto"
              href="/bookings/new/"
              aria-label={t("hero.cta")}
            >
              {t("hero.cta")}
            </motion.a>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            {[t("hero.pill.urgent"), t("hero.pill.rating"), t("hero.pill.nearby")].map((pill) => (
              <span
                key={pill}
                className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-slate-700 shadow-sm"
              >
                {pill}
              </span>
            ))}
          </div>
        </motion.div>
        <motion.div
          className="relative flex-1 rounded-2xl bg-surface text-white p-6 glass"
          variants={prefersReducedMotion ? undefined : variants.item}
          layoutId="hero-card"
        >
          <div className="text-sm text-white/70">Rezervare rapidă</div>
          <div className="mt-2 text-xl font-semibold">Montaj mobilier</div>
          <div className="mt-3 space-y-2 text-sm text-white/80">
            <div className="flex items-center justify-between rounded-xl bg-white/10 px-3 py-2">
              <span>Data</span> <span>12 Mar, 14:00</span>
            </div>
            <div className="flex items-center justify-between rounded-xl bg-white/10 px-3 py-2">
              <span>Prestator</span> <span>Ion Popescu</span>
            </div>
            <div className="flex items-center justify-between rounded-xl bg-white/10 px-3 py-2">
              <span>Tip</span> <span>Ajutor voluntar</span>
            </div>
          </div>
          {!prefersReducedMotion && (
            <>
              <motion.div
                className="absolute -right-10 bottom-0 hidden h-40 w-40 md:block"
                initial={{ x: 60, rotate: 10, opacity: 0 }}
                animate={{ x: 0, rotate: 0, opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.8, ease: "easeOut" }}
              >
                <Image src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f528.svg" alt="hammer" fill />
              </motion.div>

              <motion.div
                className="absolute -top-6 -left-4 rounded-2xl bg-white/80 px-3 py-2 text-sm font-semibold text-primary shadow-lg"
                initial={{ y: -10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                +24 meșteri online
              </motion.div>
              <motion.div
                className="absolute top-10 -right-6 rounded-2xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white shadow-lg"
                initial={{ x: 10, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.45 }}
              >
                Urgent preluat
              </motion.div>
              <motion.div
                className="absolute bottom-10 -left-6 rounded-full bg-white/90 px-3 py-2 text-sm font-semibold text-slate-900 shadow-lg"
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.6 }}
              >
                4.9 ★
              </motion.div>
            </>
          )}
        </motion.div>
      </motion.div>
    </motion.section>
  );
}

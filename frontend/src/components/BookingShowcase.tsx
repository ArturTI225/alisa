"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { StatusBadge, StatusTimeline } from "@/components/StatusBadge";
import { useI18n } from "@/app/i18n/useI18n";
import { formatDateTime, formatPlural } from "@/utils/format";

type BookingCard = {
  id: string;
  title: string;
  status: "open" | "in_review" | "matched" | "in_progress" | "done" | "cancelled";
  when: string;
  provider: string;
};

const sampleBookings: BookingCard[] = [
  { id: "101", title: "Montaj TV + cablare", status: "open", when: "2025-03-12T14:00:00Z", provider: "Ion P." },
  { id: "102", title: "Robinet reparat", status: "in_progress", when: "2025-03-13T10:00:00Z", provider: "Alina S." },
  { id: "103", title: "Prize suplimentare", status: "matched", when: "2025-03-13T16:30:00Z", provider: "Mihai D." },
];

export function BookingShowcase() {
  const [selected, setSelected] = useState<BookingCard | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const t = useI18n("ro");

  const bookings = sampleBookings; // replace with API data when available

  useEffect(() => {
    if (selected && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [selected]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-primary">{t("bookings.heading")}</div>
          <h2 className="text-2xl font-bold">{t("bookings.timeline")}</h2>
          <p className="text-sm text-slate-600">
            {formatPlural(bookings.length, {
              one: "comandă",
              few: "comenzi",
              other: "de comenzi",
            })}
          </p>
        </div>
        <a
          className="rounded-xl border border-primary/40 px-4 py-2 text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          href="/bookings/"
        >
          {t("bookings.dashboard")}
        </a>
      </div>
      {bookings.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-600">
          {t("bookings.empty")}{" "}
          <a className="font-semibold text-primary" href="/bookings/new/">
            {t("bookings.create")}
          </a>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {bookings.map((b) => (
          <motion.button
            key={b.id}
            layoutId={`booking-${b.id}`}
            className="glass flex flex-col items-start rounded-2xl p-4 text-left shadow-lg"
            onClick={() => setSelected(b)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setSelected(b);
              }
            }}
            whileHover={prefersReducedMotion ? undefined : { y: -2 }}
            tabIndex={0}
            aria-label={`Deschide detalii pentru ${b.title}`}
          >
            <StatusBadge status={b.status} />
            <h3 className="text-lg font-semibold">{b.title}</h3>
            <p className="text-sm text-slate-500">{formatDateTime(b.when)}</p>
            <div className="mt-2 text-sm font-semibold text-primary">{t("bookings.volunteerHelp")}</div>
          </motion.button>
        ))}
      </div>
      )}

      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            initial={prefersReducedMotion ? false : { opacity: 0 }}
            animate={prefersReducedMotion ? false : { opacity: 1 }}
            exit={prefersReducedMotion ? false : { opacity: 0 }}
            onClick={() => setSelected(null)}
            role="dialog"
            aria-modal="true"
            aria-label="Detalii comandă"
          >
            <motion.div
              layoutId={`booking-${selected.id}`}
              className="max-w-lg rounded-3xl bg-white p-6 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
              initial={prefersReducedMotion ? false : { scale: 0.98, opacity: 0 }}
              animate={prefersReducedMotion ? false : { scale: 1, opacity: 1 }}
              exit={prefersReducedMotion ? false : { scale: 0.98, opacity: 0 }}
            >
              <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                <StatusBadge status={selected.status} />
              </div>
              <h3 className="text-2xl font-bold">{selected.title}</h3>
              <p className="text-sm text-slate-500">{formatDateTime(selected.when)}</p>
              <p className="mt-2 text-sm text-slate-600">Prestator: {selected.provider}</p>
              <StatusTimeline current={selected.status} />
              <div className="mt-3 flex items-center justify-between text-sm font-semibold text-primary">
                <span>{t("bookings.volunteerHelp")}</span>
                <a
                  className="rounded-lg bg-primary/10 px-3 py-2 text-primary hover:bg-primary/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                  href={`/bookings/${selected.id}/`}
                >
                  {t("bookings.details")}
                </a>
              </div>
              <button
                ref={closeButtonRef}
                className="mt-4 rounded-xl bg-slate-100 px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                onClick={() => setSelected(null)}
              >
                {t("bookings.close")}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

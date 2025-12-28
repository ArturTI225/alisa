"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

type BookingCard = {
  id: string;
  title: string;
  status: string;
  when: string;
  provider: string;
  price: string;
};

const sampleBookings: BookingCard[] = [
  { id: "101", title: "Montaj TV + cablare", status: "In asteptare", when: "12 Mar, 14:00", provider: "Ion P.", price: "220 RON" },
  { id: "102", title: "Chiuveta curge", status: "Confirmata", when: "13 Mar, 10:00", provider: "Alina S.", price: "180 RON" },
  { id: "103", title: "Prize suplimentare", status: "In curs", when: "13 Mar, 16:30", provider: "Mihai D.", price: "250 RON" },
];

export function BookingShowcase() {
  const [selected, setSelected] = useState<BookingCard | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-primary">Comenzile tale</div>
          <h2 className="text-2xl font-bold">Timeline real-time</h2>
        </div>
        <a className="rounded-xl border border-primary/40 px-4 py-2 text-primary" href="/bookings/">
          Deschide dashboard
        </a>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {sampleBookings.map((b) => (
          <motion.button
            key={b.id}
            layoutId={`booking-${b.id}`}
            className="glass flex flex-col items-start rounded-2xl p-4 text-left shadow-lg"
            onClick={() => setSelected(b)}
            whileHover={{ y: -2 }}
          >
            <div className="text-xs font-semibold text-primary">{b.status}</div>
            <h3 className="text-lg font-semibold">{b.title}</h3>
            <p className="text-sm text-slate-500">{b.when}</p>
            <div className="mt-2 text-sm font-semibold text-primary">{b.price}</div>
          </motion.button>
        ))}
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelected(null)}
          >
            <motion.div
              layoutId={`booking-${selected.id}`}
              className="max-w-lg rounded-3xl bg-white p-6 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-xs font-semibold text-primary">{selected.status}</div>
              <h3 className="text-2xl font-bold">{selected.title}</h3>
              <p className="text-sm text-slate-500">{selected.when}</p>
              <p className="mt-2 text-sm text-slate-600">Prestator: {selected.provider}</p>
              <div className="mt-3 flex items-center justify-between text-sm font-semibold text-primary">
                <span>{selected.price}</span>
                <a className="rounded-lg bg-primary/10 px-3 py-2 text-primary hover:bg-primary/20" href={`/bookings/${selected.id}/`}>
                  Detalii
                </a>
              </div>
              <button className="mt-4 rounded-xl bg-slate-100 px-4 py-2 text-sm" onClick={() => setSelected(null)}>
                Închide
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

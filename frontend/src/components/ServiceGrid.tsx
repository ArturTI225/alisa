import { motion } from "framer-motion";
import { useReducedMotion } from "@/hooks/useReducedMotion";

type Props = {
  services: {
    id: number | string;
    name: string;
    description: string;
    infoLabel: string;
    category: string;
  }[];
  isLoading?: boolean;
  error?: string;
};

export function ServiceGrid({ services, isLoading, error }: Props) {
  const prefersReducedMotion = useReducedMotion();

  if (error) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Nu am putut încărca serviciile. Încearcă din nou sau vizitează{" "}
        <a className="font-semibold text-primary underline" href="/services/">
          pagina serviciilor
        </a>
        .
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, idx) => (
          <div key={idx} className="glass h-40 animate-pulse rounded-2xl bg-white/60" />
        ))}
      </div>
    );
  }
  if (!services.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-slate-600">
        Nu există servicii de afișat acum. <a className="font-semibold text-primary" href="/services/">Vezi categoriile</a>.
      </div>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {services.map((service, idx) => (
        <motion.div
          key={service.id}
          className="glass rounded-2xl p-5 shadow-lg"
          initial={prefersReducedMotion ? false : { opacity: 0, y: 10 }}
          animate={prefersReducedMotion ? false : { opacity: 1, y: 0 }}
          transition={{ delay: prefersReducedMotion ? 0 : idx * 0.05, duration: 0.35 }}
        >
          <div className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">{service.category}</div>
          <h3 className="mt-2 text-lg font-semibold">{service.name}</h3>
          <p className="text-sm text-slate-500">{service.description}</p>
          <div className="mt-3 flex items-center justify-between text-sm font-semibold text-primary">
            <span>{service.infoLabel}</span>
            <a className="rounded-lg bg-primary/10 px-3 py-2 text-primary hover:bg-primary/20" href="/bookings/new/">
              Solicită ajutor
            </a>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

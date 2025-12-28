import { motion } from "framer-motion";

type Props = {
  services: {
    id: number | string;
    name: string;
    description: string;
    priceLabel: string;
    category: string;
  }[];
  isLoading?: boolean;
};

export function ServiceGrid({ services, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, idx) => (
          <div key={idx} className="glass h-40 animate-pulse rounded-2xl bg-white/60" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {services.map((service, idx) => (
        <motion.div
          key={service.id}
          className="glass rounded-2xl p-5 shadow-lg"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.05, duration: 0.35 }}
        >
          <div className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">{service.category}</div>
          <h3 className="mt-2 text-lg font-semibold">{service.name}</h3>
          <p className="text-sm text-slate-500">{service.description}</p>
          <div className="mt-3 flex items-center justify-between text-sm font-semibold text-primary">
            <span>{service.priceLabel}</span>
            <a className="rounded-lg bg-primary/10 px-3 py-2 text-primary hover:bg-primary/20" href="/bookings/new/">
              Rezervă
            </a>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

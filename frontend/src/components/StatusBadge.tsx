type Status =
  | "open"
  | "in_review"
  | "matched"
  | "in_progress"
  | "done"
  | "cancelled";

const statusMeta: Record<
  Status,
  { label: string; description: string; className: string }
> = {
  open: {
    label: "Deschis",
    description: "Vizibil voluntarilor; se pot trimite aplicații.",
    className: "bg-blue-100 text-blue-800",
  },
  in_review: {
    label: "În review",
    description: "Moderare de către admin; vizibilitatea poate fi limitată.",
    className: "bg-amber-100 text-amber-800",
  },
  matched: {
    label: "Atribuit",
    description: "Voluntar acceptat; se poate începe lucrul.",
    className: "bg-indigo-100 text-indigo-800",
  },
  in_progress: {
    label: "În curs",
    description: "Lucrarea este în desfășurare; folosiți chatul pentru coordonare.",
    className: "bg-emerald-100 text-emerald-800",
  },
  done: {
    label: "Finalizat",
    description: "Lucrarea a fost confirmată; disponibil certificat și recenzie.",
    className: "bg-green-100 text-green-800",
  },
  cancelled: {
    label: "Anulat",
    description: "Cererea a fost oprită cu motiv înregistrat.",
    className: "bg-slate-100 text-slate-700",
  },
};

export function StatusBadge({ status }: { status: Status }) {
  const meta = statusMeta[status];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${meta.className}`}
      aria-label={`${meta.label} – ${meta.description}`}
      title={meta.description}
    >
      <span className="h-2 w-2 rounded-full bg-current opacity-70" />
      {meta.label}
    </span>
  );
}

export function StatusTimeline({ current }: { current: Status }) {
  const order: Status[] = ["open", "in_review", "matched", "in_progress", "done", "cancelled"];
  return (
    <ol className="mt-4 flex flex-wrap gap-3" aria-label="Stări cerere">
      {order.map((s) => {
        const meta = statusMeta[s];
        const isCurrent = s === current;
        const isPassed = order.indexOf(s) < order.indexOf(current) && current !== "cancelled";
        const dotColor = isCurrent || isPassed ? "bg-primary" : "bg-slate-300";
        const textColor = isCurrent ? "text-primary" : "text-slate-600";
        return (
          <li key={s} className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} aria-hidden />
            <span className={`text-xs font-semibold ${textColor}`}>{meta.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

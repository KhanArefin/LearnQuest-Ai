/** Shared UI kit. OWNER: Member 2. Everyone imports these - plan.md 4.5. */

/** A 1px-bordered surface. Depth comes from the border, not a shadow. */
export default function Card({ className = '', interactive = false, children, ...props }) {
  return (
    <div
      className={`card ${interactive ? 'row-interactive cursor-pointer' : ''} p-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-4 border-b border-line pb-3 dark:border-[#242B35]">
      <div className="min-w-0">
        <h3 className="text-base font-semibold leading-tight">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/** Consistent page title block. OWNER: Member 2. */
export default function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-line pb-4 dark:border-[#242B35]">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-ink dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>}
    </div>
  );
}

/** Shared UI kit. OWNER: Member 2. Everyone imports these - plan.md 4.5. */

export default function Tabs({
  tabs = [],
  activeTab,
  onChange,
  variant = 'underline',
  className = '',
}) {
  if (variant === 'pills') {
    return (
      <div
        role="tablist"
        className={`inline-flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800/80 ${className}`}
      >
        {tabs.map((tab) => {
          const id = tab.id ?? tab.value;
          const label = tab.label ?? tab.title ?? id;
          const isActive = id === activeTab;
          return (
            <button
              key={id}
              role="tab"
              type="button"
              aria-selected={isActive}
              onClick={() => onChange?.(id)}
              className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {tab.icon && <span>{tab.icon}</span>}
              <span>{label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300'
                      : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Default: 'underline' variant
  return (
    <div
      role="tablist"
      className={`flex border-b border-slate-200 dark:border-slate-800 ${className}`}
    >
      {tabs.map((tab) => {
        const id = tab.id ?? tab.value;
        const label = tab.label ?? tab.title ?? id;
        const isActive = id === activeTab;
        return (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={isActive}
            onClick={() => onChange?.(id)}
            className={`-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? 'border-primary-600 text-primary-600 dark:border-primary-500 dark:text-primary-400'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:border-slate-700 dark:hover:text-slate-200'
            }`}
          >
            {tab.icon && <span>{tab.icon}</span>}
            <span>{label}</span>
            {tab.badge !== undefined && (
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  isActive
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Shared UI kit. OWNER: Member 2. Everyone imports these - plan.md 4.5. */

export default function Select({ label, options = [], className = '', id, children, ...props }) {
  const selectId = id || props.name;
  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={selectId}
          className="mb-1.5 block text-sm font-medium text-body dark:text-[#C6CDD6]"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {/* Native arrows differ per platform, so draw our own. */}
        <select id={selectId} className="field cursor-pointer appearance-none pr-9" {...props}>
          {children ||
            options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="none"
          className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
        >
          <path d="M6 8l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

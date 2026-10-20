type CategoryCardProps = {
  kind: 'housing' | 'wallet' | 'groceries';
  title: string;
  detail: string;
};

/** Shared editable card structure, matching the three original illustration frames. */
function IllustrationCategoryCard({kind, title, detail}: CategoryCardProps) {
  return <div className={`illustration-category illustration-category-${kind}`}>
    <span className={`illustration-category-icon illustration-category-icon-${kind}`}>
      <img src={`/assets/auth/${kind}-icon.svg`} width="18" height="18" alt="" />
    </span>
    <div className="illustration-category-copy"><p>{title}</p><span>{detail}</span></div>
  </div>;
}

/** Figma's 64px annulus: inner radius 78%, clockwise from -90° to 180°. */
function IllustrationProgressRing() {
  const radius = 28.48;
  const circumference = 2 * Math.PI * radius;
  return <div className="illustration-progress-ring" aria-label="Savings progress: 75%">
    <svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
      <circle cx="32" cy="32" r={radius} fill="none" stroke="#FFF0E8" strokeWidth="7.04" />
      <circle cx="32" cy="32" r={radius} fill="none" stroke="#F9733B" strokeWidth="7.04"
        strokeDasharray={`${circumference * .75} ${circumference * .25}`} transform="rotate(-90 32 32)" />
    </svg>
    <span aria-hidden="true">75%</span>
  </div>;
}

/** Original Figma illustration (2001:5234), composed of live text, CSS and original SVGs. */
export function AuthFinancialIllustration() {
  return <section className="financial-illustration" aria-label="Illustrative financial summary">
    <div className="illustration-back-card" aria-hidden="true" />
    <div className="illustration-savings-card">
      <p className="illustration-savings-label">Monthly savings</p>
      <p className="illustration-savings-value">৳8,450</p>
      <span className="illustration-savings-delta">▲ +12.8% this month</span>
      <img className="illustration-savings-chart" src="/assets/auth/savings-chart.svg" width="324" height="96" alt="Illustrative savings trend" />
      <IllustrationProgressRing />
    </div>
    <IllustrationCategoryCard kind="housing" title="Housing" detail="On track" />
    <IllustrationCategoryCard kind="wallet" title="Emergency fund" detail="৳32,000 goal" />
    <IllustrationCategoryCard kind="groceries" title="Groceries" detail="−৳420 vs. last month" />
    <p className="illustration-disclaimer">Illustrative demo values — not real financial data.</p>
  </section>;
}

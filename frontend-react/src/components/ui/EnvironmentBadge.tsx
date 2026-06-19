import type { DataSourceMode } from "../../config/dataSource";

interface EnvironmentBadgeProps {
  mode: DataSourceMode;
  label: string;
  detail?: string;
}

export function EnvironmentBadge({ mode, label, detail }: EnvironmentBadgeProps) {
  const isLive = mode === "live";
  const badgeClass = isLive ? "env-badge env-badge--live" : "env-badge env-badge--mock";
  const modeText = isLive ? "Live Data" : "Mock Data";

  return (
    <div className="env-badge-wrap">
      <span
        className={badgeClass}
        aria-live="polite"
        title={detail ?? label}
      >
        {modeText}
      </span>
      <span className="env-badge-detail">
        {label}
        {detail ? (
          <>
            {" · "}
            <code>{detail}</code>
          </>
        ) : null}
      </span>
    </div>
  );
}

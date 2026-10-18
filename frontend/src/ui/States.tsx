// Skeletons, empty and error states: every state is designed, none is a raw message.
import type { CSSProperties, ReactNode } from "react";
import "./States.css";

export function Skeleton({
  width,
  height = 12,
  radius = 8,
  style,
}: {
  width?: number | string;
  height?: number;
  radius?: number;
  style?: CSSProperties;
}) {
  return (
    <span
      className="skeleton"
      aria-hidden="true"
      style={{ width: width ?? "100%", height, borderRadius: radius, ...style }}
    />
  );
}

export function SkeletonLines({ lines = 3, gap = 8 }: { lines?: number; gap?: number }) {
  return (
    <span className="skeleton-lines" style={{ gap }} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} width={i === lines - 1 ? "62%" : "100%"} />
      ))}
    </span>
  );
}

/** Screen readers hear one calm line while the skeleton shimmers. */
export function LoadingRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-live="polite" className="loading-region">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

interface StateProps {
  icon?: ReactNode;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ icon, title, children, action, compact }: StateProps) {
  return (
    <div className={`state${compact ? " state--compact" : ""}`}>
      {icon && <span className="state__icon">{icon}</span>}
      <p className="state__title">{title}</p>
      {children && <div className="state__body">{children}</div>}
      {action && <div className="state__action">{action}</div>}
    </div>
  );
}

export function ErrorState({ icon, title, children, action, compact }: StateProps) {
  return (
    <div className={`state state--error${compact ? " state--compact" : ""}`} role="alert">
      {icon && <span className="state__icon">{icon}</span>}
      <p className="state__title">{title}</p>
      {children && <div className="state__body">{children}</div>}
      {action && <div className="state__action">{action}</div>}
    </div>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="kbd">{children}</kbd>;
}

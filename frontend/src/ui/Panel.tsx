import { Children, Fragment, type ReactNode } from "react";
import "./Panel.css";

interface PanelProps {
  title?: ReactNode;
  icon?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Content runs edge to edge (tables, lists with their own padding). */
  flush?: boolean;
  labelledBy?: string;
}

export function Panel({
  title,
  icon,
  meta,
  actions,
  children,
  className,
  flush,
  labelledBy,
}: PanelProps) {
  return (
    <section
      className={`panel${flush ? " panel--flush" : ""}${className ? ` ${className}` : ""}`}
      aria-labelledby={labelledBy}
    >
      {(title || actions) && (
        <header className="panel__header">
          <h2 className="panel__title" id={labelledBy}>
            {icon}
            {title}
          </h2>
          {meta && <span className="panel__meta">{meta}</span>}
          {actions && <div className="panel__actions">{actions}</div>}
        </header>
      )}
      <div className="panel__body">{children}</div>
    </section>
  );
}

interface PageHeaderProps {
  overline?: ReactNode;
  title: ReactNode;
  /** A mono meta line under the title; direct children are separated by dots. */
  meta?: ReactNode;
  explainer?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ overline, title, meta, explainer, actions }: PageHeaderProps) {
  const metaItems = Children.toArray(meta);
  return (
    <header className="page-header">
      <div className="page-header__text">
        {overline && <p className="overline">{overline}</p>}
        <h1 className="page-header__title">{title}</h1>
        {metaItems.length > 0 && (
          <p className="page-header__meta">
            {metaItems.map((item, i) => (
              <Fragment key={i}>
                {i > 0 && <span className="sep-dot" aria-hidden="true" />}
                {item}
              </Fragment>
            ))}
          </p>
        )}
        {explainer && <p className="page-header__explainer">{explainer}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

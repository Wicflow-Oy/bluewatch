import type { ReactNode } from "react";
import type { GuideSection, GuideTable } from "./content";

interface SectionFrameProps {
  id: string;
  title: string;
  /** The section's place on the page, shown as a small "01" above the title. */
  index?: number;
  children: ReactNode;
}

/** One part of the page the table of contents can jump to. The heading takes focus after a jump. */
export function SectionFrame({ id, title, index, children }: SectionFrameProps) {
  const headingId = `${id}-title`;
  return (
    <section id={id} className="guide-section" aria-labelledby={headingId}>
      {index !== undefined && (
        <span className="guide-section__num mono" aria-hidden="true">
          {String(index + 1).padStart(2, "0")}
        </span>
      )}
      <h3 id={headingId} className="guide-section__title" tabIndex={-1}>
        {title}
      </h3>
      {children}
    </section>
  );
}

/** A section reads as its paragraphs, then its points, then its table. */
export function Section({ section, index }: { section: GuideSection; index: number }) {
  return (
    <SectionFrame id={section.id} title={section.title} index={index}>
      {section.body.map((paragraph, i) => (
        <p key={i} className="guide-text">
          {paragraph}
        </p>
      ))}
      {section.points && (
        <ul className="guide-points">
          {section.points.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
      )}
      {section.table && <Table table={section.table} />}
    </SectionFrame>
  );
}

/** The first column names each row. On a phone every row becomes a card, so cells carry their header. */
function Table({ table }: { table: GuideTable }) {
  return (
    <div className="guide-table inset">
      <table>
        <thead>
          <tr>
            {table.head.map((label, i) => (
              <th key={i} scope="col">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map(([name, ...cells], r) => (
            <tr key={r}>
              <th scope="row">{name}</th>
              {cells.map((cell, c) => (
                <td key={c} data-label={table.head[c + 1]}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

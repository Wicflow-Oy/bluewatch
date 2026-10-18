// The table's shape while the companies load: the heading, the filter bar and 12 placeholder rows.
import { useT } from "../../i18n/messages";
import { LoadingRegion, Skeleton } from "../../ui/States";
import { companiesMessages } from "./messages";

export function CompanyTableSkeleton() {
  const { t } = useT(companiesMessages);
  return (
    <LoadingRegion label={t("loadingCompanies")}>
      <section className="company-table" aria-hidden="true">
        <header className="company-table__head">
          <h2 className="company-table__title">{t("tableTitle")}</h2>
        </header>
        <div className="filters">
          <Skeleton width={320} height={36} radius={999} />
          <Skeleton width={96} height={30} radius={999} />
          <Skeleton width={84} height={30} radius={999} />
        </div>
        <ul className="company-table__skeleton sheet">
          {Array.from({ length: 12 }, (_, i) => (
            <li key={i}>
              <Skeleton width={16} height={10} />
              <Skeleton width={180} height={12} />
              <Skeleton height={12} />
            </li>
          ))}
        </ul>
      </section>
    </LoadingRegion>
  );
}

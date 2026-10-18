import { useT } from "../../i18n/messages";
import { Chip } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import type { DateMeaning } from "./dateMeaning";
import { bridgesMessages } from "./messages";

interface ConnectorProps {
  label: string;
  date: string | null | undefined;
  meaning: DateMeaning;
  today: string;
}

/** The violet line between the two sides, carrying the bridge type and its date. */
export function Connector({ label, date, meaning, today }: ConnectorProps) {
  const { t } = useT(bridgesMessages);
  return (
    <div className="bridge-link">
      <span className="bridge-link__node bridge-link__node--start" aria-hidden="true" />
      <span className="bridge-link__node bridge-link__node--end" aria-hidden="true" />
      <span className="bridge-link__type">
        <Chip tone="violet" wrap>
          {label}
        </Chip>
      </span>
      <span className="bridge-link__when">
        {date ? (
          <>
            <Deadline date={date} today={today} size="lg" />
            <span className="bridge-link__caption">{t(`when_${meaning}`)}</span>
          </>
        ) : (
          <span className="bridge-link__caption">{t("noDate")}</span>
        )}
      </span>
    </div>
  );
}

import type { Resolution } from "../contracts";
import { useT } from "../i18n/messages";
import { Chip, type Tone } from "./Chip";
import { resolutionChipMessages } from "./ResolutionChip.messages";
import { Tooltip } from "./Tooltip";
import "./ResolutionChip.css";

const TONES: Record<Resolution["state"], Tone> = {
  resolved: "teal",
  probable: "outline",
  ambiguous: "amber",
  unconfirmed: "amber",
  unresolved: "hatch",
};

/** How sure we are that the company is the register record we show; the reason is one hover away. */
export function ResolutionChip({ resolution }: { resolution: Resolution }) {
  const { t } = useT(resolutionChipMessages);
  const label = t(`state_${resolution.state}`);
  return (
    <Tooltip
      content={
        <>
          <div className="tooltip__title">{label}</div>
          <p className="muted">{resolution.reason}</p>
        </>
      }
    >
      <span className="resolution-chip" tabIndex={0}>
        <Chip tone={TONES[resolution.state]} dot={resolution.state !== "unresolved"}>
          {label}
        </Chip>
        <span className="sr-only">{`: ${resolution.reason}`}</span>
      </span>
    </Tooltip>
  );
}

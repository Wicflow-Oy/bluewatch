// "Top N to review this week": one capsule per place, and an empty slot stays empty (never padded).
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { href } from "../../lib/router";
import { ideasMessages } from "./messages";
import { IdeaTierChip, OriginChip } from "./read/chips";
import { readMessages } from "./read/messages";
import { SampleChip } from "./SampleData";
import type { IdeaQueue } from "./types";

// The API's sentence names the next idea by its rank only ("Next in line: #6 (…)"): a team's own title has no
// translation, so the list puts the title beside it.
const RANK = /#(\d+)/;

export function TopSlots({ queue, sample }: { queue: IdeaQueue; sample: boolean }) {
  const { t } = useT(ideasMessages);
  const read = useT(readMessages);
  const slots = Array.from({ length: queue.top_n }, (_, i) =>
    queue.items.find((item) => item.id === queue.top_ids[i]),
  );
  return (
    <section className="ih-top" aria-labelledby="ih-top-title">
      <h2 className="ih-section-title" id="ih-top-title">
        {t("topTitle", { n: queue.top_n })}
      </h2>
      <ol className="ih-slots" data-count={queue.top_n}>
        {slots.map((item, i) =>
          item ? (
            <li key={item.id} className="stagger-in" style={vars({ "--i": i })}>
              <a
                className="ih-slot capsule capsule--interactive"
                href={href({ name: "ideas", itemId: item.id })}
              >
                <span className="ih-slot__rank mono">#{item.rank}</span>
                <span className="ih-slot__title">{item.assessment.title}</span>
                <span className="ih-slot__chips">
                  {/* A slot is narrow: the short tier word, the full one is in the list below. */}
                  <IdeaTierChip
                    tier={item.assessment.tier}
                    label={read.t(`tierShort_${item.assessment.tier}`)}
                  />
                  {sample && <SampleChip />}
                  <OriginChip kind={item.origin.kind} />
                </span>
              </a>
            </li>
          ) : (
            <li
              key={`empty-${i}`}
              className="ih-slot ih-slot--empty hatch-frame stagger-in"
              style={vars({ "--i": i })}
            >
              {t("emptySlot")}
            </li>
          ),
        )}
      </ol>
      <div className="ih-top__notes">
        <p className="ih-top__why">{queue.why_these}</p>
        {queue.why_not_next && <NextInLine queue={queue} sentence={queue.why_not_next} />}
      </div>
    </section>
  );
}

function NextInLine({ queue, sentence }: { queue: IdeaQueue; sentence: string }) {
  const rank = Number(RANK.exec(sentence)?.[1]);
  const item = queue.items.find((i) => i.rank === rank);
  return (
    <p className="ih-top__next">
      {sentence}
      {item && (
        <a className="ih-top__next-title" href={href({ name: "ideas", itemId: item.id })}>
          {item.assessment.title}
        </a>
      )}
    </p>
  );
}

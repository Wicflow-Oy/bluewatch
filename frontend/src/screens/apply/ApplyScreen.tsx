// The student page an A'Pelago invitation opens (#/apply): describe the idea, get an honest readiness
// read at once, and decide whether to share it. It stands outside the app shell and always wears
// A'Pelago's workspace dot. Answers live in this component's state only.
import { RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { getLang, useLang, type Lang } from "../../i18n/lang";
import { useT } from "../../i18n/messages";
import { Panel } from "../../ui/Panel";
import { ErrorState } from "../../ui/States";
import { Toggle } from "../../ui/Toggle";
import { ideasApi } from "../ideas/api";
import { PHONE, useMedia } from "../ideas/read/hooks";
import type { IdeaAssessment, IdeaSubmission, PresetName } from "../ideas/types";
import { ApplyFooter, ApplyHeader } from "./ApplyChrome";
import { AnswerForm, AnswerFormSkeleton } from "./AnswerForm";
import {
  clientErrors,
  EMPTY_DRAFT,
  stillShown,
  toSubmission,
  type Draft,
  type FieldErrors,
} from "./draft";
import { explain, type Banner } from "./errors";
import { Intro } from "./Intro";
import { useMessageText } from "./message";
import { applyMessages } from "./messages";
import { ReadResult, ReadSkeleton, WhatYoullGet } from "./ReadResult";
import { EarlierShare, SharePanel, Spinner } from "./SharePanel";
import { useIdeaForm } from "./useIdeaForm";
import { useSharing } from "./useSharing";
import "../ideas/read/read.css";
import "./apply.css";

type Read =
  | { status: "idle" }
  | { status: "reading" }
  | {
      status: "done";
      assessment: IdeaAssessment;
      submission: IdeaSubmission;
      aiRead: boolean;
      lang: Lang;
    };

/** On a phone the read replaces the form; wider screens show both. */
type PhoneView = "form" | "result";

const PAGE_TITLE = "Idea Harbour · A'Pelago";

function smooth(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

export function ApplyScreen({ preset }: { preset: PresetName }) {
  const { t } = useT(applyMessages);
  const say = useMessageText();
  const lang = useLang();
  const phone = useMedia(PHONE);
  const { form, failed, reload } = useIdeaForm(preset);

  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [aiRead, setAiRead] = useState(true);
  const [checked, setChecked] = useState<{ errors: FieldErrors; draft: Draft }>({
    errors: {},
    draft: EMPTY_DRAFT,
  });
  const [banner, setBanner] = useState<Banner | null>(null);
  const [read, setRead] = useState<Read>({ status: "idle" });
  const [view, setView] = useState<PhoneView>("form");
  const sharing = useSharing(aiRead, reload);

  const formRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const bannerRef = useRef<HTMLDivElement>(null);
  const revealPending = useRef(false);

  // The invitation is A'Pelago's, whichever workspace this browser last used in the app. Before
  // paint, so a visitor coming from the Redstone workspace never sees a red flash.
  useLayoutEffect(() => {
    document.documentElement.dataset.workspace = "apelago";
    const before = document.title;
    document.title = PAGE_TITLE;
    return () => {
      document.title = before;
    };
  }, []);

  // A fresh read is announced and brought into view once it has rendered.
  useEffect(() => {
    if (!revealPending.current || read.status !== "done") return;
    revealPending.current = false;
    if (phone) window.scrollTo({ top: 0 });
    else resultRef.current?.scrollIntoView({ block: "start", behavior: smooth() });
    headingRef.current?.focus({ preventScroll: true });
  }, [read, phone]);

  useEffect(() => {
    if (banner) bannerRef.current?.scrollIntoView({ block: "nearest", behavior: smooth() });
  }, [banner]);

  const errors = stillShown(checked.errors, checked.draft, draft);
  const draftSubmission = toSubmission(draft, preset);
  const reading = read.status === "reading";

  function showErrors(next: FieldErrors) {
    setChecked({ errors: next, draft });
    // After React has marked the fields, move to the first one that needs attention.
    requestAnimationFrame(() =>
      formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus(),
    );
  }

  async function getRead() {
    const found = clientErrors(draft);
    setBanner(null);
    if (Object.keys(found).length > 0) {
      showErrors(found);
      return;
    }
    setChecked({ errors: {}, draft });
    await vetSubmission(toSubmission(draft, preset), aiRead, { reveal: true });
  }

  /** reveal: a read the team asked for is brought into view; one asked again after a language switch is not. */
  async function vetSubmission(
    submission: IdeaSubmission,
    ai: boolean,
    { reveal }: { reveal: boolean },
  ) {
    const before = read;
    setRead({ status: "reading" });
    try {
      const assessment = await ideasApi.vet(submission, ai);
      revealPending.current = reveal;
      setRead({ status: "done", assessment, submission, aiRead: ai, lang: getLang() });
      if (reveal) {
        setView("result");
        sharing.reset();
      }
    } catch (error) {
      // A failed repeat keeps the earlier read (marked current, so it is not asked for in a loop).
      setRead(before.status === "done" ? { ...before, lang: getLang() } : before);
      const outcome = explain(error);
      if (outcome.kind === "field") showErrors({ [outcome.field]: outcome.message });
      else setBanner(outcome.banner);
    }
  }

  // The read is prose in the language it was asked in; after a language switch it is asked for again.
  const staleRead = read.status === "done" && read.lang !== lang ? read : null;
  useEffect(() => {
    if (staleRead) void vetSubmission(staleRead.submission, staleRead.aiRead, { reveal: false });
    // vetSubmission is recreated on every render; the stale read alone decides when to ask again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staleRead]);

  function clearForm() {
    setDraft(EMPTY_DRAFT);
    setChecked({ errors: {}, draft: EMPTY_DRAFT });
    setBanner(null);
  }

  function editAnswers() {
    setView("form");
    window.scrollTo({ top: 0 });
  }

  const showForm = !phone || view === "form";
  const showResult = !phone || view === "result";
  const done = read.status === "done" ? read : null;
  const shareRead = () => done && form && sharing.share(done.submission, form.consent_text_version);

  const sharePanel = (variant: "card" | "dock") =>
    done &&
    form && (
      <SharePanel
        variant={variant}
        consentText={form.consent_text}
        read={done.assessment}
        readSubmission={done.submission}
        draftSubmission={draftSubmission}
        consent={sharing.consent}
        onConsent={sharing.setConsent}
        shared={sharing.shared}
        busy={sharing.busy}
        error={sharing.error}
        onShare={shareRead}
        onWithdraw={sharing.withdraw}
      />
    );

  const toggle = form && (
    <div className="ap-ai">
      <Toggle checked={aiRead} onChange={setAiRead} label={form.ai_read_text} />
      {form.ai_read_off_note && <p className="ap-ai__off">{form.ai_read_off_note}</p>}
    </div>
  );

  // Beside the button that failed: in the flow on wider screens, in the dock on a phone.
  const bannerNote = banner && (
    <div
      ref={bannerRef}
      className={`callout ${banner.tone === "error" ? "callout--red" : "callout--amber"}`}
      role="alert"
    >
      <TriangleAlert aria-hidden="true" />
      <span>{say(banner.message)}</span>
    </div>
  );

  const readButton = (
    <button
      type="button"
      className="btn btn--primary btn--lg ap-primary"
      disabled={!form || reading}
      onClick={getRead}
    >
      {reading && <Spinner />}
      {reading ? t("reading") : t("readButton")}
    </button>
  );

  return (
    <div className="ap">
      <ApplyHeader />
      <main className="ap-main" id="main">
        <div className="ap-grid">
          {showForm && (
            <div className="ap-form-col" ref={formRef}>
              <Intro />
              {sharing.earlier && !sharing.shared && (
                <EarlierShare
                  shares={sharing.earlier}
                  busy={sharing.busy}
                  error={sharing.error}
                  onWithdraw={sharing.withdraw}
                />
              )}
              {form ? (
                <>
                  <AnswerForm
                    form={form}
                    preset={preset}
                    draft={draft}
                    errors={errors}
                    onChange={setDraft}
                  />
                  <div className="ap-submit">
                    <p className="ap-privacy">
                      <ShieldCheck size={16} strokeWidth={1.5} aria-hidden="true" />
                      {form.privacy_note}
                    </p>
                    {!phone && bannerNote}
                    {toggle}
                    <div className="ap-submit__buttons">
                      {!phone && readButton}
                      <button type="button" className="btn btn--ghost btn--lg" onClick={clearForm}>
                        {t("clearForm")}
                      </button>
                    </div>
                  </div>
                </>
              ) : failed ? (
                <Panel>
                  <ErrorState
                    icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
                    title={t("formFailed")}
                    action={
                      <button type="button" className="btn" onClick={reload}>
                        <RefreshCw size={16} strokeWidth={1.5} aria-hidden="true" />
                        {t("retry")}
                      </button>
                    }
                  />
                </Panel>
              ) : (
                <AnswerFormSkeleton />
              )}
            </div>
          )}

          {showResult && (
            <div className="ap-result-col" ref={resultRef} data-state={read.status}>
              {read.status === "idle" && <WhatYoullGet />}
              {reading && <ReadSkeleton />}
              {done && form && (
                <ReadResult
                  read={done.assessment}
                  phone={phone}
                  headingRef={headingRef}
                  onEdit={phone ? editAnswers : undefined}
                  share={!phone && sharePanel("card")}
                />
              )}
            </div>
          )}
        </div>
        <ApplyFooter />
      </main>

      {phone && form && (
        <div className="ap-dock">
          {view === "form" || !done ? (
            <>
              {bannerNote}
              {readButton}
            </>
          ) : (
            sharePanel("dock")
          )}
        </div>
      )}
    </div>
  );
}

// A partner's blind set: their own calls on a few companies, scored against ours by the API in memory.
// The file is read in the browser, sent once in the request body and never stored anywhere.
import { FileUp, LoaderCircle, ShieldCheck, Upload } from "lucide-react";
import { useId, useState, type DragEvent } from "react";
import type { PrecisionReport } from "../../contracts";
import { scoreBlindSet } from "../../data";
import { useT } from "../../i18n/messages";
import { Panel } from "../../ui/Panel";
import { ErrorState } from "../../ui/States";
import { precisionMessages, type TranslatePrecision } from "./messages";
import { contentProblem, fileProblem, type BlindProblem } from "./model";
import { Rich } from "./Rich";

type UploadState =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "refused"; problem: BlindProblem }
  /** The API refused the file and said why. */
  | { kind: "rejected"; message: string }
  | { kind: "failed" }
  | { kind: "unavailable" };

interface BlindSetProps {
  /** False when the page runs on demo data: there is no scorer without the API. */
  available: boolean;
  onResult(report: PrecisionReport): void;
}

export function BlindSet({ available, onResult }: BlindSetProps) {
  const { t } = useT(precisionMessages);
  const [upload, setUpload] = useState<UploadState>(
    available ? { kind: "idle" } : { kind: "unavailable" },
  );

  const score = async (file: File) => {
    const problem =
      fileProblem(file) ??
      contentProblem(await file.text(), file.name.toLowerCase().endsWith(".json"));
    if (problem) {
      setUpload({ kind: "refused", problem });
      return;
    }
    setUpload({ kind: "busy" });
    try {
      const outcome = await scoreBlindSet(file);
      if (outcome.kind === "result") {
        onResult(outcome.data);
        setUpload({ kind: "idle" });
      } else if (outcome.kind === "rejected") {
        setUpload({ kind: "rejected", message: outcome.message });
      } else {
        setUpload({ kind: "unavailable" });
      }
    } catch {
      setUpload({ kind: "failed" });
    }
  };

  return (
    <Panel
      title={t("blindTitle")}
      icon={<Upload size={16} strokeWidth={1.5} aria-hidden="true" />}
      className="precision__order-3"
    >
      {upload.kind === "unavailable" ? (
        <div className="precision__unavailable precision__unavailable--inline hatch-frame">
          <ErrorState compact title={t("blindUnavailableTitle")}>
            {t("blindUnavailableBody")}
          </ErrorState>
        </div>
      ) : (
        <BlindUpload busy={upload.kind === "busy"} error={errorText(upload, t)} onFile={score} />
      )}
    </Panel>
  );
}

function errorText(upload: UploadState, t: TranslatePrecision) {
  if (upload.kind === "refused") return t(`problem_${upload.problem}`);
  if (upload.kind === "rejected") return upload.message;
  if (upload.kind === "failed") return t("scoringFailed");
  return null;
}

interface BlindUploadProps {
  busy: boolean;
  error: string | null;
  onFile(file: File): void;
}

function BlindUpload({ busy, error, onFile }: BlindUploadProps) {
  const { t } = useT(precisionMessages);
  const [dragging, setDragging] = useState(false);
  const inputId = useId();
  const formatId = useId();

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !busy) onFile(file);
  };

  return (
    <div className="blind">
      {/* The whole zone is the file picker's label: click or tap anywhere, or drop a file. */}
      <label
        htmlFor={inputId}
        className={`blind__drop${dragging ? " blind__drop--over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        aria-busy={busy}
      >
        {busy ? (
          <span className="blind__prompt" role="status">
            <LoaderCircle
              className="blind__spinner"
              size={16}
              strokeWidth={1.5}
              aria-hidden="true"
            />
            {t("scoring")}
          </span>
        ) : (
          <span className="blind__prompt">
            <FileUp size={16} strokeWidth={1.5} aria-hidden="true" />
            <span>
              <Rich
                text={t("dropPrompt")}
                values={{ choose: <span className="blind__choose">{t("chooseOne")}</span> }}
              />
            </span>
          </span>
        )}
      </label>
      <input
        id={inputId}
        className="sr-only"
        type="file"
        accept=".csv,.json,text/csv,application/json"
        aria-describedby={formatId}
        disabled={busy}
        onChange={(e) => {
          const file = e.currentTarget.files?.[0];
          e.currentTarget.value = ""; // the same file can be chosen again after a fix
          if (file) onFile(file);
        }}
      />
      {error && (
        <p className="blind__error" role="alert">
          {error}
        </p>
      )}
      <p className="blind__format" id={formatId}>
        {t("blindFormat")}{" "}
        <a href={templateHref(t)} download="blind_set_template.csv">
          {t("downloadTemplate")}
        </a>
      </p>
      <p className="blind__privacy">
        <ShieldCheck size={14} strokeWidth={1.5} aria-hidden="true" />
        {t("blindPrivacy")}
      </p>
    </div>
  );
}

// Lines starting with # are skipped by the scorer (bluewatch/evals/blind.py), so the help can travel
// inside the file itself, in the reader's language; the header row stays as the scorer reads it.
function templateHref(t: TranslatePrecision): string {
  const help = [
    "templateIntro",
    "templateColumns",
    "templateLevels",
    "templateStage",
    "templateUnknown",
  ] as const;
  const text = [...help.map((key) => `# ${t(key)}`), "company,id,country,trl,brl,stage", ""].join(
    "\n",
  );
  return `data:text/csv;charset=utf-8,${encodeURIComponent(text)}`;
}

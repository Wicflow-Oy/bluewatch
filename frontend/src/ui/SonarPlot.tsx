// The Sonar: every company on the list as a blip. Distance from the centre is 1 - potential, the sector is the
// vertical, the blip grows with evidence, and Act now blips are solid while Dive deeper blips are rings. A sweep
// turns once every 8 s and pings each blip it passes. Spec: TIDEPOOL-SYSTEM.md section 4.7.
import { ShieldCheck } from "lucide-react";
import { useEffect, useId, useRef, type RefObject } from "react";
import { useT } from "../i18n/messages";
import { trunc } from "../lib/format";
import { verticalLabel, type Group, type Vertical } from "../lib/labels";
import { useMeta } from "../lib/meta";
import { prefersReducedMotion, vars } from "../lib/motion";
import { sonarMessages } from "./SonarPlot.messages";
import { Tooltip } from "./Tooltip";
import "./SonarPlot.css";

export interface SonarPoint {
  id: string;
  name: string;
  rank: number;
  potential: number;
  evidence: number;
  group: Group;
  vertical: Vertical | null;
  /** The list's filters hide its row: the blip stays, faded, and still opens the card. */
  dimmed?: boolean;
}

interface SonarPlotProps {
  points: SonarPoint[];
  /** The hot blip: a hovered row, the J/K cursor or the open card. */
  selectedId?: string;
  /** Opens the card. */
  onSelect(id: string): void;
  /** Blip hover or focus highlights its row. */
  onHover?(id: string | null): void;
  /** "mini" is the phone sheet. */
  size?: "rail" | "mini";
}

// ---- geometry (SVG units, viewBox -200 -200 400 400) ----

const R_IN = 56; // potential 1.00 sits on this ring, so top blips do not pile up on the centre
const R_OUT = 168; // the band's floor sits on this ring
const ORDER: Vertical[] = [
  "marine_intelligence",
  "maritime_ports",
  "ocean_infra_clean_energy",
  "blue_biotech_water",
  "other",
];
const SWEEP_PERIOD_MS = 8000;
// Blip centres stay this far apart (21px in the 296px rail), so no blip's 28px target covers another's centre:
// every blip can be hovered and clicked, and neighbouring rank numbers do not run together.
const MIN_GAP = 28;
// A crowded blip moves along its ring within its sector first; it may leave its exact ring by at most this much
// (under 0.05 potential on the default band), and the tooltip keeps the exact numbers.
const RING_SLACK = 10;
const SECTOR_MARGIN = 3; // degrees kept clear of each spoke

const sectorOf = (p: SonarPoint): Vertical => p.vertical ?? "other";

/** The lowest ring: 0.75, or lower when the list reaches lower (0.62 sets 0.60). */
const floorOf = (points: SonarPoint[]) =>
  Math.min(0.75, Math.floor(Math.min(...points.map((p) => p.potential)) * 20) / 20);

/** Distance from the centre = 1 - potential, scaled to the band. */
const radius = (potential: number, floor: number) =>
  R_IN + Math.min(1, Math.max(0, (1 - potential) / (1 - floor))) * (R_OUT - R_IN);

/** Clockwise from 12 o'clock. */
const polar = (r: number, deg: number): [number, number] => [
  r * Math.sin((deg * Math.PI) / 180),
  -r * Math.cos((deg * Math.PI) / 180),
];

interface Blip {
  p: SonarPoint;
  angle: number;
  x: number;
  y: number;
}

/** A blip while it is placed: its angle is unwrapped inside its sector [lo, hi], r0 is its exact ring. */
interface Placing {
  p: SonarPoint;
  deg: number;
  r: number;
  r0: number;
  lo: number;
  hi: number;
}

function layout(points: SonarPoint[]) {
  const floor = floorOf(points);
  const sectors = ORDER.filter((v) => points.some((p) => sectorOf(p) === v));
  const span = 360 / Math.max(1, sectors.length);
  const placing: Placing[] = sectors.flatMap((v, i) => {
    const from = i * span - span / 2; // the first sector is centred on 12 o'clock
    const inSector = points.filter((p) => sectorOf(p) === v).sort((a, b) => a.rank - b.rank);
    const [lo, hi] =
      sectors.length > 1
        ? [from + SECTOR_MARGIN, from + span - SECTOR_MARGIN]
        : [-Infinity, Infinity];
    return inSector.map((p, k) => {
      const r = radius(p.potential, floor);
      return { p, deg: from + ((k + 1) * span) / (inSector.length + 1), r, r0: r, lo, hi };
    });
  });
  spread(placing);
  const blips: Blip[] = placing.map(({ p, deg, r }) => {
    const [x, y] = polar(r, deg);
    return { p, angle: (deg + 360) % 360, x, y };
  });
  return { floor, sectors, span, blips };
}

/** Pushes blips closer than MIN_GAP apart: mostly along their rings, inside their sectors, and off their exact
 * ring by at most RING_SLACK. A few passes settle the ten blips of a list. */
function spread(blips: Placing[]) {
  for (let pass = 0; pass < 60; pass++) {
    let moved = false;
    for (let i = 0; i < blips.length; i++) {
      for (let j = i + 1; j < blips.length; j++) {
        const a = blips[i];
        const b = blips[j];
        const [ax, ay] = polar(a.r, a.deg);
        const [bx, by] = polar(b.r, b.deg);
        const d = Math.hypot(bx - ax, by - ay);
        if (d >= MIN_GAP) continue;
        moved = true;
        const push = (MIN_GAP - d) / 2 + 0.5;
        // Apart along the ring, in the direction they already sit (b clockwise of a, or the other way).
        const turn = Math.sign(((b.deg - a.deg + 540) % 360) - 180) || 1;
        nudge(a, -turn * push, 0);
        nudge(b, turn * push, 0);
        // Rings close together: the lower potential steps out, the higher one in.
        const outer = a.r0 > b.r0 || (a.r0 === b.r0 && a.p.rank > b.p.rank) ? a : b;
        const inner = outer === a ? b : a;
        nudge(outer, 0, push / 2);
        nudge(inner, 0, -push / 2);
      }
    }
    if (!moved) return;
  }
}

/** Moves a blip `along` units along its ring and `out` units outward, inside its sector and ring slack. */
function nudge(b: Placing, along: number, out: number) {
  const deg = b.deg + (along / b.r) * (180 / Math.PI);
  b.deg = Math.min(b.hi, Math.max(b.lo, deg));
  b.r = Math.min(b.r0 + RING_SLACK, Math.max(b.r0 - RING_SLACK, b.r + out));
}

/** 1.00 down to the floor, every 0.05 (every 0.10 when the floor is under 0.60). */
function ringValues(floor: number): number[] {
  const step = floor < 0.6 ? 10 : 5;
  const values: number[] = [];
  for (let h = 100; h >= Math.round(floor * 100); h -= step) values.push(h / 100);
  if (values[values.length - 1] !== floor) values.push(floor);
  return values;
}

const pad = (rank: number) => String(rank).padStart(2, "0");

// ---- component ----

export function SonarPlot({
  points,
  selectedId,
  onSelect,
  onHover,
  size = "rail",
}: SonarPlotProps) {
  const { t } = useT(sonarMessages);
  const meta = useMeta();
  const rootRef = useRef<HTMLDivElement>(null);
  const sweepRef = useRef<HTMLDivElement>(null);
  const { floor, sectors, span, blips } = layout(points);
  const reduced = prefersReducedMotion();
  useSweep(rootRef, sweepRef, blips);

  return (
    <figure className={`sonar-plot sonar-plot--${size}`}>
      <div className="sonar" ref={rootRef}>
        <SonarField floor={floor} sectors={sectors} span={span} />
        {!reduced && points.length > 0 && (
          <div className="sonar__sweep" ref={sweepRef} aria-hidden="true" />
        )}
        <ul className="sonar__blips" aria-label={t("sonarLabel", { n: points.length })}>
          {blips.map(({ p, angle, x, y }) => (
            <li
              key={p.id}
              className={`sonar__item${x < 0 ? " sonar__item--left" : ""}`}
              style={vars({
                "--x": `${50 + (x / 400) * 100}%`,
                "--y": `${50 + (y / 400) * 100}%`,
                "--s": `${Math.round(6 + 6 * Math.min(1, Math.max(0, p.evidence)))}px`,
              })}
            >
              <Tooltip
                content={
                  <>
                    <div className="tooltip__title mono">
                      {t("sonarScores", { p: trunc(p.potential), e: trunc(p.evidence) })}
                    </div>
                    {p.name}
                  </>
                }
              >
                <button
                  type="button"
                  className={`blip blip--${p.group}`}
                  data-id={p.id}
                  data-angle={angle.toFixed(2)}
                  data-hot={p.id === selectedId}
                  data-dimmed={p.dimmed || undefined}
                  aria-label={t("sonarBlip", {
                    rank: pad(p.rank),
                    name: p.name,
                    p: trunc(p.potential),
                    e: trunc(p.evidence),
                    group: meta.group(p.group),
                  })}
                  onClick={() => onSelect(p.id)}
                  onPointerEnter={() => onHover?.(p.id)}
                  onPointerLeave={() => onHover?.(null)}
                  onFocus={() => onHover?.(p.id)}
                  onBlur={() => onHover?.(null)}
                >
                  <span className="blip__ping" aria-hidden="true" />
                  <span className="blip__core" aria-hidden="true" />
                  <span className="blip__n mono" aria-hidden="true">
                    {pad(p.rank)}
                  </span>
                </button>
              </Tooltip>
            </li>
          ))}
        </ul>
      </div>
      <SonarLegend />
      <figcaption className="callout callout--sea sonar-plot__caption">
        <ShieldCheck strokeWidth={1.5} aria-hidden="true" />
        <span>{t("caption")}</span>
      </figcaption>
      <SonarTable points={points} />
    </figure>
  );
}

/** Pings each blip as the sweep passes it. Paused off screen, in hidden tabs and with reduced motion. */
function useSweep(
  rootRef: RefObject<HTMLDivElement | null>,
  sweepRef: RefObject<HTMLDivElement | null>,
  blips: Blip[],
) {
  // Re-arm only when the blips move; their angles are read back from the rendered buttons.
  const anglesKey = blips.map((b) => `${b.p.id}@${b.angle.toFixed(2)}`).join("|");
  useEffect(() => {
    const root = rootRef.current;
    const sweep = sweepRef.current;
    if (!root || !sweep || prefersReducedMotion() || !anglesKey) return;
    const angles = [...root.querySelectorAll<HTMLElement>(".blip[data-angle]")].map((el) => ({
      el,
      angle: Number(el.dataset.angle),
    }));
    let frame = 0;
    let prev: number | null = null;
    let visible = true;
    const loop = (now: number) => {
      const a = ((now % SWEEP_PERIOD_MS) / SWEEP_PERIOD_MS) * 360;
      sweep.style.transform = `rotate(${a}deg)`;
      if (prev !== null) {
        const from = prev;
        for (const b of angles) {
          const crossed =
            from <= a ? b.angle > from && b.angle <= a : b.angle > from || b.angle <= a;
          if (crossed) ping(b.el);
        }
      }
      prev = a;
      frame = requestAnimationFrame(loop);
    };
    const run = () => {
      cancelAnimationFrame(frame);
      prev = null;
      if (visible && document.visibilityState === "visible") frame = requestAnimationFrame(loop);
    };
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      run();
    });
    io.observe(root);
    document.addEventListener("visibilitychange", run);
    return () => {
      cancelAnimationFrame(frame);
      io.disconnect();
      document.removeEventListener("visibilitychange", run);
    };
  }, [anglesKey, rootRef, sweepRef]);
}

function ping(blip: HTMLElement) {
  blip.querySelector(".blip__ping")?.animate(
    [
      { transform: "scale(1)", opacity: 0.55 },
      { transform: "scale(3.2)", opacity: 0 },
    ],
    { duration: 1400, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
  );
}

// ---- the drawn field: floor, rings, spokes, sector names, centre ----

interface SonarFieldProps {
  floor: number;
  sectors: Vertical[];
  span: number;
}

function SonarField({ floor, sectors, span }: SonarFieldProps) {
  const id = useId();
  const gradientId = `${id}-floor`;
  const boundary = -span / 2; // between the last sector and the first
  return (
    <svg viewBox="-200 -200 400 400" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={gradientId}>
          <stop offset="0%" className="sonar__glow-in" />
          <stop offset="100%" className="sonar__glow-out" />
        </radialGradient>
      </defs>
      <circle r={R_OUT} fill={`url(#${gradientId})`} />
      {ringValues(floor).map((v) => (
        <circle
          key={v}
          r={radius(v, floor)}
          className={v === floor ? "sonar__ring sonar__ring--floor" : "sonar__ring"}
        />
      ))}
      {sectors.length > 1 &&
        sectors.map((_, i) => {
          const deg = i * span - span / 2;
          const [x1, y1] = polar(R_IN - 10, deg);
          const [x2, y2] = polar(R_OUT + 6, deg);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className="sonar__spoke" />;
        })}
      {ringValues(floor).map((v) => {
        const [x, y] = polar(radius(v, floor), boundary);
        return (
          <text key={v} x={x} y={y} className="sonar__ring-label" dy="0.32em">
            {trunc(v)}
          </text>
        );
      })}
      {sectors.map((v, i) => (
        <SectorLabel
          key={v}
          id={`${id}-s${i}`}
          label={verticalLabel(v)}
          mid={i * span}
          span={span}
        />
      ))}
      <circle r={9} className="sonar__centre-ring" />
      <circle r={3} className="sonar__centre" />
    </svg>
  );
}

/** A sector's name on an arc outside the floor ring; reversed in the lower half so it stays upright. */
function SectorLabel({
  id,
  label,
  mid,
  span,
}: {
  id: string;
  label: string;
  mid: number;
  span: number;
}) {
  const half = Math.max(4, span / 2 - 10);
  const lower = Math.cos((mid * Math.PI) / 180) < 0;
  const r = lower ? R_OUT + 17 : R_OUT + 10;
  const [sx, sy] = polar(r, lower ? mid + half : mid - half);
  const [ex, ey] = polar(r, lower ? mid - half : mid + half);
  const large = half * 2 > 180 ? 1 : 0;
  const d = `M ${sx} ${sy} A ${r} ${r} 0 ${large} ${lower ? 0 : 1} ${ex} ${ey}`;
  const arcLength = (r * half * 2 * Math.PI) / 180;
  const text = label.toUpperCase();
  const squeeze = text.length * 5.2 > arcLength;
  return (
    <>
      <path id={id} d={d} fill="none" />
      <text className="sonar__sector">
        <textPath
          href={`#${id}`}
          startOffset="50%"
          textAnchor="middle"
          textLength={squeeze ? arcLength : undefined}
          lengthAdjust={squeeze ? "spacingAndGlyphs" : undefined}
        >
          {text}
        </textPath>
      </text>
    </>
  );
}

// ---- legend and the screen-reader table ----

function SonarLegend() {
  const { t } = useT(sonarMessages);
  const meta = useMeta();
  return (
    <ul className="sonar__legend" aria-hidden="true">
      <li>
        <svg viewBox="0 0 16 16" className="sonar__key">
          <circle cx="8" cy="8" r="6.5" className="sonar__key-ring" />
          <circle cx="8" cy="8" r="2" className="sonar__key-solid" />
        </svg>
        {t("legendCentre")}
      </li>
      <li>
        <svg viewBox="0 0 16 16" className="sonar__key">
          <circle cx="4" cy="8" r="2" className="sonar__key-solid" />
          <circle cx="11" cy="8" r="4" className="sonar__key-solid" />
        </svg>
        {t("legendSize")}
      </li>
      <li>
        <svg viewBox="0 0 16 16" className="sonar__key">
          <circle cx="8" cy="8" r="4.5" className="sonar__key-solid" />
        </svg>
        {meta.group("act_now")}
      </li>
      <li>
        <svg viewBox="0 0 16 16" className="sonar__key">
          <circle cx="8" cy="8" r="4" className="sonar__key-hollow" />
        </svg>
        {meta.group("dive_deeper")}
      </li>
    </ul>
  );
}

function SonarTable({ points }: { points: SonarPoint[] }) {
  const { t } = useT(sonarMessages);
  // A table ignores width: 1px, so the sr-only box wraps it; otherwise it widens the page scroller.
  return (
    <div className="sr-only">
      <table>
        <caption>{t("tableCaption")}</caption>
        <thead>
          <tr>
            <th scope="col">{t("company")}</th>
            <th scope="col">{t("sector")}</th>
            <th scope="col">{t("potential")}</th>
            <th scope="col">{t("evidence")}</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.id}>
              <th scope="row">{p.name}</th>
              <td>{verticalLabel(sectorOf(p))}</td>
              <td>{trunc(p.potential)}</td>
              <td>{trunc(p.evidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

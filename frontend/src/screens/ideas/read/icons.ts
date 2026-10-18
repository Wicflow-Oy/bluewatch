// Icons for Idea Harbour's next-step and flag kinds; the words live in messages.ts.
import {
  Coins,
  Compass,
  Copy,
  EyeOff,
  Feather,
  FileDiff,
  FlaskConical,
  Hand,
  Landmark,
  Link2Off,
  ListChecks,
  Send,
  type LucideIcon,
} from "lucide-react";
import type { FlagKind, StepKind } from "../types";

export const STEP_ICON: Record<StepKind, LucideIcon> = {
  check: ListChecks,
  programme: Compass,
  proof_step: FlaskConical,
  funding: Coins,
  invite: Send,
};

export const FLAG_ICON: Record<FlagKind, LucideIcon> = {
  near_duplicate: Copy,
  held_instructions: Hand,
  low_effort: Feather,
  grant_dependency: Landmark,
  contact_details_removed: EyeOff,
  personal_link_dropped: Link2Off,
  form_text_mismatch: FileDiff,
};

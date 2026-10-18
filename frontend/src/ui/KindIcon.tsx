import {
  Banknote,
  FlaskConical,
  GraduationCap,
  Handshake,
  Landmark,
  MessageSquareText,
  ShieldCheck,
  ShoppingCart,
  type LucideIcon,
} from "lucide-react";
import type { NextStep } from "../contracts";

export type OpportunityKind = NextStep["kind"];

const ICONS: Record<OpportunityKind, LucideIcon> = {
  programme: GraduationCap,
  ask_company: MessageSquareText,
  confirm_match: ShieldCheck,
  grant: Landmark,
  investor: Banknote,
  buyer: ShoppingCart,
  partner: Handshake,
  pilot: FlaskConical,
};

/** Decorative: the kind is always written next to it. */
export function KindIcon({ kind, size = 14 }: { kind: OpportunityKind; size?: number }) {
  const Icon = ICONS[kind];
  return <Icon size={size} strokeWidth={1.5} aria-hidden="true" />;
}

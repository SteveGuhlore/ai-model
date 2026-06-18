import type { ReviewStatus, SafetyStatus } from "@/lib/types";

const SAFETY: Record<SafetyStatus, { label: string; cls: string }> = {
  passed: { label: "SFW ✓", cls: "text-ok" },
  pending: { label: "screening", cls: "text-warn" },
  blocked: { label: "blocked", cls: "text-danger" },
};

const REVIEW: Record<ReviewStatus, { label: string; cls: string }> = {
  pending: { label: "needs review", cls: "text-warn" },
  approved: { label: "approved", cls: "text-ok" },
  rejected: { label: "rejected", cls: "text-danger" },
};

export function SafetyBadge({ status }: { status: SafetyStatus }) {
  const s = SAFETY[status];
  return <span className={`text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  const s = REVIEW[status];
  return <span className={`text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

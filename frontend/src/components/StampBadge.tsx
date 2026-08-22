export function StampBadge({
  status,
  autoApproved = false,
}: {
  status: "pending" | "reviewed";
  autoApproved?: boolean;
}) {
  const isReviewed = status === "reviewed";
  const bg = !isReviewed ? "var(--warning-soft)" : autoApproved ? "var(--ai-soft)" : "var(--success-soft)";
  const fg = !isReviewed ? "var(--warning)" : autoApproved ? "var(--ai)" : "var(--success)";
  const label = !isReviewed ? "Pending" : autoApproved ? "Auto-approved" : "Reviewed";

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ backgroundColor: bg, color: fg }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: fg }} />
      {label}
    </span>
  );
}

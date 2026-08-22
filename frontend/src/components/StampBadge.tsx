/**
 * Review status. Text-only, never a pill — pills cost horizontal padding,
 * which is what wrapped "Auto-approved" onto two lines. `whitespace-nowrap`
 * makes that structurally impossible now.
 *
 * Amber appears here and nowhere else on the page: only "Needs review"
 * earns the page's single color.
 */
export function StampBadge({
  status,
  autoApproved = false,
}: {
  status: "pending" | "reviewed";
  autoApproved?: boolean;
}) {
  if (status === "pending") {
    return (
      <span
        className="inline-flex items-center gap-1.5 whitespace-nowrap text-[13px]"
        style={{ color: "var(--signal)" }}
      >
        <span
          className="h-[5px] w-[5px] rounded-full shrink-0"
          style={{ backgroundColor: "var(--signal-mark)" }}
          aria-hidden
        />
        Needs review
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap text-[13px]"
      style={{ color: "var(--ink-3)" }}
      title={autoApproved ? "Cleared automatically — no flags, no low-confidence field" : "Approved by a reviewer"}
    >
      <span
        className="h-[5px] w-[5px] rounded-full shrink-0"
        style={
          autoApproved
            ? { border: "1px solid var(--ink-4)" }
            : { backgroundColor: "var(--ink-3)" }
        }
        aria-hidden
      />
      {autoApproved ? "Auto-approved" : "Approved"}
    </span>
  );
}

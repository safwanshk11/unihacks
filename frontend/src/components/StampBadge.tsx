/**
 * Review status. Text-only, never a pill — pills cost horizontal padding,
 * which is what wrapped "Auto-approved" onto two lines. `whitespace-nowrap`
 * makes that structurally impossible now.
 *
 * Needs review uses the signal color; approved states use the green review
 * palette so automatic and human approval remain distinct.
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
          className="inline-flex items-center gap-1.5 whitespace-nowrap text-[14px]"
        style={{ color: "var(--signal)" }}
      >
        <span
            className="h-[6px] w-[6px] rounded-full shrink-0"
          style={{ backgroundColor: "var(--signal-mark)" }}
          aria-hidden
        />
        Needs review
      </span>
    );
  }

  return (
      <span
        className="inline-flex items-center gap-1.5 whitespace-nowrap text-[14px]"
        style={{ color: autoApproved ? "var(--approved-auto)" : "var(--approved-human)" }}
      title={autoApproved ? "Cleared automatically — no flags, no low-confidence field" : "Approved by a reviewer"}
    >
      <span
          className="h-[6px] w-[6px] rounded-full shrink-0"
        style={
          autoApproved
            ? { border: "1px solid var(--approved-auto)" }
            : { backgroundColor: "var(--approved-human)" }
        }
        aria-hidden
      />
      {autoApproved ? "Auto-approved" : "Approved"}
    </span>
  );
}

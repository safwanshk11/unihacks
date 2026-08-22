import { useState } from "react";

export function Login({ onSignIn }: { onSignIn: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setBusy(true);
    setError(null);
    try {
      await onSignIn(username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  const inputStyle = {
    borderColor: "var(--rule)",
    backgroundColor: "var(--surface)",
    borderRadius: 5,
    color: "var(--ink)",
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-[380px] glow-in">
        <div className="flex items-baseline gap-2.5 mb-8">
          <span className="text-[17px] font-semibold tracking-[-0.02em]">Lumen</span>
          <span className="eyebrow">Product intelligence</span>
        </div>

        <div className="surface overflow-hidden" style={{ boxShadow: "var(--shadow-lg)" }}>
          <div className="cct-rule" />
          <div className="p-7">
            <h1 className="text-[21px] leading-[1.2] font-semibold tracking-[-0.03em]">Sign in</h1>
            <p className="text-[13px] mt-2 leading-[1.5]" style={{ color: "var(--ink-3)" }}>
              The review console holds unpublished catalogue content.
            </p>

            <form className="flex flex-col gap-4 mt-7" onSubmit={submit}>
              <label className="flex flex-col">
                <span className="eyebrow mb-2">Username</span>
                <input
                  className="w-full border px-3 py-2 text-[13.5px] focus:outline-none"
                  style={inputStyle}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                />
              </label>

              <label className="flex flex-col">
                <span className="eyebrow mb-2">Password</span>
                <input
                  type="password"
                  className="w-full border px-3 py-2 text-[13.5px] focus:outline-none"
                  style={inputStyle}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>

              {error && (
                <div
                  className="border-l-2 px-3 py-2 text-[12.5px] leading-[1.45]"
                  style={{
                    borderColor: "var(--signal-mark)",
                    backgroundColor: "var(--signal-wash)",
                    color: "var(--signal)",
                  }}
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={busy || !username.trim() || !password}
                className="mt-1 text-[13.5px] px-4 py-2.5 transition-opacity disabled:opacity-40"
                style={{ backgroundColor: "var(--ink)", color: "var(--paper-lit)", borderRadius: 5 }}
              >
                {busy ? "Signing in…" : "Sign in"}
              </button>
            </form>
          </div>
        </div>

        <p className="text-[11.5px] mt-5 leading-[1.6]" style={{ color: "var(--ink-4)" }}>
          Credentials come from <span className="font-mono text-[10.5px]">backend/.env</span>. Passwords are PBKDF2-hashed
          at startup and sessions are HMAC-signed — nothing is stored in plaintext, and no credential ships in the
          repository.
        </p>
      </div>
    </div>
  );
}

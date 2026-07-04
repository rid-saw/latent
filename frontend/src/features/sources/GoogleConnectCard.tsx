import { useEffect, useState } from "react";
import { CheckCircle2, Link2 } from "lucide-react";

const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const mock = import.meta.env.VITE_USE_MOCK !== "false";

/** Sidebar card: connect Google (one consent = YouTube + Gmail) or show status. */
export function GoogleConnectCard() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    if (mock) return;
    fetch(`${base}/api/auth/status`)
      .then((r) => r.json())
      .then((s) => setConnected(s.google))
      .catch(() => setConnected(false));
  }, []);

  if (mock) {
    return (
      <div className="mt-auto rounded-lg border border-line p-3 text-xs text-faint">
        Mock mode. Set <code className="text-soft">VITE_USE_MOCK=false</code>{" "}
        and run the backend for real content.
      </div>
    );
  }

  if (connected) {
    return (
      <div className="mt-auto flex items-center gap-2 rounded-lg border border-line p-3 text-xs text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 size={14} /> Google connected (YouTube + Gmail)
      </div>
    );
  }

  return (
    <a
      href={`${base}/api/auth/google/login`}
      className="mt-auto flex items-center gap-2 rounded-lg border border-line bg-surface p-3 text-xs text-ink hover:border-faint"
    >
      <Link2 size={14} /> Connect Google — YouTube + Gmail in one step
    </a>
  );
}

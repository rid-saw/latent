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
      <div className="mt-auto rounded-lg border border-neutral-800 p-3 text-xs text-neutral-500">
        Mock mode. Set <code className="text-neutral-400">VITE_USE_MOCK=false</code>{" "}
        and run the backend for real content.
      </div>
    );
  }

  if (connected) {
    return (
      <div className="mt-auto flex items-center gap-2 rounded-lg border border-neutral-800 p-3 text-xs text-emerald-400">
        <CheckCircle2 size={14} /> Google connected (YouTube + Gmail)
      </div>
    );
  }

  return (
    <a
      href={`${base}/api/auth/google/login`}
      className="mt-auto flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-800/60 p-3 text-xs text-neutral-200 hover:border-neutral-500"
    >
      <Link2 size={14} /> Connect Google — YouTube + Gmail in one step
    </a>
  );
}

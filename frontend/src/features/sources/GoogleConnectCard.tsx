import { useEffect } from "react";
import { AlertTriangle, CheckCircle2, Link2 } from "lucide-react";
import { useAuth } from "@/stores/auth";

const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const mock = import.meta.env.VITE_USE_MOCK !== "false";

const LOGIN_URL = `${base}/api/auth/google/login`;

/** Sidebar card: connect Gmail, or show its status.
 *
 * Connected is a clean statement with nothing to click — the status endpoint
 * verifies against Google, so there's no reason to offer a fix for a problem
 * the user doesn't have. If the token dies later, a 401 anywhere revalidates
 * the store and this flips to "expired" on its own.
 */
export function GoogleConnectCard() {
  const status = useAuth((s) => s.google);
  const check = useAuth((s) => s.check);

  useEffect(() => {
    check();
  }, [check]);

  if (mock) {
    // The demo has no backend to connect anything to. Visitors get the pitch;
    // developers running with the mock flag get the instruction.
    return import.meta.env.VITE_DEMO ? (
      <div className="mt-auto rounded-lg border border-line p-3 text-xs text-faint">
        Everything here is sample content. Run latent yourself to connect your
        own inbox.
      </div>
    ) : (
      <div className="mt-auto rounded-lg border border-line p-3 text-xs text-faint">
        Mock mode. Set <code className="text-soft">VITE_USE_MOCK=false</code> and
        run the backend for real content.
      </div>
    );
  }

  if (status === "checking") {
    return (
      <div className="mt-auto rounded-lg border border-line p-3 text-xs text-faint">
        Checking Google…
      </div>
    );
  }

  if (status === "connected") {
    return (
      <div className="mt-auto flex items-center gap-2 rounded-lg border border-line p-3 text-xs text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 size={14} /> Gmail connected
      </div>
    );
  }

  if (status === "expired") {
    return (
      <a
        href={LOGIN_URL}
        className="mt-auto block rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs hover:border-amber-500/70"
      >
        <p className="flex items-center gap-2 font-medium text-amber-700 dark:text-amber-400">
          <AlertTriangle size={14} /> Google connection expired
        </p>
        <p className="mt-1 text-soft">Reconnect to use inbox blocks.</p>
      </a>
    );
  }

  return (
    <a
      href={LOGIN_URL}
      className="mt-auto flex items-center gap-2 rounded-lg border border-line bg-surface p-3 text-xs text-ink hover:border-faint"
    >
      <Link2 size={14} /> Connect Gmail for inbox blocks
    </a>
  );
}

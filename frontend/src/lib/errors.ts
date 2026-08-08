/** Turning failures into sentences a user can act on.
 *
 * Everything that talks to the backend can fail: the source is rate-limiting
 * us, Google isn't connected, the backend isn't running, the agent timed out.
 * The UI never shows the raw failure — it shows what to do about it.
 */

/** A failed request. `status` is the HTTP code, or 0 if we never reached the
 *  backend. `data` carries anything the failure came with — block creation
 *  sends back the block it saved, so the prompt isn't lost with the error. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly data?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Reads FastAPI's {"detail": "..."} if that's what came back, else the raw body. */
export async function readDetail(res: Response): Promise<string> {
  const body = await res.text().catch(() => "");
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? "").join(", ");
  } catch {
    /* not JSON — fall through to the raw body */
  }
  return body.slice(0, 200);
}

export const OFFLINE = "You're offline. Reconnect and try again.";

/** Whether the browser is *certain* there is no network.
 *
 * Only the false case is trustworthy: `onLine === true` merely means an
 * interface exists, so it still reads true on a hotel wifi you haven't logged
 * into. That asymmetry is fine here, because this is only used to skip work
 * that is guaranteed to fail — a wrong "online" just means waiting as usual.
 *
 * Worth skipping: the provider CLIs retry internally for about three minutes
 * before giving up, and creating a block makes more than one call. Reading
 * this costs nothing; the browser keeps it up to date from the OS.
 */
export const isOffline = () =>
  typeof navigator !== "undefined" && navigator.onLine === false;

/** Human-readable message for anything thrown while calling the API. */
export function friendlyError(e: unknown): string {
  if (!(e instanceof ApiError)) {
    return "Something went wrong. Try that again.";
  }

  switch (e.status) {
    case 0:
      return "Can't reach latent's backend. Is it running? Start it with ./scripts/dev.sh";
    case 401:
      // The card lives at the bottom of the sidebar, not in Settings.
      return "Your Google connection isn't working. Reconnect from the card at the bottom of the sidebar — YouTube and inbox blocks need it.";
    case 404:
      return "That's already gone — it may have been deleted in another tab.";
    case 408:
    case 504:
      return "That took too long. The agent can be slow on the first run — try again.";
    case 429:
      return "That source is rate-limiting us right now. Wait a minute and try again.";
  }

  // 400s are our own validation messages — the backend writes those for humans
  // ("No blocks with content — create some blocks first"), so pass them through.
  if (e.status >= 400 && e.status < 500 && e.message) return e.message;

  if (e.status >= 500) {
    return "latent's backend hit a problem. Check the terminal it's running in for details.";
  }
  return e.message || "Something went wrong. Try that again.";
}

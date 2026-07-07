/** Tracks which item ids the user has already been shown, per block.
 * Returns the ids that are new this time. First sight of a block counts
 * nothing as new (otherwise everything would be badged on first visit). */

const KEY = "latent-seen-items";
const CAP = 100;

type SeenMap = Record<string, string[]>;

function read(): SeenMap {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function diffAndRecord(blockId: string, ids: string[]): string[] {
  const all = read();
  const prior = all[blockId];
  const fresh = prior ? ids.filter((id) => !prior.includes(id)) : [];
  // Remember everything shown so far (capped), not just the latest fetch,
  // so an item doesn't flip back to "new" after briefly rotating out.
  all[blockId] = [...new Set([...(prior ?? []), ...ids])].slice(-CAP);
  localStorage.setItem(KEY, JSON.stringify(all));
  return fresh;
}

export function forgetBlock(blockId: string): void {
  const all = read();
  delete all[blockId];
  localStorage.setItem(KEY, JSON.stringify(all));
}

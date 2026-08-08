import type { Block, BlockLayout, Page, Briefing } from "@/types";
import { mockApi } from "./mock";
import { httpApi } from "./http";

// The seam. The UI only ever talks to this interface, so swapping the mock
// for a real HTTP client (when the backend exists) is a one-line change below.
export interface Api {
  listPages(): Promise<Page[]>;
  createPage(name: string, emoji: string): Promise<Page>;
  updatePage(id: string, name: string, emoji: string): Promise<Page>;
  deletePage(id: string): Promise<void>;
  listBlocks(pageId: string): Promise<Block[]>;
  /** Block creation is slow (two LLM calls), so it reports as it goes:
   *  `created` once the row exists (before any work), `progress` per agent
   *  step, `preview` once raw results exist but before the critic has judged
   *  them. The promise resolves with the final, checked block. */
  createBlock(
    query: string,
    pageId: string,
    on?: {
      created?: (block: Block) => void;
      progress?: (message: string) => void;
      preview?: (block: Block) => void;
    },
  ): Promise<Block>;
  refreshBlock(block: Block): Promise<Block>;
  /** Re-run the agent for a block that never finished routing. Same work and
   *  same narration as createBlock; it just updates an existing row. */
  rebuildBlock(
    id: string,
    on?: {
      created?: (block: Block) => void;
      progress?: (message: string) => void;
      preview?: (block: Block) => void;
    },
  ): Promise<Block>;
  deleteBlock(id: string): Promise<void>;
  saveLayouts(layouts: Record<string, BlockLayout>): Promise<void>;
  getBriefing(pageId: string): Promise<Briefing | null>;
  generateBriefing(pageId: string): Promise<Briefing>;
}

const useMock = import.meta.env.VITE_USE_MOCK !== "false";

export const api: Api = useMock ? mockApi : httpApi;

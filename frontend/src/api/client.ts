import type { Block, BlockLayout, Page, Rundown } from "@/types";
import { mockApi } from "./mock";
import { httpApi } from "./http";

// The seam. The UI only ever talks to this interface, so swapping the mock
// for a real HTTP client (when the backend exists) is a one-line change below.
export interface Api {
  listPages(): Promise<Page[]>;
  createPage(name: string, emoji: string): Promise<Page>;
  deletePage(id: string): Promise<void>;
  listBlocks(pageId: string): Promise<Block[]>;
  createBlock(query: string, pageId: string): Promise<Block>;
  refreshBlock(block: Block): Promise<Block>;
  deleteBlock(id: string): Promise<void>;
  saveLayouts(layouts: Record<string, BlockLayout>): Promise<void>;
  getRundown(pageId: string): Promise<Rundown | null>;
  generateRundown(pageId: string): Promise<Rundown>;
}

const useMock = import.meta.env.VITE_USE_MOCK !== "false";

export const api: Api = useMock ? mockApi : httpApi;

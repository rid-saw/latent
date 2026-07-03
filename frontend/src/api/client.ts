import type { Block } from "@/types";
import { mockApi } from "./mock";

// The seam. The UI only ever talks to this interface, so swapping the mock
// for a real HTTP client (when the backend exists) is a one-line change below.
export interface Api {
  listBlocks(): Promise<Block[]>;
  createBlock(query: string): Promise<Block>;
  refreshBlock(block: Block): Promise<Block>;
  deleteBlock(id: string): Promise<void>;
}

const useMock = import.meta.env.VITE_USE_MOCK !== "false";

// TODO: implement httpApi against the FastAPI backend, then: useMock ? mockApi : httpApi
export const api: Api = useMock ? mockApi : mockApi;

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_USE_MOCK: string;
  readonly VITE_DEMO?: string; // set only by the Pages deploy workflow
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

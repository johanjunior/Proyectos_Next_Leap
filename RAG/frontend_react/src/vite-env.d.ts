/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string;
  readonly VITE_CHAT_REQUEST_TIMEOUT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

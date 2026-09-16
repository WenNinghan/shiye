export type Kind =
  "title" | "paragraph" | "list" | "table" | "image" | "formula";
export type Block = {
  id: string;
  kind: Kind;
  bbox: number[];
  text: string;
  original_text: string;
  cells: string[][];
  confidence: number | null;
  source: string;
  warning: string;
  latex: string;
  display: boolean;
  verified: boolean;
};
export type Page = {
  id: string;
  source_name: string;
  source_page: number;
  width: number;
  height: number;
  rotation: number;
  status: string;
  engine: string;
  error: string;
  blocks: Block[];
  candidate_blocks?: Block[] | null;
  candidate_engine?: string;
  candidate_bbox?: number[] | null;
};
export type Doc = {
  id: string;
  title: string;
  version: number;
  status: string;
  mode: string;
  provider?: "local" | "api";
  created_at: string;
  updated_at: string;
  expires_at: string;
  pages: Page[];
  message: string;
  warnings: string[];
  tasks: Task[];
};
export type HistoryItem = {
  id: string;
  title: string;
  status: string;
  pages: number;
  created_at: string;
  expires_at: string;
  version: number;
};
export type ExportFormat =
  "docx" | "md" | "txt" | "pdf-image" | "pdf-searchable" | "json";
export type Task = {
  id: string;
  title: string;
  source_text: string;
  page_id: string;
  date: string;
  time: string;
  location: string;
  kind: "event" | "deadline";
  confirmed: boolean;
  note: string;
};
export type FormulaStatus = {
  available: boolean;
  running: boolean;
  model_cached: boolean;
  loaded?: boolean;
  model: string;
  device: string;
  engine: string;
  message: string;
  install_command: string;
  paddleocr_version?: string;
  paddlepaddle_version?: string;
};

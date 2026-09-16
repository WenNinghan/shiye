import type { FormulaStatus } from "./types";
export type RecognitionStatus = { desktop: boolean; configured: boolean; revision: number; endpoint: string; model: string };
export type DesktopSettings = { desktop: boolean; configured: boolean; endpoint: string; model: string; remember: boolean; message: string; importing: boolean; formula: FormulaStatus };
export type ProviderInput = { endpoint: string; model: string; key: string; remember: boolean };
declare global {
  interface Window {
    shiyeDesktop?: {
      getSettings(): Promise<DesktopSettings>;
      saveSettings(value: ProviderInput): Promise<DesktopSettings>;
      clearSettings(): Promise<DesktopSettings>;
      importModelPack(): Promise<DesktopSettings>;
    };
  }
}
export const desktop = window.shiyeDesktop;

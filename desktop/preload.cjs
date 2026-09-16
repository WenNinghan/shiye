const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('shiyeDesktop', Object.freeze({
  getSettings: () => ipcRenderer.invoke('shiye:settings'),
  saveSettings: (value) => ipcRenderer.invoke('shiye:save-settings', value),
  clearSettings: () => ipcRenderer.invoke('shiye:clear-settings'),
  importModelPack: () => ipcRenderer.invoke('shiye:import-model'),
}));

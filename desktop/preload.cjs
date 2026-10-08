const { contextBridge, ipcRenderer } = require('electron');
const argument = process.argv.find(value => value.startsWith('--tutor-bootstrap='));
const bootstrap = JSON.parse(Buffer.from(argument?.split('=')[1] || 'e30=', 'base64').toString('utf8'));
contextBridge.exposeInMainWorld('desktop', {
  ...bootstrap,
  listProfiles: () => ipcRenderer.invoke('profiles:list'),
  createProfile: input => ipcRenderer.invoke('profiles:create', input),
  openProfile: id => ipcRenderer.invoke('profiles:open', id),
  switchProfile: () => ipcRenderer.invoke('profiles:switch'),
  saveApiKey: key => ipcRenderer.invoke('settings:api-key', key),
});

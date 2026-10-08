const { app, BrowserWindow, ipcMain, dialog, safeStorage, shell } = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn, execFile } = require('node:child_process');
const readline = require('node:readline');

const root = path.resolve(__dirname, '..');
if (process.env.CSTUTOR_SMOKE === '1') app.setPath('userData', path.join(root, 'desktop-build', 'smoke-profiles'));
let window, backend, currentProfile, apiBase, sessionToken;
let quitting = false;
const dataRoot = () => app.getPath('userData');
const profilesPath = () => path.join(dataRoot(), 'profiles.json');
const profileDirectory = id => path.join(dataRoot(), 'profiles', id);
const validId = id => typeof id === 'string' && /^[a-f0-9-]{36}$/.test(id);

async function profiles() {
  try { return JSON.parse(await fs.readFile(profilesPath(), 'utf8')).filter(p => validId(p.id)); }
  catch (error) { if (error.code === 'ENOENT') return []; throw new Error('Could not read your profiles. Your files have been kept.'); }
}
async function writeProfiles(items) {
  await fs.mkdir(dataRoot(), { recursive: true });
  await fs.writeFile(profilesPath() + '.tmp', JSON.stringify(items, null, 2));
  await fs.rename(profilesPath() + '.tmp', profilesPath());
}
async function readKey(id) {
  try { return safeStorage.decryptString(await fs.readFile(path.join(profileDirectory(id), 'api-key.enc'))); }
  catch (error) { if (error.code === 'ENOENT') return ''; throw new Error('Could not unlock this profile’s API key.'); }
}
async function storeKey(id, key) {
  if (!safeStorage.isEncryptionAvailable()) throw new Error('Windows credential encryption is unavailable.');
  const destination = path.join(profileDirectory(id), 'api-key.enc');
  await fs.writeFile(destination + '.tmp', safeStorage.encryptString(key));
  await fs.rename(destination + '.tmp', destination);
}
async function stopBackend() {
  const child = backend;
  backend = undefined;
  if (!child || child.exitCode !== null) return;
  if (!child.stdin.destroyed) child.stdin.write('STOP\n');
  await Promise.race([new Promise(resolve => child.once('exit', resolve)), new Promise(resolve => setTimeout(resolve, 4000))]);
  if (child.exitCode === null) await new Promise(resolve => execFile('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true }, resolve));
}
async function startBackend(profile) {
  await stopBackend();
  const directory = profileDirectory(profile.id);
  await fs.mkdir(directory, { recursive: true });
  const key = await readKey(profile.id);
  sessionToken = crypto.randomBytes(32).toString('hex');
  const executable = app.isPackaged ? path.join(process.resourcesPath, 'backend', 'tutor-backend.exe') : path.join(root, 'backend', 'venv', 'Scripts', 'python.exe');
  const pythonRuntime = app.isPackaged ? path.join(process.resourcesPath, 'backend', 'python-runtime', 'python.exe') : executable;
  const compiler = app.isPackaged ? path.join(process.resourcesPath, 'cpp', 'zig.exe') : path.join(root, '.tools', 'zig-x86_64-windows-0.15.2', 'zig.exe');
  const env = { ...process.env, CSTUTOR_DATA_DIR: directory, CSTUTOR_DESKTOP_TOKEN: sessionToken,
    CSTUTOR_CPP_COMPILER: compiler, CSTUTOR_PYTHON_RUNTIME: pythonRuntime,
    OPENAI_API_KEY: key, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' };
  // Fresh profiles never inherit a developer's .env/API key.
  env.CSTUTOR_DESKTOP_MODE = '1';
  const child = spawn(executable, app.isPackaged ? [] : ['-m', 'backend.desktop_entry'], { cwd: app.isPackaged ? directory : root, env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  backend = child;
  child.stderr.resume();
  child.stdin.on('error', () => {});
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('The backend did not start within two minutes.')), 120000);
    child.once('error', () => { clearTimeout(timer); reject(new Error('Could not start the bundled backend.')); });
    child.once('exit', () => { clearTimeout(timer); reject(new Error('The backend stopped during startup.')); });
    readline.createInterface({ input: child.stdout }).on('line', line => {
      if (line.startsWith('DESKTOP_READY:')) { clearTimeout(timer); resolve(JSON.parse(line.slice(14)).port); }
    });
  });
  apiBase = `http://127.0.0.1:${port}`;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { const response = await fetch(apiBase + '/health', { headers: { 'X-Desktop-Token': sessionToken } }); if (response.ok) { currentProfile = profile; return; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('The desktop backend is not responding.');
}
async function showWindow(profile = null) {
  const previous = window;
  const bootstrap = { apiBase: profile ? apiBase : '', token: profile ? sessionToken : '', profile };
  const next = new BrowserWindow({ width: 1360, height: 900, minWidth: 850, minHeight: 650, show: false, autoHideMenuBar: true,
    title: 'CS Textbook Tutor', webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true, plugins: true,
      partition: profile ? `persist:tutor-${profile.id}` : 'persist:tutor-setup',
      additionalArguments: ['--tutor-bootstrap=' + Buffer.from(JSON.stringify(bootstrap)).toString('base64')] } });
  window = next;
  next.webContents.setWindowOpenHandler(({ url }) => {
    if ((apiBase && url.startsWith(apiBase + '/textbooks/')) || /^https:\/\//.test(url)) void shell.openExternal(url);
    return { action: 'deny' };
  });
  next.webContents.on('will-navigate', (event, url) => { if (!url.startsWith('file://')) event.preventDefault(); });
  next.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  next.on('closed', () => { if (window === next) window = undefined; });
  await next.loadFile(path.join(root, 'frontend', 'dist', 'index.html'));
  if (process.env.CSTUTOR_SMOKE !== '1') next.show();
  if (previous && !previous.isDestroyed()) previous.close();
}
function trusted(event) {
  if (!window || event.sender !== window.webContents || event.senderFrame !== window.webContents.mainFrame) throw new Error('Untrusted settings request.');
}
ipcMain.handle('profiles:list', async event => { trusted(event); return profiles(); });
ipcMain.handle('profiles:create', async (event, input) => {
  trusted(event);
  if (!input || typeof input.name !== 'string' || !input.name.trim() || input.name.length > 60 || !['ocean','forest','violet','amber'].includes(input.theme)
      || !['📚','💻','🧠','🚀'].includes(input.avatar) || !['Learn at my own pace','Prepare for exams','Practice programming'].includes(input.goal)
      || typeof input.apiKey !== 'string' || input.apiKey.length > 1000) throw new Error('Check your profile details.');
  const profile = { id: crypto.randomUUID(), name: input.name.trim(), theme: input.theme, avatar: input.avatar, goal: input.goal };
  await fs.mkdir(profileDirectory(profile.id), { recursive: true });
  if (input.apiKey.trim()) await storeKey(profile.id, input.apiKey.trim());
  const items = await profiles(); items.push(profile); await writeProfiles(items);
  try { await startBackend(profile); await showWindow(profile); return { saved: true }; }
  catch (error) { await stopBackend(); throw error; }
});
ipcMain.handle('profiles:open', async (event, id) => { trusted(event); const profile = (await profiles()).find(p => p.id === id); if (!profile) throw new Error('Profile was not found.'); await startBackend(profile); await showWindow(profile); });
ipcMain.handle('profiles:switch', async event => { trusted(event); await stopBackend(); currentProfile = null; await showWindow(); });
ipcMain.handle('settings:api-key', async (event, key) => {
  trusted(event);
  if (!currentProfile || typeof key !== 'string' || !key.trim() || key.length > 1000) throw new Error('Enter your API key.');
  await storeKey(currentProfile.id, key.trim());
  const response = await fetch(apiBase + '/desktop/api-key', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Desktop-Token': sessionToken }, body: JSON.stringify({ key: key.trim() }) });
  if (!response.ok) throw new Error('Key saved. Reopen the profile to reconnect.');
  return { saved: true };
});
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.whenReady().then(() => showWindow()).catch(error => { dialog.showErrorBox('Could not open Textbook Tutor', error.message); app.quit(); });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', event => { if (!quitting) { event.preventDefault(); quitting = true; stopBackend().finally(() => app.quit()); } });
}

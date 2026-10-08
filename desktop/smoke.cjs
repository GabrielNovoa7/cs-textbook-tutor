process.env.CSTUTOR_SMOKE = '1';
const { app, BrowserWindow, safeStorage } = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
require('./main.cjs');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function ready(predicate) {
  for (let i = 0; i < 1200; i++) {
    const w = BrowserWindow.getAllWindows().at(-1);
    if (w && !w.isDestroyed() && !w.webContents.isLoading()) {
      try { if (await w.webContents.executeJavaScript(predicate)) return w; } catch {}
    }
    await pause(100);
  }
  throw new Error('Desktop window readiness timeout');
}
app.whenReady().then(async () => {
  try {
    let w = await ready('Boolean(window.desktop && document.querySelector("h1"))');
    assert.equal(await w.webContents.executeJavaScript('window.desktop.profile'), null);
    await w.webContents.executeJavaScript(`
      [...document.querySelectorAll('button')].find(b => b.textContent === 'Create a new profile')?.click();
    `);
    await pause(150);
    assert.equal(await w.webContents.executeJavaScript('document.querySelector(".setup-actions .start-concept-button").disabled'), true);
    await w.webContents.executeJavaScript(`
      const input = document.querySelector('#setup-name');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'Wizard test');
      input.dispatchEvent(new Event('input', {bubbles:true}));
    `);
    await pause(150);
    await w.webContents.executeJavaScript('document.querySelector(".setup-actions .start-concept-button").click()');
    await pause(150);
    assert.equal(await w.webContents.executeJavaScript('document.querySelector("h1").textContent'), 'Your workspace');
    await w.webContents.executeJavaScript('document.querySelector(".setup-actions .start-concept-button").click()');
    await pause(150);
    assert.equal(await w.webContents.executeJavaScript('document.querySelector("h1").textContent'), 'API key');
    await w.webContents.executeJavaScript('document.querySelector(".setup-actions .start-concept-button").click()');
    await pause(150);
    assert.equal(await w.webContents.executeJavaScript('document.querySelector("h1").textContent'), 'Ready to study');
    await w.webContents.executeJavaScript('void window.desktop.createProfile({name:"Desktop smoke test",avatar:"🚀",theme:"forest",goal:"Practice programming",apiKey:"test-key-not-real"})');
    w = await ready('Boolean(window.desktop?.profile && document.body.innerText.includes("Library"))');
    const first = await w.webContents.executeJavaScript('window.desktop.profile');
    assert.equal(first.name, 'Desktop smoke test');
    assert.equal(await w.webContents.executeJavaScript('document.documentElement.dataset.theme'), 'forest');
    const encrypted = await fs.readFile(path.join(app.getPath('userData'), 'profiles', first.id, 'api-key.enc'));
    assert.ok(!encrypted.includes(Buffer.from('test-key-not-real')));
    assert.equal(safeStorage.decryptString(encrypted), 'test-key-not-real');
    assert.equal(await w.webContents.executeJavaScript('fetch(window.desktop.apiBase+"/textbooks").then(r=>r.json()).then(x=>x.length)'), 0);
    await w.webContents.executeJavaScript('void window.desktop.switchProfile()');
    w = await ready('Boolean(window.desktop && !window.desktop.profile && document.body.innerText.includes("Welcome back"))');
    await w.webContents.executeJavaScript('void window.desktop.createProfile({name:"Second workspace",avatar:"📚",theme:"amber",goal:"Learn at my own pace",apiKey:""})');
    w = await ready('window.desktop?.profile?.name === "Second workspace" && document.body.innerText.includes("Library")');
    const second = await w.webContents.executeJavaScript('window.desktop.profile');
    assert.notEqual(first.id, second.id);
    assert.equal(await w.webContents.executeJavaScript('localStorage.getItem("tutor-profile-name")'), 'Second workspace');
    assert.equal(await w.webContents.executeJavaScript('document.documentElement.dataset.theme'), 'amber');
    console.log('PASS: onboarding, encrypted key, authenticated API, themes, separate profiles and switching.');
    app.quit();
  } catch (error) { console.error(error); process.exitCode = 1; app.quit(); }
});

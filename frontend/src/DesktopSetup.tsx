import { useEffect, useState } from 'react';
import type { DesktopProfile } from './desktop';
import App from './App';
import './desktop.css';

const themes = [{ id: 'ocean', name: 'Ocean Blue', color: '#7ca7ff' }, { id: 'forest', name: 'Forest Green', color: '#73d5b0' }, { id: 'violet', name: 'Soft Violet', color: '#bf9bff' }, { id: 'amber', name: 'Warm Amber', color: '#f4c477' }];
const goals = ['Learn at my own pace', 'Prepare for exams', 'Practice programming'];
const steps = ['Your profile', 'Your workspace', 'API key', 'Ready to study'];

export default function DesktopSetup() {
  const desktop = window.desktop;
  const [profiles, setProfiles] = useState<DesktopProfile[]>([]);
  const [creating, setCreating] = useState(false);
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [avatar, setAvatar] = useState('📚');
  const [theme, setTheme] = useState('ocean');
  const [goal, setGoal] = useState(goals[0]);
  const [apiKey, setApiKey] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (desktop && !desktop.profile) desktop.listProfiles().then(setProfiles).catch(e => setError(String(e)));
  }, [desktop]);
  useEffect(() => { if (desktop && !desktop.profile) document.documentElement.dataset.theme = theme; }, [desktop, theme]);
  if (!desktop || desktop.profile) return <App />;
  async function launch(action: () => Promise<void>) {
    setBusy(true); setError('');
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); setBusy(false); }
  }
  return <main className="desktop-setup"><section className="setup-card">
    <p className="eyebrow">CS TEXTBOOK TUTOR · DESKTOP</p>
    {profiles.length > 0 && !creating ? <>
      <h1>Welcome back</h1><p>Choose your personal study workspace.</p>
      <div className="profile-list">{profiles.map(p => <button disabled={busy} key={p.id} onClick={() => void launch(() => desktop.openProfile(p.id))}><span>{p.avatar}</span><strong>{p.name}</strong><small>{p.goal}</small></button>)}</div>
      <button className="start-concept-button" disabled={busy} onClick={() => setCreating(true)}>Create a new profile</button>
    </> : <>
      <ol className="setup-steps" aria-label="Profile setup progress">{steps.map((label, i) => <li key={label} aria-current={i === step ? 'step' : undefined} className={i <= step ? 'active' : ''}><span>{i + 1}</span>{label}</li>)}</ol>
      <h1>{steps[step]}</h1>
      {step === 0 && <><p>Start fresh with your own books and progress.</p><label className="setup-label" htmlFor="setup-name">What should we call you?</label><input id="setup-name" autoFocus maxLength={60} value={name} onChange={e => setName(e.target.value)} placeholder="Your name" autoComplete="nickname" /><fieldset><legend>Choose your avatar</legend><div className="setup-choices">{['📚', '💻', '🧠', '🚀'].map(a => <button key={a} className={avatar === a ? 'selected' : ''} aria-pressed={avatar === a} onClick={() => setAvatar(a)} aria-label={`Avatar ${a}`}>{a}</button>)}</div></fieldset></>}
      {step === 1 && <><p>Make this workspace feel like yours.</p><fieldset><legend>Choose a color style</legend><div className="setup-choices">{themes.map(t => <button key={t.id} className={theme === t.id ? 'selected' : ''} aria-pressed={theme === t.id} onClick={() => setTheme(t.id)}><span className="theme-swatch" style={{ background: t.color }} />{t.name}</button>)}</div></fieldset><div className="setup-preview"><span>{avatar}</span><div><strong>{name || 'Your'}’s study workspace</strong><p>Reading, practice, and progress in one place.</p><progress value={65} max={100} aria-label="Example progress" /></div></div><label className="setup-label" htmlFor="setup-goal">Your learning goal</label><select id="setup-goal" value={goal} onChange={e => setGoal(e.target.value)}>{goals.map(g => <option key={g}>{g}</option>)}</select></>}
      {step === 2 && <><p>Add your own OpenAI API key to create quizzes and use the tutor. You can skip this step and add it in your profile settings later.</p><label className="setup-label" htmlFor="setup-key">OpenAI API key (optional)</label><input id="setup-key" type={visible ? 'text' : 'password'} value={apiKey} onChange={e => setApiKey(e.target.value)} maxLength={1000} autoComplete="off" spellCheck={false} placeholder="Paste your API key" /><label className="setup-show"><input type="checkbox" checked={visible} onChange={e => setVisible(e.target.checked)} /> Show key</label><p className="setup-help">Your key is encrypted on this Windows account. AI features use the internet and your API account’s billing. A ChatGPT subscription does not include API usage.</p><a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">Open API-key settings ↗</a></>}
      {step === 3 && <><div className="setup-preview"><span>{avatar}</span><div><strong>{name}</strong><p>{goal}</p></div></div><dl className="setup-review"><dt>Color style</dt><dd>{themes.find(t => t.id === theme)?.name}</dd><dt>API key</dt><dd>{apiKey.trim() ? 'Added — stored encrypted' : 'Skipped — add it later'}</dd><dt>Library</dt><dd>Fresh books and progress</dd></dl><p>Your existing development library stays in its current location.</p></>}
      <footer className="setup-actions"><button disabled={busy} onClick={() => step ? setStep(step - 1) : setCreating(false)} hidden={!step && !profiles.length}>Back</button><button className="start-concept-button" disabled={busy || !name.trim()} onClick={() => step < 3 ? setStep(step + 1) : void launch(() => desktop.createProfile({ name: name.trim(), avatar, theme, goal, apiKey: apiKey.trim() }))}>{step === 3 ? 'Create profile & start studying' : step === 2 && !apiKey.trim() ? 'Skip for now →' : 'Next →'}</button></footer>
    </>}
    {busy && <p role="status">Opening your workspace… the first launch may take a moment.</p>}
    {error && <p className="setup-error" role="alert">{error}</p>}
  </section></main>;
}

export function DesktopKeySettings() {
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (!window.desktop) return null;
  return <div className="desktop-key-settings"><label htmlFor="desktop-key">Update OpenAI API key</label><input id="desktop-key" type="password" autoComplete="off" maxLength={1000} value={key} onChange={e => setKey(e.target.value)} placeholder="Paste a new key" /><button disabled={busy || !key.trim()} onClick={async () => { setBusy(true); try { await window.desktop!.saveApiKey(key.trim()); setKey(''); setMessage('API key saved securely.'); } catch (e) { setMessage(String(e)); } finally { setBusy(false); } }}>Save key</button><p role="status">{message}</p><button disabled={busy} onClick={() => void window.desktop!.switchProfile().catch(e => setMessage(String(e)))}>Switch or create profile</button></div>;
}

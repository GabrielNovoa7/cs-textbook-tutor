import { DesktopKeySettings } from "./DesktopSetup";
import { useEffect, useRef, useState } from "react";

const themes = [
  { id: "ocean", name: "Ocean Blue", color: "#7ca7ff" },
  { id: "forest", name: "Forest Green", color: "#73d5b0" },
  { id: "violet", name: "Soft Violet", color: "#bf9bff" },
  { id: "amber", name: "Warm Amber", color: "#f4c477" },
];

function saved(key: string, fallback: string) {
  try { return localStorage.getItem(key) || fallback; }
  catch { return fallback; }
}

export default function ProfilePreferences() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(() => saved("tutor-profile-name", "Student"));
  const [theme, setTheme] = useState(() => {
    const value = saved("tutor-theme", "ocean");
    return themes.some((item) => item.id === value) ? value : "ocean";
  });
  const container = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("tutor-theme", theme);
      localStorage.setItem("tutor-profile-name", name);
    } catch { /* Preferences still work when browser storage is unavailable. */ }
  }, [name, theme]);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    function escape(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
    }
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return <div className="profile-preferences" ref={container}>
    <button className="profile-trigger" ref={trigger} aria-label="Profile and appearance preferences"
      aria-expanded={open} onClick={() => setOpen(!open)}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <circle cx="12" cy="8" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" />
      </svg>
    </button>
    {open && <section className="profile-panel" aria-label="Your profile">
      <h3>Your Profile</h3>
      <label htmlFor="profile-name">Display name</label>
      <input id="profile-name" maxLength={40} value={name} onChange={(event) => setName(event.target.value)} />
      <fieldset className="theme-picker"><legend>Color preference</legend>
        {themes.map((item) => <label className="theme-choice" key={item.id}>
          <input type="radio" name="theme" value={item.id} checked={theme === item.id} onChange={() => setTheme(item.id)} />
          <span className="theme-swatch" style={{ background: item.color }} />{item.name}
        </label>)}
      </fieldset>
      <p>{window.desktop ? "Preferences are saved for this profile." : "Preferences are saved in this browser."}</p><DesktopKeySettings />
    </section>}
  </div>;
}

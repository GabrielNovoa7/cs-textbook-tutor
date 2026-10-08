export type DesktopProfile = { id: string; name: string; theme: string; avatar: string; goal: string };
declare global {
  interface Window {
    desktop?: {
      apiBase: string; token: string; profile: DesktopProfile | null;
      listProfiles(): Promise<DesktopProfile[]>;
      createProfile(input: Omit<DesktopProfile, 'id'> & { apiKey: string }): Promise<void>;
      openProfile(id: string): Promise<void>;
      switchProfile(): Promise<void>;
      saveApiKey(key: string): Promise<void>;
    };
  }
}
export const API_BASE = window.desktop?.apiBase || 'http://127.0.0.1:8000';
export function resourceUrl(path: string) {
  const url = new URL(API_BASE + path);
  if (window.desktop?.token) url.searchParams.set('desktop_token', window.desktop.token);
  return url.toString();
}
export function initializeDesktop() {
  const desktop = window.desktop;
  if (!desktop?.profile) return;
  for (const [key, value] of [['tutor-profile-name', desktop.profile.name], ['tutor-theme', desktop.profile.theme]]) {
    if (!localStorage.getItem(key)) localStorage.setItem(key, value);
  }
  const original = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    if (new URL(url, location.href).origin !== desktop.apiBase) return original(input, init);
    const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined));
    headers.set('X-Desktop-Token', desktop.token);
    return original(input, { ...init, headers });
  };
}

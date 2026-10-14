export default function WorkspaceIcon({ name }: { name: 'library' | 'path' | 'chat' | 'progress' }) {
  const paths = {
    library: 'M4 4h6v16H4z M14 4h6v16h-6z M4 8h6 M14 8h6',
    path: 'M6 5h8a4 4 0 0 1 0 8H10a4 4 0 0 0 0 8h8 M6 3v4 M18 19v4',
    chat: 'M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2z M7 9h10 M7 13h6',
    progress: 'M4 20V10 M12 20V4 M20 20v-7',
  };
  return <svg className="workspace-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import DesktopSetup from './DesktopSetup.tsx'
import { initializeDesktop } from './desktop'
import './workspace.css'

initializeDesktop()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {window.desktop && <div className="window-titlebar"><span className="window-titlebar-mark">CS</span><span>Textbook Tutor</span></div>}
    <DesktopSetup />
  </StrictMode>,
)

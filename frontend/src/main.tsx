import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import DesktopSetup from './DesktopSetup.tsx'
import { initializeDesktop } from './desktop'

initializeDesktop()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DesktopSetup />
  </StrictMode>,
)

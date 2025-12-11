/**
 * MAGNET App - Main Entry Point
 *
 * Bootstraps the MAGNET Ship Design System UI.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// Import global styles
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

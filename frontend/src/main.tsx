import { setupDemo } from './demoApi'
import React from 'react'
import ReactDOM from 'react-dom/client'
import Introduction from './Introduction'
import './fonts'
import './styles.css'
import './journal.css'

if (import.meta.env.MODE === 'demo') setupDemo()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><Introduction /></React.StrictMode>,
)

import { setupDemo } from './demoApi'
import { setupStagingNotice } from './siteNotice'
import React from 'react'
import ReactDOM from 'react-dom/client'
import Introduction from './Introduction'
import './fonts'
import './styles.css'
import './journal.css'
import './personal-journal.css'
import './tokens.css'
import './exercise.css'

if (import.meta.env.MODE === 'demo') setupDemo()
// scripts/build-staging.sh가 테스트 서버 빌드에서만 켠다.
else if (import.meta.env.VITE_NOURISHON_STAGING_NOTICE === '1') setupStagingNotice()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><Introduction /></React.StrictMode>,
)

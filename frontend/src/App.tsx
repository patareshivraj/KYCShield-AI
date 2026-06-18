import { Routes, Route, Link } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import DashboardPage from './pages/DashboardPage'
import DocumentPage from './pages/DocumentPage'
import { ShieldAlert } from 'lucide-react'

export default function App() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 flex flex-col font-sans">
      <header className="border-b border-neutral-800 bg-neutral-900 px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 text-xl font-bold tracking-tight">
          <ShieldAlert className="w-6 h-6 text-red-500" />
          KYCShield <span className="font-light text-neutral-400">Investigator</span>
        </Link>
        <div className="text-sm font-mono text-neutral-500">
          Phase 11 Workbench
        </div>
      </header>

      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/dashboard/:applicantId" element={<DashboardPage />} />
          <Route path="/documents/:documentId" element={<DocumentPage />} />
        </Routes>
      </main>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FileText, ChevronRight, ArrowLeft } from 'lucide-react'

export default function DashboardPage() {
  const { applicantId } = useParams()
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch(`/api/v1/investigation/applicants/${applicantId}`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
  }, [applicantId])

  if (!data) return <div className="p-12 text-center text-neutral-500 animate-pulse">Loading Intelligence...</div>

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-300 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Queue
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Applicant Overview</h1>
        <div className="font-mono text-sm text-neutral-500 mt-1">{applicantId}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.documents.map((doc: any) => (
          <DocumentCard key={doc.document_id} doc={doc} />
        ))}
      </div>
    </div>
  )
}

function DocumentCard({ doc }: { doc: any }) {
  const isCritical = doc.risk_level === 'CRITICAL' || doc.risk_level === 'HIGH'
  
  return (
    <Link 
      to={`/documents/${doc.document_id}`}
      className={`block p-6 rounded-xl border transition-colors ${
        isCritical ? 'bg-red-950/20 border-red-900/50 hover:border-red-500/50' : 'bg-neutral-900 border-neutral-800 hover:border-neutral-600'
      }`}
    >
      <div className="flex justify-between items-start mb-4">
        <div className="p-3 bg-neutral-950 rounded-lg">
          <FileText className={`w-6 h-6 ${isCritical ? 'text-red-500' : 'text-neutral-400'}`} />
        </div>
        <div className={`px-2.5 py-1 text-xs font-bold rounded-full ${
          doc.risk_level === 'CRITICAL' ? 'bg-red-500/20 text-red-500' : 
          doc.risk_level === 'HIGH' ? 'bg-orange-500/20 text-orange-500' : 
          'bg-green-500/20 text-green-500'
        }`}>
          {doc.risk_level}
        </div>
      </div>
      
      <h3 className="text-lg font-semibold capitalize mb-1">{doc.document_type.replace('_', ' ')}</h3>
      <div className="text-sm text-neutral-400 font-mono truncate mb-6">{doc.document_id.split('-')[0]}</div>
      
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">Risk Score</div>
          <div className={`text-2xl font-black ${isCritical ? 'text-red-500' : 'text-white'}`}>
            {doc.risk_score?.toFixed(1) || 'N/A'}
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-neutral-500" />
      </div>
    </Link>
  )
}

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileUp, ChevronRight, Activity, Beaker } from 'lucide-react'

export default function UploadPage() {
  const [applicants, setApplicants] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/v1/investigation/applicants')
      .then(r => r.json())
      .then(setApplicants)
      .catch(console.error)
  }, [])

  const runDemo = async () => {
    try {
      const resp = await fetch('/api/v1/investigation/applicants')
      const data = await resp.json()
      if (data.length > 0) {
        navigate(`/dashboard/${data[0].applicant_id}`)
      } else {
        alert("Please run 'python tests/test_risk.py' to generate demo data first.")
      }
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-8 text-center space-y-6">
        <div className="mx-auto w-16 h-16 bg-neutral-800 rounded-full flex items-center justify-center">
          <FileUp className="w-8 h-8 text-neutral-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Investigator Workbench</h2>
          <p className="text-neutral-400 mt-2">Upload KYC documents or select an existing applicant to investigate.</p>
        </div>
        
        <div className="flex justify-center gap-4">
          <button 
            onClick={runDemo}
            className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            <Beaker className="w-5 h-5" />
            Open Demo Mode
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-neutral-400" />
          Recent Applicants
        </h3>
        <div className="grid gap-3">
          {applicants.map(app => (
            <Link 
              key={app.applicant_id}
              to={`/dashboard/${app.applicant_id}`}
              className="flex items-center justify-between p-4 bg-neutral-900 border border-neutral-800 rounded-lg hover:border-neutral-600 transition-colors"
            >
              <div>
                <div className="font-mono text-sm text-neutral-300">{app.applicant_id}</div>
                <div className="text-sm text-neutral-500 mt-1">Ref: {app.external_reference} • Status: {app.job_status}</div>
              </div>
              <ChevronRight className="w-5 h-5 text-neutral-500" />
            </Link>
          ))}
          {applicants.length === 0 && (
            <div className="p-8 text-center text-neutral-500 bg-neutral-900 border border-neutral-800 border-dashed rounded-lg">
              No applicants found in the database.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

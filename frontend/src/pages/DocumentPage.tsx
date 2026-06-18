import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Layers, AlertTriangle, Fingerprint, EyeOff, Eye } from 'lucide-react'

export default function DocumentPage() {
  const { documentId } = useParams()
  const [data, setData] = useState<any>(null)
  
  const [showOCR, setShowOCR] = useState(false)
  const [showClusters, setShowClusters] = useState(true)

  useEffect(() => {
    fetch(`/api/v1/investigation/documents/${documentId}`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
  }, [documentId])

  if (!data) return <div className="p-12 text-center text-neutral-500 animate-pulse">Loading Document Analysis...</div>

  const isCritical = data.risk?.risk_level === 'CRITICAL' || data.risk?.risk_level === 'HIGH'

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to=".." relative="path" className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-300 mb-4">
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold tracking-tight capitalize">{data.document_type.replace('_', ' ')} Analysis</h1>
        </div>
        
        <div className={`px-6 py-3 rounded-xl border ${isCritical ? 'bg-red-950/30 border-red-900/50 text-red-500' : 'bg-green-950/30 border-green-900/50 text-green-500'} flex items-center gap-4`}>
          <div className="text-right">
            <div className="text-xs font-semibold uppercase tracking-wider mb-1 opacity-70">Risk Score</div>
            <div className="text-3xl font-black">{data.risk?.risk_score.toFixed(1)}</div>
          </div>
          <div className="h-10 w-px bg-current opacity-20"></div>
          <div>
            <div className="text-lg font-bold">{data.risk?.risk_level}</div>
            <div className="text-xs opacity-70">{data.risk?.executive_summary}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col - Image Viewer */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden flex flex-col">
            <div className="border-b border-neutral-800 bg-neutral-950 px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold">
                <Layers className="w-5 h-5 text-neutral-400" />
                Visual Forensics Overlay
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => setShowOCR(!showOCR)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md border flex items-center gap-2 transition-colors ${showOCR ? 'bg-blue-900/30 border-blue-800 text-blue-400' : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:bg-neutral-700'}`}
                >
                  {showOCR ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                  OCR Fields
                </button>
                <button 
                  onClick={() => setShowClusters(!showClusters)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md border flex items-center gap-2 transition-colors ${showClusters ? 'bg-red-900/30 border-red-800 text-red-400' : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:bg-neutral-700'}`}
                >
                  {showClusters ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                  Evidence Clusters
                </button>
              </div>
            </div>
            
            <div className="relative bg-black flex-1 min-h-[600px] flex items-center justify-center p-4 overflow-hidden">
              <ForensicCanvas 
                documentId={data.document_id}
                ocrFields={showOCR ? data.ocr_fields : []}
                clusters={showClusters ? data.clusters : []}
              />
            </div>
          </div>
        </div>

        {/* Right Col - Explanation */}
        <div className="space-y-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Risk Drivers
            </h3>
            <ul className="space-y-3">
              {data.risk?.investigator_summary.split(';').map((s: string, i: number) => (
                <li key={i} className="text-sm text-neutral-300 flex gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-500 mt-1.5 shrink-0" />
                  {s.trim()}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
              <Fingerprint className="w-5 h-5 text-red-400" />
              Critical Clusters
            </h3>
            <div className="space-y-4">
              {data.risk?.critical_clusters.map((c: any, i: number) => (
                <div key={i} className="p-3 bg-neutral-950 rounded-lg border border-neutral-800">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold px-2 py-1 bg-red-950 text-red-500 rounded">Rank {i + 1}</span>
                    <span className="text-xs font-mono text-neutral-500">+{c.score.toFixed(1)} pts</span>
                  </div>
                  <p className="text-sm text-neutral-300">{c.explanation}</p>
                </div>
              ))}
            </div>
          </div>
          
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
             <h3 className="text-lg font-bold mb-4">Risk Factors</h3>
             <div className="space-y-2">
               {data.risk?.factors.map((f: any, i: number) => (
                 <div key={i} className="flex justify-between items-center text-sm border-b border-neutral-800 pb-2 last:border-0">
                   <span className="text-neutral-400">{f.name}</span>
                   <span className="font-mono text-neutral-200">{f.score.toFixed(1)}</span>
                 </div>
               ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ForensicCanvas({ documentId, ocrFields, clusters }: { documentId: string, ocrFields: any[], clusters: any[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imageRef = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    const img = new Image()
    img.src = `/api/v1/investigation/documents/${documentId}/image`
    img.onload = () => {
      imageRef.current = img
      draw()
    }
  }, [documentId])

  useEffect(() => {
    draw()
  }, [ocrFields, clusters])

  const draw = () => {
    const canvas = canvasRef.current
    const container = containerRef.current
    const img = imageRef.current
    if (!canvas || !container || !img) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Calculate scaling to fit container while maintaining aspect ratio
    const containerRatio = container.clientWidth / container.clientHeight
    const imgRatio = img.width / img.height
    
    let drawWidth, drawHeight
    if (containerRatio > imgRatio) {
      drawHeight = container.clientHeight
      drawWidth = drawHeight * imgRatio
    } else {
      drawWidth = container.clientWidth
      drawHeight = drawWidth / imgRatio
    }

    canvas.width = drawWidth
    canvas.height = drawHeight
    
    // The scale factor from original image coords to canvas coords
    const scaleX = drawWidth / img.width
    const scaleY = drawHeight / img.height

    ctx.clearRect(0, 0, drawWidth, drawHeight)
    ctx.drawImage(img, 0, 0, drawWidth, drawHeight)

    // Draw OCR Boxes
    ocrFields.forEach(f => {
      if (f.bbox && f.bbox.length === 4) {
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.6)' // Blue
        ctx.lineWidth = 2
        ctx.fillStyle = 'rgba(59, 130, 246, 0.1)'
        
        // Ensure bbox is correctly parsed: might be [[x,y], [x,y], [x,y], [x,y]] or [x1,y1,x2,y2]
        // Phase 4 OCR output usually has 4 points
        if (Array.isArray(f.bbox[0])) {
           ctx.beginPath()
           ctx.moveTo(f.bbox[0][0] * scaleX, f.bbox[0][1] * scaleY)
           ctx.lineTo(f.bbox[1][0] * scaleX, f.bbox[1][1] * scaleY)
           ctx.lineTo(f.bbox[2][0] * scaleX, f.bbox[2][1] * scaleY)
           ctx.lineTo(f.bbox[3][0] * scaleX, f.bbox[3][1] * scaleY)
           ctx.closePath()
           ctx.fill()
           ctx.stroke()
        }
      }
    })

    // Draw Evidence Clusters
    clusters.forEach(c => {
      if (c.bbox && c.bbox.length === 4) {
        const [x1, y1, x2, y2] = c.bbox
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.8)' // Red
        ctx.lineWidth = 3
        ctx.fillStyle = 'rgba(239, 68, 68, 0.2)'
        
        const w = (x2 - x1) * scaleX
        const h = (y2 - y1) * scaleY
        
        ctx.fillRect(x1 * scaleX, y1 * scaleY, w, h)
        ctx.strokeRect(x1 * scaleX, y1 * scaleY, w, h)
        
        // Label
        ctx.fillStyle = 'rgba(239, 68, 68, 0.9)'
        ctx.font = '12px monospace'
        ctx.fillText(`Cluster ${c.signals.join(',')}`, x1 * scaleX, (y1 * scaleY) - 5)
      }
    })
  }

  return (
    <div ref={containerRef} className="w-full h-full flex items-center justify-center">
      <canvas ref={canvasRef} className="shadow-2xl rounded" />
    </div>
  )
}

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { topologyApi } from '../lib/api'
import DiagramViewer from '../components/diagram/DiagramViewer'

export default function TopologyDetail() {
  const { id } = useParams()
  const [showDiagram, setShowDiagram] = useState(true)
  const { data: topology, isLoading, error } = useQuery({
    queryKey: ['topology', id],
    queryFn: () => topologyApi.get(id),
    enabled: !!id,
  })

  if (isLoading) return <div>Loading topology...</div>
  if (error || !topology) return <div>Topology not found. <Link to="/topologies">Back to list</Link></div>

  return (
    <div>
      <h1>Topology: {topology.topology_id}</h1>
      <p style={{ color: '#666' }}>Status: {topology.status} · Nodes: {topology.nodes?.length ?? 0} · Edges: {topology.edges?.length ?? 0}</p>
      <button onClick={() => setShowDiagram(!showDiagram)} style={{ marginBottom: 16, padding: '8px 16px', cursor: 'pointer' }}>
        {showDiagram ? 'Hide' : 'Show'} Diagram
      </button>
      {showDiagram && topology.status === 'COMPLETED' && (
        <div style={{ height: 600, border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <DiagramViewer topologyId={id} />
        </div>
      )}
      <p style={{ marginTop: 16 }}><Link to="/topologies">Back to list</Link></p>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { topologyApi, intentBuilderApi } from '../lib/api'

const ORG_ID = 'default-org'

export default function TopologyList() {
  const { data: topologies = [], isLoading } = useQuery({
    queryKey: ['topologies', ORG_ID],
    queryFn: () => topologyApi.list(ORG_ID, 50),
  })
  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions', ORG_ID],
    queryFn: () => intentBuilderApi.listSessions(ORG_ID, 30),
    retry: false,
  })

  return (
    <div>
      <h1>Projects / Topologies</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>Latest topologies and intent sessions.</p>
      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {topologies.map((t) => (
            <li key={t.topology_id} style={{ padding: 16, marginBottom: 8, border: '1px solid #e5e7eb', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{t.topology_id}</span>
              <span style={{ color: '#6b7280', fontSize: 14 }}>{t.status} · {t.created_at?.slice(0, 10)}</span>
              <Link to={`/topologies/${t.topology_id}`} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', borderRadius: 6, textDecoration: 'none' }}>
                View Diagram
              </Link>
            </li>
          ))}
        </ul>
      )}
      {topologies.length === 0 && !isLoading && (
        <p>No topologies yet. Create one from <Link to="/intent-builder">Intent Builder</Link>.</p>
      )}
    </div>
  )
}

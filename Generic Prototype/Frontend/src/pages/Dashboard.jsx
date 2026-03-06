import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { blockApi, intentSchemaApi, governanceApi } from '../lib/api'

const ORG_ID = 'default-org'

export default function Dashboard() {
  const { data: blocks = [], isLoading: blocksLoading } = useQuery({
    queryKey: ['blocks'],
    queryFn: () => blockApi.list(),
  })
  const { data: schema, isLoading: schemaLoading } = useQuery({
    queryKey: ['schema', ORG_ID],
    queryFn: () => intentSchemaApi.getCurrent(ORG_ID),
    retry: false,
  })
  const { data: pending = [], isLoading: pendingLoading } = useQuery({
    queryKey: ['pending-approvals', ORG_ID],
    queryFn: () => governanceApi.getPendingApprovals(ORG_ID),
    retry: false,
  })

  return (
    <div>
      <h1>Dashboard</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>Intent-Based Architecture Configurator</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
        <Card title="Active Blocks" value={blocksLoading ? '...' : blocks.length} to="/blocks" />
        <Card title="Schema Version" value={schemaLoading ? '...' : (schema?.version ?? '—')} to="/intent-schema" />
        <Card title="Schema Fields" value={schemaLoading ? '...' : (schema?.fields?.length ?? 0)} to="/intent-schema" />
        <Card title="Pending Approvals" value={pendingLoading ? '...' : pending.length} to="/audit" />
      </div>
      <div style={{ marginTop: 32 }}>
        <h2>Quick actions</h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link to="/intent-builder" style={{ padding: '10px 20px', background: '#2563eb', color: '#fff', borderRadius: 8, textDecoration: 'none' }}>
            New Intent Session
          </Link>
          <Link to="/topologies" style={{ padding: '10px 20px', background: '#059669', color: '#fff', borderRadius: 8, textDecoration: 'none' }}>
            View Topologies
          </Link>
          <Link to="/intent-schema" style={{ padding: '10px 20px', background: '#6b7280', color: '#fff', borderRadius: 8, textDecoration: 'none' }}>
            Edit Schema
          </Link>
          <Link to="/blocks" style={{ padding: '10px 20px', background: '#6b7280', color: '#fff', borderRadius: 8, textDecoration: 'none' }}>
            Block Registry
          </Link>
        </div>
      </div>
      {pending.length > 0 && (
        <div style={{ marginTop: 24, padding: 16, background: '#fef3c7', borderRadius: 8 }}>
          <strong>Pending approvals:</strong> {pending.length} — <Link to="/audit">Review</Link>
        </div>
      )}
    </div>
  )
}

function Card({ title, value, to }) {
  return (
    <Link to={to} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div style={{ padding: 20, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff' }}>
        <div style={{ fontSize: 14, color: '#6b7280' }}>{title}</div>
        <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4 }}>{value}</div>
      </div>
    </Link>
  )
}

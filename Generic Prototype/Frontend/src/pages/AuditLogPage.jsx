import { useQuery } from '@tanstack/react-query'
import { governanceApi } from '../lib/api'

const ORG_ID = 'default-org'

export default function AuditLogPage() {
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['audit-logs', ORG_ID],
    queryFn: () => governanceApi.getAuditLogs({ org_id: ORG_ID, limit: 50 }),
    retry: false,
  })
  const { data: pending = [] } = useQuery({
    queryKey: ['pending', ORG_ID],
    queryFn: () => governanceApi.getPendingApprovals(ORG_ID),
    retry: false,
  })

  return (
    <div>
      <h1>Audit Log</h1>
      <p style={{ color: '#666', marginBottom: 16 }}>Org: {ORG_ID}</p>
      {pending.length > 0 && <p style={{ marginBottom: 16, padding: 12, background: '#fef3c7', borderRadius: 8 }}>Pending approvals: {pending.length}</p>}
      {isLoading ? <p>Loading...</p> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Entity</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Action</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Status</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: 8 }}>{l.id}</td>
                <td style={{ padding: 8 }}>{l.entity_type}/{l.entity_id}</td>
                <td style={{ padding: 8 }}>{l.action}</td>
                <td style={{ padding: 8 }}>{l.status}</td>
                <td style={{ padding: 8 }}>{l.created_at?.slice(0, 19)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {logs.length === 0 && !isLoading && <p>No audit logs yet.</p>}
    </div>
  )
}

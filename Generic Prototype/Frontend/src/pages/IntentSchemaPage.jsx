import { useQuery } from '@tanstack/react-query'
import { intentSchemaApi } from '../lib/api'

const ORG_ID = 'default-org'

export default function IntentSchemaPage() {
  const { data: schema, isLoading, error } = useQuery({
    queryKey: ['schema', ORG_ID],
    queryFn: () => intentSchemaApi.getCurrent(ORG_ID),
    retry: false,
  })

  if (isLoading) return <div>Loading...</div>
  if (error || !schema) return <div><h1>Intent Schema</h1><p>No active schema for this org. Create one via API or seed.</p></div>

  return (
    <div>
      <h1>Intent Schema</h1>
      <p style={{ color: '#666' }}>Version: {schema.version} · Org: {schema.org_id}</p>
      <h2>Fields</h2>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {(schema.fields || []).map((f, i) => (
          <li key={i} style={{ padding: 8, marginBottom: 4, background: '#f9fafb', borderRadius: 6 }}>
            {f.field_path || f.path} {f.required ? '(required)' : ''} — {f.field_type || 'string'}
          </li>
        ))}
      </ul>
      {(!schema.fields || schema.fields.length === 0) && <p>No fields defined.</p>}
    </div>
  )
}

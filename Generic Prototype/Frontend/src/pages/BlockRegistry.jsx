import { useQuery } from '@tanstack/react-query'
import { blockApi } from '../lib/api'
import { useState } from 'react'

export default function BlockRegistry() {
  const [category, setCategory] = useState('')
  const { data: allBlocks = [], isLoading } = useQuery({
    queryKey: ['blocks'],
    queryFn: () => blockApi.list(),
  })
  const blocks = category ? allBlocks.filter((b) => b.category === category) : allBlocks
  const categories = [...new Set(allBlocks.map((b) => b.category).filter(Boolean))].sort()

  return (
    <div>
      <h1>Block Registry</h1>
      <p style={{ color: '#666', marginBottom: 16 }}>Architecture blocks from registry.</p>
      <div style={{ marginBottom: 16 }}>
        <label>Category: </label>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ padding: 6, marginLeft: 8 }}>
          <option value="">All</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>
      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
          {blocks.map((b) => (
            <div key={b.block_id} style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff' }}>
              <strong>{b.block_id}</strong>
              <div style={{ fontSize: 14, color: '#6b7280', marginTop: 4 }}>{b.category}</div>
              <div style={{ fontSize: 12, marginTop: 8 }}>v{b.version}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

import { memo } from 'react'

/**
 * VPC / group container node: renders a labeled box that contains child nodes.
 * No connection handles - acts only as a visual container.
 */
function GroupNode({ data, selected }) {
  const label = data?.label ?? 'VPC'
  return (
    <div
      className={`architecture-group-node ${selected ? 'selected' : ''}`}
      style={{ width: '100%', height: '100%' }}
    >
      <div className="architecture-group-node__label">{label}</div>
    </div>
  )
}

export default memo(GroupNode)

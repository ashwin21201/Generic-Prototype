import { memo } from 'react'
import { Handle, Position } from 'reactflow'

/**
 * Architecture node that respects backend semantic shape (shield, cloud, circle, rectangle).
 * Renders connection handles and applies shape-specific styling via data.shape.
 */
function ArchitectureNode({ data, selected }) {
  const label = data?.label ?? ''
  const shape = (data?.shape || 'rectangle').toLowerCase()
  const description = data?.description

  return (
    <>
      <Handle type="target" position={Position.Top} className="architecture-node__handle" />
      <div
        className={`architecture-node architecture-node--${shape} ${selected ? 'selected' : ''}`}
        title={description || label}
      >
        <span className="architecture-node__label">{label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="architecture-node__handle" />
    </>
  )
}

export default memo(ArchitectureNode)

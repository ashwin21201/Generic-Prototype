import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import { resolveShape, resolveCategoryStyle } from './lib/architectureDesignConfig'

/**
 * AWS-style architecture node: category and type drive shape and color.
 * Uses backend shape when provided, otherwise derives from category.
 */
function ArchitectureNode({ data, selected }) {
  const label = data?.label ?? ''
  const description = data?.description
  const category = data?.category || 'compute'
  const shape = resolveShape(data?.shape, category)
  const style = resolveCategoryStyle(category)

  return (
    <>
      <Handle type="target" position={Position.Left} className="architecture-node__handle architecture-node__handle--target" />
      <Handle type="target" position={Position.Top} className="architecture-node__handle architecture-node__handle--target" id="top" />
      <div
        className={`architecture-node architecture-node--${shape} architecture-node--category-${(category || 'compute').toLowerCase()} ${selected ? 'architecture-node--selected' : ''}`}
        title={description || label}
        style={{
          '--arch-fill': style.fill,
          '--arch-border': style.border,
          '--arch-accent': style.accent,
        }}
      >
        <div className="architecture-node__accent" aria-hidden />
        <span className="architecture-node__label">{label}</span>
      </div>
      <Handle type="source" position={Position.Right} className="architecture-node__handle architecture-node__handle--source" />
      <Handle type="source" position={Position.Bottom} className="architecture-node__handle architecture-node__handle--source" id="bottom" />
    </>
  )
}

export default memo(ArchitectureNode)

import { memo } from 'react'

/**
 * AWS-style group/container node for VPC and solution layers.
 * Light fill, clear border, optional layer label.
 */
function GroupNode({ data, selected }) {
  const label = data?.label ?? 'VPC'
  const solutionLayer = data?.solution_layer || (data?.id?.startsWith('layer_') ? data.id.replace('layer_', '') : '')
  const isVpc = data?.id === 'vpc_container' || label === 'VPC'

  return (
    <div
      className={`architecture-group-node ${isVpc ? 'architecture-group-node--vpc' : 'architecture-group-node--layer'} ${selected ? 'architecture-group-node--selected' : ''}`}
      style={{ width: '100%', height: '100%' }}
    >
      <div className="architecture-group-node__header">
        <span className="architecture-group-node__label">{label}</span>
        {solutionLayer && !isVpc && (
          <span className="architecture-group-node__layer-tag">{solutionLayer}</span>
        )}
      </div>
    </div>
  )
}

export default memo(GroupNode)

import { memo } from 'react'
import './GroupNode.css'

function GroupNode({ data, selected }) {
  const isVPC = data.label === 'VPC'
  const layerColors = {
    'Edge': '#3b82f6',
    'Application': '#10b981',
    'Integration': '#8b5cf6',
    'Data': '#f59e0b',
    'Operations': '#ec4899',
  }
  
  const borderColor = isVPC ? '#64748b' : (layerColors[data.label] || '#475569')
  
  return (
    <div
      className={`group-node ${isVPC ? 'vpc-container' : 'layer-container'} ${selected ? 'selected' : ''}`}
      style={{
        borderColor: borderColor,
        backgroundColor: isVPC
          ? 'rgba(15, 23, 42, 0.8)'
          : 'rgba(30, 41, 59, 0.6)',
      }}
    >
      <div
        className="group-label"
        style={{
          color: borderColor,
          borderBottomColor: borderColor,
        }}
      >
        {data.label}
        {data.description && (
          <span className="group-description">{data.description}</span>
        )}
      </div>
    </div>
  )
}

export default memo(GroupNode)

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import {
  FaShieldAlt,
  FaCloud,
  FaServer,
  FaDatabase,
  FaNetworkWired,
  FaCogs,
  FaHdd,
  FaChartLine,
  FaLock,
  FaGlobe,
  FaExchangeAlt,
  FaAws
} from 'react-icons/fa'
import './ArchitectureNode.css'

// Map category to icon
const CATEGORY_ICONS = {
  security: FaShieldAlt,
  network: FaNetworkWired,
  compute: FaServer,
  data: FaDatabase,
  storage: FaHdd,
  messaging: FaExchangeAlt,
  cache: FaServer,
  observability: FaChartLine,
  external: FaGlobe,
}

// Map shape to custom rendering
const SHAPE_CLASSES = {
  shield: 'node-shape-shield',
  cloud: 'node-shape-cloud',
  hexagon: 'node-shape-hexagon',
  cylinder: 'node-shape-cylinder',
  circle: 'node-shape-circle',
  rectangle: 'node-shape-rectangle',
}

// Map provider to icon (using Font Awesome icons for reliability)
const PROVIDER_ICONS = {
  aws: FaAws,
  azure: FaCloud,
  gcp: FaCloud,
}

// Get estimated cost from config
function getNodeCost(config, products) {
  // Simple estimation based on base cost
  if (products && products.length > 0) {
    // In a real scenario, we'd calculate based on product pricing
    // For now, rough estimates
    return null // Will show from architecture level
  }
  return null
}

function ArchitectureNode({ data, isConnectable, selected }) {
  const IconComponent = CATEGORY_ICONS[data.category] || FaCogs
  const shapeClass = SHAPE_CLASSES[data.shape] || SHAPE_CLASSES.rectangle
  
  // Get primary product
  const primaryProduct = data.products?.find(p => p.recommended) || data.products?.[0]
  const ProviderIcon = primaryProduct ? PROVIDER_ICONS[primaryProduct.provider] : null

  // Determine node color based on category
  const getCategoryColor = () => {
    switch (data.category) {
      case 'security':
        return '#ef4444' // red
      case 'network':
        return '#3b82f6' // blue
      case 'compute':
        return '#10b981' // green
      case 'data':
        return '#8b5cf6' // purple
      case 'storage':
        return '#f59e0b' // amber
      case 'messaging':
        return '#ec4899' // pink
      case 'cache':
        return '#14b8a6' // teal
      case 'observability':
        return '#6366f1' // indigo
      case 'external':
        return '#64748b' // slate
      default:
        return '#6b7280' // gray
    }
  }

  const categoryColor = getCategoryColor()

  return (
    <div
      className={`architecture-node ${shapeClass} ${selected ? 'selected' : ''}`}
      style={{
        borderColor: categoryColor,
        boxShadow: selected ? `0 0 0 2px ${categoryColor}` : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={isConnectable}
        className="node-handle"
      />
      
      <div className="node-header">
        <div className="node-icon" style={{ color: categoryColor }}>
          <IconComponent size={18} />
        </div>
        <div className="node-title">
          {data.label}
        </div>
      </div>

      {data.description && (
        <div className="node-description">{data.description}</div>
      )}

      <div className="node-badges">
        {data.region && (
          <span className="node-badge region-badge" title={`Region: ${data.region}`}>
            {data.region}
          </span>
        )}
        {data.semantic_role && (
          <span className="node-badge role-badge" title={`Role: ${data.semantic_role}`}>
            {data.semantic_role.replace(/_/g, ' ')}
          </span>
        )}
        {primaryProduct && ProviderIcon && (
          <span className="node-badge provider-badge" title={primaryProduct.product_name}>
            <ProviderIcon size={12} />
            {primaryProduct.provider.toUpperCase()}
          </span>
        )}
      </div>

      {data.config && (
        <div className="node-config">
          {data.config.cpu_count && (
            <span className="config-item" title="CPU">
              {data.config.cpu_count} vCPU
            </span>
          )}
          {data.config.ram_gb && (
            <span className="config-item" title="RAM">
              {data.config.ram_gb}GB RAM
            </span>
          )}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        isConnectable={isConnectable}
        className="node-handle"
      />
    </div>
  )
}

export default memo(ArchitectureNode)

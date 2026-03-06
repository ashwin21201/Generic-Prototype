import { useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import './ArchitectureDiagram.css'
import GroupNode from './GroupNode'
import ArchitectureNode from './ArchitectureNode'
import { computeElkLayout } from './lib/elkLayout'

/**
 * Map API graph (with backend-computed layout) to ReactFlow nodes/edges.
 * Supports VPC/group container, parent_node/extent, and semantic shape (shield, cloud, circle, etc.).
 */
function mapToReactFlow(graphData) {
  const rawNodes = graphData.nodes || []
  const rawEdges = graphData.edges || []

  const nodes = rawNodes.map((n) => {
    const isGroup = (n.type || n.category) === 'group' || n.id === 'vpc_container'
    const position = n.position && typeof n.position.x === 'number' && typeof n.position.y === 'number'
      ? { x: n.position.x, y: n.position.y }
      : { x: 0, y: 0 }
    const parentNode = n.parent_node ?? n.parentNode ?? undefined
    const extent = n.extent === 'parent' ? 'parent' : undefined

    return {
      id: n.id,
      data: {
        label: (n.data && n.data.label) || (isGroup ? 'VPC' : n.id),
        ...(n.data && n.data.description && { description: n.data.description }),
        category: n.category,
        region: n.region,
        ...(n.resolved_products && { products: n.resolved_products }),
        ...(n.semantic_role && { semantic_role: n.semantic_role }),
        ...(n.placement_type && { placement_type: n.placement_type }),
        shape: n.shape || 'rectangle',
        ...(n.flow_stage != null && { flow_stage: n.flow_stage }),
      },
      position,
      type: isGroup ? 'group' : 'architecture',
      ...(parentNode && { parentNode, extent: extent || 'parent' }),
      ...(isGroup && n.style && {
        style: {
          width: n.style.width,
          height: n.style.height,
          ...n.style,
        },
      }),
    }
  })

  const edges = rawEdges.map((e) => {
    const edgeType = (e.type || 'traffic').toLowerCase()
    const stroke = edgeType === 'data' ? '#16a34a' : edgeType === 'replication' ? '#7c3aed' : '#475569'
    return {
      id: e.id,
      source: e.from ?? e.from_node ?? e.source,
      target: e.to ?? e.target,
      type: 'smoothstep',
      className: `architecture-edge architecture-edge--${edgeType}`,
      style: {
        stroke,
        strokeDasharray: edgeType === 'data' || edgeType === 'replication' ? '5 4' : undefined,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
    }
  })

  return { nodes, edges }
}

export default function ArchitectureDiagram() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [error, setError] = useState(null)
  const [title, setTitle] = useState('Architecture Diagram')
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('logical') // logical | topology

  useEffect(() => {
    const fetchArchitectureData = async () => {
      try {
        setLoading(true)

        // 1) Prefer rich diagram contract (containers/nodes/edges) + ELK layout
        const diagramResp = await fetch(`/api/architecture/diagram?view=${encodeURIComponent(viewMode)}`)
        if (diagramResp.ok) {
          const diagram = await diagramResp.json()
          const hasStruct = Array.isArray(diagram?.containers) && Array.isArray(diagram?.nodes) && Array.isArray(diagram?.edges)
          if (hasStruct) {
            const layout = await computeElkLayout(diagram)
            const rf = mapViewStructToReactFlow(diagram, layout)
            setNodes(rf.nodes)
            setEdges(rf.edges)
            setError(null)
            if (diagram.architecture_id) setTitle(`Architecture: ${diagram.architecture_id}`)
            return
          }
        }

        // 2) Fallback to legacy graph-with-products (backend positions)
        const graphResponse = await fetch(`/api/architecture/graph-with-products?view=${encodeURIComponent(viewMode)}`)
        if (graphResponse.ok) {
          const graphData = await graphResponse.json()
          const { nodes: n, edges: e } = mapToReactFlow(graphData)
          setNodes(n)
          setEdges(e)
          setError(null)
          try {
            const selectedResponse = await fetch('/api/architecture/selected')
            if (selectedResponse.ok) {
              const selected = await selectedResponse.json()
              setTitle(selected.architecture_id ? `Architecture: ${selected.architecture_id}` : 'Architecture Diagram')
            }
          } catch {}
        } else {
          // API not available or no data - fallback to sessionStorage
          const raw = sessionStorage.getItem('architectureResult')
          if (!raw) {
            setError('No architecture data. Generate an architecture from the main app first.')
            return
          }
          const result = JSON.parse(raw)
          setTitle(result.architecture_id ? `Architecture: ${result.architecture_id}` : 'Architecture Diagram')
          // Use resolved_architecture.graph (has backend layout + products); fallback to result.graph
          const graphData =
            result?.views?.[viewMode]?.graph ||
            result.resolved_architecture?.graph ||
            result.graph ||
            {}
          console.groupCollapsed('[Diagram] Loaded graph from sessionStorage fallback')
          console.log('nodes:', graphData?.nodes?.length, 'edges:', graphData?.edges?.length)
          const { nodes: n, edges: e } = mapToReactFlow(graphData)
          console.log('mapped nodes:', n.length, 'mapped edges:', e.length)
          console.groupEnd()
          setNodes(n)
          setEdges(e)
          setError(null)
        }
      } catch (e) {
        console.error('Error loading architecture:', e)
        
        // Final fallback to sessionStorage
        try {
          const raw = sessionStorage.getItem('architectureResult')
          if (raw) {
            const result = JSON.parse(raw)
            setTitle(result.architecture_id ? `Architecture: ${result.architecture_id}` : 'Architecture Diagram')
            const graphData = result.resolved_architecture?.graph || result.graph || {}
            const { nodes: n, edges: e } = mapToReactFlow(graphData)
            setNodes(n)
            setEdges(e)
            setError(null)
          } else {
            setError('Failed to load architecture data. Make sure the backend is running.')
          }
        } catch (fallbackError) {
          setError('Failed to load architecture data.')
          setNodes([])
          setEdges([])
        }
      } finally {
        setLoading(false)
      }
    }

    fetchArchitectureData()
  }, [setNodes, setEdges, viewMode])

  if (loading) {
    return (
      <div className="architecture-diagram-page">
        <div className="architecture-diagram-loading">
          <h1>Loading Architecture...</h1>
          <p>Fetching architecture data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="architecture-diagram-page">
        <div className="architecture-diagram-error">
          <h1>Architecture Diagram</h1>
          <p>{error}</p>
          <a href="/">Back to Questionnaire</a>
        </div>
      </div>
    )
  }

  return (
    <div className="architecture-diagram-page">
      <div className="architecture-diagram-header">
        <h1>{title}</h1>
        <div className="architecture-diagram-header__actions">
          <div className="architecture-diagram-view-toggle">
            <button
              type="button"
              className={viewMode === 'logical' ? 'active' : ''}
              onClick={() => setViewMode('logical')}
            >
              Logical
            </button>
            <button
              type="button"
              className={viewMode === 'topology' ? 'active' : ''}
              onClick={() => setViewMode('topology')}
            >
              Topology
            </button>
          </div>
          <a href="/">← Back to Questionnaire</a>
        </div>
      </div>
      <div className="architecture-diagram-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={{ group: GroupNode, architecture: ArchitectureNode }}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
        >
          <Background variant="dots" gap={16} size={1} />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  )
}

function mapViewStructToReactFlow(viewStruct, layout) {
  const containers = viewStruct?.containers || []
  const nodes = viewStruct?.nodes || []
  const edges = viewStruct?.edges || []

  const containersById = layout?.containersById || {}
  const nodesById = layout?.nodesById || {}

  const rfContainers = containers.map((c) => {
    const pos = containersById[c.id] || { x: 0, y: 0, width: c.style?.width || 240, height: c.style?.height || 120 }
    const parent = c.parent_id || undefined
    const parentPos = parent ? containersById[parent] : null
    const relX = parentPos ? pos.x - parentPos.x : pos.x
    const relY = parentPos ? pos.y - parentPos.y : pos.y
    return {
      id: c.id,
      type: 'group',
      data: { label: c.label || c.id, ...c },
      position: { x: relX, y: relY },
      parentNode: parent,
      extent: parent ? 'parent' : undefined,
      style: { width: pos.width, height: pos.height },
    }
  })

  const rfNodes = nodes.map((n) => {
    const pos = nodesById[n.id] || { x: 0, y: 0, width: n.style?.width || 180, height: n.style?.height || 44 }
    const parent = n.container_id || undefined
    const parentPos = parent ? containersById[parent] : null
    const relX = parentPos ? pos.x - parentPos.x : pos.x
    const relY = parentPos ? pos.y - parentPos.y : pos.y
    return {
      id: n.id,
      type: 'architecture',
      data: { label: n.product_name || n.id, ...n },
      position: { x: relX, y: relY },
      parentNode: parent,
      extent: parent ? 'parent' : undefined,
      style: { width: pos.width, height: pos.height },
    }
  })

  const rfEdges = edges.map((e) => {
    const edgeType = (e.type || 'traffic').toLowerCase()
    const stroke = edgeType === 'data' ? '#16a34a' : edgeType === 'replication' ? '#7c3aed' : '#475569'
    return {
      id: e.id || `e-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      className: `architecture-edge architecture-edge--${edgeType}`,
      style: {
        stroke,
        strokeDasharray: edgeType === 'data' || edgeType === 'replication' ? '5 4' : undefined,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
    }
  })

  return { nodes: [...rfContainers, ...rfNodes], edges: rfEdges }
}

import { useEffect, useState, useCallback } from 'react'
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
import NodeDetailsPanel from './NodeDetailsPanel'
import SearchFilter from './SearchFilter'
import CostDashboard from './CostDashboard'

/**
 * Map API graph (with backend-computed layout) to ReactFlow nodes/edges.
 * Supports VPC/group container, parent_node/extent, and semantic shape (shield, cloud, circle, etc.).
 */
function mapToReactFlow(graphData) {
  const rawNodes = graphData.nodes || []
  const rawEdges = graphData.edges || []

  console.log('🔍 Backend Graph Data:', {
    totalNodes: rawNodes.length,
    samplePositions: rawNodes.slice(0, 5).map(n => ({
      id: n.id,
      position: n.position,
      parent_node: n.parent_node,
      type: n.type
    }))
  })

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
        ...(n.solution_layer && { solution_layer: n.solution_layer }),
        ...(n.network_zone && { network_zone: n.network_zone }),
        ...(n.placement_type && { placement_type: n.placement_type }),
        shape: n.shape || 'rectangle',
        ...(n.flow_stage != null && { flow_stage: n.flow_stage }),
        ...(n.priority != null && { priority: n.priority }),
        ...(n.config && { config: n.config }),
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

  const edges = rawEdges.map((e) => ({
    id: e.id,
    source: e.from ?? e.from_node ?? e.source,
    target: e.to ?? e.target,
    type: 'smoothstep',
    style: { stroke: '#64748b', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
    data: {
      protocol: e.protocol,
      type: e.type,
      replication_mode: e.replication_mode,
    },
    label: e.protocol || e.type,
    labelStyle: { fill: '#94a3b8', fontSize: 10 },
    labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
  }))

  return { nodes, edges }
}

export default function ArchitectureDiagram() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [error, setError] = useState(null)
  const [title, setTitle] = useState('Architecture Diagram')
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('logical') // logical | topology
  const [selectedNode, setSelectedNode] = useState(null)
  const [filteredNodeIds, setFilteredNodeIds] = useState([])
  const [allNodes, setAllNodes] = useState([])
  const [showCostDashboard, setShowCostDashboard] = useState(false)

  // Node types
  const nodeTypes = {
    group: GroupNode,
    architecture: ArchitectureNode,
  }

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    if (node.type !== 'group') {
      setSelectedNode(node)
    }
  }, [])

  // Handle filter changes
  const handleFilterChange = useCallback((nodeIds) => {
    setFilteredNodeIds(nodeIds)
    
    // Update node styles based on filter
    setNodes(prevNodes => prevNodes.map(node => ({
      ...node,
      style: {
        ...node.style,
        opacity: nodeIds.length === 0 || nodeIds.includes(node.id) || node.type === 'group' ? 1 : 0.2,
      }
    })))
  }, [setNodes])

  useEffect(() => {
    const fetchArchitectureData = async () => {
      try {
        setLoading(true)
        
        // Try to fetch from API first (optimized flow)
        const graphResponse = await fetch(`/api/architecture/graph-with-products?view=${encodeURIComponent(viewMode)}`)
        
        if (graphResponse.ok) {
          // API available - use optimized flow
          const graphData = await graphResponse.json()
          console.groupCollapsed('[Diagram] Loaded graph-with-products')
          console.log('nodes:', graphData?.nodes?.length, 'edges:', graphData?.edges?.length)
          const sample = (graphData?.nodes || []).slice(0, 12).map((n) => ({
            id: n.id,
            type: n.type,
            category: n.category,
            parent_node: n.parent_node,
            shape: n.shape,
          }))
          console.table(sample)
          
          // Fetch architecture ID
          try {
            const selectedResponse = await fetch('/api/architecture/selected')
            if (selectedResponse.ok) {
              const selected = await selectedResponse.json()
              setTitle(selected.architecture_id ? `Architecture: ${selected.architecture_id}` : 'Architecture Diagram')
            }
          } catch (e) {
            console.warn('Could not fetch architecture ID:', e)
          }
          
          const { nodes: n, edges: e } = mapToReactFlow(graphData)
          console.log('mapped nodes:', n.length, 'mapped edges:', e.length)
          console.log('groups:', n.filter((x) => x.type === 'group').length, 'parented:', n.filter((x) => !!x.parentNode).length)
          console.groupEnd()
          setNodes(n)
          setAllNodes(n)
          setEdges(e)
          setError(null)
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
          setAllNodes(n)
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
            setAllNodes(n)
            setEdges(e)
            setError(null)
          } else {
            setError('Failed to load architecture data. Make sure the backend is running.')
          }
        } catch (fallbackError) {
          setError('Failed to load architecture data.')
          setNodes([])
          setAllNodes([])
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
          <button
            type="button"
            className={`cost-toggle-button ${showCostDashboard ? 'active' : ''}`}
            onClick={() => setShowCostDashboard(!showCostDashboard)}
            title="Toggle Cost Analysis"
          >
            💰 Cost Analysis
          </button>
          <a href="/">← Back to Questionnaire</a>
        </div>
      </div>
      <div className="architecture-diagram-controls">
        <SearchFilter nodes={allNodes} onFilterChange={handleFilterChange} />
      </div>
      <div className="architecture-diagram-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
        >
          <Background variant="dots" gap={16} size={1} />
          <Controls />
          <MiniMap />
        </ReactFlow>
        {selectedNode && (
          <NodeDetailsPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        )}
        {showCostDashboard && (
          <CostDashboard
            onClose={() => setShowCostDashboard(false)}
          />
        )}
      </div>
    </div>
  )
}

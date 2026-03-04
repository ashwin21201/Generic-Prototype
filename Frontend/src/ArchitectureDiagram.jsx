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

const CATEGORY_ORDER = {
  external: 0,
  security: 1,
  network: 2,
  compute: 3,
  cache: 4,
  messaging: 5,
  data: 6,
  storage: 7,
  observability: 8,
  data_processing: 9,
}

function getCategoryLevel(category) {
  if (category && CATEGORY_ORDER.hasOwnProperty(category)) {
    return CATEGORY_ORDER[category]
  }
  return 10
}

function buildLayout(nodes, edges) {
  const byCategory = {}
  nodes.forEach((n) => {
    const cat = n.category || 'other'
    if (!byCategory[cat]) byCategory[cat] = []
    byCategory[cat].push(n)
  })
  const categoryKeys = Object.keys(byCategory).sort(
    (a, b) => getCategoryLevel(a) - getCategoryLevel(b)
  )
  const positions = {}
  let y = 0
  const xGap = 220
  const yGap = 140
  categoryKeys.forEach((cat) => {
    const list = byCategory[cat]
    const width = list.length * xGap
    let x = -width / 2 + xGap / 2
    list.forEach((n) => {
      positions[n.id] = { x, y }
      x += xGap
    })
    y += yGap
  })
  return positions
}

function mapToReactFlow(graphData) {
  const rawNodes = graphData.nodes || []
  const rawEdges = graphData.edges || []
  const positions = buildLayout(rawNodes, rawEdges)

  const nodes = rawNodes.map((n) => ({
    id: n.id,
    data: {
      label: n.data?.label || n.id,
      ...(n.data?.description && { description: n.data.description }),
      category: n.category,
      region: n.region,
      // Include resolved products if available (for hover info)
      ...(n.resolved_products && { products: n.resolved_products }),
    },
    position: positions[n.id] || { x: 0, y: 0 },
    type: 'default',
  }))

  const edges = rawEdges.map((e) => ({
    id: e.id,
    source: e.from ?? e.from_node ?? e.source,
    target: e.to ?? e.target,
    type: 'smoothstep',
    markerEnd: { type: MarkerType.ArrowClosed },
  }))

  return { nodes, edges }
}

export default function ArchitectureDiagram() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [error, setError] = useState(null)
  const [title, setTitle] = useState('Architecture Diagram')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchArchitectureData = async () => {
      try {
        setLoading(true)
        
        // Try to fetch from API first (optimized flow)
        const graphResponse = await fetch('/api/architecture/graph-with-products')
        
        if (graphResponse.ok) {
          // API available - use optimized flow
          const graphData = await graphResponse.json()
          
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
          setNodes(n)
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
          
          // Extract graph from result
          const graphData = result.graph || {}
          const { nodes: n, edges: e } = mapToReactFlow(graphData)
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
            const graphData = result.graph || {}
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
  }, [setNodes, setEdges])

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
        <a href="/">← Back to Questionnaire</a>
      </div>
      <div className="architecture-diagram-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
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

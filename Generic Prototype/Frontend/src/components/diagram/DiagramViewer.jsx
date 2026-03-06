import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Controls, Background, MiniMap } from 'reactflow'
import 'reactflow/dist/style.css'
import { useQuery } from '@tanstack/react-query'
import { topologyApi } from '../../lib/api'
import ArchitectureNode from '../../ArchitectureNode'
import GroupNode from '../../GroupNode'
import { computeElkLayout } from '../../lib/elkLayout'

const nodeTypes = { architecture: ArchitectureNode, group: GroupNode }

function mapGraphToReactFlow(graph) {
  const nodes = graph?.nodes || []
  const edges = graph?.edges || []
  const rfNodes = nodes.map((n) => ({
    id: n.id,
    type: n.type === 'group' || n.category === 'container' ? 'group' : 'architecture',
    data: { label: n.data?.label ?? n.id, ...n.data, ...n },
    position: { x: n.position?.x ?? 0, y: n.position?.y ?? 0 },
    parentNode: n.parent_node || undefined,
    extent: n.extent || (n.parent_node ? 'parent' : undefined),
    style: n.style ? { width: n.style.width, height: n.style.height } : undefined,
  }))
  const rfEdges = edges.map((e) => ({
    id: e.id || `e-${e.from_node}-${e.to}`,
    source: e.from_node || e.source,
    target: e.to || e.target,
    type: 'smoothstep',
    markerEnd: { type: 'arrowclosed' },
  }))
  return { nodes: rfNodes, edges: rfEdges }
}

function mapViewStructToReactFlow(viewStruct, layout) {
  const containers = viewStruct?.containers || []
  const nodes = viewStruct?.nodes || []
  const edges = viewStruct?.edges || []

  const containersById = layout?.containersById || {}
  const nodesById = layout?.nodesById || {}

  // ReactFlow wants children positions relative to parent
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

  const rfEdges = edges.map((e) => ({
    id: e.id || `e-${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    markerEnd: { type: 'arrowclosed' },
  }))

  return { nodes: [...rfContainers, ...rfNodes], edges: rfEdges }
}

export default function DiagramViewer({ topologyId }) {
  const [view, setView] = useState('logical')
  const [mode, setMode] = useState('default')
  const [rfNodes, setRfNodes] = useState([])
  const [rfEdges, setRfEdges] = useState([])
  const { data: diagramData, isLoading, error } = useQuery({
    queryKey: ['diagram', topologyId, view, mode],
    queryFn: () => topologyApi.getDiagram(topologyId, view, mode),
    enabled: !!topologyId,
  })

  const viewData = useMemo(() => {
    if (!diagramData?.views) return null
    return diagramData.views[view] || diagramData.views.logical
  }, [diagramData, view])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!viewData) {
        setRfNodes([])
        setRfEdges([])
        return
      }

      // Prefer rich view struct (containers/nodes/edges) -> ELK layout
      if (Array.isArray(viewData.containers) && Array.isArray(viewData.nodes) && Array.isArray(viewData.edges)) {
        const layout = await computeElkLayout(viewData)
        if (cancelled) return
        const mapped = mapViewStructToReactFlow(viewData, layout)
        setRfNodes(mapped.nodes)
        setRfEdges(mapped.edges)
        return
      }

      // Fallback: backend graph with positions
      const graph = viewData.graph || viewData
      const mapped = mapGraphToReactFlow(graph)
      if (cancelled) return
      setRfNodes(mapped.nodes)
      setRfEdges(mapped.edges)
    }
    run()
    return () => {
      cancelled = true
    }
  }, [viewData])

  if (isLoading) return <div style={{ padding: 24 }}>Loading diagram...</div>
  if (error) return <div style={{ padding: 24, color: '#dc2626' }}>Failed to load diagram.</div>

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div style={{ position: 'absolute', top: 8, left: 8, zIndex: 5, display: 'flex', gap: 8 }}>
        <button onClick={() => setView('logical')} style={{ padding: '6px 12px', background: view === 'logical' ? '#2563eb' : '#f3f4f6', color: view === 'logical' ? '#fff' : '#111', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          Logical
        </button>
        <button onClick={() => setView('topology')} style={{ padding: '6px 12px', background: view === 'topology' ? '#2563eb' : '#f3f4f6', color: view === 'topology' ? '#fff' : '#111', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          Topology
        </button>
      </div>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.3}
        maxZoom={2}
        style={{ background: '#fff' }}
      >
        <Controls />
        <MiniMap />
        <Background color="#e5e7eb" gap={16} />
      </ReactFlow>
    </div>
  )
}

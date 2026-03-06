import ELK from 'elkjs/lib/elk.bundled.js'

const elk = new ELK()

/**
 * Compute ELK layered layout for a view struct:
 * {
 *   containers: [{id, parent_id, style?}],
 *   nodes: [{id, container_id, style:{width,height}}],
 *   edges: [{id, source, target}]
 * }
 *
 * Returns:
 * { containersById: {id:{x,y,width,height}}, nodesById:{id:{x,y,width,height}}, edges }
 */
export async function computeElkLayout(viewStruct, opts = {}) {
  const containers = viewStruct?.containers || []
  const nodes = viewStruct?.nodes || []
  const edges = viewStruct?.edges || []

  const direction = (viewStruct?.layout_hints?.direction || 'RIGHT').toUpperCase()
  const spacing = viewStruct?.layout_hints?.spacing ?? 40

  // Build container children map
  const childrenByContainer = new Map()
  for (const c of containers) {
    childrenByContainer.set(c.id, [])
  }
  for (const n of nodes) {
    const pid = n.container_id || null
    if (pid && childrenByContainer.has(pid)) {
      childrenByContainer.get(pid).push(n)
    }
  }
  // Containers can be nested (VPC -> layers). Ensure each container is also a child of its parent container.
  for (const c of containers) {
    const pid = c.parent_id || null
    if (pid && childrenByContainer.has(pid)) {
      childrenByContainer.get(pid).push({ __containerRef: c.id })
    }
  }

  // Identify roots (no parent)
  const containerById = new Map(containers.map((c) => [c.id, c]))
  const rootContainers = containers.filter((c) => !c.parent_id)
  const orphanNodes = nodes.filter((n) => !n.container_id)

  // Recursive builder
  function buildContainerElkNode(containerId) {
    const c = containerById.get(containerId)
    const kids = childrenByContainer.get(containerId) || []

    const elkChildren = []
    for (const k of kids) {
      if (k.__containerRef) {
        elkChildren.push(buildContainerElkNode(k.__containerRef))
      } else {
        const w = k.style?.width ?? 180
        const h = k.style?.height ?? 44
        elkChildren.push({ id: k.id, width: w, height: h })
      }
    }

    // Give containers a minimum size so ELK has something to work with.
    const baseW = c?.style?.width ?? 240
    const baseH = c?.style?.height ?? 120

    return {
      id: containerId,
      width: baseW,
      height: baseH,
      children: elkChildren,
      layoutOptions: {
        // Ensure nested containers (e.g., VPC -> layers) respect horizontal logical layout.
        // Root containers (no parent_id) follow the view direction (RIGHT for logical).
        // Nested layer containers stack their internal nodes top-to-bottom for readability.
        'elk.algorithm': 'layered',
        'elk.direction': String(c?.parent_id ? 'DOWN' : direction),
        'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
        'elk.padding': '[top=36,left=24,bottom=24,right=24]',
        'elk.spacing.nodeNode': String(spacing),
        'elk.spacing.edgeNode': String(Math.max(20, spacing / 2)),
      },
    }
  }

  const root = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': direction,
      'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
      // Help ELK take cross-container edges into account.
      'elk.layered.crossingMinimization.hierarchyHandling': 'INCLUDE_CHILDREN',
      'elk.layered.spacing.nodeNodeBetweenLayers': String(spacing),
      'elk.spacing.nodeNode': String(spacing),
      'elk.edgeRouting': 'ORTHOGONAL',
    },
    children: [
      ...rootContainers.map((c) => buildContainerElkNode(c.id)),
      ...orphanNodes.map((n) => ({
        id: n.id,
        width: n.style?.width ?? 180,
        height: n.style?.height ?? 44,
      })),
    ],
    edges: edges
      .filter((e) => e?.source && e?.target)
      .map((e) => ({ id: e.id || `e-${e.source}-${e.target}`, sources: [e.source], targets: [e.target] })),
  }

  const laidOut = await elk.layout(root)

  const containersById = {}
  const nodesById = {}

  function walk(elkNode, parentAbs = { x: 0, y: 0 }) {
    const abs = { x: (elkNode.x || 0) + parentAbs.x, y: (elkNode.y || 0) + parentAbs.y }

    if (containerById.has(elkNode.id)) {
      containersById[elkNode.id] = {
        x: abs.x,
        y: abs.y,
        width: elkNode.width || 240,
        height: elkNode.height || 120,
      }
    } else if (elkNode.id !== 'root') {
      nodesById[elkNode.id] = {
        x: abs.x,
        y: abs.y,
        width: elkNode.width || 180,
        height: elkNode.height || 44,
      }
    }

    for (const child of elkNode.children || []) {
      walk(child, abs)
    }
  }

  walk(laidOut, { x: 0, y: 0 })

  return { containersById, nodesById, edges }
}


/**
 * AWS-style architecture diagram design system.
 * Maps category and type to shape, color, and optional icon label for consistent rendering.
 */

/** Category → shape (aligns with backend CATEGORY_SHAPES; fallback when shape not provided) */
export const CATEGORY_TO_SHAPE = {
  external: 'cloud',
  network: 'rectangle',
  security: 'shield',
  compute: 'rectangle',
  messaging: 'hexagon',
  cache: 'rectangle',
  data: 'cylinder',
  storage: 'cylinder',
  observability: 'circle',
  data_processing: 'rectangle',
  container: 'rectangle',
}

/** Category → AWS-inspired accent color (border, icon strip). Hex values for CSS. */
export const CATEGORY_TO_COLOR = {
  external: { fill: '#f1f5f9', border: '#94a3b8', accent: '#64748b', label: 'External' },
  network: { fill: '#eff6ff', border: '#3b82f6', accent: '#2563eb', label: 'Networking' },
  security: { fill: '#fff1f2', border: '#e11d48', accent: '#be123c', label: 'Security' },
  compute: { fill: '#fff7ed', border: '#ea580c', accent: '#c2410c', label: 'Compute' },
  messaging: { fill: '#faf5ff', border: '#7c3aed', accent: '#6d28d9', label: 'Integration' },
  cache: { fill: '#f0fdf4', border: '#16a34a', accent: '#15803d', label: 'Cache' },
  data: { fill: '#f0fdf4', border: '#15803d', accent: '#166534', label: 'Database' },
  storage: { fill: '#ecfdf5', border: '#059669', accent: '#047857', label: 'Storage' },
  observability: { fill: '#fefce8', border: '#ca8a04', accent: '#a16207', label: 'Operations' },
  data_processing: { fill: '#f0fdf4', border: '#16a34a', accent: '#15803d', label: 'Data' },
  container: { fill: '#f8fafc', border: '#94a3b8', accent: '#64748b', label: 'Container' },
}

/** Shape precedence: backend may send shape; we fallback to category. */
export function resolveShape(shapeFromBackend, category) {
  const s = (shapeFromBackend || '').toLowerCase()
  if (['rectangle', 'shield', 'cloud', 'circle', 'hexagon', 'cylinder'].includes(s)) return s
  const cat = (category || '').toLowerCase()
  return CATEGORY_TO_SHAPE[cat] || 'rectangle'
}

/** Resolve design (color + label) for a node. */
export function resolveCategoryStyle(category) {
  const cat = (category || 'compute').toLowerCase()
  return CATEGORY_TO_COLOR[cat] || CATEGORY_TO_COLOR.compute
}

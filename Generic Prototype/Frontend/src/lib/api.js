/**
 * API client for configurator backend. Base URL uses proxy /api -> backend.
 */
const BASE = '/api'

async function request(method, path, body = null) {
  const opts = { method, headers: {} }
  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json().catch(() => ({}))
}

const intentSchemaApi = {
  getCurrent: (orgId) => request('GET', `/v1/intent-schema/?org_id=${encodeURIComponent(orgId)}`),
  getVersions: (orgId) => request('GET', `/v1/intent-schema/versions?org_id=${encodeURIComponent(orgId)}`),
  create: (body) => request('POST', '/v1/intent-schema/', body),
  validate: (body) => request('POST', '/v1/intent-schema/validate', body),
}

const intentBuilderApi = {
  listSessions: (orgId, limit = 50) => request('GET', `/v1/intent-builder/sessions?org_id=${encodeURIComponent(orgId)}&limit=${limit}`),
  createSession: (body) => request('POST', '/v1/intent-builder/sessions', body),
  getSession: (sessionId) => request('GET', `/v1/intent-builder/sessions/${sessionId}`),
  startChat: (sessionId) => request('POST', `/v1/intent-builder/sessions/${sessionId}/start-chat`),
  chat: (sessionId, message) => request('POST', `/v1/intent-builder/sessions/${sessionId}/chat`, { message }),
  submitIntent: (sessionId, opts = {}) => request('POST', `/v1/intent-builder/sessions/${sessionId}/submit`, { finalize: true, ...opts }),
  truncateHistory: (sessionId, keepCount) => request('POST', `/v1/intent-builder/sessions/${sessionId}/truncate`, { keep_history_count: keepCount }),
}

const topologyApi = {
  list: (orgId, limit = 50) => request('GET', `/v1/topologies?org_id=${encodeURIComponent(orgId)}&limit=${limit}`),
  get: (topologyId) => request('GET', `/v1/topologies/${topologyId}`),
  generate: (body) => request('POST', '/v1/topologies', body),
  getDiagram: (topologyId, view = 'logical', mode = 'default') =>
    request('GET', `/v1/diagram/topologies/${topologyId}/diagram?view=${view}&mode=${mode}`),
  addBlock: (topologyId, body) => request('POST', `/v1/topologies/${topologyId}/blocks`, body),
  removeBlock: (topologyId, nodeId) => request('DELETE', `/v1/topologies/${topologyId}/blocks/${nodeId}`),
  editSpec: (topologyId, nodeId, spec) => request('PATCH', `/v1/topologies/${topologyId}/blocks/${nodeId}/spec`, spec),
  addEdge: (topologyId, body) => request('POST', `/v1/topologies/${topologyId}/edges`, body),
  saveLayout: (topologyId, body) => request('PUT', `/v1/topologies/${topologyId}/layout`, body),
}

const blockApi = {
  list: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request('GET', `/v1/blocks/${q ? '?' + q : ''}`)
  },
  get: (blockId) => request('GET', `/v1/blocks/${blockId}`),
  create: (body) => request('POST', '/v1/blocks/', body),
  update: (blockId, body) => request('PUT', `/v1/blocks/${blockId}`, body),
  deactivate: (blockId) => request('DELETE', `/v1/blocks/${blockId}`),
}

const policyApi = {
  list: (orgId, level) => request('GET', `/v1/policies?org_id=${encodeURIComponent(orgId)}${level ? '&level=' + level : ''}`),
  get: (policyId) => request('GET', `/v1/policies/${policyId}`),
  create: (body) => request('POST', '/v1/policies/', body),
  update: (policyId, body) => request('PUT', `/v1/policies/${policyId}`, body),
  delete: (policyId) => request('DELETE', `/v1/policies/${policyId}`),
}

const impactAnalysisApi = {
  analyzeFieldChange: (body) => request('POST', '/v1/impact-analysis/analyze-field-change', body),
  canSaveChange: (body) => request('POST', '/v1/impact-analysis/can-save-change', body),
  autoUpdateFieldRename: (body) => request('POST', '/v1/impact-analysis/auto-update-field-rename', body),
}

const governanceApi = {
  getAuditLogs: (params) => request('GET', `/v1/governance/audit-logs?${new URLSearchParams(params).toString()}`),
  getPendingApprovals: (orgId) => request('GET', `/v1/governance/audit-logs/pending?org_id=${encodeURIComponent(orgId)}`),
  approve: (logId, body) => request('POST', `/v1/governance/audit-logs/${logId}/approve`, body),
  reject: (logId, body) => request('POST', `/v1/governance/audit-logs/${logId}/reject`, body),
  rollbackSchema: (orgId, body) => request('POST', `/v1/governance/schemas/${orgId}/rollback`, body),
}

export {
  intentSchemaApi,
  intentBuilderApi,
  topologyApi,
  blockApi,
  policyApi,
  impactAnalysisApi,
  governanceApi,
}

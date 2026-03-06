import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { intentBuilderApi, topologyApi } from '../lib/api'

const ORG_ID = 'default-org'
const PROJECT_ID = 'default-project'

export default function IntentBuilder() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [sessionId, setSessionId] = useState(location.state?.sessionId || null)
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [suggestedOptions, setSuggestedOptions] = useState([])
  const [intentJson, setIntentJson] = useState({})
  const [completeness, setCompleteness] = useState(null)
  const [readyToSubmit, setReadyToSubmit] = useState(false)
  const [topoError, setTopoError] = useState(null)
  const [isBotTyping, setIsBotTyping] = useState(false)

  const createSession = useMutation({
    mutationFn: () => intentBuilderApi.createSession({ org_id: ORG_ID, project_id: PROJECT_ID }),
    onSuccess: (data) => {
      setSessionId(data.id)
      startChat.mutate(data.id)
    },
  })

  const startChat = useMutation({
    mutationFn: (id) => intentBuilderApi.startChat(id),
    onSuccess: (data) => {
      setSuggestedOptions(data.suggested_options || [])
      setCompleteness(data.completeness)
      setMessages((prev) => (prev.length === 0 && data.bot_message ? [{ role: 'assistant', content: data.bot_message }] : prev))
      setReadyToSubmit(!!(data.completeness?.is_complete))
    },
  })

  const sessionQuery = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => intentBuilderApi.getSession(sessionId),
    enabled: !!sessionId,
  })

  useEffect(() => {
    if (!sessionId) {
      createSession.mutate()
    }
  }, [])

  useEffect(() => {
    if (sessionId && sessionQuery.data && !sessionQuery.isFetching) {
      const s = sessionQuery.data
      setIntentJson(s.inferred_intent || {})
      if (s.conversation_history?.length) {
        const msgs = s.conversation_history.filter((m, i) => !(i === 0 && m.role === 'user' && m.content?.includes('Hello')))
        setMessages(msgs)
      }
    }
  }, [sessionId, sessionQuery.data, sessionQuery.isFetching])

  const chatMutation = useMutation({
    mutationFn: ({ id, msg }) => intentBuilderApi.chat(id, msg),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.bot_message }])
      setSuggestedOptions(data.suggested_options || [])
      setCompleteness(data.completeness)
      setReadyToSubmit(!!(data.completeness?.is_complete))
      setIsBotTyping(false)
      if (data.intent_updates && Object.keys(data.intent_updates).length) {
        setIntentJson((prev) => merge(prev, data.intent_updates))
      }
    },
    onError: () => setIsBotTyping(false),
  })

  const submitMutation = useMutation({
    mutationFn: async () => {
      const submitRes = await intentBuilderApi.submitIntent(sessionId, { finalize: true })
      const intent = submitRes.intent_json || intentJson
      return topologyApi.generate({
        intent_json: intent,
        project_id: PROJECT_ID,
        org_id: ORG_ID,
        schema_version: null,
        session_id: sessionId,
      })
    },
    onSuccess: (data) => {
      setTopoError(null)
      navigate(`/topologies/${data.topology_id}`, { state: { sessionId } })
    },
    onError: (err) => setTopoError(err.message),
  })

  const sendMessage = (text) => {
    const msg = text || inputText.trim()
    if (!msg || isBotTyping) return
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setInputText('')
    setIsBotTyping(true)
    chatMutation.mutate({ id: sessionId, msg })
  }

  if (!sessionId && createSession.isPending) {
    return <div>Creating session...</div>
  }

  return (
    <div>
      <h1>Intent Builder</h1>
      {completeness && (
        <div style={{ marginBottom: 16 }}>
          Completeness: {Math.round((completeness.score ?? 0) * 100)}%
          {completeness.is_complete && <span style={{ marginLeft: 8, color: 'green' }}>Ready to submit</span>}
        </div>
      )}
      <div style={{ maxWidth: 720, marginBottom: 24 }}>
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, minHeight: 320, maxHeight: 420, overflow: 'auto' }}>
          {messages.map((m, i) => (
            <div key={i} style={{ textAlign: m.role === 'user' ? 'right' : 'left', marginBottom: 12 }}>
              <span style={{ padding: '8px 12px', borderRadius: 8, background: m.role === 'user' ? '#2563eb' : '#f3f4f6', color: m.role === 'user' ? '#fff' : '#111', display: 'inline-block', maxWidth: '85%' }}>
                {m.content}
              </span>
            </div>
          ))}
        </div>
        {suggestedOptions.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
            {suggestedOptions.map((opt, i) => (
              <button key={i} onClick={() => sendMessage(opt)} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' }}>
                {opt}
              </button>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your answer..."
            style={{ flex: 1, padding: 10, borderRadius: 6, border: '1px solid #d1d5db' }}
            disabled={isBotTyping}
          />
          <button onClick={() => sendMessage()} disabled={isBotTyping} style={{ padding: '10px 20px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
            Send
          </button>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <details>
          <summary>Live intent JSON</summary>
          <pre style={{ background: '#f9fafb', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200 }}>
            {JSON.stringify(intentJson, null, 2)}
          </pre>
        </details>
      </div>
      {readyToSubmit && (
        <div style={{ marginTop: 24 }}>
          <button
            onClick={() => submitMutation.mutate()}
            disabled={submitMutation.isPending}
            style={{ padding: '12px 24px', background: '#059669', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 16 }}
          >
            {submitMutation.isPending ? 'Generating...' : 'Submit & Generate Architecture'}
          </button>
          {topoError && <p style={{ color: '#dc2626', marginTop: 8 }}>{topoError}</p>}
        </div>
      )}
    </div>
  )
}

function merge(obj, updates) {
  const out = JSON.parse(JSON.stringify(obj || {}))
  for (const [path, value] of Object.entries(updates || {})) {
    const keys = path.split('.')
    let cur = out
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i]
      if (!(k in cur)) cur[k] = {}
      cur = cur[k]
    }
    cur[keys[keys.length - 1]] = value
  }
  return out
}

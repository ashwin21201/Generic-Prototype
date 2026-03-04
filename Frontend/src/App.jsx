import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [questionCount, setQuestionCount] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [architectureResult, setArchitectureResult] = useState(null)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const messagesEndRef = useRef(null)
  const architecturePanelRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const initialMessage = {
      role: 'assistant',
      content: 'Welcome! I\'ll help you design your cloud architecture by asking up to 12 questions.\n\nLet\'s start:\n\nWhat industry is this project in?\nA) BFSI\nB) Healthcare\nC) E-commerce\nD) SaaS / Technology\nE) Other'
    }
    setMessages([initialMessage])
  }, [])

  const sendMessage = async (e, directContent = null) => {
    if (e) e.preventDefault()
    
    const content = directContent || input.trim()
    if (!content || isLoading || isComplete) return

    const userMessage = { role: 'user', content }
    const newMessages = [...messages, userMessage]
    
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: newMessages }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      const assistantMessage = data.choices[0].message
      
      // Check if the response is JSON (final output)
      let isJsonResponse = false
      let cleanContent = assistantMessage.content.trim()
      
      // Remove markdown code blocks if present
      if (cleanContent.startsWith('```json')) {
        cleanContent = cleanContent.replace(/```json\n?/g, '').replace(/```/g, '').trim()
      } else if (cleanContent.startsWith('```')) {
        cleanContent = cleanContent.replace(/```\n?/g, '').trim()
      }
      
      try {
        const parsed = JSON.parse(cleanContent)
        // Check if it has the expected structure (request_metadata indicates it's the final JSON)
        if (parsed.request_metadata || parsed.functional_requirements) {
          isJsonResponse = true
        }
      } catch {
        // Not JSON, it's a regular question
      }

      if (isJsonResponse) {
        // JSON detected - don't show in chat
        setIsComplete(true)
        // Auto-save intent to backend so "Generate Architecture" works without clicking "View JSON"
        try {
          await fetch('/api/intent-json', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: assistantMessage.content })
          })
        } catch (e) {
          console.warn('Failed to auto-save intent to backend', e)
        }
        // Show success message in chat with view button
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `✅ Complete! Your Architecture Intent has been generated successfully.\n\nClick below to view the JSON or generate the architecture.`,
            isSuccess: true,
            jsonContent: assistantMessage.content
          }
        ])
      } else {
        // Regular question - add to chat
        setMessages((prev) => [...prev, assistantMessage])
        setQuestionCount((prev) => prev + 1)
      }
    } catch (error) {
      console.error('Error communicating with backend:', error)
      setMessages((prev) => [
        ...prev, 
        { 
          role: 'assistant', 
          content: '⚠️ Connection error. Make sure the FastAPI backend is running on http://localhost:8000' 
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const isJSON = (str) => {
    try {
      JSON.parse(str)
      return true
    } catch {
      return false
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  const parseOptions = (content) => {
    const optionRegex = /^([A-E])\)\s*(.+)$/gm
    const options = []
    let match
    
    while ((match = optionRegex.exec(content)) !== null) {
      options.push({
        letter: match[1],
        text: match[2].trim()
      })
    }
    
    return options.length > 0 ? options : null
  }

  const removeOptionsFromContent = (content) => {
    return content.replace(/^([A-E])\)\s*.+$/gm, '').trim()
  }

  const viewIntentJson = async (jsonContent) => {
    try {
      // First, POST the JSON to the backend
      const response = await fetch('/api/intent-json', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: jsonContent }),
      })

      if (!response.ok) {
        throw new Error(`Failed to save: ${response.status}`)
      }

      // Then redirect to the GET endpoint to view it
      window.open('/api/intent-json', '_blank')
    } catch (error) {
      console.error('Error viewing intent:', error)
      alert('Failed to load JSON')
    }
  }

  const handleOptionClick = (option) => {
    sendMessage(null, option.text)
  }

  const synthesizeArchitecture = async () => {
    setIsSynthesizing(true)
    try {
      const response = await fetch('/api/synthesize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setArchitectureResult(data)
      sessionStorage.setItem('architectureResult', JSON.stringify(data))
      window.open('/architecture', '_blank')
      setTimeout(() => {
        architecturePanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    } catch (error) {
      console.error('Error synthesizing architecture:', error)
      alert('Failed to synthesize architecture. Make sure the backend is running.')
    } finally {
      setIsSynthesizing(false)
    }
  }

  return (
    <div className={`app-container ${architectureResult ? 'has-architecture' : ''}`}>
      <div className="chat-wrapper">
        <header className="chat-header">
          <div className="header-content">
            <h1 className="title">
              <span className="icon">🏗️</span>
              Architecture Discovery Agent
            </h1>
            <p className="subtitle">
              AI-powered questionnaire to generate your cloud architecture specification
            </p>
          </div>
          <div className="status-badges">
            <div className="badge badge-live">
              <span className="pulse-dot"></span>
              Claude AI
            </div>
            {!isComplete && (
              <div className="badge badge-progress">
                Question {questionCount + 1} / 12
              </div>
            )}
            {isComplete && (
              <div className="badge badge-success">
                ✓ Complete
              </div>
            )}
          </div>
        </header>

        <div className="chat-container">
          <div className="messages-container">
            {messages.map((msg, index) => {
              const isJson = isJSON(msg.content)
              const options = msg.role === 'assistant' && !isJson && !msg.isSuccess ? parseOptions(msg.content) : null
              const isLastMessage = index === messages.length - 1
              const displayContent = options ? removeOptionsFromContent(msg.content) : msg.content
              
              return (
                <div key={index} className={`message-wrapper ${msg.role}`}>
                  <div className={`message ${isJson ? 'json-message' : ''} ${msg.isSuccess ? 'success-message' : ''}`}>
                    {msg.isSuccess ? (
                      <>
                        <div className="message-content">{displayContent}</div>
                        {msg.jsonContent && (
                          <div className="action-buttons">
                            <button
                              className="view-json-btn"
                              onClick={() => viewIntentJson(msg.jsonContent)}
                            >
                              📄 View JSON
                            </button>
                            <button
                              className="synthesize-btn"
                              onClick={synthesizeArchitecture}
                              disabled={isSynthesizing}
                            >
                              {isSynthesizing ? '⏳ Generating...' : '🏗️ Generate Architecture'}
                            </button>
                          </div>
                        )}
                      </>
                    ) : isJson ? (
                      <div className="json-container">
                        <div className="json-header">
                          <span className="json-title">📋 Architecture Intent JSON</span>
                          <button 
                            className="copy-btn"
                            onClick={() => copyToClipboard(msg.content)}
                          >
                            📋 Copy
                          </button>
                        </div>
                        <pre className="json-content">
                          {JSON.stringify(JSON.parse(msg.content), null, 2)}
                        </pre>
                      </div>
                    ) : (
                      <>
                        <div className="message-content">{displayContent}</div>
                        {options && isLastMessage && !isLoading && (
                          <div className="options-container">
                            {options.map((option) => (
                              <button
                                key={option.letter}
                                className="option-button"
                                onClick={() => handleOptionClick(option)}
                              >
                                <span className="option-letter">{option.letter}</span>
                                <span className="option-text">{option.text}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )
            })}
            
            {isLoading && (
              <div className="message-wrapper assistant">
                <div className="message loading-message">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="loading-text">Agent is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="input-container" onSubmit={sendMessage}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isComplete ? "Session complete" : "Type your answer..."}
              disabled={isLoading || isComplete}
              className="message-input"
            />
            <button 
              type="submit" 
              disabled={isLoading || !input.trim() || isComplete}
              className="send-button"
            >
              {isLoading ? '⏳' : '➤'}
            </button>
          </form>

          {!isComplete && (
            <div className="helper-text">
              💡 Answer one question at a time. The agent will guide you through the process.
            </div>
          )}
        </div>
      </div>

      {architectureResult && (
        <div className="architecture-panel" ref={architecturePanelRef}>
          <div className="architecture-header">
            <h2>🏗️ Generated Architecture</h2>
            <span className="architecture-id">ID: {architectureResult.architecture_id}</span>
          </div>

          <div className="architecture-sections">
            {/* Selected Blocks */}
            <div className="section">
              <h3>📦 Selected Blocks ({(architectureResult.selected_architecture?.selected_blocks ?? []).length})</h3>
              <div className="blocks-grid">
                {(architectureResult.selected_architecture?.selected_blocks ?? []).map((block, idx) => (
                  <div key={idx} className="block-card">
                    {block.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                ))}
              </div>
            </div>

            {/* Deployment Topology */}
            <div className="section">
              <h3>🌍 Deployment Topology</h3>
              <div className="topology-info">
                <div className="info-item">
                  <span className="label">Regions:</span>
                  <span className="value">{(architectureResult.selected_architecture?.deployment_topology?.regions ?? []).join(', ') || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Multi-AZ:</span>
                  <span className="value">{architectureResult.selected_architecture?.deployment_topology?.multi_az ? 'Yes' : 'No'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Replication:</span>
                  <span className="value">{architectureResult.selected_architecture?.deployment_topology?.replication_required ? 'Active-Active' : 'None'}</span>
                </div>
              </div>
            </div>

            {/* Graph Topology */}
            <div className="section">
              <h3>🔗 Graph Topology</h3>
              <div className="graph-stats">
                <div className="stat-card">
                  <div className="stat-value">{(architectureResult.graph?.nodes ?? []).length}</div>
                  <div className="stat-label">Nodes</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{(architectureResult.graph?.edges ?? []).length}</div>
                  <div className="stat-label">Connections</div>
                </div>
              </div>
              <div className="nodes-list">
                {(architectureResult.graph?.nodes ?? []).slice(0, 10).map((node, idx) => (
                  <div key={idx} className="node-item">
                    <span className="node-id">{node.id}</span>
                    <span className="node-category">{node.category}</span>
                    {node.region && <span className="node-region">{node.region}</span>}
                  </div>
                ))}
                {(architectureResult.graph?.nodes ?? []).length > 10 && (
                  <div className="more-items">+ {(architectureResult.graph?.nodes ?? []).length - 10} more nodes</div>
                )}
              </div>
            </div>

            {/* Compliance Report */}
            <div className="section">
              <h3>✅ Compliance Report</h3>
              <div className={`compliance-status ${architectureResult.compliance_report?.compliance_status ?? 'unknown'}`}>
                <span className="status-icon">
                  {architectureResult.compliance_report?.compliance_status === 'compliant' ? '✓' : '⚠'}
                </span>
                <span className="status-text">
                  {(architectureResult.compliance_report?.compliance_status ?? 'unknown').toUpperCase()}
                </span>
                <span className="risk-score">
                  Risk Score: {architectureResult.compliance_report?.risk_score ?? '—'}
                </span>
              </div>
              <div className="compliance-details">
                <div className="detail-item">
                  <span className="label">Sector:</span>
                  <span className="value">{architectureResult.compliance_report?.sector ?? '—'}</span>
                </div>
                <div className="detail-item">
                  <span className="label">Checks Performed:</span>
                  <span className="value">{(architectureResult.compliance_report?.checks ?? []).length}</span>
                </div>
                {(architectureResult.compliance_report?.violations ?? []).length > 0 && (
                  <div className="violations">
                    <h4>Violations ({(architectureResult.compliance_report?.violations ?? []).length})</h4>
                    {(architectureResult.compliance_report?.violations ?? []).map((violation, idx) => (
                      <div key={idx} className="violation-item">
                        <span className="severity">{violation.severity}</span>
                        <span className="violation-message">{violation.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Cost Estimate */}
            <div className="section">
              <h3>💰 Cost Estimate</h3>
              <div className="cost-display">
                <div className="cost-amount">
                  ${Number(architectureResult.resolved_architecture?.estimated_monthly_cost_usd ?? 0).toLocaleString()}
                </div>
                <div className="cost-label">per month</div>
              </div>
              <div className="scoring-summary">
                <h4>Scoring Summary</h4>
                <div className="scores-grid">
                  <div className="score-item">
                    <span className="score-label">Performance</span>
                    <span className="score-value">{((architectureResult.selected_architecture?.scoring_summary?.performance_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Cost</span>
                    <span className="score-value">{((architectureResult.selected_architecture?.scoring_summary?.cost_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Compliance</span>
                    <span className="score-value">{((architectureResult.selected_architecture?.scoring_summary?.compliance_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Simplicity</span>
                    <span className="score-value">{((architectureResult.selected_architecture?.scoring_summary?.simplicity_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Warnings */}
            {architectureResult.warnings && architectureResult.warnings.length > 0 && (
              <div className="section warnings-section">
                <h3>⚠️ Warnings</h3>
                {architectureResult.warnings.map((warning, idx) => (
                  <div key={idx} className="warning-item">
                    <span className="warning-severity">{warning.severity}</span>
                    <span className="warning-message">{warning.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App

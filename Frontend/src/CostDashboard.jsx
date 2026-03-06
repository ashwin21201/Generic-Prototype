import { useState, useEffect } from 'react'
import { FaDollarSign, FaChartPie, FaLightbulb, FaTimes, FaMapMarkerAlt, FaLayerGroup, FaTag } from 'react-icons/fa'
import './CostDashboard.css'

function CostDashboard({ onClose }) {
  const [costData, setCostData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchCostAnalysis()
  }, [])

  const fetchCostAnalysis = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/architecture/cost-analysis')
      
      if (!response.ok) {
        throw new Error('Failed to fetch cost analysis')
      }
      
      const data = await response.json()
      setCostData(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching cost analysis:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="cost-dashboard">
        <div className="cost-dashboard-header">
          <h2>Cost Analysis</h2>
          <button className="close-button" onClick={onClose}>
            <FaTimes />
          </button>
        </div>
        <div className="cost-dashboard-loading">
          <p>Loading cost analysis...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="cost-dashboard">
        <div className="cost-dashboard-header">
          <h2>Cost Analysis</h2>
          <button className="close-button" onClick={onClose}>
            <FaTimes />
          </button>
        </div>
        <div className="cost-dashboard-error">
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (!costData) {
    return null
  }

  return (
    <div className="cost-dashboard">
      <div className="cost-dashboard-header">
        <h2>
          <FaDollarSign /> Cost Analysis
        </h2>
        <button className="close-button" onClick={onClose} title="Close">
          <FaTimes />
        </button>
      </div>

      <div className="cost-dashboard-content">
        {/* Total Cost Summary */}
        <section className="cost-section summary-section">
          <div className="cost-summary-grid">
            <div className="cost-summary-card">
              <div className="cost-label">Monthly Cost</div>
              <div className="cost-value primary">
                ${costData.total_monthly_cost_usd.toLocaleString()}
              </div>
            </div>
            <div className="cost-summary-card">
              <div className="cost-label">Annual Cost</div>
              <div className="cost-value secondary">
                ${costData.estimated_annual_cost_usd.toLocaleString()}
              </div>
            </div>
          </div>
        </section>

        {/* Cost Drivers */}
        {costData.cost_drivers && costData.cost_drivers.length > 0 && (
          <section className="cost-section">
            <h3>
              <FaChartPie /> Top Cost Drivers
            </h3>
            <div className="cost-drivers-list">
              {costData.cost_drivers.map((driver, idx) => (
                <div key={idx} className="cost-driver-item">
                  <div className="driver-info">
                    <div className="driver-name">{driver.node_label}</div>
                    <div className="driver-category">{driver.category}</div>
                  </div>
                  <div className="driver-cost">
                    <div className="cost-amount">
                      ${driver.monthly_cost_usd.toLocaleString()}
                    </div>
                    <div className="cost-percentage">{driver.percentage_of_total}%</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Breakdown by Layer */}
        {costData.breakdown_by_layer && Object.keys(costData.breakdown_by_layer).length > 0 && (
          <section className="cost-section">
            <h3>
              <FaLayerGroup /> Cost by Layer
            </h3>
            <div className="cost-breakdown-list">
              {Object.entries(costData.breakdown_by_layer)
                .sort(([, a], [, b]) => b - a)
                .map(([layer, cost]) => (
                  <div key={layer} className="breakdown-item">
                    <div className="breakdown-label">{layer}</div>
                    <div className="breakdown-bar">
                      <div
                        className="breakdown-fill"
                        style={{
                          width: `${(cost / costData.total_monthly_cost_usd) * 100}%`,
                        }}
                      />
                    </div>
                    <div className="breakdown-value">${cost.toLocaleString()}</div>
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* Breakdown by Category */}
        {costData.breakdown_by_category && Object.keys(costData.breakdown_by_category).length > 0 && (
          <section className="cost-section">
            <h3>
              <FaTag /> Cost by Category
            </h3>
            <div className="cost-breakdown-list">
              {Object.entries(costData.breakdown_by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([category, cost]) => (
                  <div key={category} className="breakdown-item">
                    <div className="breakdown-label">{category}</div>
                    <div className="breakdown-bar">
                      <div
                        className="breakdown-fill"
                        style={{
                          width: `${(cost / costData.total_monthly_cost_usd) * 100}%`,
                        }}
                      />
                    </div>
                    <div className="breakdown-value">${cost.toLocaleString()}</div>
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* Breakdown by Region */}
        {costData.breakdown_by_region && Object.keys(costData.breakdown_by_region).length > 0 && (
          <section className="cost-section">
            <h3>
              <FaMapMarkerAlt /> Cost by Region
            </h3>
            <div className="cost-breakdown-list">
              {Object.entries(costData.breakdown_by_region)
                .sort(([, a], [, b]) => b - a)
                .map(([region, cost]) => (
                  <div key={region} className="breakdown-item">
                    <div className="breakdown-label">{region}</div>
                    <div className="breakdown-bar">
                      <div
                        className="breakdown-fill"
                        style={{
                          width: `${(cost / costData.total_monthly_cost_usd) * 100}%`,
                        }}
                      />
                    </div>
                    <div className="breakdown-value">${cost.toLocaleString()}</div>
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* Optimization Suggestions */}
        {costData.optimization_suggestions && costData.optimization_suggestions.length > 0 && (
          <section className="cost-section">
            <h3>
              <FaLightbulb /> Optimization Recommendations
            </h3>
            <div className="optimizations-list">
              {costData.optimization_suggestions.map((opt, idx) => (
                <div key={idx} className="optimization-item">
                  <div className="optimization-header">
                    <div className="optimization-title">{opt.title}</div>
                    <div className="optimization-savings">
                      Save ${opt.potential_savings_usd.toLocaleString()}/mo
                    </div>
                  </div>
                  <div className="optimization-description">{opt.description}</div>
                  <div className="optimization-meta">
                    <span className="meta-badge impact">Impact: {opt.impact}</span>
                    <span className="meta-badge effort">Effort: {opt.effort}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export default CostDashboard

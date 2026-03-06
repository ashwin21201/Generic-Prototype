import { memo } from 'react'
import { FaTimes, FaServer, FaMemory, FaHdd, FaMapMarkerAlt, FaLayerGroup, FaTag, FaAws, FaCloud } from 'react-icons/fa'
import './NodeDetailsPanel.css'

const PROVIDER_ICONS = {
  aws: FaAws,
  azure: FaCloud,
  gcp: FaCloud,
}

function NodeDetailsPanel({ node, onClose }) {
  if (!node) return null

  const { data } = node

  return (
    <div className="node-details-panel">
      <div className="panel-header">
        <h2>{data.label}</h2>
        <button className="close-button" onClick={onClose} title="Close">
          <FaTimes />
        </button>
      </div>

      <div className="panel-content">
        {/* Basic Info */}
        <section className="panel-section">
          <h3>Overview</h3>
          <div className="info-grid">
            {data.description && (
              <div className="info-item full-width">
                <span className="info-label">Description</span>
                <span className="info-value">{data.description}</span>
              </div>
            )}
            <div className="info-item">
              <span className="info-label"><FaTag /> Category</span>
              <span className="info-value category-badge">{data.category}</span>
            </div>
            {data.region && (
              <div className="info-item">
                <span className="info-label"><FaMapMarkerAlt /> Region</span>
                <span className="info-value">{data.region}</span>
              </div>
            )}
            {data.solution_layer && (
              <div className="info-item">
                <span className="info-label"><FaLayerGroup /> Layer</span>
                <span className="info-value">{data.solution_layer}</span>
              </div>
            )}
            {data.semantic_role && (
              <div className="info-item">
                <span className="info-label">Role</span>
                <span className="info-value">{data.semantic_role.replace(/_/g, ' ')}</span>
              </div>
            )}
            {data.network_zone && (
              <div className="info-item">
                <span className="info-label">Network Zone</span>
                <span className="info-value">{data.network_zone}</span>
              </div>
            )}
          </div>
        </section>

        {/* Configuration */}
        {data.config && (
          <section className="panel-section">
            <h3>Configuration</h3>
            <div className="info-grid">
              {data.config.cpu_count && (
                <div className="info-item">
                  <span className="info-label"><FaServer /> CPU</span>
                  <span className="info-value">{data.config.cpu_count} vCPU</span>
                </div>
              )}
              {data.config.ram_gb && (
                <div className="info-item">
                  <span className="info-label"><FaMemory /> RAM</span>
                  <span className="info-value">{data.config.ram_gb} GB</span>
                </div>
              )}
              {data.config.disk_gb && (
                <div className="info-item">
                  <span className="info-label"><FaHdd /> Disk</span>
                  <span className="info-value">
                    {data.config.disk_gb} GB
                    {data.config.disk_type && ` (${data.config.disk_type.toUpperCase()})`}
                  </span>
                </div>
              )}
              {data.config.scale_type && (
                <div className="info-item">
                  <span className="info-label">Scaling</span>
                  <span className="info-value">{data.config.scale_type}</span>
                </div>
              )}
              {data.config.min_instances != null && (
                <div className="info-item">
                  <span className="info-label">Min Instances</span>
                  <span className="info-value">{data.config.min_instances}</span>
                </div>
              )}
              {data.config.max_instances != null && (
                <div className="info-item">
                  <span className="info-label">Max Instances</span>
                  <span className="info-value">{data.config.max_instances}</span>
                </div>
              )}
              {data.config.multi_az != null && (
                <div className="info-item">
                  <span className="info-label">Multi-AZ</span>
                  <span className="info-value">{data.config.multi_az ? 'Yes' : 'No'}</span>
                </div>
              )}
              {data.config.replication_role && (
                <div className="info-item">
                  <span className="info-label">Replication</span>
                  <span className="info-value">{data.config.replication_role}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Cloud Products */}
        {data.products && data.products.length > 0 && (
          <section className="panel-section">
            <h3>Cloud Products</h3>
            <div className="products-list">
              {data.products.map((product, idx) => {
                const ProviderIcon = PROVIDER_ICONS[product.provider]
                return (
                  <div
                    key={idx}
                    className={`product-item ${product.recommended ? 'recommended' : ''}`}
                  >
                    <div className="product-header">
                      {ProviderIcon && (
                        <ProviderIcon className="provider-icon" size={20} />
                      )}
                      <div className="product-info">
                        <div className="product-name">{product.product_name}</div>
                        <div className="product-id">{product.product_id}</div>
                      </div>
                      {product.recommended && (
                        <span className="recommended-badge">Recommended</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Semantic Metadata */}
        {(data.flow_stage != null || data.placement_type || data.shape) && (
          <section className="panel-section">
            <h3>Metadata</h3>
            <div className="info-grid">
              {data.flow_stage != null && (
                <div className="info-item">
                  <span className="info-label">Flow Stage</span>
                  <span className="info-value">{data.flow_stage}</span>
                </div>
              )}
              {data.placement_type && (
                <div className="info-item">
                  <span className="info-label">Placement</span>
                  <span className="info-value">{data.placement_type.replace(/_/g, ' ')}</span>
                </div>
              )}
              {data.shape && (
                <div className="info-item">
                  <span className="info-label">Shape</span>
                  <span className="info-value">{data.shape}</span>
                </div>
              )}
              {data.priority != null && (
                <div className="info-item">
                  <span className="info-label">Priority</span>
                  <span className="info-value">{data.priority}</span>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export default memo(NodeDetailsPanel)

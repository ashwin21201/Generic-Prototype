import { memo, useState, useEffect } from 'react'
import { FaSearch, FaTimes, FaFilter } from 'react-icons/fa'
import './SearchFilter.css'

function SearchFilter({ nodes, onFilterChange }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLayer, setSelectedLayer] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedRegion, setSelectedRegion] = useState('all')
  const [showFilters, setShowFilters] = useState(false)

  // Extract unique values for filters
  const layers = ['all', ...new Set(nodes.map(n => n.data.solution_layer).filter(Boolean))]
  const categories = ['all', ...new Set(nodes.map(n => n.data.category).filter(Boolean))]
  const regions = ['all', ...new Set(nodes.map(n => n.data.region).filter(Boolean))]

  // Apply filters
  useEffect(() => {
    const filtered = nodes.filter(node => {
      const matchesSearch = searchTerm === '' || 
        node.data.label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.data.description?.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesLayer = selectedLayer === 'all' || node.data.solution_layer === selectedLayer
      const matchesCategory = selectedCategory === 'all' || node.data.category === selectedCategory
      const matchesRegion = selectedRegion === 'all' || node.data.region === selectedRegion

      return matchesSearch && matchesLayer && matchesCategory && matchesRegion
    })

    onFilterChange(filtered.map(n => n.id))
  }, [searchTerm, selectedLayer, selectedCategory, selectedRegion, nodes, onFilterChange])

  const handleClearFilters = () => {
    setSearchTerm('')
    setSelectedLayer('all')
    setSelectedCategory('all')
    setSelectedRegion('all')
  }

  const hasActiveFilters = searchTerm || selectedLayer !== 'all' || selectedCategory !== 'all' || selectedRegion !== 'all'

  return (
    <div className="search-filter-container">
      <div className="search-bar">
        <FaSearch className="search-icon" />
        <input
          type="text"
          placeholder="Search nodes by name, ID, or description..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        {searchTerm && (
          <button
            className="clear-search-button"
            onClick={() => setSearchTerm('')}
            title="Clear search"
          >
            <FaTimes />
          </button>
        )}
        <button
          className={`filter-toggle-button ${showFilters ? 'active' : ''}`}
          onClick={() => setShowFilters(!showFilters)}
          title="Toggle filters"
        >
          <FaFilter />
          {hasActiveFilters && <span className="filter-indicator" />}
        </button>
      </div>

      {showFilters && (
        <div className="filters-panel">
          <div className="filter-group">
            <label className="filter-label">Layer</label>
            <select
              className="filter-select"
              value={selectedLayer}
              onChange={(e) => setSelectedLayer(e.target.value)}
            >
              {layers.map(layer => (
                <option key={layer} value={layer}>
                  {layer === 'all' ? 'All Layers' : layer}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Category</label>
            <select
              className="filter-select"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Region</label>
            <select
              className="filter-select"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
            >
              {regions.map(region => (
                <option key={region} value={region}>
                  {region === 'all' ? 'All Regions' : region}
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button className="clear-filters-button" onClick={handleClearFilters}>
              <FaTimes /> Clear All Filters
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default memo(SearchFilter)

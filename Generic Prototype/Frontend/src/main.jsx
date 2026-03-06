import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import IntentBuilder from './pages/IntentBuilder'
import TopologyList from './pages/TopologyList'
import TopologyDetail from './pages/TopologyDetail'
import Placeholder from './pages/Placeholder'
import BlockRegistry from './pages/BlockRegistry'
import IntentSchemaPage from './pages/IntentSchemaPage'
import AuditLogPage from './pages/AuditLogPage'
import App from './App'
import ArchitectureDiagram from './ArchitectureDiagram'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/intent-builder" element={<IntentBuilder />} />
            <Route path="/topologies" element={<TopologyList />} />
            <Route path="/topologies/:id" element={<TopologyDetail />} />
            <Route path="/intent-schema" element={<IntentSchemaPage />} />
            <Route path="/blocks" element={<BlockRegistry />} />
            <Route path="/policy" element={<Placeholder title="Policy Rules" />} />
            <Route path="/impact" element={<Placeholder title="Impact Analysis" />} />
            <Route path="/audit" element={<AuditLogPage />} />
            <Route path="/legacy" element={<App />} />
            <Route path="/architecture" element={<ArchitectureDiagram />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)

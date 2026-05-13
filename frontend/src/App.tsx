import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/ui/Sidebar'
import { Overview } from './pages/Overview'
import { Forecast } from './pages/Forecast'
import { LeavePlanner } from './pages/LeavePlanner'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen bg-slate-50">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/"        element={<Overview />} />
              <Route path="/forecast" element={<Forecast />} />
              <Route path="/leave"    element={<LeavePlanner />} />
              <Route path="/workload" element={<div className="p-8 text-slate-400">Workload — Week 7</div>} />
              <Route path="/fl"       element={<div className="p-8 text-slate-400">FL Status — Week 7</div>} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

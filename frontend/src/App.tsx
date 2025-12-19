import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAppStore } from '@/store'
import { ExperimentSelectScreen } from '@/components/experiments/ExperimentSelectScreen'
import { Dashboard } from '@/components/layout/Dashboard'

function App() {
  const { isDarkMode } = useAppStore()

  // Apply dark mode class to document
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  return (
    <div className="min-h-screen bg-apple-bg text-apple-text">
      <Routes>
        <Route path="/" element={<ExperimentSelectScreen />} />
        <Route path="/experiment/:experimentId/*" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App

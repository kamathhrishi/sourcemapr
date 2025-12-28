import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type ViewMode = 'split' | 'pdf' | 'parsed'
type SidebarViewMode = 'parsed' | 'source'
type ActiveTab = 'overview' | 'documents' | 'queries'

interface HighlightIndices {
  start: number
  end: number
}

interface HtmlHighlightIndices {
  htmlStart: number
  htmlEnd: number
}

interface ChunkAnchors {
  prevAnchor: string | null
  nextAnchor: string | null
}

interface AppState {
  // Theme
  isDarkMode: boolean
  toggleDarkMode: () => void

  // Experiment
  currentExperimentId: number | null
  setExperiment: (id: number | null) => void

  // Navigation
  activeTab: ActiveTab
  setActiveTab: (tab: ActiveTab) => void

  // Document viewer
  selectedDocId: string | null
  selectDocument: (id: string | null) => void
  docViewMode: ViewMode
  setDocViewMode: (mode: ViewMode) => void
  currentPage: number
  setCurrentPage: (page: number) => void
  pdfScale: number
  setPdfScale: (scale: number) => void

  // Chunk selection & highlighting
  selectedChunkId: string | null
  selectChunk: (id: string | null) => void
  highlightChunkText: string | null
  highlightChunkIdx: HighlightIndices | null
  highlightHtmlIdx: HtmlHighlightIndices | null
  highlightAnchors: ChunkAnchors | null
  setHighlight: (text: string | null, indices?: HighlightIndices | null, htmlIndices?: HtmlHighlightIndices | null, anchors?: ChunkAnchors | null) => void
  clearHighlight: () => void

  // Query/Trace viewer
  selectedTraceId: string | null
  selectTrace: (id: string | null) => void

  // Source sidebar (in queries view)
  sidebarDocId: string | null
  sidebarPage: number
  sidebarViewMode: SidebarViewMode
  openSourceSidebar: (docId: string, page: number, chunkText?: string, indices?: HighlightIndices | null, htmlIndices?: HtmlHighlightIndices | null, anchors?: ChunkAnchors | null) => void
  closeSourceSidebar: () => void
  setSidebarViewMode: (mode: SidebarViewMode) => void
  setSidebarPage: (page: number) => void

  // Pagination
  docsPage: number
  setDocsPage: (page: number) => void
  queriesPage: number
  setQueriesPage: (page: number) => void
  chunksPage: number
  setChunksPage: (page: number) => void

  // Reset
  reset: () => void
}

const initialState = {
  isDarkMode: false,
  currentExperimentId: null,
  activeTab: 'overview' as ActiveTab,
  selectedDocId: null,
  docViewMode: 'split' as ViewMode,
  currentPage: 1,
  pdfScale: 1.2,
  selectedChunkId: null,
  highlightChunkText: null,
  highlightChunkIdx: null,
  highlightHtmlIdx: null,
  highlightAnchors: null,
  selectedTraceId: null,
  sidebarDocId: null,
  sidebarPage: 1,
  sidebarViewMode: 'parsed' as SidebarViewMode,
  docsPage: 1,
  queriesPage: 1,
  chunksPage: 1,
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...initialState,

      // Theme
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

      // Experiment
      setExperiment: (id) => set({
        currentExperimentId: id,
        activeTab: 'overview',
        selectedDocId: null,
        selectedTraceId: null,
        docsPage: 1,
        queriesPage: 1,
      }),

      // Navigation
      setActiveTab: (tab) => set({ activeTab: tab }),

      // Document viewer
      selectDocument: (id) => set({
        selectedDocId: id,
        currentPage: 1,
        selectedChunkId: null,
        highlightChunkText: null,
        highlightChunkIdx: null,
        highlightHtmlIdx: null,
        highlightAnchors: null,
        chunksPage: 1,
      }),
      setDocViewMode: (mode) => set({ docViewMode: mode }),
      setCurrentPage: (page) => set({ currentPage: page }),
      setPdfScale: (scale) => set({ pdfScale: Math.max(0.5, Math.min(3.0, scale)) }),

      // Chunk selection
      selectChunk: (id) => set({ selectedChunkId: id }),
      setHighlight: (text, indices, htmlIndices, anchors) => set({
        highlightChunkText: text,
        highlightChunkIdx: indices ?? null,
        highlightHtmlIdx: htmlIndices ?? null,
        highlightAnchors: anchors ?? null,
      }),
      clearHighlight: () => set({
        highlightChunkText: null,
        highlightChunkIdx: null,
        highlightHtmlIdx: null,
        highlightAnchors: null,
        selectedChunkId: null,
      }),

      // Query viewer
      selectTrace: (id) => set({
        selectedTraceId: id,
        sidebarDocId: null,
      }),

      // Source sidebar - preserve current view mode when switching chunks
      openSourceSidebar: (docId, page, chunkText, indices, htmlIndices, anchors) => set((state) => ({
        sidebarDocId: docId,
        sidebarPage: page,
        highlightChunkText: chunkText ?? null,
        highlightChunkIdx: indices ?? null,
        highlightHtmlIdx: htmlIndices ?? null,
        highlightAnchors: anchors ?? null,
        // Keep current view mode, only default to 'parsed' if sidebar wasn't open
        sidebarViewMode: state.sidebarDocId ? state.sidebarViewMode : 'parsed',
      })),
      closeSourceSidebar: () => set({
        sidebarDocId: null,
        highlightChunkText: null,
        highlightChunkIdx: null,
        highlightHtmlIdx: null,
        highlightAnchors: null,
      }),
      setSidebarViewMode: (mode) => set({ sidebarViewMode: mode }),
      setSidebarPage: (page) => set({ sidebarPage: page }),

      // Pagination
      setDocsPage: (page) => set({ docsPage: page }),
      setQueriesPage: (page) => set({ queriesPage: page }),
      setChunksPage: (page) => set({ chunksPage: page }),

      // Reset
      reset: () => set(initialState),
    }),
    {
      name: 'sourcemapr-storage',
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        // Don't persist navigation state
      }),
    }
  )
)

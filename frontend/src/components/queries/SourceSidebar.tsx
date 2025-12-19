import { useMemo, useEffect, useRef, useCallback, useState } from 'react'
import {
  X,
  FileText,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Highlighter,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useParsedDocument } from '@/hooks/useApi'
import { useAppStore } from '@/store'
import { api } from '@/api/client'
import type { DashboardData } from '@/api/types'

interface SourceSidebarProps {
  data: DashboardData
}

export function SourceSidebar({ data }: SourceSidebarProps) {
  const navigate = useNavigate()
  const {
    currentExperimentId,
    sidebarDocId,
    sidebarPage,
    sidebarViewMode,
    highlightChunkText,
    closeSourceSidebar,
    setSidebarViewMode,
    setSidebarPage,
  } = useAppStore()

  const parsedContainerRef = useRef<HTMLPreElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [iframeLoaded, setIframeLoaded] = useState(false)

  const document = sidebarDocId ? data.documents[sidebarDocId] : null
  const { data: parsedData, isLoading } = useParsedDocument(sidebarDocId)

  // Get file info
  const filePath = document?.file_path ?? ''
  const fileExt = filePath.toLowerCase().split('.').pop() ?? ''
  const isPdf = fileExt === 'pdf'
  const isHtml = ['htm', 'html', 'xhtml'].includes(fileExt)
  const fileUrl = document ? api.getFileUrl(document.file_path) : null

  // Split parsed text into pages
  const pages = useMemo(() => {
    if (!parsedData?.text) return ['']
    return parsedData.text.split('\n\n--- PAGE BREAK ---\n\n')
  }, [parsedData?.text])

  const totalPages = pages.length || 1
  const safePage = Math.min(Math.max(1, sidebarPage), totalPages)
  const currentPageText = pages[safePage - 1] ?? ''

  // Highlight text in content
  const highlightTextInContent = useCallback((text: string) => {
    if (!highlightChunkText) return text

    const escaped = highlightChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const normalizedSearch = escaped.replace(/\s+/g, '\\s+')
    try {
      const regex = new RegExp(`(${normalizedSearch})`, 'gi')
      return text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
    } catch {
      return text
    }
  }, [highlightChunkText])

  // Scroll to highlight
  useEffect(() => {
    if (highlightChunkText && parsedContainerRef.current) {
      const timer = setTimeout(() => {
        const highlight = parsedContainerRef.current?.querySelector('.chunk-highlight')
        if (highlight) {
          highlight.scrollIntoView({ behavior: 'instant', block: 'center' })
        }
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [highlightChunkText, sidebarPage, sidebarViewMode])

  // Reset iframe loaded state when switching views or documents
  useEffect(() => {
    setIframeLoaded(false)
  }, [sidebarDocId, sidebarViewMode])

  // Function to highlight in iframe
  const highlightInIframe = useCallback(() => {
    if (!highlightChunkText || !isHtml || !iframeRef.current) return

    try {
      const iframe = iframeRef.current
      const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document
      if (!iframeDoc || !iframeDoc.body) return

      // Remove previous highlights
      const oldHighlights = iframeDoc.querySelectorAll('.sourcemapr-highlight')
      oldHighlights.forEach((el) => {
        const parent = el.parentNode
        if (parent) {
          parent.replaceChild(iframeDoc.createTextNode(el.textContent ?? ''), el)
          parent.normalize()
        }
      })

      let style = iframeDoc.getElementById('sourcemapr-highlight-style')
      if (!style) {
        style = iframeDoc.createElement('style')
        style.id = 'sourcemapr-highlight-style'
        style.textContent = '.sourcemapr-highlight { background-color: #fef08a !important; padding: 2px 0; }'
        iframeDoc.head.appendChild(style)
      }

      // Normalize search text
      const searchText = highlightChunkText.replace(/\s+/g, ' ').trim()
      const searchLower = searchText.toLowerCase()

      // Find and highlight the matching text precisely
      const walker = iframeDoc.createTreeWalker(iframeDoc.body, NodeFilter.SHOW_TEXT, null)
      let node
      let highlighted = false
      while ((node = walker.nextNode()) && !highlighted) {
        const nodeText = node.textContent ?? ''
        const normalizedText = nodeText.toLowerCase()
        const localMatch = normalizedText.indexOf(searchLower.slice(0, Math.min(50, searchLower.length)))

        if (localMatch !== -1) {
          const range = iframeDoc.createRange()
          const matchEnd = Math.min(localMatch + searchText.length, nodeText.length)
          range.setStart(node, localMatch)
          range.setEnd(node, matchEnd)

          const highlightEl = iframeDoc.createElement('span')
          highlightEl.className = 'sourcemapr-highlight'
          try {
            range.surroundContents(highlightEl)
            highlightEl.scrollIntoView({ behavior: 'instant', block: 'center' })
            highlighted = true
          } catch {
            // Range spans multiple nodes
            node.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' })
            highlighted = true
          }
        }
      }
    } catch (e) {
      console.log('Could not highlight in iframe:', e)
    }
  }, [highlightChunkText, isHtml])

  // Highlight when iframe loads or when switching to source view with loaded iframe
  useEffect(() => {
    if (sidebarViewMode === 'source' && iframeLoaded && highlightChunkText && isHtml) {
      // Small delay to ensure DOM is ready
      const timer = setTimeout(highlightInIframe, 100)
      return () => clearTimeout(timer)
    }
  }, [sidebarViewMode, iframeLoaded, highlightChunkText, isHtml, highlightInIframe])

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setIframeLoaded(true)
  }, [])

  const handleOpenFullView = () => {
    if (!sidebarDocId) return
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
    closeSourceSidebar()
    navigate(`${basePath}/documents/${encodeURIComponent(sidebarDocId)}`)
  }

  if (!sidebarDocId || !document) return null

  return (
    <div className="w-[500px] border-l border-apple-border flex flex-col bg-apple-card shrink-0">
      {/* Header */}
      <div className="px-3 py-2 border-b border-apple-border flex items-center gap-2 shrink-0">
        <FileText className="w-4 h-4 text-apple-secondary shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{document.filename}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={handleOpenFullView}
        >
          <ExternalLink className="w-3 h-3 mr-1" />
          Full View
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={closeSourceSidebar}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Controls */}
      <div className="px-3 py-2 border-b border-apple-border bg-apple-tertiary/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Button
            variant={sidebarViewMode === 'parsed' ? 'default' : 'outline'}
            size="sm"
            className="h-6 text-xs"
            onClick={() => setSidebarViewMode('parsed')}
          >
            Parsed
          </Button>
          {(isPdf || isHtml) && (
            <Button
              variant={sidebarViewMode === 'source' ? 'default' : 'outline'}
              size="sm"
              className="h-6 text-xs"
              onClick={() => setSidebarViewMode('source')}
            >
              {isPdf ? 'PDF' : 'HTML'}
            </Button>
          )}
          <div className="w-px h-4 bg-apple-border mx-1" />
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setSidebarPage(safePage - 1)}
              disabled={safePage <= 1}
            >
              <ChevronLeft className="w-3 h-3" />
            </Button>
            <span className="text-xs text-apple-secondary min-w-[60px] text-center">
              {safePage} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setSidebarPage(safePage + 1)}
              disabled={safePage >= totalPages}
            >
              <ChevronRight className="w-3 h-3" />
            </Button>
          </div>
        </div>
        {highlightChunkText && (
          <Badge variant="secondary" className="gap-1 bg-amber-100 text-amber-700 border-0 text-xs">
            <Highlighter className="w-3 h-3" />
            Highlighted
          </Badge>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {sidebarViewMode === 'parsed' ? (
          <ScrollArea className="h-full">
            {isLoading ? (
              <div className="flex items-center justify-center h-32 text-apple-secondary">
                Loading...
              </div>
            ) : (
              <pre
                ref={parsedContainerRef}
                className="p-3 text-xs whitespace-pre-wrap font-mono bg-apple-tertiary/30"
                dangerouslySetInnerHTML={{ __html: highlightTextInContent(currentPageText) }}
              />
            )}
          </ScrollArea>
        ) : (
          <div className="h-full bg-gray-100">
            {isPdf && fileUrl ? (
              <iframe
                src={`${fileUrl}#page=${safePage}`}
                className="w-full h-full border-0"
                title={document.filename}
              />
            ) : isHtml && fileUrl ? (
              <iframe
                ref={iframeRef}
                src={fileUrl}
                className="w-full h-full border-0 bg-white"
                title={document.filename}
                sandbox="allow-same-origin"
                onLoad={handleIframeLoad}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-apple-secondary text-sm">
                No source available
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

import { useMemo, useEffect, useRef, useCallback, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import {
  X,
  FileText,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Highlighter,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useParsedDocument } from '@/hooks/useApi'
import { useAppStore } from '@/store'
import { api } from '@/api/client'
import type { DashboardData } from '@/api/types'

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

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
  const pdfContainerRef = useRef<HTMLDivElement>(null)
  const [iframeLoaded, setIframeLoaded] = useState(false)
  const [, setPdfNumPages] = useState(0)
  const [pdfScale, setPdfScale] = useState(0.8)
  const [pdfLoading, setPdfLoading] = useState(true)

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

  // Extract significant words from text (ignoring common stop words)
  const getSignificantWords = useCallback((text: string): Set<string> => {
    const stopWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
      'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
      'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their', 'we', 'our',
      'you', 'your', 'he', 'she', 'his', 'her', 'can', 'such', 'which', 'who', 'whom',
      'what', 'where', 'when', 'how', 'why', 'all', 'each', 'every', 'both', 'few', 'more',
      'most', 'other', 'some', 'any', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
      'very', 'just', 'also', 'now', 'here', 'there', 'then', 'if', 'else', 'use', 'used',
    ])

    const words = text.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 3 && !stopWords.has(w))

    return new Set(words)
  }, [])

  // Find the region in text with the most matching words from chunk
  const findBestMatchingRegion = useCallback((text: string, chunkWords: Set<string>): { start: number; end: number } | null => {
    if (chunkWords.size === 0) return null

    const textLower = text.toLowerCase()
    const windowSize = 500 // Look for ~500 char regions
    const step = 100 // Slide by 100 chars

    let bestStart = 0
    let bestEnd = 0
    let bestScore = 0

    for (let i = 0; i < text.length - 100; i += step) {
      const regionEnd = Math.min(i + windowSize, text.length)
      const region = textLower.slice(i, regionEnd)
      const regionWords = region.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/)

      // Count how many chunk words appear in this region
      let score = 0
      for (const word of regionWords) {
        if (chunkWords.has(word)) score++
      }

      if (score > bestScore) {
        bestScore = score
        bestStart = i
        bestEnd = regionEnd
      }
    }

    // Only return if we found a decent match (at least 3 words)
    if (bestScore >= 3) {
      // Expand to word boundaries
      while (bestStart > 0 && text[bestStart - 1] !== ' ' && text[bestStart - 1] !== '\n') bestStart--
      while (bestEnd < text.length && text[bestEnd] !== ' ' && text[bestEnd] !== '\n') bestEnd++
      return { start: bestStart, end: bestEnd }
    }

    return null
  }, [])

  // Highlight text in content with fallback to best matching region
  const highlightTextInContent = useCallback((text: string) => {
    if (!highlightChunkText) return text

    // First try: exact match with flexible whitespace
    const escaped = highlightChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const normalizedSearch = escaped.replace(/\s+/g, '\\s+')
    try {
      const regex = new RegExp(`(${normalizedSearch})`, 'gi')
      const exactMatch = text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
      if (exactMatch !== text) {
        return exactMatch // Found exact match
      }
    } catch {
      // Continue to fallback
    }

    // Second try: match the first 100 characters (chunk might be truncated)
    if (highlightChunkText.length > 100) {
      const shortChunk = highlightChunkText.slice(0, 100).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+')
      try {
        const regex = new RegExp(`(${shortChunk})`, 'gi')
        const shortMatch = text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
        if (shortMatch !== text) {
          return shortMatch
        }
      } catch {
        // Continue to fallback
      }
    }

    // Fallback: find region with most matching words and highlight it
    const chunkWords = getSignificantWords(highlightChunkText)
    const bestRegion = findBestMatchingRegion(text, chunkWords)

    if (bestRegion) {
      const before = text.slice(0, bestRegion.start)
      const match = text.slice(bestRegion.start, bestRegion.end)
      const after = text.slice(bestRegion.end)
      return `${before}<mark class="chunk-highlight-word">${match}</mark>${after}`
    }

    return text
  }, [highlightChunkText, getSignificantWords, findBestMatchingRegion])

  // Scroll to highlight (supports both exact and word-based highlights)
  useEffect(() => {
    if (highlightChunkText && parsedContainerRef.current) {
      const timer = setTimeout(() => {
        // Try exact highlight first, then word-based
        const highlight = parsedContainerRef.current?.querySelector('.chunk-highlight') ||
                         parsedContainerRef.current?.querySelector('.chunk-highlight-word')
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

  // PDF handlers
  const onPdfLoadSuccess = ({ numPages }: { numPages: number }) => {
    setPdfNumPages(numPages)
    setPdfLoading(false)
  }

  const onPdfLoadError = (error: Error) => {
    console.error('PDF load error:', error)
    setPdfLoading(false)
  }

  // Highlight text in PDF text layer
  const highlightPdfText = useCallback(() => {
    if (!highlightChunkText || !pdfContainerRef.current) return

    // Remove previous highlights
    const oldHighlights = pdfContainerRef.current.querySelectorAll('.pdf-chunk-highlight')
    oldHighlights.forEach(el => el.classList.remove('pdf-chunk-highlight'))

    // Find text layer elements
    const textLayers = pdfContainerRef.current.querySelectorAll('.react-pdf__Page__textContent')
    if (!textLayers.length) return

    const searchText = highlightChunkText.toLowerCase().replace(/\s+/g, ' ').trim()
    const searchWords = searchText.split(' ').filter(w => w.length > 3).slice(0, 10)

    textLayers.forEach((textLayer) => {
      const spans = textLayer.querySelectorAll('span')
      let fullText = ''
      const spanRanges: { span: Element; start: number; end: number }[] = []

      spans.forEach((span) => {
        const text = span.textContent || ''
        spanRanges.push({ span, start: fullText.length, end: fullText.length + text.length })
        fullText += text
      })

      const fullTextLower = fullText.toLowerCase()

      for (const word of searchWords) {
        const wordIdx = fullTextLower.indexOf(word)
        if (wordIdx !== -1) {
          const matchStart = wordIdx
          const matchEnd = Math.min(wordIdx + searchText.length, fullText.length)

          spanRanges.forEach(({ span, start, end }) => {
            if (start < matchEnd && end > matchStart) {
              span.classList.add('pdf-chunk-highlight')
            }
          })

          const firstHighlight = textLayer.querySelector('.pdf-chunk-highlight')
          if (firstHighlight) {
            firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
          break
        }
      }
    })
  }, [highlightChunkText])

  // Apply PDF highlighting after page renders
  useEffect(() => {
    if (highlightChunkText && !pdfLoading && isPdf && sidebarViewMode === 'source') {
      const timer = setTimeout(highlightPdfText, 300)
      return () => clearTimeout(timer)
    }
  }, [highlightChunkText, pdfLoading, isPdf, sidebarPage, sidebarViewMode, highlightPdfText])

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

      {/* Custom styles for PDF highlighting */}
      <style>{`
        .react-pdf__Page {
          position: relative;
        }
        .react-pdf__Page__canvas {
          display: block;
        }
        .react-pdf__Page__textContent {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          overflow: hidden;
          line-height: 1;
          pointer-events: none;
        }
        .react-pdf__Page__textContent span {
          position: absolute;
          color: transparent;
          white-space: pre;
          transform-origin: 0 0;
        }
        .pdf-chunk-highlight {
          background-color: rgba(251, 191, 36, 0.35) !important;
          border-radius: 2px;
          border-bottom: 2px solid #f59e0b;
        }
      `}</style>

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
          <div className="h-full bg-gray-100 overflow-auto" ref={pdfContainerRef}>
            {isPdf && fileUrl ? (
              <div className="flex flex-col items-center p-2">
                <div className="flex items-center gap-1 mb-2">
                  <Button variant="ghost" size="sm" className="h-6 px-2" onClick={() => setPdfScale(Math.max(0.4, pdfScale - 0.1))}>
                    <ZoomOut className="w-3 h-3" />
                  </Button>
                  <span className="text-xs w-10 text-center">{Math.round(pdfScale * 100)}%</span>
                  <Button variant="ghost" size="sm" className="h-6 px-2" onClick={() => setPdfScale(Math.min(2, pdfScale + 0.1))}>
                    <ZoomIn className="w-3 h-3" />
                  </Button>
                </div>
                <Document
                  file={fileUrl}
                  onLoadSuccess={onPdfLoadSuccess}
                  onLoadError={onPdfLoadError}
                  loading={
                    <div className="flex items-center justify-center h-32 text-apple-secondary text-sm">
                      Loading PDF...
                    </div>
                  }
                >
                  <Page
                    pageNumber={safePage}
                    scale={pdfScale}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    className="shadow-lg"
                  />
                </Document>
              </div>
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

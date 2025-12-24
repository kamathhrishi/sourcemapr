import { useMemo, useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import {
  ArrowLeft,
  FileText,
  Layers,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ZoomIn,
  ZoomOut,
  Code,
  Highlighter,
  Search,
  Eye,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useParsedDocument } from '@/hooks/useApi'
import { useAppStore } from '@/store'
import { api } from '@/api/client'
import type { DashboardData } from '@/api/types'

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface DocumentViewerProps {
  data: DashboardData
}

type ViewMode = 'split' | 'pdf' | 'parsed'

export function DocumentViewer({ data }: DocumentViewerProps) {
  const { docId } = useParams<{ docId: string }>()
  const navigate = useNavigate()
  const {
    currentExperimentId,
    currentPage,
    setCurrentPage,
    pdfScale,
    setPdfScale,
    selectedChunkId,
    selectChunk,
    highlightChunkText,
    setHighlight,
    clearHighlight,
  } = useAppStore()

  const [viewMode, setViewMode] = useState<ViewMode>('split')
  const [chunkSearch, setChunkSearch] = useState('')
  const [chunksExpanded, setChunksExpanded] = useState(true)
  const [numPages, setNumPages] = useState<number>(0)
  const [pdfLoading, setPdfLoading] = useState(true)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const parsedContainerRef = useRef<HTMLPreElement>(null)
  const pdfContainerRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const decodedDocId = docId ? decodeURIComponent(docId) : null
  const document = decodedDocId ? data.documents[decodedDocId] : null
  const { data: parsedData, isLoading: parsedLoading } = useParsedDocument(decodedDocId)

  // Get file info
  const filePath = document?.file_path ?? ''
  const fileExt = filePath.toLowerCase().split('.').pop() ?? ''
  const isPdf = fileExt === 'pdf'
  const isHtml = ['htm', 'html', 'xhtml'].includes(fileExt)
  const fileUrl = document ? api.getFileUrl(document.file_path) : null

  // Get chunks for this document - sorted by position in document
  const allChunks = useMemo(() => {
    if (!decodedDocId) return []
    const chunks = Object.values(data.chunks).filter((c) => c.doc_id === decodedDocId)

    // Sort by page number first, then by start_char_idx, then by index
    chunks.sort((a, b) => {
      const pageA = a.page_number ?? 0
      const pageB = b.page_number ?? 0
      if (pageA !== pageB) return pageA - pageB

      const startA = a.start_char_idx ?? 0
      const startB = b.start_char_idx ?? 0
      if (startA !== startB) return startA - startB

      return (a.index ?? 0) - (b.index ?? 0)
    })

    return chunks
  }, [data.chunks, decodedDocId])

  // Filter chunks by search
  const filteredChunks = useMemo(() => {
    if (!chunkSearch) return allChunks
    const term = chunkSearch.toLowerCase()
    return allChunks.filter((c) => c.text.toLowerCase().includes(term))
  }, [allChunks, chunkSearch])

  // Split parsed text into pages
  const pages = useMemo(() => {
    if (!parsedData?.text) return ['']
    return parsedData.text.split('\n\n--- PAGE BREAK ---\n\n')
  }, [parsedData?.text])

  const totalPages = isPdf ? numPages : pages.length || 1
  const safePage = Math.min(Math.max(1, currentPage), totalPages || 1)
  const currentPageText = pages[safePage - 1] ?? ''

  // Handle back navigation
  const handleBack = () => {
    clearHighlight()
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
    navigate(`${basePath}/documents`)
  }

  // Handle chunk click
  const handleChunkClick = (chunkId: string, text: string, startIdx?: number | null, endIdx?: number | null, pageNum?: number | null) => {
    selectChunk(chunkId)
    setHighlight(text, startIdx != null && endIdx != null ? { start: startIdx, end: endIdx } : null)
    if (pageNum) {
      setCurrentPage(pageNum)
    }
  }

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

  // Highlight text in parsed content with fallback to fuzzy matching
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

  // PDF document loaded
  const onDocumentLoadSuccess = ({ numPages: pages }: { numPages: number }) => {
    setNumPages(pages)
    setPdfLoading(false)
    setPdfError(null)
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error)
    setPdfLoading(false)
    setPdfError('Failed to load PDF')
  }

  // Highlight text in PDF text layer with fuzzy matching fallback
  const highlightPdfText = useCallback(() => {
    if (!highlightChunkText || !pdfContainerRef.current) return

    // Remove previous highlights
    const oldHighlights = pdfContainerRef.current.querySelectorAll('.pdf-chunk-highlight')
    oldHighlights.forEach(el => el.classList.remove('pdf-chunk-highlight'))

    // Find text layer elements
    const textLayers = pdfContainerRef.current.querySelectorAll('.react-pdf__Page__textContent')
    if (!textLayers.length) return

    const searchText = highlightChunkText.toLowerCase().replace(/\s+/g, ' ').trim()
    const chunkWords = getSignificantWords(highlightChunkText)

    textLayers.forEach((textLayer) => {
      const spans = textLayer.querySelectorAll('span')
      let fullText = ''
      const spanRanges: { span: Element; start: number; end: number }[] = []

      // Build full text with position mapping
      spans.forEach((span) => {
        const text = span.textContent || ''
        spanRanges.push({ span, start: fullText.length, end: fullText.length + text.length })
        fullText += text
      })

      const fullTextLower = fullText.toLowerCase()

      // First try: exact match
      const exactMatchIdx = fullTextLower.indexOf(searchText)
      if (exactMatchIdx !== -1) {
        const matchStart = exactMatchIdx
        const matchEnd = Math.min(exactMatchIdx + searchText.length, fullText.length)

        spanRanges.forEach(({ span, start, end }) => {
          if (start < matchEnd && end > matchStart) {
            span.classList.add('pdf-chunk-highlight')
          }
        })

        const firstHighlight = textLayer.querySelector('.pdf-chunk-highlight')
        if (firstHighlight) {
          firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
        return
      }

      // Second try: match first 100 chars
      if (searchText.length > 100) {
        const shortSearch = searchText.slice(0, 100)
        const shortMatchIdx = fullTextLower.indexOf(shortSearch)
        if (shortMatchIdx !== -1) {
          const matchStart = shortMatchIdx
          const matchEnd = Math.min(shortMatchIdx + shortSearch.length, fullText.length)

          spanRanges.forEach(({ span, start, end }) => {
            if (start < matchEnd && end > matchStart) {
              span.classList.add('pdf-chunk-highlight')
            }
          })

          const firstHighlight = textLayer.querySelector('.pdf-chunk-highlight')
          if (firstHighlight) {
            firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
          return
        }
      }

      // Fallback: fuzzy matching - find region with most matching words
      const bestRegion = findBestMatchingRegion(fullText, chunkWords)
      if (bestRegion) {
        spanRanges.forEach(({ span, start, end }) => {
          if (start < bestRegion.end && end > bestRegion.start) {
            span.classList.add('pdf-chunk-highlight')
          }
        })

        const firstHighlight = textLayer.querySelector('.pdf-chunk-highlight')
        if (firstHighlight) {
          firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }
    })
  }, [highlightChunkText, getSignificantWords, findBestMatchingRegion])

  // Apply PDF highlighting after page renders
  useEffect(() => {
    if (highlightChunkText && !pdfLoading && isPdf) {
      const timer = setTimeout(highlightPdfText, 300)
      return () => clearTimeout(timer)
    }
  }, [highlightChunkText, pdfLoading, isPdf, currentPage, highlightPdfText])

  // Scroll to highlight after render in parsed view (supports both exact and word-based highlights)
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
  }, [highlightChunkText, currentPage, viewMode])

  // Highlight in HTML iframe
  useEffect(() => {
    if (highlightChunkText && isHtml && iframeRef.current && (viewMode === 'split' || viewMode === 'pdf')) {
      const timer = setTimeout(() => {
        try {
          const iframe = iframeRef.current
          if (!iframe) return
          const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document
          if (!iframeDoc) return

          // Remove previous highlights
          const oldHighlights = iframeDoc.querySelectorAll('.sourcemapr-highlight')
          oldHighlights.forEach((el) => {
            const parent = el.parentNode
            if (parent) {
              parent.replaceChild(iframeDoc.createTextNode(el.textContent ?? ''), el)
              parent.normalize()
            }
          })

          // Add highlight styles
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

          // Collect all text content with node references
          const textNodes: { node: Text; text: string }[] = []
          let fullText = ''
          const walker = iframeDoc.createTreeWalker(iframeDoc.body, NodeFilter.SHOW_TEXT, null)
          let node
          while ((node = walker.nextNode())) {
            const text = node.textContent ?? ''
            textNodes.push({ node: node as Text, text })
            fullText += text
          }

          // Find match in combined text
          const fullTextNormalized = fullText.replace(/\s+/g, ' ').toLowerCase()
          const matchStart = fullTextNormalized.indexOf(searchLower.slice(0, 100))

          if (matchStart === -1) return

          // Find which nodes contain the match and highlight them
          let highlighted = false
          for (const { node: textNode, text } of textNodes) {
            const normalizedText = text.toLowerCase()
            const localMatch = normalizedText.indexOf(searchLower.slice(0, Math.min(50, searchLower.length)))
            if (localMatch !== -1 && !highlighted) {
              const range = iframeDoc.createRange()
              const matchEnd = Math.min(localMatch + searchText.length, text.length)
              range.setStart(textNode, localMatch)
              range.setEnd(textNode, matchEnd)

              const highlight = iframeDoc.createElement('span')
              highlight.className = 'sourcemapr-highlight'
              try {
                range.surroundContents(highlight)
                highlight.scrollIntoView({ behavior: 'instant', block: 'center' })
                highlighted = true
              } catch {
                textNode.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' })
                highlighted = true
              }
            }
          }
        } catch (e) {
          console.log('Could not highlight in iframe:', e)
        }
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [highlightChunkText, isHtml, viewMode])

  if (!document) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-apple-secondary">Document not found</p>
            <Button variant="outline" className="mt-4" onClick={handleBack}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Documents
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
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

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-apple-border bg-apple-card shrink-0">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="min-w-0">
            <h2 className="font-semibold text-sm flex items-center gap-2 truncate">
              <FileText className="w-4 h-4 shrink-0" />
              {document.filename}
            </h2>
            <p className="text-xs text-apple-secondary truncate">{document.file_path}</p>
          </div>
        </div>

        {/* View Mode Buttons */}
        <div className="flex items-center gap-2">
          {(isPdf || isHtml) && (
            <Button
              variant={viewMode === 'split' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('split')}
            >
              Split
            </Button>
          )}
          {isPdf && (
            <Button
              variant={viewMode === 'pdf' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('pdf')}
            >
              PDF
            </Button>
          )}
          {isHtml && (
            <Button
              variant={viewMode === 'pdf' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('pdf')}
            >
              <Code className="w-4 h-4 mr-1" />
              HTML
            </Button>
          )}
          <Button
            variant={viewMode === 'parsed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('parsed')}
          >
            Parsed
          </Button>

          <div className="w-px h-6 bg-apple-border mx-2" />

          <Badge variant="secondary">{allChunks.length} chunks</Badge>
          {totalPages > 0 && (
            <Badge variant="secondary">{totalPages} pages</Badge>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex min-h-0">
        {/* Document View */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Page Navigation */}
          {(viewMode === 'split' || viewMode === 'pdf' || (viewMode === 'parsed' && totalPages > 1)) && totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 px-3 py-2 bg-apple-card border-b border-apple-border shrink-0">
              <Button variant="ghost" size="icon" onClick={() => setCurrentPage(1)} disabled={safePage <= 1}>
                <ChevronsLeft className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setCurrentPage(safePage - 1)} disabled={safePage <= 1}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={safePage}
                  onChange={(e) => setCurrentPage(parseInt(e.target.value) || 1)}
                  className="w-14 text-center"
                />
                <span className="text-sm text-apple-secondary">of {totalPages}</span>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setCurrentPage(safePage + 1)} disabled={safePage >= totalPages}>
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setCurrentPage(totalPages)} disabled={safePage >= totalPages}>
                <ChevronsRight className="w-4 h-4" />
              </Button>
              {isPdf && (
                <div className="ml-4 flex items-center gap-1 border-l border-apple-border pl-4">
                  <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setPdfScale(Math.max(0.5, pdfScale - 0.25))}>
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <span className="text-sm w-12 text-center">{Math.round(pdfScale * 100)}%</span>
                  <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setPdfScale(Math.min(3, pdfScale + 0.25))}>
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                </div>
              )}
              {highlightChunkText && (
                <Badge variant="warning" className="ml-4 gap-1 bg-amber-100 text-amber-700 border-0">
                  <Highlighter className="w-3 h-3" />
                  Chunk Highlighted
                </Badge>
              )}
            </div>
          )}

          {/* Content Area */}
          <div className="flex-1 flex min-h-0">
            {viewMode === 'split' ? (
              <>
                {/* Left: Original Document */}
                <div className="flex-[2] flex flex-col border-r border-apple-border min-w-0">
                  <div className="px-3 py-1.5 bg-apple-tertiary/50 border-b border-apple-border text-xs text-apple-secondary flex items-center gap-1 shrink-0">
                    <FileText className="w-3 h-3" />
                    Original {isPdf ? 'PDF' : isHtml ? 'HTML' : 'Document'}
                  </div>
                  <div className="flex-1 overflow-auto bg-gray-100" ref={pdfContainerRef}>
                    {isPdf && fileUrl ? (
                      <div className="flex justify-center p-4">
                        <Document
                          file={fileUrl}
                          onLoadSuccess={onDocumentLoadSuccess}
                          onLoadError={onDocumentLoadError}
                          loading={
                            <div className="flex items-center justify-center h-32 text-apple-secondary">
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
                        {pdfError && (
                          <div className="text-red-500 text-center py-4">{pdfError}</div>
                        )}
                      </div>
                    ) : isHtml && fileUrl ? (
                      <iframe
                        ref={iframeRef}
                        src={fileUrl}
                        className="w-full h-full border-0 bg-white"
                        title={document.filename}
                        sandbox="allow-same-origin"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-apple-secondary">
                        No source document available
                      </div>
                    )}
                  </div>
                </div>

                {/* Right: Parsed Text */}
                <div className="flex-1 flex flex-col min-w-0">
                  <div className="px-3 py-1.5 bg-apple-tertiary/50 border-b border-apple-border text-xs text-apple-secondary shrink-0">
                    Parsed Text (Page {safePage})
                  </div>
                  <ScrollArea className="flex-1">
                    {parsedLoading ? (
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
                </div>
              </>
            ) : viewMode === 'pdf' ? (
              <div className="flex-1 flex flex-col">
                <div className="px-3 py-1.5 bg-apple-tertiary/50 border-b border-apple-border text-xs text-apple-secondary flex items-center gap-2 shrink-0">
                  {isPdf ? (
                    <>
                      <FileText className="w-3 h-3" />
                      Original PDF - Page {safePage} of {totalPages}
                    </>
                  ) : isHtml ? (
                    <>
                      <Code className="w-3 h-3" />
                      Original HTML Document
                    </>
                  ) : null}
                  {highlightChunkText && (
                    <Badge variant="warning" className="ml-2 gap-1 bg-amber-100 text-amber-700 border-0">
                      <Highlighter className="w-3 h-3" />
                      Chunk Highlighted
                    </Badge>
                  )}
                </div>
                <div className="flex-1 overflow-auto bg-gray-100" ref={pdfContainerRef}>
                  {isPdf && fileUrl ? (
                    <div className="flex justify-center p-4">
                      <Document
                        file={fileUrl}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading={
                          <div className="flex items-center justify-center h-32 text-apple-secondary">
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
                      {pdfError && (
                        <div className="text-red-500 text-center py-4">{pdfError}</div>
                      )}
                    </div>
                  ) : isHtml && fileUrl ? (
                    <iframe
                      ref={iframeRef}
                      src={fileUrl}
                      className="w-full h-full border-0 bg-white"
                      title={document.filename}
                      sandbox="allow-same-origin"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-apple-secondary">
                      No source document available
                    </div>
                  )}
                </div>
              </div>
            ) : (
              // Parsed view - all pages with markers
              <div className="flex-1 flex flex-col">
                <div className="px-3 py-1.5 bg-apple-tertiary/50 border-b border-apple-border text-xs text-apple-secondary flex items-center gap-2 shrink-0">
                  <FileText className="w-3 h-3" />
                  Parsed Text ({totalPages} pages) - Scroll to navigate
                  {highlightChunkText && (
                    <Badge variant="warning" className="ml-2 gap-1 bg-amber-100 text-amber-700 border-0">
                      <Highlighter className="w-3 h-3" />
                      Chunk Highlighted
                    </Badge>
                  )}
                  <span className="ml-auto bg-apple-text text-white px-2 py-0.5 rounded text-xs font-medium">
                    Page {safePage} / {totalPages}
                  </span>
                </div>
                <ScrollArea className="flex-1">
                  {parsedLoading ? (
                    <div className="flex items-center justify-center h-32 text-apple-secondary">
                      Loading...
                    </div>
                  ) : (
                    <pre ref={parsedContainerRef} className="p-4 text-sm whitespace-pre-wrap font-mono bg-apple-tertiary/30">
                      {pages.map((pageText, i) => (
                        <div key={i} className="mb-6">
                          <div className="sticky top-0 bg-apple-bg/90 backdrop-blur-sm px-2 py-1 mb-2 rounded text-xs font-medium text-apple-secondary border-b border-apple-border">
                            Page {i + 1}
                          </div>
                          <div dangerouslySetInnerHTML={{ __html: highlightTextInContent(pageText) }} />
                        </div>
                      ))}
                    </pre>
                  )}
                </ScrollArea>
              </div>
            )}
          </div>
        </div>

        {/* Chunks Panel */}
        <div className={`${chunksExpanded ? 'w-80' : 'w-10'} border-l border-apple-border flex flex-col bg-apple-card shrink-0 transition-all`}>
          {chunksExpanded ? (
            <>
              <div className="px-3 py-2 border-b border-apple-border shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-sm flex items-center gap-2">
                    <Layers className="w-4 h-4" />
                    Chunks ({allChunks.length})
                  </h3>
                  <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => setChunksExpanded(false)}>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
                <div className="relative">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-apple-secondary" />
                  <Input
                    placeholder="Search chunks..."
                    value={chunkSearch}
                    onChange={(e) => setChunkSearch(e.target.value)}
                    className="pl-7 h-7 text-xs"
                  />
                </div>
              </div>
              <ScrollArea className="flex-1">
                <div className="p-2 space-y-2">
                  {filteredChunks.map((chunk, displayIdx) => (
                    <div
                      key={chunk.chunk_id}
                      className={`p-2 rounded-lg border cursor-pointer transition-colors text-xs ${
                        selectedChunkId === chunk.chunk_id
                          ? 'border-orange-500 bg-orange-50 dark:bg-orange-950/30'
                          : 'border-apple-border hover:border-orange-400/50'
                      }`}
                      onClick={() => handleChunkClick(
                        chunk.chunk_id,
                        chunk.text,
                        chunk.start_char_idx,
                        chunk.end_char_idx,
                        chunk.page_number
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-apple-secondary">
                          Chunk {displayIdx + 1}
                        </span>
                        <div className="flex items-center gap-1">
                          {chunk.page_number && (
                            <Badge variant="secondary" className="text-[10px] px-1 py-0">
                              p.{chunk.page_number}
                            </Badge>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleChunkClick(
                                chunk.chunk_id,
                                chunk.text,
                                chunk.start_char_idx,
                                chunk.end_char_idx,
                                chunk.page_number
                              )
                            }}
                          >
                            <Eye className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                      <p className="line-clamp-3 text-apple-text">{chunk.text}</p>
                    </div>
                  ))}
                  {filteredChunks.length === 0 && (
                    <p className="text-center py-4 text-apple-secondary text-xs">
                      {chunkSearch ? 'No chunks match' : 'No chunks'}
                    </p>
                  )}
                </div>
              </ScrollArea>
            </>
          ) : (
            <Button
              variant="ghost"
              className="h-full w-full rounded-none flex flex-col gap-1"
              onClick={() => setChunksExpanded(true)}
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs [writing-mode:vertical-lr]">Chunks</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

import { useMemo, useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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
    highlightChunkIdx,
    setHighlight,
    clearHighlight,
  } = useAppStore()

  const [viewMode, setViewMode] = useState<ViewMode>('split')
  const [chunkSearch, setChunkSearch] = useState('')
  const [chunksExpanded, setChunksExpanded] = useState(true)
  const parsedContainerRef = useRef<HTMLPreElement>(null)
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

  // Get chunks for this document
  const allChunks = useMemo(() => {
    if (!decodedDocId) return []
    return Object.values(data.chunks)
      .filter((c) => c.doc_id === decodedDocId)
      .sort((a, b) => a.index - b.index)
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

  const totalPages = pages.length || 1
  const safePage = Math.min(Math.max(1, currentPage), totalPages)
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

  // Highlight text in content
  const highlightTextInContent = useCallback((text: string) => {
    if (!highlightChunkText) return text

    // Use character indices if available for precise highlighting
    if (highlightChunkIdx && viewMode === 'parsed') {
      // For full parsed view, we need to adjust indices based on page breaks
      // For now, use text matching
    }

    // Escape special regex characters
    const escaped = highlightChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    // Normalize whitespace for matching
    const normalizedSearch = escaped.replace(/\s+/g, '\\s+')
    try {
      const regex = new RegExp(`(${normalizedSearch})`, 'gi')
      return text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
    } catch {
      return text
    }
  }, [highlightChunkText, highlightChunkIdx, viewMode])

  // Scroll to highlight after render
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

          // Normalize search text - get first ~100 chars for matching
          const searchText = highlightChunkText.replace(/\s+/g, ' ').trim()
          const searchLower = searchText.toLowerCase()

          // Collect all text content with node references
          const textNodes: { node: Text; text: string; start: number }[] = []
          let fullText = ''
          const walker = iframeDoc.createTreeWalker(iframeDoc.body, NodeFilter.SHOW_TEXT, null)
          let node
          while ((node = walker.nextNode())) {
            const text = node.textContent ?? ''
            textNodes.push({ node: node as Text, text, start: fullText.length })
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

            // Check if this node contains part of our search
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
                // Range spans multiple nodes, just scroll to node
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
          {document.num_pages && (
            <Badge variant="secondary">{document.num_pages} pages</Badge>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex min-h-0">
        {/* Document View */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Page Navigation */}
          {(viewMode === 'split' || (viewMode === 'parsed' && totalPages > 1)) && (
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
                    {isPdf && (
                      <div className="ml-auto flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => setPdfScale(pdfScale - 0.2)}>
                          <ZoomOut className="w-3 h-3" />
                        </Button>
                        <span className="text-xs w-10 text-center">{Math.round(pdfScale * 100)}%</span>
                        <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => setPdfScale(pdfScale + 0.2)}>
                          <ZoomIn className="w-3 h-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 overflow-auto bg-gray-100">
                    {isPdf && fileUrl ? (
                      <iframe
                        src={`${fileUrl}#page=${safePage}&zoom=${Math.round(pdfScale * 100)}`}
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
                      Original PDF ({totalPages} pages) - Scroll to navigate
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
                  {isPdf && (
                    <div className="ml-auto flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => setPdfScale(pdfScale - 0.2)}>
                        <ZoomOut className="w-3 h-3" />
                      </Button>
                      <span className="text-xs w-10 text-center">{Math.round(pdfScale * 100)}%</span>
                      <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => setPdfScale(pdfScale + 0.2)}>
                        <ZoomIn className="w-3 h-3" />
                      </Button>
                    </div>
                  )}
                </div>
                <div className="flex-1 overflow-auto bg-gray-100">
                  {(isPdf || isHtml) && fileUrl ? (
                    <iframe
                      ref={iframeRef}
                      src={isPdf ? `${fileUrl}#zoom=${Math.round(pdfScale * 100)}` : fileUrl}
                      className="w-full h-full border-0 bg-white"
                      title={document.filename}
                      sandbox={isHtml ? "allow-same-origin" : undefined}
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
                  {filteredChunks.map((chunk) => (
                    <div
                      key={chunk.chunk_id}
                      className={`p-2 rounded-lg border cursor-pointer transition-colors text-xs ${
                        selectedChunkId === chunk.chunk_id
                          ? 'border-apple-blue bg-apple-blue/5'
                          : 'border-apple-border hover:border-apple-blue/50'
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
                          #{chunk.index + 1}
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

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
  Eye,
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
    highlightChunkIdx,
    highlightAnchors,
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
  const getSignificantWords = useCallback((text: string): Map<string, number> => {
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

    const wordCounts = new Map<string, number>()
    // Include shorter words (2+ chars) for better matching
    const words = text.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 2 && !stopWords.has(w))

    for (const word of words) {
      wordCounts.set(word, (wordCounts.get(word) || 0) + 1)
    }

    return wordCounts
  }, [])

  // Split text into sentences for better matching
  const splitIntoSentences = useCallback((text: string): { text: string; start: number; end: number }[] => {
    const sentences: { text: string; start: number; end: number }[] = []
    // Match sentences ending with . ! ? or newlines, but not abbreviations like "e.g." or "i.e."
    const sentenceRegex = /[^.!?\n]+(?:[.!?]+|\n|$)/g
    let match
    while ((match = sentenceRegex.exec(text)) !== null) {
      const sentenceText = match[0].trim()
      if (sentenceText.length > 10) { // Skip very short fragments
        sentences.push({
          text: sentenceText,
          start: match.index,
          end: match.index + match[0].length
        })
      }
    }
    return sentences
  }, [])

  // Calculate similarity score between chunk words and a text region
  const calculateSimilarityScore = useCallback((
    regionText: string,
    chunkWords: Map<string, number>
  ): number => {
    if (chunkWords.size === 0) return 0

    const regionWordsLower = regionText.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 2)

    let matchedWords = 0
    let totalWeight = 0
    const matchedSet = new Set<string>()

    for (const word of regionWordsLower) {
      if (chunkWords.has(word) && !matchedSet.has(word)) {
        matchedSet.add(word)
        matchedWords++
        // Weight longer words more heavily
        totalWeight += Math.min(word.length / 4, 3)
      }
      // Also check for partial/substring matches for longer words
      if (word.length >= 5) {
        for (const [chunkWord] of chunkWords) {
          if (chunkWord.length >= 5 && !matchedSet.has(chunkWord)) {
            if (word.includes(chunkWord) || chunkWord.includes(word)) {
              matchedSet.add(chunkWord)
              matchedWords += 0.5
              totalWeight += 1
            }
          }
        }
      }
    }

    // Score based on percentage of chunk words found + weighted score
    const coverage = matchedWords / chunkWords.size
    return coverage * 100 + totalWeight
  }, [])

  // Find best matching sentences or regions
  const findBestMatchingRegions = useCallback((
    text: string,
    chunkWords: Map<string, number>
  ): { start: number; end: number }[] => {
    if (chunkWords.size === 0) return []

    const sentences = splitIntoSentences(text)
    const scoredSentences = sentences.map(s => ({
      ...s,
      score: calculateSimilarityScore(s.text, chunkWords)
    }))

    // Sort by score descending
    scoredSentences.sort((a, b) => b.score - a.score)

    // Very low threshold - just need ANY word matches
    const minScore = Math.max(1, chunkWords.size * 0.05) // At least 5% word coverage or 1 match
    const topMatches = scoredSentences
      .filter(s => s.score >= minScore)
      .slice(0, 5) // Up to 5 highlights

    if (topMatches.length === 0) {
      // Fallback: sliding window approach - be very aggressive
      const windowSize = 400
      const step = 30
      let bestStart = 0
      let bestEnd = 0
      let bestScore = 0

      for (let i = 0; i < text.length - 30; i += step) {
        const regionEnd = Math.min(i + windowSize, text.length)
        const region = text.slice(i, regionEnd)
        const score = calculateSimilarityScore(region, chunkWords)

        if (score > bestScore) {
          bestScore = score
          bestStart = i
          bestEnd = regionEnd
        }
      }

      // Accept any positive score
      if (bestScore > 0) {
        // Expand to sentence boundaries
        while (bestStart > 0 && !['.', '!', '?', '\n'].includes(text[bestStart - 1] ?? '')) bestStart--
        while (bestEnd < text.length && !['.', '!', '?', '\n'].includes(text[bestEnd] ?? '')) bestEnd++
        return [{ start: Math.max(0, bestStart), end: Math.min(bestEnd + 1, text.length) }]
      }

      // Ultimate fallback: highlight first 500 chars if we have the chunk text
      if (text.length > 0) {
        return [{ start: 0, end: Math.min(500, text.length) }]
      }

      return []
    }

    // Merge adjacent sentences into continuous regions
    const sortedByPosition = [...topMatches].sort((a, b) => a.start - b.start)
    const merged: { start: number; end: number }[] = []

    for (const match of sortedByPosition) {
      const last = merged[merged.length - 1]
      if (!last) {
        merged.push({ start: match.start, end: match.end })
      } else if (match.start - last.end < 150) {
        // Merge if within 150 chars of each other
        last.end = match.end
      } else {
        merged.push({ start: match.start, end: match.end })
      }
    }

    return merged
  }, [splitIntoSentences, calculateSimilarityScore])

  // Normalize text by removing extra whitespace for fuzzy comparison
  const normalizeForComparison = useCallback((str: string): string => {
    return str.toLowerCase().replace(/[\s\n\r\t]+/g, ' ').trim()
  }, [])

  // Highlight text in content - prefer position indices, fallback to text matching
  const highlightTextInContent = useCallback((text: string, pageStartOffset: number = 0) => {
    if (!highlightChunkText) return text

    // BEST: Use position indices if available (most accurate)
    if (highlightChunkIdx && highlightChunkIdx.start != null && highlightChunkIdx.end != null) {
      // Adjust indices relative to current page offset
      const relStart = highlightChunkIdx.start - pageStartOffset
      const relEnd = highlightChunkIdx.end - pageStartOffset

      // Check if the chunk is within this text segment
      if (relStart >= 0 && relStart < text.length && relEnd > 0 && relEnd <= text.length) {
        const before = text.slice(0, relStart)
        const match = text.slice(relStart, relEnd)
        const after = text.slice(relEnd)
        return `${before}<mark class="chunk-highlight">${match}</mark>${after}`
      }
    }

    // FALLBACK 1: exact match with flexible whitespace (any whitespace matches any whitespace)
    const escaped = highlightChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const normalizedSearch = escaped.replace(/\s+/g, '[\\s\\n\\r\\t]+')
    try {
      const regex = new RegExp(`(${normalizedSearch})`, 'gis')
      const exactMatch = text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
      if (exactMatch !== text) {
        return exactMatch // Found exact match
      }
    } catch {
      // Continue to fallback
    }

    // FALLBACK 2: match the first 100 characters with flexible whitespace
    if (highlightChunkText.length > 100) {
      const shortChunk = highlightChunkText.slice(0, 100).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '[\\s\\n\\r\\t]+')
      try {
        const regex = new RegExp(`(${shortChunk})`, 'gis')
        const shortMatch = text.replace(regex, '<mark class="chunk-highlight">$1</mark>')
        if (shortMatch !== text) {
          return shortMatch
        }
      } catch {
        // Continue to fallback
      }
    }

    // FALLBACK 3: Aggressive word-by-word highlighting
    // Extract ALL words from chunk and highlight every match
    const chunkWords = highlightChunkText.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 3)

    // Remove common stop words for cleaner highlighting
    const stopWords = new Set(['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'her', 'was', 'one', 'our', 'out', 'with', 'this', 'that', 'from', 'have', 'been', 'will', 'would', 'could', 'should', 'into', 'more', 'some', 'such', 'than', 'them', 'then', 'these', 'they', 'were', 'what', 'when', 'where', 'which', 'while', 'your'])
    const meaningfulWords = chunkWords.filter(w => !stopWords.has(w) && w.length >= 3)

    if (meaningfulWords.length > 0) {
      let result = text
      let hasMatch = false

      // Sort by length (longer words first) to prioritize more specific matches
      const sortedWords = [...new Set(meaningfulWords)].sort((a, b) => b.length - a.length)

      for (const word of sortedWords.slice(0, 25)) {
        try {
          const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          // Match word with flexible boundaries (allow partial matches for longer words)
          const wordRegex = word.length >= 5
            ? new RegExp(`(${escaped})`, 'gi')
            : new RegExp(`\\b(${escaped})\\b`, 'gi')
          const newResult = result.replace(wordRegex, '<mark class="chunk-highlight-word">$1</mark>')
          if (newResult !== result) {
            result = newResult
            hasMatch = true
          }
        } catch {
          // Skip invalid patterns
        }
      }

      if (hasMatch) {
        return result
      }
    }

    // FALLBACK 4: find best matching sentences/regions
    const chunkWordMap = getSignificantWords(highlightChunkText)
    const bestRegions = findBestMatchingRegions(text, chunkWordMap)

    if (bestRegions.length > 0) {
      let result = ''
      let lastEnd = 0

      for (const region of bestRegions) {
        result += text.slice(lastEnd, region.start)
        result += `<mark class="chunk-highlight-fuzzy">${text.slice(region.start, region.end)}</mark>`
        lastEnd = region.end
      }
      result += text.slice(lastEnd)
      return result
    }

    // FALLBACK 5: Ultimate - highlight ANY word 3+ chars that appears in both
    if (chunkWords.length > 0) {
      let result = text
      for (const word of chunkWords.slice(0, 30)) {
        try {
          const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          const wordRegex = new RegExp(`(${escaped})`, 'gi')
          result = result.replace(wordRegex, '<mark class="chunk-highlight-word">$1</mark>')
        } catch {
          // Skip
        }
      }
      if (result !== text) {
        return result
      }
    }

    return text
  }, [highlightChunkText, highlightChunkIdx, getSignificantWords, findBestMatchingRegions, normalizeForComparison])

  // Scroll to highlight (supports exact, word-based, and fuzzy highlights)
  useEffect(() => {
    if (highlightChunkText && parsedContainerRef.current) {
      const timer = setTimeout(() => {
        // Try exact highlight first, then word-based, then fuzzy
        const highlight = parsedContainerRef.current?.querySelector('.chunk-highlight') ||
                         parsedContainerRef.current?.querySelector('.chunk-highlight-word') ||
                         parsedContainerRef.current?.querySelector('.chunk-highlight-fuzzy')
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

  // Function to highlight in iframe using HTML indices when available
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
      // Also remove parent highlights
      const oldParentHighlights = iframeDoc.querySelectorAll('.sourcemapr-highlight-parent')
      oldParentHighlights.forEach((el) => {
        (el as HTMLElement).style.backgroundColor = ''
        el.classList.remove('sourcemapr-highlight-parent')
      })

      let style = iframeDoc.getElementById('sourcemapr-highlight-style')
      if (!style) {
        style = iframeDoc.createElement('style')
        style.id = 'sourcemapr-highlight-style'
        style.textContent = '.sourcemapr-highlight { background-color: #fef08a !important; padding: 2px 0; }'
        iframeDoc.head.appendChild(style)
      }

      // Collect all text nodes with their index for searching
      const textNodes: { node: Text; text: string; idx: number }[] = []
      const walker = iframeDoc.createTreeWalker(iframeDoc.body, NodeFilter.SHOW_TEXT, null)
      let node
      let nodeIdx = 0
      while ((node = walker.nextNode())) {
        const text = node.textContent ?? ''
        if (text.trim()) {
          textNodes.push({ node: node as Text, text, idx: nodeIdx })
          nodeIdx++
        }
      }

      // For rendered HTML in iframe, use text-based matching
      const searchText = highlightChunkText.replace(/\s+/g, ' ').trim()
      if (!searchText) return

      // DEBUG
      console.log('[SourcemapR] Highlighting chunk:', searchText.slice(0, 50) + '...')
      console.log('[SourcemapR] Anchors:', highlightAnchors)
      console.log('[SourcemapR] Total text nodes:', textNodes.length)

      // Build full concatenated text from ALL nodes (needed for anchor search)
      let fullConcatenatedText = ''
      const fullNodeOffsets: { node: Text; start: number; end: number; idx: number }[] = []

      for (let i = 0; i < textNodes.length; i++) {
        const item = textNodes[i]
        if (!item) continue
        const start = fullConcatenatedText.length
        fullConcatenatedText += item.text + ' '
        fullNodeOffsets.push({ node: item.node, start, end: fullConcatenatedText.length - 1, idx: i })
      }

      const fullConcatenatedLower = fullConcatenatedText.toLowerCase()

      // Helper: extract distinctive words (4+ chars, not common words)
      const getDistinctiveWords = (text: string): string[] => {
        const stopWords = new Set(['this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'which', 'would', 'could', 'should', 'about', 'these', 'those', 'other', 'into', 'more', 'some', 'such', 'than', 'them', 'then', 'there', 'when', 'where', 'will', 'your'])
        return text.toLowerCase()
          .replace(/[^a-z0-9\s]/g, ' ')
          .split(/\s+/)
          .filter(w => w.length >= 4 && !stopWords.has(w))
      }

      // Helper: count how many words from a set appear in a text region
      const countWordMatches = (words: string[], text: string): number => {
        let count = 0
        for (const word of words) {
          if (text.includes(word)) count++
        }
        return count
      }

      // Get distinctive words from chunk and anchors
      const chunkWords = getDistinctiveWords(searchText)
      const prevAnchorWords = highlightAnchors?.prevAnchor ? getDistinctiveWords(highlightAnchors.prevAnchor) : []
      const nextAnchorWords = highlightAnchors?.nextAnchor ? getDistinctiveWords(highlightAnchors.nextAnchor) : []

      console.log('[SourcemapR] Chunk words:', chunkWords.slice(0, 5))
      console.log('[SourcemapR] Prev anchor words:', prevAnchorWords.slice(0, 5))
      console.log('[SourcemapR] Next anchor words:', nextAnchorWords.slice(0, 5))

      // Find ALL candidate positions where chunk words cluster
      const candidatePositions: { pos: number; chunkScore: number; contextScore: number }[] = []
      const windowSize = 1000 // Window to look for chunk

      // Find positions of each chunk word
      for (const word of chunkWords.slice(0, 5)) {
        let searchPos = 0
        while (searchPos < fullConcatenatedLower.length) {
          const idx = fullConcatenatedLower.indexOf(word, searchPos)
          if (idx === -1) break

          // Check if we already have a nearby candidate
          const existingNearby = candidatePositions.find(c => Math.abs(c.pos - idx) < windowSize)
          if (!existingNearby) {
            candidatePositions.push({ pos: idx, chunkScore: 0, contextScore: 0 })
          }
          searchPos = idx + word.length
        }
      }

      console.log('[SourcemapR] Found', candidatePositions.length, 'candidate positions')

      // Score each candidate by chunk word matches AND surrounding context matches
      for (const candidate of candidatePositions) {
        const regionStart = Math.max(0, candidate.pos - 200)
        const regionEnd = Math.min(fullConcatenatedLower.length, candidate.pos + windowSize)
        const region = fullConcatenatedLower.slice(regionStart, regionEnd)

        // Score: how many chunk words appear in this region
        candidate.chunkScore = countWordMatches(chunkWords, region)

        // Context score: check if prev anchor words appear BEFORE and next anchor words appear AFTER
        const beforeRegion = fullConcatenatedLower.slice(Math.max(0, candidate.pos - 1500), candidate.pos)
        const afterRegion = fullConcatenatedLower.slice(candidate.pos + 500, Math.min(fullConcatenatedLower.length, candidate.pos + 2000))

        const prevScore = countWordMatches(prevAnchorWords, beforeRegion)
        const nextScore = countWordMatches(nextAnchorWords, afterRegion)
        candidate.contextScore = prevScore + nextScore
      }

      // Sort by context score first (surrounding chunks match), then by chunk score
      candidatePositions.sort((a, b) => {
        if (b.contextScore !== a.contextScore) return b.contextScore - a.contextScore
        return b.chunkScore - a.chunkScore
      })

      console.log('[SourcemapR] Top candidates:', candidatePositions.slice(0, 3).map(c =>
        `pos=${c.pos}, chunk=${c.chunkScore}, context=${c.contextScore}`
      ))

      let highlighted = false
      let bestMatchNodeIdx = -1

      // Use the best candidate position
      if (candidatePositions.length > 0 && candidatePositions[0]) {
        const bestCandidate = candidatePositions[0]

        // Only use if it has reasonable scores
        if (bestCandidate.chunkScore >= 2 || bestCandidate.contextScore >= 2) {
          // Find the node at this position
          for (const offset of fullNodeOffsets) {
            if (offset.start <= bestCandidate.pos && offset.end >= bestCandidate.pos) {
              bestMatchNodeIdx = offset.idx
              break
            }
          }
        }
      }

      // If we found a good match via context, highlight ONLY the chunk (not anchors)
      if (bestMatchNodeIdx >= 0) {
        console.log('[SourcemapR] Best match at node index:', bestMatchNodeIdx)

        // Get the position in concatenated text where match starts
        const matchOffset = fullNodeOffsets[bestMatchNodeIdx]
        if (matchOffset) {
          // Find the exact chunk text in the region around the match
          const searchStart = Math.max(0, matchOffset.start - 100)
          const searchEnd = Math.min(fullConcatenatedLower.length, matchOffset.start + searchText.length + 500)
          const searchRegion = fullConcatenatedLower.slice(searchStart, searchEnd)

          // Try to find exact chunk text match
          const chunkLower = searchText.slice(0, 200).toLowerCase().replace(/\s+/g, ' ')
          const exactIdx = searchRegion.indexOf(chunkLower.slice(0, 50))

          if (exactIdx !== -1) {
            // Find nodes that contain the actual chunk text (not anchors)
            const chunkStartInFull = searchStart + exactIdx
            const chunkEndInFull = chunkStartInFull + Math.min(searchText.length, 500)

            for (const offset of fullNodeOffsets) {
              // Only highlight nodes within the chunk bounds
              if (offset.end >= chunkStartInFull && offset.start <= chunkEndInFull) {
                try {
                  const parent = offset.node.parentElement
                  if (parent) {
                    parent.classList.add('sourcemapr-highlight-parent')
                    parent.style.backgroundColor = '#fef08a'
                  }
                } catch { /* ignore */ }
              }
            }
          } else {
            // Fallback: just highlight the match node itself
            const parent = matchOffset.node.parentElement
            if (parent) {
              parent.classList.add('sourcemapr-highlight-parent')
              parent.style.backgroundColor = '#fef08a'
            }
          }
        }

        // Scroll to the match
        const scrollNode = textNodes[bestMatchNodeIdx]
        if (scrollNode) {
          scrollNode.node.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' })
          highlighted = true
        }
      }

      // Fallback: try single node exact match
      if (!highlighted) {
        const searchLower = searchText.slice(0, 100).toLowerCase()
        for (const { node: textNode, text } of textNodes) {
          if (highlighted) break
          const normalizedText = text.replace(/\s+/g, ' ').toLowerCase()
          const matchIdx = normalizedText.indexOf(searchLower.slice(0, 50))

          if (matchIdx !== -1) {
            try {
              const range = iframeDoc.createRange()
              const highlightLen = Math.min(searchText.length, text.length - matchIdx)
              range.setStart(textNode, matchIdx)
              range.setEnd(textNode, matchIdx + highlightLen)

              const highlightEl = iframeDoc.createElement('span')
              highlightEl.className = 'sourcemapr-highlight'
              range.surroundContents(highlightEl)
              highlightEl.scrollIntoView({ behavior: 'instant', block: 'center' })
              highlighted = true
            } catch {
              textNode.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' })
              highlighted = true
            }
          }
        }
      }

      // Final fallback: try matching any 2+ distinctive words
      if (!highlighted) {
        for (const { node: textNode, text } of textNodes) {
          if (highlighted) break
          const lowerText = text.toLowerCase()
          const matchCount = chunkWords.filter(w => lowerText.includes(w)).length
          if (matchCount >= 2) {
            textNode.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' })
            const parent = textNode.parentElement
            if (parent) {
              parent.style.backgroundColor = '#fef08a'
              parent.classList.add('sourcemapr-highlight-parent')
            }
            highlighted = true
          }
        }
      }
    } catch (e) {
      console.log('Could not highlight in iframe:', e)
    }
  }, [highlightChunkText, highlightAnchors, isHtml])

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
          {isHtml && (
            <Button
              variant={sidebarViewMode === 'source' ? 'default' : 'outline'}
              size="sm"
              className="h-6 text-xs"
              onClick={() => setSidebarViewMode('source')}
            >
              <Eye className="w-3 h-3 mr-1" />
              Original
            </Button>
          )}
          {isPdf && (
            <Button
              variant={sidebarViewMode === 'source' ? 'default' : 'outline'}
              size="sm"
              className="h-6 text-xs"
              onClick={() => setSidebarViewMode('source')}
            >
              PDF
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

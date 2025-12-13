/**
 * Custom PDF Viewer using PDF.js with chunk highlighting support
 */

class ChunkHighlightPDFViewer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            scale: 1.5,
            ...options
        };
        this.pdfDoc = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.pageRendering = false;
        this.pageNumPending = null;
        this.chunks = [];
        this.selectedChunkId = null;
        this.onPageChange = options.onPageChange || (() => {});
        this.onChunkClick = options.onChunkClick || (() => {});

        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="pdf-viewer-wrapper flex flex-col h-full bg-gray-900">
                <div class="pdf-toolbar flex items-center justify-center gap-3 px-3 py-2 bg-gray-800 border-b border-gray-700">
                    <button class="pdf-btn pdf-first p-1.5 hover:bg-gray-700 rounded" title="First page">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/>
                        </svg>
                    </button>
                    <button class="pdf-btn pdf-prev p-1.5 hover:bg-gray-700 rounded" title="Previous page">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                        </svg>
                    </button>
                    <div class="flex items-center gap-2">
                        <input type="number" class="pdf-page-input w-12 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-center text-sm" value="1" min="1">
                        <span class="text-sm text-gray-400">of <span class="pdf-total-pages">0</span></span>
                    </div>
                    <button class="pdf-btn pdf-next p-1.5 hover:bg-gray-700 rounded" title="Next page">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                        </svg>
                    </button>
                    <button class="pdf-btn pdf-last p-1.5 hover:bg-gray-700 rounded" title="Last page">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"/>
                        </svg>
                    </button>
                    <div class="border-l border-gray-600 h-6 mx-2"></div>
                    <button class="pdf-btn pdf-zoom-out p-1.5 hover:bg-gray-700 rounded" title="Zoom out">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                        </svg>
                    </button>
                    <span class="pdf-zoom-level text-xs text-gray-400 w-12 text-center">150%</span>
                    <button class="pdf-btn pdf-zoom-in p-1.5 hover:bg-gray-700 rounded" title="Zoom in">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                        </svg>
                    </button>
                </div>
                <div class="pdf-canvas-container flex-1 overflow-auto bg-gray-800 flex justify-center p-4">
                    <div class="pdf-page-wrapper relative">
                        <canvas class="pdf-canvas shadow-lg"></canvas>
                        <div class="pdf-text-layer absolute top-0 left-0 pointer-events-none"></div>
                        <div class="pdf-highlight-layer absolute top-0 left-0 pointer-events-none"></div>
                    </div>
                </div>
            </div>
            <div class="pdf-loading hidden absolute inset-0 bg-gray-900/80 flex items-center justify-center z-50">
                <div class="text-center">
                    <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                    <p class="text-sm text-gray-400">Loading PDF...</p>
                </div>
            </div>
        `;

        this.canvas = this.container.querySelector('.pdf-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.highlightLayer = this.container.querySelector('.pdf-highlight-layer');
        this.canvasContainer = this.container.querySelector('.pdf-canvas-container');
        this.loadingEl = this.container.querySelector('.pdf-loading');

        this.bindEvents();
    }

    bindEvents() {
        // Navigation
        this.container.querySelector('.pdf-first').onclick = () => this.goToPage(1);
        this.container.querySelector('.pdf-prev').onclick = () => this.goToPage(this.currentPage - 1);
        this.container.querySelector('.pdf-next').onclick = () => this.goToPage(this.currentPage + 1);
        this.container.querySelector('.pdf-last').onclick = () => this.goToPage(this.totalPages);

        // Page input
        const pageInput = this.container.querySelector('.pdf-page-input');
        pageInput.onchange = (e) => {
            const page = parseInt(e.target.value) || 1;
            this.goToPage(Math.min(Math.max(1, page), this.totalPages));
        };

        // Zoom
        this.container.querySelector('.pdf-zoom-in').onclick = () => this.setScale(this.options.scale + 0.25);
        this.container.querySelector('.pdf-zoom-out').onclick = () => this.setScale(this.options.scale - 0.25);

        // Keyboard navigation
        this.canvasContainer.tabIndex = 0;
        this.canvasContainer.onkeydown = (e) => {
            if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
                this.goToPage(this.currentPage - 1);
                e.preventDefault();
            } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
                this.goToPage(this.currentPage + 1);
                e.preventDefault();
            }
        };
    }

    async loadDocument(url) {
        console.log('[PDFViewer] Starting to load PDF from:', url);
        console.log('[PDFViewer] pdfjsLib available:', typeof pdfjsLib !== 'undefined');

        // Show loading
        if (this.loadingEl) {
            this.loadingEl.classList.remove('hidden');
        }

        try {
            // Check if pdfjsLib is available
            if (typeof pdfjsLib === 'undefined') {
                throw new Error('PDF.js library not loaded. Check if the CDN is accessible.');
            }

            console.log('[PDFViewer] Creating loading task...');

            const loadingTask = pdfjsLib.getDocument({
                url: url,
                cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
                cMapPacked: true,
                withCredentials: false,
            });

            loadingTask.onProgress = (progress) => {
                if (progress.total > 0) {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    console.log(`[PDFViewer] Loading: ${percent}%`);
                }
            };

            console.log('[PDFViewer] Waiting for PDF promise...');

            // Add timeout
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('PDF load timeout after 30 seconds')), 30000);
            });

            this.pdfDoc = await Promise.race([loadingTask.promise, timeoutPromise]);

            console.log('[PDFViewer] PDF loaded successfully, pages:', this.pdfDoc.numPages);

            this.totalPages = this.pdfDoc.numPages;
            this.container.querySelector('.pdf-total-pages').textContent = this.totalPages;
            this.container.querySelector('.pdf-page-input').max = this.totalPages;

            console.log('[PDFViewer] Rendering first page...');
            await this.renderPage(this.currentPage);
            console.log('[PDFViewer] First page rendered');

        } catch (error) {
            console.error('[PDFViewer] Error loading PDF:', error);

            const canvasContainer = this.container.querySelector('.pdf-canvas-container');
            if (canvasContainer) {
                canvasContainer.innerHTML = `
                    <div class="text-center text-red-400 p-8">
                        <p class="text-lg font-bold">Failed to load PDF</p>
                        <p class="text-sm text-gray-400 mt-2">${error.message || 'Unknown error'}</p>
                        <p class="text-xs text-gray-500 mt-4 break-all">URL: ${url}</p>
                    </div>
                `;
            }
        } finally {
            // Always hide loading
            if (this.loadingEl) {
                this.loadingEl.classList.add('hidden');
            }
        }
    }

    async renderPage(num) {
        if (!this.pdfDoc) return;

        this.pageRendering = true;

        try {
            const page = await this.pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: this.options.scale });

            this.canvas.height = viewport.height;
            this.canvas.width = viewport.width;
            this.highlightLayer.style.width = viewport.width + 'px';
            this.highlightLayer.style.height = viewport.height + 'px';

            const renderContext = {
                canvasContext: this.ctx,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            this.currentPage = num;
            this.container.querySelector('.pdf-page-input').value = num;
            this.updateButtonStates();
            this.renderHighlights(viewport);
            this.onPageChange(num);

        } catch (error) {
            console.error('Error rendering page:', error);
        }

        this.pageRendering = false;

        if (this.pageNumPending !== null) {
            const pending = this.pageNumPending;
            this.pageNumPending = null;
            await this.renderPage(pending);
        }
    }

    goToPage(num) {
        if (num < 1 || num > this.totalPages) return;

        if (this.pageRendering) {
            this.pageNumPending = num;
        } else {
            this.renderPage(num);
        }
    }

    setScale(scale) {
        this.options.scale = Math.min(Math.max(0.5, scale), 3);
        this.container.querySelector('.pdf-zoom-level').textContent =
            Math.round(this.options.scale * 100) + '%';
        this.renderPage(this.currentPage);
    }

    updateButtonStates() {
        const isFirst = this.currentPage <= 1;
        const isLast = this.currentPage >= this.totalPages;

        this.container.querySelector('.pdf-first').classList.toggle('opacity-30', isFirst);
        this.container.querySelector('.pdf-prev').classList.toggle('opacity-30', isFirst);
        this.container.querySelector('.pdf-next').classList.toggle('opacity-30', isLast);
        this.container.querySelector('.pdf-last').classList.toggle('opacity-30', isLast);
    }

    showLoading(show) {
        this.loadingEl.classList.toggle('hidden', !show);
    }

    setChunks(chunks) {
        this.chunks = chunks || [];
        if (this.pdfDoc) {
            this.renderPage(this.currentPage);
        }
    }

    selectChunk(chunkId) {
        this.selectedChunkId = chunkId;
        const chunk = this.chunks.find(c => c.chunk_id === chunkId);
        if (chunk && chunk.page_number) {
            this.goToPage(chunk.page_number);
        } else {
            this.renderHighlights();
        }
    }

    renderHighlights(viewport) {
        if (!viewport && this.pdfDoc) {
            this.pdfDoc.getPage(this.currentPage).then(page => {
                const vp = page.getViewport({ scale: this.options.scale });
                this._renderHighlightsWithViewport(vp);
            });
        } else if (viewport) {
            this._renderHighlightsWithViewport(viewport);
        }
    }

    _renderHighlightsWithViewport(viewport) {
        this.highlightLayer.innerHTML = '';

        // Get chunks for current page
        const pageChunks = this.chunks.filter(c => c.page_number === this.currentPage);

        if (pageChunks.length === 0) return;

        // Create highlight badges for each chunk on this page
        const pageHeight = viewport.height;
        const chunkHeight = Math.min(40, pageHeight / pageChunks.length);

        pageChunks.forEach((chunk, index) => {
            const isSelected = chunk.chunk_id === this.selectedChunkId;

            // Create a highlight indicator on the side
            const indicator = document.createElement('div');
            indicator.className = `absolute right-0 rounded-l-lg cursor-pointer transition-all flex items-center gap-1 px-2 py-1 text-xs font-medium ${
                isSelected
                    ? 'bg-blue-500 text-white shadow-lg'
                    : 'bg-yellow-500/80 text-yellow-900 hover:bg-yellow-400'
            }`;
            indicator.style.top = `${10 + index * (chunkHeight + 5)}px`;
            indicator.title = `Chunk #${chunk.index}: ${(chunk.text || '').slice(0, 100)}...`;
            indicator.innerHTML = `
                <span class="font-bold">#${chunk.index}</span>
                ${isSelected ? '<span class="text-[10px]">SELECTED</span>' : ''}
            `;
            indicator.onclick = () => {
                this.selectedChunkId = chunk.chunk_id;
                this.onChunkClick(chunk);
                this.renderHighlights(viewport);
            };

            this.highlightLayer.appendChild(indicator);

            // If selected, add a subtle page overlay effect
            if (isSelected) {
                const overlay = document.createElement('div');
                overlay.className = 'absolute inset-0 border-4 border-blue-500 rounded pointer-events-none';
                overlay.style.boxShadow = 'inset 0 0 20px rgba(59, 130, 246, 0.2)';
                this.highlightLayer.appendChild(overlay);
            }
        });
    }

    getCurrentPage() {
        return this.currentPage;
    }

    getTotalPages() {
        return this.totalPages;
    }

    destroy() {
        if (this.pdfDoc) {
            this.pdfDoc.destroy();
        }
        this.container.innerHTML = '';
    }
}

/**
 * Parsed Text Viewer with chunk highlighting
 */
class ChunkHighlightTextViewer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.pages = [];
        this.chunks = [];
        this.currentPage = 1;
        this.selectedChunkId = null;
        this.onPageChange = options.onPageChange || (() => {});
        this.onChunkClick = options.onChunkClick || (() => {});

        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="text-viewer-wrapper flex flex-col h-full">
                <div class="text-toolbar flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
                    <div class="flex items-center gap-2 text-xs text-gray-400">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <span>Parsed Text</span>
                    </div>
                    <div class="text-page-info text-xs text-gray-400">Page 1</div>
                </div>
                <div class="text-chunks-bar flex items-center gap-1 px-2 py-1 bg-gray-800/50 border-b border-gray-700 overflow-x-auto">
                    <span class="text-xs text-gray-500">Chunks:</span>
                    <div class="chunk-badges flex gap-1"></div>
                </div>
                <div class="text-content flex-1 overflow-y-auto p-4 bg-gray-900/50">
                    <pre class="text-sm whitespace-pre-wrap font-mono"></pre>
                </div>
            </div>
        `;

        this.contentEl = this.container.querySelector('.text-content pre');
        this.pageInfoEl = this.container.querySelector('.text-page-info');
        this.chunkBadgesEl = this.container.querySelector('.chunk-badges');
    }

    setPages(pages) {
        this.pages = pages || [];
        this.renderPage(this.currentPage);
    }

    setChunks(chunks) {
        this.chunks = chunks || [];
        this.renderChunkBadges();
        this.renderPage(this.currentPage);
    }

    goToPage(num) {
        if (num < 1 || num > this.pages.length) return;
        this.currentPage = num;
        this.renderPage(num);
        this.onPageChange(num);
    }

    selectChunk(chunkId) {
        this.selectedChunkId = chunkId;
        const chunk = this.chunks.find(c => c.chunk_id === chunkId);
        if (chunk && chunk.page_number) {
            this.goToPage(chunk.page_number);
        } else {
            this.renderPage(this.currentPage);
        }
        this.renderChunkBadges();
    }

    renderChunkBadges() {
        const pageChunks = this.chunks.filter(c => c.page_number === this.currentPage);

        if (pageChunks.length === 0) {
            this.chunkBadgesEl.innerHTML = '<span class="text-xs text-gray-600">No chunks on this page</span>';
            return;
        }

        this.chunkBadgesEl.innerHTML = pageChunks.map(chunk => {
            const isSelected = chunk.chunk_id === this.selectedChunkId;
            return `
                <button onclick="window._textViewer?.onChunkBadgeClick?.('${chunk.chunk_id}')"
                        class="px-2 py-0.5 rounded text-xs font-medium transition-all ${
                            isSelected
                                ? 'bg-blue-500 text-white'
                                : 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/40'
                        }">
                    #${chunk.index}
                </button>
            `;
        }).join('');
    }

    renderPage(num) {
        if (num < 1 || num > this.pages.length) {
            this.contentEl.textContent = 'No content';
            return;
        }

        this.currentPage = num;
        this.pageInfoEl.textContent = `Page ${num} of ${this.pages.length}`;

        const pageText = this.pages[num - 1] || '';
        const pageChunks = this.chunks.filter(c => c.page_number === num);

        // If a chunk is selected and on this page, highlight it
        const selectedChunk = pageChunks.find(c => c.chunk_id === this.selectedChunkId);

        if (selectedChunk && selectedChunk.text) {
            // Try to highlight the chunk text in the page
            const chunkText = selectedChunk.text.trim();
            const escapedChunk = this.escapeHtml(chunkText);
            const escapedPage = this.escapeHtml(pageText);

            // Find and highlight
            const highlightedHtml = escapedPage.replace(
                new RegExp(this.escapeRegex(escapedChunk.slice(0, 100)), 'g'),
                match => `<mark class="bg-blue-500/40 text-white rounded px-0.5">${match}</mark>`
            );

            this.contentEl.innerHTML = highlightedHtml;

            // Scroll to highlight
            const mark = this.contentEl.querySelector('mark');
            if (mark) {
                mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            this.contentEl.textContent = pageText;
        }

        this.renderChunkBadges();
    }

    escapeHtml(text) {
        if (!text) return '';
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    getCurrentPage() {
        return this.currentPage;
    }

    onChunkBadgeClick(chunkId) {
        this.selectChunk(chunkId);
        const chunk = this.chunks.find(c => c.chunk_id === chunkId);
        if (chunk) {
            this.onChunkClick(chunk);
        }
    }

    destroy() {
        this.container.innerHTML = '';
    }
}

// Export for use
window.ChunkHighlightPDFViewer = ChunkHighlightPDFViewer;
window.ChunkHighlightTextViewer = ChunkHighlightTextViewer;

/* ================================================================
   MDV Viewer
   Depends on: shared.js (must be loaded before this script)
   ================================================================ */

document.addEventListener('DOMContentLoaded', onPageLoad);

// Uses shared utilities from shared.js:
// - MDV_TIMING
// - MDV_CLASSES
// - mdvEscapeHtml, mdvFuzzyMatch, mdvCreateHighlighter
// - mdvAddTempHighlight
// - mdvIsInputFocused, mdvIsModKey

// -----------------------------------------------------------------------------
// PAGE STATE AND VARIABLES
// -----------------------------------------------------------------------------
const MD_BODY = document.getElementById('markdown-body')
const DIR_TREE = document.getElementById('dtree-container')
const TOC_TREE = document.getElementById('toc-container')

const dirTreeState = {
  entryMap: {},
  cachedLis: null,
  cachedEntries: null,
};

// Use shared classes instead of local definitions
const commonClasses = MDV_CLASSES;

const treeClasses = Object.freeze({
  tree: 'tree',
  entry: 'tree-entry',
  collapsed: 'tree-collapsed',
  nested: 'nested',
  active: 'active',
});

// Shared utilities from shared.js
const escapeHtml = mdvEscapeHtml;
const fuzzyMatch = mdvFuzzyMatch;
const createHighlighter = mdvCreateHighlighter;

// -----------------------------------------------------------------------------

function onPageLoad() {
  loadDirTree(DIR_TREE);
  setupSearch();
  if (MD_BODY && TOC_TREE) generateTOC(MD_BODY, TOC_TREE);
  processSearchQuery();
  setupModalsAndHeader();
  setupHeadingObserver();
  
  setTimeout(() => {
     if (window.location.hash) {
        const h = document.getElementById(window.location.hash.substring(1));
        if (h) {
           h.scrollIntoView({ block: 'start', behavior: 'auto' });
           addTempHighlight(h);
        }
     }
     
     // Force a scroll event to sync initial TOC highlights
     const mainSection = document.getElementById('section-main');
     if (mainSection) mainSection.dispatchEvent(new Event('scroll'));
  }, 100);
}

// Global modal close function (needs to be accessible from search handlers)
let _closeAllModals = null;

function closeAllModals() {
  if (_closeAllModals) _closeAllModals();
}

function setupModalsAndHeader() {
  const overlay = document.getElementById('modal-overlay');
  const dirModal = document.getElementById('dir-modal');
  const searchModal = document.getElementById('search-modal');
  
  const btnDir = document.getElementById('btn-dir-explorer');
  const btnSearch = document.getElementById('btn-search');
  const btnTheme = document.getElementById('btn-theme-toggle');

  const dirFilterInput = document.getElementById('dir-filter-input');
  const searchInput = document.getElementById('search-input');

  if (!overlay || !btnTheme) return; // fail gracefully

  // Track which modal is open for keyboard navigation
  let activeModal = null;

  function openModal(modal, focusInput) {
    if (!modal) return;
    overlay.classList.remove('hidden');
    modal.classList.remove('hidden');
    activeModal = modal;
    setTimeout(() => { if (focusInput) focusInput.focus(); }, 100);
  }

  _closeAllModals = function() {
    overlay.classList.add('hidden');
    if (dirModal) dirModal.classList.add('hidden');
    if (searchModal) searchModal.classList.add('hidden');
    activeModal = null;
    dirKeyboardIndex = -1;
    searchKeyboardIndex = -1;
    dirKeyboardActiveEntry = null;
    searchKeyboardActiveItem = null;
  };

  // Auto-select first dir entry after tree loads
  if (btnDir) {
      btnDir.addEventListener('click', () => {
        // Refresh the directory tree on every open to reflect latest file system state
        dirTreeState.entryMap = {};
        loadDirTree(DIR_TREE).then(() => {
          // Re-apply filter if one is active
          const q = dirFilterInput.value.trim().toLowerCase();
          if (q) {
            dirFilterInput.dispatchEvent(new Event('input'));
          } else {
            // Auto-select first entry
            autoSelectFirstDirEntry();
          }
        });
        openModal(dirModal, dirFilterInput);
      });
  }
  
  if (btnSearch) btnSearch.addEventListener('click', () => openModal(searchModal, searchInput));
  overlay.addEventListener('click', closeAllModals);

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    // Escape to close modals
    if (e.key === 'Escape') {
      closeAllModals();
      return;
    }

    // Handle arrow keys & enter in modals
    if (activeModal) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
        if (activeModal === dirModal) {
          handleDirKeyboard(e);
        } else if (activeModal === searchModal) {
          handleSearchKeyboard(e);
        }
        return;
      }
    }
    
    const isInputFocused = document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
    
    // Cmd/Ctrl + Shift + F   OR  bare '/' (like GitHub) : Global Content Search
    const isSearchHotKey = ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'f') || (!isInputFocused && e.key === '/');
    if (isSearchHotKey) {
      e.preventDefault();
      if (btnSearch) btnSearch.click();
    }
    
    // Cmd/Ctrl + Shift + E   OR  bare '.' : Directory Explorer
    const isDirHotKey = ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'e') || (!isInputFocused && e.key === '.');
    if (isDirHotKey) {
      e.preventDefault();
      if (btnDir) btnDir.click();
    }
  });

  // Directory filter logic
  if (dirFilterInput) {
      dirFilterInput.addEventListener('input', (e) => {
        dirKeyboardIndex = -1; // Reset keyboard selection on filter change
        const q = e.target.value.trim().toLowerCase();
        // Use cached references instead of re-querying DOM each keystroke
        const allLis = dirTreeState.cachedLis;
        const entries = dirTreeState.cachedEntries;
        if (!allLis || !entries) return;
        
        if (q === '') {
          for (let i = 0; i < allLis.length; i++) allLis[i].style.display = '';
          for (let i = 0; i < entries.length; i++) {
            if (entries[i].dataset.fullPath) entries[i].textContent = entries[i].dataset.fullPath;
          }
          autoSelectFirstDirEntry();
          return;
        }

        const highlight = createHighlighter(q);

        // Fast reveal for fuzzy matches without tree hierarchy calculations
        for (let i = 0; i < entries.length; i++) {
           const entry = entries[i];
           const pathName = entry.dataset.fullPath || '';
           if (fuzzyMatch(pathName, q)) {
              entry.parentElement.style.display = '';
              if (pathName.toLowerCase().includes(q)) {
                  entry.innerHTML = highlight(escapeHtml(pathName));
              } else {
                  entry.textContent = pathName;
              }
           } else {
              entry.parentElement.style.display = 'none';
              entry.textContent = pathName;
           }
        }
        // Auto-select first visible dir entry after filtering
        autoSelectFirstDirEntry();
      });
  }

  // Theme Toggler is already handled in live.html but here it binds globally
  // We can leave this but `live.html` binds it differently. Wait, if we use `viewer.js` in `live.html`, 
  // we should remove the redundant binding from `live.html` or just let it bind twice (it uses `classList.toggle`, twice means it undoes itself!).
  // So we MUST NOT double-bind. `live.html` should just let `viewer.js` handle it, or we check if it is already bound.
  // Actually, I'll remove it from `live.html`.
  btnTheme.addEventListener('click', () => {
    mdvToggleTheme(); // Use shared function from shared.js
  });
}

// -----------------------------------------------------------------------------
// KEYBOARD NAVIGATION FOR MODALS
// -----------------------------------------------------------------------------

let dirKeyboardIndex = -1;
let searchKeyboardIndex = -1;
let dirKeyboardActiveEntry = null;
let searchKeyboardActiveItem = null;

function autoSelectFirstDirEntry() {
  const visible = getVisibleDirEntries();
  if (visible.length > 0) {
    dirKeyboardIndex = 0;
    updateDirKeyboardHighlight(visible);
  }
}

function autoSelectFirstSearchResult() {
  const items = getVisibleSearchItems();
  if (items.length > 0) {
    searchKeyboardIndex = 0;
    updateSearchKeyboardHighlight(items);
  }
}

function getVisibleDirEntries() {
  if (!dirTreeState.cachedLis) return [];
  return dirTreeState.cachedLis.filter(li => li.style.display !== 'none');
}

function handleDirKeyboard(e) {
  const visible = getVisibleDirEntries();
  if (visible.length === 0) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    dirKeyboardIndex = Math.min(dirKeyboardIndex + 1, visible.length - 1);
    updateDirKeyboardHighlight(visible);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    dirKeyboardIndex = Math.max(dirKeyboardIndex - 1, 0);
    updateDirKeyboardHighlight(visible);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (dirKeyboardIndex >= 0 && dirKeyboardIndex < visible.length) {
      const entry = visible[dirKeyboardIndex].querySelector('.tree-entry');
      if (entry && entry.href) {
        window.location.href = entry.href;
      }
    }
  }
}

function updateDirKeyboardHighlight(visible) {
  // O(1): clear only the previously active entry instead of iterating all
  if (dirKeyboardActiveEntry) {
    dirKeyboardActiveEntry.classList.remove('keyboard-active');
    dirKeyboardActiveEntry = null;
  }
  if (dirKeyboardIndex >= 0 && dirKeyboardIndex < visible.length) {
    const entry = visible[dirKeyboardIndex].querySelector('.tree-entry');
    if (entry) {
      entry.classList.add('keyboard-active');
      entry.scrollIntoView({ block: 'nearest', behavior: 'auto' });
      dirKeyboardActiveEntry = entry;
    }
  }
}

function getVisibleSearchItems() {
  return Array.from(document.querySelectorAll('#search-results-content > li'));
}

function handleSearchKeyboard(e) {
  const items = getVisibleSearchItems();
  if (items.length === 0) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    searchKeyboardIndex = Math.min(searchKeyboardIndex + 1, items.length - 1);
    updateSearchKeyboardHighlight(items);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    searchKeyboardIndex = Math.max(searchKeyboardIndex - 1, 0);
    updateSearchKeyboardHighlight(items);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (searchKeyboardIndex >= 0 && searchKeyboardIndex < items.length) {
      const a = items[searchKeyboardIndex].querySelector('a');
      if (a && a.href) {
        window.location.href = a.href;
      }
    }
  }
}

function updateSearchKeyboardHighlight(items) {
  // O(1): clear only the previously active item instead of iterating all
  if (searchKeyboardActiveItem) {
    searchKeyboardActiveItem.classList.remove('keyboard-active');
    searchKeyboardActiveItem = null;
  }
  if (searchKeyboardIndex >= 0 && searchKeyboardIndex < items.length) {
    items[searchKeyboardIndex].classList.add('keyboard-active');
    items[searchKeyboardIndex].scrollIntoView({ block: 'nearest', behavior: 'auto' });
    searchKeyboardActiveItem = items[searchKeyboardIndex];
  }
}

// -----------------------------------------------------------------------------

function processSearchQuery() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  const l = params.get('l');
  
  if (q && l) {
    const lineno = parseInt(l, 10);
    if (!isNaN(lineno)) {
      scrollToSourceLine(lineno, q, { behavior: 'auto', block: 'center' });
    }
  }
}

function highlightTextInNode(node, query) {
  const words = query
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (words.length === 0) return;
  const regex = new RegExp(`(${words.join('|')})`, 'gi');
  
  const textNodes = [];
  function collectTextNodes(n) {
    if (n.nodeType === 3 && n.nodeValue.trim()) {
      textNodes.push({ node: n, text: n.nodeValue });
    } else if (n.nodeType === 1 && !['SCRIPT', 'STYLE', 'SPAN'].includes(n.tagName)) {
      Array.from(n.childNodes).forEach(collectTextNodes);
    }
  }
  collectTextNodes(node);
  
  const insertedSpans = [];

  textNodes.forEach((t) => {
    let text = t.text;
    let replaced = false;
    let parts = [];
    let lastIdx = 0;
    
    let match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(document.createTextNode(text.slice(lastIdx, match.index)));
      }
      const span = document.createElement('span');
      span.textContent = match[0];
      span.style.borderRadius = '3px';
      span.style.padding = '0 0.15rem';
      span.style.color = 'inherit';
      span.dataset.searchHighlight = '1';
      addTempHighlight(span, 4000, 700);
      insertedSpans.push(span);
      parts.push(span);
      lastIdx = regex.lastIndex;
      replaced = true;
    }
    if (replaced) {
      if (lastIdx < text.length) {
        parts.push(document.createTextNode(text.slice(lastIdx)));
      }
      const frag = document.createDocumentFragment();
      parts.forEach((p) => frag.appendChild(p));
      if (t.node.parentNode) t.node.parentNode.replaceChild(frag, t.node);
    }
  });

  // After highlight fades, unwrap spans to restore original text nodes
  if (insertedSpans.length > 0) {
    const cleanupDelay = 4000 + 700 + 50; // duration + transitionMs + buffer
    setTimeout(() => unwrapHighlightSpans(insertedSpans, node), cleanupDelay);
  }
}

function unwrapHighlightSpans(spans, containerNode) {
  spans.forEach(span => {
    if (!span.parentNode) return;
    const text = document.createTextNode(span.textContent);
    span.parentNode.replaceChild(text, span);
  });
  // Merge adjacent text nodes to fully restore original DOM structure
  if (containerNode && containerNode.normalize) {
    containerNode.normalize();
  }
}

// --------------------------------------------------------------------------------

// Use timing constants from shared.js
const constants = MDV_TIMING;

const state = {
  activeIndices: [],
  headings: [],
  headingEntries: [],
};

let isTocClickScrolling = false;

let isHeadingObserverSetup = false;
let animFrame = null;

function setupHeadingObserver() {
  if (!state.headings || !state.headings.length) return;

  const mainSection = document.getElementById('section-main');
  if (!mainSection) return;
  
  if (!isHeadingObserverSetup) {
    isHeadingObserverSetup = true;
    window._mdv_global_scroll_handler = () => {
      if (isTocClickScrolling || !state.headings || !state.headings.length) return;
      const ms = document.getElementById('section-main');
      if (!ms) return;
      
      if (animFrame) cancelAnimationFrame(animFrame);
      animFrame = requestAnimationFrame(() => {
        const tops = Array.from(state.headings).map(h => h.getBoundingClientRect().top);
        const mdBodyBottom = MD_BODY && MD_BODY.getBoundingClientRect ? MD_BODY.getBoundingClientRect().bottom : window.innerHeight;
        
        const mainRect = ms.getBoundingClientRect();
        const viewTop = Math.max(mainRect.top, 0);
        const viewBottom = Math.min(mainRect.bottom, window.innerHeight);

        const activeIndices = [];
        for (let i = 0; i < state.headings.length; i++) {
           const top = tops[i];
           const bottom = (i + 1 < state.headings.length) ? tops[i+1] : mdBodyBottom;
           
           if (top < viewBottom - 10 && bottom > viewTop + 10) {
             activeIndices.push(i);
           }
        }
        
        if (activeIndices.length === 0 && state.headings.length > 0) {
          activeIndices.push(0);
        }
        
        updateActiveTocItems(activeIndices);
      });
    };

    mainSection.addEventListener('scroll', window._mdv_global_scroll_handler, { passive: true });
    window.addEventListener('scroll', window._mdv_global_scroll_handler, { passive: true });
  } else if (window._mdv_global_scroll_handler) {
    // When re-rendering, just trigger an immediate update
    window._mdv_global_scroll_handler();
  }
}

function updateActiveTocItems(indices) {
  if (state.activeIndices && state.activeIndices.length === indices.length && state.activeIndices.every((val, i) => val === indices[i])) {
    return;
  }
  
  if (state.activeIndices) {
    state.activeIndices.forEach(idx => {
      if (state.headingEntries[idx]) {
        state.headingEntries[idx].classList.remove(treeClasses.active);
      }
    });
  }
  
  state.activeIndices = indices;
  let firstTarget = null;
  
  indices.forEach(idx => {
    const target = state.headingEntries[idx];
    if (target) {
      target.classList.add(treeClasses.active);
      if (!firstTarget) firstTarget = target;
    }
  });
  
  if (firstTarget && !isTocClickScrolling) {
    const tocContainer = document.getElementById('toc-container');
    const targetRect = firstTarget.getBoundingClientRect();
    const containerRect = tocContainer.getBoundingClientRect();
    
    if (targetRect.top < containerRect.top + 30 || targetRect.bottom > containerRect.bottom - 30) {
        const topPos = tocContainer.scrollTop + (targetRect.top - containerRect.top) - containerRect.height / 2;
        tocContainer.scrollTo({
            top: topPos,
            behavior: 'smooth'
        });
    }
  }
}


function generateTOC(contentContainer, treeContainer) {

  state.headings = contentContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
  state.curHeadings = null;
  state.headingEntries = new Array(state.headings.length);
  state.activeIndices = []; // Reset this to force re-highlighting of new DOM nodes


  const root = [];
  const stack = [{ level: 0, children: root }];

    state.headings.forEach((h, idx) => {
    const level = parseInt(h.tagName[1]);
    const node = {
      name: h.textContent,
      children: [],
      action: function (e) {
        if (e.ctrlKey || e.metaKey || e.button === 1) return;
        e.preventDefault();
        
        isTocClickScrolling = true;
        updateActiveTocItems([idx]);
        
        h.scrollIntoView({ block: 'start', behavior: 'smooth' });
        
        if (h.id && window.location.hash !== '#' + h.id) {
          history.pushState(null, null, '#' + h.id);
        }
        addTempHighlight(h);
        
        // Re-enable observer when scroll is roughly done
        setTimeout(() => { isTocClickScrolling = false; }, 800);
      },
      href: `${window.location.pathname}#${h.id}`,
      collapsed: false,
      metadata: {
        index: idx,
      },
      render: (item, entry) => {
        state.headingEntries[item.metadata.index] = entry;
      },
    };
    while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
    stack[stack.length - 1].children.push(node);
    stack.push({ level, children: node.children });
  });
  renderTree(treeContainer, root);
}

// -------------------------------------------------------------------------------- 

const elems = {
  input: null,
  resultsPanel: null,
  contentResults: null,
};

// Search category filters — all active by default
const searchCategories = {
  heading: true,
  code: true,
  text: true,
  link: true,
  list: true,
};

let searchAbortController = null;

function getActiveCategories() {
  return Object.keys(searchCategories).filter(k => searchCategories[k]);
}

function setupElems() {
  elems.input = document.getElementById('search-input');
  elems.resultsPanel = document.getElementById('search-results');
  elems.contentResults = document.getElementById('search-results-content');
}

function prepareSearchPanel() {
  elems.resultsPanel.style.display = 'flex';
}

function scrollToSourceLine(lineno, highlightQuery, { behavior = 'smooth', block = 'start' } = {}) {
  let targetLine = lineno;
  let targetEl = null;
  while (targetLine > 0) {
    targetEl = document.querySelector(`[data-source-line="${targetLine}"]`);
    if (targetEl) break;
    targetLine--;
  }
  if (targetEl) {
    isTocClickScrolling = true;
    targetEl.scrollIntoView({ behavior, block });
    addTempHighlight(targetEl);
    setTimeout(() => { isTocClickScrolling = false; }, 800);
    if (highlightQuery) {
      highlightTextInNode(targetEl, highlightQuery);
    }
  }
}

function getCurrentFilePath() {
  const match = window.location.pathname.match(/\/v\/(.+)/);
  return match ? match[1] : null;
}

function getTypeBadge(item) {
  if (item.line_type === 'heading') {
    return `H${item.level || 1}`;
  }
  const badges = { code: 'CODE', link: 'LINK', list: 'LIST', text: 'TXT' };
  return badges[item.line_type] || 'TXT';
}

function getBadgeClass(item) {
  if (item.line_type === 'heading') return 'badge-heading';
  const classes = { code: 'badge-code', link: 'badge-link', list: 'badge-list', text: 'badge-text' };
  return classes[item.line_type] || 'badge-text';
}

async function search() {
  prepareSearchPanel();
  elems.contentResults.innerHTML = '';
  searchKeyboardIndex = -1;

  const query = elems.input.value.trim();
  if (!query) {
    elems.contentResults.innerHTML = '';
    return;
  }

  // Cancel any in-flight request
  if (searchAbortController) searchAbortController.abort();
  searchAbortController = new AbortController();

  try {
    // Build search URL with active category types
    const activeTypes = getActiveCategories();
    let searchUrl = `/api/search?query=${encodeURIComponent(query)}`;
    if (activeTypes.length > 0 && activeTypes.length < 5) {
      searchUrl += `&types=${activeTypes.join(',')}`;
    }

    const response = await fetch(searchUrl, { signal: searchAbortController.signal });
    const results = await response.json();

    if (results.length === 0) {
      elems.contentResults.innerHTML = '<li class="search-empty-msg">No results found.</li>';
      return;
    }

    const currentPath = getCurrentFilePath();
    const highlight = createHighlighter(query);

    const frag = document.createDocumentFragment();

    results.forEach((item) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.style.display = 'block';
      a.style.textDecoration = 'none';
      a.style.color = 'inherit';

      a.href = `/v/${item.path}?q=${encodeURIComponent(query)}&l=${item.lineno}`;

      // Same-page: scroll directly
      if (currentPath === item.path) {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          closeAllModals();
          scrollToSourceLine(item.lineno, query);
        });
      }

      const safeLine = escapeHtml(item.line || '');
      const safePath = escapeHtml(item.path);
      const badge = getTypeBadge(item);
      const badgeClass = getBadgeClass(item);

      a.innerHTML = `<div class="search-result-item">
        <span class="line-type-badge ${badgeClass}">${badge}</span>
        <span class="search-result-line">${highlight(safeLine)}</span>
        <span class="search-result-path">${safePath}</span>
      </div>`;

      li.appendChild(a);
      frag.appendChild(li);
    });
    elems.contentResults.appendChild(frag);

    // Auto-select first result
    autoSelectFirstSearchResult();
  } catch (err) {
    if (err.name !== 'AbortError') throw err;
  }
}

function setupSearch() {
  setupElems();
  if (!elems.input) return;
  let debounceTimer = null;
  elems.input.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(search, 200);
  });

  // Setup category filter pills
  const categoryBar = document.getElementById('search-category-bar');
  if (categoryBar) {
    categoryBar.addEventListener('click', (e) => {
      const pill = e.target.closest('.search-cat-pill');
      if (!pill) return;
      const cat = pill.dataset.category;
      if (!cat) return;

      // Toggle this category
      searchCategories[cat] = !searchCategories[cat];
      pill.classList.toggle('active', searchCategories[cat]);

      // Ensure at least one category is active
      const anyActive = Object.values(searchCategories).some(v => v);
      if (!anyActive) {
        searchCategories[cat] = true;
        pill.classList.add('active');
        return;
      }

      // Re-trigger search with current input
      if (elems.input.value.trim()) {
        clearTimeout(debounceTimer);
        search();
      }
    });

    // Invert selection button
    const invertBtn = document.getElementById('search-cat-invert');
    if (invertBtn) {
      invertBtn.addEventListener('click', () => {
        const pills = categoryBar.querySelectorAll('.search-cat-pill');
        // Compute what the inverted state would look like
        const willBeActive = {};
        for (const key of Object.keys(searchCategories)) {
          willBeActive[key] = !searchCategories[key];
        }
        // Only invert if at least one category would remain active
        const anyWouldBeActive = Object.values(willBeActive).some(v => v);
        if (!anyWouldBeActive) return;

        // Apply the inversion
        for (const key of Object.keys(searchCategories)) {
          searchCategories[key] = willBeActive[key];
        }
        pills.forEach(pill => {
          const cat = pill.dataset.category;
          if (cat) pill.classList.toggle('active', searchCategories[cat]);
        });

        // Re-trigger search
        if (elems.input.value.trim()) {
          clearTimeout(debounceTimer);
          search();
        }
      });
    }
  }
}

// highlightMatches kept as a convenience wrapper for one-off calls
function highlightMatches(text, query) {
  return createHighlighter(query)(text);
}

// ------------------------------------------------------------------------------
// DIR TREE
// ------------------------------------------------------------------------------

function getDirTreeIds() {
  return Object.keys(dirTreeState.entryMap);
}

function extractPath(url) {
  const match = url.match(/\/v\/([^?#]+)/);
  return match ? match[1] : null;
}

// Helper to expand and highlight the current file in the directory tree
function highlightCurrentFileInDirTree() {
  const id=extractPath(window.location.pathname);
  if (!id) return;

  if (id == null || !(id in dirTreeState.entryMap)) {
    return;
  }
  const entry = dirTreeState.entryMap[id];
  entry.classList.add('current-file');
  setTimeout(() => entry.scrollIntoView({ block: 'center', behavior: 'smooth' }), 100);
}

// Dir tree related
function loadDirTree(container, callback) {
  function flattenDirTree(tree, flatList = [], pathPrefix = '') {
    tree.forEach(item => {
      const fullPath = pathPrefix ? `${pathPrefix}/${item.name}` : item.name;
      if (item.type === 'directory') {
        flattenDirTree(item.children || [], flatList, fullPath);
      } else {
        flatList.push({
          name: item.name,
          fullPath: fullPath,
          href: '/v/' + item.path,
          metadata: { id: item.path }
        });
      }
    });
    return flatList;
  }

  return fetch('/api/tree')
    .then((res) => res.json())
    .then((tree) => {
      const flatFiles = flattenDirTree(tree);
      renderFlatTree(container, flatFiles);
      highlightCurrentFileInDirTree();
    });
}

function renderFlatTree(container, flatFiles) {
  const frag = document.createDocumentFragment();
  const ul = document.createElement('ul');
  ul.classList.add(treeClasses.tree);
  ul.style.listStyle = 'none';
  ul.style.paddingLeft = '0';

  flatFiles.forEach(item => {
    const li = document.createElement('li');
    li.classList.add(treeClasses.tree);
    
    const entry = document.createElement('a');
    entry.classList.add(treeClasses.entry);
    entry.textContent = item.fullPath;
    entry.style.setProperty('--tree-depth', 0);
    entry.title = item.fullPath;
    entry.href = item.href;
    
    entry.dataset.fullPath = item.fullPath;

    li.appendChild(entry);
    dirTreeState.entryMap[item.metadata.id] = entry;
    ul.appendChild(li);
  });

  frag.appendChild(ul);
  container.innerHTML = '';
  container.appendChild(frag);

  // Cache DOM references for the filter handler
  dirTreeState.cachedLis = Array.from(ul.querySelectorAll('li'));
  dirTreeState.cachedEntries = Array.from(ul.querySelectorAll('.tree-entry'));
}

function renderTreeRecursive(tree, parentNode, depth = 0) {
  tree.forEach((item) => {
    /* item should have keys:
       - name: Display name
       - metadata: some internal value the item signifies (could be object)
       - action: the on-click function
       - href: useful in some cases
       - children: optionally, children of the element
       - collapsed: whether to start collapsed
       - render: optional function to trigger on the entry upon rendering
     */
    const li = document.createElement('li');
    li.classList.add(treeClasses.tree);

    if (item.collapsed) {
      li.classList.add(treeClasses.collapsed);
    }

    const entry = document.createElement('a');
    entry.classList.add(treeClasses.entry);
    entry.textContent = item.name;
    entry.style.setProperty('--tree-depth', depth);
    entry.addEventListener('click', item.action);

    // For tooltip
    entry.title = item.name;

    if (item.href) {
      entry.href = item.href;
    }

    li.appendChild(entry);
    if (item.render) {
      item.render(item, entry);
    }

    if (item.children && item.children.length) {
      const ul = document.createElement('ul');
      ul.classList.add(treeClasses.nested);
      renderTreeRecursive(item.children, ul, depth + 1);
      li.appendChild(ul);
    }
    parentNode.appendChild(li);
  });
}

function renderTree(container, tree) {
  const ul = document.createElement('ul');
  ul.classList.add(treeClasses.tree);
  renderTreeRecursive(tree, ul);
  container.innerHTML = '';
  container.appendChild(ul);
}

function addTempHighlight(el, duration, transitionMs) {
  mdvAddTempHighlight(el, duration, transitionMs);
}

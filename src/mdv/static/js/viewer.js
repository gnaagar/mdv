document.addEventListener('DOMContentLoaded', onPageLoad);

// -----------------------------------------------------------------------------
// PAGE STATE AND VARIABLES
// -----------------------------------------------------------------------------
const MD_BODY = document.getElementById('markdown-body')
const DIR_TREE = document.getElementById('dtree-container')
const TOC_TREE = document.getElementById('toc-container')

const dirTreeState = {
  entryMap: {},
};

const commonClasses = Object.freeze({
  scrollableWrapper: 'scrollable-wrapper',
  mdCodeCopiedHighlight: 'copied',
  tempHighlight: 'temp-highlight',
  hidden: 'hidden',
});

const treeClasses = Object.freeze({
  tree: 'tree',
  entry: 'tree-entry',
  collapsed: 'tree-collapsed',
  nested: 'nested',
  active: 'active',
});

// -----------------------------------------------------------------------------

function onPageLoad() {
  loadDirTree(DIR_TREE);
  setupSearch();
  generateTOC(MD_BODY, TOC_TREE);
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
     document.getElementById('section-main').dispatchEvent(new Event('scroll'));
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

  // Track which modal is open for keyboard navigation
  let activeModal = null;

  function openModal(modal, focusInput) {
    overlay.classList.remove('hidden');
    modal.classList.remove('hidden');
    activeModal = modal;
    setTimeout(() => { if (focusInput) focusInput.focus(); }, 100);
  }

  _closeAllModals = function() {
    overlay.classList.add('hidden');
    dirModal.classList.add('hidden');
    searchModal.classList.add('hidden');
    activeModal = null;
    dirKeyboardIndex = -1;
    searchKeyboardIndex = -1;
  };

  btnDir.addEventListener('click', () => openModal(dirModal, dirFilterInput));
  btnSearch.addEventListener('click', () => openModal(searchModal, searchInput));
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
  dirFilterInput.addEventListener('input', (e) => {
    dirKeyboardIndex = -1; // Reset keyboard selection on filter change
    const q = e.target.value.trim().toLowerCase();
    const allLis = document.querySelectorAll('#dtree-container li');
    const entries = document.querySelectorAll('#dtree-container .tree-entry');
    
    if (q === '') {
      allLis.forEach(li => li.style.display = '');
      entries.forEach(entry => {
        if (entry.dataset.fullPath) entry.textContent = entry.dataset.fullPath;
      });
      return;
    }

    const fuzzyMatch = (str, query) => {
       let qIdx = 0;
       for (let i = 0; i < str.length; i++) {
           if (str[i].toLowerCase() === query[qIdx]) {
               qIdx++;
               if (qIdx === query.length) return true;
           }
       }
       return false;
    };

    // Fast reveal for fuzzy matches without tree hierarchy calculations
    entries.forEach(entry => {
       const pathName = entry.dataset.fullPath || '';
       if (fuzzyMatch(pathName, q)) {
          entry.parentElement.style.display = '';
          if (pathName.toLowerCase().includes(q)) {
              entry.innerHTML = highlightMatches(pathName.replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c])), q);
          } else {
              entry.textContent = pathName;
          }
       } else {
          entry.parentElement.style.display = 'none';
          entry.textContent = pathName;
       }
    });
  });

  // Theme Toggler
  btnTheme.addEventListener('click', () => {
    document.body.classList.toggle('theme-dark');
    const isDark = document.body.classList.contains('theme-dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
  });
}

// -----------------------------------------------------------------------------
// KEYBOARD NAVIGATION FOR MODALS
// -----------------------------------------------------------------------------

let dirKeyboardIndex = -1;
let searchKeyboardIndex = -1;

function getVisibleDirEntries() {
  const items = document.querySelectorAll('#dtree-container li');
  return Array.from(items).filter(li => li.style.display !== 'none');
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
  visible.forEach(li => {
    const entry = li.querySelector('.tree-entry');
    if (entry) entry.classList.remove('keyboard-active');
  });
  if (dirKeyboardIndex >= 0 && dirKeyboardIndex < visible.length) {
    const entry = visible[dirKeyboardIndex].querySelector('.tree-entry');
    if (entry) {
      entry.classList.add('keyboard-active');
      entry.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
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
  items.forEach(li => li.classList.remove('keyboard-active'));
  if (searchKeyboardIndex >= 0 && searchKeyboardIndex < items.length) {
    items[searchKeyboardIndex].classList.add('keyboard-active');
    items[searchKeyboardIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}

// -----------------------------------------------------------------------------

function processSearchQuery() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  const l = params.get('l');
  
  if (q && l) {
    let targetLine = parseInt(l, 10);
    if (!isNaN(targetLine)) {
       let targetEl = null;
       // Sweep backwards locally to find the bounding block
       while (targetLine > 0) {
          targetEl = document.querySelector(`[data-source-line="${targetLine}"]`);
          if (targetEl) break;
          targetLine--;
       }
       
       if (targetEl) {
          isTocClickScrolling = true;
          
          targetEl.scrollIntoView({ behavior: 'auto', block: 'center' });
          
          setTimeout(() => { isTocClickScrolling = false; }, 800);
          
          // Pure visual highlighting on isolated block node
          highlightTextInNode(targetEl, q);
       }
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
      addTempHighlight(span, 4000, 700);
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
}

// --------------------------------------------------------------------------------

const constants = Object.freeze({
  debounceDelay: 100, // ms
  headingSwitchBuffer: 36, // px
});

const state = {
  activeIndices: [],
  headings: [],
  headingEntries: [],
};

let isTocClickScrolling = false;

function setupHeadingObserver() {
  if (!state.headings || !state.headings.length) return;

  let animFrame = null;
  const mainSection = document.getElementById('section-main');
  
  const handleScroll = () => {
    if (isTocClickScrolling) return;
    
    if (animFrame) cancelAnimationFrame(animFrame);
    animFrame = requestAnimationFrame(() => {
      const mainRect = mainSection.getBoundingClientRect();
      const activeIndices = [];
      const tops = Array.from(state.headings).map(h => h.getBoundingClientRect().top);
      const mdBodyBottom = document.getElementById('markdown-body').getBoundingClientRect().bottom;
      
      const viewTop = Math.max(mainRect.top, 0);
      const viewBottom = Math.min(mainRect.bottom, window.innerHeight);

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

  mainSection.addEventListener('scroll', handleScroll, { passive: true });
  window.addEventListener('scroll', handleScroll, { passive: true });
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

let searchAbortController = null;

function setupElems() {
  elems.input = document.getElementById('search-input');
  elems.resultsPanel = document.getElementById('search-results');
  elems.contentResults = document.getElementById('search-results-content');
}

function prepareSearchPanel() {
  elems.resultsPanel.style.display = 'flex';
}

function scrollToSourceLine(lineno, highlightQuery) {
  let targetLine = lineno;
  let targetEl = null;
  while (targetLine > 0) {
    targetEl = document.querySelector(`[data-source-line="${targetLine}"]`);
    if (targetEl) break;
    targetLine--;
  }
  if (targetEl) {
    isTocClickScrolling = true;
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    const response = await fetch(
      `/api/search?query=${encodeURIComponent(query)}`,
      { signal: searchAbortController.signal }
    );
    const results = await response.json();

    if (results.length === 0) {
      elems.contentResults.innerHTML = '<li class="search-empty-msg">No results found.</li>';
      return;
    }

    const currentPath = getCurrentFilePath();

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

      const safeLine = (item.line || '').replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]);
      const safePath = item.path.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]);
      const badge = getTypeBadge(item);
      const badgeClass = getBadgeClass(item);

      a.innerHTML = `<div class="search-result-item">
        <span class="line-type-badge ${badgeClass}">${badge}</span>
        <span class="search-result-line">${highlightMatches(safeLine, query)}</span>
        <span class="search-result-path">${safePath}</span>
      </div>`;

      li.appendChild(a);
      elems.contentResults.appendChild(li);
    });
  } catch (err) {
    if (err.name !== 'AbortError') throw err;
  }
}

function setupSearch() {
  setupElems();
  let debounceTimer = null;
  elems.input.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(search, 200);
  });
}

// Utility to highlight all occurrences of query words (case-insensitive, partial matches)
function highlightMatches(text, query) {
  if (!query) return text;
  const words = query
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (words.length === 0) return text;
  const regex = new RegExp(`(${words.join('|')})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
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

  container.innerHTML = '';
  container.appendChild(ul);
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

function addTempHighlight(el, duration = 1000, transitionMs = 500) {
  if (!el) return;
  el.classList.add(commonClasses.tempHighlight);
  // Ensure transition is set (in case CSS is missing/overridden)
  el.style.transition = `background ${transitionMs}ms, box-shadow ${transitionMs}ms`;
  setTimeout(() => {
    el.classList.add('fading');
    setTimeout(() => {
      el.classList.remove(commonClasses.tempHighlight, 'fading');
      el.style.transition = ''; // Clean up inline style
    }, transitionMs);
  }, duration);
}

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

  // Listen for scroll to highlight current TOC entry
  document.getElementById('section-main').addEventListener('scroll', highlightCurrentHeading);
  const sidebarToggler = document.getElementById("sidebar-left-toggle-area");
  const overlay = document.getElementById("overlay");

  sidebarToggler.addEventListener('click', openLeft);
  overlay.addEventListener('click', closeLeft);
}

function openLeft() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  sidebar.classList.add("open");
  overlay.classList.add("active");
}

function closeLeft() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  sidebar.classList.remove("open");
  overlay.classList.remove("active");
}

function processSearchQuery() {
  const params = new URLSearchParams(window.location.search);
  const query = params.get('q')
  const ctx = params.get('c')
  if (query && ctx) {
    highlightWordInViewer(MD_BODY, query, atob(ctx));
  }
}

function highlightWordInViewer(container, query, context) {
  console.log(query,context);
  if (!query) return;

  // Prepare search and context words
  const searchWords = query
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.toLowerCase());
  if (searchWords.length === 0) return;

  const contextWords = context
    ? context
        .replace(/[^\w\s]|_/g, '')
        .toLowerCase()
        .split(/\s+/)
        .filter(Boolean)
    : [];

  // console.log('searchWords:', searchWords);
  // console.log('contextWords:', contextWords);

  // Gather all blocks
  let blocks = Array.from(
    container.querySelectorAll('p, li, pre, div, h1, h2, h3, h4, h5, h6, tr, td, th')
  );

  // Find the window of consecutive blocks containing the most context words in order
  let bestWindow = [0, 0];
  let bestScore = -1;
  const maxWindow = 5;

  if (contextWords.length) {
    // Pre-normalize block texts
    const blockNorms = blocks.map((b) =>
      b.innerText
        .replace(/[^\w\s]|_/g, '')
        .toLowerCase()
        .split(/\s+/)
        .filter(Boolean)
    );
    // console.log('blockNorms:', blockNorms);
    for (let start = 0; start < blocks.length; ++start) {
      let joined = [];
      for (let end = start; end < Math.min(blocks.length, start + maxWindow); ++end) {
        joined = joined.concat(blockNorms[end]);
        // Score: count of context words found in order in joined
        let score = countOrderedMatch(contextWords, joined, searchWords);
        if (score > bestScore) {
          bestScore = score;
          bestWindow = [start, end];
        }
        // Early exit if perfect match
        if (score === contextWords.length) break;
      }
      if (bestScore === contextWords.length) break;
    }
    blocks = blocks.slice(bestWindow[0], bestWindow[1] + 1);
  } else {
    blocks = [container];
  }

  // console.log('bestWindow:', bestWindow);
  // console.log('bestScore:', bestScore);
  // console.log('blocks:', blocks.map(b => b.innerText.trim()));

  // Highlight search words in the best window
  blocks.forEach((block) => {
    const textNodes = [];
    function collectTextNodes(node) {
      if (node.nodeType === 3 && node.nodeValue.trim()) {
        textNodes.push({ node, text: node.nodeValue, parent: node.parentNode });
      } else if (node.nodeType === 1 && !['SCRIPT', 'STYLE', 'SPAN'].includes(node.tagName)) {
        Array.from(node.childNodes).forEach(collectTextNodes);
      }
    }
    collectTextNodes(block);

    textNodes.forEach((t) => {
      let text = t.text;
      let replaced = false;
      let parts = [];
      let lastIdx = 0;
      let regex = new RegExp(
        searchWords.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'),
        'gi'
      );
      let match;
      while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIdx) {
          parts.push(document.createTextNode(text.slice(lastIdx, match.index)));
        }
        const span = document.createElement('span');
        span.textContent = match[0];
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
  });

  // Scroll to the first .temp-highlight in any of the blocks
  let first = null;
  for (const block of blocks) {
    first = block.querySelector('.temp-highlight');
    if (first) break;
  }
  if (first) {
    first.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// Helper: count how many contextWords appear in order in joinedWords,
// but only if all searchWords are present in joinedWords
function countOrderedMatch(contextWords, joinedWords, searchWords) {
  // Prerequisite: all searchWords must be present in joinedWords
  for (const word of searchWords) {
    if (!joinedWords.some((w) => w.includes(word))) return 0;
  }
  // Count how many contextWords appear in order in joinedWords
  let i = 0,
    j = 0,
    count = 1;
  while (i < contextWords.length && j < joinedWords.length) {
    if (contextWords[i] === joinedWords[j]) {
      count++;
      i++;
    }
    j++;
  }
  return count;
}

// --------------------------------------------------------------------------------

const constants = Object.freeze({
  debounceDelay: 100, // ms
  headingSwitchBuffer: 36, // px
});

const state = {
  // curHeadings: new Set(),
  headings: [],
  headingEntries: [],
  lastUpdateTs: Date.now() - 2 * constants.debounceDelay
};

function scrollIntoViewIfNeeded(el) {
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const outOfView =
    rect.top < 0 ||
    rect.bottom > window.innerHeight ||
    rect.left < 0 ||
    rect.right > window.innerWidth;

  if (outOfView) {
    el.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    });
  }
}


// Helper to highlight the TOC entry for the current scroll position
function highlightCurrentHeading() {
  let now = Date.now();
  if (now - state.lastUpdateTs <= constants.debounceDelay) {
    return;
  }

  // if (state.headings.length == 0) {
  //   return;
  // }

  // const threshold = 20; // Extra buffer

  // const container = document.getElementById('section-main');
  // const scrollPos = container.scrollTop + threshold;
  // const topPos = container.scrollTop;
  // const bottomPos = container.scrollBottom;
  
  let last = -1, firstDist = -1;
  let firstActive = -1, lastActive = -1;

  for (let i = 0; i < state.headings.length; i++) {
    const rect = state.headings[i].getBoundingClientRect();
    if (rect.top < 0) {
      last = i;
    }

    if (rect.top >= 0 && rect.bottom + 2 * constants.headingSwitchBuffer <= window.innerHeight) {
      if (firstDist == -1) {
        firstDist = rect.top;
      }
      state.headingEntries[i].classList.add(treeClasses.active);
      if (firstActive == -1) firstActive = i;
      else if (lastActive == -1) lastActive = i;
    } else {
      state.headingEntries[i].classList.remove(treeClasses.active);
    }
  }

  if ((firstDist == -1 || firstDist > constants.headingSwitchBuffer) && last != -1) {
    state.headingEntries[last].classList.add(treeClasses.active);
  }

  if (firstActive != -1) {
    scrollIntoViewIfNeeded(state.headingEntries[firstActive]);
    scrollIntoViewIfNeeded(state.headingEntries[lastActive]);
  }

  state.lastUpdateTs = now;

  // Fire once more to cover edge cases (fast scroll stop)
  setTimeout(highlightCurrentHeading, constants.debounceDelay);

  // let low = 0,
  //   high = state.headings.length - 1,
  //   result = 0;
  //
  // while (low <= high) {
  //   let mid = Math.floor((low + high) / 2);
  //   if (state.headings[mid].offsetTop <= scrollPos) {
  //     result = mid;
  //     low = mid + 1;
  //   } else {
  //     high = mid - 1;
  //   }
  // }
  // if (state.curHeadings != null) {
  //   state.headingEntries[state.curHeadings].classList.remove(treeClasses.active);
  // }
  // state.curHeadings = result;
  // const target = state.headingEntries[result];
  // target.classList.add(treeClasses.active);
  // target.scrollIntoView({
  //   behavior: 'auto',
  //   block: 'nearest',
  //   inline: 'nearest',
  // });
  
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
        // Let browser handle certain cases, useful for opening in new tab
        if (e.ctrlKey || e.metaKey || e.button === 1) {
          return;
        }

        // Otherwise, intercept and load dynamically
        e.preventDefault();
        h.scrollIntoView({ block: 'start' });
        if (h.id && window.location.hash != h.id) {
          window.location.hash = h.id;
        }
        addTempHighlight(h);
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
  highlightCurrentHeading();
}

// -------------------------------------------------------------------------------- 

const elems = {
  input: null,
  resultsPanel: null,
  fileResults: null,
  contentResults: null,
};

function setupElems() {
  elems.input = document.getElementById('search-input');
  elems.resultsPanel = document.getElementById('search-results');
  elems.fileResults = document.getElementById('search-results-file');
  elems.contentResults = document.getElementById('search-results-content');
}

function prepareSearchPanel() {
  const rect = elems.input.getBoundingClientRect();
  elems.resultsPanel.style.left = rect.left + 'px';
  elems.resultsPanel.style.top = rect.bottom + +4 + 'px';
  elems.resultsPanel.style.display = 'block';
}

async function searchFiles(query) {
  const fileMatches = getDirTreeIds().filter((f) => f.toLowerCase().includes(query.toLowerCase()));

  if (fileMatches.length === 0) {
    elems.fileResults.innerHTML = '<li style="color:#888;padding:0.5em;">No files found.</li>';
    return;
  }

  fileMatches.forEach((key) => {
    const li = document.createElement('li');
    li.className = 'file';

    const a = document.createElement('a');
    // Remove default link styling
    a.style.textDecoration = 'none';
    a.style.color = 'inherit';
    a.href = '/v/' + key;
    a.innerHTML = highlightMatches(key, query);

    li.appendChild(a);
    elems.fileResults.appendChild(li);
  });
}

async function searchContent(query) {
  // 2. Global content/context search
  const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
  const results = await response.json();
  if (results.length === 0) {
    elems.contentResults.innerHTML = '<li style="color:#888;padding:0.5em;">No content found.</li>';
    return;
  }
  results.forEach((item) => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    // Remove default link styling
    a.style.display = 'block';
    a.style.textDecoration = 'none';
    a.style.color = 'inherit';
    a.href = `/v/${item.path}?q=${encodeURIComponent(query)}&c=${btoa(item.preview)}`;
    a.innerHTML = `<div>
      <strong>${highlightMatches(item.path, query)}</strong>
      <pre style="font-size:smaller;color:#555;margin-top:2px;">${highlightMatches(
        item.preview.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]),
        query
      )}</pre>
    </div>`;
    li.appendChild(a);
    elems.contentResults.appendChild(li);
  });
}

async function search() {
  prepareSearchPanel();

  elems.fileResults.innerHTML = '';
  elems.contentResults.innerHTML = '';

  const query = elems.input.value.trim();

  if (!query) {
    elems.resultsPanel.style.display = 'none';
    return;
  }
  elems.resultsPanel.style.display = 'block';

  searchFiles(query);
  searchContent(query);
}

function setupSearch() {
  setupElems();
  let debounceTimer = null;
  elems.input.addEventListener('input', function () {
    // console.log('query: ', elems.input.value);
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(search, 300);
  });

  // Hide results when clicking outside
  document.addEventListener('click', (e) => {
    if (!elems.resultsPanel.contains(e.target) && e.target !== elems.input) {
      elems.resultsPanel.style.display = 'none';
    }
  });

  // Hide on Escape
  elems.input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      elems.resultsPanel.style.display = 'none';
      elems.input.value = '';
    }
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
  entry.classList.add(treeClasses.active);
  // Expand all parent directories
  let li = entry.closest('li');
  while (li) {
    li.classList.remove(treeClasses.collapsed);
    li = li.parentElement.closest('li');
  }
  // Scroll into view if not visible
  // entry.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

// Dir tree related
function loadDirTree(container, callback) {
  // recursive function to enrich all nodes
  function enrichDirTree(tree) {
    return tree.map((item) => {
      if (item.type === 'directory') {
        return {
          name: item.name,
          action: function (e) {
            const li = this.parentNode;
            li.classList.toggle(treeClasses.collapsed);
            e.stopPropagation();
          },
          children: enrichDirTree(item.children || []),
          collapsed: true, // Start directories collapsed
          metadata: {
            isFile: false,
          },
        };
      } else {
        return {
          name: item.name,
          collapsed: false, // Files are not collapsible
          href: '/v/' + item.path,
          metadata: {
            id: item.path,
          },
          render: (item, entry) => {
            dirTreeState.entryMap[item.metadata.id] = entry;
          },
        };
      }
    });
  }
  return fetch('/api/tree')
    .then((res) => res.json())
    .then((tree) => {
      renderTree(container, enrichDirTree(tree));
      highlightCurrentFileInDirTree();
    });
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

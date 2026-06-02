/* ================================================================
   MDV Markdown
   Depends on: shared.js (must be loaded before this script)
   ================================================================ */

document.addEventListener('DOMContentLoaded', async () => {
  const mdbody = document.getElementById('markdown-body');
  if (!mdbody) return;

  let topLevelHeading = mdbody.querySelector('h1');
  if (topLevelHeading) {
    document.title = topLevelHeading.textContent;
  }

  wrapTablesAndImages(mdbody);
  simplifyAnchorText(mdbody);
  postProcessTasklists(mdbody);

  renderMath(mdbody);
  renderMermaidDiagrams();
  // Make code blocks copy-able
  genCopyButtons(mdbody);
});

let lastMermaidTheme = null;

function renderMermaidDiagrams() {
  const isDark = typeof mdvIsDark === 'function' ? mdvIsDark() : document.body.classList.contains('theme-dark');
  lastMermaidTheme = isDark ? "dark" : "default";
  mermaid.initialize({
    startOnLoad: false,
    theme: lastMermaidTheme
  });

  // Convert code blocks → Mermaid containers
  document.querySelectorAll("code.language-mermaid").forEach(block => {
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = block.textContent;
    // Save original text for dynamic re-theming
    div.setAttribute('data-mermaid-src', block.textContent);
    block.parentElement.replaceWith(div);
  });

  mermaid.run();
}

document.addEventListener('themeChanged', (e) => {
  const theme = e.detail.isDark ? "dark" : "default";
  if (theme === lastMermaidTheme) return;
  lastMermaidTheme = theme;
  mermaid.initialize({
    startOnLoad: false,
    theme
  });
  
  document.querySelectorAll('.mermaid').forEach(div => {
     div.removeAttribute('data-processed');
     div.innerHTML = div.getAttribute('data-mermaid-src');
  });
  
  mermaid.run();
});

function renderMath(container) {
  const unescapeLatex = (text) => text.replace(/\\\\/g, '\\');

  // Unified inline + block math rendering in a single DOM query
  container.querySelectorAll('.math.inline, .math.block').forEach((el) => {
    katex.render(unescapeLatex(el.textContent), el, {
      throwOnError: false,
      displayMode: el.classList.contains('block'),
    });
  });
}


// Post page load function
// Add copy-to-clipboard buttons for code blocks
function genCopyButtons(container) {
  // Parse icons once as templates — cloneNode is faster than re-parsing innerHTML
  const copyTpl = document.createElement('template');
  copyTpl.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
  const checkTpl = document.createElement('template');
  checkTpl.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

  const pres = container.querySelectorAll('pre');
  if (pres.length === 0) return;

  // Batch all DOM mutations in one frame to avoid layout thrashing
  requestAnimationFrame(() => {
    pres.forEach((pre) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'code-wrapper';
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);

      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.appendChild(copyTpl.content.cloneNode(true));
      wrapper.appendChild(btn);

      let copyTimeout = null;
      btn.addEventListener('click', async () => {
        if (copyTimeout) clearTimeout(copyTimeout);
        const codeEl = pre.querySelector('code');
        const content = codeEl ? codeEl.textContent : pre.textContent;
        await navigator.clipboard.writeText(content);
        btn.replaceChildren(checkTpl.content.cloneNode(true));
        copyTimeout = setTimeout(() => {
          btn.replaceChildren(copyTpl.content.cloneNode(true));
          copyTimeout = null;
        }, 1200);
      });
    });
  });
}

function wrapTablesAndImages(container) {
  // Wrap tables in .md-table
  container.querySelectorAll('table').forEach(table => {
    if (table.parentElement.classList.contains('md-table')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'md-table';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });

  // Wrap images in .md-image
  container.querySelectorAll('img').forEach(img => {
    if (img.parentElement.classList.contains('md-image')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'md-image';
    img.parentNode.insertBefore(wrapper, img);
    wrapper.appendChild(img);
  });
}

function simplifyAnchorText(container) {
  container.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href').trim();
    const text = a.textContent.trim();
    if (text === href) {
      if (href.startsWith('http://')) {
        a.textContent = href.substring(7);
      } else if (href.startsWith('https://')) {
        a.textContent = href.substring(8);
      }
    }
  });
}

function postProcessTasklists(container) {
  container.querySelectorAll('li').forEach(li => {
    const checkbox = li.querySelector('input[type="checkbox"]');
    if (checkbox) {
      checkbox.disabled = true;
      if (checkbox.checked) {
        li.classList.add('task-completed');
      }
    }
  });
}


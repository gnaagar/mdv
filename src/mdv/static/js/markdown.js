document.addEventListener('DOMContentLoaded', async () => {
  mdbody = document.getElementById('markdown-body')

  let topLevelHeading = mdbody.querySelector('h1');
  if (topLevelHeading) {
    document.title = topLevelHeading.textContent;
  }

  renderMath(mdbody);
  renderMermaidDiagrams();
  // Make code blocks copy-able
  genCopyButtons(mdbody);
});

function renderMermaidDiagrams() {
  const isDark = document.body.classList.contains('theme-dark') || localStorage.getItem('theme') === 'dark';
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark ? "dark" : "default"
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
  const isDark = e.detail.isDark;
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark ? "dark" : "default"
  });
  
  document.querySelectorAll('.mermaid').forEach(div => {
     div.removeAttribute('data-processed');
     div.innerHTML = div.getAttribute('data-mermaid-src');
  });
  
  mermaid.run();
});

function renderMath(container) {
  const unescapeLatex = (text) => text.replace(/\\\\/g, '\\');

  // Inline math
  container.querySelectorAll('.math.inline').forEach((el) => {
    katex.render(unescapeLatex(el.textContent), el, {
      throwOnError: false,
      displayMode: false,
    });
  });

  // Block math
  container.querySelectorAll('.math.block').forEach((el) => {
    katex.render(unescapeLatex(el.textContent), el, {
      throwOnError: false,
      displayMode: true,
    });
  });
}


// Post page load function
// Add copy-to-clipboard buttons for code blocks
function genCopyButtons(container) {
  const copyIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
  const checkIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

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
      btn.innerHTML = copyIcon;
      wrapper.appendChild(btn);

      btn.addEventListener('click', async () => {
        const codeEl = pre.querySelector('code');
        const content = codeEl ? codeEl.textContent : pre.textContent;
        await navigator.clipboard.writeText(content);
        btn.innerHTML = checkIcon;
        setTimeout(() => { btn.innerHTML = copyIcon; }, 1200);
      });
    });
  });
}

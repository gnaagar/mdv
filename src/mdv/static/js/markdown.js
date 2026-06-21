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

let exploreModal = null;
let modalContent = null;
let modalViewport = null;
let modalTitle = null;

// Zoom/pan state variables for the explore modal
let mScale = 1;
let mTranslateX = 0;
let mTranslateY = 0;
let mIsDragging = false;
let mStartX = 0;
let mStartY = 0;
let mTouchStartDist = 0;
let zoomSlider = null;

function updateModalTransform() {
  if (modalContent) {
    modalContent.style.transform = `translate(${mTranslateX}px, ${mTranslateY}px) scale(${mScale})`;
  }
  if (zoomSlider) {
    zoomSlider.value = mScale;
  }
}

function getOrCreateExploreModal() {
  if (exploreModal) return exploreModal;

  exploreModal = document.createElement('div');
  exploreModal.id = 'mermaid-explore-modal';
  exploreModal.className = 'mermaid-modal';
  
  exploreModal.innerHTML = `
    <div class="mermaid-modal-container">
      <div class="mermaid-modal-header">
        <span class="mermaid-modal-title" id="mermaid-modal-title">Explore Diagram</span>
        <div class="mermaid-modal-toolbar">
          <button class="mermaid-modal-btn m-zoom-out" title="Zoom Out">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
          <input type="range" class="mermaid-modal-slider m-zoom-slider" min="0.15" max="5" step="0.05" value="1" title="Zoom Slider">
          <button class="mermaid-modal-btn m-zoom-in" title="Zoom In">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
          <button class="mermaid-modal-btn m-reset" title="Reset View">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          </button>
          <button class="mermaid-modal-btn m-close" title="Close Explorer">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
      </div>
      <div class="mermaid-modal-viewport" id="mermaid-modal-viewport">
        <div class="mermaid-modal-content" id="mermaid-modal-content"></div>
      </div>
    </div>
  `;

  document.body.appendChild(exploreModal);

  modalContent = exploreModal.querySelector('#mermaid-modal-content');
  modalViewport = exploreModal.querySelector('#mermaid-modal-viewport');
  modalTitle = exploreModal.querySelector('#mermaid-modal-title');
  zoomSlider = exploreModal.querySelector('.m-zoom-slider');

  // Slider listener
  zoomSlider.addEventListener('input', (e) => {
    mScale = parseFloat(e.target.value);
    if (modalContent) {
      modalContent.style.transform = `translate(${mTranslateX}px, ${mTranslateY}px) scale(${mScale})`;
    }
  });

  // Button Listeners
  exploreModal.querySelector('.m-zoom-in').addEventListener('click', (e) => {
    e.stopPropagation();
    mScale = Math.min(mScale + 0.15, 5);
    updateModalTransform();
  });

  exploreModal.querySelector('.m-zoom-out').addEventListener('click', (e) => {
    e.stopPropagation();
    mScale = Math.max(mScale - 0.15, 0.15);
    updateModalTransform();
  });

  exploreModal.querySelector('.m-reset').addEventListener('click', (e) => {
    e.stopPropagation();
    mScale = 1;
    mTranslateX = 0;
    mTranslateY = 0;
    updateModalTransform();
  });

  const closeModal = () => {
    exploreModal.classList.remove('active');
    modalContent.innerHTML = '';
  };

  exploreModal.querySelector('.m-close').addEventListener('click', (e) => {
    e.stopPropagation();
    closeModal();
  });



  // Mouse drag panning inside modal
  const onMouseMove = (e) => {
    if (!mIsDragging) return;
    mTranslateX = e.clientX - mStartX;
    mTranslateY = e.clientY - mStartY;
    updateModalTransform();
  };

  const onMouseUp = () => {
    if (mIsDragging) {
      mIsDragging = false;
      modalViewport.style.cursor = 'grab';
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    }
  };

  modalViewport.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('.mermaid-modal-btn')) return;

    mIsDragging = true;
    mStartX = e.clientX - mTranslateX;
    mStartY = e.clientY - mTranslateY;
    modalViewport.style.cursor = 'grabbing';

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
  });

  // Touch panning and pinch zoom gestures inside modal
  const onTouchMove = (e) => {
    if (mIsDragging && e.touches.length === 1) {
      mTranslateX = e.touches[0].clientX - mStartX;
      mTranslateY = e.touches[0].clientY - mStartY;
      updateModalTransform();
      e.preventDefault();
    } else if (e.touches.length === 2 && mTouchStartDist > 0) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const factor = dist / mTouchStartDist;
      mScale = Math.min(Math.max(mScale * factor, 0.15), 6);
      mTouchStartDist = dist;
      updateModalTransform();
      e.preventDefault();
    }
  };

  const onTouchEnd = () => {
    mIsDragging = false;
    mTouchStartDist = 0;
    window.removeEventListener('touchmove', onTouchMove);
    window.removeEventListener('touchend', onTouchEnd);
  };

  modalViewport.addEventListener('touchstart', (e) => {
    if (e.target.closest('.mermaid-modal-btn')) return;

    if (e.touches.length === 1) {
      mIsDragging = true;
      mStartX = e.touches[0].clientX - mTranslateX;
      mStartY = e.touches[0].clientY - mTranslateY;
      window.addEventListener('touchmove', onTouchMove, { passive: false });
      window.addEventListener('touchend', onTouchEnd);
    } else if (e.touches.length === 2) {
      mIsDragging = false;
      mTouchStartDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      window.addEventListener('touchmove', onTouchMove, { passive: false });
      window.addEventListener('touchend', onTouchEnd);
    }
  });

  return exploreModal;
}

function openExploreModal(titleText, svgHtml) {
  const modal = getOrCreateExploreModal();
  
  modalTitle.textContent = `Explore: ${titleText || 'Diagram'}`;
  modalContent.innerHTML = svgHtml;
  
  mScale = 1;
  mTranslateX = 0;
  mTranslateY = 0;
  updateModalTransform();
  
  modal.classList.add('active');
}

function renderMermaidDiagrams() {
  const isDark = typeof mdvIsDark === 'function' ? mdvIsDark() : document.body.classList.contains('theme-dark');
  lastMermaidTheme = isDark ? "dark" : "default";
  mermaid.initialize({
    startOnLoad: false,
    theme: lastMermaidTheme
  });

  // Convert code blocks → Subtle explore wrapper and Mermaid containers
  document.querySelectorAll("code.language-mermaid").forEach(block => {
    const wrapper = document.createElement("div");
    wrapper.className = "mermaid-wrapper";

    const btnExplore = document.createElement("button");
    btnExplore.className = "mermaid-explore-btn";
    btnExplore.title = "Maximize Diagram";
    btnExplore.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>`;

    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = block.textContent;
    div.setAttribute('data-mermaid-src', block.textContent);

    wrapper.appendChild(btnExplore);
    wrapper.appendChild(div);

    block.parentElement.replaceWith(wrapper);

    btnExplore.addEventListener('click', (e) => {
      e.stopPropagation();

      // Find the nearest preceding heading to use as the title
      let title = "";
      let prev = wrapper.previousElementSibling;
      while (prev) {
        if (/^H[1-6]$/i.test(prev.tagName)) {
          title = prev.textContent.trim();
          break;
        }
        if (prev.classList.contains('mermaid-wrapper') || prev.tagName === 'PRE') {
          break;
        }
        prev = prev.previousElementSibling;
      }

      openExploreModal(title, div.innerHTML);
    });
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
  
  // Close explore modal if open to prevent theme mismatch in modal display
  const modal = document.getElementById('mermaid-explore-modal');
  if (modal && modal.classList.contains('active')) {
    modal.classList.remove('active');
    const content = modal.querySelector('#mermaid-modal-content');
    if (content) content.innerHTML = '';
  }

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
  // Wrap tables in .md-table-container > .md-table
  container.querySelectorAll('table').forEach(table => {
    if (table.parentElement.classList.contains('md-table')) return;
    
    const containerDiv = document.createElement('div');
    containerDiv.className = 'md-table-container';
    
    const wrapper = document.createElement('div');
    wrapper.className = 'md-table';
    
    table.parentNode.insertBefore(containerDiv, table);
    containerDiv.appendChild(wrapper);
    wrapper.appendChild(table);

    function updateScrollShadows() {
      const scrollLeft = wrapper.scrollLeft;
      const maxScroll = wrapper.scrollWidth - wrapper.clientWidth;
      
      containerDiv.classList.toggle('scroll-left-active', scrollLeft > 1);
      containerDiv.classList.toggle('scroll-right-active', maxScroll > 1 && scrollLeft < maxScroll - 1);
    }

    wrapper.addEventListener('scroll', updateScrollShadows);
    setTimeout(updateScrollShadows, 50);
    window.addEventListener('resize', updateScrollShadows);
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


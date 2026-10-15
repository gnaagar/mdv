(() => {
  /* ── 16:9 viewport scaling ──────────────────────────────────────────────── */
  const SLIDE_W = 1600;
  const SLIDE_H = 900;
  const OUTER_GAP = 0;

  /* ── Slide navigation ───────────────────────────────────────────────────── */
  const slides = [...document.querySelectorAll('.slide')];
  const count = document.getElementById('slide-count');
  let current = 0;
  let diagramId = 0;

  function updateHeaderSync() {
    const activeSlide = slides[current];
    if (!activeSlide) return;

    if (activeSlide.classList.contains('title-slide')) {
      document.body.classList.add('is-title-slide');
      document.documentElement.style.removeProperty('--header-bottom');
      return;
    }

    document.body.classList.remove('is-title-slide');
    const h2 = activeSlide.querySelector('.slide-markdown > h2:first-child');
    if (h2) {
      const bottom = Math.round(h2.getBoundingClientRect().bottom);
      document.documentElement.style.setProperty('--header-bottom', `${bottom}px`);
    } else {
      document.documentElement.style.setProperty('--header-bottom', '0px');
    }
  }

  function scaleSlides() {
    const isFullscreen = Boolean(document.fullscreenElement || document.webkitFullscreenElement);
    const availableW = Math.max(1, window.innerWidth - OUTER_GAP * 2);
    const availableH = Math.max(1, window.innerHeight - OUTER_GAP * 2);
    const maxScale = isFullscreen ? Number.POSITIVE_INFINITY : 1;
    const scale = Math.min(maxScale, availableW / SLIDE_W, availableH / SLIDE_H);
    document.documentElement.style.setProperty('--slide-scale', scale);
    updateHeaderSync();
  }

  window.addEventListener('resize', scaleSlides);
  document.addEventListener('fullscreenchange', scaleSlides);
  document.addEventListener('webkitfullscreenchange', scaleSlides);

  async function renderSlideDiagrams(slide) {
    if (!window.mermaid?.render) return;
    for (const diagram of slide.querySelectorAll('.mermaid')) {
      if (diagram.hasAttribute('data-processed')) continue;
      diagram.setAttribute('data-processed', 'true');

      try {
        const { svg, bindFunctions } = await window.mermaid.render(
          `slide-mermaid-${diagramId++}`, diagram.dataset.mermaidSrc
        );
        diagram.innerHTML = svg;
        bindFunctions?.(diagram);
      } catch (error) {
        diagram.removeAttribute('data-processed');
        console.error('Unable to render mermaid diagram:', error);
      }
    }
  }

  const show = (index) => {
    current = Math.max(0, Math.min(index, slides.length - 1));
    slides.forEach((slide, i) => {
      const active = i === current;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
    });
    if (count) {
      count.textContent = `${current + 1} / ${slides.length}`;
      if (slides[current] && count.parentElement !== slides[current]) {
        slides[current].appendChild(count);
      }
    }
    history.replaceState(null, '', `#${current + 1}`);
    updateHeaderSync();
    requestAnimationFrame(() => {
      renderSlideDiagrams(slides[current]);
      updateHeaderSync();
    });
  };

  const init = () => {
    document.documentElement.classList.remove('theme-dark');
    document.body.classList.remove('theme-dark');
    window.mermaid?.initialize?.({
      startOnLoad: false,
      flowchart: { wrappingWidth: 200 }
    });
    scaleSlides();
    const fromHash = Number.parseInt(location.hash.slice(1), 10);
    show(fromHash ? fromHash - 1 : 0);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  document.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (['ArrowRight', 'ArrowDown', ' ', 'PageDown'].includes(event.key)) { event.preventDefault(); show(current + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) { event.preventDefault(); show(current - 1); }
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(slides.length - 1);
    else if (event.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  });
})();

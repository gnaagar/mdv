(() => {
  /* ── 16:9 viewport scaling ──────────────────────────────────────────────── */
  const SLIDE_W = 1600;
  const SLIDE_H = 900;

  function scaleSlides() {
    // Cap at 1: never enlarge beyond 1600×900; scale down if viewport is smaller.
    const scale = Math.min(1, window.innerWidth / SLIDE_W, window.innerHeight / SLIDE_H);
    document.documentElement.style.setProperty('--slide-scale', scale);
  }

  scaleSlides();
  window.addEventListener('resize', scaleSlides);

  window.mermaid.initialize({
    startOnLoad: false
  });

  /* ── Slide navigation ───────────────────────────────────────────────────── */
  const slides = [...document.querySelectorAll('.slide')];
  const count = document.getElementById('slide-count');
  let current = 0;
  let diagramId = 0;

  async function renderSlideDiagrams(slide) {
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
    count.textContent = `${current + 1} / ${slides.length}`;
    history.replaceState(null, '', `#${current + 1}`);
    requestAnimationFrame(() => {
      renderSlideDiagrams(slides[current]);
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.documentElement.classList.remove('theme-dark');
    document.body.classList.remove('theme-dark');
    window.mermaid.initialize({
      startOnLoad: false,
      flowchart: { wrappingWidth: 200 }
    });
    const fromHash = Number.parseInt(location.hash.slice(1), 10);
    show(fromHash ? fromHash - 1 : 0);
  });

  document.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (['ArrowRight', 'ArrowDown', ' ', 'PageDown'].includes(event.key)) { event.preventDefault(); show(current + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) { event.preventDefault(); show(current - 1); }
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(slides.length - 1);
    else if (event.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  });
})();

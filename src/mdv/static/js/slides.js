(() => {
  const slides = [...document.querySelectorAll('.slide')];
  const count = document.getElementById('slide-count');
  let current = 0;
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
      const slide = slides[current];
      const diagrams = slide.querySelectorAll('.mermaid');
      if (window.mermaid && diagrams.length) {
        diagrams.forEach((diagram) => {
          if (diagram.dataset.mermaidSrc) diagram.textContent = diagram.dataset.mermaidSrc;
          diagram.removeAttribute('data-processed');
        });
        window.mermaid.run({ nodes: diagrams }).catch((error) => console.error('Unable to render Mermaid diagram:', error));
      }
    });
  };
  const fromHash = Number.parseInt(location.hash.slice(1), 10);
  if (fromHash) show(fromHash - 1);
  document.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (['ArrowRight', 'ArrowDown', ' ', 'PageDown'].includes(event.key)) { event.preventDefault(); show(current + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) { event.preventDefault(); show(current - 1); }
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(slides.length - 1);
    else if (event.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  });
})();

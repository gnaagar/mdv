document.addEventListener('DOMContentLoaded', async () => {
  mdbody = document.getElementById('markdown-body')

  let topLevelHeading = mdbody.querySelector('h1');
  if (topLevelHeading) {
    document.title = topLevelHeading.textContent;
  }

  renderMath(mdbody);
  // Make code blocks copy-able
  genCopyButtons(mdbody);
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


document.querySelectorAll('pre').forEach((pre, i) => {
  const wrapper = document.createElement('div');
  wrapper.className = 'code-wrapper';

  pre.parentNode.insertBefore(wrapper, pre);
  wrapper.appendChild(pre);

  const btn = document.createElement('button');
  btn.className = 'copy-btn';
  btn.innerHTML = `
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
  `;

  wrapper.appendChild(btn);

  btn.addEventListener('click', async () => {
    const codeEl = pre.querySelector('code');
    const content = codeEl ? codeEl.textContent : pre.textContent;
    await navigator.clipboard.writeText(content);
    const original = btn.innerHTML;

    btn.innerHTML = `
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
</svg>
    `;

    setTimeout(() => {
      btn.innerHTML = original;
    }, 1200);

  });
});

  // container.querySelectorAll('pre > code').forEach((codeBlock) => {
  //   const pre = codeBlock.parentNode;
  //   pre.addEventListener('click', () => {
  //     const selection = window.getSelection();
  //     if (selection && selection.toString().length > 0) return; // Don't copy if selecting
  //     navigator.clipboard.writeText(codeBlock.innerText).then(() => {
  //       pre.classList.add('copied');
  //       pre.style.transition = 'none';
  //       setTimeout(() => {
  //         pre.style.transition = 'background-color 0.2s ease';
  //         pre.classList.remove('copied');
  //       }, 200);
  //     });
  //   });
  // });
}

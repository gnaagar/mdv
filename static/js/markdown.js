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
  container.querySelectorAll('pre > code').forEach((codeBlock) => {
    const pre = codeBlock.parentNode;
    pre.addEventListener('click', () => {
      const selection = window.getSelection();
      if (selection && selection.toString().length > 0) return; // Don't copy if selecting
      navigator.clipboard.writeText(codeBlock.innerText).then(() => {
        pre.classList.add('copied');
        pre.style.transition = 'none';
        setTimeout(() => {
          pre.style.transition = 'background-color 0.2s ease';
          pre.classList.remove('copied');
        }, 200);
      });
    });
  });
}

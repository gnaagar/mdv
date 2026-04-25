/* ================================================================
   MDV Shared JavaScript Utilities
   Theme toggle, DOM helpers, timing constants
   Import this in all HTML pages that use viewer.js, csvviewer.js, etc.
   ================================================================ */

"use strict";

/* ----------------------------------------------------------
   Timing Constants
   ---------------------------------------------------------- */
const MDV_TIMING = Object.freeze({
  debounce: 200,
  scrollReset: 800,
  highlight: 4000,
  highlightFade: 500,
  highlightTransition: 700,
  copyFeedback: 1200,
  undoDelay: 500,
  modalOpen: 100,
});

/* ----------------------------------------------------------
   CSS Class Constants
   ---------------------------------------------------------- */
const MDV_CLASSES = Object.freeze({
  scrollableWrapper: 'scrollable-wrapper',
  mdCodeCopiedHighlight: 'copied',
  tempHighlight: 'temp-highlight',
  hidden: 'hidden',
  themeDark: 'theme-dark',
  themeLight: 'theme-light',

  // Tree classes
  tree: 'tree',
  entry: 'tree-entry',
  collapsed: 'tree-collapsed',
  nested: 'nested',
  active: 'active',
  keyboardActive: 'keyboard-active',
});

/* ----------------------------------------------------------
   Theme Utilities
   ---------------------------------------------------------- */
function mdvGetTheme() {
  const stored = localStorage.getItem('theme');
  if (stored) return stored;
  return document.body.classList.contains('theme-dark') ? 'dark' : 'light';
}

function mdvIsDark() {
  return document.body.classList.contains(MDV_CLASSES.themeDark) ||
         localStorage.getItem('theme') === 'dark';
}

function mdvToggleTheme() {
  const isDark = document.body.classList.toggle(MDV_CLASSES.themeDark);
  const theme = isDark ? 'dark' : 'light';
  localStorage.setItem('theme', theme);
  document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
  return isDark;
}

function mdvDispatchThemeChange(isDark) {
  document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
}

/* ----------------------------------------------------------
   DOM Utilities
   ---------------------------------------------------------- */
function mdvEscapeHtml(s) {
  return s.replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
}

function mdvFuzzyMatch(str, query) {
  let qIdx = 0;
  for (let i = 0; i < str.length; i++) {
    if (str[i].toLowerCase() === query[qIdx]) {
      qIdx++;
      if (qIdx === query.length) return true;
    }
  }
  return false;
}

function mdvCreateHighlighter(query) {
  if (!query) return (text) => text;
  const words = query
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (words.length === 0) return (text) => text;
  const regex = new RegExp(`(${words.join('|')})`, 'gi');
  return (text) => text.replace(regex, '<mark>$1</mark>');
}

/* ----------------------------------------------------------
   Highlight Utilities
   ---------------------------------------------------------- */
function mdvAddTempHighlight(el, duration, transitionMs) {
  if (!el) return;
  // Use defaults from timing constants
  duration = duration ?? MDV_TIMING.highlight;
  transitionMs = transitionMs ?? MDV_TIMING.highlightTransition;

  el.classList.add(MDV_CLASSES.tempHighlight);
  el.style.transition = `background ${transitionMs}ms, box-shadow ${transitionMs}ms`;

  setTimeout(() => {
    el.classList.add('fading');
    setTimeout(() => {
      el.classList.remove(MDV_CLASSES.tempHighlight, 'fading');
      el.style.transition = ''; // Clean up inline style
    }, transitionMs);
  }, duration);
}

function mdvUnwrapHighlightSpans(spans, containerNode) {
  spans.forEach(span => {
    if (!span.parentNode) return;
    const text = document.createTextNode(span.textContent);
    span.parentNode.replaceChild(text, span);
  });
  // Merge adjacent text nodes to fully restore original DOM structure
  if (containerNode && containerNode.normalize) {
    containerNode.normalize();
  }
}

/* ----------------------------------------------------------
   Debounce Utilities
   ---------------------------------------------------------- */
function mdvDebounce(fn, delay) {
  let timeout = null;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), delay ?? MDV_TIMING.debounce);
  };
}

/* ----------------------------------------------------------
   Keyboard Utilities
   ---------------------------------------------------------- */
function mdvIsInputFocused() {
  return document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
}

function mdvIsModKey(e) {
  return e.metaKey || e.ctrlKey;
}

/* ----------------------------------------------------------
   Initialize theme on page load
   ---------------------------------------------------------- */
function mdvInitTheme() {
  const stored = localStorage.getItem('theme');
  if (stored === 'dark') {
    document.body.classList.add(MDV_CLASSES.themeDark);
  } else if (stored === 'light') {
    document.body.classList.remove(MDV_CLASSES.themeDark);
  }
  // Otherwise let CSS defaults apply
}

// Auto-initialize when DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mdvInitTheme);
  } else {
    mdvInitTheme();
  }
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MDV_TIMING,
    MDV_CLASSES,
    mdvGetTheme,
    mdvIsDark,
    mdvToggleTheme,
    mdvDispatchThemeChange,
    mdvEscapeHtml,
    mdvFuzzyMatch,
    mdvCreateHighlighter,
    mdvAddTempHighlight,
    mdvUnwrapHighlightSpans,
    mdvDebounce,
    mdvIsInputFocused,
    mdvIsModKey,
    mdvInitTheme,
  };
}
/* ================================================================
   MDV Shared JavaScript Utilities
   Theme toggle, DOM helpers, timing constants
   Import this in all HTML pages that use viewer.js, etc.
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
  const cls = document.body.className;
  const m = cls.match(/\btheme-(\S+)/);
  return m ? m[1] : 'std-light';
}

function mdvIsDark() {
  const theme = mdvGetTheme();
  return theme.includes('dark');
}

function mdvSetTheme(name) {
  const isDark = name.includes('dark');
  document.body.className = 'theme-' + name;
  document.body.classList.toggle('theme-dark', isDark);
  localStorage.setItem('theme', name);
  document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
  // Update all toggle buttons
  const btns = document.querySelectorAll('#btn-theme-toggle');
  btns.forEach(function(b) { b.title = 'Switch Theme (' + name + ')'; });
  // Sync modal checkmark
  const modal = document.getElementById('theme-modal');
  if (modal) {
    modal.querySelectorAll('.theme-option-check').forEach(function(c) { c.style.display = 'none'; });
    var sel = modal.querySelector('.theme-option[data-theme="' + name + '"] .theme-option-check');
    if (sel) sel.style.display = '';
  }
}

function mdvToggleTheme() {
  var themes = window.MDV_THEMES || ['std-light', 'std-dark'];
  var current = mdvGetTheme();
  var idx = themes.indexOf(current);
  if (idx < 0) idx = -1;
  var next = themes[(idx + 1) % themes.length];
  mdvSetTheme(next);
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
  var theme = mdvGetTheme();
  var btns = document.querySelectorAll('#btn-theme-toggle');
  btns.forEach(function(b) { b.title = 'Switch Theme (' + theme + ')'; });
  // Sync theme modal checkmark with resolved theme
  var modal = document.getElementById('theme-modal');
  if (modal) {
    modal.querySelectorAll('.theme-option-check').forEach(function(c) {
      c.style.display = 'none';
    });
    var sel = modal.querySelector('.theme-option[data-theme="' + theme + '"] .theme-option-check');
    if (sel) sel.style.display = '';
  }
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
    mdvSetTheme,
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
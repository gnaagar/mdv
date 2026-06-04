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
  var stored = localStorage.getItem('theme');
  if (stored === 'light') stored = 'std-light';
  if (stored === 'dark') stored = 'std-dark';
  
  if (stored && window.MDV_THEMES && window.MDV_THEMES.indexOf(stored) >= 0) {
    return stored;
  }
  
  if (document.body) {
    const cls = document.body.className;
    const m = cls.match(/\btheme-(\S+)/);
    if (m && window.MDV_THEMES && window.MDV_THEMES.indexOf(m[1]) >= 0) {
      return m[1];
    }
  }
  
  return 'std-light';
}

function mdvGetActiveTheme() {
  return mdvGetTheme();
}

function mdvIsDark() {
  // First check CSS custom property for active theme mode
  const targetEl = document.body || document.documentElement;
  const mode = getComputedStyle(targetEl).getPropertyValue('--theme-mode').trim();
  if (mode === 'dark') return true;
  if (mode === 'light') return false;

  // Fallbacks: active class or name matching
  if (document.documentElement.classList.contains('theme-dark')) return true;
  if (document.body && document.body.classList.contains('theme-dark')) return true;
  return mdvGetActiveTheme().includes('dark');
}

function mdvSetTheme(name) {
  // Migrate legacy names
  if (name === 'light') name = 'std-light';
  if (name === 'dark') name = 'std-dark';

  localStorage.setItem('theme', name);

  // Apply to html and body elements
  document.documentElement.className = 'theme-' + name;
  if (document.body) {
    document.body.className = 'theme-' + name;
  }

  var isDark = name.includes('dark');
  document.documentElement.classList.toggle('theme-dark', isDark);
  if (document.body) {
    document.body.classList.toggle('theme-dark', isDark);
  }
  document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));

  // Update dynamic stylesheet link with onload verification to prevent race conditions
  const linkEl = document.getElementById('theme-stylesheet');
  if (linkEl) {
    linkEl.onload = function() {
      var accurateDark = mdvIsDark();
      if (accurateDark !== isDark) {
        document.documentElement.classList.toggle('theme-dark', accurateDark);
        if (document.body) {
          document.body.classList.toggle('theme-dark', accurateDark);
        }
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: accurateDark } }));
      }
    };
    linkEl.href = '/static/themes/' + name + '.css';
  }

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
  if (idx < 0) idx = 0;
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
  var preferred = mdvGetTheme();
  var active = mdvGetActiveTheme();

  if (document.body) {
    if (!document.body.className.includes('theme-')) {
      document.body.className = 'theme-' + active;
    }
    const isDark = mdvIsDark();
    document.body.classList.toggle('theme-dark', isDark);
    document.documentElement.classList.toggle('theme-dark', isDark);
  }

  var btns = document.querySelectorAll('#btn-theme-toggle');
  btns.forEach(function(b) { b.title = 'Switch Theme (' + preferred + ')'; });

  // Sync theme modal checkmark with preferred theme
  var modal = document.getElementById('theme-modal');
  if (modal) {
    modal.querySelectorAll('.theme-option-check').forEach(function(c) {
      c.style.display = 'none';
    });
    var sel = modal.querySelector('.theme-option[data-theme="' + preferred + '"] .theme-option-check');
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
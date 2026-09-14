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
   Canonical stored values: "light" | "dark" | "system"
   Resolved CSS stems come from MDV_LIGHT_THEME / MDV_DARK_THEME
   injected by the server from mdv.json (defaults: sans / sans-dark).
   ---------------------------------------------------------- */

function mdvLightTheme() {
  return window.MDV_LIGHT_THEME || 'sans';
}

function mdvDarkTheme() {
  return window.MDV_DARK_THEME || 'sans-dark';
}

/** Returns "light" | "dark" | "system" — the canonical stored mode. */
function mdvGetMode() {
  var cookieMatch = document.cookie.match(/(^|;)\s*theme\s*=\s*([^;]+)/);
  var stored = cookieMatch ? decodeURIComponent(cookieMatch[2]) : null;
  if (!stored) stored = localStorage.getItem('theme');
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  return 'system';
}

/** Resolves a canonical mode to the actual CSS file stem. */
function mdvResolveStem(mode) {
  if (mode === 'dark') return mdvDarkTheme();
  if (mode === 'light') return mdvLightTheme();
  // system: follow OS preference
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  return prefersDark ? mdvDarkTheme() : mdvLightTheme();
}

/** Returns the currently active CSS file stem (e.g. "sans" or "sans-dark"). */
function mdvGetTheme() {
  return mdvResolveStem(mdvGetMode());
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

  // Fallbacks
  if (document.documentElement.classList.contains('theme-dark')) return true;
  if (document.body && document.body.classList.contains('theme-dark')) return true;
  return mdvGetTheme() === mdvDarkTheme();
}

/**
 * Set the theme mode. Accepts: "light" | "dark" | "system".
 * Resolves to a CSS stem and applies it.
 */
function mdvSetTheme(mode) {
  // Normalise
  if (mode !== 'light' && mode !== 'dark' && mode !== 'system') mode = 'system';

  localStorage.setItem('theme', mode);
  document.cookie = "theme=" + encodeURIComponent(mode) + "; path=/; max-age=31536000; SameSite=Lax";

  var stem = mdvResolveStem(mode);
  var isDark = (stem === mdvDarkTheme());

  // Apply to html and body elements
  document.documentElement.className = 'theme-' + stem;
  if (document.body) {
    document.body.className = 'theme-' + stem;
  }

  document.documentElement.classList.toggle('theme-dark', isDark);
  if (document.body) {
    document.body.classList.toggle('theme-dark', isDark);
  }
  document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark, mode, stem } }));

  // Update dynamic stylesheet link
  const linkEl = document.getElementById('theme-stylesheet');
  if (linkEl) {
    linkEl.onload = function() {
      var accurateDark = mdvIsDark();
      if (accurateDark !== isDark) {
        document.documentElement.classList.toggle('theme-dark', accurateDark);
        if (document.body) {
          document.body.classList.toggle('theme-dark', accurateDark);
        }
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: accurateDark, mode, stem } }));
      }
    };
    linkEl.href = '/static/themes/' + stem + '.css';
  }

  // Sync modal checkmarks
  _mdvSyncThemeModal(mode);

  // Update toggle button title
  const btns = document.querySelectorAll('#btn-theme-toggle');
  const label = mode.charAt(0).toUpperCase() + mode.slice(1);
  btns.forEach(function(b) { b.title = 'Appearance (' + label + ')'; });
}

/** Sync the checkmark in the theme modal to the currently active mode. */
function _mdvSyncThemeModal(mode) {
  const modal = document.getElementById('theme-modal');
  if (!modal) return;
  modal.querySelectorAll('.theme-option-check').forEach(function(c) { c.style.display = 'none'; });
  var sel = modal.querySelector('.theme-option[data-mode="' + mode + '"] .theme-option-check');
  if (sel) sel.style.display = '';
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
  var mode = mdvGetMode();
  var stem = mdvResolveStem(mode);
  var isDark = (stem === mdvDarkTheme());

  if (document.body) {
    if (!document.body.className.includes('theme-')) {
      document.body.className = 'theme-' + stem;
    }
    document.body.classList.toggle('theme-dark', isDark);
    document.documentElement.classList.toggle('theme-dark', isDark);
  }

  var btns = document.querySelectorAll('#btn-theme-toggle');
  var label = mode.charAt(0).toUpperCase() + mode.slice(1);
  btns.forEach(function(b) { b.title = 'Appearance (' + label + ')'; });

  _mdvSyncThemeModal(mode);
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
    mdvGetMode,
    mdvGetTheme,
    mdvIsDark,
    mdvSetTheme,
    mdvResolveStem,
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
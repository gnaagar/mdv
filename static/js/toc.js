import { treeClasses, renderTree, addTempHighlight } from './commons.js';

const constants = Object.freeze({
  debounceDelay: 100, // ms
  headingSwitchBuffer: 36, // px
});

const state = {
  // curHeadings: new Set(),
  headings: [],
  headingEntries: [],
  lastUpdateTs: Date.now() - 2 * constants.debounceDelay
};


// Helper to highlight the TOC entry for the current scroll position
export function highlightCurrentHeading() {
  let now = Date.now();
  if (now - state.lastUpdateTs <= constants.debounceDelay) {
    return;
  }

  // if (state.headings.length == 0) {
  //   return;
  // }

  // const threshold = 20; // Extra buffer

  // const container = document.getElementById('section-main');
  // const scrollPos = container.scrollTop + threshold;
  // const topPos = container.scrollTop;
  // const bottomPos = container.scrollBottom;
  
  let last = -1, firstDist = -1;

  for (let i = 0; i < state.headings.length; i++) {
    const rect = state.headings[i].getBoundingClientRect();
    if (rect.top < 0) {
      last = i;
    }

    if (rect.top >= 0 && rect.bottom + 2 * constants.headingSwitchBuffer <= window.innerHeight) {
      if (firstDist == -1) {
        firstDist = rect.top;
      }
      state.headingEntries[i].classList.add(treeClasses.active);
    } else {
      state.headingEntries[i].classList.remove(treeClasses.active);
    }
  }

  if ((firstDist == -1 || firstDist > constants.headingSwitchBuffer) && last != -1) {
    state.headingEntries[last].classList.add(treeClasses.active);
  }

  state.lastUpdateTs = now;

  // Fire once more to cover edge cases (fast scroll stop)
  setTimeout(highlightCurrentHeading, constants.debounceDelay);

  // let low = 0,
  //   high = state.headings.length - 1,
  //   result = 0;
  //
  // while (low <= high) {
  //   let mid = Math.floor((low + high) / 2);
  //   if (state.headings[mid].offsetTop <= scrollPos) {
  //     result = mid;
  //     low = mid + 1;
  //   } else {
  //     high = mid - 1;
  //   }
  // }
  // if (state.curHeadings != null) {
  //   state.headingEntries[state.curHeadings].classList.remove(treeClasses.active);
  // }
  // state.curHeadings = result;
  // const target = state.headingEntries[result];
  // target.classList.add(treeClasses.active);
  // target.scrollIntoView({
  //   behavior: 'auto',
  //   block: 'nearest',
  //   inline: 'nearest',
  // });
  
}

export function generateTOC(contentContainer, treeContainer) {
  let topLevelHeading = contentContainer.querySelector('h1');
  if (topLevelHeading) {
    document.title = topLevelHeading.textContent;
  }

  state.headings = contentContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
  state.curHeadings = null;
  state.headingEntries = new Array(state.headings.length);

  const root = [];
  const stack = [{ level: 0, children: root }];

  state.headings.forEach((h, idx) => {
    const level = parseInt(h.tagName[1]);
    const node = {
      name: h.textContent,
      children: [],
      action: function (e) {
        // Let browser handle certain cases, useful for opening in new tab
        if (e.ctrlKey || e.metaKey || e.button === 1) {
          return;
        }

        // Otherwise, intercept and load dynamically
        e.preventDefault();
        h.scrollIntoView({ block: 'start' });
        if (h.id && window.location.hash != h.id) {
          window.location.hash = h.id;
        }
        addTempHighlight(h);
      },
      href: `${window.location.pathname}#${h.id}`,
      collapsed: false,
      metadata: {
        index: idx,
      },
      render: (item, entry) => {
        state.headingEntries[item.metadata.index] = entry;
      },
    };
    while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
    stack[stack.length - 1].children.push(node);
    stack.push({ level, children: node.children });
  });
  renderTree(treeContainer, root);
  highlightCurrentHeading();
}

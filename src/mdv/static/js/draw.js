document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('draw-canvas');
    const tools = document.querySelectorAll('.tool-btn');
    const colorBtns = document.querySelectorAll('.color-btn');
    const copyBtn = document.getElementById('copy-svg-btn');
    const clearBtn = document.getElementById('clear-svg-btn');
    const undoBtn = document.getElementById('undo-btn');

    // Modal elements
    const importBtn = document.getElementById('import-svg-btn');
    const importModal = document.getElementById('import-modal');
    const importText = document.getElementById('import-svg-text');
    const importCancelBtn = document.getElementById('import-cancel-btn');
    const importConfirmBtn = document.getElementById('import-confirm-btn');

    let currentTool = 'pointer';
    let selectedColor = 'default';
    
    let isDrawing = false;
    let isMoving = false;
    let isSelecting = false;
    let startX = 0;
    let startY = 0;
    let currentElement = null;
    let textInput = null;
    let currentPoints = [];
    
    let selectedElements = new Set();
    const clearSelection = () => {
        selectedElements.forEach(el => el.classList.remove('selected'));
        selectedElements.clear();
    };
    
    let undoStack = [];
    const saveState = () => {
        undoStack.push(canvas.innerHTML);
    };
    saveState(); 

    const undo = () => {
        if (undoStack.length > 1) { 
            undoStack.pop(); 
            canvas.innerHTML = undoStack[undoStack.length - 1]; 
            clearSelection();
        }
    };

    undoBtn.addEventListener('click', undo);

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
            e.preventDefault();
            undo();
        } else if (e.key === 'Backspace' || e.key === 'Delete') {
            if (selectedElements.size > 0) {
                e.preventDefault();
                selectedElements.forEach(el => {
                    if (el.parentNode === canvas) canvas.removeChild(el);
                });
                clearSelection();
                saveState();
            }
        }
    });

    tools.forEach(btn => {
        btn.addEventListener('click', () => {
            tools.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTool = btn.dataset.tool;
            canvas.style.cursor = currentTool === 'pointer' ? 'default' : (currentTool === 'snapshot' ? 'crosshair' : 'crosshair');
            
            if (currentTool !== 'pointer') {
                clearSelection();
            }
            if (textInput) finalizeText();
        });
    });

    colorBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            colorBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedColor = btn.dataset.color;
        });
    });

    const getSmoothPath = (pts) => {
        if (pts.length === 0) return '';
        if (pts.length === 1) return `M ${pts[0][0]} ${pts[0][1]} L ${pts[0][0]} ${pts[0][1]}`;
        let path = `M ${pts[0][0]} ${pts[0][1]}`;
        for (let i = 1; i < pts.length - 1; i++) {
            let xc = (pts[i][0] + pts[i + 1][0]) / 2;
            let yc = (pts[i][1] + pts[i + 1][1]) / 2;
            path += ` Q ${pts[i][0]} ${pts[i][1]}, ${xc} ${yc}`;
        }
        path += ` L ${pts[pts.length - 1][0]} ${pts[pts.length - 1][1]}`;
        return path;
    };

    const getMouseCoords = (e) => {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    };

    const createSVGElement = (type) => {
        const el = document.createElementNS('http://www.w3.org/2000/svg', type);
        const colorValue = selectedColor === 'default' ? 'currentColor' : selectedColor;
        
        if (type !== 'text') {
            el.setAttribute('stroke', colorValue);
            el.setAttribute('fill', 'transparent');
            el.setAttribute('stroke-width', '2');
            el.setAttribute('vector-effect', 'non-scaling-stroke');
            if (type === 'path') {
                el.setAttribute('stroke-linecap', 'round');
                el.setAttribute('stroke-linejoin', 'round');
            }
        } else {
            el.setAttribute('fill', colorValue);
            el.setAttribute('font-family', 'var(--font-mono, monospace)');
            el.setAttribute('font-size', '16px');
        }
        
        if (selectedColor !== 'default') {
            el.style.color = selectedColor;
        }
        return el;
    };

    const getCleanSVGText = (cleanSVG) => {
        cleanSVG.style.background = 'transparent';
        cleanSVG.style.display = 'block';
        cleanSVG.style.margin = '20px auto';
        cleanSVG.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        
        const styleText = `
          svg { --draw-red: #d32f2f; --draw-blue: #1976d2; --draw-green: #388e3c; --draw-purple: #7b1fa2; --draw-orange: #f57c00; }
          .theme-dark svg, @media (prefers-color-scheme: dark) { svg { --draw-red: #ef5350; --draw-blue: #42a5f5; --draw-green: #66bb6a; --draw-purple: #ab47bc; --draw-orange: #ffa726; } }
        `.replace(/\s+/g, ' ').trim();
        
        const styleEl = document.createElement('style');
        styleEl.textContent = styleText;
        cleanSVG.insertBefore(styleEl, cleanSVG.firstChild);
        
        return cleanSVG.outerHTML.replace(/\r?\n|\r/g, '').replace(/>\s+</g, '><').trim();
    };

    canvas.addEventListener('mousedown', (e) => {
        if (textInput) finalizeText();
        
        const coords = getMouseCoords(e);
        startX = coords.x;
        startY = coords.y;

        if (currentTool === 'pointer') {
            let targetEl = e.target;
            while (targetEl && targetEl.parentNode !== canvas && targetEl.tagName !== 'svg') {
                targetEl = targetEl.parentNode;
            }

            if (targetEl && targetEl.tagName !== 'svg' && targetEl.tagName !== 'defs' && targetEl.tagName !== 'style') {
                if (!selectedElements.has(targetEl)) {
                    if (!e.shiftKey) clearSelection();
                    selectedElements.add(targetEl);
                    targetEl.classList.add('selected');
                }
                
                isMoving = true;
                selectedElements.forEach(el => {
                    let tx = 0, ty = 0;
                    const tf = el.getAttribute('transform');
                    if (tf) {
                        const match = tf.match(/translate\(([-\d.]+),\s*([-.\d]+)\)/);
                        if (match) {
                            tx = parseFloat(match[1]);
                            ty = parseFloat(match[2]);
                        }
                    }
                    el.dataset.initTx = tx;
                    el.dataset.initTy = ty;
                });
            } else {
                clearSelection();
                isSelecting = true;
                currentElement = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                currentElement.classList.add('selection-box');
                currentElement.setAttribute('x', startX);
                currentElement.setAttribute('y', startY);
                currentElement.setAttribute('width', '0');
                currentElement.setAttribute('height', '0');
                canvas.appendChild(currentElement);
            }
            return;
        }

        isDrawing = true;

        if (currentTool === 'text') {
            handleTextClick(startX, startY);
            isDrawing = false; 
            return;
        }

        let type = currentTool;
        if (currentTool === 'arrow') type = 'line';
        if (currentTool === 'pencil') type = 'path';
        if (currentTool === 'snapshot') type = 'rect';
        
        currentElement = createSVGElement(type);
        
        if (currentTool === 'rect' || currentTool === 'snapshot') {
            currentElement.setAttribute('x', startX);
            currentElement.setAttribute('y', startY);
            currentElement.setAttribute('width', '0');
            currentElement.setAttribute('height', '0');
            if (currentTool === 'rect') currentElement.setAttribute('rx', '4');
            if (currentTool === 'snapshot') {
                currentElement.classList.add('snapshot-box');
                currentElement.setAttribute('stroke-dasharray', '4');
                currentElement.setAttribute('stroke', 'var(--tree-active-color)');
            }
        } else if (currentTool === 'circle') {
            currentElement.setAttribute('cx', startX);
            currentElement.setAttribute('cy', startY);
            currentElement.setAttribute('r', '0');
        } else if (currentTool === 'line' || currentTool === 'arrow') {
            currentElement.setAttribute('x1', startX);
            currentElement.setAttribute('y1', startY);
            currentElement.setAttribute('x2', startX);
            currentElement.setAttribute('y2', startY);
            if (currentTool === 'arrow') {
                currentElement.setAttribute('marker-end', 'url(#arrowhead)');
            }
        } else if (currentTool === 'pencil') {
            currentPoints = [[startX, startY]];
            currentElement.setAttribute('d', `M ${startX} ${startY}`);
        }

        canvas.appendChild(currentElement);
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!isDrawing && !isMoving && !isSelecting) return;

        const coords = getMouseCoords(e);
        const currentX = coords.x;
        const currentY = coords.y;

        if (isMoving) {
            const dx = currentX - startX;
            const dy = currentY - startY;
            selectedElements.forEach(el => {
                const initTx = parseFloat(el.dataset.initTx || 0);
                const initTy = parseFloat(el.dataset.initTy || 0);
                el.setAttribute('transform', `translate(${initTx + dx}, ${initTy + dy})`);
            });
            return;
        }

        if (isSelecting && currentElement) {
            const x = Math.min(startX, currentX);
            const y = Math.min(startY, currentY);
            const w = Math.abs(currentX - startX);
            const h = Math.abs(currentY - startY);
            currentElement.setAttribute('x', x);
            currentElement.setAttribute('y', y);
            currentElement.setAttribute('width', w);
            currentElement.setAttribute('height', h);
            return;
        }

        if (!currentElement) return;

        if (currentTool === 'rect' || currentTool === 'snapshot') {
            const x = Math.min(startX, currentX);
            const y = Math.min(startY, currentY);
            const w = Math.abs(currentX - startX);
            const h = Math.abs(currentY - startY);
            currentElement.setAttribute('x', x);
            currentElement.setAttribute('y', y);
            currentElement.setAttribute('width', w);
            currentElement.setAttribute('height', h);
        } else if (currentTool === 'circle') {
            const r = Math.sqrt(Math.pow(currentX - startX, 2) + Math.pow(currentY - startY, 2));
            currentElement.setAttribute('r', r);
        } else if (currentTool === 'line' || currentTool === 'arrow') {
            currentElement.setAttribute('x2', currentX);
            currentElement.setAttribute('y2', currentY);
        } else if (currentTool === 'pencil') {
            currentPoints.push([currentX, currentY]);
            currentElement.setAttribute('d', getSmoothPath(currentPoints));
        }
    });

    canvas.addEventListener('mouseup', () => {
        if (isMoving) {
            isMoving = false;
            saveState();
            return;
        }

        if (isSelecting) {
            isSelecting = false;
            if (currentElement) {
                const b1 = currentElement.getBBox();
                canvas.removeChild(currentElement);
                currentElement = null;
                
                if (b1.width > 5 && b1.height > 5) {
                    Array.from(canvas.children).forEach(child => {
                        if (child.tagName !== 'defs' && child.tagName !== 'style') {
                            const b2 = child.getBBox();
                            if (!(b2.x > b1.x + b1.width || 
                                  b2.x + b2.width < b1.x || 
                                  b2.y > b1.y + b1.height || 
                                  b2.y + b2.height < b1.y)) {
                                selectedElements.add(child);
                                child.classList.add('selected');
                            }
                        }
                    });
                }
            }
            return;
        }

        if (isDrawing && currentElement) {
            if (currentTool === 'snapshot') {
                const box = currentElement.getBBox();
                canvas.removeChild(currentElement); 
                
                if (box.width > 10 && box.height > 10) {
                    const cleanSVG = canvas.cloneNode(true);
                    cleanSVG.removeAttribute('id');
                    cleanSVG.removeAttribute('class');
                    cleanSVG.setAttribute('viewBox', `${box.x} ${box.y} ${box.width} ${box.height}`);
                    cleanSVG.setAttribute('width', box.width);
                    cleanSVG.setAttribute('height', box.height);
                    
                    navigator.clipboard.writeText(getCleanSVGText(cleanSVG)).then(() => {
                        const snapBtn = document.querySelector('[data-tool="snapshot"]');
                        const origBtnHtml = snapBtn.innerHTML;
                        snapBtn.innerHTML = '<span style="color:var(--task-completed-color, green);font-weight:bold;font-size:12px;">Saved</span>';
                        setTimeout(() => snapBtn.innerHTML = origBtnHtml, 1500);
                    });
                }
                isDrawing = false;
                currentElement = null;
                return; 
            }

            let isTooSmall = false;
            if (currentTool === 'rect') {
                isTooSmall = parseInt(currentElement.getAttribute('width')) < 5 && parseInt(currentElement.getAttribute('height')) < 5;
            } else if (currentTool === 'circle') {
                isTooSmall = parseInt(currentElement.getAttribute('r')) < 5;
            } else if (currentTool === 'line' || currentTool === 'arrow') {
                const x1 = parseInt(currentElement.getAttribute('x1'));
                const y1 = parseInt(currentElement.getAttribute('y1'));
                const x2 = parseInt(currentElement.getAttribute('x2'));
                const y2 = parseInt(currentElement.getAttribute('y2'));
                isTooSmall = Math.abs(x2 - x1) < 5 && Math.abs(y2 - y1) < 5;
            } else if (currentTool === 'pencil') {
                isTooSmall = currentPoints.length < 3; 
            }

            if (isTooSmall) {
                canvas.removeChild(currentElement);
            } else {
                saveState();
            }
        }
        
        isDrawing = false;
        currentElement = null;
    });

    const handleTextClick = (x, y) => {
        const input = document.createElement('input');
        input.type = 'text';
        input.style.position = 'absolute';
        input.style.left = `${x}px`;
        input.style.top = `${y - 10}px`; 
        input.style.fontFamily = 'monospace';
        input.style.fontSize = '16px';
        input.style.background = 'transparent';
        input.style.color = selectedColor === 'default' ? 'var(--text-color)' : selectedColor;
        input.style.border = '1px dashed var(--tree-active-color)';
        input.style.outline = 'none';
        input.style.padding = '2px';
        input.style.zIndex = '100';
        
        document.querySelector('.canvas-wrapper').appendChild(input);
        
        textInput = { element: input, x, y };
        
        setTimeout(() => input.focus(), 0);

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') finalizeText();
            if (e.key === 'Escape') cancelText();
        });
    };

    const finalizeText = () => {
        if (!textInput) return;
        const val = textInput.element.value.trim();
        if (val) {
            const textEl = createSVGElement('text');
            textEl.setAttribute('x', textInput.x);
            textEl.setAttribute('y', textInput.y + 6);
            textEl.textContent = val;
            canvas.appendChild(textEl);
            saveState();
        }
        textInput.element.remove();
        textInput = null;
    };

    const cancelText = () => {
        if (!textInput) return;
        textInput.element.remove();
        textInput = null;
    };

    // Modal Import SVG Logic
    importBtn.addEventListener('click', () => {
        importText.value = '';
        importModal.style.display = 'flex';
        setTimeout(() => importText.focus(), 50);
    });

    const closeImport = () => {
        importModal.style.display = 'none';
    };

    importCancelBtn.addEventListener('click', closeImport);

    importConfirmBtn.addEventListener('click', () => {
        const content = importText.value.trim();
        if (!content) {
            closeImport();
            return;
        }

        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div>${content}</div>`, 'text/html');
        const importedSvg = doc.querySelector('svg');
        
        if (importedSvg) {
            const normalizeColors = (node) => {
                const stroke = node.getAttribute('stroke');
                const fill = node.getAttribute('fill');
                
                if (stroke && stroke !== 'none' && !stroke.includes('var(')) node.setAttribute('stroke', 'currentColor');
                if (fill && fill !== 'none' && fill !== 'transparent' && !fill.includes('var(')) node.setAttribute('fill', 'currentColor');
                
                if (node.children) {
                    Array.from(node.children).forEach(normalizeColors);
                }
            };

            Array.from(importedSvg.children).forEach(child => {
                 if (child.tagName.toLowerCase() === 'defs' && child.innerHTML.includes('arrowhead')) return;
                 if (child.tagName.toLowerCase() === 'style') return; 
                 normalizeColors(child);
                 canvas.appendChild(child.cloneNode(true));
            });
            
            saveState();
        }
        closeImport();
    });

    // Copy SVG
    copyBtn.addEventListener('click', () => {
        const cleanSVG = canvas.cloneNode(true);
        cleanSVG.removeAttribute('id');
        cleanSVG.removeAttribute('class');
        
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        const children = [...canvas.children];
        let hasContent = false;
        
        children.forEach(child => {
            if (child.tagName.toLowerCase() !== 'defs' && child.tagName.toLowerCase() !== 'style') {
                hasContent = true;
                const bbox = child.getBBox();
                if (bbox.width || bbox.height) { 
                    minX = Math.min(minX, bbox.x - 5);
                    minY = Math.min(minY, bbox.y - 5);
                    maxX = Math.max(maxX, bbox.x + bbox.width + 5);
                    maxY = Math.max(maxY, bbox.y + bbox.height + 5);
                }
            }
        });
        
        if (hasContent && minX !== Infinity) {
            const width = maxX - minX;
            const height = maxY - minY;
            cleanSVG.setAttribute('viewBox', `${minX} ${minY} ${width} ${height}`);
            cleanSVG.setAttribute('width', width);
            cleanSVG.setAttribute('height', height);
        } else {
            const viewBoxStr = "0 0 " + canvas.clientWidth + " " + canvas.clientHeight;
            cleanSVG.setAttribute('viewBox', viewBoxStr);
            cleanSVG.setAttribute('width', canvas.clientWidth);
            cleanSVG.setAttribute('height', canvas.clientHeight);
        }
        
        navigator.clipboard.writeText(getCleanSVGText(cleanSVG)).then(() => {
            const origText = copyBtn.innerText;
            copyBtn.innerText = 'Copied!';
            setTimeout(() => copyBtn.innerText = origText, 2000);
        });
    });

    clearBtn.addEventListener('click', () => {
        const childNodes = Array.from(canvas.childNodes);
        childNodes.forEach(node => {
            if (node.tagName && node.tagName.toLowerCase() !== 'defs' && node.tagName.toLowerCase() !== 'style') {
                canvas.removeChild(node);
            }
        });
        saveState();
    });
});

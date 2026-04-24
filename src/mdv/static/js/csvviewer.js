document.addEventListener('DOMContentLoaded', () => {
    const filenameInput = document.getElementById('csv-filename');
    const filename = filenameInput ? filenameInput.value : '';
    const tableContainer = document.getElementById('csv-table-container');
    const sqlInput = document.getElementById('sql-input');
    const btnExecute = document.getElementById('btn-execute');
    const historyList = document.getElementById('history-list');

    const btnThemeToggle = document.getElementById('btn-theme-toggle');
    if (btnThemeToggle) {
        btnThemeToggle.addEventListener('click', () => {
            const isDark = document.body.classList.contains('theme-dark');
            if (isDark) {
                document.body.classList.remove('theme-dark');
                document.body.classList.add('theme-light');
                localStorage.setItem('theme', 'light');
                window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: false } }));
            } else {
                document.body.classList.remove('theme-light');
                document.body.classList.add('theme-dark');
                localStorage.setItem('theme', 'dark');
                window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: true } }));
            }
        });
    }

    let history = [];
    let isFirstLoad = true;

    async function executeQuery(query, addToHistory = true) {
        tableContainer.innerHTML = '<div class="loading-state">Executing query...</div>';

        try {
            const response = await fetch('/api/csv/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, query })
            });

            const result = await response.json();

            if (!result.success) {
                tableContainer.innerHTML = `<div class="error-msg">Error: ${result.error}</div>`;
                return;
            }

            if (isFirstLoad && result.headers && result.headers.length > 0) {
                isFirstLoad = false;
                if (!sqlInput.value.trim()) {
                    sqlInput.value = `SELECT * FROM data LIMIT 10`;
                }
            }

            if (addToHistory && !query.trim().toUpperCase().startsWith("SELECT * FROM DATA LIMIT 10")) {
                if (!history.includes(query)) {
                    history.unshift(query);
                    if (history.length > 20) history.pop();
                    renderHistory();
                }
            }

            renderTable(result.headers, result.data);

        } catch (e) {
            tableContainer.innerHTML = `<div class="error-msg">Network error: ${e.message}</div>`;
        }
    }

    function renderTable(headers, data) {
        if (!data || data.length === 0) {
            tableContainer.innerHTML = '<div class="empty-state">No results found</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'csv-data-table';

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headers.forEach(h => {
            const th = document.createElement('th');
            th.textContent = h;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        data.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(h => {
                const td = document.createElement('td');
                td.textContent = row[h] !== null ? row[h] : 'NULL';
                if (row[h] === null) td.classList.add('null-cell');
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        tableContainer.innerHTML = '';
        tableContainer.appendChild(table);
    }

    function renderHistory() {
        historyList.innerHTML = '';
        history.forEach(q => {
            const li = document.createElement('li');
            li.textContent = q;
            li.addEventListener('click', () => {
                sqlInput.value = q;
                executeQuery(q, false);
            });
            historyList.appendChild(li);
        });
    }

    if (btnExecute) {
        btnExecute.addEventListener('click', () => {
            const query = sqlInput.value.trim() || 'SELECT * FROM data LIMIT 10';
            executeQuery(query);
        });
    }

    if (sqlInput) {
        sqlInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                btnExecute.click();
            }
        });
    }

    // Resizing logic for panels
    let isResizing = false;
    const topPanel = document.querySelector('.csv-top-panel');
    const bottomPanel = document.querySelector('.csv-bottom-panel');
    const resizeHandle = document.querySelector('.csv-resize-handle');

    if (resizeHandle) {
        resizeHandle.addEventListener('mousedown', function (e) {
            isResizing = true;
            document.body.style.cursor = 'row-resize';
            e.preventDefault();
        });

        window.addEventListener('mousemove', function (e) {
            if (!isResizing) return;
            const containerOffsetTop = document.querySelector('.csv-container').offsetTop;
            const headerHeight = document.querySelector('.csv-header').offsetHeight;

            // Pointer position relative to the flexible area
            const pointerY = e.clientY - containerOffsetTop - headerHeight;
            const totalHeight = window.innerHeight - headerHeight;

            // Limit bounds
            if (pointerY > 100 && pointerY < totalHeight - 100) {
                const topPct = (pointerY / totalHeight) * 100;
                const bottomPct = 100 - topPct;

                topPanel.style.flex = `0 0 ${topPct}%`;
                bottomPanel.style.flex = `0 0 ${bottomPct}%`;
            }
        });

        window.addEventListener('mouseup', function (e) {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
            }
        });
    }

    // Initial load
    if (filename) {
        executeQuery('SELECT * FROM data LIMIT 10', false);
    }
});

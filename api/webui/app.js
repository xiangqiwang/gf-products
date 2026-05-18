document.addEventListener('DOMContentLoaded', () => {
    // ---- Default Date Initialization ----
    function initDefaultDates() {
        const now = new Date();
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(now.getFullYear() - 1);

        const formatDateForInput = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${minutes}`;
        };

        const startStr = formatDateForInput(oneYearAgo);
        const endStr = formatDateForInput(now);

        // Update all date inputs in the document
        ['start_date', 'end_date', 'q_start', 'q_end'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = (id.includes('start') ? startStr : endStr);
        });
    }
    initDefaultDates();

    // ---- Navigation Logic ----
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            // Remove active classes
            navItems.forEach(nav => nav.classList.remove('active'));
            sections.forEach(sec => sec.classList.remove('active'));
            
            // Add active to clicked nav and corresponding section
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // ---- Platform Tiled Selection Logic ----
    function initPlatformSelector(containerId, hiddenInputId, isMulti = false) {
        const container = document.getElementById(containerId);
        const hiddenInput = document.getElementById(hiddenInputId);
        if (!container || !hiddenInput) return;

        const tiles = container.querySelectorAll('.platform-tile');
        tiles.forEach(tile => {
            tile.addEventListener('click', () => {
                const val = tile.getAttribute('data-value');
                
                if (!isMulti) {
                    // Single select logic
                    tiles.forEach(t => t.classList.remove('active'));
                    tile.classList.add('active');
                    hiddenInput.value = val;
                } else {
                    // Multi select logic with "all" support
                    if (val === 'all') {
                        // Select "all", deselect others
                        tiles.forEach(t => t.classList.remove('active'));
                        tile.classList.add('active');
                    } else {
                        // Select a specific platform, deselect "all"
                        const allTile = container.querySelector('[data-value="all"]');
                        if (allTile) allTile.classList.remove('active');
                        
                        tile.classList.toggle('active');
                        
                        // If nothing is selected, default back to "all"
                        const activeTiles = container.querySelectorAll('.platform-tile.active');
                        if (activeTiles.length === 0 && allTile) {
                            allTile.classList.add('active');
                        }
                    }
                    
                    // Update hidden input with comma separated values
                    const values = Array.from(container.querySelectorAll('.platform-tile.active'))
                                      .map(t => t.getAttribute('data-value'));
                    hiddenInput.value = values.join(',');
                }
            });
        });
    }

    initPlatformSelector('platform-selector', 'platform', false);
    initPlatformSelector('q-platform-selector', 'q_platform', true);

    // ---- Advanced Settings UI Toggle ----
    const crawlerTypeSelect = document.getElementById('crawler_type');
    const advancedSettings = document.getElementById('advanced-settings');
    
    function toggleAdvancedSettings() {
        if (crawlerTypeSelect.value === 'search') {
            advancedSettings.style.display = 'block';
        } else {
            advancedSettings.style.display = 'none';
        }
    }
    
    crawlerTypeSelect.addEventListener('change', toggleAdvancedSettings);
    toggleAdvancedSettings(); // Initial check

    // ---- Clear Database Logic ----
    const btnClearDb = document.getElementById('btn-clear-db');
    if (btnClearDb) {
        btnClearDb.addEventListener('click', async () => {
            if (!confirm('确定要清除数据库吗？这将永久删除所有已采集的数据。')) {
                return;
            }
            
            btnClearDb.disabled = true;
            btnClearDb.textContent = '⌛ 正在清除...';
            
            try {
                const response = await fetch('/api/data/clear_database', { method: 'POST' });
                const data = await response.json();
                
                if (response.ok) {
                    alert('数据库已成功清空并重新初始化。');
                    // Refresh data table if currently in query view
                    if (document.getElementById('query').classList.contains('active')) {
                        document.getElementById('table-body').innerHTML = '<tr><td colspan="4" class="text-center">数据库已清空</td></tr>';
                    }
                } else {
                    alert('清除失败: ' + (data.detail || '未知错误'));
                }
            } catch (e) {
                alert('请求失败: ' + e.message);
            } finally {
                btnClearDb.disabled = false;
                btnClearDb.textContent = '🗑️ 清除数据库';
            }
        });
    }

    // ---- Date Initialization (Local Time) ----
    const now = new Date();
    const lastWeek = new Date();
    lastWeek.setDate(now.getDate() - 7);
    
    const formatDateLocal = (date) => {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    };

    const formatDateTimeLocal = (date) => {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${d}T${h}:${min}`;
    };
    
    document.getElementById('start_date').value = formatDateLocal(lastWeek);
    document.getElementById('end_date').value = formatDateLocal(now);
    document.getElementById('q_start').value = formatDateTimeLocal(lastWeek);
    document.getElementById('q_end').value = formatDateTimeLocal(now);

    // ---- Crawler Collection Logic ----
    const crawlerForm = document.getElementById('crawler-form');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const summaryCard = document.getElementById('task-summary');
    const summaryStart = document.getElementById('summary-start');
    const summaryEnd = document.getElementById('summary-end');
    const summaryCount = document.getElementById('summary-count');
    const statusText = document.getElementById('crawler-status');

    let lastStatus = 'idle';

    async function updateStatus() {
        try {
            const response = await fetch('/api/crawler/status');
            const data = await response.json();
            
            statusText.textContent = getStatusLabel(data.status);
            statusText.className = `status-${data.status}`;
            
            // Handle Task Summary visibility
            if (data.status === 'running') {
                btnStart.disabled = true;
                btnStop.disabled = false;
                if (summaryCard) summaryCard.style.display = 'none';
            } else if (data.status === 'idle') {
                btnStart.disabled = false;
                btnStop.disabled = true;
                
                // If it just finished, show the summary
                if (lastStatus === 'running' || lastStatus === 'stopping') {
                    if (summaryCard && data.started_at && data.ended_at) {
                        summaryStart.textContent = formatIso(data.started_at);
                        summaryEnd.textContent = formatIso(data.ended_at);
                        summaryCount.textContent = data.total_collected || 0;
                        summaryCard.style.display = 'block';
                    }
                }
            } else {
                btnStart.disabled = false;
                btnStop.disabled = true;
            }
            
            lastStatus = data.status;
        } catch (e) {
            console.error('Failed to poll status:', e);
        }
    }

    function getStatusLabel(status) {
        const labels = {
            'idle': '空闲',
            'running': '正在采集...',
            'stopping': '正在停止...',
            'error': '发生错误'
        };
        return labels[status] || status;
    }

    function formatIso(isoStr) {
        if (!isoStr) return '-';
        const date = new Date(isoStr);
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        const s = String(date.getSeconds()).padStart(2, '0');
        return `${y}-${m}-${d} ${h}:${min}:${s}`;
    }

    // Poll status every 2 seconds
    setInterval(updateStatus, 2000);
    updateStatus();

    crawlerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const platform = document.getElementById('platform').value;
        const type = document.getElementById('crawler_type').value;
        const loginType = document.getElementById('login_type').value;
        const keywords = document.getElementById('keyword').value;
        const maxNotesCount = parseInt(document.getElementById('max_notes_count').value) || 20;
        const startDate = document.getElementById('start_date').value;
        const endDate = document.getElementById('end_date').value;

        btnStart.disabled = true;
        btnStop.disabled = false;

        try {
            const response = await fetch('/api/crawler/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    platform: platform,
                    crawler_type: type,
                    login_type: loginType,
                    keywords: keywords,
                    max_notes_count: maxNotesCount,
                    start_date: startDate,
                    end_date: endDate
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                alert('启动失败: ' + (data.detail || '未知错误'));
                btnStart.disabled = false;
                btnStop.disabled = true;
            }
        } catch (error) {
            alert('请求错误: ' + error.message);
            btnStart.disabled = false;
            btnStop.disabled = true;
        }
    });

    btnStop.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/crawler/stop', { method: 'POST' });
            const data = await response.json();
            
            // Reset UI anyway
            btnStart.disabled = false;
            btnStop.disabled = true;
        } catch (e) {
            alert('停止请求失败: ' + e.message);
            btnStart.disabled = false;
            btnStop.disabled = true;
        }
    });

    // ---- Data Query Logic ----
    const queryForm = document.getElementById('query-form');
    const tableHeadRow = document.getElementById('table-head-row');
    const tableBody = document.getElementById('table-body');
    const paginationInfo = document.getElementById('pagination-info');

    const formatTs = (ts) => {
        if (!ts) return '-';
        const date = new Date(ts);
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        const s = String(date.getSeconds()).padStart(2, '0');
        return `${y}-${m}-${d} ${h}:${min}:${s}`;
    };

    // Field mapping for different platforms
    const tableMappings = {
        'xhs': [
            { key: '_idx', label: '序号' },
            { key: 'title', label: '内容' },
            { key: 'nickname', label: '作者' },
            { key: 'display_gender', label: '性别' },
            { key: 'display_fans', label: '粉丝量' },
            { key: 'display_ip', label: 'IP属地' },
            { key: 'create_time', label: '发布时间', format: (val) => formatTs(val) },
            { key: 'liked_count', label: '点赞' },
            { key: 'note_url', label: '链接', isUrl: true }
        ],
        'dy': [
            { key: '_idx', label: '序号' },
            { key: 'title', label: '内容' },
            { key: 'nickname', label: '作者' },
            { key: 'display_gender', label: '性别' },
            { key: 'display_fans', label: '粉丝量' },
            { key: 'display_ip', label: 'IP属地' },
            { key: 'create_time', label: '发布时间', format: (val) => formatTs(val) },
            { key: 'liked_count', label: '点赞' },
            { key: 'aweme_url', label: '链接', isUrl: true }
        ],
        'wb': [
            { key: '_idx', label: '序号' },
            { key: 'content', label: '内容', format: (val) => (val||'').substring(0, 30) + '...' },
            { key: 'nickname', label: '作者' },
            { key: 'display_gender', label: '性别' },
            { key: 'display_fans', label: '粉丝数' },
            { key: 'display_ip', label: 'IP属地' },
            { key: 'create_time', label: '发布时间', format: (val) => formatTs(val) },
            { key: 'liked_count', label: '点赞' },
            { key: 'note_url', label: '链接', isUrl: true }
        ],
        'mixed': [
            { key: '_idx', label: '序号' },
            { key: 'platform_type', label: '平台', format: (val) => {
                const map = {'xhs':'小红书','wb':'微博','dy':'抖音','bili':'B站','ks':'快手','zhihu':'知乎'};
                return map[val] || val;
            }},
            { key: 'title', label: '内容/标题', format: (val, row) => (val || row.content || row.desc || '').substring(0, 20) + '...' },
            { key: 'nickname', label: '作者' },
            { key: 'display_gender', label: '性别' },
            { key: 'display_fans', label: '粉丝量' },
            { key: 'display_ip', label: 'IP属地' },
            { key: 'create_time', label: '发布时间', format: (val) => formatTs(val) },
            { key: 'liked_count', label: '互动' },
            { key: 'note_url', label: '链接', isUrl: true }
        ]
    };
    
    // Default mapping if not explicitly defined
    const defaultMapping = tableMappings['mixed'];

    let currentQueryPage = 1;
    const itemsPerPage = 50;

    async function performSearch(page = 1) {
        currentQueryPage = page;
        const platform = document.getElementById('q_platform').value;
        const keyword = document.getElementById('q_keyword').value;
        const startTime = document.getElementById('q_start').value;
        const endTime = document.getElementById('q_end').value;

        // Construct query URL
        const url = new URL(window.location.origin + '/api/data/sqlite_query');
        url.searchParams.append('platform', platform);
        url.searchParams.append('page', page);
        url.searchParams.append('limit', itemsPerPage);
        if (keyword) url.searchParams.append('keyword', keyword);
        if (startTime) url.searchParams.append('start_time', new Date(startTime).getTime());
        if (endTime) url.searchParams.append('end_time', new Date(endTime).getTime());

        try {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">正在汇总各平台数据...</td></tr>';
            console.log('Query URL:', url.toString());
            const response = await fetch(url);
            const resData = await response.json();
            console.log('Query Response:', resData);

            if (!response.ok || resData.error) {
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center log-level-error">${resData.error || '查询失败'}</td></tr>`;
                return;
            }

            const data = resData.data;
            const total = resData.total;
            paginationInfo.textContent = `共 ${total} 条结果`;

            if (!data || data.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center">没有查到相关数据</td></tr>';
                document.getElementById('prev-page').disabled = true;
                document.getElementById('next-page').disabled = true;
                return;
            }

            // Update pagination UI
            const totalPages = Math.ceil(total / itemsPerPage);
            document.getElementById('current-page-display').textContent = `第 ${currentQueryPage} / ${totalPages || 1} 页`;
            document.getElementById('prev-page').disabled = currentQueryPage <= 1;
            document.getElementById('next-page').disabled = currentQueryPage >= totalPages;

            // Determine which mapping to use
            let mappingKey = platform;
            if (platform.includes(',') || platform === 'all') {
                mappingKey = 'mixed';
            }
            const columns = tableMappings[mappingKey] || defaultMapping;
            tableHeadRow.innerHTML = columns.map(col => `<th>${col.label}</th>`).join('');

            // Render table body
            tableBody.innerHTML = data.map((row, rowIndex) => {
                const cells = columns.map(col => {
                    if (col.key === '_idx') {
                        return `<td>${(currentQueryPage - 1) * itemsPerPage + rowIndex + 1}</td>`;
                    }
                    let val = row[col.key] || '';
                    if (col.format) val = col.format(val, row);
                    if (col.isUrl) {
                        const link = row.note_url || row.aweme_url || row.video_url || '#';
                        return `<td><a href="${link}" target="_blank">查看</a></td>`;
                    }
                    return `<td>${val}</td>`;
                }).join('');
                return `<tr>${cells}</tr>`;
            }).join('');

        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center log-level-error">网络错误: ${error.message}</td></tr>`;
        }
    }

    queryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        performSearch(1);
    });

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentQueryPage > 1) {
            performSearch(currentQueryPage - 1);
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        performSearch(currentQueryPage + 1);
    });

    // ---- History Logic ----
    const historyBody = document.getElementById('history-body');
    const modalDetail = document.getElementById('modal-task-detail');
    const closeDetail = document.getElementById('close-detail');
    let historyTasks = []; // Cache to store tasks
    
    async function fetchHistory() {
        try {
            historyBody.innerHTML = '<tr><td colspan="6" class="text-center">加载中...</td></tr>';
            const res = await fetch('/api/data/collection_history');
            const data = await res.json();
            
            if (!res.ok || data.error) {
                historyBody.innerHTML = `<tr><td colspan="6" class="text-center log-level-error">${data.error || '获取失败'}</td></tr>`;
                return;
            }
            
            if (!data.data || data.data.length === 0) {
                historyBody.innerHTML = '<tr><td colspan="6" class="text-center">暂无采集历史记录</td></tr>';
                return;
            }
            
            historyTasks = data.data; // Update cache
            
            historyBody.innerHTML = data.data.map((item, index) => {
                const keyword = item.keyword || '-';
                const statsMatch = (item.logs || '').split('\n')[0].match(/New: (\d+), Updated: (\d+), Duplicates: (\d+)/);
                let statsHtml = '';
                if (statsMatch) {
                    const [_, n, u, d] = statsMatch;
                    if (parseInt(n) > 0) statsHtml += `<span class="badge badge-success">新:${n}</span> `;
                    if (parseInt(u) > 0) statsHtml += `<span class="badge badge-warning">更:${u}</span> `;
                    if (parseInt(d) > 0) statsHtml += `<span class="badge badge-secondary">重:${d}</span> `;
                }
                
                return `
                <tr>
                    <td>${item.platform.toUpperCase()}</td>
                    <td>${item.crawler_type}</td>
                    <td><span title="${keyword.replace(/"/g, '&quot;')}">${keyword.substring(0, 20)}${keyword.length > 20 ? '...' : ''}</span></td>
                    <td>${item.start_time}</td>
                    <td>
                        <span class="status-badge status-${item.status}">${item.status}</span>
                        <div style="margin-top:4px">${statsHtml}</div>
                    </td>
                    <td><button class="btn-detail" data-index="${index}">详情</button></td>
                </tr>
                `;
            }).join('');
        } catch (e) {
            historyBody.innerHTML = `<tr><td colspan="6" class="text-center log-level-error">网络错误: ${e.message}</td></tr>`;
        }
    }

    // Modal Logic
    async function openTaskDetail(item) {
        document.getElementById('detail-platform').innerText = (item.platform || '').toUpperCase();
        document.getElementById('detail-keyword').innerText = item.keyword || '-';
        document.getElementById('detail-count').innerText = item.total_count || 0;
        document.getElementById('detail-time').innerText = `${item.start_time || '-'} ~ ${item.end_time || '-'}`;
        
        const resultsBody = document.getElementById('detail-results-body');
        resultsBody.innerHTML = '<tr><td colspan="8" class="text-center">正在加载抓取成果...</td></tr>';
        
        modalDetail.style.display = 'block';
        
        // Fetch Results
        try {
            const res = await fetch(`/api/data/task_results/${item.id}`);
            const data = await res.json();
            if (data.data && data.data.length > 0) {
                resultsBody.innerHTML = data.data.map(row => `
                    <tr>
                        <td>${row.index}</td>
                        <td title="${row.content}">${row.content}</td>
                        <td>${row.nickname}</td>
                        <td>${row.gender}</td>
                        <td>${row.fans}</td>
                        <td>${row.ip}</td>
                        <td>${row.stats}</td>
                        <td><a href="${row.link}" target="_blank" class="link-btn">打开</a></td>
                    </tr>
                `).join('');
            } else {
                resultsBody.innerHTML = '<tr><td colspan="8" class="text-center">该任务未捕获到新成果（可能数据已存在或不在时间范围内）</td></tr>';
            }
        } catch (e) {
            resultsBody.innerHTML = `<tr><td colspan="8" class="text-center log-level-error">加载结果失败: ${e.message}</td></tr>`;
        }
    }

    // Delegate click events for history body
    historyBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-detail')) {
            const index = e.target.getAttribute('data-index');
            const item = historyTasks[index];
            if (item) openTaskDetail(item);
        }
    });

    closeDetail.onclick = () => modalDetail.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modalDetail) modalDetail.style.display = 'none';
    }

    // Load history when clicking history nav
    document.querySelector('[data-target="history"]').addEventListener('click', fetchHistory);
});

// Javascript IPC Bridge Controller for COA Parser Hub

let appConfig = null;
let currentTasksList = [];
let activeReviewTask = null;

// Viewer state
let docPreviewPages = [];
let currentPreviewPageIdx = 0;
let currentZoom = 1.0;
let panX = 0;
let panY = 0;
let isPanning = false;
let startX = 0;
let startY = 0;

// Drag and drop sorting state
let draggedItem = null;

// Initialize theme immediately on script load
const initialTheme = localStorage.getItem('theme') || 'light';
document.body.className = initialTheme === 'light' ? 'light-mode' : 'dark-mode';

// Restore sidebar collapsed state immediately on load
const sidebarCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
const sidebarEl = document.querySelector('.sidebar');
const sidebarToggleEl = document.getElementById('sidebar-toggle-btn');
if (sidebarEl && sidebarToggleEl) {
    if (sidebarCollapsed) {
        sidebarEl.classList.add('collapsed');
        sidebarToggleEl.innerText = '▶';
        sidebarToggleEl.title = '展開側邊欄';
    } else {
        sidebarEl.classList.remove('collapsed');
        sidebarToggleEl.innerText = '◀';
        sidebarToggleEl.title = '收合側邊欄';
    }
}

// Initialize app when pywebview is fully bridged
window.addEventListener('pywebviewready', () => {
    appendSystemLog("已成功連接 Python 後端引擎。");
    initApp();
});

function setTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('light-mode');
        document.body.classList.remove('dark-mode');
        const lightBtn = document.getElementById('theme-light-btn');
        const darkBtn = document.getElementById('theme-dark-btn');
        if (lightBtn && darkBtn) {
            lightBtn.classList.add('btn-primary');
            lightBtn.classList.remove('btn-secondary');
            darkBtn.classList.add('btn-secondary');
            darkBtn.classList.remove('btn-primary');
        }
    } else {
        document.body.classList.add('dark-mode');
        document.body.classList.remove('light-mode');
        const lightBtn = document.getElementById('theme-light-btn');
        const darkBtn = document.getElementById('theme-dark-btn');
        if (lightBtn && darkBtn) {
            darkBtn.classList.add('btn-primary');
            darkBtn.classList.remove('btn-secondary');
            lightBtn.classList.add('btn-secondary');
            lightBtn.classList.remove('btn-primary');
        }
    }
    localStorage.setItem('theme', theme);
}
window.setTheme = setTheme;

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    if (sidebar && toggleBtn) {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        toggleBtn.innerText = isCollapsed ? '▶' : '◀';
        toggleBtn.title = isCollapsed ? '展開側邊欄' : '收合側邊欄';
        localStorage.setItem('sidebar-collapsed', isCollapsed ? 'true' : 'false');
    }
}
window.toggleSidebar = toggleSidebar;

async function initApp() {
    try {
        // Initialize theme button states in DOM
        setTheme(localStorage.getItem('theme') || 'light');

        // 1. Load general settings
        await refreshConfig();
        
        // 2. Load and mask key
        await checkAPIKeyStatus();
        
        // 3. Load tasks from SQLite database
        await loadTasks();
        
        // 4. Initialize pan & zoom event listeners
        initViewerPanAndZoom();
        
        appendSystemLog("系統控制儀表板初始化成功。");
    } catch (err) {
        console.error("Initialization error:", err);
        appendSystemLog("系統初始化時發生錯誤：" + err, "error-log");
    }
}

// =============================================================================
// TAB NAVIGATION
// =============================================================================
function switchTab(tabId, preventAutoLoad = false) {
    // Toggle sidebar tabs active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    const activeNav = document.getElementById(`nav-${tabId}`);
    if (activeNav) activeNav.classList.add('active');

    // Toggle panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    const activePane = document.getElementById(`pane-${tabId}`);
    if (activePane) activePane.classList.add('active');

    // Tab-specific loading logic
    if (tabId === 'tasks') {
        loadTasks();
    } else if (tabId === 'settings') {
        renderSettings();
    } else if (tabId === 'review') {
        if (!preventAutoLoad) {
            autoLoadReviewTask();
        }
    }
}

async function autoLoadReviewTask() {
    if (!window.pywebview || !window.pywebview.api) return;
    
    // Check if we already have an active task loaded
    if (activeReviewTask) {
        // Just reload preview and data to be safe
        loadReviewTask(activeReviewTask);
        return;
    }
    
    // Fetch the latest tasks list from DB
    currentTasksList = await window.pywebview.api.get_tasks();
    
    // Try to find the first task needing review
    const reviewable = currentTasksList.find(t => t.status === "ReviewNeeded");
    if (reviewable) {
        loadReviewTask(reviewable);
    } else {
        // Fallback to first completed task to allow edits
        const completed = currentTasksList.find(t => t.status === "Completed");
        if (completed) {
            loadReviewTask(completed);
        } else {
            // No tasks found in database
            const previewContainer = document.getElementById('document-preview-container');
            previewContainer.innerHTML = `<div class="preview-placeholder">目前隊列中沒有任何化學證書。請先至「排程儀表板」選擇資料夾並開始分析。</div>`;
            
            // Clear review form fields
            document.getElementById('viewer-doc-title').innerText = "文件預覽";
            document.getElementById('review-file-path').value = "";
            
            // Clear all input values
            const formInputs = document.querySelectorAll('#review-fields-form input[type="text"], #review-fields-form select');
            formInputs.forEach(input => input.value = "");
            
            const badges = document.querySelectorAll('#review-fields-form .badge-conf');
            badges.forEach(badge => {
                badge.innerText = "-";
                badge.className = "badge-conf";
            });
            
            const traces = document.querySelectorAll('#review-fields-form .traceability-info');
            traces.forEach(trace => trace.innerText = "來源原文定位: N/A");
            
            document.getElementById('review-warnings-box').style.display = 'none';
        }
    }
}

// =============================================================================
// SIDEBAR STATUS & CONFIG
// =============================================================================
async function refreshConfig() {
    if (window.pywebview && window.pywebview.api) {
        appConfig = await window.pywebview.api.get_config();
        
        // Update GAS URL Dot Indicator
        const gasUrl = appConfig.gas_web_app_url;
        const gasDot = document.getElementById('gas-status-dot');
        const gasText = document.getElementById('gas-status-text');
        const gasContainer = document.getElementById('gas-status-container');
        
        if (gasUrl) {
            gasDot.className = "dot green";
            gasDot.style.boxShadow = "0 0 8px var(--success)";
            gasText.innerText = "GAS 雲端已啟用";
            if (gasContainer) gasContainer.title = "GAS 雲端已啟用";
        } else {
            gasDot.className = "dot";
            gasDot.style.boxShadow = "none";
            gasText.innerText = "GAS 雲端未啟用";
            if (gasContainer) gasContainer.title = "GAS 雲端未啟用";
        }
    }
}

async function checkAPIKeyStatus() {
    if (window.pywebview && window.pywebview.api) {
        const maskedKey = await window.pywebview.api.get_api_key_masked();
        const apiDot = document.getElementById('api-status-dot');
        const apiText = document.getElementById('api-status-text');
        const apiContainer = document.getElementById('api-status-container');
        
        if (maskedKey) {
            apiDot.className = "dot green";
            apiDot.style.boxShadow = "0 0 8px var(--success)";
            apiText.innerText = "Gemini 已授權";
            if (apiContainer) apiContainer.title = "Gemini 已授權";
        } else {
            apiDot.className = "dot orange";
            apiDot.style.boxShadow = "0 0 8px var(--warning)";
            apiText.innerText = "API 金鑰未設定";
            if (apiContainer) apiContainer.title = "API 金鑰未設定";
        }
    }
}

// =============================================================================
// FOLDER INPUT & PIPELINE CONTROL
// =============================================================================
async function selectFolder() {
    if (window.pywebview && window.pywebview.api) {
        const folder = await window.pywebview.api.select_folder();
        if (folder) {
            document.getElementById('selected-folder-path').innerText = folder;
            document.getElementById('btn-start').removeAttribute('disabled');
            appendSystemLog(`已選擇資料夾：${folder}`);
        }
    }
}

async function startPipeline() {
    const folderPath = document.getElementById('selected-folder-path').innerText;
    if (!folderPath || folderPath === "未選擇任何資料夾") return;
    
    // Disable actions
    document.getElementById('btn-select-folder').setAttribute('disabled', 'true');
    document.getElementById('btn-start').setAttribute('disabled', 'true');
    document.getElementById('btn-cancel').removeAttribute('disabled');
    
    // Clear log and open console
    clearLogs();
    const logDrawer = document.getElementById('log-drawer');
    if (logDrawer.classList.contains('collapsed')) {
        toggleLogDrawer();
    }
    
    // Reset stats cards UI
    document.getElementById('stat-total').innerText = "0";
    document.getElementById('stat-completed').innerText = "0";
    document.getElementById('stat-review').innerText = "0";
    document.getElementById('stat-failed').innerText = "0";
    
    // Show progress bar
    const progressBanner = document.getElementById('progress-banner');
    progressBanner.style.display = 'block';
    updateProgressBar(0, "正在掃描資料夾內容...");
    
    // Trigger Python bridge call
    appendSystemLog("開始掃描檔案並建立分析排程...");
    const res = await window.pywebview.api.start_pipeline(folderPath);
    
    if (res.status === "error") {
        showToast("啟動分析排程錯誤: " + res.message);
        resetPipelineControls();
    } else if (res.status === "empty") {
        showToast("沒有找到可處理檔案: " + res.message);
        resetPipelineControls();
    }
}

async function cancelPipeline() {
    if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.cancel_pipeline();
        appendSystemLog("使用者已取消分析排程。", "warn-log");
        resetPipelineControls();
    }
}

function resetPipelineControls() {
    document.getElementById('btn-select-folder').removeAttribute('disabled');
    document.getElementById('btn-start').removeAttribute('disabled');
    document.getElementById('btn-cancel').setAttribute('disabled', 'true');
    document.getElementById('progress-banner').style.display = 'none';
}

function updateProgressBar(percent, statusText) {
    document.getElementById('progress-percent').innerText = `${percent}%`;
    document.getElementById('progress-bar-fill').style.width = `${percent}%`;
    document.getElementById('progress-status').innerText = statusText;
}

// =============================================================================
// PIPELINE PROCESS BACKEND EVENT HANDLERS
// =============================================================================
window.onPipelineProgress = function(status, message, taskId) {
    // 1. Add log to drawer
    if (status === "error") {
        appendSystemLog(message, "error-log");
    } else if (status === "progress" && message.includes("Skipping")) {
        appendSystemLog(message, "warn-log");
    } else {
        appendSystemLog(message, "info-log");
    }
    
    // 2. Query stats & update table progress live
    loadTasks();
    
    // 3. Update Progress Bar
    if (status === "finished") {
        showToast("排程分析圓滿完成！將自動開啟人工驗證中心...");
        updateProgressBar(100, "完成");
        setTimeout(() => {
            document.getElementById('progress-banner').style.display = 'none';
            // Auto switch to review tab to let the user review extracted data immediately
            switchTab('review');
        }, 1500);
        resetPipelineControls();
    } else if (status === "error") {
        showToast("分析過程中發生錯誤。");
        resetPipelineControls();
    }
};

// =============================================================================
// TASK LISTING & RENDERING (DASHBOARD GRID)
// =============================================================================
async function loadTasks() {
    if (!window.pywebview || !window.pywebview.api) return;
    
    currentTasksList = await window.pywebview.api.get_tasks();
    
    // Compute stats
    let total = currentTasksList.length;
    let completed = 0;
    let reviewNeeded = 0;
    let failed = 0;
    
    const tbody = document.getElementById('tasks-tbody');
    tbody.innerHTML = '';
    
    if (total === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state">隊列目前是空的。請選擇包含 COA 證書的資料夾以開始。</td></tr>`;
        updateStats(0, 0, 0, 0);
        return;
    }
    
    currentTasksList.forEach(task => {
        // Increment stats
        if (task.status === "Completed") completed++;
        else if (task.status === "ReviewNeeded") reviewNeeded++;
        else if (task.status === "Failed") failed++;
        
        // Assemble Row
        const tr = document.createElement('tr');
        tr.id = `task-row-${task.id}`;
        
        // Col 1: Filename
        const tdName = document.createElement('td');
        tdName.style.fontFamily = "var(--font-sans)";
        tdName.style.fontWeight = "500";
        tdName.innerText = task.file_name;
        
        // Col 2: Status
        const tdStatus = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `badge-status ${task.status.toLowerCase()}`;
        
        let statusZH = task.status;
        if (task.status === "ReviewNeeded") statusZH = "待確認";
        else if (task.status === "Completed") statusZH = "已完成";
        else if (task.status === "Failed") statusZH = "失敗";
        
        badge.innerText = statusZH;
        tdStatus.appendChild(badge);
        
        // Col 3: Warnings list
        const tdWarnings = document.createElement('td');
        tdWarnings.style.fontSize = "12px";
        if (task.validation_errors && task.validation_errors.length > 0) {
            const warningsText = task.validation_errors.join('; ');
            tdWarnings.className = "orange-text";
            tdWarnings.innerText = warningsText;
        } else if (task.status === "Completed") {
            tdWarnings.className = "green-text";
            tdWarnings.innerText = "已驗證並同步至雲端試算表";
        } else {
            tdWarnings.innerText = "-";
        }
        
        // Col 4: Action button
        const tdActions = document.createElement('td');
        const actionBtn = document.createElement('button');
        actionBtn.className = "btn btn-sm btn-secondary";
        
        if (task.status === "ReviewNeeded") {
            actionBtn.className = "btn btn-sm btn-primary";
            actionBtn.innerText = "🔍 審核";
            actionBtn.onclick = () => loadReviewTask(task);
        } else if (task.status === "Completed") {
            actionBtn.innerText = "✏️ 編輯";
            actionBtn.onclick = () => loadReviewTask(task);
        } else {
            actionBtn.innerText = "❌ 刪除";
            actionBtn.className = "btn btn-sm btn-danger";
            actionBtn.onclick = () => deleteTask(task.file_path);
        }
        
        tdActions.appendChild(actionBtn);
        
        tr.appendChild(tdName);
        tr.appendChild(tdStatus);
        tr.appendChild(tdWarnings);
        tr.appendChild(tdActions);
        
        tbody.appendChild(tr);
    });
    
    updateStats(total, completed, reviewNeeded, failed);
}

function updateStats(total, completed, review, failed) {
    document.getElementById('stat-total').innerText = total;
    document.getElementById('stat-completed').innerText = completed;
    document.getElementById('stat-review').innerText = review;
    document.getElementById('stat-failed').innerText = failed;
    
    // Update badge counter in sidebar
    const counter = document.getElementById('review-counter');
    if (review > 0) {
        counter.innerText = review;
        counter.style.display = 'block';
    } else {
        counter.style.display = 'none';
    }
}

async function deleteTask(path) {
    if (confirm("確定要從隊列中移除此檔案嗎？")) {
        await window.pywebview.api.delete_task(path);
        showToast("任務已移除。");
        loadTasks();
    }
}

async function clearQueue() {
    if (confirm("警告：這將會清除本機資料庫中的所有排程紀錄！確定要清空嗎？")) {
        await window.pywebview.api.clear_queue();
        showToast("隊列已成功清空。");
        loadTasks();
    }
}

// =============================================================================
// VERIFICATION HUB & INTERACTIVE DUAL VIEW
// =============================================================================
async function loadReviewTask(task) {
    activeReviewTask = task;
    switchTab('review', true);
    
    // 1. Reset Preview Pane Loader
    const previewContainer = document.getElementById('document-preview-container');
    previewContainer.innerHTML = `<div class="preview-placeholder">正在載入文件頁面預覽...</div>`;
    
    document.getElementById('viewer-doc-title').innerText = task.file_name;
    document.getElementById('review-file-path').value = task.file_path;
    
    // Reset zoom
    currentZoom = 1.0;
    updateZoomDisplay();
    
    // 2. Call Bridge to Render PDF/Image Pages
    docPreviewPages = await window.pywebview.api.get_document_pages_b64(task.file_path);
    currentPreviewPageIdx = 0;
    
    if (docPreviewPages && docPreviewPages.length > 0) {
        renderPreviewPage();
        updatePageControls();
    } else {
        previewContainer.innerHTML = `<div class="preview-placeholder text-danger">⚠️ 無法渲染此檔案的預覽網頁。</div>`;
    }
    
    // 3. Fill Form Fields
    const data = task.extracted_data || {};
    
    // Fill Raw values
    document.getElementById('review-product-raw').value = data.product_raw || "N/A";
    document.getElementById('review-brand-raw').value = data.brand_raw || "N/A";
    document.getElementById('review-batch-no').value = data.batch_no || "N/A";
    document.getElementById('review-cas-raw').value = data.cas_no_raw || "N/A";
    document.getElementById('review-mw-raw').value = data.mw_raw || "N/A";
    document.getElementById('review-expiry-raw').value = data.expiry_raw || "N/A";
    document.getElementById('review-purity-raw').value = data.purity_raw || "N/A";
    document.getElementById('review-amount-raw').value = data.amount_raw || "N/A";
    document.getElementById('review-storage-raw').value = data.storage_raw || "N/A";
    
    // Fill Standard values
    document.getElementById('review-product-std').value = data.product_std || "N/A";
    document.getElementById('review-brand-std').value = data.brand_std || "N/A";
    document.getElementById('review-cas-std').value = data.cas_no_std || "N/A";
    document.getElementById('review-mw-std').value = data.mw_std || "N/A";
    document.getElementById('review-expiry-std').value = data.expiry_std || "N/A";
    document.getElementById('review-purity-std').value = data.purity_std || "N/A";
    document.getElementById('review-amount-std').value = data.amount_std || "N/A";
    document.getElementById('review-storage-std').value = data.storage_std || "RT";
    
    // Fill Confidences
    setConfidenceBadge('conf-product', data.product_std_confidence || 'high');
    setConfidenceBadge('conf-brand', data.brand_raw_confidence || 'high');
    setConfidenceBadge('conf-batch', data.batch_no_confidence || 'high');
    setConfidenceBadge('conf-cas', data.cas_no_raw_confidence || 'high');
    setConfidenceBadge('conf-mw', data.mw_raw_confidence || 'high');
    setConfidenceBadge('conf-expiry', data.expiry_raw_confidence || 'high');
    setConfidenceBadge('conf-purity', data.purity_raw_confidence || 'high');
    setConfidenceBadge('conf-amount', data.amount_raw_confidence || 'high');
    setConfidenceBadge('conf-storage', data.storage_raw_confidence || 'high');
    
    // Fill Traceability Source Sentences
    const trace = data.traceability || {};
    document.getElementById('trace-product').innerText = "來源原文定位: " + (trace.product_source || "N/A");
    document.getElementById('trace-brand').innerText = "來源原文定位: " + (trace.brand_source || "N/A");
    document.getElementById('trace-batch').innerText = "來源原文定位: " + (trace.batch_source || "N/A");
    document.getElementById('trace-cas').innerText = "來源原文定位: " + (trace.cas_no_source || "N/A");
    document.getElementById('trace-mw').innerText = "來源原文定位: " + (trace.mw_source || "N/A");
    document.getElementById('trace-expiry').innerText = "來源原文定位: " + (trace.expiry_source || "N/A");
    document.getElementById('trace-purity').innerText = "來源原文定位: " + (trace.purity_source || "N/A");
    document.getElementById('trace-amount').innerText = "來源原文定位: " + (trace.amount_source || "N/A");
    document.getElementById('trace-storage').innerText = "來源原文定位: " + (trace.storage_source || "N/A");
    
    // 4. Render Validation Warning alerts
    const alertsBox = document.getElementById('review-warnings-box');
    const alertsList = document.getElementById('review-warnings-list');
    alertsList.innerHTML = '';
    
    if (task.validation_errors && task.validation_errors.length > 0) {
        alertsBox.style.display = 'block';
        task.validation_errors.forEach(err => {
            const li = document.createElement('li');
            li.innerText = err;
            alertsList.appendChild(li);
        });
    } else {
        alertsBox.style.display = 'none';
    }
}

function setConfidenceBadge(elementId, val) {
    const badge = document.getElementById(elementId);
    let valZH = val;
    if (val === 'high') valZH = '高';
    else if (val === 'medium') valZH = '中';
    else if (val === 'low') valZH = '低';
    
    badge.innerText = valZH;
    badge.className = `badge-conf ${val.toLowerCase()}`;
}

// Preview page renderers
function renderPreviewPage() {
    const container = document.getElementById('document-preview-container');
    container.innerHTML = '';
    
    // Reset zoom and pan offsets when loading a new document
    currentZoom = 1.0;
    panX = 0;
    panY = 0;
    updateZoomDisplay();
    container.style.cursor = 'grab';
    
    const imgData = docPreviewPages[currentPreviewPageIdx];
    const imgEl = document.createElement('img');
    imgEl.className = "viewer-image";
    imgEl.id = "active-viewer-img";
    imgEl.src = `data:image/jpeg;base64,${imgData}`;
    imgEl.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    container.appendChild(imgEl);
}

function updatePageControls() {
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const counter = document.getElementById('page-counter');
    
    counter.innerText = `第 ${currentPreviewPageIdx + 1} 頁 / 共 ${docPreviewPages.length} 頁`;
    
    if (currentPreviewPageIdx > 0) prevBtn.removeAttribute('disabled');
    else prevBtn.setAttribute('disabled', 'true');
    
    if (currentPreviewPageIdx < docPreviewPages.length - 1) nextBtn.removeAttribute('disabled');
    else nextBtn.setAttribute('disabled', 'true');
}

function changePreviewPage(direction) {
    const newIdx = currentPreviewPageIdx + direction;
    if (newIdx >= 0 && newIdx < docPreviewPages.length) {
        currentPreviewPageIdx = newIdx;
        renderPreviewPage();
        updatePageControls();
    }
}

function zoomImage(amount) {
    const nextZoom = currentZoom + amount;
    if (nextZoom >= 0.2 && nextZoom <= 5.0) {
        currentZoom = nextZoom;
        updateZoomDisplay();
        updateImageTransform();
    }
}

function updateZoomDisplay() {
    document.getElementById('zoom-level').innerText = `${Math.round(currentZoom * 100)}%`;
}

function updateImageTransform() {
    const img = document.getElementById('active-viewer-img');
    if (img) {
        img.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    }
}

function initViewerPanAndZoom() {
    const container = document.getElementById('document-preview-container');
    if (!container) return;

    container.addEventListener('mousedown', (e) => {
        const img = document.getElementById('active-viewer-img');
        if (!img) return;
        isPanning = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
        container.style.cursor = 'grabbing';
        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateImageTransform();
    });

    window.addEventListener('mouseup', () => {
        if (isPanning) {
            isPanning = false;
            container.style.cursor = 'grab';
        }
    });

    container.addEventListener('wheel', (e) => {
        const img = document.getElementById('active-viewer-img');
        if (!img) return;
        
        e.preventDefault();
        
        const zoomFactor = 0.1;
        let nextZoom = currentZoom;
        if (e.deltaY < 0) {
            nextZoom += zoomFactor;
        } else {
            nextZoom -= zoomFactor;
        }
        
        // Bound zoom between 0.2 and 5.0
        if (nextZoom >= 0.2 && nextZoom <= 5.0) {
            currentZoom = nextZoom;
            updateZoomDisplay();
            updateImageTransform();
        }
    }, { passive: false });
}

// Submit Human Review Form
async function submitReview() {
    if (!activeReviewTask) return;
    
    const filePath = document.getElementById('review-file-path').value;
    
    // Construct verified data dictionary matching Python schema
    const data = {
        // Raw values
        product_raw: document.getElementById('review-product-raw').value,
        brand_raw: document.getElementById('review-brand-raw').value,
        batch_no: document.getElementById('review-batch-no').value,
        cas_no_raw: document.getElementById('review-cas-raw').value,
        mw_raw: document.getElementById('review-mw-raw').value,
        expiry_raw: document.getElementById('review-expiry-raw').value,
        purity_raw: document.getElementById('review-purity-raw').value,
        amount_raw: document.getElementById('review-amount-raw').value,
        storage_raw: document.getElementById('review-storage-raw').value,
        
        // Standardized values
        product_std: document.getElementById('review-product-std').value,
        brand_std: document.getElementById('review-brand-std').value,
        cas_no_std: document.getElementById('review-cas-std').value,
        mw_std: document.getElementById('review-mw-std').value,
        expiry_std: document.getElementById('review-expiry-std').value,
        purity_std: document.getElementById('review-purity-std').value,
        amount_std: document.getElementById('review-amount-std').value,
        storage_std: document.getElementById('review-storage-std').value,
        
        // Pass along original confidence and traceability unmodified
        product_std_confidence: activeReviewTask.extracted_data.product_std_confidence,
        brand_raw_confidence: activeReviewTask.extracted_data.brand_raw_confidence || 'high',
        batch_no_confidence: activeReviewTask.extracted_data.batch_no_confidence,
        cas_no_raw_confidence: activeReviewTask.extracted_data.cas_no_raw_confidence || 'high',
        mw_raw_confidence: activeReviewTask.extracted_data.mw_raw_confidence || 'high',
        expiry_raw_confidence: activeReviewTask.extracted_data.expiry_raw_confidence,
        purity_raw_confidence: activeReviewTask.extracted_data.purity_raw_confidence,
        amount_raw_confidence: activeReviewTask.extracted_data.amount_raw_confidence || 'high',
        storage_raw_confidence: activeReviewTask.extracted_data.storage_raw_confidence,
        traceability: activeReviewTask.extracted_data.traceability
    };
    
    appendSystemLog(`正在儲存 ${activeReviewTask.file_name} 的驗證校對資料...`);
    const res = await window.pywebview.api.verify_and_complete_task(filePath, data);
    
    if (res.status === "success") {
        showToast(`已儲存並同步：${activeReviewTask.file_name}`);
        // Go next
        await loadNextReviewItem(1);
    } else {
        showToast("儲存失敗：" + res.message);
    }
}

function copyRawToStd(fieldPrefix) {
    const rawEl = document.getElementById(`review-${fieldPrefix}-raw`);
    const stdEl = document.getElementById(`review-${fieldPrefix}-std`);
    if (rawEl && stdEl) {
        if (fieldPrefix === 'storage') {
            const rawVal = rawEl.value.toLowerCase();
            if (rawVal.includes('2-8') || rawVal.includes('4°') || rawVal.includes('4c') || rawVal.includes('refrigerat')) {
                stdEl.value = '4°C';
            } else if (rawVal.includes('-20') || rawVal.includes('freeze') || rawVal.includes('frozen')) {
                stdEl.value = '-20°C';
            } else if (rawVal.includes('room') || rawVal.includes('rt') || rawVal.includes('ambient') || rawVal.includes('15-25')) {
                stdEl.value = 'RT';
            } else {
                stdEl.value = 'RT'; // default fallback
            }
        } else {
            stdEl.value = rawEl.value;
        }
        showToast("已帶入原始值至標準化欄位");
    }
}
window.copyRawToStd = copyRawToStd;

async function skipTask(direction) {
    await loadNextReviewItem(direction);
}

async function loadNextReviewItem(direction) {
    // Reload task lists first to sync statuses
    currentTasksList = await window.pywebview.api.get_tasks();
    
    // Find index of current task
    const currIdx = currentTasksList.findIndex(t => t.file_path === activeReviewTask.file_path);
    
    // Look for next/prev ReviewNeeded item or simply next in queue
    let found = false;
    
    // Look in direction from current index
    let step = direction;
    let nextIdx = currIdx + step;
    
    while (nextIdx >= 0 && nextIdx < currentTasksList.length) {
        const candidate = currentTasksList[nextIdx];
        if (candidate.status === "ReviewNeeded") {
            loadReviewTask(candidate);
            found = true;
            break;
        }
        nextIdx += step;
    }
    
    // If not found in specific direction, look anywhere in the queue
    if (!found) {
        const nextReviewable = currentTasksList.find(t => t.status === "ReviewNeeded");
        if (nextReviewable) {
            loadReviewTask(nextReviewable);
        } else {
            // No more files need review!
            showToast("所有證書已驗證完成並同步！");
            activeReviewTask = null;
            switchTab('tasks');
        }
    }
}

// Listen to Keyboard events for pure keyboard verification workflow
document.addEventListener('keydown', (e) => {
    // Only capture keyboard shortcuts when Verification Hub pane is active
    const reviewPane = document.getElementById('pane-review');
    if (!reviewPane.classList.contains('active') || !activeReviewTask) return;
    
    // Enter key submits (on input tags it naturally triggers submit, but we capture globally to be safe)
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        submitReview();
    }
    
    // Skip to next with Down Arrow (if not inside select option dropdowns)
    if (e.key === 'ArrowDown' && e.ctrlKey) {
        e.preventDefault();
        skipTask(1);
    }
    
    // Return to previous with Up Arrow
    if (e.key === 'ArrowUp' && e.ctrlKey) {
        e.preventDefault();
        skipTask(-1);
    }
});

// =============================================================================
// SETTINGS PANEL & DRAG SORTING
// =============================================================================
async function renderSettings() {
    await refreshConfig();
    
    // Masked Key
    const maskedKey = await window.pywebview.api.get_api_key_masked();
    document.getElementById('settings-gemini-key').value = maskedKey;
    
    // Sync URL
    document.getElementById('settings-gas-url').value = appConfig.gas_web_app_url || '';
    
    // Standardizations
    document.getElementById('settings-name-fmt').value = appConfig.standardization_rules.name_format;
    document.getElementById('settings-date-fmt').value = appConfig.standardization_rules.date_format;
    
    // Mappings
    const maps = appConfig.standardization_rules.temp_mappings || {};
    document.getElementById('mapping-frozen').value = (maps["-20°C"] || []).join(', ');
    document.getElementById('mapping-cold').value = (maps["4°C"] || []).join(', ');
    document.getElementById('mapping-rt').value = (maps["RT"] || []).join(', ');
    
    // Export Columns Sequence list
    renderSortableColumns();
}

function renderSortableColumns() {
    const list = document.getElementById('columns-sortable-list');
    list.innerHTML = '';
    
    const order = appConfig.fields_order || [];
    const visibility = appConfig.fields_visibility || {};
    const headers = appConfig.column_headers || {};
    
    // Default column friendly name labels as fallback
    const friendlyLabels = {
        "brand_raw": "廠牌 (原始)",
        "product_raw": "產品名稱 (原始)",
        "mw_raw": "分子量 (原始)",
        "cas_no_raw": "CAS Number (原始)",
        "batch_no": "生產批號 (Batch No)",
        "expiry_raw": "有效期限 (原始)",
        "amount_raw": "包裝容量 (原始)",
        "purity_raw": "純度/含量 (原始)",
        "storage_raw": "儲存條件 (原始)",
        "brand_std": "廠牌 (標準化)",
        "product_std": "產品名稱 (標準化)",
        "mw_std": "分子量 (標準化)",
        "cas_no_std": "CAS Number (標準化)",
        "expiry_std": "有效期限 (標準化)",
        "amount_std": "包裝容量 (標準化)",
        "purity_std": "純度/含量 (標準化)",
        "storage_std": "儲存條件 (標準化對應)"
    };
    
    order.forEach(fieldId => {
        const isVisible = visibility[fieldId] !== false;
        const currentLabel = headers[fieldId] || friendlyLabels[fieldId] || fieldId;
        
        const li = document.createElement('li');
        li.className = "draggable-item";
        li.draggable = true;
        li.dataset.id = fieldId;
        
        li.innerHTML = `
            <div class="handle-label" style="display: flex; align-items: center; gap: 8px; flex-grow: 1;">
                <span class="drag-icon" style="cursor: grab;">☰</span>
                <input type="text" class="col-name-input" data-id="${fieldId}" value="${currentLabel}" style="flex-grow: 1; max-width: 280px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 6px; padding: 4px 10px; font-size: 0.9rem; transition: border-color var(--transition-fast);">
            </div>
            <div class="sort-actions" style="display: flex; align-items: center; gap: 6px;">
                <button class="sort-btn" onclick="moveColumn('${fieldId}', -1); event.stopPropagation();" title="上移">🔼</button>
                <button class="sort-btn" onclick="moveColumn('${fieldId}', 1); event.stopPropagation();" title="下移">🔽</button>
                <input type="checkbox" class="col-visibility-chk" data-id="${fieldId}" ${isVisible ? 'checked' : ''} style="margin-left: 6px; width: 16px; height: 16px; cursor: pointer;">
            </div>
        `;
        
        // Add Drag Event Listeners
        li.addEventListener('dragstart', handleDragStart);
        li.addEventListener('dragover', handleDragOver);
        li.addEventListener('drop', handleDrop);
        li.addEventListener('dragend', handleDragEnd);
        
        list.appendChild(li);
    });
}

function moveColumn(fieldId, direction) {
    const order = appConfig.fields_order || [];
    const index = order.indexOf(fieldId);
    if (index === -1) return;
    
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= order.length) return; // Boundary check
    
    // Save current check state of visible columns and customized names
    const listItems = document.querySelectorAll('#columns-sortable-list .draggable-item');
    listItems.forEach(item => {
        const id = item.dataset.id;
        const chk = item.querySelector('.col-visibility-chk');
        const inputName = item.querySelector('.col-name-input');
        if (chk) {
            appConfig.fields_visibility[id] = chk.checked;
        }
        if (inputName) {
            if (!appConfig.column_headers) appConfig.column_headers = {};
            appConfig.column_headers[id] = inputName.value.trim();
        }
    });
    
    // Swap items in the order list
    const temp = order[index];
    order[index] = order[newIndex];
    order[newIndex] = temp;
    
    appConfig.fields_order = order;
    
    // Re-render
    renderSortableColumns();
}
window.moveColumn = moveColumn;

// HTML5 Drag and Drop Handlers
function handleDragStart(e) {
    draggedItem = this;
    e.dataTransfer.effectAllowed = 'move';
    this.style.opacity = '0.4';
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault(); 
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation(); 
    }
    
    if (draggedItem !== this) {
        const list = document.getElementById('columns-sortable-list');
        const items = Array.from(list.children);
        const draggedIdx = items.indexOf(draggedItem);
        const targetIdx = items.indexOf(this);
        
        if (draggedIdx < targetIdx) {
            this.after(draggedItem);
        } else {
            this.before(draggedItem);
        }
    }
    return false;
}

function handleDragEnd() {
    this.style.opacity = '1.0';
    draggedItem = null;
}

async function testAndSaveAPIKey() {
    const key = document.getElementById('settings-gemini-key').value.trim();
    if (!key || key.includes('******')) {
        showToast("請輸入新的 API 金鑰。");
        return;
    }
    
    appendSystemLog("正在認證並加密儲存 API 金鑰至憑證管理系統...");
    const res = await window.pywebview.api.save_api_key(key);
    
    if (res.status === "success") {
        showToast("Gemini API 金鑰儲存並測試通過！");
        await checkAPIKeyStatus();
    } else {
        showToast("API 金鑰驗證失敗！請檢查您的金鑰。");
    }
}

async function saveSettings() {
    if (!window.pywebview || !window.pywebview.api) return;
    
    // 1. Gather column sequence, visibility, and customized names
    const listItems = document.querySelectorAll('#columns-sortable-list .draggable-item');
    const order = [];
    const visibility = {};
    const columnHeaders = {};
    
    listItems.forEach(item => {
        const fieldId = item.dataset.id;
        const chk = item.querySelector('.col-visibility-chk');
        const inputName = item.querySelector('.col-name-input');
        
        order.push(fieldId);
        visibility[fieldId] = chk.checked;
        if (inputName) {
            columnHeaders[fieldId] = inputName.value.trim();
        }
    });
    
    // 2. Gather temperature mappings
    const mappingFrozen = document.getElementById('mapping-frozen').value.split(',').map(s => s.trim()).filter(s => s);
    const mappingCold = document.getElementById('mapping-cold').value.split(',').map(s => s.trim()).filter(s => s);
    const mappingRT = document.getElementById('mapping-rt').value.split(',').map(s => s.trim()).filter(s => s);
    
    // 3. Assemble Config object
    const newConfig = {
        gas_web_app_url: document.getElementById('settings-gas-url').value.trim(),
        output_format: "xlsx",
        fields_order: order,
        fields_visibility: visibility,
        column_headers: columnHeaders,
        standardization_rules: {
            name_format: document.getElementById('settings-name-fmt').value,
            date_format: document.getElementById('settings-date-fmt').value,
            temp_mappings: {
                "-20°C": mappingFrozen,
                "4°C": mappingCold,
                "RT": mappingRT
            }
        }
    };
    
    appendSystemLog("正在儲存系統設定設定參數至 config.json...");
    const res = await window.pywebview.api.save_config(newConfig);
    
    if (res.status === "success") {
        showToast("設定已成功儲存套用！");
        await refreshConfig();
    } else {
        showToast("儲存設定失敗。");
    }
}

// =============================================================================
// EXPORT SUMMARY REPORT
// =============================================================================
async function exportExcel() {
    if (!window.pywebview || !window.pywebview.api) return;
    
    const savePath = await window.pywebview.api.select_excel_save_path();
    if (!savePath) return;
    
    appendSystemLog(`正在將已完成的任務資料庫匯出為 Excel 報表：${savePath}...`);
    const res = await window.pywebview.api.export_summary_report(savePath);
    
    if (res.status === "success") {
        showToast("Excel 報表匯出成功！");
        appendSystemLog("Excel 報告已成功儲存。", "info-log");
    } else {
        showToast("匯出失敗：" + res.message);
        appendSystemLog("匯出發生錯誤：" + res.message, "error-log");
    }
}

// =============================================================================
// LOG DRAWER PANEL & TOASTS
// =============================================================================
function toggleLogDrawer() {
    const drawer = document.getElementById('log-drawer');
    
    if (drawer.classList.contains('collapsed')) {
        drawer.classList.remove('collapsed');
        drawer.classList.add('expanded');
    } else {
        drawer.classList.remove('expanded');
        drawer.classList.add('collapsed');
    }
}

window.appendLog = function(msg) {
    const body = document.getElementById('log-drawer-body');
    const log = document.createElement('div');
    log.className = "log-message";
    
    // Classify log type color
    if (msg.includes("[ERROR]")) log.className += " error-log";
    else if (msg.includes("[WARNING]")) log.className += " warn-log";
    else if (msg.includes("[SYSTEM]")) log.className += " system-log";
    else log.className += " info-log";
    
    log.innerText = msg;
    body.appendChild(log);
    
    // Auto Scroll to bottom
    body.scrollTop = body.scrollHeight;
};

function appendSystemLog(msg, typeClass = "system-log") {
    const body = document.getElementById('log-drawer-body');
    const log = document.createElement('div');
    log.className = `log-message ${typeClass}`;
    
    const now = new Date().toLocaleTimeString();
    log.innerText = `[${now}] [介面] ${msg}`;
    body.appendChild(log);
    body.scrollTop = body.scrollHeight;
}

function clearLogs() {
    document.getElementById('log-drawer-body').innerHTML = '';
    appendSystemLog("系統日誌已清空。");
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.className = "toast show";
    setTimeout(() => {
        toast.className = "toast";
    }, 3000);
}

function togglePasswordView(id) {
    const input = document.getElementById(id);
    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

function openGuide() {
    // Native pywebview create a new browser window pointing to user guide instructions!
    if (window.pywebview) {
        // Locate tutorial.html relative path
        window.open('tutorial.html', '_blank', 'width=800,height=600');
    }
}

function copyAllLogs() {
    const messages = Array.from(document.querySelectorAll('#log-drawer-body .log-message'))
        .map(el => el.innerText)
        .join('\n');
    if (!messages) {
        showToast("目前沒有日誌內容可以複製。");
        return;
    }
    navigator.clipboard.writeText(messages).then(() => {
        showToast("已成功複製所有日誌至剪貼簿！");
    }).catch(err => {
        showToast("複製日誌失敗：" + err);
    });
}
window.copyAllLogs = copyAllLogs;

// Helpers
String.prototype.strip = function() {
    return this.replace(/^\s+|\s+$/g, '');
};

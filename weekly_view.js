let pyApi = null;
let tasks = [];
let currentWeekStart = new Date();
let projectColors = {};
let projectTitles = {};
let selectedTaskId = null;

// Configuration
const HOUR_HEIGHT = 60; // pixels per hour
const SNAP_MINUTES = 15;
const SNAP_PIXELS = (SNAP_MINUTES / 60) * HOUR_HEIGHT;
const MIN_TASK_HEIGHT = SNAP_PIXELS;

// State for drag/resize
let isDragging = false;
let isResizing = false;
let resizeEdge = null; // 'top' or 'bottom'
let draggedTask = null;
let dragStartX, dragStartY;
let taskOriginalTop, taskOriginalLeft;
let taskOriginalHeight;
let dragPlaceholder = null;
let ctrlPressed = false;
let activeCard = null;
let lastClickTime = 0;
let lastClickTaskId = null;
let lastMouseX = 0;
let lastMouseY = 0;
let pendingGridDate = null;
let pendingGridMinutes = null;
let dragMoved = false;

let currentWorkSettings = null;
let hasScrolledThisSession = false;
const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
let currentWeekStartStr = "";

function setWeekStart(dateStr) {
    if (currentWeekStartStr === dateStr) {
        refreshTasks();
        return;
    }
    currentWeekStartStr = dateStr;
    currentWeekStart = new Date(dateStr + 'T00:00:00');
    initCalendar();
    refreshTasks();

    if (!hasScrolledThisSession) {
        hasScrolledThisSession = true;
        setTimeout(() => {
            scrollTo730();
        }, 100);
    }
}
window.setWeekStart = setWeekStart;

document.addEventListener('DOMContentLoaded', () => {
    new QWebChannel(qt.webChannelTransport, (channel) => {
        pyApi = channel.objects.pyApi;
        pyApi.get_project_colors((colors) => {
            projectColors = colors || {};
            // Migration: Convert HSL to RGBA if any
            let migrated = false;
            for (let code in projectColors) {
                if (projectColors[code].startsWith('hsl')) {
                    const rgb = hslToRgb(projectColors[code]);
                    if (rgb) {
                        projectColors[code] = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 1)`;
                        pyApi.save_project_color(code, projectColors[code]);
                        migrated = true;
                    }
                }
            }
            pyApi.get_project_titles((titles) => {
                projectTitles = titles || {};
                initCalendar();
                refreshTasks();
            });
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Control') {
            ctrlPressed = true;
            if (isDragging) {
                if (activeCard) activeCard.style.opacity = '1';
                handleMouseMove({ clientX: lastMouseX, clientY: lastMouseY });
            }
        } else if (e.key === 'Escape') {
            if (isDragging || isResizing) {
                cleanupAfterAction();
            }
        }
    });
    document.addEventListener('keyup', (e) => {
        if (e.key === 'Control') {
            ctrlPressed = false;
            if (isDragging) {
                if (activeCard) activeCard.style.opacity = '0.5';
                handleMouseMove({ clientX: lastMouseX, clientY: lastMouseY });
            }
        }
    });

    // Task Popup Close on Outside Click
    document.addEventListener('mousedown', (e) => {
        const tPopup = document.getElementById('task-popup');
        const gPopup = document.getElementById('grid-popup');

        // If clicking outside both popups, hide them
        if (tPopup && tPopup.style.display !== 'none' && !tPopup.contains(e.target)) {
            hideTaskPopup();
        }
        if (gPopup && gPopup.style.display !== 'none' && !gPopup.contains(e.target)) {
            hideGridPopup();
        }
    });

    // Context menu handling (Right click)
    document.addEventListener('contextmenu', (e) => {
        const card = e.target.closest('.task-card');
        const col = e.target.closest('.task-column');

        if (card) {
            e.preventDefault();
            const taskId = parseInt(card.dataset.id);
            if (!isNaN(taskId)) {
                showTaskPopup(taskId, e.clientX, e.clientY);
            }
            return;
        } else if (col) {
            e.preventDefault();
            const rect = col.getBoundingClientRect();
            const y = e.clientY - rect.top;
            const minutes = Math.floor((y / HOUR_HEIGHT) * 60);
            const dateStr = col.dataset.date;
            if (dateStr && !isNaN(minutes) && isInsideWorkHours(dateStr, minutes)) {
                showGridPopup(dateStr, minutes, e.clientX, e.clientY);
            }
        } else {
            e.preventDefault();
        }
    });

    // Click handling (Left click)
    document.addEventListener('click', (e) => {
        const card = e.target.closest('.task-card');
        const col = e.target.closest('.task-column');
        const nav = e.target.closest('.nav-button');
        const tPopup = e.target.closest('.task-popup');
        const gPopup = e.target.closest('.grid-popup');

        if (nav || tPopup || gPopup) return;

        // Requirement: Suppress popups if we just finished a drag/resize
        if (dragMoved) return;

        if (card) {
            const taskId = parseInt(card.dataset.id);
            if (!isNaN(taskId)) {
                showTaskPopup(taskId, e.clientX, e.clientY);
            }
            return;
        }

        if (col) {
            const rect = col.getBoundingClientRect();
            const y = e.clientY - rect.top;
            const minutes = Math.floor((y / HOUR_HEIGHT) * 60);
            const dateStr = col.dataset.date;

            if (dateStr && !isNaN(minutes) && isInsideWorkHours(dateStr, minutes)) {
                showGridPopup(dateStr, minutes, e.clientX, e.clientY);
            }
        }
    });

    document.getElementById('grid-add-task').onclick = () => {
        if (pyApi && pendingGridDate && pendingGridMinutes !== null) {
            pyApi.add_task_at(pendingGridDate, pendingGridMinutes);
        }
        hideGridPopup();
    };

});

function updateNowIndicator() {
    const layer = document.getElementById('now-indicator-layer');
    if (!layer) return;
    layer.innerHTML = '';

    const now = new Date();
    const startOfWeek = new Date(currentWeekStart);
    startOfWeek.setHours(0, 0, 0, 0);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(endOfWeek.getDate() + 7);

    if (now < startOfWeek || now >= endOfWeek) return;

    const dayIndex = now.getDay();
    const minutes = now.getHours() * 60 + now.getMinutes();
    const top = (minutes / 60) * HOUR_HEIGHT;

    const bar = document.createElement('div');
    bar.className = 'now-indicator-line';
    bar.style.top = `${top}px`;
    bar.style.left = `calc(${(dayIndex / 7) * 100}%)`;
    bar.style.width = `calc(${100 / 7}%)`;

    const dot = document.createElement('div');
    dot.className = 'now-indicator-dot';
    bar.appendChild(dot);
    layer.appendChild(bar);
}

function deselectTask() {
    selectedTaskId = null;
    document.querySelectorAll('.task-card.selected').forEach(c => c.classList.remove('selected'));
}



function scrollTo730() {
    const body = document.getElementById('calendar-body');
    if (body) body.scrollTop = 450;
}

function initCalendar() {
    renderHeaders();
    renderTimeLabels();
    renderGrid();
}

function renderHeaders() {
    const headers = document.getElementById('day-headers');
    headers.innerHTML = '';
    const startOfWeek = new Date(currentWeekStart);
    const today = new Date();

    for (let i = 0; i < 7; i++) {
        const date = new Date(startOfWeek);
        date.setDate(date.getDate() + i);
        const isToday = date.toDateString() === today.toDateString();
        const dayHeader = document.createElement('div');
        dayHeader.className = `day-header ${isToday ? 'today' : ''}`;
        dayHeader.dataset.date = formatDateLocal(date);
        dayHeader.innerHTML = `
            <div class="day-name">${dayNames[i]}</div>
            <div class="day-date">${date.getDate()}</div>
        `;
        headers.appendChild(dayHeader);
    }
}

function renderTimeLabels() {
    const timeLabels = document.getElementById('time-labels');
    timeLabels.innerHTML = '';
    for (let i = 0; i < 24; i++) {
        const label = document.createElement('div');
        label.className = 'time-label';
        const hour = i === 0 ? '12 AM' : i < 12 ? `${i} AM` : i === 12 ? '12 PM' : `${i - 12} PM`;
        label.textContent = i === 0 ? '' : hour;
        timeLabels.appendChild(label);
    }
}

function renderGrid() {
    const gridLines = document.getElementById('grid-lines');
    gridLines.innerHTML = '';
    const rowsLayer = document.createElement('div');
    rowsLayer.className = 'grid-rows-layer';
    for (let i = 0; i < 24; i++) {
        const row = document.createElement('div');
        row.className = 'grid-row';
        rowsLayer.appendChild(row);
    }
    gridLines.appendChild(rowsLayer);

    const colsLayer = document.createElement('div');
    colsLayer.className = 'grid-cols-layer day-columns';
    const startOfWeek = new Date(currentWeekStart);
    for (let i = 0; i < 7; i++) {
        const date = new Date(startOfWeek);
        date.setDate(date.getDate() + i);
        const col = document.createElement('div');
        col.className = 'grid-column';
        col.dataset.date = formatDateLocal(date);
        colsLayer.appendChild(col);
    }
    gridLines.appendChild(colsLayer);
}

function refreshTasks() {
    const startOfWeek = new Date(currentWeekStart);
    const endDate = new Date(startOfWeek);
    endDate.setDate(endDate.getDate() + 6);

    pyApi.get_tasks(formatDateLocal(startOfWeek), formatDateLocal(endDate), (loadedTasks) => {
        tasks = loadedTasks;
        pyApi.get_project_titles((titles) => {
            projectTitles = titles || {};
            renderTasks();
            updateNowIndicator();
        });

        pyApi.get_work_settings(formatDateLocal(startOfWeek), formatDateLocal(endDate), (settings) => {
            try {
                currentWorkSettings = JSON.parse(settings);
                renderWorkIndicators();
            } catch (e) {
                console.error("Failed to parse work settings:", e);
                currentWorkSettings = {};
                renderWorkIndicators();
            }
        });
    });
}

function timeToMinutes(timeStr) {
    if (!timeStr) return 0;
    const [h, m] = timeStr.split(':').map(Number);
    return h * 60 + m;
}

function renderWorkIndicators() {
    const layer = document.getElementById('work-indicators-layer');
    if (!layer || !currentWorkSettings) return;
    layer.innerHTML = '';

    const startOfWeek = new Date(currentWeekStart);
    for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
        const col = document.createElement('div');
        col.className = 'indicator-column';
        layer.appendChild(col);

        const date = new Date(startOfWeek);
        date.setDate(date.getDate() + dayIndex);
        const dateStr = formatDateLocal(date);
        const settings = currentWorkSettings[dateStr];

        // If hours is 0, show disabled overlay for full day
        const isDisabled = settings && settings.hours === 0;

        if (isDisabled) {
            const overlay = document.createElement('div');
            overlay.className = 'disabled-day-overlay';
            overlay.style.top = '0px';
            overlay.style.height = '1440px';
            col.appendChild(overlay);
            continue;
        }

        if (!settings) continue;

        const startMin = timeToMinutes(settings.start);
        const lunchStartMin = timeToMinutes(settings.lunch_start);
        const lunchEndMin = timeToMinutes(settings.lunch_end);
        const workHours = settings.hours;

        const lunchDuration = Math.max(0, lunchEndMin - lunchStartMin);
        const endMin = startMin + lunchDuration + (workHours * 60);

        const startTop = (startMin / 60) * HOUR_HEIGHT;
        const endTop = (endMin / 60) * HOUR_HEIGHT;
        const lunchTop = (lunchStartMin / 60) * HOUR_HEIGHT;
        const lunchHeight = (lunchDuration / 60) * HOUR_HEIGHT;

        // --- Hatching for non-work times ---
        if (startTop > 0) {
            const topOverlay = document.createElement('div');
            topOverlay.className = 'disabled-day-overlay';
            topOverlay.style.top = '0px';
            topOverlay.style.height = `${startTop}px`;
            col.appendChild(topOverlay);
        }
        if (endTop < 1440) {
            const bottomOverlay = document.createElement('div');
            bottomOverlay.className = 'disabled-day-overlay';
            bottomOverlay.style.top = `${endTop}px`;
            bottomOverlay.style.height = `${1440 - endTop}px`;
            col.appendChild(bottomOverlay);
        }

        const startLine = document.createElement('div');
        startLine.className = 'work-boundary-line';
        startLine.style.top = `${startTop}px`;
        col.appendChild(startLine);

        const endLine = document.createElement('div');
        endLine.className = 'work-boundary-line';
        endLine.style.top = `${endTop}px`;
        col.appendChild(endLine);

        if (lunchHeight > 0) {
            const lunchArea = document.createElement('div');
            lunchArea.className = 'lunch-break-area';
            lunchArea.style.top = `${lunchTop}px`;
            lunchArea.style.height = `${lunchHeight}px`;
            lunchArea.textContent = 'Lunch Time';
            col.appendChild(lunchArea);
        }
    }
}

function renderTasks() {
    const container = document.getElementById('tasks-container');
    container.innerHTML = '';
    for (let i = 0; i < 7; i++) {
        const col = document.createElement('div');
        col.className = 'task-column';
        col.id = `day-column-${i}`;

        // Match date with day-header
        const dayHeader = document.querySelector(`.day-header:nth-child(${i + 1})`);
        if (dayHeader) {
            col.dataset.date = dayHeader.dataset.date;
        }

        container.appendChild(col);
    }

    const startOfWeek = new Date(currentWeekStart);
    startOfWeek.setHours(0, 0, 0, 0);

    tasks.forEach(task => {
        if (!task || !task.task_date) return;
        const taskDate = new Date(task.task_date + 'T00:00:00');
        const dayDiff = Math.floor((taskDate - startOfWeek) / (1000 * 60 * 60 * 24));
        if (dayDiff >= 0 && dayDiff < 7) {
            const card = createTaskCard(task, dayDiff);
            const targetCol = document.getElementById(`day-column-${dayDiff}`);
            if (targetCol) targetCol.appendChild(card);
        }
    });
}

function createTaskCard(task, dayIndex) {
    const startTimeParts = task.start_time.split(':');
    const endTimeParts = task.end_time.split(':');
    const startMinutes = parseInt(startTimeParts[0]) * 60 + parseInt(startTimeParts[1]);
    const endMinutes = parseInt(endTimeParts[0]) * 60 + parseInt(endTimeParts[1]);
    const durationMinutes = endMinutes - startMinutes;
    const top = (startMinutes / 60) * HOUR_HEIGHT;
    const height = (durationMinutes / 60) * HOUR_HEIGHT;

    const card = document.createElement('div');
    card.className = 'task-card';
    if (selectedTaskId === task.id) card.classList.add('selected');
    card.style.top = `${top}px`;
    card.style.height = `${height}px`;
    card.dataset.id = task.id;

    if (task.project_code) {
        if (!projectColors[task.project_code]) {
            projectColors[task.project_code] = generateRandomColor();
            pyApi.save_project_color(task.project_code, projectColors[task.project_code]);
        }
        const bgColor = projectColors[task.project_code];
        const textColor = getContrastColor(bgColor);
        card.style.backgroundColor = bgColor;
        card.style.color = textColor;
        card.style.setProperty('--contrast-color', textColor);
    }

    const projectTitle = projectTitles[task.project_code] || '';

    let displayDesc = '';
    if (task.description && task.description.trim()) {
        if (task.description.includes('<html')) {
            const doc = new DOMParser().parseFromString(task.description, 'text/html');
            displayDesc = doc.body.innerHTML;
        } else {
            displayDesc = task.description.trim().replace(/\n/g, '<br>');
        }
    }

    card.innerHTML = `
        <div class="resize-handle-top"></div>
        <div class="task-project">${task.project_code || 'No Project'}</div>
        ${projectTitle ? `<div class="task-title" title="${projectTitle}">${projectTitle}</div>` : ''}
        <div class="task-time">${task.start_time.substring(0, 5)} - ${task.end_time.substring(0, 5)}</div>
        <div class="task-desc">${displayDesc}</div>
        <div class="resize-handle-bottom"></div>
    `;

    const observer = new ResizeObserver(entries => {
        for (let entry of entries) {
            adjustVisibilityBasedOnHeight(entry.target);
        }
    });
    observer.observe(card);

    card.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        if (selectedTaskId !== task.id) {
            deselectTask();
            selectedTaskId = task.id;
            card.classList.add('selected');
        }
        handleMouseDown(e, task, card);
    });

    card.querySelector('.resize-handle-top').addEventListener('mousedown', (e) => {
        e.stopPropagation();
        handleResizeStart(e, task, card, 'top');
    });

    card.querySelector('.resize-handle-bottom').addEventListener('mousedown', (e) => {
        e.stopPropagation();
        handleResizeStart(e, task, card, 'bottom');
    });

    return card;
}

function generateRandomColor() {
    let bestColor = null;
    let maxContrast = 0;

    for (let i = 0; i < 20; i++) {
        const hue = Math.floor(Math.random() * 360);
        const saturation = 50 + Math.floor(Math.random() * 30);
        const lightness = 25 + Math.floor(Math.random() * 25);
        const hsl = `hsl(${hue}, ${saturation}%, ${lightness}%)`;

        const rgb = hslToRgb(hsl);
        if (!rgb) continue;
        const L = getRelativeLuminance(rgb.r, rgb.g, rgb.b);
        const contrastWithWhite = 1.05 / (L + 0.05); // L of white is 1.0

        const rgba = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 1)`;
        if (contrastWithWhite >= 5.0) return rgba;

        if (contrastWithWhite > maxContrast) {
            maxContrast = contrastWithWhite;
            bestColor = rgba;
        }
    }
    return bestColor || `rgba(64, 64, 64, 1)`;
}

function getContrastColor(bgColor) {
    if (!bgColor) return '#ffffff';

    const rgb = colorToRgb(bgColor);
    if (!rgb) return '#ffffff';

    const L = getRelativeLuminance(rgb.r, rgb.g, rgb.b);

    // WCAG contrast ratio formula: (L1 + 0.05) / (L2 + 0.05)
    // L for white is 1.0, L for black is 0.0
    const contrastWithWhite = (1.0 + 0.05) / (L + 0.05);
    const contrastWithBlack = (L + 0.05) / (0.0 + 0.05);

    // Target 5:1 contrast
    if (contrastWithWhite >= 5) return '#ffffff';
    if (contrastWithBlack >= 5) return '#1a1c1e';

    // If neither meets 5:1, pick the one with higher contrast
    return contrastWithWhite > contrastWithBlack ? '#ffffff' : '#1a1c1e';
}

function getRelativeLuminance(r, g, b) {
    const a = [r, g, b].map(v => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
}

function colorToRgb(colorStr) {
    if (colorStr.startsWith('rgba')) return rgbaToRgb(colorStr);
    if (colorStr.startsWith('hsl')) return hslToRgb(colorStr);
    return null;
}

function rgbaToRgb(rgba) {
    const match = rgba.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d\.]+)\)/);
    if (!match) return null;
    return {
        r: parseInt(match[1]),
        g: parseInt(match[2]),
        b: parseInt(match[3]),
        a: parseFloat(match[4])
    };
}

function hslToRgb(hsl) {
    const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
    if (!match) return null;
    let h = parseInt(match[1]) / 360;
    let s = parseInt(match[2]) / 100;
    let l = parseInt(match[3]) / 100;
    let r, g, b;
    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }
    return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
}

function stripHtml(html) {
    let tmp = document.createElement("DIV");
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || "";
}

function handleMouseDown(e, task, card) {
    if (e.button !== 0) return;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
    hideTaskPopup();
    hideGridPopup();
    isDragging = true;
    draggedTask = task;
    dragMoved = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    taskOriginalTop = card.offsetTop;
    taskOriginalLeft = card.offsetLeft;
    activeCard = card;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

function handleResizeStart(e, task, card, edge) {
    hideTaskPopup();
    hideGridPopup();
    isResizing = true;
    resizeEdge = edge;
    draggedTask = task;
    dragStartX = e.clientX; // Ensure we have a start point for threshold
    dragStartY = e.clientY;
    taskOriginalHeight = card.offsetHeight;
    taskOriginalTop = card.offsetTop;
    activeCard = card;
    dragMoved = false;
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
}


const DRAG_THRESHOLD = 5;

function handleMouseMove(e) {
    if (!isDragging || !draggedTask) return;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
    const taskId = draggedTask.id;

    const deltaX = e.clientX - dragStartX;
    const deltaY = e.clientY - dragStartY;

    if (!dragMoved && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
        dragMoved = true;
        // Activation: Only now do we treat it as a drag
        document.body.classList.add('is-dragging');
        if (activeCard) {
            activeCard.style.opacity = ctrlPressed ? '1' : '0.5';
            createPlaceholder(activeCard);
        }
    }
    if (!dragMoved) return;

    // Update opacity based on copy mode
    if (activeCard) {
        activeCard.style.opacity = ctrlPressed ? '1' : '0.5';
    }

    const gridRect = document.getElementById('grid-container').getBoundingClientRect();
    const colWidth = gridRect.width / 7;
    const relativeX = e.clientX - gridRect.left;
    let currentTargetDayIndex = Math.floor(relativeX / colWidth);
    currentTargetDayIndex = Math.max(0, Math.min(6, currentTargetDayIndex));

    let newTop = taskOriginalTop + deltaY;
    newTop = Math.round(newTop / SNAP_PIXELS) * SNAP_PIXELS;
    const placeholderHeight = dragPlaceholder.offsetHeight;

    // Remove clamping to work hours, only clamp to day boundaries
    newTop = Math.max(0, Math.min(1440 - placeholderHeight, newTop));

    if (currentWorkSettings && taskId) {
        if (isPositionValid(currentTargetDayIndex, newTop, placeholderHeight, taskId)) {
            document.body.style.cursor = 'default';
        } else {
            document.body.style.cursor = 'not-allowed';
        }
    }

    // Handle Copy Tooltip
    let tooltip = document.getElementById('copy-tooltip');
    if (ctrlPressed && dragMoved) {
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'copy-tooltip';
            tooltip.textContent = 'Copy';
            document.body.appendChild(tooltip);
        }
        tooltip.style.left = `${e.clientX + 15}px`;
        tooltip.style.top = `${e.clientY + 15}px`;
    } else if (tooltip) {
        tooltip.remove();
    }

    dragPlaceholder.style.top = `${newTop}px`;
    dragPlaceholder.style.left = `calc(${(currentTargetDayIndex / 7) * 100}% + 2px)`;
    dragPlaceholder.style.width = `calc(${100 / 7}% - 4px)`;
    updatePlaceholderTime(newTop, placeholderHeight);
}

function handleMouseUp(e) {
    if (!isDragging) return;
    if (dragMoved) {
        const finalTop = parseFloat(dragPlaceholder.style.top);
        const gridRect = document.getElementById('grid-container').getBoundingClientRect();
        const colWidth = gridRect.width / 7;
        const relativeX = e.clientX - gridRect.left;
        let targetDayIndex = Math.floor(relativeX / colWidth);
        targetDayIndex = Math.max(0, Math.min(6, targetDayIndex));

        if (!dragPlaceholder || !draggedTask) return;
        if (!isPositionValid(targetDayIndex, finalTop, dragPlaceholder.offsetHeight, draggedTask.id)) {
            cleanupAfterAction();
            return;
        }

        const startMinutes = (finalTop / HOUR_HEIGHT) * 60;
        const durationMinutes = (dragPlaceholder.offsetHeight / HOUR_HEIGHT) * 60;
        const startHour = Math.floor(startMinutes / 60);
        const startMin = Math.round(startMinutes % 60);
        const endHourTotal = Math.floor((startMinutes + durationMinutes) / 60);
        const endMin = Math.round((startMinutes + durationMinutes) % 60);

        const startTimeStr = `${startHour.toString().padStart(2, '0')}:${startMin.toString().padStart(2, '0')}:00`;
        const endTimeStr = `${endHourTotal.toString().padStart(2, '0')}:${endMin.toString().padStart(2, '0')}:00`;

        const startOfWeek = new Date(currentWeekStart);
        const targetDate = new Date(startOfWeek);
        targetDate.setHours(0, 0, 0, 0);
        targetDate.setDate(targetDate.getDate() + targetDayIndex);
        const dateStr = formatDateLocal(targetDate);

        if (dateStr) {
            const taskId = draggedTask.id;
            const resolved = resolveLunchOverlap(dateStr, startMinutes, startMinutes + durationMinutes);
            if (resolved.length === 0) {
                cleanupAfterAction();
                return;
            }

            const segments = resolved.map(seg => ({
                start: minutesToTimeStr(seg.start),
                end: minutesToTimeStr(seg.end)
            }));

            if (ctrlPressed) {
                segments.forEach(seg => {
                    pyApi.duplicate_task(taskId, dateStr, seg.start, seg.end);
                });
                refreshTasks();
            } else {
                pyApi.update_task_multi(taskId, dateStr, JSON.stringify(segments), () => refreshTasks());
            }
        }
    }
    cleanupAfterAction();
}


function handleResizeMove(e) {
    if (!isResizing || !draggedTask) return;
    const deltaY = e.clientY - dragStartY;

    if (!dragMoved && Math.abs(deltaY) > DRAG_THRESHOLD) {
        dragMoved = true;
        document.body.classList.add('is-resizing');
        document.body.style.cursor = 'ns-resize';
        if (activeCard) {
            activeCard.style.opacity = '0.5';
            createPlaceholder(activeCard);
        }
    }
    if (!dragMoved || !dragPlaceholder) return;

    const taskId = draggedTask.id;
    const dateStr = draggedTask.task_date;

    if (resizeEdge === 'bottom') {
        let newHeight = taskOriginalHeight + deltaY;
        newHeight = Math.round(newHeight / SNAP_PIXELS) * SNAP_PIXELS;
        newHeight = Math.max(SNAP_PIXELS, newHeight);

        if (currentWorkSettings) {
            const settings = currentWorkSettings[dateStr];
            if (settings) {
                const startMin = timeToMinutes(settings.start);
                const lunchStartMin = timeToMinutes(settings.lunch_start);
                const lunchEndMin = timeToMinutes(settings.lunch_end);
                const lunchDuration = Math.max(0, lunchEndMin - lunchStartMin);
                const endMin = startMin + lunchDuration + (settings.hours * 60);

                const maxBottom = (endMin / 60) * HOUR_HEIGHT;
                if (taskOriginalTop + newHeight > maxBottom) {
                    newHeight = maxBottom - taskOriginalTop;
                }
            }
        }
        dragPlaceholder.style.height = `${newHeight}px`;
        updatePlaceholderTime(taskOriginalTop, newHeight);
    } else {
        let newTop = taskOriginalTop + deltaY;
        newTop = Math.round(newTop / SNAP_PIXELS) * SNAP_PIXELS;
        let newHeight = (taskOriginalTop + taskOriginalHeight) - newTop;

        if (newHeight < MIN_TASK_HEIGHT) {
            newHeight = MIN_TASK_HEIGHT;
            newTop = (taskOriginalTop + taskOriginalHeight) - MIN_TASK_HEIGHT;
        }

        if (currentWorkSettings) {
            const settings = currentWorkSettings[dateStr];
            if (settings) {
                const minTop = (timeToMinutes(settings.start) / 60) * HOUR_HEIGHT;
                if (newTop < minTop) {
                    newTop = minTop;
                    newHeight = (taskOriginalTop + taskOriginalHeight) - minTop;
                }
            }
        }
        dragPlaceholder.style.top = `${newTop}px`;
        dragPlaceholder.style.height = `${newHeight}px`;
        updatePlaceholderTime(newTop, newHeight);
    }

    // Dynamic cursor for resize
    const startOfWeek = new Date(currentWeekStart);
    const taskDate = new Date(dateStr + 'T00:00:00');
    const dayIndex = Math.floor((taskDate - startOfWeek) / (1000 * 60 * 60 * 24));

    if (isPositionValid(dayIndex, parseFloat(dragPlaceholder.style.top), parseFloat(dragPlaceholder.style.height), taskId)) {
        document.body.style.cursor = 'ns-resize';
    } else {
        document.body.style.cursor = 'not-allowed';
    }
}

function handleResizeEnd(e) {
    if (!isResizing) return;
    const finalTop = parseFloat(dragPlaceholder.style.top);
    const finalHeight = parseFloat(dragPlaceholder.style.height);

    if (!draggedTask || !dragPlaceholder) return;
    const taskDate = new Date(draggedTask.task_date + 'T00:00:00');
    const startOfWeek = new Date(currentWeekStart);
    const dayIndex = Math.floor((taskDate - startOfWeek) / (1000 * 60 * 60 * 24));

    if (!isPositionValid(dayIndex, finalTop, finalHeight, draggedTask.id)) {
        cleanupAfterAction();
        return;
    }

    const startMinutes = (finalTop / HOUR_HEIGHT) * 60;
    const durationMinutes = (finalHeight / HOUR_HEIGHT) * 60;
    const dateStr = draggedTask.task_date;
    const taskId = draggedTask.id;

    const resolved = resolveLunchOverlap(dateStr, startMinutes, startMinutes + durationMinutes);
    if (resolved.length === 0) {
        cleanupAfterAction();
        return;
    }

    const segments = resolved.map(seg => ({
        start: minutesToTimeStr(seg.start),
        end: minutesToTimeStr(seg.end)
    }));

    pyApi.update_task_multi(taskId, dateStr, JSON.stringify(segments), () => refreshTasks());
    cleanupAfterAction();
}

function isPositionValid(dayIndex, top, height, excludeTaskId) {
    const startOfWeek = new Date(currentWeekStart);
    const targetDate = new Date(startOfWeek);
    targetDate.setDate(targetDate.getDate() + dayIndex);
    const settings = currentWorkSettings[formatDateLocal(targetDate)];

    if (!settings || settings.hours === 0) return false;

    const startMin = timeToMinutes(settings.start);
    const lunchStartMin = timeToMinutes(settings.lunch_start);
    const lunchEndMin = timeToMinutes(settings.lunch_end);
    const lunchDuration = Math.max(0, lunchEndMin - lunchStartMin);
    const endMin = startMin + lunchDuration + (settings.hours * 60);

    const startTop = (startMin / 60) * HOUR_HEIGHT;
    const endTop = (endMin / 60) * HOUR_HEIGHT;

    // Check if task is within [startTop, endTop]
    // Tolerance of 0.1px for rounding
    if (top < startTop - 0.1 || (top + height) > endTop + 0.1) return false;

    // Task collision check
    const startOfWeekFull = new Date(currentWeekStart);
    startOfWeekFull.setHours(0, 0, 0, 0);

    for (const task of tasks) {
        if (!task || !task.task_date) continue;

        // Skip the task itself UNLESS we are specifically copying during a drag
        const isCopying = isDragging && ctrlPressed;
        if (!isCopying && task.id === excludeTaskId) continue;

        const taskDate = new Date(task.task_date + 'T00:00:00');
        const taskDayIndex = Math.floor((taskDate - startOfWeekFull) / (1000 * 60 * 60 * 24));

        if (taskDayIndex === dayIndex) {
            const tStartMin = timeToMinutes(task.start_time);
            const tEndMin = timeToMinutes(task.end_time);
            const tTop = (tStartMin / 60) * HOUR_HEIGHT;
            const tHeight = ((tEndMin - tStartMin) / 60) * HOUR_HEIGHT;

            // Overlap check
            if (top < tTop + tHeight - 0.1 && top + height > tTop + 0.1) {
                return false;
            }
        }
    }

    return true;
}

function createPlaceholder(card) {
    dragPlaceholder = document.createElement('div');
    dragPlaceholder.className = 'drag-placeholder';
    dragPlaceholder.style.top = `${card.offsetTop}px`;
    const col = card.parentElement;
    const container = document.getElementById('tasks-container');
    const dayIndex = Array.from(container.children).indexOf(col);
    dragPlaceholder.style.left = `calc(${(dayIndex / 7) * 100}% + 2px)`;
    dragPlaceholder.style.width = `calc(${100 / 7}% - 4px)`;
    dragPlaceholder.style.height = `${card.offsetHeight}px`;

    // Copy style from original card
    dragPlaceholder.style.backgroundColor = card.style.backgroundColor;
    dragPlaceholder.style.color = card.style.color;

    // Show all info in the preview
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = card.innerHTML;
    // Reset visibility logic for the preview content
    tempDiv.querySelectorAll('.task-title, .task-time, .task-desc').forEach(el => el.style.display = '');
    dragPlaceholder.innerHTML = tempDiv.innerHTML;
    dragPlaceholder.classList.add('dragging-preview');

    // Initial visibility check
    adjustVisibilityBasedOnHeight(dragPlaceholder);

    container.appendChild(dragPlaceholder);
}

function updatePlaceholderTime(top, height) {
    if (!dragPlaceholder) return;

    // Update Visibility
    adjustVisibilityBasedOnHeight(dragPlaceholder);

    const timeEl = dragPlaceholder.querySelector('.task-time');
    if (!timeEl) return;

    const startMinutes = (top / HOUR_HEIGHT) * 60;
    const endMinutes = ((top + height) / HOUR_HEIGHT) * 60;

    // Formatting match: HH:mm - HH:mm
    const startStr = minutesToTimeStr(startMinutes).substring(0, 5);
    const endStr = minutesToTimeStr(endMinutes).substring(0, 5);

    timeEl.textContent = `${startStr} - ${endStr}`;
}

function adjustVisibilityBasedOnHeight(element) {
    const h = element.offsetHeight || parseFloat(element.style.height) || 0;
    const title = element.querySelector('.task-title');
    const time = element.querySelector('.task-time');
    const desc = element.querySelector('.task-desc');

    // Reset visibility
    if (title) title.style.display = '';
    if (time) time.style.display = '';
    if (desc) desc.style.display = '';

    // Priority: Code > Desc > Time > Title
    // Base padding/margin/project code height ~ 22px
    const baseH = 26; // Added 4px buffer
    const titleH = title ? 15 : 0;
    const timeH = time ? 18 : 0;
    const descMinH = 15; // Represents one line

    // Hide Title first
    if (h < baseH + descMinH + timeH + titleH) {
        if (title) title.style.display = 'none';
    }
    // Hide Time second
    if (h < baseH + descMinH + timeH) {
        if (time) time.style.display = 'none';
    }
    // Hide Desc third
    if (h < baseH + descMinH) {
        if (desc) desc.style.display = 'none';
    }

    // Line clamping for description to avoid partial lines
    if (desc && desc.style.display !== 'none') {
        const remainingH = h - baseH - (time && time.style.display !== 'none' ? timeH : 0) - (title && title.style.display !== 'none' ? titleH : 0);
        const lines = Math.floor(remainingH / 13); // Roughly 13px per line
        if (lines > 0) {
            desc.style.webkitLineClamp = lines;
            desc.style.display = '-webkit-box';
        } else {
            desc.style.display = 'none';
        }
    }
}

function cleanupAfterAction() {
    isDragging = false;
    isResizing = false;
    document.body.style.cursor = '';
    document.body.classList.remove('is-dragging', 'is-resizing');
    if (dragPlaceholder) dragPlaceholder.remove();
    if (activeCard) activeCard.style.opacity = '1';
    activeCard = null;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.removeEventListener('mouseup', handleResizeEnd);

    // Explicitly remove copy tooltip if it exists
    const tooltip = document.getElementById('copy-tooltip');
    if (tooltip) tooltip.remove();

    // Use a small timeout for state reset so the 'click' event (which fires after mouseup)
    // can still see that a drag happened.
    setTimeout(() => {
        dragMoved = false;
        draggedTask = null;
    }, 50);
}


function formatDateLocal(date) {
    if (!date || isNaN(date.getTime())) return null;
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function minutesToTimeStr(minutes) {
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:00`;
}

function resolveLunchOverlap(dateStr, startMin, endMin) {
    const settings = currentWorkSettings[dateStr];
    if (!settings) return [{ start: startMin, end: endMin }];

    const lunchStartMin = timeToMinutes(settings.lunch_start);
    const lunchEndMin = timeToMinutes(settings.lunch_end);

    if (lunchEndMin <= lunchStartMin) return [{ start: startMin, end: endMin }];

    const epsilon = 0.1;

    // Case 1: No overlap
    if (endMin <= lunchStartMin + epsilon || startMin >= lunchEndMin - epsilon) {
        return [{ start: startMin, end: endMin }];
    }

    // Case 2: Spans across lunch
    if (startMin < lunchStartMin - epsilon && endMin > lunchEndMin + epsilon) {
        return [
            { start: startMin, end: lunchStartMin },
            { start: lunchEndMin, end: endMin }
        ];
    }

    // Case 3: Ends during lunch (but starts before)
    if (startMin < lunchStartMin - epsilon && endMin > lunchStartMin + epsilon) {
        return [{ start: startMin, end: lunchStartMin }];
    }

    // Case 4: Starts during lunch (but ends after)
    if (startMin < lunchEndMin - epsilon && endMin > lunchEndMin + epsilon) {
        return [{ start: lunchEndMin, end: endMin }];
    }

    // Case 5: Entirely within lunch
    return [];
}

function showTaskPopup(taskId, x, y) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    const popup = document.getElementById('task-popup');
    const projectName = document.getElementById('popup-project-name');
    const dateEl = document.getElementById('popup-date');
    const timeEl = document.getElementById('popup-time');
    const descEl = document.getElementById('popup-desc');

    // Populate data
    projectName.textContent = task.project_code || 'No Project';
    const projColor = projectColors[task.project_code] || '#4285f4';

    // Set popup border color
    popup.style.borderColor = projColor;

    if (task.description && task.description.trim()) {
        descEl.style.display = 'block';
        if (task.description.includes('<html')) {
            // Qt Rich Text: parse document and extract body content directly
            const doc = new DOMParser().parseFromString(task.description, 'text/html');
            descEl.innerHTML = doc.body.innerHTML;
        } else {
            // Plain text: preserve newlines
            descEl.innerHTML = task.description.trim().replace(/\n/g, '<br>');
        }
    } else {
        descEl.style.display = 'none';
        descEl.innerHTML = '';
    }

    // Format Date: "Tuesday, 24 February"
    const dateObj = new Date(task.task_date + 'T00:00:00');
    const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
    const dayNum = dateObj.getDate();
    const monthName = dateObj.toLocaleDateString('en-US', { month: 'long' });
    dateEl.textContent = `${dayName}, ${dayNum} ${monthName}`;

    // Format Time: "12:00 - 2:30pm"
    timeEl.textContent = `${task.start_time.substring(0, 5)} - ${formatTaskTime(task.end_time)}`;

    // Show popup to get its dimensions
    popup.style.display = 'flex';
    popup.style.visibility = 'hidden';

    // Positioning
    requestAnimationFrame(() => {
        const rect = popup.getBoundingClientRect();
        // Offset slightly so the mouse cursor doesn't block interactions or intercept double-clicks
        let finalX = x + 15;
        let finalY = y + 15;

        // Ensure popup stays inside the window
        if (finalX + rect.width > window.innerWidth) finalX = window.innerWidth - rect.width - 20;
        if (finalY + rect.height > window.innerHeight) finalY = window.innerHeight - rect.height - 20;
        if (finalX < 20) finalX = 20;
        if (finalY < 20) finalY = 20;

        popup.style.left = `${finalX}px`;
        popup.style.top = `${finalY}px`;
        popup.style.visibility = 'visible';
    });

    // Action listeners
    document.getElementById('popup-edit').onclick = () => {
        hideTaskPopup();
        pyApi.edit_task_dialog(taskId);
    };
    document.getElementById('popup-delete').onclick = () => {
        hideTaskPopup();
        pyApi.delete_task_dialog(taskId);
    };
    document.getElementById('popup-close').onclick = hideTaskPopup;

    // Select the task visually
    deselectTask();
    selectedTaskId = taskId;
    const card = document.querySelector(`.task-card[data-id="${taskId}"]`);
    if (card) card.classList.add('selected');
}

function hideTaskPopup() {
    const popup = document.getElementById('task-popup');
    if (popup) popup.style.display = 'none';
}

function showGridPopup(dateStr, minutes, x, y) {
    hideTaskPopup();
    const popup = document.getElementById('grid-popup');
    pendingGridDate = dateStr;
    pendingGridMinutes = minutes;

    popup.style.display = 'block';
    popup.style.visibility = 'hidden';

    requestAnimationFrame(() => {
        const rect = popup.getBoundingClientRect();
        let finalX = x;
        let finalY = y;

        if (finalX + rect.width > window.innerWidth) finalX = window.innerWidth - rect.width - 10;
        if (finalY + rect.height > window.innerHeight) finalY = window.innerHeight - rect.height - 10;

        popup.style.left = `${finalX}px`;
        popup.style.top = `${finalY}px`;
        popup.style.visibility = 'visible';
    });
}

function hideGridPopup() {
    const popup = document.getElementById('grid-popup');
    if (popup) popup.style.display = 'none';
    pendingGridDate = null;
    pendingGridMinutes = null;
}

function formatTaskTime(timeStr) {
    const parts = timeStr.split(':');
    let h = parseInt(parts[0]);
    const m = parts[1];
    const ampm = h >= 12 ? 'pm' : 'am';
    h = h % 12;
    h = h ? h : 12; // the hour '0' should be '12'
    return `${h}:${m}${ampm}`;
}

function isInsideWorkHours(dateStr, minutes) {
    if (!currentWorkSettings || !currentWorkSettings[dateStr]) return false;
    const settings = currentWorkSettings[dateStr];

    if (!settings.start || settings.hours === undefined) return false;

    const startMins = timeToMinutes(settings.start);
    const lunchStartMins = timeToMinutes(settings.lunch_start);
    const lunchEndMins = timeToMinutes(settings.lunch_end);
    const lunchDuration = Math.max(0, lunchEndMins - lunchStartMins);
    const endMins = startMins + lunchDuration + (settings.hours * 60);

    // Within workday?
    if (minutes < startMins || minutes >= endMins) return false;

    // Not during lunch?
    if (minutes >= lunchStartMins && minutes < lunchEndMins) return false;

    return true;
}

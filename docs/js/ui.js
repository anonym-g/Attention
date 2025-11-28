// docs/js/ui.js

import { state, saveSettings } from './state.js';
import { loadData } from './data_loader.js';
import { loop, renderCurrentState } from './render.js';
import { LANG_TITLES, CONFIG } from './constants.js';

export function updateLayoutMetrics() {
    const container = document.getElementById('chart-container');
    if (!container) return;

    // 1. 获取容器高度
    state.chartHeight = container.clientHeight;

    // 2. 计算整数行高
    state.rowHeight = Math.floor(state.chartHeight / CONFIG.barCount);

    // 3. 调整 GitHub 图标位置和大小
    const githubLink = document.getElementById('github-link');
    if (githubLink) {
        // 基于 CSS height: 81% 计算像素高度
        const barHeight = Math.max(1, state.rowHeight * 0.81);

        githubLink.style.width = `${barHeight}px`;
        githubLink.style.height = `${barHeight}px`;

        // 中心点与第 10 个条目的中心线对齐
        const rect = container.getBoundingClientRect();

        // 第 10 个条目是 index 9
        const targetRowIndex = 9;

        // 容器 Top + (9.5 * 行高)
        const rowCenterY = rect.top + (targetRowIndex * state.rowHeight) + (state.rowHeight / 2);

        // 计算 CSS bottom: 视口高度 - (中心线 + 半个图标高)
        const iconBottomEdgeY = rowCenterY + (barHeight / 2);
        githubLink.style.bottom = `${window.innerHeight - iconBottomEdgeY}px`;

        githubLink.style.right = '25px';
    }
}

export function updateTitle() {
    const titleEl = document.getElementById('chart-title');
    if(titleEl) titleEl.innerText = LANG_TITLES[state.lang] || 'Wikipedia Top 10';
}

export function setupControls() {
    const container = document.getElementById('chart-container');
    if (container) {
        const resizeObserver = new ResizeObserver(() => {
            updateLayoutMetrics();
            // 如果处于暂停或捕捉模式，尺寸变化后需要重绘一帧以应用新高度
            if (!state.isPlaying || state.mode === 'capture') {
                renderCurrentState(0);
            }
        });
        resizeObserver.observe(container);
    }

    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.onchange = (e) => {
        state.lang = e.target.value;
        saveSettings();
        loadData(e.target.value);
    };

    const btnPlay = document.getElementById('btn-play');
    if (btnPlay) btnPlay.onclick = () => {
        state.isPlaying = !state.isPlaying;
        btnPlay.innerText = state.isPlaying ? "Pause" : "Play";
        if (state.isPlaying) {
            state.lastFrameTime = performance.now();
            loop(state.lastFrameTime);
        }
    };

    const rangeSpeed = document.getElementById('speed-range');
    if (rangeSpeed) {
        rangeSpeed.value = state.playbackSpeed;
        const valEl = document.getElementById('speed-val');
        if(valEl) valEl.innerText = state.playbackSpeed + "x";

        rangeSpeed.oninput = (e) => {
            state.playbackSpeed = parseFloat(e.target.value);
            if(valEl) valEl.innerText = state.playbackSpeed + "x";
            saveSettings();
        };
    }

    const chkLog = document.getElementById('chk-log');
    if (chkLog) {
        chkLog.checked = state.isLogScale;
        chkLog.onchange = (e) => {
            state.isLogScale = e.target.checked;
            saveSettings();
            renderCurrentState(0.016);
        };
    }
}

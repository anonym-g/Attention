// docs/js/app.js

import { state } from './state.js';
import { CONFIG } from './constants.js';
import { loadData } from './data_loader.js';
import { updateLayoutMetrics, setupControls } from './ui.js';
import { advanceSimulation } from './render.js';

window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    state.lang = params.get('lang') || state.lang;
    state.paramDate = params.get('date');
    state.paramPrevDate = params.get('prev_date');

    if (params.get('mode') === 'capture') {
        document.body.classList.add('capture-mode');
        state.mode = 'capture';
        state.isPlaying = false;
        state.isLogScale = true;
    }

    updateLayoutMetrics();
    window.addEventListener('resize', updateLayoutMetrics);
    setupControls();
    loadData(state.lang, state.paramDate);
});

// --- 提供给 Playwright 的自动化接口 ---

/**
 * 根据录制起始帧和预渲染帧数，静默模拟动画以建立正确的初始状态。
 */
window.initializeToFrame = (recordingStartFrame, preRollFrames) => {
    const simulationStartFrame = recordingStartFrame - preRollFrames;
    const simulationStartMinute = simulationStartFrame;

    state.bars = {};
    document.getElementById('chart-container').innerHTML = '';

    let initialDateIndex = state.data.dates.indexOf(state.paramDate);
    let framesToSimulate = recordingStartFrame - simulationStartFrame;

    if (simulationStartMinute < 0) {
        const prevDateIndex = state.data.dates.indexOf(state.paramPrevDate);
        if (prevDateIndex !== -1) {
            initialDateIndex = prevDateIndex;
            state.currentMinute = 1440 + simulationStartMinute;
        } else {
            initialDateIndex = state.data.dates.indexOf(state.paramDate);
            state.currentMinute = 0;
            framesToSimulate = 0;
        }
    } else {
        state.currentMinute = simulationStartMinute;
    }
    state.currentDateIndex = initialDateIndex;

    const dt = 1 / CONFIG.fps;
    for (let i = 0; i < framesToSimulate; i++) {
        advanceSimulation(dt);
    }
};

/**
 * 将动画向前推进一帧，供 Playwright 调用。
 */
window.advanceFrame = () => {
    advanceSimulation(1 / CONFIG.fps);
};

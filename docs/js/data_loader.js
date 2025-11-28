// docs/js/data_loader.js

import { state, saveSettings } from './state.js';
import { updateTitle } from './ui.js';
import { loop, renderCurrentState, advanceSimulation } from './render.js';
import { CONFIG } from './constants.js';

export async function loadData(lang, initialDate = null) {
    const loading = document.getElementById('loading');
    if(loading) loading.style.display = 'block';

    if (state.animationFrameId) cancelAnimationFrame(state.animationFrameId);

    document.getElementById('chart-container').innerHTML = '';
    state.bars = {};
    state.lang = lang;
    updateTitle();

    const langSelect = document.getElementById('lang-select');
    if(langSelect) langSelect.value = lang;

    try {
        state.config = window.INJECTED_CONFIG || await (await fetch(`config.json`)).json();
        state.data = window.INJECTED_DATA || await (await fetch(`data/history_${lang}.json`)).json();

        state.currentDateIndex = 0;
        if (initialDate && state.data.dates.includes(initialDate)) {
            state.currentDateIndex = state.data.dates.indexOf(initialDate);
        }
        state.currentMinute = 0;

        if (state.mode === 'normal') {
            const preRunHours = 1.5; // 预加载小时数。
            const preRunTargetMinutes = preRunHours * 60;

            // 使用标准时间步长 (dt) 逐帧推进模拟。
            const simulationDt = 1 / CONFIG.fps;
            while (state.currentMinute < preRunTargetMinutes) {
                advanceSimulation(simulationDt);
            }
        }

        if(loading) loading.style.display = 'none';
        window.appReady = true;

        if (state.mode === 'normal') {
            state.isPlaying = true;
            const btnPlay = document.getElementById('btn-play');
            if(btnPlay) btnPlay.innerText = "Pause";
            state.lastFrameTime = performance.now();
            loop(state.lastFrameTime);
        } else {
            renderCurrentState(1 / CONFIG.fps);
        }

    } catch (e) {
        console.error("Failed to load data or config", e);
        if(loading) loading.innerText = "Error loading data/config: " + e.message;
    }
}

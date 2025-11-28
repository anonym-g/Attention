// docs/js/render.js

import { state } from './state.js';
import { CONFIG } from './constants.js';
import { getValueAt, calculateTrend, getDerivativeColor } from './utils.js';

export function loop(timestamp) {
    if (!state.isPlaying) return;
    const dt = (timestamp - state.lastFrameTime) / 1000;
    state.lastFrameTime = timestamp;
    advanceSimulation(dt);
    state.animationFrameId = requestAnimationFrame(loop);
}

export function advanceSimulation(dt) {
    if (!state.data || !state.data.dates.length) return;

    const baseSpeed = 1440 / CONFIG.secondsPerDay;
    const effectiveSpeed = (state.mode === 'capture') ? 1 : state.playbackSpeed;
    state.currentMinute += baseSpeed * dt * effectiveSpeed;

    while (state.currentMinute >= 1440) {
        state.currentMinute -= 1440;
        state.currentDateIndex++;
        if (state.currentDateIndex >= state.data.dates.length) state.currentDateIndex = 0;
    }
    renderCurrentState(dt);
}

export function renderCurrentState(dt) {
    if (!state.data || !state.data.dates.length || !state.config) return;

    if (state.currentDateIndex >= state.data.dates.length) state.currentDateIndex = 0;

    const dateStr = state.data.dates[state.currentDateIndex];
    const hour = Math.floor(state.currentMinute / 60);
    const minute = Math.floor(state.currentMinute % 60);

    const timeDisplay = document.getElementById('time-display');
    if(timeDisplay) {
        timeDisplay.innerText = `${dateStr.replace(/-/g, '/')}-${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
    }

    let currentValues = [];
    for (const title of Object.keys(state.data.articles)) {
        const val = getValueAt(title, state.currentDateIndex, state.currentMinute);
        if (val > 0) {
            const trendDelta = calculateTrend(title, state.currentDateIndex, state.currentMinute, CONFIG.derivativeWindow);
            currentValues.push({ title, val, pastVal: val - trendDelta });
        }
    }

    currentValues.sort((a, b) => b.val - a.val);
    const topN = currentValues.slice(0, CONFIG.barCount);
    const frameMaxVal = topN.length > 0 ? Math.max(1, topN[0].val) : 1;

    const activeTitles = new Set();
    const container = document.getElementById('chart-container');

    topN.forEach((item, index) => {
        activeTitles.add(item.title);
        let barObj = state.bars[item.title];
        if (!barObj) {
            const el = createBarElement(item.title);
            container.appendChild(el);
            el.style.top = `${state.chartHeight}px`;
            barObj = { el, currentY: state.chartHeight, targetY: 0, speedFactor: CONFIG.minSpeed };
            state.bars[item.title] = barObj;
        }

        barObj.targetY = index * state.rowHeight;
        barObj.el.style.height = `${state.rowHeight}px`;
        barObj.el.querySelector('.bar-rank').innerText = index + 1;
        barObj.el.querySelector('.bar-value').innerText = item.val.toLocaleString();
        barObj.el.style.opacity = '1';

        let widthPct = state.isLogScale
            ? (Math.log(Math.max(1, item.val)) / Math.log(Math.max(1.1, frameMaxVal))) * 100
            : (item.val / frameMaxVal) * 100;
        widthPct = Math.max(Math.min(widthPct, 100), 15);

        const fillEl = barObj.el.querySelector('.bar-fill');
        fillEl.style.width = `${widthPct}%`;

        const trendDelta = item.val - item.pastVal;
        const slope = trendDelta / CONFIG.derivativeWindow;
        fillEl.style.backgroundColor = getDerivativeColor(slope);

        const normalizedPosDelta = frameMaxVal > 1 ? Math.abs(trendDelta) / frameMaxVal : 0;
        barObj.speedFactor = CONFIG.minSpeed + (CONFIG.maxSpeed - CONFIG.minSpeed) * normalizedPosDelta;
    });

    for (const title in state.bars) {
        if (!activeTitles.has(title)) {
            const barObj = state.bars[title];
            barObj.targetY = state.chartHeight + state.rowHeight;
            barObj.speedFactor = CONFIG.minSpeed;
            barObj.el.style.opacity = '0.5';
            if (barObj.currentY > state.chartHeight + 200 && barObj.el.parentNode) {
               container.removeChild(barObj.el);
               delete state.bars[title];
            }
        }
    }

    const timeScale = Math.min(dt * 60, 1.0);
    for (const title in state.bars) {
        const barObj = state.bars[title];
        barObj.currentY += (barObj.targetY - barObj.currentY) * Math.min(1, barObj.speedFactor * timeScale);
        barObj.el.style.top = `${barObj.currentY}px`;
    }
}

function createBarElement(title) {
    const el = document.createElement('div');
    el.className = 'bar-row';
    el.innerHTML = `<div class="bar-rank"></div><div class="bar-track"><div class="bar-fill"><span class="bar-title">${title.replace(/_/g, ' ')}</span><span class="bar-value">0</span></div></div>`;
    return el;
}

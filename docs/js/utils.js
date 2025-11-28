// docs/js/utils.js

import { state } from './state.js';

export function getValueAt(title, dateIndex, minute) {
    while (minute < 0) { minute += 1440; dateIndex--; }
    while (minute >= 1440) { minute -= 1440; dateIndex++; }
    if (dateIndex < 0 || dateIndex >= state.data.dates.length) return 0;

    const articleData = state.data.articles[title];
    const dateStr = state.data.dates[dateIndex];
    if (!articleData || !articleData.minutes || !articleData.minutes[dateStr]) return 0;

    const arr = articleData.minutes[dateStr];
    return arr[Math.min(Math.floor(minute), arr.length - 1)] || 0;
}

export function calculateTrend(title, dateIndex, currentMinute, windowSize) {
    const samples = 10;
    const step = windowSize / samples;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0, n = 0;
    for (let i = 0; i < samples; i++) {
        const val = getValueAt(title, dateIndex, currentMinute - (i * step));
        const x = -(i * step);
        sumX += x; sumY += val; sumXY += x * val; sumXX += x * x; n++;
    }
    if (n < 2) return 0;
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    return isNaN(slope) ? 0 : slope * windowSize;
}

export function getDerivativeColor(slope) {
    if (!state.config) return 'hsl(180, 10%, 30%)';
    if (slope === undefined) return 'hsl(180, 10%, 30%)';

    const baseThreshold = state.config.baseThreshold;
    const scaleFactor = state.config.scalingFactors[state.lang] || 1.0;
    const dynamicThreshold = baseThreshold * scaleFactor;
    const ratio = slope / dynamicThreshold;

    const clampedRatio = Math.max(-1, Math.min(1, ratio));
    let hue;
    if (clampedRatio > 0) {
        hue = 120 - clampedRatio * 120; // 绿 -> 红
    } else {
        hue = 120 - clampedRatio * 150; // 绿 -> 紫
    }

    const overdriveRatio = Math.max(0, Math.min(1, Math.abs(ratio) - 1));
    const lightness = 55 - (overdriveRatio * 20);

    return `hsl(${hue}, 90%, ${lightness}%)`;
}

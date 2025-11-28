// docs/js/state.js

const savedSettings = JSON.parse(localStorage.getItem('wiki_viz_settings') || '{}');

export const state = {
    data: null, // 动画数据
    config: null, // 配置数据
    isPlaying: true,
    currentDateIndex: 0,
    currentMinute: 0,
    playbackSpeed: savedSettings.playbackSpeed || 1,
    isLogScale: savedSettings.isLogScale !== undefined ? savedSettings.isLogScale : true,
    colorMode: 'derivative',
    lang: savedSettings.lang || 'en',
    mode: 'normal', // 'normal' 或 'capture'
    // URL参数
    paramDate: null,
    paramPrevDate: null,
    // 动画状态
    bars: {},
    rowHeight: 60,
    chartHeight: 0,
    lastFrameTime: 0,
    animationFrameId: null
};

export function saveSettings() {
    if (state.mode === 'capture') return;
    const settings = {
        lang: state.lang,
        playbackSpeed: state.playbackSpeed,
        isLogScale: state.isLogScale
    };
    localStorage.setItem('wiki_viz_settings', JSON.stringify(settings));
}

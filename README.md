# Attention
Tracking Wikipedia daily pageview trend, and automatically post on X (Twitter).

Feel free to check out the deployed [Project's GitHub Page](https://anonym-g.github.io/Attention).

## Project structure:

```
Attention/
├── .github/
│   └── workflows/
│       └── daily_report.yml      # GitHub Action for daily execution
├── data/
│   └── *.json                    # Cache for daily top articles data
├── docs/
│   ├── css/
│   │   ├── style.css             # Main stylesheet for the visualization page
│   │   └── variables.css         # CSS custom properties (colors, fonts, etc.)
│   ├── data/
│   │   └── history_*.json        # Processed historical data for animations
│   ├── js/
│   │   ├── app.js                # Main application entry point, initializes the app
│   │   ├── constants.js          # Global constants for the frontend animation
│   │   ├── data_loader.js        # Handles fetching and loading of data files
│   │   ├── render.js             # Core animation loop and DOM rendering logic
│   │   ├── state.js              # Global state management for the visualization
│   │   ├── ui.js                 # UI event handlers and layout-related functions
│   │   └── utils.js              # Frontend utility functions (calculations, color generation)
│   ├── config.json               # Frontend configuration (e.g., color thresholds)
│   └── index.html                # The HTML page that renders the animation
├── pictures/
│   └── YYYY-MM-DD/
│       └── lang_code/*.png       # Daily screenshots for tweets
├── src/
│   ├── animator.py               # Renders the video using Playwright and FFmpeg
│   ├── config.py                 # Main project configuration
│   ├── main.py                   # Main script: orchestrates fetching, rendering, and posting
│   ├── twitter_client.py         # Handles X (Twitter) API interactions
│   ├── utils.py                  # Utility functions (file handling, cleanup)
│   ├── wiki_api.py               # Fetches data from Wikimedia APIs
│   └── test_video_gen.py         # Standalone script for testing video generation
├── videos/
│   └── YYYY-MM-DD/
│       └── lang_code/*.mp4       # Daily video segments and final outputs
├── requirements.txt              # Python dependencies
└── README.md
```

## Tweet List

#### 2025-11-19: https://x.com/trailblaziger/status/1991369684428755293
#### 2025-11-20: https://x.com/trailblaziger/status/1991704915681378329
#### 2025-11-21: https://x.com/trailblaziger/status/1992065689515954568
#### 2025-11-22: https://x.com/trailblaziger/status/1992433847783313800
#### 2025-11-23: https://x.com/trailblaziger/status/1992795370259456427
#### 2025-11-24: https://x.com/trailblaziger/status/1993155557939724576
#### 2025-11-25: https://x.com/trailblaziger/status/1993517960477220997
#### 2025-11-26: https://x.com/trailblaziger/status/1993879969034846255
#### 2025-11-27: https://x.com/trailblaziger/status/1994242524610007403
#### 2025-11-28: https://x.com/trailblaziger/status/1994626325093421080

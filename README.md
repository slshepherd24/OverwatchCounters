# OverwatchCounters — hosted edition

This version serves the existing analyzer and provides `/api/stats` from the same origin. The server attempts Blizzard's undocumented statistics endpoint, then a community weekly snapshot for PC. Only validated hero win-rate values are returned. If neither source works, the app **does not fabricate win rates** and continues with its strategic scoring.

## Run locally

Install Python 3.10+ and run `python server.py` in this directory. Open `http://localhost:8000`. Opening `index.html` directly will **not** provide the statistics endpoint.

## Publish

1. Upload this folder to a GitHub repository.
2. On Render, choose **New > Blueprint**, connect the repository, and use `render.yaml`.
3. Render provides a URL after the deployment finishes. On the free tier the server may sleep while idle.

No API keys or Python packages are required. The in-memory cache refreshes every 6 hours and resets on server restart. Profile settings are stored in the user's browser, not synced across devices.

## Important caveats

- The upstream Blizzard endpoint is undocumented and may change, reject automated requests, or use a different response format. The community JSON URL and schema also need testing against the current published dataset.
- Rank/map filtering is **only** represented as such when the official feed returns parseable records. Community fallback is labeled **all ranks / all maps**.
- An observed win rate is not a predicted win probability for your exact team composition.
- This build is deployment-ready but live upstream access has not been verified here. Check the status banner after deployment.

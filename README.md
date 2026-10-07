# D-SAT Link Budget & Constellation Coverage Tool

## Run
1. Install Python 3.11/3.12.
2. In this folder: `python -m venv .venv`
3. Windows: `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `streamlit run app.py`

The application calculates TLE/SGP4 geometry, range, elevation, FSPL, C/N0, Eb/N0, link margin, passes, revisit time, point/grid coverage, data volume, multiple satellites, and CSV export.

Team Project – ROSPIN Summer School 2026
This project was developed as part of a team during the ROSPIN Summer School. My main contribution focused on the link budget calculations and analysis, including FSPL, C/N₀, Eb/N₀, and link margin.

Default D-SAT: NORAD 42794. The default simulation starts 24 Aug 2026 UTC, near the TLE epoch. Do not manually enter ranges: they are calculated from TLE + time + ground coordinates. The 10-degree minimum elevation is a project assumption. City coverage is not geographic-area coverage; grid mode is only an approximate offline area-style metric and should use an official Romania boundary for a final scientific area percentage.

# The State of America's Health — auto-updating dashboard

A self-contained, interactive dashboard of U.S. health-condition prevalence, synthesized
from public CDC / SAMHSA / NCI data. It refreshes itself weekly from live CDC sources.

**Live page:** enable GitHub Pages (see below) → `https://timothygreenzweig-sys.github.io/us_healthcare/`

## Views
- **Overall** — ranked prevalence of 15 major conditions among U.S. adults
- **By age** — how blood pressure, obesity, and diabetes shift across age bands
- **Over time** — multi-year BRFSS trends per condition
- **By state** — tile-grid map + ranked list for 10 conditions, with an Everyone/Women/Men breakdown
- **Real-time** — weekly respiratory surveillance (COVID-19 / flu / RSV ED-visit share + ARI activity)
- **CSV / PNG export** of any view (in the published claude.ai artifact runtime)

## How it updates
`build_dashboard.py` pulls current data and regenerates `index.html` from `template.html`:

| Data | Source (data.cdc.gov) |
|------|-----------------------|
| Chronic conditions by state (+ by sex) | BRFSS Prevalence `dttw-5yxu` |
| Obesity by state (+ by sex) | DNPAO BRFSS `hn4x-zwk7` |
| Multi-year trends | BRFSS `dttw-5yxu` (US, Overall) |
| Real-time respiratory (weekly) | NSSP ED visits `7xva-uux8` + ARI activity `f3zz-zga5` |

National *overall*, *by-age*, and *different-base* figures are curated constants from the most
authoritative source per condition (NHANES / NHIS / SAMHSA / NCI), which update roughly annually.

The build auto-selects the newest available data year for each state measure.

## Run it yourself
```bash
python3 build_dashboard.py   # pure Python stdlib; needs internet to data.cdc.gov
```
Open the resulting `index.html` in any browser.

## Weekly automation
`.github/workflows/weekly-refresh.yml` runs the build every Monday, and commits `index.html`
only when the data actually changed. GitHub Pages (Deploy from branch → `main` / root) then
serves the refreshed page automatically.

## Caveats
Figures come from different surveys and years and **overlap** (one person can appear in many),
so they don't sum to 100%. State/age/trend views use self-reported BRFSS (lower than measured
NHANES); compare *within* a view, not across. Prevalence is not severity. See the in-page notes.

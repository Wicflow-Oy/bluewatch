# Data

Everything here is public, company-level data collected for this prototype on 16–17 Oct 2026. It holds no names of people, no e-mail addresses and no phone numbers: where a source named a founder or a staff member, the file says only that a person is named. Sole traders (private persons) are never kept.

## `seed/`: the verified demo set
| File | What it holds | Sources |
|---|---|---|
| `startups.json` | 136 Nordic and Baltic ocean companies with registry IDs, verticals and evidence URLs | PRH, Brreg, RIK, VIES, company websites |
| `investors.json` | 60 VCs, corporate VCs, angel networks and public funders: stages, tickets, theses. Each row is tagged `read`, `read+snippet`, `snippet` or `name-only` | The investors' own websites |
| `grants.json` | 43 funding instruments with their eligibility rules, each rule tagged by source, plus 17 open EU topics | Funders' call pages; EU Funding & Tenders portal |
| `partners.json` | 84 corporates, ports, public buyers, test beds and universities | Organisations' websites, TED |
| `bridges_seed.json` | 10 hand-checked opportunity bridges and one gap-ledger example | TED, CORDIS, Interreg, funders' pages |
| `hackathon_projects_seed.json`, `hackathon_scout_seed.json` | 217 public hackathon results at project level, with no participant names, and the scout's scoring weights | Organisers' result pages |
| `research_prestartup.json` | 32 EU and Interreg research projects with Finnish participants, and 13 research groups | CORDIS, Interreg Central Baltic |
| `answer_keys.json` | Reference readiness bands for companies the judges know, used only to measure precision. **The bands are our own inference from public evidence.** | Public evidence per row |
| `signals_cache.json` | Dated public signals for 87 companies (register notices, TED awards, first certificates) | PRH, TED, crt.sh, Wayback |
| `monday10_demo_2026-10-12.json` | The hand-curated list from the research phase ("Monday 10" was the list's earlier name) | As above |

## `presets/`: the theses
`blue.json` (blue economy) and `climate_circular.json` (climate and circular economy): verticals, keywords, grant topics, stage window, weights and thresholds. The engine is the same for both.

## `eval/`: what the rules and the reader are measured against
- `precision/traps.json`: the entity-matching traps (look-alike names, foreign namesakes).
- `precision/blind_set_example.csv`: the format of a partner's blind set.
- `reader/pages.json`, `reader/traps.json`: the reader's eval pages and its false-positive traps.

## `fixtures/`: recorded responses, used by tests and the offline demo
- `sources/`: responses from PRH (companies and trade register notices), Brreg, TED and CORDIS, plus an extract from the Estonian e-Business Register (legal persons only); `live_2026-10-17/` holds the requests recorded live on 17 Oct.
- `read/`: the reader's benchmark and calibration results.

Sweden's register (SCB) is not loaded yet: its weekly bulk file also lists sole traders by personal number, so it needs a legal-persons-only import first. Swedish companies come from the research pack only, and the app shows SCB as unavailable rather than counting it as zero.

## Licences
- **Finnish Patent and Registration Office (PRH):** CC BY 4.0.
- **Brønnøysund Register Centre (Brreg):** NLOD 2.0.
- **Estonian e-Business Register (RIK):** CC BY 4.0.
- **TED and CORDIS:** © European Union, CC BY 4.0.
- **Company and investor websites:** facts are quoted briefly with a link to the page.

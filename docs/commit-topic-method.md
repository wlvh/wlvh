# Commit Topic Map Method

The profile chart is regenerated from owned, non-fork repository commits on
each default branch. Private repositories are included during local
classification so the chart reflects real work, but raw private commit
messages and private repo names are kept out of the committed files.

## What the chart actually shows

`assets/commit-topic-map.svg` is a **monthly stacked-column** view of the
**past 12 months**, designed to read like a continuation of the GitHub
contribution heatmap that sits above it on the profile page. The full input
corpus runs back to the first owned commit, but only the trailing twelve
months are drawn — that is the same window the GitHub heatmap covers.

Each column is a calendar month. Each colored segment inside a column is one
**working theme**. The annotation above each column shows the column total
and, for months with at least 30 commits, the dominant theme.

The right-hand legend repeats each theme with a per-theme **sparkline**: a
mini monthly trend scaled to that theme's own twelve-month maximum, so it
shows *when* the work happened, not *how much* relative to the headline.

## The ten working themes

The classifier replaces the old commit-verb taxonomy (feat/fix/docs/…) with
ten domains. The intent is to show **what the year of work was about**, not
how each commit was tagged.

| Theme | Color | What it means |
| --- | --- | --- |
| Agent Orchestration | `#6f42c1` | Claude Code / Codex workflow design, sync passes, dispatch, multi-agent coordination, governance |
| LLM Eval & Contracts | `#bf3989` | NL2DAX evaluation, capability/runtime contracts, merge-readiness gates, codex audits, constitution suggestion |
| Quant Strategy & Optuna | `#1a7f37` | Hyperparameter search, overfit guardrails, batch/performance contracts, hot-path tuning |
| Live Trading Ops | `#2da44e` | Allocate orchestration, monitoring dashboards, CCXT live trading bots |
| Backtest & MCS Research | `#bf8700` | Block bootstrap, Model Confidence Set, live backtest pipelines, alpha parameters, report generation |
| Time-Series ML | `#1b7c83` | Crossformer / DTHelper / m5 model integrations, hourly crypto calendars |
| Semantic Model & DAX | `#0969da` | Semantic model v2, DAX runner, query contracts, CSAT, time-anchor / serialization |
| Data Pipeline & Schema | `#218bff` | Field profiling kernels, schema refresh, duplicate scanners, shared LLM runners, RAG |
| AST & Code Tooling | `#bc4c00` | PySymphony, ASTAuditor, auto-fix undefined symbols, circular-dependency detection |
| Content & Methodology | `#57606a` | AI magazine articles, daily radar archives, HowToUseLLM notes, governance docs (CLAUDE.md / AGENTS.md) |

The taxonomy is intentionally narrative rather than statistical: it tells the
reader "this person spent the year on agent orchestration, quant research,
semantic models, and the methodology around them," instead of "this person
opened 412 fix: PRs."

## Classification rules

Each commit is scored against every theme:

- **Repo prior**: if the commit's repository is listed in the theme's
  `repos` array, the theme gets `repo_weight` (default 5) added.
- **Keyword presence**: every keyword that appears as a substring of
  `repo + subject + body` (lowercased) adds `keyword_weight` (default 1).

Highest total wins; ties resolve in declaration order, which is also the
stacking order in the chart. Two repositories (`trading`) are deliberately
listed under more than one theme so that keywords (`optuna` / `allocate` /
`monitor` …) decide whether each commit reads as strategy work or live ops.

`skip_merge_commits: true` makes the classifier drop rows where the
collector flagged `is_merge`, so the headline number reflects actual work
rather than merge bookkeeping.

## Privacy boundary

| File | Tracked? | Contents |
| --- | --- | --- |
| `data/commits_raw.jsonl` | ignored | full local commit text including private repos |
| `data/commits_classified.jsonl` | ignored | classified rows with private repo names |
| `data/commit_taxonomy.local.json` | ignored | taxonomy with private repo priors |
| `data/commit_taxonomy.json` | tracked | same taxonomy with private repo priors redacted |
| `data/commit_topics_public.json` | tracked | aggregate counts only, no raw text, no private repo names |
| `assets/commit-topic-map.svg` | tracked | rendered visual |

The committed taxonomy keeps the same category ids, labels, colors, and
keywords as the local one — only the `repos` arrays differ.

## Regenerate locally

```bash
python3 scripts/collect_commits.py \
  --owner wlvh \
  --output data/commits_raw.jsonl \
  --include-private

python3 scripts/classify_commits.py \
  --raw data/commits_raw.jsonl \
  --taxonomy data/commit_taxonomy.local.json \
  --classified data/commits_classified.jsonl \
  --public data/commit_topics_public.json

python3 scripts/render_commit_topic_map.py \
  --aggregate data/commit_topics_public.json \
  --output assets/commit-topic-map.svg
```

For the standard cadence (and for invoking these from Claude Code), see
`AGENTS.md`.

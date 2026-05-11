# AGENTS.md — Claude Code operations manual

This repo is wlvh's GitHub profile (`wlvh/wlvh`). Its README is the public
profile page; `assets/commit-topic-map.svg` is the visualization that sits
under the GitHub contribution heatmap.

When you (Claude Code) are invoked inside this directory, your default job
is to **regenerate the commit topic map** so the profile reflects the last
twelve months of work. Treat this file as the source of truth for the
procedure — `docs/commit-topic-method.md` explains the *why*, this file
explains the *how*.

## TL;DR

1. Refresh local commit corpus from GitHub.
2. Re-classify against the local (private-aware) taxonomy.
3. Re-render the SVG.
4. Sanity-check the distribution and the headline number.
5. Commit *only* the public artefacts; never commit ignored files.

## Prerequisites you should verify before running anything

- `gh auth status` returns the wlvh account with the `repo` scope.
- `python3 --version` resolves (stdlib only — no `pip install` needed).
- Working directory is the root of `wlvh/wlvh` profile repo.
- `.gitignore` already excludes `commits_raw.jsonl`,
  `commits_classified.jsonl`, and `commit_taxonomy.local.json`. Do not
  modify those rules — they are the privacy boundary.

## Standard regeneration

Run these four scripts in order. Each command is independent of in-memory
state, so you can stop and resume between them.

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

python3 scripts/build_index_html.py \
  --svg assets/commit-topic-map.svg \
  --output index.html
```

Default render size is 880 × 660. Pass `--width` / `--height` only if you
have a specific reason — the README references the SVG without dimensions.

The final step rebuilds `index.html` with the SVG inlined into the main
document plus a JavaScript tooltip handler. This is necessary because
GitHub Pages can serve the static SVG, but Chromium does not fire
`<title>`-based native tooltips on segments inside an `<object>`-embedded
SVG sub-document. Inlining puts the segments in the main document where a
small JS handler can show a styled tooltip on hover. Skip this step only
if you have a reason — the profile README's `interactive version` link
goes to the GitHub Pages copy of `index.html`.

## Sanity checks before committing

After regenerating, run:

```bash
python3 - <<'PY'
import json
data = json.load(open("data/commit_topics_public.json"))
print(f"total (all-time): {data['total_commits']:,}")
print(f"public repos: {data['public_repo_count']}, private: {data['private_repo_count']}")
print()
print("Past 12 months per theme:")
months = sorted(data["monthly_counts"].keys())[-12:]
totals = {}
for m in months:
    for cid, n in data["monthly_counts"][m].items():
        totals[cid] = totals.get(cid, 0) + n
labels = {c["id"]: c["label"] for c in data["categories"]}
window_total = sum(totals.values())
print(f"  window total: {window_total}")
for cid, n in sorted(totals.items(), key=lambda kv: -kv[1]):
    print(f"  {labels.get(cid, cid):30s} {n:4d}  {n/window_total*100:5.1f}%")
PY
```

Expectations (drift outside these ranges means investigate, do not ship):

- `total (all-time)` should be **monotonically non-decreasing** between
  runs. A sudden drop means a collection or filter regression.
- `Other` (id `other`) should be **under 5%** of the past-12-month window.
  Higher means the taxonomy is missing a real domain — see
  "When to update the taxonomy" below.
- The headline number rendered in the SVG (`commits this year`) should
  match the `window total` printed above. If it doesn't, the renderer is
  filtering differently than the sanity-check script.

Also open the SVG in a previewer (`qlmanage -t -s 1600 -o /tmp assets/commit-topic-map.svg`)
and confirm: 12 monthly columns, all 10 themes in legend, the year boundary
dashed line lands between two columns that straddle a calendar year, and
none of the dominant-theme labels collide with the column count.

## When to update the taxonomy

Reach for `data/commit_taxonomy.local.json` (and mirror to
`data/commit_taxonomy.json` with private repos redacted) when:

1. **A new repo with substantial commits appears** that has no repo prior
   yet. Sample 15–20 of its commits, decide which theme it belongs to, and
   add the repo to that theme's `repos` array.
2. **`Other` share is climbing past 5%**. Inspect the local
   `commits_classified.jsonl` for rows with category `other` and either
   add keywords that capture the missed concept, or add a new theme entry
   if a genuinely new domain has emerged.
3. **A theme has stopped earning commits** for several months. Don't
   delete it — keep the slot so the timeline reads consistently — but
   consider whether its repo priors or keywords have drifted away from the
   work pattern.

When you add a theme, pick a color that stays distinguishable from the
nine others against a white background. The existing palette is built from
GitHub's primer hues; pull a sibling hue from there.

After any taxonomy edit, **always**:

- Update `data/commit_taxonomy.json` (the committed mirror) to match,
  with private repo names stripped.
- Re-run classification and rendering.
- Update `docs/commit-topic-method.md` if the public theme table needs to
  reflect a new theme or new color.
- Update `THEME_ORDER` and `THEME_SHORT_LABEL` in
  `scripts/render_commit_topic_map.py` if you added or removed a theme.

## When **not** to update

- Do **not** rewrite the taxonomy because individual commits look
  misclassified. The classifier is deterministic and trades per-commit
  precision for monthly stability. A handful of misclassifications inside
  a busy month rounds out in the column total.
- Do **not** add a "fix" / "feat" / "chore" category back in. That is
  exactly the failure mode this rewrite was meant to address.
- Do **not** broaden a keyword to a generic English word ("fix", "update",
  "add") — those words appear in every domain and will pollute every
  column.

## Privacy checks before commit

Run `git status` and confirm that:

- `data/commits_raw.jsonl` is **untracked / ignored**.
- `data/commits_classified.jsonl` is **untracked / ignored**.
- `data/commit_taxonomy.local.json` is **untracked / ignored**.
- The only files staged are some subset of:
  `data/commit_taxonomy.json`,
  `data/commit_topics_public.json`,
  `assets/commit-topic-map.svg`,
  `scripts/*.py`,
  `docs/commit-topic-method.md`,
  `AGENTS.md`,
  `README.md`.

If anything else is staged, stop and figure out why. Do not commit private
repo names or raw commit messages.

## Where the SVG is shown

The profile `README.md` references the SVG as a top-of-page block, full
width below the GitHub contribution heatmap. Do not switch it back to a
right-floated thumbnail — the chart is designed to be read at native
880px width.

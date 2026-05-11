# Commit Topic Map Method

The profile chart is generated from owned, non-fork repository commits on each
default branch. Private repositories can be included during local generation,
but raw private commit messages are ignored by Git and are not published.

The taxonomy is intentionally data-derived: repository clusters, repeated commit
phrases, and sampled subjects are inspected first, then mapped into a compact set
of public-facing categories. The committed taxonomy redacts private repository
names; a local ignored `data/commit_taxonomy.local.json` can add private repo
priors when generating the aggregate chart. The output is a directional
portfolio map, not a statistical proof of effort or impact.

Generated files:

- `data/commits_raw.jsonl`: ignored local raw commit records.
- `data/commits_classified.jsonl`: ignored local classification audit rows.
- `data/commit_taxonomy.local.json`: ignored private-aware taxonomy.
- `data/commit_topics_public.json`: public aggregate counts only.
- `assets/commit-topic-map.svg`: profile README visual.

Regenerate locally:

```bash
python3 scripts/collect_commits.py --owner wlvh --output data/commits_raw.jsonl --include-private
python3 scripts/classify_commits.py --raw data/commits_raw.jsonl --taxonomy data/commit_taxonomy.local.json --classified data/commits_classified.jsonl --public data/commit_topics_public.json
python3 scripts/render_commit_topic_map.py --aggregate data/commit_topics_public.json --output assets/commit-topic-map.svg
```

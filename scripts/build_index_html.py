"""Wrap the rendered commit topic map SVG in an interactive HTML page.

Purpose:
    GitHub renders the profile README SVG as an <img>, so segment-level
    hover tooltips never fire there. Even on the GitHub Pages mirror,
    embedding via <object> leaves the SVG in a sub-document where Chromium
    does not render <title>-based native tooltips. Inlining the SVG into
    the main HTML document and attaching a JavaScript tooltip handler is
    the only embedding that reliably shows the per-segment commit list.

Call graph:
    main -> parse_args -> read_svg -> render_html -> write_output
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildConfig:
    """Runtime parameters for the HTML wrapper build.

    Attributes:
        svg_path: Path to the SVG produced by render_commit_topic_map.py.
        output_path: HTML file to write at the wlvh/wlvh repository root.
    """

    svg_path: Path
    output_path: Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>wlvh — commit topic map · past 12 months</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Interactive monthly stacked-column view of wlvh's past 12 months of commits across ten working themes, with per-segment hover tooltips listing public-repo commit subjects.">
<style>
  :root {{
    color-scheme: light;
    --fg: #1f2328;
    --muted: #656d76;
    --soft: #8c959f;
    --link: #0969da;
    --border: #d0d7de;
    --bg: #ffffff;
    --tip-bg: rgba(31, 35, 40, 0.96);
    --tip-fg: #ffffff;
  }}
  html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--fg);
  }}
  body {{
    font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 960px;
    margin: 0 auto;
    padding: 40px 24px 64px;
    line-height: 1.55;
  }}
  h1 {{
    font-size: 22px;
    margin: 0 0 6px;
    font-weight: 700;
  }}
  p.lede {{
    color: var(--muted);
    margin: 0 0 24px;
    font-size: 13px;
  }}
  p.lede strong {{
    color: var(--fg);
    font-weight: 600;
  }}
  a {{
    color: var(--link);
    text-decoration: none;
  }}
  a:hover {{
    text-decoration: underline;
  }}
  .chart-wrap {{
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    background: var(--bg);
  }}
  .chart-wrap svg {{
    display: block;
    width: 100%;
    height: auto;
    /* The chart wrap clips overflow so the rounded path tops never poke
       past the rounded container corners. */
    overflow: hidden;
  }}
  /* Per-segment highlight on hover so the tooltip target is visible. */
  .chart-wrap svg [data-hoverable] {{
    transition: filter 0.12s ease;
    cursor: default;
  }}
  .chart-wrap svg [data-hoverable]:hover {{
    filter: brightness(1.12) saturate(1.05);
  }}
  #ttip {{
    position: fixed;
    background: var(--tip-bg);
    color: var(--tip-fg);
    padding: 9px 12px;
    border-radius: 6px;
    font: 12px/1.55 ui-sans-serif, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Helvetica, Arial, sans-serif;
    pointer-events: none;
    white-space: pre-line;
    max-width: 380px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
    visibility: hidden;
    opacity: 0;
    transition: opacity 0.10s ease;
    z-index: 100;
  }}
  #ttip.show {{
    visibility: visible;
    opacity: 1;
  }}
  footer {{
    margin-top: 32px;
    font-size: 12px;
    color: var(--soft);
  }}
  footer a {{
    color: var(--muted);
  }}
</style>
</head>
<body>
<h1>wlvh — commit topic map · past 12 months</h1>
<p class="lede">
  Hover any colored segment to see
  <strong>which public-repo commits</strong>
  contributed to that month · theme bucket. Private-repo work is counted
  but never quoted — see the
  <a href="https://github.com/wlvh/wlvh/blob/main/docs/commit-topic-method.md">methodology note</a>
  for the privacy boundary.
</p>
<div class="chart-wrap">
{svg}
</div>
<div id="ttip" role="tooltip" aria-live="polite"></div>
<footer>
  Source: <a href="https://github.com/wlvh/wlvh">github.com/wlvh/wlvh</a>
  · regenerated deterministically, see
  <a href="https://github.com/wlvh/wlvh/blob/main/AGENTS.md">AGENTS.md</a>.
</footer>
<script>
(() => {{
  const tip = document.getElementById('ttip');
  if (!tip) return;
  // Inlined SVG sits inside .chart-wrap; only stacked-column segments carry
  // gradient fills, so we target those directly.
  const segments = document.querySelectorAll(
    '.chart-wrap svg rect[fill^="url("], .chart-wrap svg path[fill^="url("]'
  );
  segments.forEach(el => {{
    const titleEl = el.querySelector(':scope > title');
    if (!titleEl) return;
    const text = titleEl.textContent;
    // Suppress the native browser tooltip so it doesn't double up with ours.
    titleEl.remove();
    el.setAttribute('data-hoverable', '1');
    el.setAttribute('aria-label', text.replace(/\\n+/g, ' · '));

    el.addEventListener('mouseenter', () => {{
      tip.textContent = text;
      tip.classList.add('show');
    }});
    el.addEventListener('mousemove', (event) => {{
      const pad = 14;
      let x = event.clientX + pad;
      let y = event.clientY + pad;
      const w = tip.offsetWidth;
      const h = tip.offsetHeight;
      if (x + w > window.innerWidth - 8) x = event.clientX - w - pad;
      if (y + h > window.innerHeight - 8) y = event.clientY - h - pad;
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
    }});
    el.addEventListener('mouseleave', () => {{
      tip.classList.remove('show');
    }});
  }});
}})();
</script>
</body>
</html>
"""


def parse_args() -> BuildConfig:
    """Parse explicit paths so the build never depends on hidden state."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    return BuildConfig(svg_path=Path(args.svg), output_path=Path(args.output))


def read_svg(*, svg_path: Path) -> str:
    """Read the rendered SVG file and strip an XML declaration if present."""

    text = svg_path.read_text(encoding="utf-8").strip()
    if text.startswith("<?xml"):
        # Inline SVG must not carry an XML declaration when embedded inside
        # HTML — strip the first processing instruction line.
        text = text.split("?>", 1)[1].lstrip()
    return text


def render_html(*, svg_markup: str) -> str:
    """Wrap inline SVG markup in the HTML page template."""

    return HTML_TEMPLATE.format(svg=svg_markup)


def write_output(*, output_path: Path, html: str) -> None:
    """Write the wrapped HTML page to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    """Read the SVG, wrap it, and write the interactive HTML page."""

    config = parse_args()
    svg_markup = read_svg(svg_path=config.svg_path)
    html = render_html(svg_markup=svg_markup)
    write_output(output_path=config.output_path, html=html)
    print(f"wrote {config.output_path}")


if __name__ == "__main__":
    main()

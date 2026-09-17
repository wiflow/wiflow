#!/usr/bin/env python3
"""Generate assets/banner.svg: one dark banner with a dot-matrix WIFLOW wordmark.

Run from the repo root:  python scripts/gen_banner.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

W, H = 900, 180
BG, EDGE = "#0d1117", "#30363d"
ON, OFF = "#ffb000", "#21262d"
TEXT, DIM = "#e6edf3", "#8b949e"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# 5x7 dot-matrix glyphs (7 rows each)
F = {
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
}


def dots(text, col0, row0):
    c = col0
    for ch in text:
        g = F[ch]
        for r, row in enumerate(g):
            for k, bit in enumerate(row):
                if bit == "1":
                    yield c + k, row0 + r
        c += len(g[0]) + 1


def main():
    pitch = 9
    text = "WIFLOW"
    cols = sum(len(F[c][0]) for c in text) + len(text) - 1  # 35
    grid_w, grid_h = cols * pitch, 7 * pitch
    gx, gy = 48, (H - grid_h) // 2
    lit = set(dots(text, 0, 0))

    off = "".join(
        f'<circle cx="{gx + (c + .5) * pitch:g}" cy="{gy + (r + .5) * pitch:g}" r="{pitch * .17:g}"/>'
        for r in range(7) for c in range(cols) if (c, r) not in lit
    )
    on = "".join(
        f'<circle cx="{gx + (c + .5) * pitch:g}" cy="{gy + (r + .5) * pitch:g}" r="{pitch * .36:g}"/>'
        for c, r in sorted(lit)
    )

    tx = W - 48
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="WIFLOW — backend &amp; game-server developer">
<title>WIFLOW</title>
<defs>
  <pattern id="grid" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="9" cy="9" r="1" fill="#161b22"/></pattern>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="12"/></clipPath>
</defs>
<g clip-path="url(#c)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{EDGE}"/>
<g fill="{OFF}">{off}</g>
<g fill="{ON}">{on}</g>
<g font-family="{SANS}" text-anchor="end">
  <text x="{tx}" y="{H / 2 - 14:g}" font-size="20" font-weight="600" fill="{TEXT}">Backend, game-server &amp; infrastructure developer</text>
  <text x="{tx}" y="{H / 2 + 14:g}" font-size="14" fill="{DIM}">Server cores, plugins, and the networks they run on</text>
  <text x="{tx}" y="{H / 2 + 42:g}" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{ON}">RUST · KOTLIN · JAVA · NODE.JS</text>
</g>
</svg>
"""
    OUT.mkdir(exist_ok=True)
    (OUT / "banner.svg").write_text(svg, encoding="utf-8")
    print(f"wrote assets/banner.svg ({W}x{H}, {len(lit)} lit dots)")


if __name__ == "__main__":
    main()

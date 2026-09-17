#!/usr/bin/env python3
"""Contribution snake that stays inside the grid.

Fetches the user's GitHub contribution calendar and renders an animated SVG:
a snake of N segments hunts down every contribution cell in the 53x7 grid,
always heading for the nearest one. Nothing ever leaves the grid.

Usage:
    python scripts/gen_snake.py --user wiflow --out dist
Requires the `gh` CLI (authenticated, or GH_TOKEN set).
"""
import argparse
import json
import subprocess
from pathlib import Path

CELL, DOT, RADIUS = 16, 12, 2
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

PALETTES = {
    "light": dict(dots=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"], border="rgba(27,31,35,.06)"),
    "dark": dict(dots=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"], border="rgba(255,255,255,.05)"),
}

QUERY = """
query($login:String!){ user(login:$login){ contributionsCollection{ contributionCalendar{
  weeks{ contributionDays{ weekday contributionLevel } } } } } }
"""


def fetch_grid(user):
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={user}"],
        check=True, capture_output=True, text=True,
    ).stdout
    weeks = json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = {}
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[(x, day["weekday"])] = LEVELS[day["contributionLevel"]]
    return grid, len(weeks)


def hunt_path(grid, snake_len, start=(0, 3)):
    """Snake-game style path: repeatedly walk to the nearest uneaten contribution cell.

    BFS runs inside the grid only. The snake's own body counts as an obstacle,
    time-aware: a body cell frees up once the tail has moved past it.
    """
    from collections import deque

    cells = set(grid)
    todo = {c for c, lvl in grid.items() if lvl}
    path = [start]
    body = deque([start] * snake_len)  # index 0 = head

    def bfs(head):
        # occupied-until: body index j frees after (snake_len - j) steps
        until = {}
        for j, c in enumerate(body):
            until[c] = min(until.get(c, 99), snake_len - j)
        clamp = lambda d: min(d, snake_len)
        prev = {(head, 0): None}
        q = deque([(head, 0)])
        while q:
            (c, d) = q.popleft()
            if c in todo and d > 0:
                out, s = [], (c, clamp(d))
                while prev[s] is not None:
                    out.append(s[0])
                    s = prev[s]
                return out[::-1]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n not in cells:
                    continue
                nd = d + 1
                if nd < until.get(n, 0):
                    continue
                key = (n, clamp(nd))
                if key in prev:
                    continue
                prev[key] = (c, clamp(d))
                q.append((n, nd))
        return None

    while todo:
        leg = bfs(path[-1])
        if not leg:  # boxed in: step anywhere free and retry
            h = path[-1]
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                n = (h[0] + dx, h[1] + dy)
                if n in cells and n not in body:
                    leg = [n]
                    break
            if not leg:
                break
        for c in leg:
            path.append(c)
            body.appendleft(c)
            body.pop()
            todo.discard(c)
    return path


def render(grid, cols, path, palette, snake_len=8, step_ms=100, pause_ms=2500, snake_color="#ffb000"):
    rows = 7
    W, H = cols * CELL, rows * CELL
    steps = len(path)
    total_ms = steps * step_ms + pause_ms
    pct = lambda ms: f"{100 * ms / total_ms:.3f}"

    css = [
        f"@keyframes fade{{0%{{opacity:0}}1.5%{{opacity:1}}{pct(steps*step_ms+pause_ms*0.6)}%{{opacity:1}}100%{{opacity:0}}}}",
        f".s{{animation:fade {total_ms}ms linear infinite}}",
    ]
    body, snake = [], []

    # Cells: draw every cell; contribution cells get an "eaten" animation keyed to the head's arrival.
    when = {}
    for i, cell in enumerate(path):  # first visit eats the cell
        when.setdefault(cell, i)
    for (x, y), lvl in sorted(grid.items()):
        px, py = x * CELL + (CELL - DOT) / 2, y * CELL + (CELL - DOT) / 2
        fill = palette["dots"][lvl]
        attrs = f'x="{px:g}" y="{py:g}" width="{DOT}" height="{DOT}" rx="{RADIUS}" fill="{fill}" stroke="{palette["border"]}"'
        if lvl:
            t = when[(x, y)] * step_ms
            k = f"c{x}_{y}"
            css.append(
                f"@keyframes {k}{{0%,{pct(t)}%{{fill:{fill}}}{pct(t + step_ms)}%,100%{{fill:{palette['dots'][0]}}}}}"
            )
            body.append(f'<rect class="{k}" {attrs}/>')
            css.append(f".{k}{{animation:{k} {total_ms}ms linear infinite}}")
        else:
            body.append(f"<rect {attrs}/>")

    # Snake: each segment follows the path with an offset; keyframes only at direction changes.
    def pos(i):
        x, y = path[max(0, min(i, steps - 1))]
        return x * CELL + CELL / 2, y * CELL + CELL / 2

    for seg in range(snake_len):
        frames = []
        prev_dir = None
        for i in range(steps):
            j = i - seg  # this segment lags the head by `seg` steps
            cur = pos(j)
            nxt = pos(j + 1)
            d = (nxt[0] - cur[0], nxt[1] - cur[1])
            if i == 0 or d != prev_dir or i == steps - 1:
                frames.append((i * step_ms, cur))
            prev_dir = d
        frames.append((steps * step_ms + pause_ms, pos(steps - 1 - seg)))
        kf = "".join(f"{pct(t)}%{{transform:translate({x:g}px,{y:g}px)}}" for t, (x, y) in frames)
        k = f"g{seg}"
        css.append(f"@keyframes {k}{{{kf}}}")
        css.append(f".{k}{{animation:{k} {total_ms}ms linear infinite}}")
        size = DOT - seg * 0.5
        shade = 1 - seg * 0.06
        snake.append(
            f'<rect class="{k}" x="{-size/2:g}" y="{-size/2:g}" width="{size:g}" height="{size:g}" '
            f'rx="{RADIUS + 1}" fill="{snake_color}" opacity="{shade:.2f}"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution snake">'
        f"<title>Contribution snake</title><style>{''.join(css)}</style>"
        f"<g>{''.join(body)}</g>"
        f'<g class="s">{"".join(snake)}</g>'
        "</svg>"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--length", type=int, default=8)
    ap.add_argument("--snake-color", default="#ffb000")
    a = ap.parse_args()

    grid, cols = fetch_grid(a.user)
    path = hunt_path(grid, a.length)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, pal in (("github-snake.svg", "light"), ("github-snake-dark.svg", "dark")):
        svg = render(grid, cols, path, PALETTES[pal], snake_len=a.length, snake_color=a.snake_color)
        (out / name).write_text(svg, encoding="utf-8")
        print(f"wrote {out / name} ({len(svg) // 1024} KB, {len(path)} cells, snake {a.length})")


if __name__ == "__main__":
    main()

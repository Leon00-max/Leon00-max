"""Builds dark_mode.svg and light_mode.svg for the GitHub profile README.

Run locally:   python generate.py            (uses cached/placeholder stats)
In Actions:    GITHUB_TOKEN=... python generate.py   (pulls live stats)

Edit config.json to change the text. Drop an image named avatar.png in this
folder to control the ASCII portrait; otherwise your GitHub avatar is used.
"""

import datetime as dt
import io
import json
import os
import urllib.request
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
USER = CFG["username"]
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
CACHE = os.path.join(ROOT, "stats_cache.json")

ASCII_COLS, ASCII_ROWS = 40, 24
THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                 dots="#616e7f", ramp=" .:-=+*#%@"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069",
                  dots="#c2cfde", ramp="@%#*+=-:. "),
}


# ---------- stats ----------
def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats():
    base = graphql(
        """query($login:String!){ user(login:$login){
             createdAt
             followers{totalCount}
             repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
             repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){
               totalCount nodes{stargazerCount}}
             contributionsCollection{contributionCalendar{totalContributions}}
           }}""",
        {"login": USER},
    )["user"]

    # Commits across every year since the account was created (API max = 1 year per window).
    start = int(base["createdAt"][:4])
    now = dt.datetime.now(dt.timezone.utc)
    parts = []
    for y in range(start, now.year + 1):
        to = now.isoformat() if y == now.year else f"{y}-12-31T23:59:59Z"
        parts.append(f'y{y}: contributionsCollection(from:"{y}-01-01T00:00:00Z", to:"{to}")'
                     "{totalCommitContributions restrictedContributionsCount}")
    years = graphql("query($login:String!){user(login:$login){" + " ".join(parts) + "}}",
                    {"login": USER})["user"]
    commits = sum(v["totalCommitContributions"] for v in years.values())

    return {
        "repos": base["repositories"]["totalCount"],
        "contributed": base["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in base["repositories"]["nodes"]),
        "commits": commits,
        "followers": base["followers"]["totalCount"],
        "contrib_year": base["contributionsCollection"]["contributionCalendar"]["totalContributions"],
    }


def get_stats():
    if TOKEN:
        try:
            stats = fetch_stats()
            json.dump(stats, open(CACHE, "w"), indent=2)
            return stats
        except Exception as e:  # keep the card alive even if the API hiccups
            print("stats fetch failed, using cache:", e)
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    return dict(repos=0, contributed=0, stars=0, commits=0, followers=0, contrib_year=0)


# ---------- uptime ----------
def uptime(since):
    a = dt.date.fromisoformat(since)
    b = dt.date.today()
    months = (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)
    anchor_m = a.month - 1 + months
    anchor = dt.date(a.year + anchor_m // 12, anchor_m % 12 + 1, min(a.day, 28))
    days = (b - anchor).days
    y, m = divmod(months, 12)
    pl = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{pl(y, 'year')}, {pl(m, 'month')}, {pl(days, 'day')}"


# ---------- ascii portrait ----------
def load_avatar():
    local = os.path.join(ROOT, "avatar.png")
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        if os.path.exists(local):
            return Image.open(local)
        with urllib.request.urlopen(f"https://github.com/{USER}.png?size=240", timeout=20) as r:
            return Image.open(io.BytesIO(r.read()))
    except Exception as e:
        print("avatar unavailable, using fallback art:", e)
        return None


FALLBACK = r"""
     ___________________________________
    |  _____________________________  |
    | |                             | |
    | |  $ whoami                   | |
    | |  kami                       | |
    | |                             | |
    | |  $ cat skills.txt           | |
    | |  build . break . secure     | |
    | |                             | |
    | |  $ ./ship --prod            | |
    | |  [####################] OK  | |
    | |                             | |
    | |  $ _                        | |
    | |_____________________________| |
    |_________________________________|
           \_____________________/
         ___|___________________|___
        /  [][][][][][][][][][][]   \
       /  [][][][][][][][][][][][]   \
      /___[_____________________]____\
""".strip("\n").splitlines()


def ascii_art(img, ramp):
    if img is None:
        return FALLBACK
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img).convert("RGBA")  # alpha = transparent bg -> blank
    # character cells are ~8.8px wide x 20px tall, so crop to that aspect first
    target = (ASCII_COLS * 8.8) / (ASCII_ROWS * 20)
    w, h = img.size
    if w / h > target:
        nw = int(h * target); img = img.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = int(w / target); img = img.crop((0, 0, w, nh))  # keep the face (top)
    small = img.resize((ASCII_COLS, ASCII_ROWS))
    alpha = small.getchannel("A").tobytes()
    px = ImageOps.autocontrast(small.convert("L"), cutoff=2).tobytes()
    n = len(ramp) - 1
    rows = []
    for r in range(ASCII_ROWS):
        sl = slice(r * ASCII_COLS, (r + 1) * ASCII_COLS)
        rows.append("".join(" " if a < 128 else ramp[round(v / 255 * n)]
                            for v, a in zip(px[sl], alpha[sl])).rstrip())
    return rows


# ---------- svg ----------
def kv_line(key, value, width):
    lead = width - len(". " + key + ":") - len(value) - 2
    return key, " " + "." * max(lead, 1) + " ", value


def build_lines(stats):
    W = CFG["line_width"]
    up = uptime(CFG["coding_since"])
    lines = [("header", CFG["header"])]
    for i, sec in enumerate(CFG["sections"]):
        if i:
            lines.append(("blank",))
        for k, v in sec:
            lines.append(("kv",) + kv_line(k, v.replace("{uptime}", up), W))
    lines += [("blank",), ("header", "- Contact")]
    for k, v in CFG["contact"]:
        if v:
            lines.append(("kv",) + kv_line(k, v, W))
    s = {k: ("--" if v is None else (f"{v:,}" if isinstance(v, int) else v))
         for k, v in stats.items()}
    lines += [
        ("blank",), ("header", "- GitHub Stats"),
        ("kv2", ("Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}"),
                ("Stars", s["stars"])),
        ("kv2", ("Commits", s['commits']), ("Followers", s["followers"])),
        ("kv",) + kv_line("Contributions (last year)", s['contrib_year'], W),
    ]
    return lines


def render(theme, lines, art):
    t = THEMES[theme]
    W = CFG["line_width"]
    x0, y0, step = 420, 30, 20
    height = max(len(lines), len(art)) * step + 40
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="{height}" '
        'font-family="Consolas, \'DejaVu Sans Mono\', \'Courier New\', monospace" font-size="16px">',
        f"<style>.k{{fill:{t['key']}}} .v{{fill:{t['value']}}} .d{{fill:{t['dots']}}} "
        "text,tspan{white-space:pre}</style>",
        f'<rect width="1020" height="{height}" fill="{t["bg"]}" rx="15"/>',
        f'<text x="15" y="{y0}" fill="{t["text"]}">',
    ]
    for i, row in enumerate(art):
        out.append(f'<tspan x="15" y="{y0 + i * step}">{escape(row)}</tspan>')
    out += ["</text>", f'<text x="{x0}" y="{y0}" fill="{t["text"]}">']
    for i, ln in enumerate(lines):
        y = y0 + i * step
        if ln[0] == "header":
            out.append(f'<tspan x="{x0}" y="{y}">{escape(ln[1])} '
                       f'{"-" * (W - len(ln[1]) - 1)}</tspan>')
        elif ln[0] == "kv":
            k, dots, v = ln[1:]
            out.append(f'<tspan x="{x0}" y="{y}" class="d">. </tspan><tspan class="k">'
                       f'{escape(k)}</tspan>:<tspan class="d">{dots}</tspan>'
                       f'<tspan class="v">{escape(v)}</tspan>')
        elif ln[0] == "kv2":
            (k1, v1), (k2, v2) = ln[1], ln[2]
            right = f" | {k2}: {v2}"
            k, dots, v = kv_line(k1, v1, W - len(right))
            out.append(f'<tspan x="{x0}" y="{y}" class="d">. </tspan><tspan class="k">{k}</tspan>:'
                       f'<tspan class="d">{dots}</tspan><tspan class="v">{escape(v)}</tspan>'
                       f' | <tspan class="k">{k2}</tspan>: <tspan class="v">{escape(v2)}</tspan>')
    out += ["</text>", "</svg>"]
    return "\n".join(out) + "\n"


def main():
    stats = get_stats()
    lines = build_lines(stats)
    img = load_avatar()
    for theme in THEMES:
        art = ascii_art(img, THEMES[theme]["ramp"])
        with open(os.path.join(ROOT, f"{theme}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, lines, art))
    print("built dark_mode.svg + light_mode.svg", stats)


if __name__ == "__main__":
    main()

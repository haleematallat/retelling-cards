"""Fixed-rule YouTube sample: per finding, per query, first results in rank order.
long = default search, duration >= 300s; short = YouTube's own "<4 min" filter, duration <= 180s.
Keeps the first N per class that have an English transcript. Run: uv run --with yt-dlp --with youtube-transcript-api collect_youtube.py
"""
import json, subprocess, sys, time, urllib.parse, pathlib
from itertools import zip_longest
from youtube_transcript_api import YouTubeTranscriptApi

N = 20  # per finding per class, before relevance screening
OUT = pathlib.Path("data/youtube"); (OUT / "cache").mkdir(parents=True, exist_ok=True)
F = json.load(open("findings.json"))
FMT = "%(id)s\t%(duration)s\t%(view_count)s\t%(channel)s\t%(title)s"

def search(q, short):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + ("&sp=EgIYAQ%3D%3D" if short else "")
    r = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", "60", "--print", FMT, url], capture_output=True, text=True)
    rows = [l.split("\t", 4) for l in r.stdout.splitlines() if l.count("\t") == 4]
    return [dict(id=i, duration=float(d), views=int(v) if v.isdigit() else None, channel=c, title=t, query=q, rank=k)
            for k, (i, d, v, c, t) in enumerate(rows, 1) if d.replace(".", "").isdigit()]

api = YouTubeTranscriptApi()
for fid, f in F.items():
    for cls, short in (("long", False), ("short", True)):
        dest = OUT / f"{fid}_{cls}.json"
        if dest.exists() and json.load(open(dest)): continue
        lists = [search(q, short) for q in f["yt_queries"]]
        seen, kept = set(), []
        for v in (v for tup in zip_longest(*lists) for v in tup if v):  # interleave queries by rank
            if v["id"] in seen or len(kept) >= N: continue
            seen.add(v["id"])
            if (short and v["duration"] > 180) or (not short and v["duration"] < 300): continue
            cache = OUT / "cache" / (v["id"] + ".txt")  # so a rate-limit stop loses nothing
            try:
                if not cache.exists():
                    cache.write_text(" ".join(x.text for x in api.fetch(v["id"], languages=["en"]))); time.sleep(10)
                v["text"] = cache.read_text()
            except Exception as e:
                if "Blocked" in type(e).__name__:  # rate-limited: stop, keep nothing partial, resume later
                    sys.exit(f"blocked at {fid} {cls} after {len(kept)}; rerun later")
                print("skip", v["id"], type(e).__name__, file=sys.stderr); continue
            m = subprocess.run(["yt-dlp", "--skip-download", "--print", "%(channel_follower_count)s\t%(upload_date)s",
                                "https://www.youtube.com/watch?v=" + v["id"]], capture_output=True, text=True).stdout.strip().split("\t")
            v["subscribers"] = int(m[0]) if m and m[0].isdigit() else None
            v["upload_date"] = m[1] if len(m) > 1 else None
            kept.append(v)
        dest.write_text(json.dumps(kept, indent=1))
        print(fid, cls, len(kept), flush=True)

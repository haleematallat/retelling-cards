"""Fetch lab blog posts and news article text. Keeps, per finding, the first 15 distinct news articles (syndicated copies count once)
(in query/rank order) that return >= 250 words of extractable text.
Run: uv run --with trafilatura collect_text.py
"""
import json, pathlib, trafilatura

F = json.load(open("findings.json"))
D = pathlib.Path("data")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def grab(url):
    try:
        html = trafilatura.fetch_url(url)
        if not html: return None
        d = trafilatura.bare_extraction(html, with_metadata=True, favor_recall=True)
        d = d if isinstance(d, dict) else d.as_dict()
        return {"text": d.get("text") or "", "date": d.get("date"), "page_title": d.get("title")}
    except Exception as e:
        print("fail", url, type(e).__name__); return None

blogs = {}
for fid, f in F.items():
    g = grab(f["blog"]) or {"text": ""}
    blogs[fid] = [dict(url=f["blog"], **g)]
    print("blog", fid, len(g["text"].split()), "words")
(D / "blog.json").write_text(json.dumps(blogs, indent=1))

urls = {}
for p in sorted(D.glob("news_urls_*.json")):
    for fid, rows in json.load(open(p)).items(): urls.setdefault(fid, []).extend(rows)
news, log = {}, []
for fid, rows in urls.items():
    kept, seen = [], set()
    for r in sorted(rows, key=lambda r: (r["rank"], r["query"])):  # interleave queries by rank
        if len(kept) >= 15: break
        u = r["url"].split("?")[0]
        if u in seen: continue
        seen.add(u)
        g = grab(r["url"])
        key = " ".join(g["text"].split()[:60]) if g else None  # syndicated copies count once
        ok = bool(g) and len(g["text"].split()) >= 250 and key not in seen
        seen.add(key)
        log.append(dict(finding=fid, url=r["url"], kept=ok, words=len(g["text"].split()) if g else 0))
        if ok: kept.append({**r, **g})
    news[fid] = kept
    print("news", fid, len(kept), "of", len(rows))
(D / "news.json").write_text(json.dumps(news, indent=1))
(D / "news_fetch_log.json").write_text(json.dumps(log, indent=1))

"""News sample by rule: date-windowed Google News RSS, fixed queries, fixed exclusions, funnel logged.
Frame: "English-language items Google News surfaces for these queries in this window", not "the news".
Run: uv run --with googlenewsdecoder --with trafilatura collect_news_rss.py [finding ...]
Output: data/news_rss.json {finding: [article...]}, data/news_funnel.json
"""
import json, re, sys, time, html, pathlib, urllib.request, urllib.parse
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime
import trafilatura
from googlenewsdecoder import gnewsdecoder

D = pathlib.Path("data")
F = json.load(open("findings.json"))
DENY = {  # fixed before collection (PREREG.md)
    "lab": "anthropic.com openai.com apolloresearch.ai palisaderesearch.org metr.org apple.com redwoodresearch.org emergent-misalignment.com truthful.ai arxiv.org",
    "social": "reddit.com x.com twitter.com youtube.com facebook.com linkedin.com substack.com medium.com lesswrong.com alignmentforum.org threads.net bsky.app quora.com news.ycombinator.com",
    "aggregator": "msn.com yahoo.com aol.com flipboard.com newsbreak.com biztoc.com ground.news smartnews.com",
    "wire": "prnewswire.com businesswire.com globenewswire.com einpresswire.com accesswire.com",
}
DENY = {d: k for k, v in DENY.items() for d in v.split()}
STUB = re.compile(r"subscribe to (continue|read)|sign in to (continue|read)|enable javascript|already a subscriber|create a free account to|verify you are human|access denied", re.I)
dom = lambda u: re.sub(r"^www\.", "", urllib.parse.urlparse(u).netloc.lower())
denied = lambda d: next((k for x, k in DENY.items() if d == x or d.endswith("." + x)), None)
shingles = lambda t: {" ".join(w[i:i + 5]) for w in [re.findall(r"\w+", t.lower())] for i in range(max(1, len(w) - 4))}

cache = D / "news_rss_cache.json"
C = json.load(open(cache)) if cache.exists() else {"url": {}, "text": {}}

def rss(q, start, end):
    u = "https://news.google.com/rss/search?q=" + urllib.parse.quote(f"{q} after:{start} before:{end}") + "&hl=en-US&gl=US&ceid=US:en"
    s = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode()
    return re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?<source url=\"(.*?)\">(.*?)</source>", s, re.S)

def body(url):
    if url not in C["text"]:
        try:
            h = trafilatura.fetch_url(url)
            C["text"][url] = (trafilatura.extract(h, favor_recall=True) or "") if h else ""
        except Exception:
            C["text"][url] = ""
    return C["text"][url]

out = json.load(open(D / "news_rss.json")) if (D / "news_rss.json").exists() else {}
funnel = json.load(open(D / "news_funnel.json")) if (D / "news_funnel.json").exists() else {}
for fid in sys.argv[1:] or list(F):
    f = F[fid]; pub = date.fromisoformat(f["published"])
    items, seen = [], set()
    for qi, q in enumerate(f["news_queries"]):
        for rank, (title, link, pd, src_url, src) in enumerate(rss(q, pub - timedelta(days=1), pub + timedelta(days=91)), 1):
            if link in seen: continue
            seen.add(link); items.append(dict(query=qi, rank=rank, title=html.unescape(title), link=link, date=parsedate_to_datetime(pd).date().isoformat(), outlet=html.unescape(src), src_domain=dom(src_url)))
        time.sleep(2)
    fn = {"retrieved": len(items), "denied_domain": 0, "url_not_resolved": 0, "no_body_or_under_150_words": 0, "stub": 0, "near_duplicate": 0}
    kept = []
    for it in sorted(items, key=lambda x: (x["rank"], x["query"])):
        why = denied(it["src_domain"])
        if why: fn["denied_domain"] += 1; continue
        if it["link"] not in C["url"]:
            try: C["url"][it["link"]] = gnewsdecoder(it["link"], interval=1).get("decoded_url")
            except Exception: C["url"][it["link"]] = None
            cache.write_text(json.dumps(C))
        url = C["url"][it["link"]]
        if not url: fn["url_not_resolved"] += 1; continue
        text = body(url); n = len(text.split())
        if n < 150: fn["no_body_or_under_150_words"] += 1; continue
        if n < 300 and STUB.search(text): fn["stub"] += 1; continue
        sh = shingles(text)
        if any(len(sh & k["_sh"]) / len(sh | k["_sh"]) >= 0.8 for k in kept): fn["near_duplicate"] += 1; continue
        days = (date.fromisoformat(it["date"]) - pub).days
        title = re.sub(r"\s+-\s+" + re.escape(it["outlet"]) + r"$", "", it["title"])
        kept.append(dict(url=url, domain=dom(url), outlet=it["outlet"], title=title, date=it["date"], days=days, query=it["query"], rank=it["rank"], words=n, text=text, _sh=sh))
    cache.write_text(json.dumps(C))
    for k in kept: del k["_sh"]
    fn["kept"] = len(kept); fn["kept_0_30_days"] = sum(0 <= k["days"] <= 30 for k in kept)
    out[fid], funnel[fid] = kept, fn
    (D / "news_rss.json").write_text(json.dumps(out, indent=1)); (D / "news_funnel.json").write_text(json.dumps(funnel, indent=1))
    print(fid, fn, flush=True)

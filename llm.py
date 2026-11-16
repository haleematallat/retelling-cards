"""One tiny client for the non-Claude models: local Ollama and the Modal vLLM endpoints.
chat("ollama:qwen3.5:9b", prompt) / chat("modal:A", prompt). Modal endpoints are read from .modal_endpoints.json.
"""
import json, re, urllib.request, pathlib
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).parent


def _post(url, body, headers=None, timeout=900):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def chat(model, prompt, system=None, temperature=0.0, max_tokens=4000, retries=3):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    for attempt in range(retries):
        try:
            if model.startswith("ollama:"):
                r = _post("http://localhost:11434/api/chat", {"model": model[7:], "stream": False, "think": False, "messages": msgs,
                                                               "options": {"temperature": temperature, "num_ctx": 16384}})
                return r["message"]["content"]
            ep = json.load(open(ROOT / ".modal_endpoints.json"))[model.split(":", 1)[1]]
            r = _post(ep["base_url"].rstrip("/") + "/chat/completions",
                      {"model": ep["model"], "messages": msgs, "temperature": temperature, "max_tokens": max_tokens, **ep.get("extra", {})},
                      {"Authorization": "Bearer " + ep["api_key"]})
            return r["choices"][0]["message"]["content"] or ""
        except Exception as e:
            if attempt == retries - 1: raise
    return ""


def chat_json(model, prompt, check=lambda d: True, **kw):
    """Ask until the reply parses as JSON and passes check; returns None after 3 failures."""
    for _ in range(3):
        m = re.search(r"[\[{].*[\]}]", chat(model, prompt, **kw), re.S)
        try:
            d = json.loads(m.group(0))
            if check(d): return d
        except Exception:
            pass
    return None


def pmap(fn, items, workers=8):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))


if __name__ == "__main__":
    import sys
    print(chat(sys.argv[1], "Reply with the single word: ok"))

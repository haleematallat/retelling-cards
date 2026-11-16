"""Two OpenAI-compatible vLLM endpoints on Modal. Deploy: uvx modal deploy modal_serve.py::app_a (and ::app_b)
Needs Modal Secret 'retelling-vllm-key' with VLLM_API_KEY (never hard-code the key)."""
import subprocess
import modal

VLLM = "0.21.0"
MODELS = {
    "gpt-oss-120b": dict(hf="openai/gpt-oss-120b", gpu="T4", extra=["--max-model-len", "16384"]),
    "mistral-small-3-2": dict(hf="mistralai/Mistral-Small-3.2-24B-Instruct-2506", gpu="H100",
        extra=["--max-model-len", "16384", "--tokenizer-mode", "mistral", "--config-format", "mistral",
               "--load-format", "mistral", "--limit-mm-per-prompt", '{"image":0}']),
}

image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(f"vllm=={VLLM}", "huggingface_hub[hf_xet]")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)
hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
secret = modal.Secret.from_name("retelling-vllm-key")


def _serve(name):
    import os
    cfg = MODELS[name]
    cmd = ["vllm", "serve", cfg["hf"], "--served-model-name", name,
           "--host", "0.0.0.0", "--port", "8000", "--api-key", os.environ["VLLM_API_KEY"],
           "--gpu-memory-utilization", "0.92", "--max-num-seqs", "32", *cfg["extra"]]
    subprocess.Popen(cmd)


def _opts(name):
    return dict(image=image, gpu=MODELS[name]["gpu"], secrets=[secret], timeout=3600, scaledown_window=300,
                volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache})


app_a = modal.App("retelling-gpt-oss-120b")
app_b = modal.App("retelling-mistral-small-3-2")


@app_a.function(**_opts("gpt-oss-120b"))
@modal.concurrent(max_inputs=32)
@modal.web_server(port=8000, startup_timeout=1500)
def serve_a():
    _serve("gpt-oss-120b")


@app_b.function(**_opts("mistral-small-3-2"))
@modal.concurrent(max_inputs=32)
@modal.web_server(port=8000, startup_timeout=1500)
def serve_b():
    _serve("mistral-small-3-2")

"""ZDR Router (api.router.hello.ai) の /v1/videos で minimax-h3 を生成する ComfyUI ノード。生成は全て ZDR Router 側で行う。"""
import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

import av
import comfy.model_management
from aiohttp import web
from comfy_api.latest import InputImpl
from PIL import Image
from server import PromptServer

URL = "https://api.router.hello.ai/v1/videos"
# キーをウィジェットに置くとワークフロー JSON と mp4 のメタデータに平文で残るため、ファイルから読む
KEY_FILE = os.path.join(os.path.dirname(__file__), "api_key.txt")
ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"]
# ZDR Router が受け付ける参照画像の data URL の合計文字数の上限
MAX_DATA_URL_CHARS = 1_000_000


class ZDRRouterError(RuntimeError):
    def __init__(self, code, body):
        super().__init__(f"ZDR Router {code}: {body}")
        self.code = code


def _call(method, url, key, body=None):
    req = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise ZDRRouterError(e.code, e.read().decode(errors="replace")[:500]) from None


def _get(url, key):
    # 投入済みのジョブは課金が確定しているので、一時的な通信断や 5xx では諦めない
    while True:
        try:
            return _call("GET", url, key)
        except ZDRRouterError as e:
            if e.code < 500:
                raise
        except OSError:
            pass
        comfy.model_management.throw_exception_if_processing_interrupted()
        time.sleep(10)


def _last_frame_data_url(video):
    # 連結済みなら最後のクリップだけを開く。get_components() は全フレームを float テンソルにするので 2K×15 秒で十数 GB になる
    src = getattr(video, "videos", [video])[-1].get_stream_source()
    with av.open(src) as c:
        if c.duration:
            c.seek(max(c.duration - 2 * av.time_base, 0))
        frame = None
        for frame in c.decode(video=0):
            pass
        img = frame.to_image()
    # ZDR Router は参照画像を合計約 750KB までしか受けず、2 倍アップスケール済みの 2688×1536 だと超える。H3 は短辺 768 に縮めて使うので画質は落ちない
    s = 768 / min(img.size)
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    for quality in (95, 90, 85, 80, 70, 60):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        if len(url) < MAX_DATA_URL_CHARS:
            break
    return url


class ZDRRouterVideo:
    CATEGORY = "ZDR Router"
    RETURN_TYPES = ("VIDEO",)
    FUNCTION = "generate"
    DESCRIPTION = "ZDR Router の minimax-h3 で動画を生成する。extend_from をつなぐと、その動画の最終フレームから続きを生成して後ろに連結する。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "seconds": ("INT", {"default": 5, "min": 5, "max": 15}),
                "aspect_ratio": (ASPECT_RATIOS,),
            },
            "optional": {
                "extend_from": ("VIDEO", {"tooltip": "続きを作る元の動画。aspect_ratio は元と揃える"}),
            },
        }

    def generate(self, prompt, seconds, aspect_ratio, extend_from=None):
        with open(KEY_FILE) as f:
            key = f.read().strip()
        body = {"model": "minimax-h3", "prompt": prompt, "seconds": seconds, "aspect_ratio": aspect_ratio}
        if extend_from is not None:
            body["frame_images"] = [{"type": "first_frame", "image_url": _last_frame_data_url(extend_from)}]
        job = json.loads(_call("POST", URL, key, body))
        while job["status"] in ("pending", "in_progress"):
            comfy.model_management.throw_exception_if_processing_interrupted()
            time.sleep(10)
            job = json.loads(_get(f"{URL}/{job['id']}", key))
        if job["status"] != "completed":
            raise RuntimeError(f"ZDR Router の動画ジョブ {job['id']} が {job['status']} で終わりました: {job.get('error')}")
        clip = InputImpl.VideoFromFile(io.BytesIO(_get(f"{URL}/{job['id']}/content", key)))
        return (clip if extend_from is None else InputImpl.VideoFromList([extend_from, clip]),)


@PromptServer.instance.routes.get("/zdr_router/api_key")
async def _api_key_status(request):
    return web.json_response({"configured": os.path.isfile(KEY_FILE)})


@PromptServer.instance.routes.post("/zdr_router/api_key")
async def _save_api_key(request):
    key = (await request.json()).get("key")
    if not isinstance(key, str) or not key.strip() or any(c.isspace() for c in key.strip()):
        return web.json_response({"error": "invalid key"}, status=400)
    with os.fdopen(os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        f.write(key.strip())
    return web.json_response({"configured": True})


WEB_DIRECTORY = "./js"
NODE_CLASS_MAPPINGS = {"ZDRRouterVideo": ZDRRouterVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"ZDRRouterVideo": "ZDR Router Video (minimax-h3)"}

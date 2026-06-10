"""
星辰学院 - AI NPC 对话系统
Web 服务入口 (Flask App)
========================
提供 RESTful API 和 Web 界面。

启动方式: python src/app.py
访问地址: http://127.0.0.1:5001
"""

import os
import sys
import time
import json
import uuid
import shutil
import base64
import binascii
import logging
import re
from collections import defaultdict, deque

# 确保 src 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
import requests
from flask import Flask, Response, render_template, jsonify, request, stream_with_context
from flask_cors import CORS

from npc_engine import NPCManager


# ---------------------------------------------------------------------------
# 配置和日志
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
NPCS_DIR = os.path.join(PROJECT_ROOT, "npcs")
CUSTOM_NPCS_FILE = os.path.join(NPCS_DIR, "custom.json")
AVATARS_DIR = os.path.join(PROJECT_ROOT, "static", "avatars")
MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_MIME_TO_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "webp": "webp",
    "gif": "gif",
}


def load_config() -> dict:
    """加载服务配置。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


config = load_config()
server_config = config.get("server", {})

logging.basicConfig(
    level=getattr(logging, str(server_config.get("log_level", "INFO")).upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_custom_npcs() -> dict:
    """读取自定义 NPC 注册文件。"""
    if not os.path.exists(CUSTOM_NPCS_FILE):
        return {}
    try:
        with open(CUSTOM_NPCS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        logger.exception("读取自定义 NPC 失败")
        return {}


def save_custom_npcs(npcs: dict) -> None:
    """保存自定义 NPC 注册文件。"""
    os.makedirs(os.path.dirname(CUSTOM_NPCS_FILE), exist_ok=True)
    if not npcs:
        if os.path.exists(CUSTOM_NPCS_FILE):
            os.remove(CUSTOM_NPCS_FILE)
        return

    with open(CUSTOM_NPCS_FILE, "w", encoding="utf-8") as f:
        json.dump(npcs, f, ensure_ascii=False, indent=2)


def build_custom_soul(npc: dict) -> str:
    """生成自定义 NPC 的 SOUL.md。"""
    return "\n".join([
        f"# {npc['name']}",
        "",
        f"## 身份",
        npc.get("title") or npc["name"],
        "",
        "## 性格",
        npc["personality"],
        "",
        "## 背景故事",
        npc.get("backstory") or "暂无详细背景，请根据性格自然发挥。",
        "",
        "## 说话风格",
        npc.get("speech_style") or "自然、稳定地保持角色身份，用中文回应。",
        "",
        "## 对话原则",
        "- 始终保持该角色身份，不要打破第四面墙。",
        "- 结合玩家的好感度、记忆和上下文调整态度。",
        "- 回答要像真实游戏 NPC，而不是配置说明。",
    ])


def write_custom_soul(npc_id: str, npc: dict) -> None:
    """为自定义 NPC 写入角色设定文件。"""
    npc_dir = os.path.join(NPCS_DIR, npc_id)
    os.makedirs(npc_dir, exist_ok=True)
    soul_path = os.path.join(npc_dir, "SOUL.md")
    with open(soul_path, "w", encoding="utf-8") as f:
        f.write(build_custom_soul(npc))


def store_uploaded_avatar(npc_id: str, avatar_value: str) -> str:
    """保存 data URL 头像，普通 Emoji 则原样返回。"""
    avatar = (avatar_value or "").strip()
    if not avatar:
        return "✨"

    if not avatar.startswith("data:image/"):
        return avatar[:8]

    match = re.match(r"^data:image/(png|jpe?g|webp|gif);base64,([A-Za-z0-9+/=\s]+)$", avatar, re.IGNORECASE)
    if not match:
        raise ValueError("头像图片格式不正确")

    raw_ext = match.group(1).lower()
    ext = AVATAR_MIME_TO_EXT.get(raw_ext)
    if not ext:
        raise ValueError("头像仅支持 JPG、PNG、WEBP、GIF")

    try:
        image_bytes = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("头像图片数据无法读取") from exc

    if len(image_bytes) > MAX_AVATAR_BYTES:
        raise ValueError("头像图片不能超过 2MB")

    os.makedirs(AVATARS_DIR, exist_ok=True)
    avatar_filename = f"{npc_id}.{ext}"
    avatar_path = os.path.join(AVATARS_DIR, avatar_filename)
    with open(avatar_path, "wb") as f:
        f.write(image_bytes)

    return f"/static/avatars/{avatar_filename}"


def remove_uploaded_avatar(npc_id: str) -> None:
    """删除自定义 NPC 上传过的头像文件。"""
    for ext in set(AVATAR_MIME_TO_EXT.values()):
        avatar_path = os.path.abspath(os.path.join(AVATARS_DIR, f"{npc_id}.{ext}"))
        avatars_root = os.path.abspath(AVATARS_DIR)
        if avatar_path.startswith(avatars_root + os.sep) and os.path.exists(avatar_path):
            os.remove(avatar_path)


# ---------------------------------------------------------------------------
# App 初始化
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 开发阶段禁用静态文件缓存
CORS(app)

# 全局 NPC 管理器
manager = NPCManager(CONFIG_PATH)

# 简单内存限流：每个 IP 每分钟最多 N 次 API 请求
RATE_LIMIT_PER_MINUTE = int(server_config.get("rate_limit_per_minute", 30))
_rate_windows: dict[str, deque[float]] = defaultdict(deque)


@app.before_request
def rate_limit_api_requests():
    """对 API 请求进行分钟级限流。"""
    if not request.path.startswith("/api/") or request.path == "/api/health":
        return None

    now = time.monotonic()
    client_id = request.headers.get("X-Forwarded-For", request.remote_addr or "anonymous").split(",")[0].strip()
    window = _rate_windows[client_id]

    while window and now - window[0] >= 60:
        window.popleft()

    if len(window) >= RATE_LIMIT_PER_MINUTE:
        logger.warning("API 限流触发: client=%s path=%s", client_id, request.path)
        return jsonify({"success": False, "error": "请求过于频繁，请稍后再试"}), 429

    window.append(now)
    return None


# ---------------------------------------------------------------------------
# 页面路由
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """主页 - 对话界面"""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------

@app.route("/api/npcs", methods=["GET"])
def list_npcs():
    """获取所有 NPC 列表及其当前状态"""
    try:
        npcs = manager.list_npcs()
        return jsonify({"success": True, "npcs": npcs})
    except Exception as e:
        logger.exception("获取 NPC 列表失败")
        return jsonify({"success": False, "error": "学院人物暂时无法加载"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    return jsonify({
        "success": True,
        "status": "ok",
        "service": "star-academy-npc",
        "npc_count": len(manager.npc_registry),
        "timestamp": int(time.time()),
    })


@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    """测试 OpenAI 兼容 API 连接。"""
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "mock")
    if provider == "mock":
        return jsonify({"ok": True, "message": "Mock 模式可用"})

    base_url = str(data.get("base_url", "")).strip().rstrip("/")
    api_key = str(data.get("api_key", "")).strip()
    if not base_url:
        return jsonify({"ok": False, "error": "请填写 API 地址"})

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=10)
        if resp.status_code == 401:
            return jsonify({"ok": False, "error": "API 密钥无效"}), 200
        if resp.status_code >= 400:
            return jsonify({"ok": False, "error": f"HTTP {resp.status_code}"}), 200
        return jsonify({"ok": True})
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": str(e)[:100]}), 200


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """获取当前服务端默认 LLM 设置。"""
    return jsonify({"success": True, "settings": config.get("llm", {})})


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """更新当前进程内的默认 LLM 设置，不重写带注释的 config.yaml。"""
    data = request.get_json(silent=True) or {}
    allowed = {"provider", "model", "base_url", "api_key", "temperature", "max_tokens"}
    llm_cfg = config.setdefault("llm", {})
    for key in allowed:
        if key in data:
            llm_cfg[key] = data[key]
    manager.config["llm"] = llm_cfg
    return jsonify({"success": True, "settings": llm_cfg})


@app.route("/api/npcs/custom", methods=["POST"])
def create_custom_npc():
    """创建自定义 NPC。"""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:20]
    personality = str(data.get("personality", "")).strip()[:200]
    if not name or not personality:
        return jsonify({"ok": False, "error": "名称和性格描述为必填"}), 400

    title = str(data.get("title", "")).strip()[:30]
    npc_id = f"custom_{uuid.uuid4().hex[:8]}"
    try:
        avatar = store_uploaded_avatar(npc_id, str(data.get("avatar", "✨")))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    npc = {
        "id": npc_id,
        "name": name,
        "full_name": title or name,
        "title": title or "自定义角色",
        "avatar": avatar,
        "description": personality,
        "personality": personality,
        "backstory": str(data.get("backstory", "")).strip()[:500],
        "speech_style": str(data.get("speech_style", "")).strip()[:50],
        "dir": npc_id,
        "is_custom": True,
    }

    custom_npcs = load_custom_npcs()
    custom_npcs[npc_id] = npc
    save_custom_npcs(custom_npcs)
    write_custom_soul(npc_id, npc)
    manager.reload_registry()

    created = manager.get_npc(npc_id).get_npc_info()
    return jsonify({"ok": True, "success": True, "npc_id": npc_id, "npc": created})


@app.route("/api/npcs/<npc_id>/delete", methods=["POST"])
def delete_custom_npc(npc_id: str):
    """删除自定义 NPC。"""
    if not npc_id.startswith("custom_"):
        return jsonify({"ok": False, "error": "只能删除自定义角色"}), 400

    custom_npcs = load_custom_npcs()
    if npc_id not in custom_npcs:
        return jsonify({"ok": False, "error": "角色不存在"}), 404

    del custom_npcs[npc_id]
    save_custom_npcs(custom_npcs)

    npc_dir = os.path.abspath(os.path.join(NPCS_DIR, npc_id))
    npcs_root = os.path.abspath(NPCS_DIR)
    if npc_dir.startswith(npcs_root + os.sep) and os.path.isdir(npc_dir):
        shutil.rmtree(npc_dir)
    remove_uploaded_avatar(npc_id)

    manager.reload_registry()
    return jsonify({"ok": True, "success": True})


@app.route("/api/npcs/<npc_id>", methods=["GET"])
def get_npc(npc_id: str):
    """获取指定 NPC 的详细信息"""
    try:
        npc = manager.get_npc(npc_id)
        return jsonify({"success": True, "npc": npc.get_npc_info()})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("获取 NPC 详情失败: npc_id=%s", npc_id)
        return jsonify({"success": False, "error": "人物信息暂时无法加载"}), 500


@app.route("/api/npcs/<npc_id>/chat", methods=["POST"])
def chat_with_npc(npc_id: str):
    """与指定 NPC 对话"""
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"success": False, "error": "请提供 message 字段"}), 400

        message = data["message"].strip()
        if not message:
            return jsonify({"success": False, "error": "消息不能为空"}), 400

        if len(message) > 500:
            return jsonify({"success": False, "error": "消息过长（最多 500 字）"}), 400

        settings = data.get("settings") if isinstance(data.get("settings"), dict) else None
        result = manager.chat(npc_id, message, settings)
        return jsonify({"success": True, **result})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("NPC 对话失败: npc_id=%s", npc_id)
        return jsonify({"success": False, "error": "网络波动，请稍后再试"}), 500


@app.route("/api/npcs/<npc_id>/chat/stream", methods=["POST"])
def chat_with_npc_stream(npc_id: str):
    """与指定 NPC 流式对话（SSE）。"""
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "请提供 message 字段"}), 400

    message = str(data["message"]).strip()
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"}), 400

    if len(message) > 500:
        return jsonify({"success": False, "error": "消息过长（最多 500 字）"}), 400

    settings = data.get("settings") if isinstance(data.get("settings"), dict) else None

    def send_event(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def generate():
        try:
            for event in manager.chat_events(npc_id, message, settings):
                yield send_event(event)
        except ValueError as exc:
            yield send_event({"type": "error", "message": str(exc)})
        except Exception:
            logger.exception("NPC 流式对话失败: npc_id=%s", npc_id)
            yield send_event({"type": "error", "message": "网络波动，请稍后再试"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/npcs/<npc_id>/reset", methods=["POST"])
def reset_npc(npc_id: str):
    """重置指定 NPC 的记忆和好感度"""
    try:
        manager.reset_npc(npc_id)
        return jsonify({"success": True, "message": f"{npc_id} 已重置"})
    except Exception as e:
        logger.exception("重置 NPC 失败: npc_id=%s", npc_id)
        return jsonify({"success": False, "error": "重置失败，请稍后再试"}), 500


@app.route("/api/npcs/<npc_id>/session", methods=["POST"])
def start_session(npc_id: str):
    """开始新的对话会话"""
    try:
        manager.start_session(npc_id)
        npc = manager.get_npc(npc_id)
        return jsonify({"success": True, "npc": npc.get_npc_info()})
    except Exception as e:
        logger.exception("新会话启动失败: npc_id=%s", npc_id)
        return jsonify({"success": False, "error": "新会话暂时无法开始"}), 500


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 5001)
    debug = server_cfg.get("debug", True)

    logger.info("星辰学院 - AI NPC 对话系统启动: http://%s:%s", host, port)

    app.run(host=host, port=port, debug=debug)

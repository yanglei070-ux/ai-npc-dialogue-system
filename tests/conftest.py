import os
import sys

import pytest
import yaml


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.insert(0, SRC_DIR)


@pytest.fixture
def temp_npc_dir(tmp_path):
    npc_dir = tmp_path / "npc"
    npc_dir.mkdir()
    return npc_dir


@pytest.fixture
def app(tmp_path, monkeypatch):
    import app as app_module
    from npc_engine import NPCManager

    project_root = tmp_path
    npcs_dir = project_root / "npcs"
    avatars_dir = project_root / "static" / "avatars"
    npcs_dir.mkdir()
    avatars_dir.mkdir(parents=True)

    for npc_id, name in [("eileen", "艾琳教授"), ("toms", "老汤姆"), ("shadow", "影")]:
        npc_dir = npcs_dir / npc_id
        npc_dir.mkdir()
        (npc_dir / "SOUL.md").write_text(f"# {name}\n请用中文保持角色扮演。", encoding="utf-8")

    config = {
        "llm": {
            "provider": "mock",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "temperature": 0.85,
            "max_tokens": 512,
            "mock": {"enabled": True},
        },
        "game": {
            "max_memory_turns": 10,
            "max_fact_count": 20,
            "affinity": {
                "initial": 50,
                "min": 0,
                "max": 100,
                "tiers": {
                    "hostile": [0, 20],
                    "cold": [21, 40],
                    "neutral": [41, 60],
                    "warm": [61, 80],
                    "bonded": [81, 100],
                },
            },
        },
        "npcs": {
            "eileen": {"id": "eileen", "name": "艾琳教授", "title": "魔药课教授", "avatar": "E", "description": "严厉", "dir": "eileen"},
            "toms": {"id": "toms", "name": "老汤姆", "title": "图书馆管理员", "avatar": "T", "description": "温和", "dir": "toms"},
            "shadow": {"id": "shadow", "name": "影", "title": "神秘学生", "avatar": "S", "description": "冷漠", "dir": "shadow"},
        },
        "server": {"host": "127.0.0.1", "port": 5001, "debug": False, "rate_limit_per_minute": 1000},
    }
    config_path = project_root / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(app_module, "NPCS_DIR", str(npcs_dir))
    monkeypatch.setattr(app_module, "CUSTOM_NPCS_FILE", str(npcs_dir / "custom.json"))
    monkeypatch.setattr(app_module, "AVATARS_DIR", str(avatars_dir))
    app_module.config.clear()
    app_module.config.update(config)
    app_module.manager = NPCManager(str(config_path))
    app_module.RATE_LIMIT_PER_MINUTE = 1000
    app_module._rate_windows.clear()
    app_module.app.config["TESTING"] = True
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()

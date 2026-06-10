import json


def test_get_npcs(client):
    response = client.get("/api/npcs")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert len(payload["npcs"]) == 3


def test_post_chat(client):
    response = client.post("/api/npcs/eileen/chat", json={"message": "谢谢教授"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["response"]
    assert "affinity" in payload


def test_post_chat_stream(client):
    response = client.post("/api/npcs/eileen/chat/stream", json={"message": "我想学习魔药"})
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "text/event-stream" in response.content_type
    assert '"type": "token"' in body
    assert '"type": "done"' in body


def test_create_and_delete_custom_npc(client):
    created = client.post("/api/npcs/custom", json={
        "name": "测试角色",
        "personality": "温和可靠",
        "title": "测试导师",
        "avatar": "*",
    }).get_json()
    assert created["ok"] is True
    npc_id = created["npc_id"]

    deleted = client.post(f"/api/npcs/{npc_id}/delete").get_json()
    assert deleted["ok"] is True


def test_get_settings(client):
    response = client.get("/api/settings")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["settings"]["provider"] == "mock"


def test_post_settings(client):
    response = client.post("/api/settings", json={"provider": "mock", "model": "test-model"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["settings"]["model"] == "test-model"

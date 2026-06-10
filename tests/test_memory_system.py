from memory_system import MemorySystem


def test_add_message_records_history(temp_npc_dir):
    memory = MemorySystem(str(temp_npc_dir))
    memory.add_message("player", "我叫小明")
    history = memory.get_conversation_history()
    assert history[-1]["role"] == "player"
    assert history[-1]["content"] == "我叫小明"


def test_add_fact_deduplicates_similar_fact(temp_npc_dir):
    memory = MemorySystem(str(temp_npc_dir))
    memory.add_fact("玩家名叫「小明」")
    memory.add_fact("玩家名叫「小红」")
    assert len(memory.get_facts()) == 1
    assert "小红" in memory.get_facts()[0]


def test_get_recent_history_limits_turns(temp_npc_dir):
    memory = MemorySystem(str(temp_npc_dir), max_turns=5)
    for idx in range(4):
        memory.add_message("player", f"p{idx}")
        memory.add_message("npc", f"n{idx}")
    assert len(memory.get_conversation_history(2)) == 4
    assert memory.get_conversation_history(2)[0]["content"] == "p2"


def test_reset_clears_memory(temp_npc_dir):
    memory = MemorySystem(str(temp_npc_dir))
    memory.add_message("player", "hello")
    memory.add_fact("玩家喜欢魔药")
    memory.reset()
    assert memory.get_conversation_history() == []
    assert memory.get_facts() == []


def test_serialization_reloads_existing_file(temp_npc_dir):
    memory = MemorySystem(str(temp_npc_dir))
    memory.add_message("player", "你好")
    memory.add_fact("玩家来自星辰学院")
    reloaded = MemorySystem(str(temp_npc_dir))
    assert reloaded.get_conversation_history()[0]["content"] == "你好"
    assert reloaded.get_facts() == ["玩家来自星辰学院"]

from affinity_system import AffinitySystem


def test_analyze_and_update_positive_message(temp_npc_dir):
    affinity = AffinitySystem("eileen", str(temp_npc_dir), initial=50)
    result = affinity.analyze_and_update("谢谢教授，我想认真学习魔药")
    assert result["delta"] > 0
    assert affinity.value > 50


def test_tier_calculation_boundary(temp_npc_dir):
    affinity = AffinitySystem("shadow", str(temp_npc_dir), initial=20)
    assert affinity.get_tier()["name"] == "hostile"
    affinity.change(1, "boundary")
    assert affinity.get_tier()["name"] == "cold"


def test_format_for_prompt_contains_current_value(temp_npc_dir):
    affinity = AffinitySystem("toms", str(temp_npc_dir), initial=65)
    prompt = affinity.format_for_prompt()
    assert "65/100" in prompt
    assert "好感度" in prompt


def test_change_clamps_to_bounds(temp_npc_dir):
    affinity = AffinitySystem("eileen", str(temp_npc_dir), initial=50, min_val=0, max_val=100)
    affinity.change(999, "too high")
    assert affinity.value == 100
    affinity.change(-999, "too low")
    assert affinity.value == 0

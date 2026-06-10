"""
好感度系统 (Affinity System)
============================
管理 NPC 对玩家的好感度，支持：
- 好感度增减（基于关键词和对话内容分析）
- 好感度等级划分
- 态度描述生成
- 对话选项对好感度的影响
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# 默认好感度等级定义
DEFAULT_TIERS = {
    "hostile":  {"range": [0,  20], "label": "敌对", "emoji": "💢"},
    "cold":     {"range": [21, 40], "label": "冷淡", "emoji": "❄️"},
    "neutral":  {"range": [41, 60], "label": "中立", "emoji": "😐"},
    "warm":     {"range": [61, 80], "label": "友好", "emoji": "😊"},
    "bonded":   {"range": [81, 100], "label": "羁绊", "emoji": "💫"},
}

# 关键词好感度加成（正面）
POSITIVE_KEYWORDS = [
    ("请", 1), ("谢谢", 2), ("感谢", 2), ("厉害", 1), ("佩服", 2),
    ("帮忙", 1), ("请教", 2), ("学习", 1), ("努力", 1), ("练习", 1),
    ("有趣", 1), ("好奇", 1), ("想知道", 2), ("对不起", 2), ("抱歉", 2),
    ("关心", 1), ("朋友", 2), ("信任", 2), ("陪你", 3),
    ("好看", 1), ("了不起", 2), ("尊敬", 2),
]

# 关键词好感度扣减（负面）
NEGATIVE_KEYWORDS = [
    ("笨", -2), ("蠢", -3), ("无聊", -2), ("讨厌", -2),
    ("滚", -3), ("闭嘴", -3), ("垃圾", -3), ("废物", -3),
    ("不在乎", -2), ("随便", -1), ("无所谓", -1),
    ("威胁", -3), ("强迫", -2), ("命令", -2),
]

# NPC 专属好感度关键词
NPC_SPECIFIC_KEYWORDS = {
    "eileen": {
        "positive": [("魔药", 2), ("坩埚", 1), ("配方", 2), ("材料", 1), ("调配", 2)],
        "negative": [("爆炸", -1), ("偷懒", -2), ("不想学", -2)],
    },
    "toms": {
        "positive": [("书", 1), ("阅读", 2), ("历史", 2), ("知识", 1), ("故事", 1)],
        "negative": [("撕书", -5), ("书没用", -3), ("不想看", -1)],
    },
    "shadow": {
        "positive": [("等你", 2), ("陪你", 3), ("没事", 1), ("理解", 2), ("不介意", 2)],
        "negative": [("你是谁", -1), ("追问", -2), ("跟踪", -3), ("逼问", -3)],
    },
}


class AffinitySystem:
    """好感度管理器"""

    def __init__(self, npc_id: str, data_dir: str,
                 initial: int = 50, min_val: int = 0, max_val: int = 100,
                 tiers: Optional[dict] = None):
        """
        初始好好感度系统。

        Args:
            npc_id: NPC 标识符（eileen / toms / shadow）
            data_dir: NPC 数据目录
            initial: 初始好感度
            min_val: 好感度下限
            max_val: 好感度上限
            tiers: 好感度等级定义
        """
        self.npc_id = npc_id
        self.data_dir = data_dir
        self.initial = initial
        self.min_val = min_val
        self.max_val = max_val
        self.tiers = self._normalize_tiers(tiers) if tiers else DEFAULT_TIERS
        self.affinity_file = os.path.join(data_dir, "affinity.json")
        self._data = self._load()

    @staticmethod
    def _normalize_tiers(raw_tiers: dict) -> dict:
        """
        将 config.yaml 中的简化 tiers 格式转换为完整格式。

        config.yaml 格式:  {"hostile": [0, 20], "cold": [21, 40], ...}
        完整格式:         {"hostile": {"range": [0, 20], "label": "敌对", "emoji": "💢"}, ...}
        """
        labels = {"hostile": "敌对", "cold": "冷淡", "neutral": "中立", "warm": "友好", "bonded": "羁绊"}
        emojis = {"hostile": "💢", "cold": "❄️", "neutral": "😐", "warm": "😊", "bonded": "💫"}

        normalized = {}
        for name, value in raw_tiers.items():
            if isinstance(value, list):
                # 简化格式: hostile: [0, 20]
                normalized[name] = {
                    "range": value,
                    "label": labels.get(name, name),
                    "emoji": emojis.get(name, "❓"),
                }
            elif isinstance(value, dict):
                # 已经是完整格式
                normalized[name] = value
            else:
                continue
        return normalized or DEFAULT_TIERS

    def _load(self) -> dict:
        """从磁盘加载好感度数据"""
        if os.path.exists(self.affinity_file):
            try:
                with open(self.affinity_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"value": self.initial, "history": []}

    def save(self) -> None:
        """持久化好感度数据"""
        os.makedirs(os.path.dirname(self.affinity_file), exist_ok=True)
        with open(self.affinity_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def reset(self) -> None:
        """重置好感度到初始值"""
        self._data = {"value": self.initial, "history": []}
        self.save()

    # ------------------------------------------------------------------
    # 好感度查询
    # ------------------------------------------------------------------

    @property
    def value(self) -> int:
        """当前好感度值"""
        return self._data.get("value", self.initial)

    def get_tier(self) -> dict:
        """获取当前好感度等级信息"""
        v = self.value
        for tier_name, tier_info in self.tiers.items():
            lo, hi = tier_info["range"]
            if lo <= v <= hi:
                return {
                    "name": tier_name,
                    "label": tier_info["label"],
                    "emoji": tier_info["emoji"],
                    "value": v,
                    "range": tier_info["range"],
                }
        # fallback
        return {
            "name": "neutral",
            "label": "中立",
            "emoji": "😐",
            "value": v,
            "range": [41, 60],
        }

    def get_attitude_description(self) -> str:
        """根据当前好感度生成态度描述"""
        tier = self.get_tier()
        descriptions = {
            "hostile": f"{tier['emoji']} 当前好感度: {self.value}/100（{tier['label']}）\n对方对你充满敌意，不愿意与你交流。",
            "cold": f"{tier['emoji']} 当前好感度: {self.value}/100（{tier['label']}）\n对方对你比较冷淡，但勉强愿意交流。",
            "neutral": f"{tier['emoji']} 当前好感度: {self.value}/100（{tier['label']}）\n对方以正常态度对待你。",
            "warm": f"{tier['emoji']} 当前好感度: {self.value}/100（{tier['label']}）\n对方把你当作朋友，态度亲切。",
            "bonded": f"{tier['emoji']} 当前好感度: {self.value}/100（{tier['label']}）\n对方与你建立了深厚的羁绊，愿意分享秘密。",
        }
        return descriptions.get(tier["name"], descriptions["neutral"])

    # ------------------------------------------------------------------
    # 好感度修改
    # ------------------------------------------------------------------

    def change(self, delta: int, reason: str = "") -> int:
        """
        修改好感度。

        Args:
            delta: 变化量（正数增加，负数减少）
            reason: 变化原因

        Returns:
            变化后的好感度值
        """
        old_value = self.value
        new_value = max(self.min_val, min(self.max_val, old_value + delta))
        self._data["value"] = new_value

        # 记录变化历史
        self._data.setdefault("history", []).append({
            "delta": delta,
            "old": old_value,
            "new": new_value,
            "reason": reason,
        })

        # 只保留最近 50 条记录
        if len(self._data["history"]) > 50:
            self._data["history"] = self._data["history"][-50:]

        self.save()
        return new_value

    def _keyword_analysis(self, player_message: str) -> tuple[int, list[str]]:
        """
        使用关键词分析玩家消息，返回 (delta, reasons)。
        """
        delta = 0
        reasons = []

        # 检查通用正面关键词
        msg_lower = player_message.lower()
        for keyword, score in POSITIVE_KEYWORDS:
            if keyword in msg_lower:
                delta += score
                reasons.append(f"+{score}（{keyword}）")

        # 检查通用负面关键词
        for keyword, score in NEGATIVE_KEYWORDS:
            if keyword in msg_lower:
                delta += score  # score 已经是负数
                reasons.append(f"{score}（{keyword}）")

        # 检查 NPC 专属关键词
        npc_keywords = NPC_SPECIFIC_KEYWORDS.get(self.npc_id, {})
        for keyword, score in npc_keywords.get("positive", []):
            if keyword in msg_lower:
                delta += score
                reasons.append(f"+{score}（{keyword}·专属）")

        for keyword, score in npc_keywords.get("negative", []):
            if keyword in msg_lower:
                delta += score
                reasons.append(f"{score}（{keyword}·专属）")

        # 消息长度加成（认真写长消息的玩家获得少量好感加成）
        if len(player_message) > 50:
            delta += 1
            reasons.append("+1（认真对话）")

        # 限制单次变化幅度
        delta = max(-10, min(10, delta))

        if delta == 0:
            delta = 0  # 无变化
            reasons.append("无明显变化")

        return delta, reasons

    def analyze_and_update(self, player_message: str, llm_config: Optional[dict] = None) -> dict:
        """
        分析玩家消息并自动调整好感度。

        Args:
            player_message: 玩家发送的消息
            llm_config: 可选 LLM 配置，用于更精细的情感分析

        Returns:
            {"delta": 变化量, "reason": 原因, "new_value": 新值}
        """
        keyword_delta, keyword_reasons = self._keyword_analysis(player_message)
        delta = keyword_delta
        reasons = keyword_reasons

        if self._can_use_llm_analysis(llm_config):
            try:
                llm_delta, llm_reason = self._llm_sentiment_analysis(player_message, llm_config or {})
                delta = int(round(llm_delta * 0.7 + keyword_delta * 0.3))
                reasons = [f"LLM分析：{llm_reason}", f"关键词参考：{', '.join(keyword_reasons)}"]
            except Exception:
                logger.debug("LLM 好感度分析失败，已降级为关键词分析: npc_id=%s", self.npc_id, exc_info=True)

        delta = max(-10, min(10, delta))
        reason_str = ", ".join(reasons) if reasons else "无变化"
        new_value = self.change(delta, reason_str)

        return {
            "delta": delta,
            "reason": reason_str,
            "new_value": new_value,
        }

    def _can_use_llm_analysis(self, llm_config: Optional[dict]) -> bool:
        """判断是否具备调用 LLM 做好感度分析的条件。"""
        if not llm_config:
            return False
        provider = llm_config.get("provider", "mock")
        if provider == "mock":
            return False
        return bool(llm_config.get("api_key") or os.environ.get("OPENAI_API_KEY") or provider == "ollama")

    def _llm_sentiment_analysis(self, player_message: str, llm_config: dict) -> tuple[int, str]:
        """使用 OpenAI 兼容 API 分析好感度变化。"""
        from openai import OpenAI

        provider = llm_config.get("provider", "openai")
        base_url = llm_config.get("base_url") or "https://api.openai.com/v1"
        model = llm_config.get("model") or "gpt-4o-mini"
        api_key = llm_config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        if provider == "ollama":
            api_key = api_key or "ollama"

        client = OpenAI(api_key=api_key, base_url=base_url)
        current = self.get_summary()
        prompt = f"""分析玩家消息对 NPC 好感度的影响。

NPC 当前好感度：{current['value']}/100（{current['tier']}）
玩家消息：{json.dumps(player_message, ensure_ascii=False)}

请评估这条消息对好感度的影响，输出 JSON：
{{"delta": 整数(-5到+5), "reason": "简短原因"}}

评分标准：
- +3 到 +5：明确的善意、赞美、关心、帮助
- +1 到 +2：友好的日常交流
- 0：中性或无明显情绪
- -1 到 -2：轻微冷淡、敷衍或冒犯
- -3 到 -5：明确恶意、侮辱、威胁、背叛

只输出 JSON。"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        delta = max(-5, min(5, int(result.get("delta", 0))))
        reason = str(result.get("reason") or "情感倾向分析").strip()
        return delta, reason

    # ------------------------------------------------------------------
    # 对话选项生成
    # ------------------------------------------------------------------

    def get_suggested_responses(self) -> list[dict]:
        """
        根据当前好感度生成建议的对话选项。
        每个选项包含文本和预期好感度变化。
        """
        tier = self.get_tier()["name"]

        # 通用选项
        options = [
            {"text": "你好，我想和你聊聊。", "effect": "+1~2", "type": "neutral"},
            {"text": "谢谢你的帮助！", "effect": "+2~3", "type": "positive"},
        ]

        # 根据 NPC 和好感度添加专属选项
        if self.npc_id == "eileen":
            if tier in ("neutral", "warm", "bonded"):
                options.append({
                    "text": "教授，我对魔药学非常感兴趣，能教我更多吗？",
                    "effect": "+3~5",
                    "type": "positive",
                })
            if tier in ("warm", "bonded"):
                options.append({
                    "text": "教授，您左眼的伤疤……是怎么来的？",
                    "effect": "???",
                    "type": "special",
                })

        elif self.npc_id == "toms":
            options.append({
                "text": "汤姆爷爷，能给我推荐一些书吗？",
                "effect": "+2~3",
                "type": "positive",
            })
            if tier in ("warm", "bonded"):
                options.append({
                    "text": "您认识那个叫「影」的学生吗？",
                    "effect": "???",
                    "type": "special",
                })

        elif self.npc_id == "shadow":
            if tier in ("cold", "neutral"):
                options.append({
                    "text": "你总是独处吗？我可以坐在这里吗？",
                    "effect": "+2~4",
                    "type": "positive",
                })
            if tier in ("warm", "bonded"):
                options.append({
                    "text": "影，你脖子后面那个印记是什么？",
                    "effect": "???",
                    "type": "special",
                })
            options.append({
                "text": "我只是路过而已。",
                "effect": "-1~0",
                "type": "neutral",
            })

        return options

    # ------------------------------------------------------------------
    # Prompt 上下文
    # ------------------------------------------------------------------

    def format_for_prompt(self) -> str:
        """生成供 LLM prompt 使用的好感度描述"""
        tier = self.get_tier()
        return (
            f"【当前好感度】{self.value}/100（{tier['label']}）\n"
            f"请根据好感度等级调整你的态度：\n"
            f"  - 好感度低时更加冷淡和防备\n"
            f"  - 好感度高时更加亲切和信任\n"
            f"  - 好感度极高时可以透露一些秘密或深层信息"
        )

    def get_summary(self) -> dict:
        """获取好感度摘要（用于 API 返回）"""
        tier = self.get_tier()
        return {
            "value": self.value,
            "tier": tier["name"],
            "tier_label": tier["label"],
            "tier_emoji": tier["emoji"],
            "description": self.get_attitude_description(),
        }

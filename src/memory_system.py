"""
记忆系统 (Memory System)
========================
管理 NPC 的对话记忆和玩家事实记录。
每个 NPC 独立存储记忆，支持：
- 对话历史（最近 N 轮）
- 玩家关键事实提取与存储
- 上次交互时间追踪
- 会话计数
"""

import json
import os
from datetime import datetime
from typing import Optional


class MemorySystem:
    """NPC 记忆管理器"""

    def __init__(self, npc_dir: str, max_turns: int = 10, max_facts: int = 20):
        """
        初始化记忆系统。

        Args:
            npc_dir: NPC 数据目录（如 npcs/eileen/）
            max_turns: 保留最近多少轮对话
            max_facts: 最多保存多少条玩家事实
        """
        self.npc_dir = npc_dir
        self.max_turns = max_turns
        self.max_facts = max_facts
        self.memory_file = os.path.join(npc_dir, "memory.json")
        self._memory = self._load_memory()

    def _load_memory(self) -> dict:
        """从磁盘加载记忆数据"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return self._normalize_memory(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_memory()

    def _default_memory(self) -> dict:
        """返回默认的空记忆结构"""
        return {
            "conversation_history": [],
            "player_facts": [],
            "last_interaction": None,
            "total_interactions": 0,
            "session_count": 0,
        }

    def _normalize_memory(self, raw: dict) -> dict:
        """兼容旧版/精简版记忆 JSON 字段。"""
        memory = self._default_memory()
        if not isinstance(raw, dict):
            return memory

        memory["conversation_history"] = raw.get("conversation_history") or raw.get("messages") or []
        memory["player_facts"] = raw.get("player_facts") or raw.get("facts") or []
        memory["last_interaction"] = raw.get("last_interaction")
        memory["total_interactions"] = raw.get("total_interactions", len(memory["conversation_history"]))
        memory["session_count"] = raw.get("session_count", 0)
        return memory

    def save(self) -> None:
        """将记忆持久化到磁盘"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._memory, f, ensure_ascii=False, indent=2)

    def reset(self) -> None:
        """清空所有记忆"""
        self._memory = self._default_memory()
        self.save()

    # ------------------------------------------------------------------
    # 对话历史
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        """
        添加一条对话记录。

        Args:
            role: "player" 或 "npc"
            content: 消息内容
        """
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        self._memory["conversation_history"].append(entry)
        self._memory["total_interactions"] += 1

        # 保留最近 max_turns * 2 条消息（每轮包含 player + npc 各一条）
        max_messages = self.max_turns * 2
        if len(self._memory["conversation_history"]) > max_messages:
            self._memory["conversation_history"] = self._memory[
                "conversation_history"
            ][-max_messages:]

        self._memory["last_interaction"] = datetime.now().isoformat()
        self.save()

    def get_conversation_history(self, n: Optional[int] = None) -> list[dict]:
        """
        获取最近 n 轮对话历史。

        Args:
            n: 获取最近 n 轮（每轮 = player + npc），None 表示全部

        Returns:
            对话历史列表
        """
        history = self._memory["conversation_history"]
        if n is not None:
            history = history[-(n * 2):]
        return history

    def format_history_for_prompt(self, n: Optional[int] = None) -> str:
        """将对话历史格式化为 prompt 可用的字符串"""
        history = self.get_conversation_history(n)
        if not history:
            return "（这是你们的第一次对话）"

        lines = ["【对话历史】"]
        for entry in history:
            speaker = "玩家" if entry["role"] == "player" else "NPC"
            lines.append(f"  {speaker}: {entry['content']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 玩家事实
    # ------------------------------------------------------------------

    def add_fact(self, fact: str) -> None:
        """
        记录一条关于玩家的事实。

        Args:
            fact: 事实描述（如 "玩家名叫小明"）
        """
        facts = self._memory["player_facts"]

        # 去重：如果已有类似的事实，更新它
        for i, existing in enumerate(facts):
            if self._facts_are_similar(existing, fact):
                facts[i] = fact
                self.save()
                return

        facts.append(fact)
        if len(facts) > self.max_facts:
            facts = facts[-self.max_facts:]
        self._memory["player_facts"] = facts
        self.save()

    def _facts_are_similar(self, a: str, b: str) -> bool:
        """简单的相似度判断：如果前半部分相同则认为是同类事实"""
        # 用于更新同名事实，比如 "玩家名叫小明" -> "玩家名叫大明"
        a_prefix = a[:len(a) // 2] if len(a) > 4 else a
        b_prefix = b[:len(b) // 2] if len(b) > 4 else b
        return a_prefix == b_prefix

    def get_facts(self) -> list[str]:
        """获取所有已记录的玩家事实"""
        return self._memory.get("player_facts", [])

    def format_facts_for_prompt(self) -> str:
        """将玩家事实格式化为 prompt 可用的字符串"""
        facts = self.get_facts()
        if not facts:
            return "（你还不了解这个玩家）"

        lines = ["【你对玩家的了解】"]
        for fact in facts:
            lines.append(f"  - {fact}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 会话信息
    # ------------------------------------------------------------------

    def get_session_count(self) -> int:
        """获取总会话次数"""
        return self._memory.get("session_count", 0)

    def increment_session(self) -> None:
        """递增会话计数"""
        self._memory["session_count"] = self._memory.get("session_count", 0) + 1
        self.save()

    def get_last_interaction(self) -> Optional[str]:
        """获取上次交互时间"""
        return self._memory.get("last_interaction")

    def is_returning_player(self) -> bool:
        """判断玩家是否是回访（之前有过交互）"""
        return self._memory.get("total_interactions", 0) > 0

    def get_summary(self) -> dict:
        """获取记忆摘要（用于 API 返回）"""
        return {
            "total_interactions": self._memory.get("total_interactions", 0),
            "session_count": self._memory.get("session_count", 0),
            "facts_count": len(self._memory.get("player_facts", [])),
            "last_interaction": self._memory.get("last_interaction"),
            "conversation_turns": len(self._memory.get("conversation_history", [])) // 2,
        }

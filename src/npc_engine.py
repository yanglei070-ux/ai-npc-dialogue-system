"""
NPC 核心引擎 (NPC Engine)
=========================
整合 SOUL.md 性格配置、记忆系统、好感度系统和 LLM 调用，
为每个 NPC 提供完整的对话能力。
"""

import os
import re
import json
import yaml
import random
import logging
from typing import Optional

from memory_system import MemorySystem
from affinity_system import AffinitySystem


logger = logging.getLogger(__name__)


def _normalize_npc_info(npc_id: str, raw_info: dict) -> dict:
    """补齐 NPC 配置字段。"""
    info = {**raw_info}
    info["id"] = info.get("id") or npc_id
    info["dir"] = info.get("dir") or info["id"]
    info.setdefault("name", info["id"])
    info.setdefault("full_name", info["name"])
    info.setdefault("title", "学院人物")
    info.setdefault("avatar", "✦")
    info.setdefault("description", "星辰学院中的神秘人物。")
    return info


def _load_custom_registry(project_root: str) -> dict[str, dict]:
    """加载用户创建的自定义 NPC。"""
    custom_file = os.path.join(project_root, "npcs", "custom.json")
    if not os.path.exists(custom_file):
        return {}

    try:
        with open(custom_file, "r", encoding="utf-8") as f:
            raw_custom = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("自定义 NPC 文件读取失败: %s", custom_file)
        return {}

    registry: dict[str, dict] = {}
    for npc_id, raw_info in raw_custom.items():
        if not npc_id or not isinstance(raw_info, dict):
            continue
        info = _normalize_npc_info(npc_id, raw_info)
        info["is_custom"] = True
        info["dir"] = info["id"]
        registry[info["id"]] = info
    return registry


def build_npc_registry(config: dict, project_root: Optional[str] = None) -> dict[str, dict]:
    """从 config.yaml 构建 NPC 注册表。"""
    raw_npcs = config.get("npcs")
    if not raw_npcs:
        logger.warning("config.yaml 未配置 npcs，NPC 列表为空")
        registry = {}
    elif isinstance(raw_npcs, list):
        items = [(item.get("id"), item) for item in raw_npcs if isinstance(item, dict)]
        registry = {}
        for npc_id, raw_info in items:
            if npc_id and isinstance(raw_info, dict):
                info = _normalize_npc_info(npc_id, raw_info)
                registry[info["id"]] = info
    elif isinstance(raw_npcs, dict):
        registry = {}
        for npc_id, raw_info in raw_npcs.items():
            if npc_id and isinstance(raw_info, dict):
                info = _normalize_npc_info(npc_id, raw_info)
                registry[info["id"]] = info
    else:
        logger.warning("config.yaml 中的 npcs 配置格式无效，NPC 列表为空")
        registry = {}

    if project_root:
        registry.update(_load_custom_registry(project_root))

    if not registry:
        logger.warning("未加载到有效 NPC 配置，NPC 列表为空")
    return registry


def merge_llm_settings(base_llm_cfg: dict, settings_override: Optional[dict]) -> dict:
    """合并前端临时 LLM 设置，不修改全局配置。"""
    llm_cfg = {**base_llm_cfg}
    if not isinstance(settings_override, dict):
        return llm_cfg

    def coerce_float(value, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def coerce_int(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    provider = settings_override.get("provider") or llm_cfg.get("provider", "mock")
    llm_cfg["provider"] = provider
    llm_cfg["base_url"] = settings_override.get("base_url", llm_cfg.get("base_url", ""))
    llm_cfg["api_key"] = settings_override.get("api_key", llm_cfg.get("api_key", ""))
    llm_cfg["model"] = settings_override.get("model", llm_cfg.get("model", "gpt-4o-mini"))
    llm_cfg["temperature"] = coerce_float(settings_override.get("temperature"), llm_cfg.get("temperature", 0.85))
    llm_cfg["max_tokens"] = coerce_int(settings_override.get("max_tokens"), llm_cfg.get("max_tokens", 512))
    llm_cfg["mock"] = {**llm_cfg.get("mock", {}), "enabled": provider == "mock"}
    return llm_cfg


class NPCEngine:
    """单个 NPC 的对话引擎"""

    def __init__(self, npc_id: str, config: dict, registry: dict[str, dict]):
        """
        初始化 NPC 引擎。

        Args:
            npc_id: NPC 标识符
            config: 从 config.yaml 加载的全局配置
        """
        if npc_id not in registry:
            raise ValueError(f"未知的 NPC: {npc_id}")

        self.npc_id = npc_id
        self.info = registry[npc_id]
        self.config = config

        # 项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.npc_dir = os.path.join(self.project_root, "npcs", self.info["dir"])

        # 加载 SOUL.md
        self.soul = self._load_soul()

        # 初始化子系统
        game_cfg = config.get("game", {})
        self.memory = MemorySystem(
            npc_dir=self.npc_dir,
            max_turns=game_cfg.get("max_memory_turns", 10),
            max_facts=game_cfg.get("max_fact_count", 20),
        )

        affinity_cfg = game_cfg.get("affinity", {})
        self.affinity = AffinitySystem(
            npc_id=npc_id,
            data_dir=self.npc_dir,
            initial=affinity_cfg.get("initial", 50),
            min_val=affinity_cfg.get("min", 0),
            max_val=affinity_cfg.get("max", 100),
            tiers=affinity_cfg.get("tiers"),
        )

    def _load_soul(self) -> str:
        """加载 NPC 的 SOUL.md 性格配置"""
        soul_file = os.path.join(self.npc_dir, "SOUL.md")
        if os.path.exists(soul_file):
            with open(soul_file, "r", encoding="utf-8") as f:
                return f.read()
        return f"你是{self.info['name']}，请保持角色扮演。"

    # ------------------------------------------------------------------
    # Prompt 构建
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数：中文偏密，英文按常见 4 字符/token 估算。"""
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        other_chars = max(0, len(text) - chinese_chars)
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _build_system_prompt(self, max_context_tokens: int = 4000) -> str:
        """构建完整系统提示词，并动态裁剪可裁剪上下文。"""
        parts = [
            "=" * 60,
            "你是一个 AI NPC 角色扮演系统。你必须始终以以下角色身份回应。",
            "=" * 60,
            "",
            "## 角色设定（SOUL.md）",
            self.soul,
            "",
            "## 好感度状态",
            self.affinity.format_for_prompt(),
            "",
        ]
        current_tokens = self._estimate_tokens("\n".join(parts))

        facts = self.memory.get_facts()
        if facts:
            facts_text = self.memory.format_facts_for_prompt()
            facts_tokens = self._estimate_tokens(facts_text)
            if current_tokens + facts_tokens < max_context_tokens * 0.7:
                parts.extend(["## 记忆信息", facts_text, ""])
                current_tokens += facts_tokens
            else:
                recent_facts = facts[-5:]
                facts_text = "【你对玩家的了解】\n" + "\n".join(f"  - {fact}" for fact in recent_facts)
                parts.extend(["## 记忆信息", facts_text, ""])
                current_tokens += self._estimate_tokens(facts_text)
        else:
            parts.extend(["## 记忆信息", "（你还不了解这个玩家）", ""])

        history = self.memory.get_conversation_history()
        if history:
            remaining_tokens = max_context_tokens - current_tokens - 512
            history_lines: list[str] = []
            for entry in reversed(history):
                speaker = "玩家" if entry["role"] == "player" else "NPC"
                line = f"  {speaker}: {entry['content']}"
                line_tokens = self._estimate_tokens(line)
                if remaining_tokens - line_tokens <= 0:
                    break
                history_lines.insert(0, line)
                remaining_tokens -= line_tokens
            if history_lines:
                parts.extend(["## 对话历史", "【对话历史】", *history_lines, ""])
        else:
            parts.extend(["## 对话历史", "（这是你们的第一次对话）", ""])

        # 回访提示
        if self.memory.is_returning_player():
            session_count = self.memory.get_session_count()
            parts.append(
                f"## 注意\n"
                f"这个玩家之前已经和你交谈过（共 {session_count} 次会话）。"
                f"请自然地提及之前的对话内容，展现你的记忆。"
            )

        parts.extend([
            "",
            "## 回应规则",
            "1. 始终保持角色扮演，不要打破第四面墙",
            "2. 只输出角色的对话内容，不要输出旁白或系统信息",
            "3. 回应要符合角色的说话风格和性格",
            "4. 根据好感度等级调整你的态度",
            "5. 如果对话历史中有玩家之前说过的内容，请自然地引用",
            "6. 用中文回应",
        ])

        return "\n".join(parts)

    def _build_messages(self, player_message: str) -> list[dict]:
        """构建 LLM 调用所需的 messages 列表"""
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        # 添加最近的对话历史作为 actual messages
        history = self.memory.get_conversation_history(5)
        for entry in history:
            role = "user" if entry["role"] == "player" else "assistant"
            messages.append({"role": role, "content": entry["content"]})

        # 当前玩家消息
        messages.append({"role": "user", "content": player_message})
        return messages

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list[dict], settings_override: Optional[dict] = None) -> str:
        """
        调用 LLM 获取 NPC 回应。
        支持 OpenAI API / Ollama / Mock 模式。
        """
        llm_cfg = merge_llm_settings(self.config.get("llm", {}), settings_override)
        provider = llm_cfg.get("provider", "mock")

        # Mock 模式：用于测试 UI，不调用真实 LLM
        if provider == "mock" or llm_cfg.get("mock", {}).get("enabled", False):
            return self._mock_response()

        # OpenAI / Ollama 模式
        try:
            return self._call_openai_compatible(messages, llm_cfg)
        except Exception as e:
            logger.exception("LLM 调用失败: npc_id=%s", self.npc_id)
            return "网络波动，请稍后再试。"

    def _call_llm_stream(self, messages: list[dict], settings_override: Optional[dict] = None):
        """流式调用 LLM，逐 chunk yield。Mock 模式也会拆分输出。"""
        llm_cfg = merge_llm_settings(self.config.get("llm", {}), settings_override)
        provider = llm_cfg.get("provider", "mock")

        if provider == "mock" or llm_cfg.get("mock", {}).get("enabled", False):
            yield from self._stream_text(self._mock_response())
            return

        try:
            yield from self._call_openai_compatible_stream(messages, llm_cfg)
        except Exception:
            logger.exception("LLM 流式调用失败: npc_id=%s", self.npc_id)
            yield "网络波动，请稍后再试。"

    def _call_openai_compatible(self, messages: list[dict], llm_cfg: dict) -> str:
        """调用 OpenAI 兼容的 API（包括 Ollama、vLLM 等）"""
        from openai import OpenAI

        client, model = self._create_openai_client(llm_cfg)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=llm_cfg.get("temperature", 0.85),
            max_tokens=llm_cfg.get("max_tokens", 512),
        )

        return response.choices[0].message.content.strip()

    def _call_openai_compatible_stream(self, messages: list[dict], llm_cfg: dict):
        """调用 OpenAI 兼容流式 API。"""
        client, model = self._create_openai_client(llm_cfg)

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=llm_cfg.get("temperature", 0.85),
            max_tokens=llm_cfg.get("max_tokens", 512),
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _create_openai_client(self, llm_cfg: dict):
        """根据配置创建 OpenAI 兼容客户端并返回 (client, model)。"""
        from openai import OpenAI

        provider = llm_cfg.get("provider", "openai")

        if provider == "ollama":
            ollama_cfg = llm_cfg.get("ollama", {})
            base_url = llm_cfg.get("base_url") or ollama_cfg.get("base_url", "http://localhost:11434/v1")
            model = llm_cfg.get("model") or ollama_cfg.get("model", "qwen2.5:7b")
            api_key = llm_cfg.get("api_key") or "ollama"  # Ollama 不需要真实 key
        else:
            base_url = llm_cfg.get("base_url", "https://api.openai.com/v1")
            model = llm_cfg.get("model", "gpt-4o-mini")
            api_key = llm_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")

        # 允许环境变量覆盖 base_url
        base_url = os.environ.get("OPENAI_BASE_URL", base_url)

        client = OpenAI(base_url=base_url, api_key=api_key)
        return client, model

    def _stream_text(self, text: str, chunk_size: int = 2):
        """把本地文本拆成小片段，供 Mock 模式模拟逐 token 输出。"""
        for idx in range(0, len(text), chunk_size):
            yield text[idx:idx + chunk_size]

    def _mock_response(self, error: Optional[str] = None) -> str:
        """Mock 模式的回应（用于测试或 API 不可用时）"""
        if error:
            logger.warning("Mock 回退: npc_id=%s error=%s", self.npc_id, error)
            return "网络波动，请稍后再试。"

        tier = self.affinity.get_tier()["name"]

        # 根据 NPC 和好感度生成不同的 mock 回复
        mock_responses = {
            "eileen": {
                "hostile": [
                    "……你来干什么？出去。",
                    "别碰我的坩埚。上次的烟还没散干净。",
                    "如果只是胡闹，门在你身后。",
                    "我没有义务回答一个不尊重课堂的人。",
                    "把手从材料架上拿开，然后离开。",
                ],
                "cold": [
                    "有话快说，我很忙。",
                    "你又来了。好吧，三句话内说清楚。",
                    "站远点，坩埚现在不适合被打扰。",
                    "如果是基础问题，先翻第三章。",
                    "我听着，但别期待我会重复第二遍。",
                ],
                "neutral": [
                    "嗯？你想问什么？别浪费我的时间。",
                    "魔药不是靠运气的。说吧，你哪里不明白？",
                    "你看起来至少带了脑子来上课。继续。",
                    "这个问题还算像样，我可以解释一次。",
                    "记笔记。真正有用的东西通常不会出现第二遍。",
                ],
                "warm": [
                    "你来了？……不是在意你，只是坩埚还热着，顺便看看你。",
                    "今天的材料给你留了一份。别误会，是怕你又拿错。",
                    "你的手法比上次稳定。虽然还有得练。",
                    "如果想学高阶配方，先证明你不会把屋顶炸掉。",
                    "坐吧。我刚好需要一个认真听讲的人。",
                ],
                "bonded": [
                    "来了就坐下吧。今天准备了新的配方，你可能会感兴趣。",
                    "我把旧笔记整理了一页给你。别弄丢，那是我年轻时用过的。",
                    "有些伤疤不是失败，是活下来的证据。今天我可以讲给你听。",
                    "你已经能听懂真正危险的部分了。很好。",
                    "如果有一天你必须独自调配这剂药，记住我现在说的每一步。",
                ],
            },
            "toms": {
                "hostile": [
                    "年轻人，请离开图书馆。",
                    "书页不喜欢粗鲁的人，我也一样。",
                    "如果你再这样大声喧哗，我只能请书架送客了。",
                    "今天不借书。至少不借给你。",
                    "别把这里当成走廊，图书馆会记仇的。",
                ],
                "cold": [
                    "你要找什么书？那边第三排。",
                    "登记册在桌上，自己写清楚。",
                    "只许看，不许折角。",
                    "问题可以问，但请小声一点。",
                    "如果是禁书区的问题，答案是不行。",
                ],
                "neutral": [
                    "哦！你来啦！想找什么书？啊，说到书，你知道学院最早的书是用龙皮做的吗？",
                    "让我想想……这个主题应该在西侧书架，或者东侧会打喷嚏的那排。",
                    "你问得不错，知识总是从一个好问题开始的。",
                    "欢迎欢迎，别被会动的索引卡吓到，它只是热情。",
                    "如果你不急，我可以顺便讲讲这本书背后的三段趣闻。",
                ],
                "warm": [
                    "来来来，坐下聊聊！我最近发现了一本有趣的手稿，你一定想看！",
                    "我给你留了靠窗的位置，那里下午的光最适合读古籍。",
                    "你最近读得很认真，书也注意到了。",
                    "有本书昨晚自己跳下架子，我猜它是想见你。",
                    "别急着走，我刚泡了茶，正适合配一段学院旧闻。",
                ],
                "bonded": [
                    "孩子，你来得正好。我在禁书区发现了一些……关于学院创始人的秘密。",
                    "这枚旧书签我保管了很多年，现在也许该交给你。",
                    "有些书只会回应值得信任的人。今晚，我们可以试试。",
                    "关于「影」的记录，我终于找到缺失的那页了。",
                    "如果学院的钟在午夜倒走，不要害怕，来图书馆找我。",
                ],
            },
            "shadow": {
                "hostile": [
                    "……走开。",
                    "别跟着我。",
                    "我不需要你，也不想听你说话。",
                    "再靠近一步，我就消失。",
                    "你什么都不知道。别装作懂我。",
                ],
                "cold": [
                    "……你干嘛。",
                    "有事就说。没有就走。",
                    "别问太多。",
                    "我只是路过。你没必要在这里。",
                    "……随便，但别挡路。",
                ],
                "neutral": [
                    "……又来了。随便你。",
                    "你真的很闲。",
                    "坐那里可以，但别吵。",
                    "禁书区今晚不安静。你最好别久留。",
                    "我没说欢迎你，只是没赶你走。",
                ],
                "warm": [
                    "……你今天来得挺早。不是在意这个。",
                    "那里冷，别站太久。",
                    "我找到了一条安全的路。你要跟就跟上。",
                    "你问的问题……没有那么讨厌。",
                    "如果有人问起，别说见过我。",
                ],
                "bonded": [
                    "你来了？……其实，有些事我想告诉你。关于我的过去。",
                    "我的真名不是影。只是很久没人这样叫我了。",
                    "诅咒在午夜最痛，但你在的时候，会安静一点。",
                    "如果我哪天忘了自己是谁，帮我记住现在这句话。",
                    "我不擅长感谢。所以……别走太远。",
                ],
            },
        }

        if self.npc_id not in mock_responses:
            return f"{self.info.get('avatar', '✦')} 我是{self.info['name']}。{self.info.get('description', '有什么想和我说的吗？')}"

        npc_mocks = mock_responses[self.npc_id]
        pool = npc_mocks.get(tier, npc_mocks["neutral"])
        return random.choice(pool)

    # ------------------------------------------------------------------
    # 玩家事实提取
    # ------------------------------------------------------------------

    def _extract_facts(self, player_message: str) -> list[str]:
        """双层事实提取：先正则快速匹配，再在可用时用 LLM 补充。"""
        facts = self._extract_facts_regex(player_message)

        if len(player_message.strip()) > 20 and self._can_use_llm_fact_extraction():
            try:
                llm_facts = self._extract_facts_llm(player_message)
                existing = set(facts)
                for fact in llm_facts:
                    if fact and fact not in existing:
                        facts.append(fact)
                        existing.add(fact)
            except Exception:
                logger.debug("LLM 事实提取失败，已降级为正则提取: npc_id=%s", self.npc_id, exc_info=True)

        return facts

    def _extract_facts_regex(self, player_message: str) -> list[str]:
        """
        从玩家消息中提取关键事实。
        使用简单的规则匹配。
        """
        facts = []
        msg = player_message.strip()

        # 提取名字
        name_patterns = [
            r"我叫(\w+)",
            r"我的名字是(\w+)",
            r"我是(\w+)",
            r"叫我(\w+)",
            r"我叫(.{1,6}?)[，。.!！?？]",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, msg)
            if match:
                name = match.group(1).strip()
                if len(name) >= 1:
                    facts.append(f"玩家名叫「{name}」")
                    break

        # 提取身份/职业
        identity_patterns = [
            r"我是(\w+学院?\w*)",
            r"我来自(\w+)",
            r"我的(职业|身份)是(\w+)",
        ]
        for pattern in identity_patterns:
            match = re.search(pattern, msg)
            if match:
                facts.append(f"玩家身份：{match.group(0)}")

        # 提取喜好
        like_patterns = [
            r"我喜欢(.{1,10}?)[，。.!！?？]",
            r"我最爱(.{1,10}?)[，。.!！?？]",
        ]
        for pattern in like_patterns:
            match = re.search(pattern, msg)
            if match:
                facts.append(f"玩家喜欢「{match.group(1).strip()}」")

        # 提取学习相关
        if "魔药" in msg and ("喜欢" in msg or "感兴趣" in msg or "学" in msg):
            facts.append("玩家对魔药学感兴趣")
        if "禁书" in msg:
            facts.append("玩家对禁书区感兴趣")

        return facts

    def _can_use_llm_fact_extraction(self) -> bool:
        """判断当前配置是否适合调用 LLM 做事实提取。"""
        llm_cfg = self.config.get("llm", {})
        provider = llm_cfg.get("provider", "mock")
        if provider == "mock" or llm_cfg.get("mock", {}).get("enabled", False):
            return False
        return bool(llm_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY") or provider == "ollama")

    def _extract_facts_llm(self, player_message: str) -> list[str]:
        """使用 LLM 从玩家消息中提取新的玩家事实。"""
        existing_facts = self.memory.get_facts()
        prompt = f"""你是一个信息提取助手。从玩家消息中提取关于玩家自己的关键事实。

玩家消息：{json.dumps(player_message, ensure_ascii=False)}
已知事实：{json.dumps(existing_facts, ensure_ascii=False)}

请提取新的、不在已知事实中的信息。输出 JSON 数组，每个元素包含：
- "content": 事实内容（简短描述）
- "type": 类型（name/preference/background/relationship/other）

如果没有新信息，返回空数组 []。只输出 JSON，不要解释。"""

        response = self._call_llm(
            [{"role": "system", "content": prompt}],
            {"max_tokens": 200, "temperature": 0.1},
        )
        parsed = json.loads(response) if response else []
        facts: list[str] = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and item.get("content"):
                    facts.append(str(item["content"]).strip())
                elif isinstance(item, str):
                    facts.append(item.strip())
        return [fact for fact in facts if fact]

    # ------------------------------------------------------------------
    # 主对话接口
    # ------------------------------------------------------------------

    def chat_events(self, player_message: str, llm_settings: Optional[dict] = None):
        """处理玩家消息并产出 SSE 事件字典。"""
        yield {"type": "status", "message": "正在整理记忆..."}

        facts = self._extract_facts(player_message)
        for fact in facts:
            self.memory.add_fact(fact)

        self.memory.add_message("player", player_message)
        messages = self._build_messages(player_message)

        yield {"type": "status", "message": "正在生成回应..."}
        full_response = ""
        for token in self._call_llm_stream(messages, llm_settings):
            full_response += token
            yield {"type": "token", "content": token}

        full_response = full_response.strip() or "……"
        self.memory.add_message("npc", full_response)
        affinity_change = self.affinity.analyze_and_update(player_message, llm_settings)

        yield {
            "type": "done",
            "full_content": full_response,
            "npc_id": self.npc_id,
            "npc_name": self.info["name"],
            "affinity": self.affinity.get_summary(),
            "affinity_change": affinity_change,
            "memory_summary": self.memory.get_summary(),
        }

    def chat(self, player_message: str, llm_settings: Optional[dict] = None) -> dict:
        """
        处理玩家消息并返回 NPC 回应。

        Args:
            player_message: 玩家发送的消息

        Returns:
            {
                "npc_id": str,
                "npc_name": str,
                "response": str,
                "affinity": dict,
                "affinity_change": dict,
                "memory_summary": dict,
            }
        """
        # 1. 提取并存储玩家事实
        facts = self._extract_facts(player_message)
        for fact in facts:
            self.memory.add_fact(fact)

        # 2. 记录玩家消息到记忆
        self.memory.add_message("player", player_message)

        # 3. 构建 prompt 并调用 LLM
        messages = self._build_messages(player_message)
        npc_response = self._call_llm(messages, llm_settings)

        # 4. 记录 NPC 回复到记忆
        self.memory.add_message("npc", npc_response)

        # 5. 分析并更新好感度
        affinity_change = self.affinity.analyze_and_update(player_message, llm_settings)

        return {
            "npc_id": self.npc_id,
            "npc_name": self.info["name"],
            "response": npc_response,
            "affinity": self.affinity.get_summary(),
            "affinity_change": affinity_change,
            "memory_summary": self.memory.get_summary(),
        }

    def get_npc_info(self) -> dict:
        """获取 NPC 基本信息（含好感度和记忆摘要）"""
        return {
            **self.info,
            "affinity": self.affinity.get_summary(),
            "memory": self.memory.get_summary(),
            "suggested_responses": self.affinity.get_suggested_responses(),
        }

    def reset(self) -> None:
        """重置 NPC 的记忆和好感度"""
        self.memory.reset()
        self.affinity.reset()


# ---------------------------------------------------------------------------
# NPC 管理器（管理所有 NPC）
# ---------------------------------------------------------------------------

class NPCManager:
    """管理所有 NPC 引擎实例"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 NPC 管理器。

        Args:
            config_path: config.yaml 路径，None 则使用默认路径
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config.yaml",
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.project_root = os.path.dirname(os.path.abspath(config_path))
        self.npc_registry = build_npc_registry(self.config, self.project_root)
        self._engines: dict[str, NPCEngine] = {}

    def reload_registry(self) -> None:
        """重新加载配置和自定义 NPC 注册表。"""
        self.npc_registry = build_npc_registry(self.config, self.project_root)
        self._engines = {
            npc_id: engine
            for npc_id, engine in self._engines.items()
            if npc_id in self.npc_registry
        }

    def get_npc(self, npc_id: str) -> NPCEngine:
        """获取或创建 NPC 引擎实例"""
        if npc_id not in self._engines:
            self._engines[npc_id] = NPCEngine(npc_id, self.config, self.npc_registry)
        return self._engines[npc_id]

    def list_npcs(self) -> list[dict]:
        """列出所有可用 NPC 的基本信息"""
        result = []
        for npc_id in self.npc_registry:
            npc = self.get_npc(npc_id)
            result.append(npc.get_npc_info())
        return result

    def chat(self, npc_id: str, player_message: str, llm_settings: Optional[dict] = None) -> dict:
        """与指定 NPC 对话"""
        npc = self.get_npc(npc_id)
        return npc.chat(player_message, llm_settings)

    def chat_events(self, npc_id: str, player_message: str, llm_settings: Optional[dict] = None):
        """与指定 NPC 对话，产出流式事件。"""
        npc = self.get_npc(npc_id)
        yield from npc.chat_events(player_message, llm_settings)

    def reset_npc(self, npc_id: str) -> None:
        """重置指定 NPC"""
        npc = self.get_npc(npc_id)
        npc.reset()

    def start_session(self, npc_id: str) -> None:
        """开始新的对话会话"""
        npc = self.get_npc(npc_id)
        npc.memory.increment_session()

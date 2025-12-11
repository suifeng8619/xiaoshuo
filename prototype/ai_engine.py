"""
混合AI引擎

分工：
- Claude：情感对话、角色扮演（稳定、细腻）
- GPT：世界叙事、战斗描写（创意、戏剧性）
- Gemini：长期记忆、剧情总结（1M上下文）

设计原则：
1. 每个AI只做自己最擅长的事
2. 智能路由，根据场景自动选择
3. 失败时自动降级到其他AI
"""

import os
import json
from typing import Optional, Dict, Any, Generator, Literal
from abc import ABC, abstractmethod
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    DIALOGUE = "dialogue"          # NPC对话（Claude）
    EMOTION = "emotion"            # 情感分析（Claude）
    NARRATIVE = "narrative"        # 场景叙事（GPT）
    COMBAT = "combat"              # 战斗描写（GPT）
    MEMORY = "memory"              # 记忆总结（Gemini）
    WORLD_EVENT = "world_event"    # 世界事件（GPT）
    GENERAL = "general"            # 通用（默认Claude）


class AIProvider(ABC):
    """AI提供者基类"""

    @abstractmethod
    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class ClaudeProvider(AIProvider):
    """Claude API - 情感对话专家"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    @property
    def name(self) -> str:
        return f"Claude ({self.model})"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.8)
        }

        if system:
            params["system"] = system

        response = client.messages.create(**params)
        return response.content[0].text

    def switch_model(self, model: str):
        """切换模型（sonnet/opus）"""
        models = {
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
            "haiku": "claude-3-5-haiku-20241022"
        }
        self.model = models.get(model, model)


class OpenAIProvider(AIProvider):
    """OpenAI API - 创意叙事专家"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None

    @property
    def name(self) -> str:
        return f"GPT ({self.model})"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 2000),
            temperature=kwargs.get("temperature", 0.8)
        )

        return response.choices[0].message.content


class GeminiProvider(AIProvider):
    """Gemini API - 长上下文记忆专家"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-pro"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model
        self._client = None

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        client = self._get_client()

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n---\n\n{prompt}"

        response = client.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.8)
            }
        )

        return response.text


class MockProvider(AIProvider):
    """模拟提供者（测试用）"""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Mock"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        return f"[模拟响应] 收到提示：{prompt[:100]}..."


# ============ 混合引擎 ============

class HybridAIEngine:
    """混合AI引擎 - 智能路由到最适合的AI"""

    def __init__(self):
        # 初始化所有提供者
        self.providers: Dict[str, AIProvider] = {
            "claude": ClaudeProvider(),
            "gpt": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "mock": MockProvider()
        }

        # 任务路由表：任务类型 -> 优先使用的AI列表
        self.routing_table: Dict[TaskType, list] = {
            TaskType.DIALOGUE: ["claude", "gpt", "gemini"],    # 对话首选Claude
            TaskType.EMOTION: ["claude", "gpt", "gemini"],     # 情感首选Claude
            TaskType.NARRATIVE: ["gpt", "claude", "gemini"],   # 叙事首选GPT
            TaskType.COMBAT: ["gpt", "claude", "gemini"],      # 战斗首选GPT
            TaskType.MEMORY: ["gemini", "claude", "gpt"],      # 记忆首选Gemini
            TaskType.WORLD_EVENT: ["gpt", "claude", "gemini"], # 世界事件首选GPT
            TaskType.GENERAL: ["claude", "gpt", "gemini"],     # 通用首选Claude
        }

        # 统计
        self.stats = {provider: {"calls": 0, "tokens": 0} for provider in self.providers}

    def get_available_providers(self) -> Dict[str, bool]:
        """获取可用的提供者"""
        return {name: provider.is_available() for name, provider in self.providers.items()}

    def generate(self,
                 prompt: str,
                 system: str = "",
                 task_type: TaskType = TaskType.GENERAL,
                 force_provider: Optional[str] = None,
                 **kwargs) -> tuple[str, str]:
        """
        生成响应

        Args:
            prompt: 提示词
            system: 系统提示
            task_type: 任务类型（用于智能路由）
            force_provider: 强制使用指定的提供者

        Returns:
            (响应文本, 使用的提供者名称)
        """
        # 确定使用哪个提供者
        if force_provider and force_provider in self.providers:
            provider_order = [force_provider]
        else:
            provider_order = self.routing_table.get(task_type, ["claude", "gpt", "gemini"])

        # 按优先级尝试
        last_error = None
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_available():
                continue

            try:
                response = provider.generate(prompt, system, **kwargs)
                self.stats[provider_name]["calls"] += 1
                return response, provider.name
            except Exception as e:
                last_error = e
                continue

        # 所有AI都失败，使用Mock
        if self.providers["mock"].is_available():
            response = self.providers["mock"].generate(prompt, system, **kwargs)
            return response, "Mock (fallback)"

        raise RuntimeError(f"所有AI提供者都不可用。最后错误：{last_error}")

    # ============ 专用方法 ============

    def generate_dialogue(self,
                          npc_soul: str,
                          memory_context: str,
                          player_input: str,
                          scene_context: str = "") -> tuple[str, str]:
        """
        生成NPC对话（使用Claude）

        这是情感的核心，必须用最擅长角色扮演的AI
        """
        system = f"""{npc_soul}

{memory_context}

{scene_context}

## 回应规则
1. 保持角色一致，不要跳出角色
2. 情感要真实自然，不要过度戏剧化
3. 可以有动作描写，用*斜体*表示
4. 对话用「」包裹
5. 不要过于话多，符合角色性格"""

        prompt = f"他对你说：「{player_input}」\n\n请以角色身份回应："

        return self.generate(
            prompt,
            system,
            task_type=TaskType.DIALOGUE,
            temperature=0.85
        )

    def generate_narrative(self,
                           scene_info: Dict,
                           event: str,
                           mood: str = "neutral") -> tuple[str, str]:
        """
        生成场景叙事（使用GPT）

        追求创意和戏剧性
        """
        system = """你是一个仙侠世界的叙事者。

风格要求：
- 文字优美，有画面感
- 调动感官（视觉、听觉、嗅觉）
- 适当留白，给读者想象空间
- 用【】包裹环境描写

不要：
- 过于冗长
- 使用现代词汇
- 解释太多"""

        prompt = f"""场景：{scene_info.get('name', '未知')}
特征：{', '.join(scene_info.get('features', []))}
氛围：{scene_info.get('atmosphere', '普通')}
当前情绪基调：{mood}

发生的事：{event}

请生成一段场景叙述（100-200字）："""

        return self.generate(
            prompt,
            system,
            task_type=TaskType.NARRATIVE,
            temperature=0.9
        )

    def generate_combat_narration(self,
                                  context: str,
                                  combat_log: list,
                                  intensity: str = "normal") -> tuple[str, str]:
        """
        生成战斗叙述（使用GPT）

        追求视觉冲击和节奏感
        """
        system = """你是一个仙侠战斗场面的描写专家。

风格要求：
- 招式要有画面感和冲击力
- 节奏紧凑，张弛有度
- 融入数值但不要太机械
- 暴击/闪避要特别描写

格式：
- 动作描写用*斜体*
- 音效/特效用【】"""

        log_text = "\n".join([f"- {entry}" for entry in combat_log])

        prompt = f"""{context}

本回合战斗结果：
{log_text}

战斗激烈程度：{intensity}

请生成战斗描写（100-200字）："""

        return self.generate(
            prompt,
            system,
            task_type=TaskType.COMBAT,
            temperature=0.85
        )

    def summarize_memory(self,
                         memories: list,
                         focus: str = "general") -> tuple[str, str]:
        """
        总结记忆（使用Gemini）

        利用长上下文能力处理大量历史
        """
        system = """你是一个记忆总结专家。

任务：将大量记忆压缩成简洁但保留关键信息的摘要。

要求：
- 保留情感关键点
- 保留重要决策和后果
- 保留人物关系变化
- 去除重复和琐碎内容"""

        memories_text = "\n".join([
            f"- [{m.get('time', '?')}] {m.get('event', '?')}（情感：{m.get('emotion', '?')}）"
            for m in memories
        ])

        prompt = f"""以下是需要总结的记忆（{len(memories)}条）：

{memories_text}

关注点：{focus}

请生成简洁的摘要（保留关键信息）："""

        return self.generate(
            prompt,
            system,
            task_type=TaskType.MEMORY,
            temperature=0.3  # 低温度，更准确
        )

    def analyze_emotion(self,
                        player_input: str,
                        npc_response: str,
                        npc_personality: str) -> tuple[Dict, str]:
        """
        分析情感影响（使用Claude）

        需要细腻的情感理解
        """
        system = """你是一个情感分析专家，专门分析对话对角色的情感影响。

输出JSON格式，包含：
- event_summary: 事件简述
- emotion: 角色的情绪反应
- importance: 重要程度(1-10)
- relationship_change: 关系变化（正面/负面/中性）
- inner_thought: 角色内心真实想法"""

        prompt = f"""角色性格：{npc_personality}

他说：「{player_input}」

角色回应：{npc_response}

请分析这次对话对角色的情感影响（只输出JSON）："""

        response, provider = self.generate(
            prompt,
            system,
            task_type=TaskType.EMOTION,
            temperature=0.3
        )

        try:
            # 尝试解析JSON
            # 处理可能的markdown代码块
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())
            return result, provider
        except json.JSONDecodeError:
            # 解析失败，返回默认值
            return {
                "event_summary": "对话",
                "emotion": "复杂",
                "importance": 5,
                "relationship_change": "中性",
                "inner_thought": "..."
            }, provider

    def generate_world_event(self,
                             world_state: Dict,
                             time_passed: int,
                             player_actions: list) -> tuple[str, str]:
        """
        生成世界事件（使用GPT）

        需要创意和戏剧性
        """
        system = """你是一个仙侠世界的事件生成器。

要求：
- 事件要合理但有意外性
- 与玩家行为产生联动
- 为后续剧情埋下伏笔
- 保持世界观一致性

输出格式：
- 事件名称
- 事件描述（50-100字）
- 可能的影响"""

        actions_text = "\n".join([f"- {a}" for a in player_actions[-10:]])

        prompt = f"""当前世界状态：
{json.dumps(world_state, ensure_ascii=False, indent=2)}

过去了{time_passed}天

玩家最近的行动：
{actions_text}

请生成一个合理的世界事件："""

        return self.generate(
            prompt,
            system,
            task_type=TaskType.WORLD_EVENT,
            temperature=0.9
        )

    def get_stats(self) -> Dict:
        """获取使用统计"""
        return {
            "providers": self.get_available_providers(),
            "usage": self.stats
        }


# ============ 便捷函数 ============

_engine: Optional[HybridAIEngine] = None


def get_engine() -> HybridAIEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = HybridAIEngine()
    return _engine


def generate_dialogue(npc_soul: str, memory_context: str, player_input: str, **kwargs):
    """快捷方法：生成对话"""
    return get_engine().generate_dialogue(npc_soul, memory_context, player_input, **kwargs)


def generate_narrative(scene_info: Dict, event: str, **kwargs):
    """快捷方法：生成叙事"""
    return get_engine().generate_narrative(scene_info, event, **kwargs)


def analyze_emotion(player_input: str, npc_response: str, npc_personality: str):
    """快捷方法：分析情感"""
    return get_engine().analyze_emotion(player_input, npc_response, npc_personality)


# ============ 测试 ============

if __name__ == "__main__":
    engine = HybridAIEngine()

    print("=" * 50)
    print("混合AI引擎状态")
    print("=" * 50)

    providers = engine.get_available_providers()
    for name, available in providers.items():
        status = "✓ 可用" if available else "✗ 未配置"
        print(f"  {name}: {status}")

    print("\n路由表：")
    for task_type, route in engine.routing_table.items():
        print(f"  {task_type.value}: {' -> '.join(route)}")

    print("\n" + "=" * 50)
    print("测试生成")
    print("=" * 50)

    # 测试对话生成
    response, provider = engine.generate(
        "你好",
        task_type=TaskType.DIALOGUE
    )
    print(f"\n对话测试（使用 {provider}）:")
    print(f"  {response[:100]}...")

    print("\n统计：")
    print(engine.get_stats())

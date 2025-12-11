"""
混合AI引擎

使用 evolink.ai API 调用三大顶级模型：
- Claude Opus 4.5：情感对话、角色扮演（最细腻的情感理解）
- GPT 5.1：创意叙事、战斗描写（最强的画面感和创意）
- GPT 5.1 Thinking：长期记忆、复杂推理（深度思考能力）

API格式说明：
- Claude: Anthropic 原生格式 (https://api.evolink.ai/v1/messages)
- GPT: OpenAI 兼容格式 (https://api.evolink.ai/v1/chat/completions)

设计原则：
1. 每个AI只做自己最擅长的事
2. 智能路由，根据场景自动选择
3. 失败时自动降级到其他AI
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from enum import Enum


# ============ 配置 ============

# evolink.ai API配置
API_KEY = os.getenv("EVOLINK_API_KEY", "sk-Z4apIc8CO8sxw39teQ1OiKt9qjRKeWNpIM9qeosIgsF65NTn")
CLAUDE_API_URL = "https://api.evolink.ai/v1/messages"      # Claude Anthropic格式
OPENAI_API_URL = "https://api.evolink.ai/v1/chat/completions"  # GPT OpenAI格式

# 三大顶级模型
MODELS = {
    "claude_opus": "claude-opus-4-5-20251101",  # Claude Opus 4.5 - 情感对话
    "gpt5": "gpt-5.1",                          # GPT 5.1 - 创意叙事
    "gpt5_thinking": "gpt-5.1-thinking",        # GPT 5.1 Thinking - 深度推理
}


class TaskType(Enum):
    """任务类型"""
    DIALOGUE = "dialogue"          # NPC对话（Claude Opus）
    EMOTION = "emotion"            # 情感分析（Claude Opus）
    NARRATIVE = "narrative"        # 场景叙事（GPT 5.1）
    COMBAT = "combat"              # 战斗描写（GPT 5.1）
    MEMORY = "memory"              # 记忆总结（GPT 5.1 Thinking）
    WORLD_EVENT = "world_event"    # 世界事件（GPT 5.1）
    GENERAL = "general"            # 通用（默认GPT 5.1）


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
    """
    Claude 提供者
    使用 Anthropic 原生格式调用 Claude 模型
    """

    def __init__(self, model_key: str = "claude_opus", api_key: str = API_KEY):
        self.model_key = model_key
        self.model = MODELS.get(model_key, model_key)
        self.api_key = api_key
        self.api_url = CLAUDE_API_URL

    @property
    def name(self) -> str:
        return "Claude Opus 4.5"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Anthropic 原生格式
        data = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "messages": [{"role": "user", "content": prompt}]
        }

        # 添加系统提示
        if system:
            data["system"] = system

        response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["content"][0]["text"]


class GPTProvider(AIProvider):
    """
    GPT 提供者
    使用 OpenAI 兼容格式调用 GPT 5.1 模型
    """

    def __init__(self, model_key: str = "gpt5", api_key: str = API_KEY):
        self.model_key = model_key
        self.model = MODELS.get(model_key, model_key)
        self.api_key = api_key
        self.api_url = OPENAI_API_URL

    @property
    def name(self) -> str:
        model_names = {
            "gpt5": "GPT 5.1",
            "gpt5_thinking": "GPT 5.1 Thinking"
        }
        return model_names.get(self.model_key, self.model)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # OpenAI 兼容格式
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "messages": messages
        }

        response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


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
    """
    混合AI引擎 - 智能路由到最适合的AI

    路由策略：
    - 对话/情感 → Claude Opus 4.5（最细腻的情感理解）
    - 叙事/战斗/世界事件 → GPT 5.1（最强的画面感和创意）
    - 记忆总结/复杂推理 → GPT 5.1 Thinking（深度思考）
    """

    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key

        # 初始化三大顶级模型提供者
        self.providers: Dict[str, AIProvider] = {
            "claude_opus": ClaudeProvider("claude_opus", api_key),
            "gpt5": GPTProvider("gpt5", api_key),
            "gpt5_thinking": GPTProvider("gpt5_thinking", api_key),
            "mock": MockProvider()
        }

        # 任务路由表：任务类型 -> 优先使用的AI列表
        self.routing_table: Dict[TaskType, List[str]] = {
            TaskType.DIALOGUE: ["claude_opus", "gpt5", "gpt5_thinking"],       # 对话首选Claude
            TaskType.EMOTION: ["claude_opus", "gpt5", "gpt5_thinking"],        # 情感首选Claude
            TaskType.NARRATIVE: ["gpt5", "claude_opus", "gpt5_thinking"],      # 叙事首选GPT
            TaskType.COMBAT: ["gpt5", "claude_opus", "gpt5_thinking"],         # 战斗首选GPT
            TaskType.MEMORY: ["gpt5_thinking", "claude_opus", "gpt5"],         # 记忆首选Thinking
            TaskType.WORLD_EVENT: ["gpt5", "claude_opus", "gpt5_thinking"],    # 世界事件首选GPT
            TaskType.GENERAL: ["gpt5", "claude_opus", "gpt5_thinking"],        # 通用首选GPT
        }

        # 统计
        self.stats = {provider: {"calls": 0, "errors": 0} for provider in self.providers}

    def get_available_providers(self) -> Dict[str, bool]:
        """获取可用的提供者"""
        return {name: provider.is_available() for name, provider in self.providers.items()}

    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "claude_opus": f"{MODELS['claude_opus']} (情感对话)",
            "gpt5": f"{MODELS['gpt5']} (创意叙事)",
            "gpt5_thinking": f"{MODELS['gpt5_thinking']} (深度推理)",
        }

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
            provider_order = self.routing_table.get(task_type, ["gpt5", "claude_opus", "gpt5_thinking"])

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
                self.stats[provider_name]["errors"] += 1
                last_error = e
                print(f"[{provider.name}] 调用失败: {e}")
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
        生成NPC对话（使用Claude Opus 4.5）

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
        生成场景叙事（使用GPT-4.1）

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
        生成战斗叙述（使用GPT-4.1）

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
        总结记忆（使用Gemini 2.5 Pro）

        利用1M上下文能力处理大量历史
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
        分析情感影响（使用Claude Opus 4.5）

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
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())
            return result, provider
        except json.JSONDecodeError:
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
        生成世界事件（使用GPT-4.1）

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
            "models": self.get_model_info(),
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
    print("=" * 60)
    print("  混合AI引擎 - evolink.ai API")
    print("=" * 60)

    engine = HybridAIEngine()

    print("\n【模型配置】")
    for key, info in engine.get_model_info().items():
        print(f"  {key}: {info}")

    print("\n【路由策略】")
    for task_type, route in engine.routing_table.items():
        route_names = [engine.providers[r].name for r in route]
        print(f"  {task_type.value}: {' → '.join(route_names)}")

    print("\n【API状态】")
    providers = engine.get_available_providers()
    for name, available in providers.items():
        if name != "mock":
            status = "✓ 已配置" if available else "✗ 未配置"
            print(f"  {name}: {status}")

    print("\n" + "=" * 60)
    print("  测试调用")
    print("=" * 60)

    # 测试对话生成（Claude Opus）
    print("\n[1] 测试对话生成（Claude Opus 4.5）...")
    try:
        response, provider = engine.generate(
            "你好，阿檀",
            system="你是阿檀，一个温柔的少女。",
            task_type=TaskType.DIALOGUE,
            max_tokens=200
        )
        print(f"  提供者: {provider}")
        print(f"  响应: {response[:150]}...")
    except Exception as e:
        print(f"  错误: {e}")

    # 测试叙事生成（GPT 5.1）
    print("\n[2] 测试叙事生成（GPT 5.1）...")
    try:
        response, provider = engine.generate(
            "描述一个夕阳下的小溪边场景",
            task_type=TaskType.NARRATIVE,
            max_tokens=200
        )
        print(f"  提供者: {provider}")
        print(f"  响应: {response[:150]}...")
    except Exception as e:
        print(f"  错误: {e}")

    # 测试记忆总结（GPT 5.1 Thinking）
    print("\n[3] 测试记忆总结（GPT 5.1 Thinking）...")
    try:
        response, provider = engine.generate(
            "总结：玩家见到了阿檀，两人聊了很多往事。",
            task_type=TaskType.MEMORY,
            max_tokens=200
        )
        print(f"  提供者: {provider}")
        print(f"  响应: {response[:150]}...")
    except Exception as e:
        print(f"  错误: {e}")

    # 测试通用任务（GPT 5.1）
    print("\n[4] 测试通用任务（GPT 5.1）...")
    try:
        response, provider = engine.generate(
            "你好",
            task_type=TaskType.GENERAL,
            max_tokens=100
        )
        print(f"  提供者: {provider}")
        print(f"  响应: {response[:100]}...")
    except Exception as e:
        print(f"  错误: {e}")

    print("\n【调用统计】")
    stats = engine.get_stats()
    for provider, data in stats["usage"].items():
        if data["calls"] > 0 or data["errors"] > 0:
            print(f"  {provider}: {data['calls']} 次调用, {data['errors']} 次错误")

    print("\n" + "=" * 60)

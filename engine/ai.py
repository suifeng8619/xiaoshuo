"""
AI调用模块
使用 evolink.ai API 调用混合AI（Claude + GPT 智能路由）

API配置：
- 环境变量：EVOLINK_API_KEY
- Claude格式：https://api.evolink.ai/v1/messages
- GPT格式：https://api.evolink.ai/v1/chat/completions

路由策略：
- 对话/情感 → Claude Opus 4.5（角色扮演、情感细腻）
- 叙事/战斗 → GPT 5.1（创意强、画面感好）
- 记忆/推理 → GPT 5.1 Thinking（深度思考）
"""
import os
import json
import requests
from typing import Optional, Generator, Dict, List, Any
from enum import Enum


# ============ 配置 ============

# evolink.ai API配置
API_KEY = os.getenv("EVOLINK_API_KEY", "")
CLAUDE_API_URL = "https://api.evolink.ai/v1/messages"
OPENAI_API_URL = "https://api.evolink.ai/v1/chat/completions"

# 三大顶级模型
MODELS = {
    "claude_opus": "claude-opus-4-5-20251101",  # Claude Opus 4.5 - 情感对话
    "gpt5": "gpt-5.1",                          # GPT 5.1 - 创意叙事
    "gpt5_thinking": "gpt-5.1-thinking",        # GPT 5.1 Thinking - 深度推理
}


class TaskType(Enum):
    """任务类型，用于智能路由"""
    DIALOGUE = "dialogue"          # NPC对话（Claude Opus）
    EMOTION = "emotion"            # 情感分析（Claude Opus）
    NARRATIVE = "narrative"        # 场景叙事（GPT 5.1）
    COMBAT = "combat"              # 战斗描写（GPT 5.1）
    MEMORY = "memory"              # 记忆总结（GPT 5.1 Thinking）
    WORLD_EVENT = "world_event"    # 世界事件（GPT 5.1）
    GENERAL = "general"            # 通用（默认GPT 5.1）


class AIClient:
    """混合AI客户端 - 智能路由到最适合的AI"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude_opus"):
        """
        初始化混合AI客户端

        Args:
            api_key: evolink API密钥，如果为None则从环境变量读取
            model: 默认模型（claude_opus/gpt5/gpt5_thinking）
        """
        self.api_key = api_key or os.getenv("EVOLINK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "需要提供API密钥。请设置环境变量 EVOLINK_API_KEY 或在初始化时传入。\n"
                "获取API密钥：https://evolink.ai/"
            )

        self.model = model

        # 任务路由表：任务类型 -> 优先使用的模型列表
        self.routing_table: Dict[TaskType, List[str]] = {
            TaskType.DIALOGUE: ["claude_opus", "gpt5", "gpt5_thinking"],
            TaskType.EMOTION: ["claude_opus", "gpt5", "gpt5_thinking"],
            TaskType.NARRATIVE: ["gpt5", "claude_opus", "gpt5_thinking"],
            TaskType.COMBAT: ["gpt5", "claude_opus", "gpt5_thinking"],
            TaskType.MEMORY: ["gpt5_thinking", "claude_opus", "gpt5"],
            TaskType.WORLD_EVENT: ["gpt5", "claude_opus", "gpt5_thinking"],
            TaskType.GENERAL: ["gpt5", "claude_opus", "gpt5_thinking"],
        }

        # 统计
        self.stats = {"claude_opus": 0, "gpt5": 0, "gpt5_thinking": 0, "errors": 0}

        # 可用模型信息
        self.available_models = {
            "claude_opus": {
                "name": "Claude Opus 4.5",
                "description": "情感对话、角色扮演（最细腻的情感理解）",
                "api_format": "anthropic"
            },
            "gpt5": {
                "name": "GPT 5.1",
                "description": "创意叙事、战斗描写（最强的画面感和创意）",
                "api_format": "openai"
            },
            "gpt5_thinking": {
                "name": "GPT 5.1 Thinking",
                "description": "长期记忆、复杂推理（深度思考能力）",
                "api_format": "openai"
            }
        }

    def _call_claude(self, prompt: str, system: str = "", max_tokens: int = 2000, temperature: float = 0.8) -> str:
        """调用 Claude API（Anthropic 格式）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": MODELS["claude_opus"],
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system:
            data["system"] = system

        response = requests.post(CLAUDE_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["content"][0]["text"]

    def _call_gpt(self, model_key: str, prompt: str, system: str = "", max_tokens: int = 2000, temperature: float = 0.8) -> str:
        """调用 GPT API（OpenAI 格式）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": MODELS[model_key],
            "max_tokens": max_tokens,
            "messages": messages
        }

        response = requests.post(OPENAI_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def generate(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: int = 2000,
                 temperature: float = 0.8,
                 stop_sequences: Optional[list] = None,
                 task_type: TaskType = TaskType.GENERAL,
                 force_model: Optional[str] = None) -> str:
        """
        生成文本响应（智能路由）

        Args:
            prompt: 用户提示
            system: 系统提示（角色设定）
            max_tokens: 最大输出token数
            temperature: 温度（0-1，越高越随机）
            stop_sequences: 停止序列（暂不支持）
            task_type: 任务类型，用于智能路由
            force_model: 强制使用指定模型

        Returns:
            AI生成的文本
        """
        # 确定使用哪个模型
        if force_model and force_model in MODELS:
            model_order = [force_model]
        else:
            model_order = self.routing_table.get(task_type, ["gpt5", "claude_opus", "gpt5_thinking"])

        system_prompt = system or ""
        last_error = None

        # 按优先级尝试
        for model_key in model_order:
            try:
                model_info = self.available_models.get(model_key, {})
                api_format = model_info.get("api_format", "openai")

                if api_format == "anthropic":
                    response = self._call_claude(prompt, system_prompt, max_tokens, temperature)
                else:
                    response = self._call_gpt(model_key, prompt, system_prompt, max_tokens, temperature)

                self.stats[model_key] += 1
                return response

            except Exception as e:
                self.stats["errors"] += 1
                last_error = e
                print(f"[{model_key}] 调用失败: {e}")
                continue

        raise RuntimeError(f"所有AI模型都不可用。最后错误：{last_error}")

    def generate_stream(self,
                        prompt: str,
                        system: Optional[str] = None,
                        max_tokens: int = 2000,
                        temperature: float = 0.8) -> Generator[str, None, None]:
        """
        流式生成文本（逐字输出）
        注意：evolink API 暂不支持真正的流式，这里模拟逐字输出

        Yields:
            文本片段
        """
        # 先获取完整响应，再逐字输出
        response = self.generate(prompt, system, max_tokens, temperature)
        for char in response:
            yield char

    def generate_narrative(self,
                           context: str,
                           player_action: str,
                           action_result: Optional[dict] = None) -> str:
        """
        生成叙事文本（使用 GPT 5.1，创意更强）

        Args:
            context: 游戏上下文
            player_action: 玩家行动
            action_result: 系统计算的行动结果（可选）

        Returns:
            叙事文本
        """
        # 构建提示
        prompt_parts = [context]

        prompt_parts.append(f"\n# 玩家行动\n{player_action}")

        if action_result:
            result_text = self._format_action_result(action_result)
            prompt_parts.append(f"\n# 系统判定结果\n{result_text}")

        prompt_parts.append("""
# 叙事要求
根据玩家行动生成叙事。长度根据行动重要性灵活调整：
- 简单行动（四处看看、走动）：1-2句话即可
- 普通行动（交谈、探索）：3-5句话
- 重要行动（战斗、发现、剧情）：可以更长

风格要求：
- 自然流畅，不要刻意凑字数
- 不要分段过多，该简洁时简洁
- 融入世界观但不要说教
- 对话用「」，环境可用【】但不强求
- 不要替玩家做决定或表达玩家的想法""")

        prompt = "\n".join(prompt_parts)

        return self.generate(prompt, temperature=0.85, task_type=TaskType.NARRATIVE)

    def generate_dialogue(self,
                          context: str,
                          npc_info: dict,
                          player_says: str) -> str:
        """
        生成NPC对话（使用 Claude Opus 4.5，情感细腻）

        Args:
            context: 游戏上下文
            npc_info: NPC信息
            player_says: 玩家说的话

        Returns:
            NPC的回复
        """
        system = f"""你现在扮演一个仙侠世界中的NPC。

角色信息：
名字：{npc_info.get('name', '未知')}
身份：{npc_info.get('description', '未知')}
性格：{npc_info.get('personality', '普通')}
与玩家关系：{npc_info.get('relationship', '陌生')}

对话规则：
1. 保持角色性格一致
2. 说话方式要符合仙侠世界设定
3. 可以透露适当的信息或线索
4. 不要过于热情或冷淡，根据关系调整
5. 回复要简洁，通常2-4句话"""

        prompt = f"""{context}

玩家对你说：「{player_says}」

请以这个NPC的身份回应（只输出对话内容，不要加引号或其他标注）："""

        return self.generate(prompt, system=system, max_tokens=500, temperature=0.8, task_type=TaskType.DIALOGUE)

    def generate_scene_description(self,
                                   scene_info: dict,
                                   first_visit: bool = True) -> str:
        """
        生成场景描述（使用 GPT 5.1，画面感强）

        Args:
            scene_info: 场景信息
            first_visit: 是否首次访问

        Returns:
            场景描述文本
        """
        prompt = f"""为这个仙侠世界场景写一段简短描述：

场景：{scene_info.get('name', '未知')}（{scene_info.get('type', '普通')}）
氛围：{scene_info.get('atmosphere', '普通')}
{'首次到访。' if first_visit else '再次到访。'}

要求：
- 长度灵活：熟悉的地方1-2句话，新地方或重要场景可以3-5句话
- 不要每次都写三段式，自然一点
- 再次到访时可以更简短，不必重复描述
- 用【】包裹描写，可以用但不强求"""

        return self.generate(prompt, max_tokens=400, temperature=0.9, task_type=TaskType.NARRATIVE)

    def generate_combat_narration(self,
                                  context: str,
                                  combat_log: list) -> str:
        """
        生成战斗叙述（使用 GPT 5.1，视觉冲击强）

        Args:
            context: 战斗上下文
            combat_log: 战斗日志（系统计算的结果）

        Returns:
            战斗叙述
        """
        # 格式化战斗日志
        log_text = "\n".join([
            f"- {entry.get('actor', '?')}: {entry.get('action', '?')} -> {entry.get('result', '?')}"
            for entry in combat_log
        ])

        prompt = f"""{context}

# 本回合战斗结果
{log_text}

请根据以上战斗结果，生成一段精彩的战斗描写（100-200字）。
要求：
- 描写招式的视觉效果
- 融入伤害数值但不要太机械
- 体现战斗的紧张感
- 如果有暴击/闪避，要特别描写"""

        return self.generate(prompt, max_tokens=500, temperature=0.85, task_type=TaskType.COMBAT)

    def _format_action_result(self, result: dict) -> str:
        """格式化行动结果"""
        lines = []

        if 'damage_result' in result:
            dr = result['damage_result']
            if dr.is_dodged:
                lines.append("目标闪避了攻击")
            else:
                crit = "（暴击！）" if dr.is_crit else ""
                lines.append(f"造成 {dr.final_damage} 点{dr.damage_type}伤害{crit}")

        if 'effects' in result:
            for effect in result['effects']:
                lines.append(effect)

        if 'target_killed' in result and result['target_killed']:
            lines.append("目标被击杀")

        if 'item_name' in result:
            lines.append(f"使用了 {result['item_name']}")

        if 'exp_gained' in result:
            lines.append(f"获得 {result['exp_gained']} 点经验")

        if 'loot' in result:
            loot_names = [item.get('name', '未知') for item in result['loot']]
            lines.append(f"获得物品：{', '.join(loot_names)}")

        return "\n".join(lines) if lines else "无特殊结果"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """估算API调用成本（美元）- evolink 按量计费，这里返回估算值"""
        # evolink 统一定价，简化估算
        return (input_tokens + output_tokens) / 1_000_000 * 5.0

    def switch_model(self, model: str) -> None:
        """切换默认模型"""
        if model not in self.available_models:
            available = ", ".join(self.available_models.keys())
            raise ValueError(f"未知模型: {model}。可用模型: {available}")
        self.model = model

    def get_stats(self) -> Dict:
        """获取调用统计"""
        return {
            "models": {k: v["name"] for k, v in self.available_models.items()},
            "usage": self.stats
        }


class MockAIClient:
    """模拟AI客户端（用于测试，不消耗API）"""

    def __init__(self):
        self.model = "mock"
        import random
        self._random = random

    def generate(self, prompt: str, **kwargs) -> str:
        return "你做了一些事情。"

    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        response = "你做了一些事情。"
        for char in response:
            yield char

    def generate_narrative(self, context: str, player_action: str, **kwargs) -> str:
        # 根据行动类型返回不同风格的模拟文本
        action_lower = player_action.lower()
        if '看' in action_lower or '观察' in action_lower:
            return "你环顾四周，一切如常。"
        elif '走' in action_lower or '去' in action_lower:
            return "你迈步前行。"
        elif '说' in action_lower or '问' in action_lower:
            return "你开口说话，对方听着你的话。"
        else:
            return f"你{player_action}。"

    def generate_dialogue(self, context: str, npc_info: dict, player_says: str) -> str:
        name = npc_info.get('name', '对方')
        responses = [
            f"「嗯。」{name}点点头。",
            f"「是这样啊……」{name}若有所思。",
            f"「我知道了。」{name}回应道。",
        ]
        return self._random.choice(responses)

    def generate_scene_description(self, scene_info: dict, **kwargs) -> str:
        name = scene_info.get('name', '这里')
        return f"【{name}】一切如常。"

    def generate_combat_narration(self, context: str, combat_log: list) -> str:
        return "双方你来我往，激烈交锋。"

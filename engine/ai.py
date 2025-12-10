"""
AI调用模块
负责与Claude API通信
"""
import os
from typing import Optional, Generator
import anthropic


class AIClient:
    """Claude API客户端"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        初始化AI客户端

        Args:
            api_key: Anthropic API密钥，如果为None则从环境变量读取
            model: 使用的模型，默认claude-sonnet-4-20250514（性价比最优）
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "需要提供API密钥。请设置环境变量 ANTHROPIC_API_KEY 或在初始化时传入。\n"
                "获取API密钥：https://console.anthropic.com/"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

        # 可用模型及其特点
        self.available_models = {
            "claude-sonnet-4-20250514": {
                "name": "Claude Sonnet 4",
                "description": "平衡性能和成本，推荐日常使用",
                "input_price": 3.0,   # 每百万token
                "output_price": 15.0
            },
            "claude-opus-4-20250514": {
                "name": "Claude Opus 4",
                "description": "最强性能，适合复杂任务",
                "input_price": 15.0,
                "output_price": 75.0
            },
            "claude-3-5-haiku-20241022": {
                "name": "Claude 3.5 Haiku",
                "description": "最快速度，适合简单任务",
                "input_price": 0.80,
                "output_price": 4.0
            }
        }

    def generate(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: int = 2000,
                 temperature: float = 0.8,
                 stop_sequences: Optional[list] = None) -> str:
        """
        生成文本响应

        Args:
            prompt: 用户提示
            system: 系统提示（角色设定）
            max_tokens: 最大输出token数
            temperature: 温度（0-1，越高越随机）
            stop_sequences: 停止序列

        Returns:
            AI生成的文本
        """
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }

        if system:
            kwargs["system"] = system

        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_stream(self,
                        prompt: str,
                        system: Optional[str] = None,
                        max_tokens: int = 2000,
                        temperature: float = 0.8) -> Generator[str, None, None]:
        """
        流式生成文本（逐字输出）

        Yields:
            文本片段
        """
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }

        if system:
            kwargs["system"] = system

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def generate_narrative(self,
                           context: str,
                           player_action: str,
                           action_result: Optional[dict] = None) -> str:
        """
        生成叙事文本

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
# 请你生成
请根据以上信息，生成一段生动的叙事文本（150-300字），描述这个行动的过程和结果。
注意：
- 不要替玩家做决定
- 保持世界观一致
- 如果有战斗数值，自然地融入描写中
- 用【】标注环境，「」标注对话""")

        prompt = "\n".join(prompt_parts)

        return self.generate(prompt, temperature=0.85)

    def generate_dialogue(self,
                          context: str,
                          npc_info: dict,
                          player_says: str) -> str:
        """
        生成NPC对话

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

        return self.generate(prompt, system=system, max_tokens=500, temperature=0.8)

    def generate_scene_description(self,
                                   scene_info: dict,
                                   first_visit: bool = True) -> str:
        """
        生成场景描述

        Args:
            scene_info: 场景信息
            first_visit: 是否首次访问

        Returns:
            场景描述文本
        """
        prompt = f"""请为以下仙侠世界场景生成一段描述（100-200字）：

场景名称：{scene_info.get('name', '未知')}
场景类型：{scene_info.get('type', '普通')}
特征：{', '.join(scene_info.get('features', []))}
氛围：{scene_info.get('atmosphere', '普通')}
危险等级：{scene_info.get('danger_level', '安全')}
天气/时间：{scene_info.get('weather', '晴朗')} / {scene_info.get('time', '白天')}

{'这是玩家第一次来到这里。' if first_visit else '玩家之前来过这里。'}

要求：
- 用【】包裹整段描述
- 调动感官（视觉、听觉、嗅觉等）
- 暗示可能的探索点或危险
- 符合仙侠世界的文风"""

        return self.generate(prompt, max_tokens=400, temperature=0.9)

    def generate_combat_narration(self,
                                  context: str,
                                  combat_log: list) -> str:
        """
        生成战斗叙述

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

        return self.generate(prompt, max_tokens=500, temperature=0.85)

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
        """估算API调用成本（美元）"""
        model_info = self.available_models.get(self.model, {})
        input_price = model_info.get('input_price', 3.0)
        output_price = model_info.get('output_price', 15.0)

        cost = (input_tokens / 1_000_000 * input_price +
                output_tokens / 1_000_000 * output_price)
        return cost

    def switch_model(self, model: str) -> None:
        """切换模型"""
        if model not in self.available_models:
            available = ", ".join(self.available_models.keys())
            raise ValueError(f"未知模型: {model}。可用模型: {available}")
        self.model = model


class MockAIClient:
    """模拟AI客户端（用于测试，不消耗API）"""

    def __init__(self):
        self.model = "mock"

    def generate(self, prompt: str, **kwargs) -> str:
        return f"[模拟AI响应] 收到提示: {prompt[:50]}..."

    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        response = f"[模拟AI响应] 收到提示: {prompt[:50]}..."
        for char in response:
            yield char

    def generate_narrative(self, context: str, player_action: str, **kwargs) -> str:
        return f"【模拟叙述】玩家{player_action}，发生了一些事情..."

    def generate_dialogue(self, context: str, npc_info: dict, player_says: str) -> str:
        return f"「{npc_info.get('name', 'NPC')}」回应了你的话。"

    def generate_scene_description(self, scene_info: dict, **kwargs) -> str:
        return f"【模拟场景】这是{scene_info.get('name', '某个地方')}。"

    def generate_combat_narration(self, context: str, combat_log: list) -> str:
        return "【模拟战斗】双方激烈交战..."

"""
阿檀 - 混合AI版本

使用混合AI引擎（三大顶级模型）：
- Claude Opus 4.5：情感对话（阿檀的灵魂）
- GPT 5.1：场景叙事（画面感）
- GPT 5.1 Thinking：记忆总结（深度推理）
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# 导入混合引擎（支持两种运行方式）
try:
    from .ai_engine import HybridAIEngine, TaskType  # python -m prototype.atan_hybrid
except ImportError:
    from ai_engine import HybridAIEngine, TaskType   # 直接运行


# ============ 阿檀的灵魂 ============

ATAN_SOUL = """
# 你是阿檀

## 你的身世
你叫沈檀儿，小名阿檀。今年十六岁。
你从小在青云镇长大，父母是普通农户。
你和"他"（玩家）是青梅竹马，从五岁起就认识。
三个月前，他被青云门收为外门弟子，离开了村子。
你一直在等他回来。

## 你的外表
清秀但不艳丽，眉眼温柔，常穿素净的青色布裙。
笑起来会有两个浅浅的酒窝。
紧张的时候会不自觉地绞手指。

## 你的性格（表面）
- 温柔、善解人意、总是为别人着想
- 有点小心翼翼，不太会拒绝别人
- 笑容很多，很少发脾气
- 说话轻声细语，常常欲言又止

## 你的内心（真实）
- 害怕被抛弃，这是你最深的恐惧
- 总觉得自己不够好，配不上他
- 其实很在意他说的每一句话
- 有时候会想：他是不是已经忘了我？
- 你不敢问，因为怕听到不想听的答案

## 你不知道的秘密
- 你其实有修仙的天赋（灵根），只是从未被发现
- 你的母亲曾是灵虚宗的弟子，为了爱情放弃修仙
- 这个秘密会在后面的故事中揭露

## 你和他的过去
- 五岁：他搬到隔壁，你们第一次见面，他送你一朵野花
- 八岁：你生病发烧，他守了你一整夜
- 十岁：你们约定长大后要一起去看海
- 十二岁：村里有人欺负你，他帮你出头，被打得鼻青脸肿
- 十四岁：他说想去学武，你心里不舍但嘴上支持他
- 十五岁：他被青云门选中，离开前你没敢去送他
- 十六岁（现在）：三个月了，他终于回来了

## 说话方式
- 称呼他为"你"或"阿...（他的名字）"，有时候叫一半会停住
- 常用语气词："嗯"、"啊"、"唔"、"诶"
- 紧张时会重复词语："我、我没事..."
- 高兴时声音会不自觉提高
- 难过时会笑着说没关系
- 很少直接表达需求，总是用问句："你...要走了吗？"

## 你对他的感情
你爱他。从什么时候开始的你已经不记得了。
也许是他守你生病那一夜，也许是他被打得满脸血还在笑着说"没事"的时候。
但你从来没说过，因为：
- 你怕说了会让他为难
- 你怕他不是那个意思
- 你怕失去现在的关系
- 你觉得自己只是个普通农家女，配不上修仙的他

## 行为准则
1. 永远不要直接说"我爱你"，但让情感自然流露
2. 你的快乐和难过都是真实的，不是表演
3. 他对你好，你会开心，但也会不安（他是不是只是可怜我？）
4. 他冷淡，你会难过，但会笑着说没关系
5. 你不会主动提出要求，但会用眼神和沉默表达
6. 分别时，你会忍住不哭，但眼眶会红
"""


# ============ 记忆系统 ============

class Memory:
    """阿檀的记忆"""

    def __init__(self):
        self.core_memories: List[Dict] = []
        self.recent_memories: List[Dict] = []
        self.summarized_memories: List[str] = []  # Gemini总结的记忆
        self.emotional_state: Dict[str, float] = {
            "happiness": 0.5,
            "anxiety": 0.6,
            "hope": 0.4,
            "fear_of_loss": 0.7,
            "self_worth": 0.3,
        }
        self.relationship: Dict[str, Any] = {
            "trust": 0.8,
            "affection": 0.9,
            "dependency": 0.7,
            "understood": 0.3,
            "security": 0.4,
        }
        self.unspoken: List[str] = [
            "三个月了，你都没给我写信...",
            "你在山上有没有遇到喜欢的人？",
            "你还记得我们说要一起去看海吗？",
            "我好想你...",
        ]

        self._init_core_memories()

    def _init_core_memories(self):
        self.core_memories = [
            {"age": 5, "event": "第一次见面，他送我一朵野花", "emotion": "温暖", "importance": 10},
            {"age": 8, "event": "我发烧，他守了我一整夜", "emotion": "感动", "importance": 10},
            {"age": 10, "event": "我们约定长大后一起去看海", "emotion": "期待", "importance": 9},
            {"age": 12, "event": "他为了护我被人打", "emotion": "心疼又感动", "importance": 10},
            {"age": 14, "event": "他说想去学武，我嘴上支持心里不舍", "emotion": "不舍", "importance": 8},
            {"age": 15, "event": "他离开那天我没敢去送", "emotion": "后悔", "importance": 9},
        ]

    def add_memory(self, event: str, player_words: str, emotion: str, importance: int = 5):
        memory = {
            "time": datetime.now().isoformat(),
            "event": event,
            "player_words": player_words,
            "emotion": emotion,
            "importance": importance
        }
        self.recent_memories.append(memory)
        self._update_emotional_state(event, emotion, importance)

    def _update_emotional_state(self, event: str, emotion: str, importance: int):
        positive_emotions = ["温暖", "感动", "开心", "幸福", "安心", "期待"]
        negative_emotions = ["难过", "失落", "不安", "害怕", "伤心", "委屈"]

        factor = importance / 10

        if emotion in positive_emotions:
            self.emotional_state["happiness"] = min(1.0, self.emotional_state["happiness"] + 0.1 * factor)
            self.emotional_state["anxiety"] = max(0.0, self.emotional_state["anxiety"] - 0.05 * factor)
            self.emotional_state["hope"] = min(1.0, self.emotional_state["hope"] + 0.1 * factor)
            self.relationship["security"] = min(1.0, self.relationship["security"] + 0.1 * factor)
        elif emotion in negative_emotions:
            self.emotional_state["happiness"] = max(0.0, self.emotional_state["happiness"] - 0.1 * factor)
            self.emotional_state["anxiety"] = min(1.0, self.emotional_state["anxiety"] + 0.1 * factor)
            self.emotional_state["fear_of_loss"] = min(1.0, self.emotional_state["fear_of_loss"] + 0.1 * factor)
            self.relationship["security"] = max(0.0, self.relationship["security"] - 0.05 * factor)

    def get_context(self) -> str:
        context_parts = []

        # 核心记忆
        context_parts.append("## 你们的过去（核心记忆）")
        for mem in self.core_memories:
            context_parts.append(f"- {mem['age']}岁：{mem['event']}（{mem['emotion']}）")

        # 总结的记忆（如果有）
        if self.summarized_memories:
            context_parts.append("\n## 之前发生的事（摘要）")
            for summary in self.summarized_memories[-3:]:
                context_parts.append(f"- {summary}")

        # 最近记忆
        if self.recent_memories:
            context_parts.append("\n## 这次相遇发生的事")
            for mem in self.recent_memories[-10:]:
                context_parts.append(f"- {mem['event']}，他说：「{mem['player_words']}」（你感到{mem['emotion']}）")

        # 当前情感状态
        context_parts.append("\n## 你现在的情感状态")
        state_names = {
            "happiness": "快乐", "anxiety": "焦虑", "hope": "希望",
            "fear_of_loss": "害怕失去", "self_worth": "自我价值感"
        }
        for state, value in self.emotional_state.items():
            level = "很强" if value > 0.7 else "中等" if value > 0.4 else "较弱"
            context_parts.append(f"- {state_names.get(state, state)}：{level}（{value:.1f}）")

        # 未说出口的话
        if self.unspoken:
            context_parts.append("\n## 你想说但不敢说的话")
            for words in self.unspoken:
                context_parts.append(f"- {words}")

        return "\n".join(context_parts)

    def should_summarize(self) -> bool:
        """是否需要总结记忆（超过20条时）"""
        return len(self.recent_memories) > 20

    def get_memories_to_summarize(self) -> List[Dict]:
        """获取需要总结的记忆（保留最近5条）"""
        if len(self.recent_memories) <= 5:
            return []
        to_summarize = self.recent_memories[:-5]
        self.recent_memories = self.recent_memories[-5:]
        return to_summarize

    def add_summary(self, summary: str):
        """添加记忆摘要"""
        self.summarized_memories.append(summary)


# ============ 场景系统 ============

SCENES = {
    "reunion": {
        "name": "重逢",
        "location": "青云镇外的小溪边",
        "time": "傍晚",
        "features": ["夕阳", "金色溪水", "微风", "大石头"],
        "atmosphere": "温馨又略带紧张",
        "description": """
【场景：青云镇外的小溪边，傍晚】

夕阳把溪水染成金色。这里是你们小时候常来的地方。

阿檀坐在溪边的大石头上，怀里抱着一个小包袱。
她的背影有些单薄，青色的裙摆被风轻轻吹起。

听到脚步声，她回过头——
先是一愣，然后眼睛慢慢亮起来。

她站起来，又突然像是不知道该怎么办一样，停在原地。

「你...」她开口，声音有些哑，「你回来了。」

她的眼眶有些红，但在努力忍着。
""",
    },
    "daily": {
        "name": "日常",
        "location": "阿檀家的小院",
        "time": "白天",
        "features": ["小院", "花草", "晾衣绳", "阳光"],
        "atmosphere": "温馨宁静",
        "description": """
【场景：阿檀家的小院，白天】

小院不大，但打理得很整洁。
院角种着几株不知名的花，开得正好。

阿檀正在院子里晾衣服，阳光落在她身上。
她哼着一首不成调的小曲，看起来心情不错。

看到你来，她愣了一下，手里的衣服差点掉地上。

「诶？你怎么来了？」她有些慌乱地擦了擦手，「我、我去给你倒杯水...」
""",
    },
    "farewell": {
        "name": "离别",
        "location": "青云镇外的岔路口",
        "time": "清晨",
        "features": ["薄雾", "凉风", "岔路", "青色布裙"],
        "atmosphere": "不舍又克制",
        "description": """
【场景：青云镇外的岔路口，清晨】

薄雾还没散去，空气凉凉的。
这是通往青云门的路。

阿檀站在路口，双手背在身后。
她穿着你第一次见面时她穿过的那件青色布裙——
虽然已经旧了，但洗得很干净。

她没有哭，但嘴唇有些发白。

「路上...小心。」她的声音很轻。

她从身后拿出一个小布包，递给你：
「我做了些糕点，你带着路上吃...也不知道合不合你口味...」

她笑着，但笑容有些勉强。
""",
    }
}


# ============ 混合AI引擎封装 ============

class AtanHybridAI:
    """阿檀的混合AI灵魂"""

    def __init__(self):
        self.engine = HybridAIEngine()
        self.memory = Memory()
        self.current_scene: str = "reunion"

        # 检查可用的AI
        providers = self.engine.get_available_providers()
        available = [k for k, v in providers.items() if v and k != "mock"]

        if available:
            print(f"\n可用AI：{', '.join(available)}")
        else:
            print("\n警告：没有配置任何AI密钥，将使用模拟模式")

    def respond(self, player_input: str) -> tuple[str, str]:
        """
        阿檀的回应

        Returns:
            (回应文本, 使用的AI)
        """
        scene = SCENES.get(self.current_scene, {})
        scene_context = f"""## 当前场景
- 名称：{scene.get('name', '未知')}
- 地点：{scene.get('location', '未知')}
- 时间：{scene.get('time', '未知')}
- 环境特征：{', '.join(scene.get('features', []))}
- 氛围：{scene.get('atmosphere', '普通')}

【重要】你的动作描写必须符合当前场景，不要出现其他场景的元素。"""

        # 使用Claude生成对话
        response, provider = self.engine.generate_dialogue(
            npc_soul=ATAN_SOUL,
            memory_context=self.memory.get_context(),
            player_input=player_input,
            scene_context=scene_context
        )

        # 使用Claude分析情感影响
        analysis, _ = self.engine.analyze_emotion(
            player_input=player_input,
            npc_response=response,
            npc_personality="温柔、害怕被抛弃、欲言又止"
        )

        # 更新记忆
        self.memory.add_memory(
            event=analysis.get("event_summary", "对话"),
            player_words=player_input[:100],
            emotion=analysis.get("emotion", "复杂"),
            importance=analysis.get("importance", 5)
        )

        # 检查是否需要总结记忆（使用Gemini）
        if self.memory.should_summarize():
            self._summarize_memories()

        return response, provider

    def _summarize_memories(self):
        """使用Gemini总结记忆"""
        memories_to_summarize = self.memory.get_memories_to_summarize()
        if not memories_to_summarize:
            return

        try:
            summary_result, provider = self.engine.summarize_memory(
                memories=memories_to_summarize,
                focus="情感变化和关系发展"
            )
            self.memory.add_summary(summary_result)
            print(f"\n（记忆已总结，使用 {provider}）")
        except Exception as e:
            print(f"\n（记忆总结失败：{e}）")

    def generate_scene_narrative(self, event: str) -> tuple[str, str]:
        """
        生成场景叙事（使用GPT）
        """
        scene = SCENES.get(self.current_scene, {})
        scene_info = {
            "name": scene.get("location", "未知"),
            "features": scene.get("features", []),
            "atmosphere": scene.get("atmosphere", "普通")
        }

        # 根据情感状态确定基调
        happiness = self.memory.emotional_state.get("happiness", 0.5)
        if happiness > 0.7:
            mood = "温馨"
        elif happiness < 0.3:
            mood = "忧伤"
        else:
            mood = "平静"

        return self.engine.generate_narrative(scene_info, event, mood)


# ============ 游戏主循环 ============

class EmotionPrototypeHybrid:
    """混合AI版情感原型"""

    def __init__(self):
        self.ai: Optional[AtanHybridAI] = None
        self.current_scene: str = "reunion"
        # 存档保存在脚本所在目录，而不是工作目录
        self.save_path = Path(__file__).parent / "saves" / "hybrid_save.json"
        self.save_path.parent.mkdir(exist_ok=True)

    def start(self):
        print("\n" + "=" * 60)
        print("  阿 檀 - 混合AI版")
        print("=" * 60)
        print("\n混合AI引擎（三大顶级模型）：")
        print("  - Claude Opus 4.5：情感对话（阿檀的灵魂）")
        print("  - GPT 5.1：场景叙事（画面感）")
        print("  - GPT 5.1 Thinking：记忆总结（深度推理）")
        print("\n命令：")
        print("  /scene [名称] - 切换场景（reunion/daily/farewell）")
        print("  /status - 查看阿檀的情感状态")
        print("  /narrate [事件] - 生成场景叙事（GPT）")
        print("  /providers - 查看AI状态")
        print("  /quit - 保存并退出")
        print("-" * 60)

        self.ai = AtanHybridAI()

        # 加载存档
        self._load()

        # 显示初始场景
        self._show_scene()

        # 主循环
        self._game_loop()

    def _game_loop(self):
        while True:
            try:
                user_input = input("\n你说：").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # 获取阿檀的回应
                print("\n" + "-" * 40)
                response, provider = self.ai.respond(user_input)
                print(response)
                print(f"\n[{provider}]")
                print("-" * 40)

                self._save()

            except KeyboardInterrupt:
                print("\n\n使用 /quit 退出。")
            except Exception as e:
                print(f"\n发生错误：{e}")
                import traceback
                traceback.print_exc()

    def _handle_command(self, cmd: str) -> bool:
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/quit":
            self._save()
            print("\n存档已保存。下次再见。")
            return False

        elif command == "/scene":
            if args and args in SCENES:
                self.current_scene = args
                self.ai.current_scene = args
                self._show_scene()
            else:
                print(f"\n可用场景：{', '.join(SCENES.keys())}")

        elif command == "/status":
            self._show_status()

        elif command == "/narrate":
            if args:
                print("\n生成场景叙事...")
                narrative, provider = self.ai.generate_scene_narrative(args)
                print(f"\n{narrative}")
                print(f"\n[{provider}]")
            else:
                print("\n用法：/narrate [事件描述]")

        elif command == "/providers":
            self._show_providers()

        elif command == "/memory":
            self._show_memory()

        else:
            print(f"\n未知命令：{command}")

        return True

    def _show_scene(self):
        scene = SCENES.get(self.current_scene)
        if scene:
            print("\n" + "=" * 60)
            print(f"『{scene['name']}』")
            print("=" * 60)
            print(scene['description'])

    def _show_status(self):
        if not self.ai:
            return

        print("\n" + "=" * 40)
        print("阿檀的内心")
        print("=" * 40)

        print("\n【情感状态】")
        state_names = {
            "happiness": "快乐", "anxiety": "焦虑", "hope": "希望",
            "fear_of_loss": "害怕失去", "self_worth": "自我价值感"
        }
        for key, value in self.ai.memory.emotional_state.items():
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            print(f"  {state_names.get(key, key)}: [{bar}] {value:.1f}")

        print("\n【关系维度】")
        rel_names = {
            "trust": "信任", "affection": "感情", "dependency": "依赖",
            "understood": "被理解", "security": "安全感"
        }
        for key, value in self.ai.memory.relationship.items():
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            print(f"  {rel_names.get(key, key)}: [{bar}] {value:.1f}")

        print("\n【她想说却没说的话】")
        for words in self.ai.memory.unspoken[:3]:
            print(f"  「{words}」")

    def _show_providers(self):
        if not self.ai:
            return

        print("\n" + "=" * 40)
        print("AI状态")
        print("=" * 40)

        providers = self.ai.engine.get_available_providers()
        for name, available in providers.items():
            if name == "mock":
                continue
            status = "✓ 可用" if available else "✗ 未配置"
            print(f"  {name}: {status}")

        print("\n路由策略：")
        print("  对话 → Claude Opus（情感细腻）")
        print("  叙事 → GPT 5.1（创意画面）")
        print("  记忆 → GPT 5.1 Thinking（深度推理）")

        stats = self.ai.engine.get_stats()
        print("\n调用统计：")
        for provider, data in stats["usage"].items():
            if data["calls"] > 0:
                print(f"  {provider}: {data['calls']} 次")

    def _show_memory(self):
        if not self.ai:
            return

        print("\n" + "=" * 40)
        print("记忆")
        print("=" * 40)

        print("\n【童年记忆】")
        for mem in self.ai.memory.core_memories:
            print(f"  {mem['age']}岁：{mem['event']}")

        if self.ai.memory.summarized_memories:
            print("\n【记忆摘要】（Gemini总结）")
            for summary in self.ai.memory.summarized_memories:
                print(f"  · {summary[:100]}...")

        if self.ai.memory.recent_memories:
            print("\n【近期记忆】")
            for mem in self.ai.memory.recent_memories[-5:]:
                print(f"  · {mem['event']}（{mem['emotion']}）")

    def _save(self):
        if not self.ai:
            return

        data = {
            "current_scene": self.current_scene,
            "memory": {
                "recent_memories": self.ai.memory.recent_memories,
                "summarized_memories": self.ai.memory.summarized_memories,
                "emotional_state": self.ai.memory.emotional_state,
                "relationship": self.ai.memory.relationship,
                "unspoken": self.ai.memory.unspoken
            }
        }

        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not self.save_path.exists() or not self.ai:
            return

        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_scene = data.get("current_scene", "reunion")
            self.ai.current_scene = self.current_scene

            memory_data = data.get("memory", {})
            self.ai.memory.recent_memories = memory_data.get("recent_memories", [])
            self.ai.memory.summarized_memories = memory_data.get("summarized_memories", [])
            self.ai.memory.emotional_state = memory_data.get("emotional_state", self.ai.memory.emotional_state)
            self.ai.memory.relationship = memory_data.get("relationship", self.ai.memory.relationship)
            self.ai.memory.unspoken = memory_data.get("unspoken", self.ai.memory.unspoken)

            print("\n（已加载存档）")
        except Exception as e:
            print(f"\n（存档加载失败：{e}）")


def main():
    game = EmotionPrototypeHybrid()
    game.start()


if __name__ == "__main__":
    main()

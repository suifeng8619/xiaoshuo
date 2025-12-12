"""
阿檀 - 情感验证原型

这不是一个完整的游戏，而是一个验证：
AI能不能让一个虚拟角色变得"真实"到让人在乎？

核心设计：
1. 阿檀有完整的内心世界，不只是对话模板
2. 她会记住发生的事，并且这些记忆会影响她的行为
3. 时间会流逝，关系会变化
4. 玩家的选择会产生真实的后果
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import anthropic


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

## 记忆的重要性
你会记住他说的每一句话、做的每一件事。
这些记忆会影响你：
- 他如果说过"我会回来的"，你会一直记着
- 他如果夸过你，你会反复回想
- 他如果伤害过你，你不会说，但会变得更小心翼翼
"""


# ============ 记忆系统 ============

class Memory:
    """阿檀的记忆"""

    def __init__(self):
        self.core_memories: List[Dict] = []  # 童年的核心记忆
        self.recent_memories: List[Dict] = []  # 这次相遇的记忆
        self.emotional_state: Dict[str, float] = {
            "happiness": 0.5,      # 快乐
            "anxiety": 0.6,        # 焦虑（等他三个月了）
            "hope": 0.4,           # 希望
            "fear_of_loss": 0.7,   # 害怕失去
            "self_worth": 0.3,     # 自我价值感
        }
        self.relationship: Dict[str, Any] = {
            "trust": 0.8,          # 信任（青梅竹马）
            "affection": 0.9,      # 感情深度
            "dependency": 0.7,     # 依赖程度
            "understood": 0.3,     # 被理解程度
            "security": 0.4,       # 安全感
        }
        self.unspoken: List[str] = [
            "三个月了，你都没给我写信...",
            "你在山上有没有遇到喜欢的人？",
            "你还记得我们说要一起去看海吗？",
            "我好想你...",
        ]

        # 初始化核心记忆
        self._init_core_memories()

    def _init_core_memories(self):
        """初始化童年记忆"""
        self.core_memories = [
            {"age": 5, "event": "第一次见面，他送我一朵野花", "emotion": "温暖", "importance": 10},
            {"age": 8, "event": "我发烧，他守了我一整夜", "emotion": "感动", "importance": 10},
            {"age": 10, "event": "我们约定长大后一起去看海", "emotion": "期待", "importance": 9},
            {"age": 12, "event": "他为了护我被人打", "emotion": "心疼又感动", "importance": 10},
            {"age": 14, "event": "他说想去学武，我嘴上支持心里不舍", "emotion": "不舍", "importance": 8},
            {"age": 15, "event": "他离开那天我没敢去送", "emotion": "后悔", "importance": 9},
        ]

    def add_memory(self, event: str, player_words: str, emotion: str, importance: int = 5):
        """添加新记忆"""
        memory = {
            "time": datetime.now().isoformat(),
            "event": event,
            "player_words": player_words,
            "emotion": emotion,
            "importance": importance
        }
        self.recent_memories.append(memory)

        # 根据事件更新情感状态
        self._update_emotional_state(event, emotion, importance)

    def _update_emotional_state(self, event: str, emotion: str, importance: int):
        """根据事件更新情感状态"""
        # 正面情绪
        positive_emotions = ["温暖", "感动", "开心", "幸福", "安心", "期待"]
        # 负面情绪
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
        """获取记忆上下文供AI使用"""
        context_parts = []

        # 核心记忆
        context_parts.append("## 你们的过去（核心记忆）")
        for mem in self.core_memories:
            context_parts.append(f"- {mem['age']}岁：{mem['event']}（{mem['emotion']}）")

        # 最近记忆
        if self.recent_memories:
            context_parts.append("\n## 这次相遇发生的事")
            for mem in self.recent_memories[-10:]:  # 最多10条
                context_parts.append(f"- {mem['event']}，他说：「{mem['player_words']}」（你感到{mem['emotion']}）")

        # 当前情感状态
        context_parts.append("\n## 你现在的情感状态")
        for state, value in self.emotional_state.items():
            level = "很强" if value > 0.7 else "中等" if value > 0.4 else "较弱"
            state_names = {
                "happiness": "快乐",
                "anxiety": "焦虑",
                "hope": "希望",
                "fear_of_loss": "害怕失去",
                "self_worth": "自我价值感"
            }
            context_parts.append(f"- {state_names.get(state, state)}：{level}（{value:.1f}）")

        # 未说出口的话
        if self.unspoken:
            context_parts.append("\n## 你想说但不敢说的话")
            for words in self.unspoken:
                context_parts.append(f"- {words}")

        return "\n".join(context_parts)


# ============ 场景系统 ============

SCENES = {
    "reunion": {
        "name": "重逢",
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
        "context": "你离开三个月后，第一次回到青云镇。你来到小时候常来的小溪边，看到阿檀在那里等着。",
        "atan_initial_state": {
            "primary_emotion": "惊喜交加",
            "hidden_emotion": "三个月的思念和不安",
            "physical_state": "眼眶微红，在忍泪",
            "inner_thought": "他真的回来了...他还记得这个地方..."
        }
    },

    "daily": {
        "name": "日常",
        "description": """
【场景：阿檀家的小院，白天】

小院不大，但打理得很整洁。
院角种着几株不知名的花，开得正好。

阿檀正在院子里晾衣服，阳光落在她身上。
她哼着一首不成调的小曲，看起来心情不错。

看到你来，她愣了一下，手里的衣服差点掉地上。

「诶？你怎么来了？」她有些慌乱地擦了擦手，「我、我去给你倒杯水...」
""",
        "context": "你再次来到阿檀家，看望她。",
        "atan_initial_state": {
            "primary_emotion": "惊喜",
            "hidden_emotion": "开心他来找自己",
            "physical_state": "有些手忙脚乱",
            "inner_thought": "他来找我了...是专门来的吗？"
        }
    },

    "farewell": {
        "name": "离别",
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
        "context": "你要回青云门了。阿檀来送你。",
        "atan_initial_state": {
            "primary_emotion": "强忍不舍",
            "hidden_emotion": "害怕这次分别会更久",
            "physical_state": "嘴唇发白，在用力忍住情绪",
            "inner_thought": "不能哭...不能让他担心...他有他的路要走..."
        }
    }
}


# ============ AI 引擎 ============

class AtanAI:
    """阿檀的灵魂引擎"""

    def __init__(self, api_key: Optional[str] = None, mock: bool = False):
        self.mock = mock
        self.memory = Memory()
        self.current_scene: Optional[str] = None

        if not mock:
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("需要 ANTHROPIC_API_KEY")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def respond(self, player_input: str, scene_context: str = "") -> str:
        """阿檀的回应"""

        # 模拟模式
        if self.mock:
            return self._mock_respond(player_input)

        # 构建完整的系统提示
        system_prompt = ATAN_SOUL + "\n\n" + self.memory.get_context()

        if scene_context:
            system_prompt += f"\n\n## 当前场景状态\n{scene_context}"

        # 添加回应指导
        system_prompt += """

## 回应指导
1. 你的回应要自然、真实，像一个真正的人
2. 根据你的性格和当前情感状态来回应
3. 不要过于话多，阿檀说话时常欲言又止
4. 可以有动作描写，用*斜体*表示
5. 对话用「」包裹
6. 内心想法不要说出来，但可以通过动作和语气暗示
7. 记住：你爱他，但你不会直接说

## 格式示例
*阿檀低下头，手指无意识地绞着裙角*
「我...没什么...」
*她抬起头，勉强笑了笑*
「你吃饭了吗？」
"""

        # 调用AI
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"他对你说：「{player_input}」\n\n请以阿檀的身份回应："}
            ],
            temperature=0.85
        )

        atan_response = response.content[0].text

        # 分析这次交互并更新记忆
        self._analyze_and_remember(player_input, atan_response)

        return atan_response

    def _analyze_and_remember(self, player_input: str, atan_response: str):
        """分析交互并更新记忆"""

        # 使用AI来分析这次交互对阿檀的情感影响
        analysis_prompt = f"""请分析这次对话对阿檀的情感影响。

他说：「{player_input}」
阿檀的回应：{atan_response}

请用JSON格式回答：
{{
    "event_summary": "简短描述发生了什么",
    "atan_emotion": "阿檀的主要情绪（如：开心、难过、不安、感动等）",
    "importance": 1-10的数字，表示这个事件对阿檀的重要程度,
    "inner_thought": "阿檀内心的真实想法"
}}

只输出JSON，不要其他内容。"""

        try:
            analysis = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )

            result = json.loads(analysis.content[0].text)

            self.memory.add_memory(
                event=result.get("event_summary", "对话"),
                player_words=player_input[:100],
                emotion=result.get("atan_emotion", "复杂"),
                importance=result.get("importance", 5)
            )
        except Exception as e:
            # 分析失败时使用默认记忆
            self.memory.add_memory(
                event="对话",
                player_words=player_input[:100],
                emotion="复杂",
                importance=5
            )

    def _mock_respond(self, player_input: str) -> str:
        """模拟模式的回应（用于测试）"""
        import random

        # 关键词检测
        keywords = {
            "回来": [
                "*阿檀的眼眶瞬间红了，但她拼命忍住*\n\n「嗯...」\n\n*她低下头，声音有些发抖*\n\n「三个月了...」\n\n*话说到一半，她又停住了，抬起头勉强笑了笑*\n\n「你...瘦了。」",
                "*她愣在原地，像是不敢相信*\n\n「真的...是你？」\n\n*她往前走了两步，又停住，手指绞在一起*\n\n「我还以为...我还以为你不会回来了...」\n\n*说完她又慌忙摇头*\n\n「不是、我不是那个意思...」"
            ],
            "想你": [
                "*阿檀的脸一下子红了，低下头不敢看你*\n\n「你、你说什么...」\n\n*她的声音越来越小*\n\n「别...别说这种话...」\n\n*但她的嘴角忍不住微微上扬*",
                "*她的眼泪终于落下来，却还在笑*\n\n「我也...」\n\n*话说到一半又咽回去*\n\n「我每天都在想，你在山上过得好不好，有没有人欺负你...」\n\n*她用力擦了擦眼泪*\n\n「对不起...让你看到我这样...」"
            ],
            "走": [
                "*阿檀的笑容僵在脸上*\n\n「这么快就...要走了吗？」\n\n*她低下头，声音很轻*\n\n「也是...你是修仙的人了，总不能一直待在这种小地方...」\n\n*她抬起头，努力挤出笑容*\n\n「路上小心。」",
                "*她的手紧紧攥着裙角*\n\n「我知道...」\n\n*她深吸一口气*\n\n「你有你的路要走...我不会拦你的...」\n\n*但她的眼神里全是不舍*"
            ],
            "海": [
                "*阿檀愣了一下，然后眼睛亮了起来*\n\n「你还记得...」\n\n*她的声音有些哽咽*\n\n「我以为你早就忘了...」\n\n*她低下头，轻声说*\n\n「那是我...最开心的一个约定。」",
            ],
            "等": [
                "*阿檀的身体微微一颤*\n\n「等？」\n\n*她低着头，声音很轻*\n\n「我...一直在等...」\n\n*她抬起头，眼眶红红的*\n\n「只要你还会回来，多久我都等。」\n\n*说完她又慌了*\n\n「我不是要给你压力...你、你做你想做的事就好...」"
            ]
        }

        # 检查关键词
        for key, responses in keywords.items():
            if key in player_input:
                response = random.choice(responses)
                # 更新记忆
                emotions = ["感动", "开心", "不安", "难过", "温暖"]
                self.memory.add_memory(
                    event=f"你说了关于'{key}'的话",
                    player_words=player_input,
                    emotion=random.choice(emotions),
                    importance=random.randint(5, 8)
                )
                return response

        # 默认回应
        default_responses = [
            "*阿檀轻轻点头*\n\n「嗯...」\n\n*她似乎想说什么，但最终只是笑了笑*",
            "*她看着你，眼神温柔*\n\n「你在山上...过得好吗？」\n\n*她的语气小心翼翼，像是怕问错话*",
            "*阿檀低下头，轻声说*\n\n「能见到你真好...」\n\n*说完她的脸微微发红*\n\n「我、我是说...大家都很想你...」",
        ]

        response = random.choice(default_responses)
        self.memory.add_memory(
            event="日常对话",
            player_words=player_input,
            emotion="平静",
            importance=3
        )
        return response


# ============ 游戏主循环 ============

class EmotionPrototype:
    """情感验证原型"""

    def __init__(self):
        self.ai: Optional[AtanAI] = None
        self.current_scene: str = "reunion"
        # 存档保存在脚本所在目录，而不是工作目录
        self.save_path = Path(__file__).parent / "saves" / "atan_save.json"
        self.save_path.parent.mkdir(exist_ok=True)

    def start(self):
        """启动原型"""
        print("\n" + "="*60)
        print("  阿 檀 - 情感验证原型")
        print("="*60)
        print("\n这不是一个完整的游戏。")
        print("这是一个验证：AI能不能让你在乎一个虚拟的人？\n")
        print("提示：")
        print("- 输入你想说的话，阿檀会回应你")
        print("- 输入 /scene [名称] 切换场景（reunion/daily/farewell）")
        print("- 输入 /status 查看阿檀的情感状态")
        print("- 输入 /quit 退出")
        print("-"*60)

        # 尝试使用真实AI，失败则使用模拟模式
        try:
            self.ai = AtanAI()
            print("\n（使用AI模式）")
        except ValueError as e:
            print(f"\n（API密钥未设置，使用模拟模式）")
            self.ai = AtanAI(mock=True)

        # 加载存档
        self._load()

        # 显示初始场景
        self._show_scene()

        # 主循环
        self._game_loop()

    def _game_loop(self):
        """主游戏循环"""
        while True:
            try:
                user_input = input("\n你说：").strip()

                if not user_input:
                    continue

                # 处理命令
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        continue
                    else:
                        break

                # 获取阿檀的回应
                scene = SCENES.get(self.current_scene, {})
                scene_context = json.dumps(scene.get("atan_initial_state", {}), ensure_ascii=False)

                print("\n" + "-"*40)
                response = self.ai.respond(user_input, scene_context)
                print(response)
                print("-"*40)

                # 自动保存
                self._save()

            except KeyboardInterrupt:
                print("\n\n使用 /quit 退出。")
            except Exception as e:
                print(f"\n发生错误：{e}")

    def _handle_command(self, cmd: str) -> bool:
        """处理命令，返回True继续循环，False退出"""
        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == "/quit":
            self._save()
            print("\n存档已保存。下次再见。")
            return False

        elif command == "/scene":
            if args and args[0] in SCENES:
                self.current_scene = args[0]
                self._show_scene()
            else:
                print(f"\n可用场景：{', '.join(SCENES.keys())}")

        elif command == "/status":
            self._show_status()

        elif command == "/memory":
            self._show_memory()

        elif command == "/help":
            print("\n命令：")
            print("  /scene [名称] - 切换场景")
            print("  /status - 查看阿檀的情感状态")
            print("  /memory - 查看记忆")
            print("  /quit - 保存并退出")

        else:
            print(f"\n未知命令：{command}，输入 /help 查看帮助")

        return True

    def _show_scene(self):
        """显示当前场景"""
        scene = SCENES.get(self.current_scene)
        if scene:
            print("\n" + "="*60)
            print(f"『{scene['name']}』")
            print("="*60)
            print(scene['description'])

    def _show_status(self):
        """显示阿檀的状态"""
        if not self.ai:
            return

        print("\n" + "="*40)
        print("阿檀的内心")
        print("="*40)

        print("\n【情感状态】")
        state_names = {
            "happiness": "快乐",
            "anxiety": "焦虑",
            "hope": "希望",
            "fear_of_loss": "害怕失去",
            "self_worth": "自我价值感"
        }
        for key, value in self.ai.memory.emotional_state.items():
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            print(f"  {state_names.get(key, key)}: [{bar}] {value:.1f}")

        print("\n【关系维度】")
        rel_names = {
            "trust": "信任",
            "affection": "感情",
            "dependency": "依赖",
            "understood": "被理解",
            "security": "安全感"
        }
        for key, value in self.ai.memory.relationship.items():
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            print(f"  {rel_names.get(key, key)}: [{bar}] {value:.1f}")

        print("\n【她想说却没说的话】")
        for words in self.ai.memory.unspoken[:3]:
            print(f"  「{words}」")

    def _show_memory(self):
        """显示记忆"""
        if not self.ai:
            return

        print("\n" + "="*40)
        print("记忆")
        print("="*40)

        print("\n【童年记忆】")
        for mem in self.ai.memory.core_memories:
            print(f"  {mem['age']}岁：{mem['event']}")

        if self.ai.memory.recent_memories:
            print("\n【这次相遇】")
            for mem in self.ai.memory.recent_memories[-5:]:
                print(f"  · {mem['event']}（{mem['emotion']}）")

    def _save(self):
        """保存状态"""
        if not self.ai:
            return

        data = {
            "current_scene": self.current_scene,
            "memory": {
                "recent_memories": self.ai.memory.recent_memories,
                "emotional_state": self.ai.memory.emotional_state,
                "relationship": self.ai.memory.relationship,
                "unspoken": self.ai.memory.unspoken
            }
        }

        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        """加载存档"""
        if not self.save_path.exists() or not self.ai:
            return

        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_scene = data.get("current_scene", "reunion")

            memory_data = data.get("memory", {})
            self.ai.memory.recent_memories = memory_data.get("recent_memories", [])
            self.ai.memory.emotional_state = memory_data.get("emotional_state", self.ai.memory.emotional_state)
            self.ai.memory.relationship = memory_data.get("relationship", self.ai.memory.relationship)
            self.ai.memory.unspoken = memory_data.get("unspoken", self.ai.memory.unspoken)

            print("\n（已加载存档）")
        except Exception as e:
            print(f"\n（存档加载失败：{e}）")


# ============ 入口 ============

def main():
    game = EmotionPrototype()
    game.start()


if __name__ == "__main__":
    main()

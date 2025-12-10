# 技术架构设计文档

## 架构理念

**AI是灵魂，不是装饰。**

这不是一个"带AI描写的传统游戏"，而是一个"AI驱动的叙事体验"。

架构的核心目标：
1. **让AI真正理解情境** —— 完整的上下文构建
2. **让NPC真正"活着"** —— 持久记忆和人格一致性
3. **让选择真正有后果** —— 事件系统和状态追踪
4. **让世界真正会变化** —— 时间系统和世界演化

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Game Shell                               │
│                      (命令行交互层)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Game Director                               │
│                    (游戏导演/总控)                               │
│  - 场景调度                                                      │
│  - 剧情推进                                                      │
│  - 事件分发                                                      │
└───┬───────────────┬───────────────┬───────────────┬─────────────┘
    │               │               │               │
┌───▼───┐      ┌────▼────┐    ┌─────▼─────┐   ┌────▼────┐
│ World │      │Character│    │   Story   │   │   AI    │
│Manager│      │ Manager │    │  Manager  │   │ Engine  │
└───┬───┘      └────┬────┘    └─────┬─────┘   └────┬────┘
    │               │               │               │
    │          ┌────▼────┐         │               │
    │          │ Memory  │◄────────┘               │
    │          │ System  │                         │
    │          └────┬────┘                         │
    │               │                              │
    └───────────────┴──────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│                      Persistence Layer                           │
│                       (持久化层)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. Game Director (游戏导演)

游戏的总控制器，负责协调所有子系统。

```python
class GameDirector:
    """
    游戏导演，负责：
    - 游戏主循环
    - 场景切换
    - 事件调度
    - 时间推进
    """

    def __init__(self):
        self.world = WorldManager()
        self.characters = CharacterManager()
        self.story = StoryManager()
        self.ai = AIEngine()
        self.event_bus = EventBus()

    def run(self):
        """主循环"""
        while self.is_running:
            # 1. 获取玩家输入
            player_input = self.get_input()

            # 2. 解析意图
            intent = self.parse_intent(player_input)

            # 3. 执行行动
            result = self.execute_action(intent)

            # 4. 触发后果
            self.event_bus.emit(result.events)

            # 5. 推进时间
            self.world.advance_time(result.time_cost)

            # 6. 生成叙事
            narrative = self.ai.narrate(result)

            # 7. 输出
            self.display(narrative)
```

### 2. World Manager (世界管理器)

管理游戏世界的状态。

```python
class WorldManager:
    """
    世界管理器，负责：
    - 时间系统
    - 地点系统
    - 势力系统
    - 世界事件
    """

    def __init__(self):
        self.time = TimeSystem()
        self.locations = LocationSystem()
        self.factions = FactionSystem()
        self.world_events = WorldEventSystem()

    def advance_time(self, duration: TimeDelta):
        """推进时间"""
        self.time.advance(duration)

        # 时间推进会触发各种变化
        self.world_events.check_triggers(self.time.current)
        self.factions.update_relations()
        self.locations.update_states()

    def get_current_context(self) -> WorldContext:
        """获取当前世界上下文（给AI用）"""
        return WorldContext(
            time=self.time.current,
            season=self.time.season,
            location=self.player_location,
            nearby_events=self.world_events.get_nearby(),
            faction_states=self.factions.get_summary()
        )
```

### 3. Character Manager (角色管理器)

管理所有角色，包括玩家和NPC。

```python
class CharacterManager:
    """
    角色管理器，负责：
    - 玩家角色
    - NPC管理
    - 关系网络
    """

    def __init__(self):
        self.player = None
        self.npcs: Dict[str, NPC] = {}
        self.relationships = RelationshipGraph()

    def get_npc(self, npc_id: str) -> NPC:
        """获取NPC"""
        return self.npcs.get(npc_id)

    def update_relationship(self, npc_id: str, changes: RelationshipChange):
        """更新关系"""
        npc = self.npcs[npc_id]
        npc.relationship.apply_change(changes)

        # 关系变化可能触发事件
        if npc.relationship.crossed_threshold():
            self.event_bus.emit(RelationshipEvent(npc_id, changes))

    def get_npc_context(self, npc_id: str) -> NPCContext:
        """获取NPC上下文（给AI用）"""
        npc = self.npcs[npc_id]
        return NPCContext(
            basic_info=npc.info,
            personality=npc.personality,
            relationship=npc.relationship,
            memories=npc.memory.get_relevant(),
            current_mood=npc.mood,
            current_goals=npc.goals
        )
```

### 4. Memory System (记忆系统)

最核心的系统之一，让NPC"记住"一切。

```python
class MemorySystem:
    """
    记忆系统，负责：
    - 存储记忆
    - 检索相关记忆
    - 记忆衰减
    """

    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.memories: List[Memory] = []
        self.emotional_state = EmotionalState()

    def add_memory(self, event: Event, emotional_impact: EmotionalImpact):
        """添加记忆"""
        memory = Memory(
            event=event,
            timestamp=current_time(),
            importance=self._calculate_importance(event, emotional_impact),
            emotional_impact=emotional_impact,
            tags=self._extract_tags(event)
        )
        self.memories.append(memory)
        self.emotional_state.update(emotional_impact)

    def get_relevant(self, context: QueryContext, limit: int = 10) -> List[Memory]:
        """获取相关记忆"""
        # 基于以下因素检索：
        # 1. 相关性（标签匹配）
        # 2. 重要性
        # 3. 时间近度
        # 4. 情感强度

        scored_memories = []
        for memory in self.memories:
            score = self._calculate_relevance(memory, context)
            scored_memories.append((score, memory))

        scored_memories.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scored_memories[:limit]]

    def get_core_memories(self) -> List[Memory]:
        """获取核心记忆（永不遗忘的）"""
        return [m for m in self.memories if m.importance >= 8]
```

### 5. AI Engine (AI引擎)

与AI交互的核心模块。

```python
class AIEngine:
    """
    AI引擎，负责：
    - 构建上下文
    - 调用AI生成
    - 解析AI响应
    """

    def __init__(self):
        self.client = AnthropicClient()
        self.context_builder = ContextBuilder()

    def generate_dialogue(self, npc: NPC, player_says: str) -> DialogueResponse:
        """生成NPC对话"""

        # 1. 构建上下文
        context = self.context_builder.build_dialogue_context(
            npc=npc,
            player_says=player_says,
            world_state=self.world.get_current_context(),
            recent_events=self.get_recent_events()
        )

        # 2. 构建提示词
        prompt = self._build_dialogue_prompt(context)

        # 3. 调用AI
        response = self.client.generate(
            system=DIALOGUE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        # 4. 解析响应
        return self._parse_dialogue_response(response)

    def narrate_scene(self, scene: Scene, events: List[Event]) -> str:
        """生成场景叙述"""
        context = self.context_builder.build_narrative_context(scene, events)
        prompt = self._build_narrative_prompt(context)
        return self.client.generate(
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

    def make_npc_decision(self, npc: NPC, situation: Situation) -> NPCAction:
        """让NPC做决策"""
        context = self.context_builder.build_decision_context(npc, situation)
        prompt = self._build_decision_prompt(context)
        response = self.client.generate(
            system=NPC_DECISION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_decision_response(response)
```

### 6. Story Manager (剧情管理器)

管理剧情进度和触发器。

```python
class StoryManager:
    """
    剧情管理器，负责：
    - 主线进度
    - 支线任务
    - 剧情触发器
    - 标记系统
    """

    def __init__(self):
        self.main_quest_progress = 0
        self.flags: Dict[str, Any] = {}
        self.triggers: List[StoryTrigger] = []
        self.active_quests: List[Quest] = []

    def check_triggers(self, event: Event):
        """检查剧情触发器"""
        for trigger in self.triggers:
            if trigger.should_fire(event, self.flags):
                self._fire_trigger(trigger)

    def set_flag(self, flag_name: str, value: Any):
        """设置剧情标记"""
        self.flags[flag_name] = value

    def get_current_chapter(self) -> Chapter:
        """获取当前章节"""
        return CHAPTERS[self.main_quest_progress]
```

### 7. Event Bus (事件总线)

解耦各系统的核心。

```python
class EventBus:
    """
    事件总线，负责：
    - 事件订阅
    - 事件发布
    - 事件处理
    """

    def __init__(self):
        self.handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        self.handlers[event_type].append(handler)

    def emit(self, event: Event):
        """发布事件"""
        for handler in self.handlers[event.type]:
            handler(event)

    def emit_many(self, events: List[Event]):
        """批量发布事件"""
        for event in events:
            self.emit(event)
```

---

## 数据模型

### 角色数据

```python
@dataclass
class Character:
    """角色基础数据"""
    id: str
    name: str
    is_player: bool = False

    # 基础属性
    realm: Realm                    # 境界
    attributes: Attributes          # 属性
    skills: List[Skill]            # 技能
    equipment: Equipment           # 装备
    inventory: Inventory           # 背包

    # 状态
    status: CharacterStatus        # 当前状态
    location: str                  # 当前位置

    # 只有NPC有
    personality: Optional[Personality] = None
    relationship: Optional[Relationship] = None
    memory: Optional[MemorySystem] = None
    goals: Optional[List[Goal]] = None


@dataclass
class Personality:
    """性格定义"""
    core_traits: List[str]         # 核心特质
    speaking_style: str            # 说话风格
    values: List[str]              # 价值观
    fears: List[str]               # 恐惧
    desires: List[str]             # 渴望
    taboos: List[str]              # 禁忌（不会说/做的事）


@dataclass
class Relationship:
    """关系数据"""
    trust: int = 50                # 信任度 0-100
    affection: int = 50            # 好感度 0-100
    respect: int = 50              # 尊敬度 0-100
    dependency: int = 0            # 依赖度 0-100
    understanding: int = 0         # 理解度 0-100

    tags: List[str] = field(default_factory=list)  # 态度标签
    unresolved: List[str] = field(default_factory=list)  # 未解决的情感

    def apply_change(self, change: RelationshipChange):
        """应用变化"""
        self.trust = clamp(self.trust + change.trust, 0, 100)
        self.affection = clamp(self.affection + change.affection, 0, 100)
        # ... 其他属性

    def crossed_threshold(self) -> Optional[str]:
        """检查是否跨越阈值"""
        if self.affection >= 80 and "深厚情感" not in self.tags:
            self.tags.append("深厚情感")
            return "affection_high"
        if self.trust < 20 and "信任危机" not in self.tags:
            self.tags.append("信任危机")
            return "trust_crisis"
        return None
```

### 记忆数据

```python
@dataclass
class Memory:
    """记忆条目"""
    id: str
    event: Event                   # 事件
    timestamp: GameTime            # 时间戳
    importance: int                # 重要度 1-10
    emotional_impact: EmotionalImpact  # 情感影响
    tags: List[str]               # 标签（用于检索）

    # 元数据
    can_forget: bool = True        # 是否可以遗忘
    referenced_count: int = 0      # 被提及次数


@dataclass
class EmotionalImpact:
    """情感影响"""
    emotions: List[str]            # 触发的情感
    intensity: int                 # 强度 1-10
    attitude_change: Dict[str, int]  # 态度变化


@dataclass
class Event:
    """事件"""
    type: EventType
    description: str
    participants: List[str]        # 参与者ID
    location: str
    consequences: List[str]        # 后果描述
```

### 世界数据

```python
@dataclass
class WorldState:
    """世界状态"""
    current_time: GameTime
    player_location: str
    faction_relations: Dict[str, Dict[str, int]]
    world_events: List[WorldEvent]
    flags: Dict[str, Any]


@dataclass
class GameTime:
    """游戏时间"""
    year: int
    month: int
    day: int
    hour: int

    @property
    def season(self) -> str:
        if self.month in [3, 4, 5]:
            return "spring"
        elif self.month in [6, 7, 8]:
            return "summer"
        elif self.month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"

    def advance(self, hours: int = 0, days: int = 0, months: int = 0, years: int = 0):
        """推进时间"""
        # ... 实现时间推进逻辑
```

---

## AI提示词设计

### 系统提示词结构

```python
DIALOGUE_SYSTEM_PROMPT = """
你是一个角色扮演AI，负责扮演游戏中的NPC。

## 你的角色
你正在扮演：{npc_name}

## 角色设定
{personality_description}

## 与玩家的关系
{relationship_description}

## 相关记忆
{relevant_memories}

## 当前情境
{current_situation}

## 规则
1. 你必须始终保持角色，不能打破第四面墙
2. 你的回应必须符合角色的性格和说话风格
3. 你要考虑与玩家的关系和过去的记忆
4. 你有自己的想法和情感，不是玩家的提线木偶
5. 你可以拒绝玩家的请求，可以生气，可以有自己的诉求
6. 回应要简洁自然，像真人对话，不要过于书面化

## 输出格式
直接输出角色的对话，不要加引号或角色名前缀。
如果需要描述动作或表情，用括号包裹，如：(她低下头)

## 现在，玩家对你说了什么...
"""


NARRATIVE_SYSTEM_PROMPT = """
你是一个叙事AI，负责生成游戏中的场景描写和事件叙述。

## 风格要求
- 简洁有力，不堆砌辞藻
- 重要时刻才浓墨重彩
- 多用短句，制造节奏感
- 留白比说满更好
- 像网文的简洁，但不要轻浮

## 示例
差的写法：
"阿檀那双如秋水般的眼眸中泛着点点泪光，她樱唇轻启，用如黄莺般悦耳的声音说道..."

好的写法：
"阿檀看着你，眼圈红了。"

## 现在请描写以下场景...
"""


NPC_DECISION_SYSTEM_PROMPT = """
你是一个NPC决策AI，负责决定NPC在特定情境下的行为。

## 你的角色
{npc_name}

## 性格特征
{personality}

## 当前目标
{goals}

## 与玩家的关系
{relationship}

## 当前情境
{situation}

## 决策规则
1. 行为必须符合角色性格
2. 要考虑与玩家的关系
3. 要追求角色自己的目标
4. 不要总是配合玩家，NPC有自己的意志

## 输出格式
输出一个JSON，包含：
- action: 采取的行动
- reason: 为什么这样做（不会告诉玩家）
- dialogue: 如果说话，说什么
- emotional_change: 情感变化
"""
```

---

## 存储设计

### 文件结构

```
data/
├── saves/
│   ├── save_001/
│   │   ├── world.json          # 世界状态
│   │   ├── player.json         # 玩家数据
│   │   ├── npcs/
│   │   │   ├── atan.json       # 阿檀数据
│   │   │   ├── shifu.json      # 师父数据
│   │   │   └── ...
│   │   ├── story.json          # 剧情进度
│   │   └── meta.json           # 存档元数据
│   └── ...
├── config/
│   ├── world.yaml              # 世界设定
│   ├── characters.yaml         # 角色设定
│   ├── skills.yaml             # 技能配置
│   ├── items.yaml              # 物品配置
│   └── story/
│       ├── chapter1.yaml       # 第一章剧情
│       └── ...
└── prompts/
    ├── dialogue.txt            # 对话提示词
    ├── narrative.txt           # 叙事提示词
    └── decision.txt            # 决策提示词
```

### 存档格式

```json
// player.json
{
  "id": "player_001",
  "name": "玩家名",
  "realm": {
    "major": "练气期",
    "minor": 3,
    "exp": 340,
    "exp_to_next": 500
  },
  "attributes": {
    "hp": 85,
    "hp_max": 100,
    "mp": 40,
    "mp_max": 50,
    "attack": 25,
    "defense": 15,
    "speed": 110
  },
  "skills": ["basic_sword", "cloud_sword"],
  "equipment": {
    "weapon": "iron_sword",
    "armor": null
  },
  "inventory": [...],
  "currency": {
    "gold": 150,
    "spirit_stones": 5
  },
  "karma": 10,
  "location": "云霞峰"
}

// npcs/atan.json
{
  "id": "atan",
  "name": "沈檀儿",
  "nickname": "阿檀",
  "status": "alive",
  "location": "青云门外门",
  "relationship": {
    "trust": 85,
    "affection": 70,
    "respect": 60,
    "dependency": 65,
    "understanding": 55,
    "tags": ["青梅竹马", "担忧"],
    "unresolved": ["玩家上次历练差点死了"]
  },
  "memories": [
    {
      "id": "mem_001",
      "event": "第一次相遇",
      "timestamp": "第0年春",
      "importance": 10,
      "emotional_impact": {
        "emotions": ["感激", "依赖"],
        "intensity": 9
      },
      "can_forget": false
    },
    ...
  ],
  "current_mood": "担忧",
  "current_goals": ["照顾好自己", "等玩家回来", "学会修炼"]
}
```

---

## 实现优先级

### Phase 1: 最小可玩版本 (2周)

```yaml
目标: 能玩完序章，体验核心循环

实现:
  - GameDirector 基础框架
  - 简单的命令解析
  - 阿檀的基础对话（AI生成）
  - 基础的记忆系统（只记住最近10件事）
  - 简单的时间流逝
  - 一个场景（青云门）
  - 一个战斗（新手试炼）

不实现:
  - 复杂的关系计算
  - 完整的技能系统
  - 多场景
  - 存档读取
```

### Phase 2: 核心体验 (2周)

```yaml
目标: 完成第一幕，关系系统可用

实现:
  - 完整的记忆系统
  - 关系数值和阈值
  - 多场景切换
  - 师父、大师兄、小师妹
  - 第一幕剧情
  - 存档系统

不实现:
  - 复杂的世界事件
  - 门派势力
  - 装备炼化
```

### Phase 3: 完整体验 (4周)

```yaml
目标: 完成前三幕，世界有深度

实现:
  - 完整的世界系统
  - 势力关系
  - 复杂的剧情分支
  - 多结局
  - 玄影线
  - 身世之谜

不实现:
  - 轮回系统
  - 隐藏结局
```

### Phase 4: 深度内容 (4周)

```yaml
目标: 轮回系统，多周目

实现:
  - 死亡和轮回
  - 因果继承
  - 记忆碎片
  - 隐藏剧情
  - 多周目变化
```

---

## 技术栈

```yaml
语言: Python 3.10+

核心依赖:
  - anthropic: Claude API
  - pyyaml: 配置文件
  - pydantic: 数据验证
  - rich: 终端美化（可选）

存储:
  - JSON文件存储
  - 未来可迁移到SQLite

测试:
  - pytest
  - 模拟AI用于测试
```

---

*本文档定义了技术实现的整体架构。具体的类和函数实现将在开发过程中迭代完善。*

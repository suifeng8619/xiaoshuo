# 技术架构设计文档

## 架构理念

**规则驱动世界，AI润色叙事。**

这不是一个"带AI描写的传统游戏"，而是一个"活世界+AI叙事"的结合体。

核心原则：
1. **世界运转靠规则** —— 时间、日程、事件触发都是确定性的
2. **AI只负责表达** —— 对话、描写、文本变体
3. **玩家选择有后果** —— 事件系统和状态标记追踪一切
4. **NPC真正"活着"** —— 有日程、有目标、有记忆

---

## 一、主循环流程

### 1.1 游戏主循环

```
┌─────────────────────────────────────────────────────────────────┐
│                        游戏主循环                                │
└─────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │  玩家输入     │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  解析意图     │  ← 规则层：判断行动类型
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  执行行动     │  ← 规则层：计算时间消耗、移动、战斗等
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  推进时间     │  ← 规则层：时间流逝、NPC日程执行
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  事件检查     │  ← 规则层：检查触发条件、选择事件
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  状态更新     │  ← 规则层：关系、标记、世界状态
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  叙事生成     │  ← AI层：生成对话、描写
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  输出验证     │  ← 规则层：检查AI输出一致性
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  显示输出     │
     └──────────────┘
```

### 1.2 详细流程说明

```python
class GameLoop:
    """游戏主循环"""

    def run(self):
        while self.is_running:
            # 1. 获取玩家输入
            player_input = self.get_input()

            # 2. 解析意图（规则层）
            intent = self.intent_parser.parse(player_input)
            # intent = {type: "move", target: "溪边"} 或
            # intent = {type: "talk", npc: "阿檀", content: "你好"}

            # 3. 执行行动（规则层）
            action_result = self.action_executor.execute(intent)
            # action_result = {
            #   success: true,
            #   time_cost: 2时辰,
            #   location_changed: true,
            #   new_location: "后山溪边"
            # }

            # 4. 推进时间（规则层）
            time_events = self.world.advance_time(action_result.time_cost)
            # 执行所有NPC的日程
            # 返回这段时间内发生的事件

            # 5. 事件检查（规则层）
            triggered_events = self.event_manager.check_triggers(
                location=self.world.player_location,
                time=self.world.current_time,
                flags=self.story.flags
            )

            # 6. 状态更新（规则层）
            self.update_states(action_result, triggered_events)

            # 7. 构建场景上下文（规则层 → AI层）
            scene_context = self.build_scene_context()

            # 8. 叙事生成（AI层）
            narrative = self.ai_engine.generate_narrative(
                scene_context=scene_context,
                action_result=action_result,
                events=triggered_events
            )

            # 9. 输出验证（规则层）
            validated_narrative = self.validator.check(
                narrative,
                scene_context
            )

            # 10. 显示输出
            self.display(validated_narrative)
```

---

## 二、系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Game Shell                               │
│                      (命令行交互层)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Game Director                               │
│                    (游戏导演/总控)                                │
│  - 主循环控制                                                    │
│  - 意图解析                                                      │
│  - 行动调度                                                      │
│  - 输出验证                                                      │
└───┬───────────────┬───────────────┬───────────────┬─────────────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ World  │    │Character │    │  Event   │    │   AI     │
│Manager │    │ Manager  │    │ Manager  │    │ Engine   │
│        │    │          │    │          │    │          │
│- Time  │    │- Player  │    │- 事件池   │    │- Claude  │
│- Space │    │- NPCs    │    │- 触发器   │    │- GPT     │
│- State │    │- 关系图   │    │- 调度器   │    │- 路由    │
└───┬────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
    │              │               │               │
    │         ┌────▼─────┐         │               │
    │         │ Memory   │◄────────┘               │
    │         │ System   │                         │
    │         │          │                         │
    │         │- 存储    │                         │
    │         │- 检索    │                         │
    │         │- 衰减    │                         │
    │         └────┬─────┘                         │
    │              │                               │
    └──────────────┴───────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                      Event Bus                                   │
│                    (事件总线)                                     │
│  - 订阅/发布                                                     │
│  - 解耦各系统                                                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                  Persistence Layer                               │
│                    (持久化层)                                     │
│  - JSON存储                                                      │
│  - 自动存档                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详细设计

### 3.1 World Manager (世界管理器)

```python
class WorldManager:
    """
    世界管理器
    负责时间、空间、世界状态的管理
    """

    def __init__(self):
        self.time_system = TimeSystem()
        self.location_system = LocationSystem()
        self.world_state = WorldState()

    # ========== 时间系统 ==========

    def advance_time(self, duration: TimeDelta) -> List[Event]:
        """
        推进时间
        这是世界运转的核心方法
        """
        events = []
        days_to_simulate = duration.to_days()

        if days_to_simulate < 1:
            # 短时间：直接推进
            self.time_system.advance(duration)
            events.extend(self._check_time_events())
        else:
            # 长时间：逐日模拟
            for day in range(days_to_simulate):
                # 执行当日模拟
                day_events = self._simulate_day()
                events.extend(day_events)

                # 检查是否需要中断
                interrupt_event = self._find_interrupt_event(day_events)
                if interrupt_event:
                    events.append(interrupt_event)
                    break

        return events

    def _simulate_day(self) -> List[Event]:
        """模拟一天"""
        events = []

        for time_slot in [MORNING, AFTERNOON, EVENING, NIGHT]:
            # 1. 推进到该时段
            self.time_system.advance_to_slot(time_slot)

            # 2. 执行所有NPC日程
            self.character_manager.execute_schedules(time_slot)

            # 3. 检查时段事件
            slot_events = self.event_manager.check_time_slot_events(time_slot)
            events.extend(slot_events)

            # 4. roll随机扰动
            perturbation = self._roll_perturbation()
            if perturbation:
                events.append(perturbation)

        # 5. 日结算
        self._daily_settlement()

        return events

    # ========== 空间系统 ==========

    def get_location(self, location_id: str) -> LocationNode:
        """获取地点节点"""
        return self.location_system.get_node(location_id)

    def get_npcs_at_location(self, location_id: str) -> List[NPC]:
        """获取当前在该地点的NPC"""
        current_slot = self.time_system.current_slot
        npcs = []

        for npc in self.character_manager.all_npcs():
            schedule = npc.get_schedule_for_slot(current_slot)
            if schedule.location == location_id:
                npcs.append(npc)

        return npcs

    def move_player(self, target_location: str) -> MoveResult:
        """移动玩家"""
        current = self.player_location
        target = self.location_system.get_node(target_location)

        if not target:
            return MoveResult(success=False, reason="地点不存在")

        # 计算移动时间
        travel_time = self.location_system.get_travel_time(current, target_location)

        # 执行移动
        self.player_location = target_location

        return MoveResult(
            success=True,
            time_cost=travel_time,
            new_location=target_location,
            npcs_present=self.get_npcs_at_location(target_location)
        )

    # ========== 上下文构建 ==========

    def get_scene_context(self) -> SceneContext:
        """获取当前场景上下文（给AI用）"""
        location = self.get_location(self.player_location)
        npcs = self.get_npcs_at_location(self.player_location)

        return SceneContext(
            location_name=location.name,
            location_features=location.features,
            time_slot=self.time_system.current_slot,
            time_display=self.time_system.display_time(),
            weather=self.world_state.weather,
            atmosphere=location.atmosphere,
            npcs_present=[
                {
                    "name": npc.name,
                    "activity": npc.current_activity,
                    "mood": npc.current_mood
                }
                for npc in npcs
            ]
        )
```

### 3.2 Character Manager (角色管理器)

```python
class CharacterManager:
    """
    角色管理器
    管理玩家和所有NPC
    """

    def __init__(self):
        self.player: Player = None
        self.npcs: Dict[str, NPC] = {}
        self.relationship_graph = RelationshipGraph()

    # ========== NPC日程系统 ==========

    def execute_schedules(self, time_slot: TimeSlot):
        """执行所有NPC在当前时段的日程"""
        for npc in self.npcs.values():
            self._execute_npc_schedule(npc, time_slot)

    def _execute_npc_schedule(self, npc: NPC, time_slot: TimeSlot):
        """执行单个NPC的日程"""
        # 1. 获取当前时段的日程
        schedule = npc.get_schedule_for_slot(time_slot)

        # 2. 检查是否有条件覆盖
        override = npc.check_schedule_override(time_slot, self.world_state)
        if override:
            schedule = override

        # 3. 检查是否被打断
        if npc.interrupted_by:
            if npc.interrupted_by.priority < schedule.priority:
                # 继续处理打断事件
                return
            else:
                # 恢复日程
                npc.interrupted_by = None

        # 4. 执行日程
        npc.current_location = schedule.location
        npc.current_activity = schedule.activity

    # ========== 关系系统 ==========

    def get_relationship(self, npc_id: str) -> Relationship:
        """获取与NPC的关系"""
        return self.relationship_graph.get(self.player.id, npc_id)

    def update_relationship(self, npc_id: str, changes: Dict[str, int], context: str):
        """更新关系"""
        relationship = self.get_relationship(npc_id)

        # 应用变化（带权重）
        for dimension, delta in changes.items():
            current = getattr(relationship, dimension)
            new_value = clamp(current + delta, 0, 100)
            setattr(relationship, dimension, new_value)

        # 检查阈值跨越
        threshold_event = relationship.check_threshold_crossing()
        if threshold_event:
            self.event_bus.emit(threshold_event)

        # 记录到NPC记忆
        npc = self.npcs[npc_id]
        npc.memory.add_relationship_change(changes, context)

    # ========== 上下文构建 ==========

    def get_npc_context(self, npc_id: str) -> NPCContext:
        """获取NPC上下文（给AI用）"""
        npc = self.npcs[npc_id]
        relationship = self.get_relationship(npc_id)

        return NPCContext(
            # 基础信息
            name=npc.name,
            personality=npc.personality,
            speaking_style=npc.speaking_style,

            # 当前状态（规则层已确定）
            current_activity=npc.current_activity,
            current_mood=npc.current_mood,
            health_state=npc.health_state,

            # 关系摘要（不给具体数值）
            relationship_state=relationship.get_state_label(),
            relationship_description=relationship.get_description(),
            unresolved_conflicts=relationship.unresolved,

            # 相关记忆
            relevant_memories=npc.memory.get_relevant(
                context=self.current_scene_context,
                limit=5
            ),

            # 禁忌
            taboos=npc.taboos,
            secrets_unknown_to_player=npc.get_unknown_secrets()
        )
```

### 3.3 Event Manager (事件管理器)

```python
class EventManager:
    """
    事件管理器
    管理事件池、触发、调度
    """

    def __init__(self):
        # 事件池（按层级）
        self.daily_pool: List[Event] = []
        self.opportunity_pool: List[Event] = []
        self.critical_pool: List[Event] = []

        # 状态
        self.active_events: List[Event] = []
        self.pending_events: List[Event] = []
        self.cooldowns: Dict[str, GameTime] = {}

        # 配额
        self.daily_limit = 3
        self.opportunity_limit = 2
        self.critical_limit = 1

    def check_triggers(self, location: str, time: GameTime, flags: Dict) -> List[Event]:
        """检查所有可触发的事件"""
        triggered = []

        # 按层级检查
        for pool, limit in [
            (self.critical_pool, self.critical_limit),
            (self.opportunity_pool, self.opportunity_limit),
            (self.daily_pool, self.daily_limit)
        ]:
            candidates = self._find_candidates(pool, location, time, flags)
            selected = self._select_events(candidates, limit)
            triggered.extend(selected)

        return triggered

    def _find_candidates(self, pool: List[Event], location: str,
                         time: GameTime, flags: Dict) -> List[Event]:
        """找出所有满足条件的候选事件"""
        candidates = []

        for event in pool:
            # 检查冷却
            if self._is_on_cooldown(event.id):
                continue

            # 检查时间窗口
            if not event.check_time_window(time):
                continue

            # 检查地点条件
            if event.location_required and location not in event.locations:
                continue

            # 检查前置条件
            if not event.check_preconditions(flags, self.world_state, self.characters):
                continue

            candidates.append(event)

        return candidates

    def _select_events(self, candidates: List[Event], limit: int) -> List[Event]:
        """从候选中选择事件"""
        if not candidates:
            return []

        # 计算综合评分
        scored = []
        for event in candidates:
            score = self._calculate_score(event)
            scored.append((score, event))

        # 按分数排序
        scored.sort(reverse=True, key=lambda x: x[0])

        # 检查互斥，选择不冲突的
        selected = []
        for score, event in scored:
            if len(selected) >= limit:
                break
            if not self._conflicts_with(event, selected):
                selected.append(event)

        return selected

    def _calculate_score(self, event: Event) -> float:
        """计算事件评分"""
        score = 0.0

        # 优先级权重 (0.4)
        score += event.priority * 0.4

        # 紧急度权重 (0.3) - 临近过期的更紧急
        urgency = self._calculate_urgency(event)
        score += urgency * 0.3

        # 相关性权重 (0.2)
        relevance = self._calculate_relevance(event)
        score += relevance * 0.2

        # 随机因子 (0.1)
        score += random.random() * 0.1

        return score

    def trigger_event(self, event: Event) -> EventResult:
        """触发事件"""
        # 1. 标记触发
        event.trigger_count += 1
        self.cooldowns[event.id] = self.world.current_time + event.cooldown

        # 2. 应用效果
        for flag in event.effects.set_flags:
            self.story.set_flag(flag)

        for flag in event.effects.clear_flags:
            self.story.clear_flag(flag)

        for rel_change in event.effects.relationship_changes:
            self.characters.update_relationship(
                rel_change.npc,
                rel_change.changes,
                event.name
            )

        # 3. 安排后续事件
        for followup in event.effects.schedule_followups:
            self._schedule_followup(followup)

        # 4. 选择变体
        variant = self._select_variant(event)

        return EventResult(
            event=event,
            variant=variant,
            ai_prompt_tags=variant.ai_prompt_tags if variant else []
        )
```

### 3.4 AI Engine (AI引擎)

```python
class AIEngine:
    """
    AI引擎
    负责构建上下文、调用AI、验证输出
    """

    def __init__(self):
        self.providers = {
            "claude_opus": ClaudeProvider("claude_opus"),
            "gpt5": GPTProvider("gpt5"),
            "gpt5_thinking": GPTProvider("gpt5_thinking"),
        }

        self.routing_table = {
            TaskType.DIALOGUE: ["claude_opus", "gpt5"],
            TaskType.NARRATIVE: ["gpt5", "claude_opus"],
            TaskType.MEMORY: ["gpt5_thinking", "claude_opus"],
        }

    # ========== 对话生成 ==========

    def generate_dialogue(self, npc_context: NPCContext, player_says: str,
                          scene_context: SceneContext) -> DialogueResult:
        """生成NPC对话"""

        # 1. 构建上下文（规则层数据）
        context = self._build_dialogue_context(npc_context, player_says, scene_context)

        # 2. 构建系统提示词
        system_prompt = self._build_dialogue_system_prompt(npc_context)

        # 3. 构建用户提示词
        user_prompt = self._build_dialogue_user_prompt(context, player_says)

        # 4. 调用AI
        response, provider = self._call_ai(
            TaskType.DIALOGUE,
            system_prompt,
            user_prompt
        )

        # 5. 解析响应
        dialogue = self._parse_dialogue_response(response)

        return DialogueResult(
            text=dialogue.text,
            action=dialogue.action,
            emotion=dialogue.emotion,
            provider=provider
        )

    def _build_dialogue_context(self, npc_context: NPCContext, player_says: str,
                                 scene_context: SceneContext) -> str:
        """构建对话上下文"""
        return f"""
## 场景
- 地点：{scene_context.location_name}
- 时段：{scene_context.time_slot}
- 特征：{', '.join(scene_context.location_features)}

## {npc_context.name}当前状态
- 正在做：{npc_context.current_activity}
- 心情：{npc_context.current_mood}
- 健康：{npc_context.health_state}

## 你们的关系
- 状态：{npc_context.relationship_description}
- 未解决：{', '.join(npc_context.unresolved_conflicts) or '无'}

## 相关记忆
{self._format_memories(npc_context.relevant_memories)}

## 禁忌
- 【不要出现】：{', '.join(npc_context.taboos)}
- 【不要提及】：{', '.join(npc_context.secrets_unknown_to_player)}
"""

    # ========== 场景叙事 ==========

    def generate_narrative(self, scene_context: SceneContext,
                           action_result: ActionResult,
                           events: List[Event]) -> str:
        """生成场景叙事"""

        system_prompt = NARRATIVE_SYSTEM_PROMPT

        user_prompt = f"""
## 当前场景
{self._format_scene(scene_context)}

## 刚刚发生
{self._format_action(action_result)}

## 触发的事件
{self._format_events(events)}

## 要求
- 简洁有力，不堆砌辞藻
- 描写要符合当前场景特征
- 如果有NPC在场，描述他们当前的状态
"""

        response, _ = self._call_ai(TaskType.NARRATIVE, system_prompt, user_prompt)

        return response

    # ========== 输出验证 ==========

    def validate_output(self, output: str, context: SceneContext,
                        npc_context: NPCContext = None) -> ValidationResult:
        """验证AI输出"""
        issues = []

        # 1. 检查地点一致性
        location_issues = self._check_location_consistency(output, context)
        issues.extend(location_issues)

        # 2. 检查NPC行动一致性
        if npc_context:
            activity_issues = self._check_activity_consistency(output, npc_context)
            issues.extend(activity_issues)

        # 3. 检查禁忌
        if npc_context:
            taboo_issues = self._check_taboos(output, npc_context)
            issues.extend(taboo_issues)

        # 判断严重程度
        if any(i.severity == "critical" for i in issues):
            return ValidationResult(valid=False, issues=issues, action="reject")
        elif issues:
            return ValidationResult(valid=True, issues=issues, action="warn")
        else:
            return ValidationResult(valid=True, issues=[], action="pass")
```

### 3.5 Memory System (记忆系统)

```python
class MemorySystem:
    """
    记忆系统
    为每个NPC管理记忆
    """

    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.memories: List[Memory] = []

    def add_memory(self, event: Event, emotional_impact: EmotionalImpact):
        """添加记忆"""
        memory = Memory(
            id=self._generate_id(),
            event=event,
            timestamp=current_game_time(),
            importance=self._calculate_importance(event, emotional_impact),
            emotional_impact=emotional_impact,
            tags=self._extract_tags(event),
            can_forget=event.category != "core"
        )
        self.memories.append(memory)

    def get_relevant(self, context: QueryContext, limit: int = 5) -> List[Memory]:
        """获取相关记忆"""
        scored = []

        for memory in self.memories:
            score = self._calculate_relevance(memory, context)
            scored.append((score, memory))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scored[:limit]]

    def _calculate_relevance(self, memory: Memory, context: QueryContext) -> float:
        """计算相关性分数"""
        score = 0.0

        # 1. 标签匹配
        tag_overlap = len(set(memory.tags) & set(context.keywords))
        score += tag_overlap * 0.3

        # 2. 重要性
        score += (memory.importance / 10) * 0.3

        # 3. 时间近度（最近的记忆更容易被想起）
        days_ago = (current_game_time() - memory.timestamp).days
        recency = max(0, 1 - days_ago / 365)  # 一年内线性衰减
        score += recency * 0.2

        # 4. 情感强度
        score += (memory.emotional_impact.intensity / 10) * 0.2

        return score

    def decay_memories(self):
        """记忆衰减（每月调用一次）"""
        for memory in self.memories:
            if memory.can_forget:
                # 根据类型衰减
                if memory.importance <= 5:
                    memory.importance -= 0.5
                elif memory.importance <= 8:
                    memory.importance -= 0.1

                # 移除衰减到0的记忆
                if memory.importance <= 0:
                    self.memories.remove(memory)
```

---

## 四、数据模型

### 4.1 时间数据

```python
@dataclass
class GameTime:
    """游戏时间"""
    year: int
    month: int      # 1-12
    day: int        # 1-30
    slot: TimeSlot  # MORNING/AFTERNOON/EVENING/NIGHT

    def advance(self, slots: int = 0, days: int = 0, months: int = 0):
        """推进时间"""
        # ... 实现

    def to_display(self) -> str:
        """显示用字符串"""
        season = ["春", "夏", "秋", "冬"][(self.month - 1) // 3]
        slot_names = {
            MORNING: "早晨",
            AFTERNOON: "午后",
            EVENING: "黄昏",
            NIGHT: "夜晚"
        }
        return f"第{self.year}年{season}，{self.month}月{self.day}日，{slot_names[self.slot]}"


class TimeSlot(Enum):
    """时段"""
    MORNING = "morning"      # 卯-辰 (05:00-09:00)
    AFTERNOON = "afternoon"  # 巳-午 (09:00-13:00)
    EVENING = "evening"      # 未-酉 (13:00-19:00)
    NIGHT = "night"          # 戌-子 (19:00-01:00)
```

### 4.2 地点数据

```python
@dataclass
class LocationNode:
    """地点节点"""
    id: str
    name: str
    type: str  # region/territory/location/hotspot

    # 环境
    features: List[str]       # 环境特征
    atmosphere: str           # 氛围
    available_actions: List[str]  # 可用行动

    # 连接
    adjacent: Dict[str, float]  # 相邻节点及移动时间

    # 绑定
    bound_events: List[str]   # 绑定的事件ID
```

### 4.3 NPC数据

```python
@dataclass
class NPC:
    """NPC数据"""
    id: str
    name: str

    # 性格
    personality: Personality
    speaking_style: str
    taboos: List[str]

    # 日程
    default_schedule: Dict[TimeSlot, ScheduleSlot]
    schedule_overrides: List[ScheduleOverride]

    # 目标
    goals: List[Goal]
    hard_constraints: List[str]

    # 状态
    current_location: str
    current_activity: str
    current_mood: str
    health_state: str

    # 系统
    memory: MemorySystem
    secrets: List[Secret]


@dataclass
class ScheduleSlot:
    """日程时段"""
    location: str
    activity: str
    interruptible: bool
    priority: int  # 1-5，数字越小优先级越高


@dataclass
class ScheduleOverride:
    """日程覆盖"""
    condition: str
    target_slot: TimeSlot  # None表示所有时段
    location: str
    activity: str
```

### 4.4 事件数据

```python
@dataclass
class Event:
    """事件"""
    id: str
    name: str
    category: str  # encounter/plot/daily/crisis
    tier: str      # daily/opportunity/critical

    # 调度
    priority: float
    cooldown: TimeDelta
    max_triggers: int
    trigger_count: int = 0

    # 条件
    window: TimeWindow
    locations: List[str]
    preconditions: Preconditions
    triggers: List[Trigger]

    # 打断
    interrupt: bool
    interrupt_dialogue: bool

    # 效果
    effects: EventEffects

    # 变体
    variants: List[EventVariant]

    # 叙事
    narrative: NarrativeConfig


@dataclass
class EventEffects:
    """事件效果"""
    set_flags: List[str]
    clear_flags: List[str]
    relationship_changes: List[RelationshipChange]
    schedule_followups: List[FollowupConfig]
    world_state_changes: Dict[str, Any]
```

---

## 五、文件结构

```
xiaoshuo/
├── engine/
│   ├── core/
│   │   ├── game_director.py    # 游戏导演
│   │   ├── game_loop.py        # 主循环
│   │   └── event_bus.py        # 事件总线
│   │
│   ├── world/
│   │   ├── world_manager.py    # 世界管理器
│   │   ├── time_system.py      # 时间系统
│   │   ├── location_system.py  # 地点系统
│   │   └── world_state.py      # 世界状态
│   │
│   ├── character/
│   │   ├── character_manager.py  # 角色管理器
│   │   ├── npc.py              # NPC类
│   │   ├── schedule.py         # 日程系统
│   │   ├── relationship.py     # 关系系统
│   │   └── memory.py           # 记忆系统
│   │
│   ├── event/
│   │   ├── event_manager.py    # 事件管理器
│   │   ├── event_pool.py       # 事件池
│   │   ├── trigger.py          # 触发器
│   │   └── scheduler.py        # 调度器
│   │
│   ├── ai/
│   │   ├── ai_engine.py        # AI引擎
│   │   ├── providers/          # AI提供者
│   │   │   ├── claude.py
│   │   │   └── gpt.py
│   │   ├── context_builder.py  # 上下文构建
│   │   └── validator.py        # 输出验证
│   │
│   └── persistence/
│       ├── save_manager.py     # 存档管理
│       └── serializers.py      # 序列化
│
├── data/
│   ├── locations/              # 地点配置
│   │   └── qingyun_sect.yaml
│   ├── npcs/                   # NPC配置
│   │   ├── atan.yaml
│   │   └── shifu.yaml
│   ├── events/                 # 事件配置
│   │   ├── daily/
│   │   ├── opportunity/
│   │   └── critical/
│   └── saves/                  # 存档
│
├── config/
│   ├── game.yaml               # 游戏配置
│   ├── ai.yaml                 # AI配置
│   └── balance.yaml            # 平衡配置
│
└── docs/design/                # 设计文档
```

---

## 六、实现路线图

### Phase 1: 核心框架 (1-2周)

```yaml
目标: 主循环能跑通，世界能运转

实现:
  - GameDirector 框架
  - TimeSystem（时段切换）
  - LocationSystem（节点图）
  - 单个NPC（阿檀）的日程系统
  - 基础AI对话（不验证）

验证:
  - 玩家能移动到不同地点
  - 时间能推进
  - 阿檀按日程出现在不同地点
  - 能和阿檀对话
```

### Phase 2: 事件系统 (1-2周)

```yaml
目标: 事件池能触发，世界有"内容"

实现:
  - EventManager
  - 3个日常事件 + 1个关键事件
  - 事件触发和效果
  - 状态标记系统

验证:
  - 去特定地点能触发事件
  - 事件有效果（关系变化、标记设置）
  - 冷却生效
```

### Phase 3: 完整NPC (1-2周)

```yaml
目标: NPC真正"活"起来

实现:
  - 完整的日程系统（含覆盖和打断）
  - 记忆系统
  - 关系阈值事件
  - AI上下文完整构建
  - 输出验证

验证:
  - 关系变化会影响阿檀行为
  - 阿檀记得之前的事
  - AI输出和场景一致
```

### Phase 4: 长行动与世界演化 (1-2周)

```yaml
目标: 闭关、远行等长行动；世界会变化

实现:
  - 长行动的逐日模拟
  - 随机扰动
  - 叙事吸引子
  - 多NPC（师父、大师兄）

验证:
  - 闭关30天，世界继续运转
  - 错过事件有后果
  - 多NPC日程不冲突
```

---

## 七、AI提示词模板

### 7.1 对话系统提示词

```
你是一个角色扮演AI，负责扮演游戏中的NPC。

## 你的角色
你正在扮演：{npc_name}

## 性格设定
{personality_description}

## 说话风格
{speaking_style}

## 规则
1. 你必须始终保持角色，不能打破第四面墙
2. 你的回应必须符合角色的性格和说话风格
3. 你要考虑与玩家的关系和过去的记忆
4. 你有自己的想法和情感，不是玩家的提线木偶
5. 你可以拒绝玩家的请求，可以生气，可以有自己的诉求
6. 回应要简洁自然，像真人对话，不要过于书面化
7. 【重要】你的动作描写必须符合当前场景和你正在做的事

## 输出格式
直接输出角色的对话和动作。
动作用括号包裹，如：(她低下头)
不要加引号或角色名前缀。
```

### 7.2 叙事系统提示词

```
你是一个叙事AI，负责生成游戏中的场景描写。

## 风格要求
- 简洁有力，不堆砌辞藻
- 重要时刻才浓墨重彩
- 多用短句，制造节奏感
- 留白比说满更好

## 规则
1. 描写必须符合当前场景的特征
2. 如果有NPC在场，描述他们正在做的事（由系统提供）
3. 不要添加场景中不存在的元素
4. 不要暗示未来剧情

## 差的写法
"阿檀那双如秋水般的眼眸中泛着点点泪光，她樱唇轻启..."

## 好的写法
"阿檀看着你，眼圈红了。"
```

---

*本文档定义了技术实现的整体架构。核心原则：规则驱动世界运转，AI负责叙事润色，分工明确，不越界。*

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

    依赖注入:
    - world_manager: 世界管理器（时间、地点）
    - character_manager: 角色管理器（NPC状态、关系）
    - story_manager: 故事管理器（标记、剧情进度）
    """

    def __init__(self, world_manager: 'WorldManager',
                 character_manager: 'CharacterManager',
                 story_manager: 'StoryManager'):
        # 依赖注入
        self.world = world_manager
        self.characters = character_manager
        self.story = story_manager

        # 事件池（按层级）
        self.daily_pool: List[Event] = []
        self.opportunity_pool: List[Event] = []
        self.critical_pool: List[Event] = []

        # 状态
        self.active_events: List[Event] = []
        self.pending_events: List[Event] = []
        self.cooldowns: Dict[str, GameTime] = {}

        # 互斥组占用
        self.active_mutex_groups: Set[str] = set()

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

    def _conflicts_with(self, event: Event, selected: List[Event]) -> bool:
        """检查事件是否与已选事件冲突"""
        # 1. 检查互斥组
        for group in getattr(event, 'mutex_groups', []):
            if group in self.active_mutex_groups:
                return True
            for sel_event in selected:
                if group in getattr(sel_event, 'mutex_groups', []):
                    return True

        # 2. 检查显式互斥
        for sel_event in selected:
            if event.id in getattr(sel_event, 'exclusive_with', []):
                return True
            if sel_event.id in getattr(event, 'exclusive_with', []):
                return True

        return False

    def _calculate_urgency(self, event: Event) -> float:
        """计算紧急度：越接近过期越紧急"""
        expiry = getattr(event, 'expiry', None)
        if not expiry or not expiry.deadline:
            return 0.5  # 无截止时间，中等紧急

        current = self.world.time_system.current_time
        deadline = expiry.deadline

        # 计算剩余时间比例
        available_from = getattr(event, 'available_from', current)
        total_window = (deadline - available_from).total_days()
        remaining = (deadline - current).total_days()

        if remaining <= 0:
            return 1.0  # 已过期，最高紧急
        if total_window <= 0:
            return 0.5

        # 剩余时间越少，紧急度越高
        urgency = 1.0 - (remaining / total_window)
        return min(1.0, max(0.0, urgency))

    def _calculate_relevance(self, event: Event) -> float:
        """计算与当前情境的相关性"""
        relevance = 0.0
        player_location = self.world.player_location

        # 地点匹配
        if hasattr(event, 'locations') and player_location in event.locations:
            relevance += 0.3

        # 相关NPC在场
        npcs_here = self.world.get_npcs_at_location(player_location)
        involved_npcs = getattr(event, 'involved_npcs', [])
        for npc in npcs_here:
            if npc.id in involved_npcs:
                relevance += 0.2

        # 剧情连贯性
        follows_event = getattr(event, 'follows_event', None)
        if follows_event and follows_event in self.story.recently_triggered:
            relevance += 0.3

        return min(1.0, relevance)

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

## 八、AI成本控制策略

### 8.1 Token预算系统

```python
class TokenBudgetManager:
    """Token预算管理器"""

    def __init__(self):
        # 每日预算（可配置）
        self.daily_budget = {
            "claude_opus": 50000,   # Claude Opus 4.5
            "gpt5": 100000,         # GPT 5.1
            "gpt5_thinking": 30000  # GPT 5.1 Thinking（最贵）
        }

        # 单次调用上限
        self.per_call_limit = {
            "claude_opus": 4000,
            "gpt5": 4000,
            "gpt5_thinking": 8000  # 思考链可能更长
        }

        # 当日已使用
        self.daily_usage = defaultdict(int)

        # 任务类型优先级（预算紧张时降级）
        self.task_priority = {
            TaskType.DIALOGUE: 1,      # 最重要
            TaskType.NARRATIVE: 2,
            TaskType.MEMORY: 3,
            TaskType.DESCRIPTION: 4    # 可省略
        }

    def request_budget(self, provider: str, estimated_tokens: int,
                       task_type: TaskType) -> BudgetDecision:
        """请求预算"""
        remaining = self.daily_budget[provider] - self.daily_usage[provider]

        if estimated_tokens <= remaining:
            return BudgetDecision(
                approved=True,
                provider=provider,
                max_tokens=min(estimated_tokens, self.per_call_limit[provider])
            )

        # 预算不足，尝试降级
        return self._try_fallback(provider, estimated_tokens, task_type)

    def _try_fallback(self, original_provider: str, tokens: int,
                      task_type: TaskType) -> BudgetDecision:
        """降级策略"""
        # 降级顺序：claude_opus → gpt5 → gpt5_thinking → 模板
        fallback_chain = {
            "claude_opus": ["gpt5", "template"],
            "gpt5": ["claude_opus", "template"],
            "gpt5_thinking": ["gpt5", "claude_opus", "template"]
        }

        for fallback in fallback_chain.get(original_provider, []):
            if fallback == "template":
                return BudgetDecision(
                    approved=True,
                    provider="template",
                    use_template=True
                )

            remaining = self.daily_budget[fallback] - self.daily_usage[fallback]
            if tokens <= remaining:
                return BudgetDecision(
                    approved=True,
                    provider=fallback,
                    degraded_from=original_provider,
                    max_tokens=min(tokens, self.per_call_limit[fallback])
                )

        # 所有AI都超预算，使用模板
        return BudgetDecision(approved=True, provider="template", use_template=True)
```

### 8.2 智能缓存系统

```python
class ResponseCache:
    """AI响应缓存"""

    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)

    def get_cache_key(self, prompt_type: str, context_hash: str,
                      npc_id: str = None) -> str:
        """生成缓存键"""
        # 对话缓存考虑NPC状态
        if prompt_type == "dialogue" and npc_id:
            return f"{prompt_type}:{npc_id}:{context_hash}"
        return f"{prompt_type}:{context_hash}"

    def get(self, key: str) -> Optional[CachedResponse]:
        """获取缓存"""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now() - entry.created_at > self.ttl:
            del self.cache[key]
            return None

        # LRU: 移到末尾
        self.cache.move_to_end(key)
        return entry.response

    def set(self, key: str, response: str, metadata: dict = None):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 移除最老的
            self.cache.popitem(last=False)

        self.cache[key] = CacheEntry(
            response=response,
            created_at=datetime.now(),
            metadata=metadata
        )


# 可缓存的场景类型
CACHEABLE_SCENARIOS = {
    "location_description": {
        "ttl": 24,  # 小时
        "vary_by": ["location_id", "time_slot", "weather"]
    },
    "generic_greeting": {
        "ttl": 168,  # 一周
        "vary_by": ["npc_id", "relationship_state"]
    },
    "combat_action": {
        "ttl": 1,
        "vary_by": ["action_type", "target_type"]
    }
}
```

### 8.3 上下文压缩

```python
class ContextCompressor:
    """上下文压缩器 - 减少token使用"""

    def compress_memories(self, memories: List[Memory], max_tokens: int = 500) -> str:
        """压缩记忆列表"""
        if not memories:
            return "无相关记忆"

        # 按重要性排序
        sorted_memories = sorted(memories, key=lambda m: m.importance, reverse=True)

        compressed = []
        token_count = 0

        for memory in sorted_memories:
            summary = self._summarize_memory(memory)
            summary_tokens = self._estimate_tokens(summary)

            if token_count + summary_tokens > max_tokens:
                break

            compressed.append(summary)
            token_count += summary_tokens

        return "\n".join(compressed)

    def _summarize_memory(self, memory: Memory) -> str:
        """单条记忆摘要"""
        time_ago = self._format_time_ago(memory.timestamp)
        return f"- [{time_ago}] {memory.summary} (情感:{memory.emotional_impact.type})"

    def compress_npc_context(self, full_context: NPCContext) -> NPCContext:
        """压缩NPC上下文（用于非关键对话）"""
        return NPCContext(
            name=full_context.name,
            current_mood=full_context.current_mood,
            relationship_state=full_context.relationship_state,
            # 省略详细记忆和禁忌
            relevant_memories=full_context.relevant_memories[:2],
            taboos=full_context.taboos[:3]
        )


class TokenEstimator:
    """Token估算器"""

    # 粗略估算：1 token ≈ 4个英文字符 ≈ 1.5个中文字符
    CHARS_PER_TOKEN_EN = 4
    CHARS_PER_TOKEN_CN = 1.5

    def estimate(self, text: str) -> int:
        """估算token数量"""
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - cn_chars

        cn_tokens = cn_chars / self.CHARS_PER_TOKEN_CN
        other_tokens = other_chars / self.CHARS_PER_TOKEN_EN

        return int(cn_tokens + other_tokens)
```

### 8.4 降级模板系统

```python
class TemplateEngine:
    """
    当AI预算耗尽时使用的模板引擎
    保证游戏能继续运行
    """

    def __init__(self):
        self.templates = self._load_templates()

    def generate_dialogue(self, npc_id: str, context: str,
                          player_says: str) -> str:
        """模板对话生成"""
        npc_templates = self.templates["dialogue"].get(npc_id, self.templates["dialogue"]["default"])

        # 根据上下文选择模板
        if "问候" in player_says or "你好" in player_says:
            return random.choice(npc_templates["greeting"])

        if "怎么了" in player_says or "发生什么" in player_says:
            return random.choice(npc_templates["concerned"])

        if "告别" in player_says or "走了" in player_says:
            return random.choice(npc_templates["farewell"])

        # 默认回复
        return random.choice(npc_templates["default"])

    def generate_description(self, location_id: str, time_slot: str) -> str:
        """模板场景描写"""
        location_templates = self.templates["location"].get(location_id)
        if not location_templates:
            return f"你来到了{location_id}。"

        return location_templates.get(time_slot, location_templates["default"])


# 模板示例 (data/templates/dialogue.yaml)
DIALOGUE_TEMPLATES = """
atan:
  greeting:
    - (她抬起头，眼睛亮了亮) "你来了。"
    - "早啊。" (她放下手中的活计)
    - (她朝你点点头) "你吃过了吗？"

  farewell:
    - "路上小心。" (她目送你离去)
    - (她轻声说) "早点回来。"
    - "去吧。" (她低下头继续干活，但你感觉她在偷偷看你)

  concerned:
    - (她皱起眉) "怎么了？"
    - "发生什么事了？" (她放下手中的东西，认真看着你)
    - (她走近一步) "你看起来不太对劲。"

  default:
    - (她想了想) "嗯..."
    - (她看着你，没有说话)
    - "是这样啊。" (她若有所思)

default:
  greeting:
    - "道友有礼了。"
    - "见过道友。"

  default:
    - "原来如此。"
    - "在下明白了。"
"""
```

### 8.5 成本监控与报警

```python
class CostMonitor:
    """成本监控"""

    def __init__(self):
        self.pricing = {
            # 价格单位：美元/1M tokens
            "claude_opus": {"input": 15, "output": 75},
            "gpt5": {"input": 5, "output": 15},
            "gpt5_thinking": {"input": 10, "output": 30}
        }

        # 每日成本上限（美元）
        self.daily_cost_limit = 1.0

        # 告警阈值
        self.alert_threshold = 0.8  # 80%时告警

    def record_usage(self, provider: str, input_tokens: int, output_tokens: int):
        """记录使用"""
        cost = self._calculate_cost(provider, input_tokens, output_tokens)
        self.daily_cost += cost

        if self.daily_cost >= self.daily_cost_limit * self.alert_threshold:
            self._send_alert(f"AI成本已达预算{int(self.alert_threshold*100)}%")

    def get_cost_report(self) -> dict:
        """获取成本报告"""
        return {
            "daily_cost": f"${self.daily_cost:.4f}",
            "daily_limit": f"${self.daily_cost_limit:.2f}",
            "usage_percent": f"{(self.daily_cost/self.daily_cost_limit)*100:.1f}%",
            "by_provider": self.usage_by_provider,
            "by_task": self.usage_by_task
        }
```

---

## 九、持久化格式

### 9.1 存档结构总览

```yaml
# saves/save_001/manifest.yaml
save_id: "save_001"
save_name: "第一个存档"
created_at: "2024-01-15T10:30:00"
updated_at: "2024-01-16T15:45:00"
game_version: "0.1.0"
play_time_hours: 12.5
thumbnail: "saves/save_001/screenshot.png"

# 存档文件列表
files:
  - world_state.json      # 世界状态
  - player.json           # 玩家数据
  - npcs/                 # NPC数据目录
  - events.json           # 事件状态
  - story_flags.json      # 剧情标记
```

### 9.2 世界状态 (world_state.json)

```json
{
  "time": {
    "year": 1,
    "month": 3,
    "day": 15,
    "slot": "afternoon",
    "total_days_elapsed": 75
  },

  "calendar": {
    "current_season": "spring",
    "upcoming_events": [
      {"id": "sword_tomb_opening", "date": {"year": 3, "month": 6}}
    ],
    "holidays": []
  },

  "weather": {
    "current": "clear",
    "temperature": "warm",
    "special_condition": null
  },

  "world_events": {
    "active": ["beast_tide_warning"],
    "completed": ["sect_competition_year_1"],
    "failed": []
  },

  "resource_state": {
    "spirit_stone_pool": 15000,
    "market_prices": {
      "recovery_pill": 15,
      "qi_gathering_pill": 50
    }
  }
}
```

### 9.3 玩家数据 (player.json)

```json
{
  "basic": {
    "name": "玩家自定义名",
    "age": 17,
    "gender": "male",
    "origin": "orphan"
  },

  "cultivation": {
    "realm": "qi_refining",
    "level": 3,
    "progress": 0.65,
    "techniques": [
      {"id": "basic_breathing", "mastery": 0.8},
      {"id": "cloud_step", "mastery": 0.3}
    ]
  },

  "stats": {
    "hp": {"current": 85, "max": 100},
    "spirit_power": {"current": 40, "max": 50},
    "stamina": {"current": 70, "max": 100}
  },

  "location": {
    "current": "yunxia_peak",
    "previous": "practice_ground",
    "home_base": "player_cave"
  },

  "inventory": {
    "spirit_stones": {"low": 150, "mid": 2, "high": 0},
    "items": [
      {"id": "jade_pendant", "quantity": 1, "bound": true},
      {"id": "recovery_pill", "quantity": 5, "bound": false}
    ],
    "equipment": {
      "weapon": "basic_sword",
      "armor": "disciple_robe",
      "accessory": "jade_pendant"
    }
  },

  "sect_status": {
    "faction": "qingyun_sect",
    "rank": "outer_disciple",
    "contribution": 120,
    "reputation": 45
  }
}
```

### 9.4 NPC数据 (npcs/atan.json)

```json
{
  "id": "atan",
  "basic": {
    "name": "沈檀儿",
    "nickname": "阿檀",
    "age": 16,
    "realm": "mortal"
  },

  "location": {
    "current": "kitchen",
    "last_seen_by_player": "kitchen"
  },

  "state": {
    "health": "healthy",
    "mood": "content",
    "current_activity": "preparing_breakfast",
    "interrupted_by": null
  },

  "relationship_with_player": {
    "trust": 65,
    "affection": 72,
    "respect": 55,
    "fear": 0,
    "debt": 3,

    "state_label": "亲近",
    "attitude_tags": ["关心", "依赖", "暗自担忧"],

    "unresolved": [
      {"type": "promise", "content": "带她去看后山的桃花", "made_on": "year_1_month_2"},
      {"type": "question", "content": "为什么最近总是很晚才回来"}
    ]
  },

  "memories": {
    "core": [
      {
        "id": "first_meeting",
        "summary": "流浪时相遇，一起分了半块饼",
        "emotional_weight": 10,
        "timestamp": "prologue"
      },
      {
        "id": "player_protected_her",
        "summary": "被欺负时玩家挺身而出挨了打",
        "emotional_weight": 9,
        "timestamp": "prologue"
      }
    ],

    "recent": [
      {
        "id": "mem_001",
        "summary": "玩家送了一枝野花",
        "importance": 6,
        "emotional_impact": "happy",
        "timestamp": {"year": 1, "month": 3, "day": 10}
      },
      {
        "id": "mem_002",
        "summary": "玩家连续三天没来看她",
        "importance": 4,
        "emotional_impact": "worried",
        "timestamp": {"year": 1, "month": 3, "day": 12}
      }
    ],

    "emotional_ledger": {
      "positive_balance": 15,
      "negative_balance": 3,
      "last_major_event": "mem_001",
      "days_since_interaction": 2
    }
  },

  "secrets": {
    "level_1_revealed": false,
    "level_2_revealed": false,
    "level_3_revealed": false
  },

  "schedule_overrides": []
}
```

### 9.5 事件状态 (events.json)

**重要：所有时间戳使用绝对刻（absolute_tick）存储，便于排序和比较**

```json
{
  "format_version": "1.0",
  "last_saved_tick": 612,

  "triggered_events": [
    {
      "id": "atan_daily_greeting_001",
      "trigger_count": 5,
      "last_triggered_tick": 600,
      "last_triggered_display": "第1年春3月14日午后"
    },
    {
      "id": "master_first_teaching",
      "trigger_count": 1,
      "last_triggered_tick": 20,
      "last_triggered_display": "第1年春1月5日早晨"
    }
  ],

  "cooldowns": {
    "atan_daily_greeting_001": {
      "expires_tick": 616,
      "expires_display": "第1年春3月15日黄昏"
    },
    "random_encounter_forest": {
      "expires_tick": 624,
      "expires_display": "第1年春3月16日黄昏"
    }
  },

  "active_event_chains": [
    {
      "chain_id": "jade_pendant_mystery",
      "current_step": 2,
      "started_tick": 128,
      "started_display": "第1年春2月1日早晨",
      "deadline_tick": null
    }
  ],

  "pending_events": [
    {
      "event_id": "sword_tomb_invitation",
      "scheduled_tick": 2920,
      "scheduled_display": "第3年春5月1日早晨",
      "conditions_met": false
    }
  ],

  "event_history": [
    {
      "event_id": "master_first_teaching",
      "timestamp_tick": 20,
      "timestamp_display": "第1年春1月5日早晨",
      "variant_used": "standard",
      "player_choice": null,
      "outcome": "completed"
    }
  ]
}
```

### 9.6 加载时ID校验

```python
class EventDataValidator:
    """事件数据加载校验器"""

    def __init__(self, event_registry: Dict[str, Event]):
        """
        Args:
            event_registry: 游戏定义的所有事件ID -> Event映射
        """
        self.registry = event_registry

    def validate_and_repair(self, events_data: dict) -> ValidationReport:
        """
        加载时校验events.json，处理ID不匹配问题

        返回:
            ValidationReport: 包含警告、错误、修复操作
        """
        report = ValidationReport()

        # 1. 校验triggered_events中的ID
        valid_triggered = []
        for entry in events_data.get("triggered_events", []):
            event_id = entry.get("id")
            if event_id not in self.registry:
                report.add_warning(
                    f"事件ID '{event_id}' 不存在于当前版本，已从触发记录中移除"
                )
                continue
            valid_triggered.append(entry)
        events_data["triggered_events"] = valid_triggered

        # 2. 校验cooldowns中的ID
        valid_cooldowns = {}
        for event_id, cooldown in events_data.get("cooldowns", {}).items():
            if event_id not in self.registry:
                report.add_warning(
                    f"事件ID '{event_id}' 不存在，冷却记录已移除"
                )
                continue
            valid_cooldowns[event_id] = cooldown
        events_data["cooldowns"] = valid_cooldowns

        # 3. 校验active_event_chains
        valid_chains = []
        for chain in events_data.get("active_event_chains", []):
            chain_id = chain.get("chain_id")
            if not self._chain_exists(chain_id):
                report.add_error(
                    f"事件链 '{chain_id}' 不存在，请检查游戏版本兼容性"
                )
                # 事件链不移除，标记为需要人工处理
                chain["_invalid"] = True
            valid_chains.append(chain)
        events_data["active_event_chains"] = valid_chains

        # 4. 校验pending_events
        valid_pending = []
        for pending in events_data.get("pending_events", []):
            event_id = pending.get("event_id")
            if event_id not in self.registry:
                report.add_warning(
                    f"待触发事件 '{event_id}' 不存在，已移除"
                )
                continue
            valid_pending.append(pending)
        events_data["pending_events"] = valid_pending

        # 5. 检查时间一致性
        current_tick = events_data.get("last_saved_tick", 0)
        for cooldown_id, cooldown in events_data["cooldowns"].items():
            if cooldown.get("expires_tick", 0) < current_tick:
                report.add_info(
                    f"事件 '{cooldown_id}' 冷却已过期，将在加载时清除"
                )
                del events_data["cooldowns"][cooldown_id]

        return report

    def _chain_exists(self, chain_id: str) -> bool:
        """检查事件链是否存在"""
        # 事件链定义在单独的chain_registry中
        return chain_id in self.chain_registry


@dataclass
class ValidationReport:
    """校验报告"""
    infos: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_info(self, msg: str):
        self.infos.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_error(self, msg: str):
        self.errors.append(msg)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def to_log(self) -> str:
        lines = []
        for info in self.infos:
            lines.append(f"[INFO] {info}")
        for warn in self.warnings:
            lines.append(f"[WARN] {warn}")
        for err in self.errors:
            lines.append(f"[ERROR] {err}")
        return "\n".join(lines)


# ============ 绝对刻计算 ============
class TickCalculator:
    """
    绝对刻（absolute_tick）计算器

    时间结构（与 03_systems.md、06_specifications.md 统一）：
    - 1天 = 4时段 = 8时辰（每时段2时辰）
    - 1月 = 30天
    - 1年 = 12月

    tick 定义：
    - 1 tick = 1 时段（即2时辰）
    - 绝对刻 = 从游戏开始经过的时段总数
    - 公式: (year-1)*12*30*4 + (month-1)*30*4 + (day-1)*4 + slot_index

    换算关系：
    - 1天 = 4 ticks (= 4时段 = 8时辰)
    - 1月 = 120 ticks
    - 1年 = 1440 ticks

    如需以时辰为最小单位，可使用 tick * 2 转换为时辰数。
    """

    SLOTS_PER_DAY = 4          # 每天4个时段
    TICKS_PER_DAY = 4          # 每天4个tick（1 tick = 1 时段）
    HOURS_PER_SLOT = 2         # 每时段2时辰
    HOURS_PER_DAY = 8          # 每天8时辰
    DAYS_PER_MONTH = 30
    MONTHS_PER_YEAR = 12

    SLOT_INDEX = {
        "morning": 0,
        "afternoon": 1,
        "evening": 2,
        "night": 3
    }

    @classmethod
    def to_tick(cls, year: int, month: int, day: int, slot: str) -> int:
        """将游戏时间转换为绝对刻"""
        slot_idx = cls.SLOT_INDEX.get(slot, 0)
        return (
            (year - 1) * cls.MONTHS_PER_YEAR * cls.DAYS_PER_MONTH * cls.SLOTS_PER_DAY +
            (month - 1) * cls.DAYS_PER_MONTH * cls.SLOTS_PER_DAY +
            (day - 1) * cls.SLOTS_PER_DAY +
            slot_idx
        )

    @classmethod
    def from_tick(cls, tick: int) -> dict:
        """将绝对刻转换为游戏时间"""
        slots_per_year = cls.MONTHS_PER_YEAR * cls.DAYS_PER_MONTH * cls.SLOTS_PER_DAY
        slots_per_month = cls.DAYS_PER_MONTH * cls.SLOTS_PER_DAY

        year = tick // slots_per_year + 1
        remainder = tick % slots_per_year

        month = remainder // slots_per_month + 1
        remainder = remainder % slots_per_month

        day = remainder // cls.SLOTS_PER_DAY + 1
        slot_idx = remainder % cls.SLOTS_PER_DAY

        slot_names = ["morning", "afternoon", "evening", "night"]

        return {
            "year": year,
            "month": month,
            "day": day,
            "slot": slot_names[slot_idx]
        }

    @classmethod
    def to_display(cls, tick: int) -> str:
        """将绝对刻转换为显示字符串"""
        t = cls.from_tick(tick)
        seasons = ["春", "夏", "秋", "冬"]
        season = seasons[(t["month"] - 1) // 3]
        slot_names = {
            "morning": "早晨",
            "afternoon": "午后",
            "evening": "黄昏",
            "night": "夜晚"
        }
        return f"第{t['year']}年{season}{t['month']}月{t['day']}日{slot_names[t['slot']]}"
```

### 9.7 剧情标记 (story_flags.json)

```json
{
  "main_storylines": {
    "revenge": {
      "phase": 1,
      "flags": {
        "parents_death_known": true,
        "jade_pendant_activated": false,
        "enemy_first_encounter": false
      }
    },
    "bond": {
      "phase": 1,
      "flags": {
        "atan_awakening_hint": false,
        "atan_confession": false
      }
    },
    "truth": {
      "phase": 0,
      "flags": {}
    }
  },

  "world_flags": {
    "joined_sect": true,
    "completed_first_mission": true,
    "met_senior_brother": true,
    "met_junior_sister": true
  },

  "npc_flags": {
    "atan": {
      "knows_player_identity": false,
      "cultivation_started": false
    },
    "master": {
      "shared_wine": false,
      "mentioned_past": false
    }
  },

  "achievements": [
    {"id": "first_breakthrough", "unlocked_at": {"year": 1, "month": 2, "day": 15}},
    {"id": "first_friend", "unlocked_at": {"year": 1, "month": 1, "day": 1}}
  ]
}
```

### 9.8 存档读写接口

```python
class SaveManager:
    """存档管理器"""

    SAVE_VERSION = "1.0"

    def save(self, save_id: str, save_name: str = None):
        """保存游戏"""
        save_dir = Path(f"data/saves/{save_id}")
        save_dir.mkdir(parents=True, exist_ok=True)

        # 1. 保存manifest
        manifest = {
            "save_id": save_id,
            "save_name": save_name or f"存档 {save_id}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "game_version": GAME_VERSION,
            "save_format_version": self.SAVE_VERSION,
            "play_time_hours": self.game.play_time_hours
        }
        self._write_yaml(save_dir / "manifest.yaml", manifest)

        # 2. 保存各模块数据
        self._write_json(save_dir / "world_state.json",
                        self.world_manager.serialize())
        self._write_json(save_dir / "player.json",
                        self.player.serialize())
        self._write_json(save_dir / "events.json",
                        self.event_manager.serialize())
        self._write_json(save_dir / "story_flags.json",
                        self.story_manager.serialize())

        # 3. 保存NPC数据
        npcs_dir = save_dir / "npcs"
        npcs_dir.mkdir(exist_ok=True)
        for npc in self.character_manager.all_npcs():
            self._write_json(npcs_dir / f"{npc.id}.json", npc.serialize())

        return save_dir

    def load(self, save_id: str):
        """加载游戏"""
        save_dir = Path(f"data/saves/{save_id}")

        # 1. 读取manifest，检查版本
        manifest = self._read_yaml(save_dir / "manifest.yaml")
        self._check_version_compatibility(manifest["save_format_version"])

        # 2. 加载各模块
        self.world_manager.deserialize(
            self._read_json(save_dir / "world_state.json"))
        self.player.deserialize(
            self._read_json(save_dir / "player.json"))
        self.event_manager.deserialize(
            self._read_json(save_dir / "events.json"))
        self.story_manager.deserialize(
            self._read_json(save_dir / "story_flags.json"))

        # 3. 加载NPC数据
        npcs_dir = save_dir / "npcs"
        for npc_file in npcs_dir.glob("*.json"):
            npc_data = self._read_json(npc_file)
            self.character_manager.load_npc(npc_data)

    def auto_save(self):
        """自动存档（每推进1天调用）"""
        self.save("autosave", "自动存档")

    def list_saves(self) -> List[SaveInfo]:
        """列出所有存档"""
        saves_dir = Path("data/saves")
        saves = []

        for save_dir in saves_dir.iterdir():
            if save_dir.is_dir():
                manifest_path = save_dir / "manifest.yaml"
                if manifest_path.exists():
                    manifest = self._read_yaml(manifest_path)
                    saves.append(SaveInfo(
                        save_id=manifest["save_id"],
                        save_name=manifest["save_name"],
                        updated_at=manifest["updated_at"],
                        play_time=manifest["play_time_hours"]
                    ))

        return sorted(saves, key=lambda s: s.updated_at, reverse=True)
```

### 9.9 数据迁移策略

```python
class SaveMigrator:
    """存档版本迁移"""

    MIGRATIONS = {
        ("1.0", "1.1"): "_migrate_1_0_to_1_1",
        ("1.1", "1.2"): "_migrate_1_1_to_1_2",
    }

    def migrate(self, save_data: dict, from_version: str, to_version: str) -> dict:
        """执行迁移"""
        current = from_version

        while current != to_version:
            migration_key = (current, self._next_version(current))
            if migration_key not in self.MIGRATIONS:
                raise MigrationError(f"No migration path from {current}")

            migration_func = getattr(self, self.MIGRATIONS[migration_key])
            save_data = migration_func(save_data)
            current = migration_key[1]

        return save_data

    def _migrate_1_0_to_1_1(self, data: dict) -> dict:
        """示例迁移：添加新字段"""
        # 为player添加新的stats字段
        if "mental_state" not in data["player"]["stats"]:
            data["player"]["stats"]["mental_state"] = {"current": 100, "max": 100}

        # 更新版本号
        data["manifest"]["save_format_version"] = "1.1"
        return data
```

---

*本文档定义了技术实现的整体架构。核心原则：规则驱动世界运转，AI负责叙事润色，分工明确，不越界。AI成本需要精细管控，持久化需要版本兼容。*

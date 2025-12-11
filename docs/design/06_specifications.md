# 基础规范文档

> 版本: 1.0
> 本文档定义跨模块的统一规范、ID词表、公式和流程，解决设计文档间的缝隙问题

---

## 第一章：时间系统规范

### 1.1 时间单位定义

```yaml
time_units:
  # 基础单位
  时辰:
    real_world_equivalent: 2小时
    game_ticks: 1
    description: 最小可操作时间单位

  时段:
    composition: 2时辰
    values: [morning, afternoon, evening, night]
    game_ticks: 2

  日:
    composition: 4时段 = 8时辰
    game_ticks: 8

  月:
    composition: 30日
    game_ticks: 240

  季:
    composition: 3月
    game_ticks: 720

  年:
    composition: 4季 = 12月
    game_ticks: 2880

# 时段对应时辰（每时段固定2时辰）
time_slot_mapping:
  morning:    [第1时辰, 第2时辰]  # 05:00-09:00 (2时辰)
  afternoon:  [第3时辰, 第4时辰]  # 09:00-13:00 (2时辰)
  evening:    [第5时辰, 第6时辰]  # 13:00-17:00 (2时辰)
  night:      [第7时辰, 第8时辰]  # 17:00-21:00 (2时辰)
  # 21:00-05:00 为休眠期，不计入活动时辰
  # 合计：4时段 × 2时辰 = 8时辰/日 ✓
```

### 1.2 旅行时间规范

**所有 `travel_time` 字段单位统一为"时辰"**

```yaml
travel_time_rules:
  unit: 时辰

  # 移动方式修正
  modifiers:
    walk: 1.0      # 基准
    fly: 0.2       # 飞行速度是步行5倍
    teleport: 0    # 瞬移

  # 跨时段规则
  cross_slot_rules:
    # 移动消耗 <= 当前时段剩余时辰：在当前时段内完成
    # 移动消耗 > 当前时段剩余时辰：进入下一时段

    calculation: |
      remaining_in_slot = slot_end_tick - current_tick
      if travel_time <= remaining_in_slot:
          arrive_in_current_slot()
      else:
          overflow = travel_time - remaining_in_slot
          advance_slots(ceil(overflow / 2))  # 每时段2时辰

  # 跨日规则
  cross_day_rules:
    threshold: 8  # 超过8时辰（1日）视为长途旅行
    treatment: |
      if travel_time >= 8:
          enter_long_action_mode()
          simulate_day_by_day()
      else:
          normal_travel()

  # 夜间移动惩罚
  night_travel:
    speed_modifier: 0.5   # 夜间移动速度减半
    danger_modifier: 1.5  # 危险遭遇概率增加
    exception: "筑基以上或有照明法器"
```

### 1.3 跨日移动完整示例

```python
class TravelSimulator:
    """旅行模拟器 - 处理跨日移动"""

    def simulate_travel(self, origin: str, destination: str,
                        start_time: GameTime) -> TravelResult:
        """
        完整旅行模拟示例：从青云门到剑冢 (20时辰)

        示例时间线：
        - 出发：第1年3月15日 morning (第1时辰)
        - 距离：20时辰（飞行4时辰，步行20时辰）
        - 假设步行
        """
        travel_time = self.get_travel_time(origin, destination)  # 20
        current = start_time.copy()

        # === 第1天：15日 ===
        # morning: 第1-2时辰 → 出发，消耗2时辰，剩余18
        # afternoon: 第3-4时辰 → 赶路，消耗2时辰，剩余16
        # evening: 第5-6时辰 → 赶路，消耗2时辰，剩余14
        # night: 第7-8时辰 → 夜间减速(×0.5)，实际消耗1时辰，剩余13
        #        → 日结算触发：relationship_decay, days_since_interaction++

        # === 第2天：16日 ===
        # morning: 2时辰，剩余11
        # afternoon: 2时辰，剩余9
        # evening: 2时辰，剩余7
        # night: 1时辰（夜间减速），剩余6
        #        → 日结算触发

        # === 第3天：17日 ===
        # morning-evening: 6时辰，剩余0
        # 抵达时间：第1年3月17日 evening

        days_elapsed = 0
        remaining = travel_time

        while remaining > 0:
            # 计算当前时段可用时辰
            slot_remaining = current.get_slot_remaining_ticks()

            # 夜间减速
            speed_mod = 0.5 if current.slot == 'night' else 1.0
            effective_travel = min(slot_remaining, remaining / speed_mod) * speed_mod

            remaining -= effective_travel
            current.advance_ticks(int(effective_travel / speed_mod))

            # 跨日检查
            if current.tick == 0:  # 新的一天开始
                days_elapsed += 1
                self._trigger_daily_settlement_for_traveler()

        return TravelResult(
            arrival_time=current,
            days_on_road=days_elapsed,
            total_decay_applied=days_elapsed  # 每天都触发衰减
        )

    def _trigger_daily_settlement_for_traveler(self):
        """旅途中的每日结算"""
        # 1. 关系衰减照常执行
        self.relationship_manager.apply_daily_decay_all()

        # 2. 互动计数照常增加（玩家在路上=没互动）
        for npc in self.npc_manager.get_all():
            npc.memory.days_since_interaction += 1

        # 3. 随机遭遇检查（旅途专用）
        if random.random() < 0.15:  # 15%概率
            self.event_scheduler.roll_travel_encounter()
```

### 1.4 长行动与日程衔接

```yaml
long_action_settlement:
  # 长行动定义
  definition:
    threshold: "> 1日"
    examples: [闭关, 远行, 炼丹, 疗伤]

  # 每日模拟流程
  daily_simulation_order:
    1_morning:
      - execute_npc_schedules(morning)
      - check_time_slot_events(morning)
      - apply_random_perturbation(0.05)

    2_afternoon:
      - execute_npc_schedules(afternoon)
      - check_time_slot_events(afternoon)
      - apply_random_perturbation(0.05)

    3_evening:
      - execute_npc_schedules(evening)
      - check_time_slot_events(evening)
      - apply_random_perturbation(0.03)

    4_night:
      - execute_npc_schedules(night)
      - check_time_slot_events(night)

    5_daily_settlement:
      - apply_relationship_decay()
      - update_days_since_interaction()
      - check_pending_events_expiry()
      - check_interrupt_events()  # 可能打断长行动
      - auto_save_if_needed()

  # 长行动中的位置
  player_location_during_long_action:
    retreat: "personal_cave"      # 闭关
    travel: "in_transit"          # 旅途中（特殊节点）
    alchemy: "alchemy_room"       # 炼丹
    healing: "healing_chamber"    # 疗伤

  # 打断判定
  interrupt_check:
    frequency: "每日结算时"
    triggers:
      - "critical_pool 事件触发"
      - "NPC主动寻找玩家且 priority >= 80"
      - "玩家生命危险"
      - "外敌入侵门派"
```

### 1.4 结算钩子时机表

```yaml
settlement_hooks:
  # 每时段
  per_slot:
    - npc_schedule_execution
    - event_trigger_check
    - random_perturbation_roll

  # 每日
  per_day:
    - relationship_decay_daily        # trust/affection 按日衰减
    - days_since_interaction += 1     # 未互动天数
    - pending_events_expiry_check     # 过期事件检查
    - npc_emotion_decay               # 情绪衰减
    - economy_daily_expense           # 每日消耗扣款

  # 每周 (每7日)
  per_week:
    - memory_relevance_update         # 记忆相关性刷新
    - npc_goal_progress_check         # NPC目标进度

  # 每月 (每30日)
  per_month:
    - relationship_monthly_decay      # 月度大衰减
    - memory_compression              # 记忆压缩
    - economy_monthly_settlement      # 月结算（门派月例等）
    - world_state_evolution           # 世界状态演化
    - price_fluctuation               # 价格波动

  # 每季 (每90日)
  per_season:
    - narrative_attractor_recommendation  # 叙事吸引子推荐
    - major_event_scheduling              # 大型事件安排

  # 每年 (每360日)
  per_year:
    - age_increment                   # 年龄增长
    - npc_lifecycle_check             # NPC生命周期事件
    - spirit_decline_check            # 灵气衰减检查
    - cultivation_bottleneck_check    # 修炼瓶颈检查
```

---

## 第二章：ID命名规范

### 2.1 ID命名规则

```yaml
id_conventions:
  # 通用规则
  general:
    format: snake_case
    language: english
    max_length: 50
    allowed_chars: "[a-z0-9_]"

  # 各类型前缀
  prefixes:
    location: ""              # 地点无前缀：qingyun_sect
    npc: ""                   # NPC无前缀：atan, master_yunyin
    event: ""                 # 事件无前缀：revenge_001
    item: "item_"             # 物品：item_jade_pendant
    skill: "skill_"           # 技能：skill_basic_sword
    flag: "flag_"             # 标记：flag_parents_death_known
    quest: "quest_"           # 任务：quest_first_mission

  # 命名模式
  patterns:
    location: "{region}_{place}" or "{place}"
    npc: "{role}_{name}" or "{nickname}"
    event: "{storyline}_{sequence}" or "{category}_{sequence}"
    flag: "flag_{subject}_{state}"
```

### 2.2 地点ID词表 (location_id)

```yaml
# ============ 青云门区域 ============
qingyun_sect:
  id: qingyun_sect
  type: sect
  region: east_domain
  display_name: 青云门
  aliases: [青云, 本门, 门派]

  # 子节点
  sub_locations:
    yunxia_peak:
      id: yunxia_peak
      display_name: 云霞峰
      aliases: [师父的山峰, 云隐子洞府]
      travel_time_from_main: 2  # 时辰

    main_hall:
      id: main_hall
      display_name: 大殿
      aliases: [议事大殿, 门派大厅]
      travel_time_from_main: 0

    practice_ground:
      id: practice_ground
      display_name: 演武场
      aliases: [练功场, 比武场]
      travel_time_from_main: 1

    library:
      id: library
      display_name: 藏经阁
      aliases: [经阁, 典籍楼]
      travel_time_from_main: 2

    herb_garden:
      id: herb_garden
      display_name: 药园
      aliases: [灵药园, 种药处]
      travel_time_from_main: 3

    sect_market:
      id: sect_market
      display_name: 坊市
      aliases: [门派市场, 交易区]
      travel_time_from_main: 2

    kitchen:
      id: kitchen
      display_name: 膳房
      aliases: [厨房, 伙房]
      travel_time_from_main: 2

    servant_quarters:
      id: servant_quarters
      display_name: 杂役住所
      aliases: [下人房, 仆役区]
      travel_time_from_main: 3

    player_cave:
      id: player_cave
      display_name: 玩家洞府
      aliases: [我的洞府, 住处]
      travel_time_from_main: 2

    back_mountain:
      id: back_mountain
      display_name: 后山
      aliases: [山后, 后峰]
      travel_time_from_main: 4

    back_mountain_stream:
      id: back_mountain_stream
      display_name: 后山溪边
      aliases: [溪边, 小溪]
      parent: back_mountain
      travel_time_from_main: 5

    back_mountain_cliff:
      id: back_mountain_cliff
      display_name: 后山悬崖
      aliases: [悬崖, 断崖]
      parent: back_mountain
      travel_time_from_main: 6

# ============ 野外区域 ============
qingfeng_forest:
  id: qingfeng_forest
  type: wild
  region: east_domain
  display_name: 青风林
  aliases: [青风森林, 林子]
  travel_time_from_qingyun: 4
  danger_level: low

broken_valley:
  id: broken_valley
  type: wild
  region: east_domain
  display_name: 断魂谷
  aliases: [断谷, 凶险之地]
  travel_time_from_qingyun: 8
  danger_level: medium

abandoned_mine:
  id: abandoned_mine
  type: wild
  region: east_domain
  display_name: 废弃矿洞
  aliases: [矿洞, 旧矿, 矿洞节点]  # 统一事件中的"矿洞节点"
  travel_time_from_qingyun: 6
  danger_level: medium

# ============ 城镇 ============
tianji_city:
  id: tianji_city
  type: city
  region: center_domain
  display_name: 天机城
  aliases: [天机, 大城]
  travel_time_from_qingyun: 10

  sub_locations:
    auction_house:
      id: tianji_auction_house
      display_name: 万宝楼
      aliases: [拍卖行]

    tianji_inn:
      id: tianji_inn
      display_name: 云来客栈
      aliases: [客栈, 旅店]

    tianji_black_market:
      id: tianji_black_market
      display_name: 黑市
      aliases: [地下市场]

# ============ 秘境 ============
sword_tomb:
  id: sword_tomb
  type: secret_realm
  region: north_domain
  display_name: 剑冢
  aliases: [剑墓, 万剑冢]
  travel_time_from_qingyun: 20
  danger_level: extreme

ancient_cave:
  id: ancient_cave
  type: secret_realm
  region: west_domain
  display_name: 上古洞府
  aliases: [古洞, 遗迹]
  travel_time_from_qingyun: 15
  danger_level: high

# ============ 特殊节点 ============
in_transit:
  id: in_transit
  type: special
  display_name: 旅途中
  description: 长途旅行时的虚拟位置

personal_cave:
  id: personal_cave
  type: special
  display_name: 个人洞府
  aliases: [我的洞府, 闭关处, player_residence]
  description: 玩家的私人空间，闭关/休息时的位置
  note: "与player_cave区分：player_cave是青云门内的具体洞府，personal_cave是抽象的私人空间概念"

# ============ 路段节点（用于护送/旅行事件）============
escort_routes:
  qingyun_to_tianji_route:
    id: qingyun_to_tianji_route
    type: route
    display_name: 青云门至天机城商路
    aliases: [护送路段, 商路]
    waypoints: [qingyun_sect, qingfeng_forest, broken_valley, tianji_city]
    total_travel_time: 10
    danger_zones: [broken_valley]

  qingyun_to_sword_tomb_route:
    id: qingyun_to_sword_tomb_route
    type: route
    display_name: 青云门至剑冢之路
    aliases: [北上之路, 剑冢路]
    waypoints: [qingyun_sect, north_pass, sword_tomb]
    total_travel_time: 20
    danger_zones: [north_pass]

# ============ 秘境入口 ============
secret_realm_entrances:
  sword_tomb_entrance:
    id: sword_tomb_entrance
    type: entrance
    display_name: 剑冢入口
    aliases: [剑冢门户, 危险秘境入口]
    parent: sword_tomb
    travel_time_from_qingyun: 20
    access_condition: "需要门派令牌或特殊机缘"

  ancient_cave_entrance:
    id: ancient_cave_entrance
    type: entrance
    display_name: 上古洞府入口
    aliases: [古洞入口, 遗迹入口]
    parent: ancient_cave
    travel_time_from_qingyun: 15
    access_condition: "需要特定钥匙或阵法知识"

# ============ 危险区域节点 ============
danger_zones:
  north_pass:
    id: north_pass
    type: wild
    display_name: 北境隘口
    aliases: [危险山口, 妖兽出没处]
    travel_time_from_qingyun: 12
    danger_level: high
    note: "通往剑冢的必经之路，常有妖兽出没"

  demon_forest:
    id: demon_forest
    type: wild
    display_name: 幽冥林
    aliases: [黑森林, 魔林]
    travel_time_from_qingyun: 15
    danger_level: extreme
    note: "幽冥宗势力范围边缘"

# ============ 云峰顶（单独列出，事件中常用）============
cloud_peak_top:
  id: cloud_peak_top
  type: landmark
  display_name: 云峰顶
  aliases: [山顶, 峰顶, 最高处]
  parent: yunxia_peak
  travel_time_from_yunxia: 1
  spirit_density: 1.5
  note: "师父常在此处观云悟道，重要对话场景"
```

### 2.3 NPC ID词表 (npc_id)

```yaml
# ============ 核心NPC ============
atan:
  id: atan
  display_name: 沈檀儿
  aliases: [阿檀, 檀儿, 她]
  category: core

master_yunyin:
  id: master_yunyin
  display_name: 云隐子
  aliases: [师父, 云隐真人, 秦远]
  category: core

enemy_xuanying:
  id: enemy_xuanying
  display_name: 玄影
  aliases: [仇人, 黑衣人, 那个人]
  category: core

senior_suyunfan:
  id: senior_suyunfan
  display_name: 苏云帆
  aliases: [大师兄, 师兄, 云帆]
  category: core

junior_linxueyao:
  id: junior_linxueyao
  display_name: 林雪瑶
  aliases: [小师妹, 雪瑶, 师妹]
  category: core

# ============ 重要NPC ============
sect_master:
  id: sect_master
  display_name: 清虚真人
  aliases: [掌门, 掌门师伯]
  category: important

elder_luo:
  id: elder_luo
  display_name: 洛天明
  aliases: [洛长老, 执法长老]
  category: important

elder_zhao:
  id: elder_zhao
  display_name: 赵元真
  aliases: [赵长老, 那个刁难人的长老]
  category: important

# ============ 其他势力 ============
wanjian_genius:
  id: wanjian_genius
  display_name: 萧逸尘
  aliases: [剑痴, 万剑宗那个天才]
  category: other_faction

youming_yueji:
  id: youming_yueji
  display_name: 月姬
  aliases: [神秘女子, 玄影师妹]
  category: other_faction
```

### 2.4 行动ID词表 (action_id)

```yaml
# ============ 日常行动 ============
daily_actions:
  prepare_meal:
    id: prepare_meal
    display_variants: [准备饭菜, 做饭, 准备早膳, 准备午膳]

  wash_clothes:
    id: wash_clothes
    display_variants: [洗衣, 洗衣服, 浆洗]

  fetch_water:
    id: fetch_water
    display_variants: [打水, 挑水, 取水]

  gather_herbs:
    id: gather_herbs
    display_variants: [采药, 采集灵草, 摘药]

  sweep_floor:
    id: sweep_floor
    display_variants: [扫地, 打扫, 清扫]

  rest:
    id: rest
    display_variants: [休息, 歇息, 小憩]

  sleep:
    id: sleep
    display_variants: [睡觉, 就寝, 入眠]

# ============ 修炼行动 ============
cultivation_actions:
  meditate:
    id: meditate
    display_variants: [打坐, 吐纳, 冥想, 修炼]

  practice_technique:
    id: practice_technique
    display_variants: [练功, 修炼武技, 练习剑法]

  study_manual:
    id: study_manual
    display_variants: [研读功法, 看书, 参悟典籍]

  refine_pill:
    id: refine_pill
    display_variants: [炼丹, 炼制丹药]

  breakthrough_attempt:
    id: breakthrough_attempt
    display_variants: [冲击境界, 突破, 闭关突破]

# ============ 社交行动 ============
social_actions:
  chat:
    id: chat
    display_variants: [闲聊, 聊天, 说话]

  teach:
    id: teach
    display_variants: [指导, 教导, 传授]

  spar:
    id: spar
    display_variants: [切磋, 比试, 过招]

  wait_for_someone:
    id: wait_for_someone
    display_variants: [等人, 等待, 守候]

# ============ 移动行动 ============
movement_actions:
  walk:
    id: walk
    display_variants: [步行, 走路, 前往]

  fly:
    id: fly
    display_variants: [飞行, 御剑飞行, 腾空]

  patrol:
    id: patrol
    display_variants: [巡逻, 巡视, 查看]
```

---

## 第三章：事件系统规范

### 3.1 事件数据结构完整定义

```yaml
event_schema:
  # 基础信息
  id: string                    # 唯一标识，如 "revenge_001"
  name: string                  # 显示名称
  category: enum                # encounter/plot/daily/crisis
  tier: enum                    # daily/opportunity/critical

  # 调度控制
  scheduling:
    priority: float             # 0.0-1.0，越高越优先
    cooldown: TimeDelta         # 冷却时间
    max_triggers: int           # 最大触发次数，-1表示无限
    trigger_count: int          # 当前已触发次数

  # 互斥与并发
  concurrency:
    mutex_groups: List[string]  # 互斥组，同组事件不能同时触发
    exclusive_with: List[string] # 与特定事件互斥
    concurrency_slot: string    # 占用的并发槽位

  # 触发条件
  conditions:
    time_window:
      start: GameTime | null
      end: GameTime | null
      slots: List[TimeSlot] | null  # 限定时段
      days_of_month: List[int] | null

    locations: List[location_id]    # 必须用ID
    location_type: string | null    # 或按类型匹配

    preconditions:
      flags_required: List[string]
      flags_forbidden: List[string]
      relationship: Dict[npc_id, condition]
      player_state: Dict[stat, condition]
      world_state: Dict[key, condition]

  # 打断规则
  interrupt:
    can_interrupt: bool         # 是否可打断其他事件
    can_be_interrupted: bool    # 是否可被打断
    interrupt_priority: int     # 打断优先级，越高越难被打断

  # 过期处理
  expiry:
    deadline: GameTime | null   # 绝对截止时间
    duration: TimeDelta | null  # 相对有效期（从可触发开始计算）
    expiry_consequence:
      type: enum                # none/flag_set/relationship_change/trigger_event
      details: Dict

  # 效果
  effects:
    set_flags: List[string]
    clear_flags: List[string]
    relationship_changes: List[RelationshipChange]
    world_state_changes: Dict
    schedule_followups: List[FollowupConfig]
    unlock_events: List[event_id]
    lock_events: List[event_id]

  # 变体
  variants: List[EventVariant]

  # AI叙事配置
  narrative:
    template_id: string | null
    ai_prompt_tags: List[string]
    tone: string
    length: enum                # short/medium/long
```

### 3.2 事件调度完整算法

```python
class EventScheduler:
    """事件调度器完整实现"""

    def __init__(self, world_manager, character_manager, story_manager):
        # 依赖注入
        self.world = world_manager
        self.characters = character_manager
        self.story = story_manager

        # 事件池
        self.pools = {
            'critical': [],
            'opportunity': [],
            'daily': []
        }

        # 状态
        self.cooldowns: Dict[str, GameTime] = {}
        self.pending_events: List[PendingEvent] = []
        self.active_mutex_groups: Set[str] = set()

        # 配额
        self.slot_quotas = {
            'critical': 1,
            'opportunity': 2,
            'daily': 3
        }

    def check_and_trigger(self) -> List[TriggeredEvent]:
        """主入口：检查并触发事件"""
        triggered = []

        # 按优先级顺序检查
        for tier in ['critical', 'opportunity', 'daily']:
            tier_triggered = self._process_tier(tier)
            triggered.extend(tier_triggered)

        return triggered

    def _process_tier(self, tier: str) -> List[TriggeredEvent]:
        """处理单个层级"""
        candidates = self._find_candidates(self.pools[tier])
        if not candidates:
            return []

        # 评分排序
        scored = [(self._calculate_score(e), e) for e in candidates]
        scored.sort(reverse=True, key=lambda x: x[0])

        # 按配额和互斥选择
        selected = []
        quota = self.slot_quotas[tier]

        for score, event in scored:
            if len(selected) >= quota:
                break

            # 检查互斥
            if self._check_mutex_conflict(event, selected):
                continue

            # 检查并发槽
            if not self._check_concurrency_slot(event):
                continue

            selected.append(event)

        # 触发选中的事件
        return [self._trigger_event(e) for e in selected]

    def _find_candidates(self, pool: List[Event]) -> List[Event]:
        """找出所有满足条件的候选"""
        candidates = []
        current_time = self.world.time_system.current_time
        current_location = self.world.player_location

        for event in pool:
            # 1. 检查冷却
            if event.id in self.cooldowns:
                if current_time < self.cooldowns[event.id]:
                    continue

            # 2. 检查触发次数
            if event.max_triggers != -1:
                if event.trigger_count >= event.max_triggers:
                    continue

            # 3. 检查时间窗口
            if not self._check_time_window(event, current_time):
                continue

            # 4. 检查地点
            if event.locations and current_location not in event.locations:
                continue

            # 5. 检查前置条件
            if not self._check_preconditions(event):
                continue

            candidates.append(event)

        return candidates

    def _calculate_score(self, event: Event) -> float:
        """计算事件评分"""
        score = 0.0

        # 1. 基础优先级 (权重 0.35)
        score += event.priority * 0.35

        # 2. 紧急度 (权重 0.30)
        urgency = self._calculate_urgency(event)
        score += urgency * 0.30

        # 3. 相关性 (权重 0.25)
        relevance = self._calculate_relevance(event)
        score += relevance * 0.25

        # 4. 随机因子 (权重 0.10)
        score += random.random() * 0.10

        return score

    def _calculate_urgency(self, event: Event) -> float:
        """计算紧急度：越接近过期越紧急"""
        if not event.expiry.deadline:
            return 0.5  # 无截止时间，中等紧急

        current = self.world.time_system.current_time
        deadline = event.expiry.deadline
        total_window = (deadline - event.available_from).total_days()
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

        # 地点匹配
        if self.world.player_location in event.locations:
            relevance += 0.3

        # NPC在场
        npcs_here = self.world.get_npcs_at_location(self.world.player_location)
        for npc in npcs_here:
            if npc.id in event.involved_npcs:
                relevance += 0.2

        # 剧情连贯性
        if event.follows_event:
            if event.follows_event in self.story.recently_triggered:
                relevance += 0.3

        return min(1.0, relevance)

    def _check_mutex_conflict(self, event: Event, selected: List[Event]) -> bool:
        """检查互斥冲突"""
        for group in event.mutex_groups:
            if group in self.active_mutex_groups:
                return True

        for selected_event in selected:
            if event.id in selected_event.exclusive_with:
                return True
            if selected_event.id in event.exclusive_with:
                return True

        return False

    def _trigger_event(self, event: Event) -> TriggeredEvent:
        """触发事件"""
        # 1. 更新计数和冷却
        event.trigger_count += 1
        if event.cooldown:
            self.cooldowns[event.id] = (
                self.world.time_system.current_time + event.cooldown
            )

        # 2. 占用互斥组
        for group in event.mutex_groups:
            self.active_mutex_groups.add(group)

        # 3. 应用效果
        self._apply_effects(event.effects)

        # 4. 选择变体
        variant = self._select_variant(event)

        return TriggeredEvent(event=event, variant=variant)

    # ========== 过期处理 ==========

    def check_expiry(self):
        """每日结算时调用：检查过期事件"""
        current_time = self.world.time_system.current_time
        expired = []

        for pending in self.pending_events:
            if pending.deadline and current_time > pending.deadline:
                expired.append(pending)

        for event in expired:
            self._handle_expiry(event)
            self.pending_events.remove(event)

    def _handle_expiry(self, event: Event):
        """处理过期事件"""
        consequence = event.expiry_consequence

        if consequence.type == 'none':
            pass

        elif consequence.type == 'flag_set':
            for flag in consequence.details.get('flags', []):
                self.story.set_flag(flag)

        elif consequence.type == 'relationship_change':
            for change in consequence.details.get('changes', []):
                self.characters.update_relationship(
                    change['npc'],
                    change['changes'],
                    f"错过事件: {event.name}"
                )

        elif consequence.type == 'trigger_event':
            followup_id = consequence.details.get('event_id')
            if followup_id:
                self._schedule_followup(followup_id, delay=0)

        # 记录到历史
        self.story.record_event_result(event.id, 'expired')
```

### 3.3 打断与对话栈

```python
class InterruptManager:
    """打断管理器"""

    def __init__(self):
        self.dialogue_stack: List[DialogueState] = []
        self.interrupted_actions: List[InterruptedAction] = []

    def try_interrupt(self, new_event: Event, current_context: Context) -> bool:
        """尝试打断当前活动"""
        if not new_event.can_interrupt:
            return False

        current_priority = current_context.current_priority

        if new_event.interrupt_priority > current_priority:
            # 保存当前状态
            self._save_current_state(current_context)

            # 执行打断
            return True

        return False

    def _save_current_state(self, context: Context):
        """保存被打断的状态"""
        if context.in_dialogue:
            self.dialogue_stack.append(DialogueState(
                npc_id=context.dialogue_npc,
                topic=context.dialogue_topic,
                turn=context.dialogue_turn,
                saved_at=context.current_time,
                expires_at=context.current_time.end_of_day()  # 对话当日过期
            ))
        else:
            self.interrupted_actions.append(InterruptedAction(
                action_id=context.current_action,
                progress=context.action_progress,
                saved_at=context.current_time,
                expires_at=context.current_time + TimeDelta(slots=2)  # 2时段后过期
            ))

    def try_resume(self, context: Context) -> Optional[ResumeAction]:
        """尝试恢复被打断的活动"""
        current_time = context.current_time

        # 检查对话栈
        if self.dialogue_stack:
            dialogue = self.dialogue_stack[-1]
            if current_time <= dialogue.expires_at:
                self.dialogue_stack.pop()
                return ResumeAction(
                    type='dialogue',
                    state=dialogue,
                    prompt=f"（之前的对话被打断了）要继续和{dialogue.npc_id}的对话吗？"
                )
            else:
                # 过期，丢弃
                self.dialogue_stack.pop()

        # 检查行动栈
        if self.interrupted_actions:
            action = self.interrupted_actions[-1]
            if current_time <= action.expires_at:
                self.interrupted_actions.pop()
                return ResumeAction(
                    type='action',
                    state=action,
                    prompt=f"要继续之前的{action.action_id}吗？"
                )
            else:
                self.interrupted_actions.pop()

        return None

    def daily_cleanup(self):
        """每日清理过期的打断状态"""
        current_time = get_current_time()

        self.dialogue_stack = [
            d for d in self.dialogue_stack
            if d.expires_at >= current_time
        ]

        self.interrupted_actions = [
            a for a in self.interrupted_actions
            if a.expires_at >= current_time
        ]
```

---

## 第四章：NPC决策系统规范

### 4.1 决策权重公式

```python
class NPCDecisionEngine:
    """NPC决策引擎"""

    def decide_action(self, npc: NPC, context: DecisionContext) -> Action:
        """决定NPC的行动"""
        candidates = self._get_action_candidates(npc, context)
        scored = []

        for action in candidates:
            score = self._calculate_action_score(npc, action, context)
            scored.append((score, action))

        # 排序并选择
        scored.sort(reverse=True, key=lambda x: x[0])

        # 使用softmax增加随机性，或直接选最高
        if context.allow_randomness:
            return self._softmax_select(scored, temperature=0.3)
        else:
            return scored[0][1]

    def _calculate_action_score(self, npc: NPC, action: Action,
                                 context: DecisionContext) -> float:
        """
        核心评分公式：
        score = Σ(weight_i × goal_alignment_i) + emotion_mod + relationship_mod + risk_mod + noise
        """
        score = 0.0

        # 1. 目标对齐度 (权重来自 decision_weights)
        for goal in npc.current_goals:
            weight = npc.decision_weights.get(goal.type, 0.5)
            alignment = self._calculate_goal_alignment(action, goal)
            score += weight * alignment

        # 2. 情绪修正
        emotion_mod = self._get_emotion_modifier(npc.current_mood, action)
        score += emotion_mod * 0.2

        # 3. 关系修正（与玩家的关系影响涉及玩家的行动）
        if action.involves_player:
            relationship = self.characters.get_relationship(npc.id)
            relationship_mod = self._get_relationship_modifier(relationship, action)
            score += relationship_mod * 0.3

        # 4. 风险修正
        risk_mod = self._get_risk_modifier(npc, action, context)
        score += risk_mod * npc.decision_weights.get('risk_tolerance', 0.5)

        # 5. 随机噪声
        noise = random.gauss(0, 0.1)
        score += noise

        return score

    def _calculate_goal_alignment(self, action: Action, goal: Goal) -> float:
        """计算行动与目标的对齐度"""
        alignment_table = {
            # (action_type, goal_type): alignment_score
            ('protect_player', 'player_safety'): 1.0,
            ('seek_teaching', 'cultivation_progress'): 0.8,
            ('confess', 'romantic_fulfillment'): 0.9,
            ('betray', 'self_preservation'): 0.7,
            # ... 更多映射
        }

        key = (action.type, goal.type)
        return alignment_table.get(key, 0.0)

    def _get_emotion_modifier(self, mood: str, action: Action) -> float:
        """情绪对行动的影响"""
        emotion_action_modifiers = {
            'happy': {'confess': 0.3, 'help': 0.2, 'attack': -0.2},
            'sad': {'withdraw': 0.3, 'confess': -0.2, 'help': -0.1},
            'angry': {'attack': 0.4, 'confront': 0.3, 'help': -0.3},
            'scared': {'flee': 0.5, 'hide': 0.4, 'confront': -0.4},
            'worried': {'check_on': 0.3, 'protect': 0.2},
        }

        if mood in emotion_action_modifiers:
            return emotion_action_modifiers[mood].get(action.type, 0.0)
        return 0.0

    def _get_relationship_modifier(self, relationship: Relationship,
                                    action: Action) -> float:
        """关系对行动的影响"""
        # 好感度影响帮助/伤害行动
        affection_factor = (relationship.affection - 50) / 100  # -0.5 to 0.5

        # 信任度影响分享/隐瞒行动
        trust_factor = (relationship.trust - 50) / 100

        action_relationship_weights = {
            'help': affection_factor * 0.5 + trust_factor * 0.3,
            'protect': affection_factor * 0.6,
            'confess': affection_factor * 0.4 + trust_factor * 0.4,
            'share_secret': trust_factor * 0.7,
            'betray': -affection_factor * 0.8 - trust_factor * 0.5,
        }

        return action_relationship_weights.get(action.type, 0.0)
```

### 4.2 嫉妒值状态机（苏云帆专用）

```python
class JealousyStateMachine:
    """嫉妒值状态机"""

    STATES = {
        'normal': (0, 30),
        'uneasy': (30, 50),
        'resentful': (50, 70),
        'dangerous': (70, 90),
        'breaking': (90, 100)
    }

    def __init__(self, npc_id: str):
        self.npc_id = npc_id
        self.jealousy = 0
        self.current_state = 'normal'

    def update(self, event_type: str, context: Context):
        """根据事件更新嫉妒值"""
        changes = {
            'player_praised_by_master': +10,
            'player_breakthrough': +15,
            'player_gets_rare_resource': +8,
            'player_shows_concern': -5,
            'player_asks_for_help': -10,
            'player_fails': -3,
            'player_struggles': -2,
        }

        delta = changes.get(event_type, 0)
        self.jealousy = max(0, min(100, self.jealousy + delta))

        # 更新状态
        new_state = self._determine_state()
        if new_state != self.current_state:
            self._on_state_change(self.current_state, new_state)
            self.current_state = new_state

    def _determine_state(self) -> str:
        for state, (low, high) in self.STATES.items():
            if low <= self.jealousy < high:
                return state
        return 'breaking'

    def _on_state_change(self, old_state: str, new_state: str):
        """状态变化时的行为触发"""
        transitions = {
            ('normal', 'uneasy'): {
                'unlock_events': ['suyunfan_complex_emotion_001'],
                'schedule_override': None
            },
            ('uneasy', 'resentful'): {
                'unlock_events': ['suyunfan_avoiding_player_001'],
                'schedule_override': 'avoid_player_schedule'
            },
            ('resentful', 'dangerous'): {
                'unlock_events': ['suyunfan_temptation_001'],
                'flag_set': 'suyunfan_vulnerable_to_manipulation'
            },
            ('dangerous', 'breaking'): {
                'unlock_events': ['suyunfan_crisis_001'],
                'flag_set': 'suyunfan_breaking_point'
            }
        }

        key = (old_state, new_state)
        if key in transitions:
            actions = transitions[key]
            # 执行相应动作
            self._execute_transition_actions(actions)

    def get_schedule_modifier(self) -> Optional[ScheduleOverride]:
        """根据当前状态返回日程覆盖"""
        if self.current_state == 'resentful':
            return ScheduleOverride(
                condition="always",
                effect="减少与玩家同处一地的时间"
            )
        elif self.current_state in ['dangerous', 'breaking']:
            return ScheduleOverride(
                condition="always",
                effect="完全回避玩家"
            )
        return None
```

### 4.3 关系衰减执行

```python
class RelationshipDecay:
    """关系衰减管理"""

    # 衰减率（每月）
    MONTHLY_DECAY_RATES = {
        'trust': 0.5,
        'affection': 0.3,
        'respect': 0.2,
        'fear': 1.0,  # 恐惧消退快
    }

    def apply_daily_decay(self, relationship: Relationship, days: int = 1):
        """应用每日衰减（按月衰减率折算）"""
        for dimension, monthly_rate in self.MONTHLY_DECAY_RATES.items():
            daily_rate = monthly_rate / 30
            current = getattr(relationship, dimension)

            # 只有超过50的部分才衰减（维持中性基准）
            if current > 50:
                decay = daily_rate * days
                new_value = max(50, current - decay)
                setattr(relationship, dimension, new_value)
            elif current < 50 and dimension == 'fear':
                # 恐惧低于50也向50回归
                recovery = daily_rate * days
                new_value = min(50, current + recovery)
                setattr(relationship, dimension, new_value)

    def apply_monthly_decay(self, relationship: Relationship):
        """每月大衰减（月结算时调用）"""
        for dimension, rate in self.MONTHLY_DECAY_RATES.items():
            current = getattr(relationship, dimension)
            if current > 50:
                new_value = max(50, current - rate)
                setattr(relationship, dimension, new_value)

    def update_interaction_counter(self, npc_memory: NPCMemory, had_interaction: bool):
        """更新互动计数"""
        if had_interaction:
            npc_memory.days_since_interaction = 0
        else:
            npc_memory.days_since_interaction += 1

            # 检查忽视阈值
            if npc_memory.days_since_interaction >= 30:
                self._trigger_neglect_event(npc_memory.owner_id)
```

### 4.4 长行动期间的关系衰减联动

```python
class LongActionRelationshipManager:
    """
    长行动期间的关系衰减管理

    核心问题：玩家闭关30天，与NPC的关系如何变化？
    """

    def simulate_retreat(self, player: Player, duration_days: int,
                          location: str = 'personal_cave'):
        """
        模拟闭关期间的关系变化

        示例：闭关30天
        - 每日衰减：trust -0.017/天, affection -0.01/天
        - 30天累计：trust -0.5, affection -0.3
        - 互动计数：days_since_interaction += 30
        """
        decay_manager = RelationshipDecay()

        for day in range(duration_days):
            # 1. 执行NPC的每日日程（他们的生活继续）
            self.npc_scheduler.execute_daily_schedules()

            # 2. 应用关系衰减
            for npc_id in self.character_manager.get_all_npc_ids():
                relationship = self.character_manager.get_relationship(npc_id)
                npc_memory = self.character_manager.get_npc(npc_id).memory

                # 每日衰减
                decay_manager.apply_daily_decay(relationship, days=1)

                # 更新互动计数（闭关=没互动）
                decay_manager.update_interaction_counter(npc_memory, had_interaction=False)

            # 3. 检查打断事件
            interrupt_event = self.event_scheduler.check_retreat_interrupt()
            if interrupt_event:
                return RetreatResult(
                    completed=False,
                    interrupted_at_day=day,
                    interrupt_event=interrupt_event,
                    total_decay=self._calculate_total_decay(day)
                )

            # 4. 检查NPC主动寻找
            seeking_npcs = self._check_npcs_seeking_player(day)
            if seeking_npcs:
                # 记录但不打断，除非紧急
                for npc_id in seeking_npcs:
                    self._record_missed_visit(npc_id, day)

        # 闭关完成
        return RetreatResult(
            completed=True,
            total_days=duration_days,
            total_decay=self._calculate_total_decay(duration_days)
        )

    def _calculate_total_decay(self, days: int) -> Dict[str, Dict[str, float]]:
        """计算指定天数的总衰减量"""
        decay = RelationshipDecay()
        result = {}

        for npc_id in self.character_manager.get_all_npc_ids():
            rel = self.character_manager.get_relationship(npc_id)
            npc_decay = {}

            for dimension, monthly_rate in decay.MONTHLY_DECAY_RATES.items():
                daily_rate = monthly_rate / 30
                current = getattr(rel, dimension)

                if current > 50:
                    total_decay = min(current - 50, daily_rate * days)
                    npc_decay[dimension] = -total_decay

            result[npc_id] = npc_decay

        return result

    def _check_npcs_seeking_player(self, retreat_day: int) -> List[str]:
        """检查是否有NPC主动寻找闭关中的玩家"""
        seeking = []

        for npc_id in ['atan', 'junior_linxueyao']:  # 会主动关心的NPC
            npc = self.character_manager.get_npc(npc_id)
            relationship = self.character_manager.get_relationship(npc_id)

            # 高好感度的NPC会在玩家消失N天后来找
            concern_threshold = 100 - relationship.affection  # 好感越高越早来
            concern_threshold = max(3, concern_threshold // 10)  # 最少3天

            if retreat_day >= concern_threshold:
                if random.random() < 0.3:  # 30%概率每天来找
                    seeking.append(npc_id)

        return seeking

    def _record_missed_visit(self, npc_id: str, day: int):
        """记录错过的探望"""
        npc = self.character_manager.get_npc(npc_id)
        npc.memory.add_memory(Memory(
            summary=f"去找{self.player.name}，但他在闭关",
            importance=3,
            emotional_impact={'disappointment': 0.2}
        ))


# ============ 使用示例 ============
"""
# 闭关30天的完整模拟

manager = LongActionRelationshipManager()
result = manager.simulate_retreat(player, duration_days=30)

if result.completed:
    print(f"闭关完成，总计衰减：")
    for npc_id, decay in result.total_decay.items():
        print(f"  {npc_id}: {decay}")
    # 输出示例：
    # atan: {'trust': -0.5, 'affection': -0.3, 'respect': -0.2}
    # senior_suyunfan: {'trust': -0.5, 'affection': -0.3}

else:
    print(f"闭关在第{result.interrupted_at_day}天被打断")
    print(f"打断事件：{result.interrupt_event.name}")
"""
```

---

## 第五章：AI系统规范

### 5.1 完整调用链

```python
class AIEngine:
    """AI引擎完整调用链"""

    def generate(self, task_type: TaskType, context: Context) -> GenerationResult:
        """
        完整调用链：
        1. 预算检查
        2. 缓存查询
        3. 上下文构建
        4. AI调用
        5. 输出验证
        6. 降级处理
        7. 成本记录
        """

        # 1. 预算检查
        provider = self.routing_table[task_type][0]
        estimated_tokens = self.token_estimator.estimate(context)

        budget_decision = self.budget_manager.request_budget(
            provider, estimated_tokens, task_type
        )

        if budget_decision.use_template:
            return self._generate_from_template(task_type, context)

        provider = budget_decision.provider

        # 2. 缓存查询
        cache_key = self._build_cache_key(task_type, context)
        cached = self.cache.get(cache_key)
        if cached:
            return GenerationResult(text=cached, from_cache=True)

        # 3. 上下文构建
        prompt = self._build_prompt(task_type, context)

        # 4. AI调用
        try:
            response = self._call_provider(provider, prompt)
        except AIError as e:
            # 调用失败，尝试降级
            return self._handle_failure(task_type, context, e)

        # 5. 输出验证
        validation = self._validate_output(response, context)

        if not validation.valid:
            if validation.action == 'reject':
                # 6. 降级处理
                return self._handle_validation_failure(task_type, context, validation)
            # warning级别，记录但继续

        # 7. 成本记录
        self.cost_monitor.record_usage(
            provider,
            prompt.input_tokens,
            response.output_tokens
        )

        # 缓存结果
        if self._is_cacheable(task_type, context):
            self.cache.set(cache_key, response.text)

        return GenerationResult(text=response.text, provider=provider)

    def _handle_validation_failure(self, task_type: TaskType, context: Context,
                                    validation: ValidationResult) -> GenerationResult:
        """处理验证失败"""
        # 记录失败
        self.logger.warning(f"AI验证失败: {validation.issues}")

        # 尝试重试一次
        if not context.is_retry:
            context.is_retry = True
            # 添加更严格的约束到prompt
            context.extra_constraints = validation.issues
            return self.generate(task_type, context)

        # 重试也失败，使用模板
        self.logger.error(f"AI重试失败，降级到模板")
        return self._generate_from_template(task_type, context)
```

### 5.2 验证规则详细定义

```python
class OutputValidator:
    """输出验证器"""

    def validate(self, output: str, context: Context,
                 npc_context: NPCContext = None) -> ValidationResult:
        """完整验证"""
        issues = []

        # 1. 地点一致性检查
        issues.extend(self._check_location(output, context))

        # 2. 行动一致性检查
        if npc_context:
            issues.extend(self._check_activity(output, npc_context))

        # 3. 禁忌检查
        if npc_context:
            issues.extend(self._check_taboos(output, npc_context))

        # 4. 秘密泄露检查
        if npc_context:
            issues.extend(self._check_secret_leak(output, npc_context))

        # 5. 时间一致性检查
        issues.extend(self._check_time_consistency(output, context))

        # 6. NPC存在性检查
        issues.extend(self._check_npc_existence(output, context))

        return self._compile_result(issues)

    def _check_location(self, output: str, context: Context) -> List[Issue]:
        """检查地点描述是否与当前位置一致"""
        issues = []
        current_loc = context.scene.location_name

        # 提取输出中的地点描述
        mentioned_places = self._extract_place_mentions(output)

        for place in mentioned_places:
            # 检查是否是当前地点或其子节点
            if not self._is_valid_location_reference(place, current_loc):
                issues.append(Issue(
                    type='location_mismatch',
                    severity='critical',
                    detail=f"提到了不在当前场景的地点: {place}"
                ))

        return issues

    def _check_activity(self, output: str, npc_context: NPCContext) -> List[Issue]:
        """检查NPC行动描述是否与日程一致"""
        issues = []
        expected_activity = npc_context.current_activity

        # 获取该行动的允许动词
        allowed_verbs = self._get_allowed_verbs(expected_activity)

        # 提取输出中的动作描写
        described_actions = self._extract_action_descriptions(output)

        for action in described_actions:
            if not self._action_matches(action, allowed_verbs):
                issues.append(Issue(
                    type='activity_mismatch',
                    severity='critical',
                    detail=f"NPC应该在{expected_activity}，但描写为{action}"
                ))

        return issues

    def _check_taboos(self, output: str, npc_context: NPCContext) -> List[Issue]:
        """检查是否违反禁忌"""
        issues = []

        for taboo in npc_context.taboos:
            if taboo in output:
                issues.append(Issue(
                    type='taboo_violation',
                    severity='warning',
                    detail=f"包含禁忌内容: {taboo}"
                ))

        return issues

    def _check_secret_leak(self, output: str, npc_context: NPCContext) -> List[Issue]:
        """检查是否泄露未解锁的秘密"""
        issues = []

        for secret in npc_context.secrets_unknown_to_player:
            # 检查是否包含秘密关键词
            if self._contains_secret_keywords(output, secret):
                issues.append(Issue(
                    type='secret_leak',
                    severity='critical',
                    detail=f"泄露了未解锁的秘密"
                ))

        return issues

    def _get_allowed_verbs(self, activity_id: str) -> List[str]:
        """获取行动允许的动词"""
        activity_verbs = {
            'prepare_meal': ['切', '洗', '煮', '炒', '准备', '端', '盛'],
            'wash_clothes': ['洗', '搓', '晾', '晒', '拧'],
            'meditate': ['盘坐', '闭目', '吐纳', '运气', '静坐'],
            'rest': ['躺', '靠', '休息', '闭目', '发呆'],
            'wait_for_someone': ['站', '坐', '等', '望', '看'],
        }
        return activity_verbs.get(activity_id, [])
```

### 5.3 上下文构建时的字段过滤

```python
class ContextBuilder:
    """上下文构建器"""

    def build_npc_context(self, npc_id: str, include_secrets: bool = False) -> NPCContext:
        """构建NPC上下文，自动过滤敏感信息"""
        npc = self.characters.get_npc(npc_id)
        relationship = self.characters.get_relationship(npc_id)

        # 基础信息
        context = NPCContext(
            name=npc.display_name,  # 使用显示名，不是ID
            personality=npc.personality.surface,  # 只给表面性格
            speaking_style=npc.speaking_style,

            # 当前状态
            current_activity=self._get_activity_display(npc.current_activity),
            current_mood=npc.current_mood,
            current_location=self._get_location_display(npc.current_location),

            # 关系（不给具体数值）
            relationship_state=relationship.get_state_label(),
            relationship_description=relationship.get_natural_description(),
        )

        # 相关记忆（压缩后）
        context.relevant_memories = self._compress_memories(
            npc.memory.get_relevant(self.current_scene, limit=5)
        )

        # 禁忌列表
        context.taboos = npc.taboos.copy()

        # 未知秘密转为禁忌（关键！）
        unknown_secrets = npc.get_unknown_secrets()
        for secret in unknown_secrets:
            context.taboos.extend(secret.forbidden_keywords)

        # 不传给AI的字段
        # - npc.id（用display_name代替）
        # - relationship具体数值
        # - 未解锁的secrets详细内容
        # - decision_weights
        # - hidden personality

        return context

    def _get_activity_display(self, activity_id: str) -> str:
        """将action_id转换为显示文本"""
        activity_displays = {
            'prepare_meal': '正在准备饭菜',
            'wash_clothes': '正在洗衣服',
            'meditate': '正在打坐修炼',
            'rest': '正在休息',
            'wait_for_someone': '似乎在等什么人',
        }
        return activity_displays.get(activity_id, activity_id)
```

### 5.4 环境元素白名单系统

```python
class EnvironmentWhitelist:
    """
    环境元素白名单 - 防止AI杜撰不存在的元素

    核心原则：AI只能使用白名单中的元素，不能自己编造
    """

    def __init__(self, world_manager, character_manager, story_manager):
        self.world = world_manager
        self.characters = character_manager
        self.story = story_manager

    def build_whitelist(self, scene: Scene) -> EnvironmentElements:
        """
        构建当前场景的可用元素白名单
        """
        return EnvironmentElements(
            # 可用地点
            available_locations=self._get_available_locations(scene),

            # 可提及的NPC
            available_npcs=self._get_available_npcs(scene),

            # 可用物品
            available_items=self._get_available_items(scene),

            # 可用技能/功法
            available_skills=self._get_available_skills(),

            # 可用天气/环境描述
            available_weather=self._get_available_weather(),

            # 禁止元素（明确不能出现）
            forbidden_elements=self._get_forbidden_elements(scene),
        )

    def _get_available_locations(self, scene: Scene) -> List[str]:
        """获取可提及的地点"""
        current = scene.location_id
        available = []

        # 1. 当前地点
        available.append(self.world.get_location_display(current))

        # 2. 当前地点的子节点
        for sub in self.world.get_sub_locations(current):
            available.append(sub.display_name)

        # 3. 相邻地点（可以"望向远方"提及）
        for neighbor in self.world.get_neighbors(current):
            available.append(f"远处的{neighbor.display_name}")

        # 4. 玩家已知的地点（可以在对话中提及）
        for known_loc in self.story.player_known_locations:
            if known_loc not in available:
                available.append(known_loc)

        return available

    def _get_available_npcs(self, scene: Scene) -> List[NPCReference]:
        """获取可提及的NPC"""
        available = []

        # 1. 当前场景中的NPC（可以直接互动）
        for npc_id in scene.npcs_present:
            npc = self.characters.get_npc(npc_id)
            available.append(NPCReference(
                name=npc.display_name,
                aliases=npc.aliases,
                can_interact=True,
                can_mention=True
            ))

        # 2. 玩家已知的NPC（可以在对话中提及，但不能凭空出现）
        for npc_id in self.story.player_known_npcs:
            if npc_id not in scene.npcs_present:
                npc = self.characters.get_npc(npc_id)
                available.append(NPCReference(
                    name=npc.display_name,
                    aliases=npc.aliases,
                    can_interact=False,
                    can_mention=True
                ))

        return available

    def _get_available_items(self, scene: Scene) -> List[str]:
        """获取可用物品"""
        items = []

        # 1. 玩家携带的物品
        for item in self.world.player.inventory:
            items.append(item.display_name)

        # 2. 场景中的物品
        for item in scene.scene_items:
            items.append(item.display_name)

        # 3. NPC可能给予的物品（根据事件）
        if scene.active_event:
            for reward in scene.active_event.possible_rewards:
                items.append(reward.display_name)

        return items

    def _get_available_skills(self) -> List[str]:
        """获取可提及的功法/技能"""
        skills = []

        # 1. 玩家已学
        for skill in self.world.player.skills:
            skills.append(skill.display_name)

        # 2. 玩家已知（听说过但未学）
        for skill_id in self.story.player_known_skills:
            skill = self.world.get_skill(skill_id)
            skills.append(skill.display_name)

        # 3. 通用功法（世界观常识）
        skills.extend([
            '基础吐纳法', '基础剑术', '轻身术',
            '青云剑诀',  # 本门功法
        ])

        return skills

    def _get_available_weather(self) -> List[str]:
        """获取当前可用的天气描述"""
        current_weather = self.world.current_weather
        time_slot = self.world.current_time_slot

        weather_descriptions = {
            'sunny': ['阳光明媚', '晴空万里', '日光和煦'],
            'cloudy': ['云层密布', '天色阴沉', '乌云低垂'],
            'rainy': ['细雨绵绵', '大雨倾盆', '雨声淅沥'],
            'snowy': ['白雪皑皑', '飘雪纷飞', '寒风凛冽'],
            'foggy': ['云雾缭绕', '雾气弥漫', '能见度低'],
        }

        time_descriptions = {
            'morning': ['晨光熹微', '朝霞满天', '露水未干'],
            'afternoon': ['日正当空', '暑气蒸腾'],
            'evening': ['夕阳西下', '暮色四合', '晚霞如火'],
            'night': ['星月交辉', '夜色如墨', '万籁俱寂'],
        }

        available = weather_descriptions.get(current_weather, [])
        available.extend(time_descriptions.get(time_slot, []))

        return available

    def _get_forbidden_elements(self, scene: Scene) -> ForbiddenElements:
        """获取明确禁止的元素"""
        forbidden = ForbiddenElements(
            # 不能出现的地点（尚未解锁/不存在）
            locations=[],

            # 不能出现的NPC（玩家不认识/已死亡）
            npcs=[],

            # 不能出现的物品（不存在于当前场景）
            items=[],

            # 不能提及的信息（未解锁的秘密）
            secrets=[],

            # 不能使用的称呼（关系未到）
            appellations=[],
        )

        # 1. 未解锁的地点
        all_locations = self.world.get_all_location_ids()
        known_locations = set(self.story.player_known_locations)
        forbidden.locations = [
            self.world.get_location_display(loc)
            for loc in all_locations if loc not in known_locations
        ]

        # 2. 未知的NPC
        all_npcs = self.characters.get_all_npc_ids()
        known_npcs = set(self.story.player_known_npcs)
        for npc_id in all_npcs:
            if npc_id not in known_npcs:
                npc = self.characters.get_npc(npc_id)
                forbidden.npcs.append(npc.display_name)
                forbidden.npcs.extend(npc.aliases)

        # 3. 未解锁的秘密
        for secret in self.story.get_all_secrets():
            if not secret.is_unlocked:
                forbidden.secrets.extend(secret.keywords)

        # 4. 关系未到的称呼
        for npc_id in scene.npcs_present:
            relationship = self.characters.get_relationship(npc_id)
            npc = self.characters.get_npc(npc_id)

            for appellation in npc.intimate_appellations:
                if relationship.affection < appellation.required_affection:
                    forbidden.appellations.append(appellation.text)

        return forbidden


# ============ 白名单使用示例 ============
"""
# 在AI调用前构建白名单

whitelist = environment_whitelist.build_whitelist(current_scene)

# 添加到prompt中
prompt = f'''
你正在为一个修仙游戏生成对话。

【可用元素】
地点：{', '.join(whitelist.available_locations)}
人物：{', '.join([n.name for n in whitelist.available_npcs if n.can_interact])}
可提及的人物：{', '.join([n.name for n in whitelist.available_npcs if n.can_mention])}
环境描述：{', '.join(whitelist.available_weather)}

【禁止元素 - 绝对不能出现】
地点：{', '.join(whitelist.forbidden_elements.locations[:10])}...
人物：{', '.join(whitelist.forbidden_elements.npcs[:10])}...
信息：{', '.join(whitelist.forbidden_elements.secrets[:10])}...

如果你需要提及白名单之外的元素，请用"某处"、"某人"等模糊称呼代替。
'''

# 验证时也使用白名单
validator.validate_against_whitelist(ai_output, whitelist)
"""
```

---

## 第六章：持久化规范

### 6.1 时间相关字段存储

```yaml
# 过期/冷却时间存储规范
time_storage:
  # 推荐：存储绝对时间
  format: absolute_game_time

  example:
    event_cooldown:
      event_id: "atan_daily_greeting_001"
      cooldown_until:
        year: 1
        month: 3
        day: 16
        slot: "morning"

    event_expiry:
      event_id: "sword_tomb_invitation"
      expires_at:
        year: 3
        month: 6
        day: 1
        slot: null  # null表示当日结束

  # 加载时的处理
  on_load: |
    current = get_current_game_time()
    for event in pending_events:
        if event.expires_at and current > event.expires_at:
            mark_as_expired(event)
```

### 6.2 标记一致性校验

```python
class FlagResolver:
    """标记解析器 - 确保一致性"""

    def __init__(self, story_manager):
        self.story = story_manager
        self.computed_flags = {}

    def resolve_all(self):
        """重建所有组合标记"""
        self._resolve_confession_available()
        self._resolve_betrayal_possible()
        self._resolve_phase_transitions()

    def _resolve_confession_available(self):
        """计算"可以告白"标记"""
        atan_rel = self.characters.get_relationship('atan')
        atan_mem = self.characters.get_npc('atan').memory

        can_confess = (
            atan_rel.affection >= 80 and
            atan_rel.trust >= 70 and
            len(atan_mem.get_shared_crisis_memories()) >= 3 and
            not self.story.has_flag('atan_confession_rejected')
        )

        self.computed_flags['atan_confession_available'] = can_confess

    def validate_on_load(self, save_data: dict) -> List[str]:
        """加载时验证存档一致性"""
        errors = []

        # 检查事件ID存在性
        for event_record in save_data['events']['triggered_events']:
            if event_record['id'] not in self.event_registry:
                errors.append(f"未知事件ID: {event_record['id']}")

        # 检查地点ID存在性
        player_loc = save_data['player']['location']['current']
        if player_loc not in self.location_registry:
            errors.append(f"未知地点ID: {player_loc}")

        # 检查NPC ID存在性
        for npc_file in save_data.get('npc_files', []):
            if npc_file['id'] not in self.npc_registry:
                errors.append(f"未知NPC ID: {npc_file['id']}")

        return errors
```

---

## 第七章：经济系统规范

### 7.1 自动扣款与负债

```python
class EconomyManager:
    """经济管理器"""

    def monthly_settlement(self, player: Player):
        """月结算"""
        # 1. 计算收入
        income = self._calculate_monthly_income(player)

        # 2. 计算支出
        expenses = self._calculate_monthly_expenses(player)

        # 3. 结算
        balance = income - expenses

        if balance >= 0:
            player.spirit_stones.low += balance
        else:
            # 负债处理
            self._handle_debt(player, abs(balance))

    def _calculate_monthly_expenses(self, player: Player) -> int:
        """计算月支出"""
        expenses = 0

        # 基础修炼消耗
        realm_costs = {
            'qi_refining': 30,
            'foundation_building': 100,
            'golden_core': 300,
        }
        expenses += realm_costs.get(player.realm, 30)

        # 食宿（如果不是门派提供）
        if not player.has_sect_housing:
            expenses += 10

        return expenses

    def _handle_debt(self, player: Player, amount: int):
        """处理负债"""
        # 先尝试从中品灵石换
        mid_needed = (amount + 99) // 100
        if player.spirit_stones.mid >= mid_needed:
            player.spirit_stones.mid -= mid_needed
            player.spirit_stones.low += mid_needed * 100 - amount
            return

        # 真的没钱了
        player.debt += amount
        player.debt_months += 1

        # 触发负债事件
        if player.debt_months >= 3:
            self.event_bus.emit('player_debt_crisis', {
                'debt': player.debt,
                'months': player.debt_months
            })

            # 声望下降
            player.sect_reputation -= 10

        # 第一次负债也要提醒
        elif player.debt_months == 1:
            self.event_bus.emit('player_debt_warning', {
                'debt': player.debt
            })
```

### 7.2 价格波动系统

```python
class PriceManager:
    """
    价格管理器 - 周期刷新 + 事件驱动

    价格公式：
    current_price = base_price × seasonal_mod × event_mod × supply_demand_mod × random_noise
    """

    BASE_PRICES = {
        # 丹药类
        'recovery_pill': 15,
        'qi_gathering_pill': 50,
        'foundation_building_pill': 50000,

        # 材料类
        'spirit_herb': 5,
        'beast_core_low': 20,
        'beast_core_mid': 200,

        # 装备类
        'basic_sword': 100,
        'spirit_robe': 300,
    }

    # 物品分类
    ITEM_CATEGORIES = {
        'recovery_pill': 'healing',
        'qi_gathering_pill': 'cultivation',
        'foundation_building_pill': 'cultivation',
        'spirit_herb': 'material',
        'beast_core_low': 'material',
        'beast_core_mid': 'material',
        'basic_sword': 'equipment',
        'spirit_robe': 'equipment',
    }

    def __init__(self):
        self.current_prices = self.BASE_PRICES.copy()
        self.supply_demand = {item: 1.0 for item in self.BASE_PRICES}
        self.last_refresh_month = 0

    # ========== 周期刷新 ==========

    def monthly_refresh(self, current_month: int):
        """
        月度价格刷新 - 每月1日执行

        规则：
        1. 基础随机波动 ±10%
        2. 季节性调整
        3. 供需调整（基于上月交易量）
        """
        if current_month == self.last_refresh_month:
            return

        self.last_refresh_month = current_month
        season = self._get_season(current_month)

        for item, base_price in self.BASE_PRICES.items():
            # 1. 季节性修正
            seasonal_mod = self._get_seasonal_modifier(item, season)

            # 2. 供需修正（缓慢回归1.0）
            self.supply_demand[item] = 0.9 * self.supply_demand[item] + 0.1 * 1.0
            supply_mod = self.supply_demand[item]

            # 3. 随机波动 ±10%
            random_mod = random.uniform(0.9, 1.1)

            # 4. 计算最终价格
            final_price = base_price * seasonal_mod * supply_mod * random_mod
            self.current_prices[item] = max(1, int(final_price))

    def _get_season(self, month: int) -> str:
        """月份→季节"""
        if month in [1, 2, 3]:
            return 'spring'
        elif month in [4, 5, 6]:
            return 'summer'
        elif month in [7, 8, 9]:
            return 'autumn'
        else:
            return 'winter'

    def _get_seasonal_modifier(self, item: str, season: str) -> float:
        """季节性价格修正"""
        seasonal_effects = {
            # 春季：灵草丰收，材料降价
            'spring': {'material': 0.85, 'healing': 0.9},

            # 夏季：兽潮活跃，兽核降价，疗伤品涨价
            'summer': {'beast_core': 0.8, 'healing': 1.2},

            # 秋季：丰收季，全品类稳定
            'autumn': {},

            # 冬季：物资紧缺，全品类涨价
            'winter': {'material': 1.15, 'healing': 1.1, 'cultivation': 1.1},
        }

        category = self.ITEM_CATEGORIES.get(item, 'misc')
        effects = seasonal_effects.get(season, {})

        return effects.get(category, 1.0)

    # ========== 事件驱动 ==========

    def apply_event_modifier(self, world_state: WorldState):
        """
        事件驱动的价格修正

        特点：
        - 立即生效
        - 叠加在周期价格之上
        - 事件结束后自动移除
        """
        event_modifiers = {}

        # 兽潮影响
        if world_state.has_event('beast_tide'):
            event_modifiers['beast_core_low'] = 0.7   # 供应增加
            event_modifiers['beast_core_mid'] = 0.7
            event_modifiers['recovery_pill'] = 1.3   # 需求增加

        # 秘境开启影响
        if world_state.has_event('secret_realm_opening'):
            event_modifiers['recovery_pill'] = 1.2
            event_modifiers['basic_sword'] = 1.3
            event_modifiers['spirit_robe'] = 1.3

        # 门派大比影响
        if world_state.has_event('sect_competition'):
            event_modifiers['qi_gathering_pill'] = 1.25
            event_modifiers['recovery_pill'] = 1.15

        # 战乱影响（全面涨价）
        if world_state.has_event('faction_war'):
            for item in self.current_prices:
                if item not in event_modifiers:
                    event_modifiers[item] = 1.2
                else:
                    event_modifiers[item] *= 1.2

        # 应用事件修正
        for item, modifier in event_modifiers.items():
            if item in self.current_prices:
                self.current_prices[item] = int(self.current_prices[item] * modifier)

    # ========== 供需反馈 ==========

    def record_transaction(self, item: str, quantity: int, is_buy: bool):
        """
        记录交易，影响供需

        大量购买 → 需求上升 → 价格上涨
        大量出售 → 供应上升 → 价格下跌
        """
        if item not in self.supply_demand:
            return

        # 交易量影响供需
        impact = quantity * 0.01  # 每件商品影响1%

        if is_buy:
            # 购买增加需求，价格上涨
            self.supply_demand[item] = min(1.5, self.supply_demand[item] + impact)
        else:
            # 出售增加供应，价格下跌
            self.supply_demand[item] = max(0.5, self.supply_demand[item] - impact)

    # ========== 价格上下限 ==========

    def _clamp_price(self, item: str, price: int) -> int:
        """价格上下限（防止极端波动）"""
        base = self.BASE_PRICES.get(item, price)
        min_price = max(1, int(base * 0.5))   # 最低50%
        max_price = int(base * 2.0)           # 最高200%
        return max(min_price, min(max_price, price))


# ============ 价格系统使用示例 ============
"""
# 初始化
price_manager = PriceManager()

# 月度刷新（每月1日日结算时调用）
def on_month_start(current_month: int):
    price_manager.monthly_refresh(current_month)

# 事件触发时更新（在事件触发后调用）
def on_event_triggered(event_id: str):
    price_manager.apply_event_modifier(world_state)

# 玩家交易时记录
def on_player_buy(item: str, quantity: int):
    price_manager.record_transaction(item, quantity, is_buy=True)

def on_player_sell(item: str, quantity: int):
    price_manager.record_transaction(item, quantity, is_buy=False)

# 获取当前价格
current_price = price_manager.current_prices['recovery_pill']
"""
```

---

## 第八章：记忆压缩规范

### 8.1 压缩触发时机

```yaml
memory_compression:
  triggers:
    periodic:
      frequency: "每30游戏日"
      condition: "always"

    on_event:
      - "长行动结束"
      - "重大剧情节点完成"
      - "NPC关系阶段跨越"

    threshold:
      condition: "memory_count > 50"
      action: "立即压缩"
```

### 8.2 压缩算法

```python
class MemoryCompressor:
    """记忆压缩器"""

    MAX_RECENT_MEMORIES = 50
    COMPRESS_THRESHOLD_DAYS = 100
    MERGE_SIMILARITY_THRESHOLD = 0.7

    def compress(self, npc_memory: NPCMemory, current_date: GameTime):
        """执行压缩"""
        # 1. 按时间分组
        old_memories = []
        recent_memories = []

        for memory in npc_memory.recent_memories:
            age_days = (current_date - memory.timestamp).total_days()
            if age_days > self.COMPRESS_THRESHOLD_DAYS:
                old_memories.append(memory)
            else:
                recent_memories.append(memory)

        # 2. 压缩旧记忆
        compressed = self._compress_old_memories(old_memories)

        # 3. 合并相似记忆
        merged_recent = self._merge_similar(recent_memories)

        # 4. 裁剪到上限
        if len(merged_recent) > self.MAX_RECENT_MEMORIES:
            merged_recent = self._prune_by_importance(
                merged_recent,
                self.MAX_RECENT_MEMORIES
            )

        # 5. 更新
        npc_memory.compressed_memories.extend(compressed)
        npc_memory.recent_memories = merged_recent

    def _compress_old_memories(self, memories: List[Memory]) -> List[CompressedMemory]:
        """压缩旧记忆"""
        # 按月份分组
        by_month = defaultdict(list)
        for m in memories:
            key = (m.timestamp.year, m.timestamp.month)
            by_month[key].append(m)

        compressed = []
        for (year, month), month_memories in by_month.items():
            # 保留最重要的事件
            important = [m for m in month_memories if m.importance >= 7]

            # 其他合并为摘要
            others = [m for m in month_memories if m.importance < 7]
            if others:
                summary = self._generate_period_summary(others)
                compressed.append(CompressedMemory(
                    period=f"第{year}年{month}月",
                    summary=summary,
                    event_count=len(others)
                ))

            # 重要事件单独保留
            for m in important:
                compressed.append(CompressedMemory(
                    period=f"第{year}年{month}月",
                    summary=m.summary,
                    original_importance=m.importance
                ))

        return compressed

    def _merge_similar(self, memories: List[Memory]) -> List[Memory]:
        """合并相似记忆"""
        merged = []
        used = set()

        for i, m1 in enumerate(memories):
            if i in used:
                continue

            similar_group = [m1]
            for j, m2 in enumerate(memories[i+1:], i+1):
                if j in used:
                    continue
                if self._calculate_similarity(m1, m2) > self.MERGE_SIMILARITY_THRESHOLD:
                    similar_group.append(m2)
                    used.add(j)

            if len(similar_group) > 1:
                # 合并
                merged.append(self._merge_group(similar_group))
            else:
                merged.append(m1)

        return merged

    def _merge_group(self, memories: List[Memory]) -> Memory:
        """合并一组相似记忆"""
        # 取最高重要性
        max_importance = max(m.importance for m in memories)

        # 取最近时间戳
        latest = max(memories, key=lambda m: m.timestamp)

        # 生成合并摘要
        summary = f"（{len(memories)}次类似经历）{memories[0].summary}"

        return Memory(
            id=f"merged_{memories[0].id}",
            summary=summary,
            importance=max_importance,
            timestamp=latest.timestamp,
            emotional_impact=memories[0].emotional_impact,
            merged_count=len(memories)
        )
```

---

## 第九章：灵气衰退系统规范

### 9.1 灵气衰退等级表

```yaml
spirit_decline_levels:
  # 灵气衰退是修仙世界的大背景，影响所有修炼相关系统
  # 衰退等级 0-5，游戏初始为 level 1（轻微衰退）

  level_0:
    name: 灵气鼎盛
    description: 上古时期的灵气浓度，现已不存在
    occurrence: "仅存在于传说和特殊秘境中"

    effects:
      cultivation_efficiency: 1.5      # 修炼效率 150%
      breakthrough_difficulty: 0.7     # 突破难度 70%
      tribulation_intensity: 0.8       # 渡劫强度 80%
      resource_respawn_rate: 2.0       # 资源刷新速率 200%
      spirit_beast_spawn: 1.5          # 灵兽出现率 150%

  level_1:
    name: 轻微衰退
    description: 游戏初始状态，灵气略有稀薄
    occurrence: "当前时代的基准状态"

    effects:
      cultivation_efficiency: 1.0      # 基准
      breakthrough_difficulty: 1.0     # 基准
      tribulation_intensity: 1.0       # 基准
      resource_respawn_rate: 1.0       # 基准
      spirit_beast_spawn: 1.0          # 基准

  level_2:
    name: 中度衰退
    description: 灵气明显稀薄，低阶修士受影响较大
    trigger: "游戏进行约 3-5 年后可能触发"

    effects:
      cultivation_efficiency: 0.85
      breakthrough_difficulty: 1.15
      tribulation_intensity: 1.1
      resource_respawn_rate: 0.8
      spirit_beast_spawn: 0.85

    narrative_effects:
      - "门派月例灵石减少"
      - "低阶弟子进境变慢"
      - "部分灵草绝迹"

  level_3:
    name: 严重衰退
    description: 灵气大幅衰减，开始影响金丹期以下的所有修士
    trigger: "通常与重大剧情事件关联"

    effects:
      cultivation_efficiency: 0.7
      breakthrough_difficulty: 1.3
      tribulation_intensity: 1.2
      resource_respawn_rate: 0.6
      spirit_beast_spawn: 0.7

    narrative_effects:
      - "筑基变得困难，失败率上升"
      - "门派开始争夺资源"
      - "散修生存艰难"
      - "部分秘境入口关闭"

  level_4:
    name: 末法初现
    description: 接近末法时代，修仙已变得极为困难
    trigger: "剧情后期或特定路线"

    effects:
      cultivation_efficiency: 0.5
      breakthrough_difficulty: 1.5
      tribulation_intensity: 1.4
      resource_respawn_rate: 0.4
      spirit_beast_spawn: 0.5

    narrative_effects:
      - "元婴期以下修士进境几乎停滞"
      - "大量门派衰落或合并"
      - "修仙者开始寻找上古遗迹"
      - "部分秘法失传"

  level_5:
    name: 末法降临
    description: 极端情况，灵气几乎枯竭
    trigger: "Bad Ending 路线或特殊事件"

    effects:
      cultivation_efficiency: 0.3
      breakthrough_difficulty: 2.0
      tribulation_intensity: 1.8
      resource_respawn_rate: 0.2
      spirit_beast_spawn: 0.3

    narrative_effects:
      - "修仙文明面临崩溃"
      - "高阶修士开始沉睡保存修为"
      - "凡人数量激增"
      - "大能开始寻找逆转之法"
```

### 9.2 灵气衰退的游戏影响

```python
class SpiritDeclineManager:
    """
    灵气衰退管理器

    灵气衰退影响：
    1. 修炼效率
    2. 突破成功率
    3. 渡劫难度
    4. 资源刷新
    5. 灵兽出现
    6. 物价
    """

    DECLINE_LEVELS = {
        0: {'cultivation': 1.5, 'breakthrough': 0.7, 'tribulation': 0.8, 'resource': 2.0, 'beast': 1.5},
        1: {'cultivation': 1.0, 'breakthrough': 1.0, 'tribulation': 1.0, 'resource': 1.0, 'beast': 1.0},
        2: {'cultivation': 0.85, 'breakthrough': 1.15, 'tribulation': 1.1, 'resource': 0.8, 'beast': 0.85},
        3: {'cultivation': 0.7, 'breakthrough': 1.3, 'tribulation': 1.2, 'resource': 0.6, 'beast': 0.7},
        4: {'cultivation': 0.5, 'breakthrough': 1.5, 'tribulation': 1.4, 'resource': 0.4, 'beast': 0.5},
        5: {'cultivation': 0.3, 'breakthrough': 2.0, 'tribulation': 1.8, 'resource': 0.2, 'beast': 0.3},
    }

    def __init__(self, initial_level: int = 1):
        self.current_level = initial_level
        self.modifiers = self.DECLINE_LEVELS[initial_level]

    def get_cultivation_efficiency(self, location_spirit_density: float = 1.0) -> float:
        """
        计算实际修炼效率

        公式: base_efficiency × decline_mod × location_density
        """
        return self.modifiers['cultivation'] * location_spirit_density

    def get_breakthrough_chance(self, base_chance: float, player_preparation: float = 1.0) -> float:
        """
        计算突破成功率

        公式: base_chance / difficulty_mod × preparation
        """
        difficulty = self.modifiers['breakthrough']
        return min(0.95, base_chance / difficulty * player_preparation)

    def get_tribulation_power(self, player_realm: str) -> float:
        """
        计算渡劫强度

        高等级衰退 = 更难的天劫
        """
        realm_base = {
            'foundation_building': 1.0,
            'golden_core': 1.5,
            'nascent_soul': 2.0,
        }

        base = realm_base.get(player_realm, 1.0)
        return base * self.modifiers['tribulation']

    def get_resource_respawn_time(self, base_days: int) -> int:
        """
        计算资源刷新时间

        衰退等级越高，刷新越慢
        """
        rate = self.modifiers['resource']
        if rate <= 0:
            return base_days * 10  # 极端情况
        return int(base_days / rate)

    def check_spirit_beast_spawn(self, base_probability: float) -> bool:
        """
        检查灵兽出现

        衰退等级越高，灵兽越少
        """
        adjusted_prob = base_probability * self.modifiers['beast']
        return random.random() < adjusted_prob

    # ========== 衰退等级变化 ==========

    def increase_decline(self, reason: str = "natural"):
        """灵气进一步衰退"""
        if self.current_level < 5:
            self.current_level += 1
            self.modifiers = self.DECLINE_LEVELS[self.current_level]
            self._trigger_decline_event(reason)

    def decrease_decline(self, reason: str = "player_action"):
        """灵气恢复（罕见）"""
        if self.current_level > 0:
            self.current_level -= 1
            self.modifiers = self.DECLINE_LEVELS[self.current_level]
            self._trigger_recovery_event(reason)

    def _trigger_decline_event(self, reason: str):
        """触发衰退相关事件"""
        events_by_level = {
            2: 'spirit_decline_noticed',      # NPC开始议论
            3: 'spirit_decline_crisis',       # 门派会议
            4: 'spirit_decline_desperate',    # 寻找解决方案
            5: 'spirit_decline_apocalypse',   # 末日场景
        }

        event_id = events_by_level.get(self.current_level)
        if event_id:
            self.event_bus.emit('schedule_event', {'event_id': event_id})

    def _trigger_recovery_event(self, reason: str):
        """触发灵气恢复事件（稀有成就）"""
        self.event_bus.emit('achievement_unlocked', {
            'achievement': 'spirit_recovery',
            'reason': reason
        })


# ============ 衰退系统与其他系统的整合 ============

class CultivationSystem:
    """修炼系统 - 受灵气衰退影响"""

    def calculate_cultivation_gain(self, player, duration_hours: int) -> int:
        """计算修炼获得的经验"""
        # 基础经验
        base_exp = duration_hours * 10

        # 功法加成
        technique_mod = player.technique.efficiency

        # 地点灵气密度
        location = world.get_location(player.location)
        spirit_density = location.spirit_density

        # 灵气衰退影响
        decline_mod = spirit_decline_manager.get_cultivation_efficiency(spirit_density)

        # 最终经验
        final_exp = int(base_exp * technique_mod * decline_mod)

        return max(1, final_exp)


class BreakthroughSystem:
    """突破系统 - 受灵气衰退影响"""

    def attempt_breakthrough(self, player) -> BreakthroughResult:
        """尝试突破"""
        # 基础成功率
        base_chance = self._get_base_chance(player.realm)

        # 准备度（资源/状态/心境）
        preparation = self._calculate_preparation(player)

        # 应用灵气衰退
        final_chance = spirit_decline_manager.get_breakthrough_chance(
            base_chance, preparation
        )

        # 掷骰
        roll = random.random()

        if roll < final_chance:
            return BreakthroughResult(success=True)
        elif roll < final_chance + 0.1:
            return BreakthroughResult(success=False, backlash='minor')
        else:
            return BreakthroughResult(success=False, backlash='major')
```

### 9.3 灵气衰退的剧情整合

```yaml
spirit_decline_story_hooks:
  # 灵气衰退作为世界观背景，与主线剧情深度整合

  level_2_hooks:
    discovery_event:
      trigger: "玩家修炼时感到异常"
      dialogue: "师父，弟子最近修炼总觉得灵气不如从前充沛..."
      unlock_flag: "spirit_decline_aware"

    sect_discussion:
      trigger: "flag: spirit_decline_aware AND 月会"
      content: "各位，近来灵气有衰退之象..."

  level_3_hooks:
    resource_conflict:
      trigger: "spirit_decline_level >= 3"
      events:
        - "sect_resource_dispute"     # 门派内部资源争夺
        - "inter_sect_tension"        # 门派间关系紧张

    atan_concern:
      trigger: "spirit_decline_level >= 3 AND relationship.atan.affection >= 60"
      dialogue: "公子，我观天象，似有大变将至..."

  level_4_hooks:
    ancient_secret:
      trigger: "spirit_decline_level >= 4 AND story_progress >= 60%"
      unlock: "仙途真相线索"
      hint: "上古大能预见了这一切..."

    desperate_measures:
      trigger: "spirit_decline_level >= 4"
      events:
        - "sect_merger_proposal"      # 门派合并提议
        - "forbidden_technique_temptation"  # 禁术诱惑

  player_agency:
    # 玩家可以影响灵气衰退（后期）
    slow_decline:
      condition: "完成特定任务链"
      effect: "衰退速度减缓50%"

    reverse_decline:
      condition: "找到上古遗物 + 特定路线"
      effect: "可以降低1级衰退"

    transcend_decline:
      condition: "True Ending 路线"
      effect: "超脱末法影响"
```

---

*本文档定义了跨模块的统一规范。实现时应以此为准，确保各系统间的一致性。*

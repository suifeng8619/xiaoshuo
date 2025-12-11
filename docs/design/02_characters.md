# 角色设计文档

> 版本: 2.0 - 活世界架构
> 本文档定义NPC的人设、行为规则、互动接口和时间节点

---

## 第一章：设计原则

### 1.1 核心原则

每个重要角色都必须满足：

1. **有血有肉**：有欲望、有恐惧、有矛盾、有秘密
2. **会变化**：不是立牌坊，会因为经历而改变
3. **有立场**：在关键时刻会做出自己的选择，不一定符合玩家期望
4. **能失去**：可以死亡、可以离开、可以反目，这样玩家才会珍惜
5. **有时间**：寿命有限，瓶颈会卡，不是永远等待玩家

### 1.2 NPC行为护栏

AI生成NPC行为时的硬性约束：

```yaml
global_constraints:
  # 绝对不可违反
  hard_rules:
    - 核心人格不可突变（需要事件链支撑）
    - 关系值变化必须在[-20, +20]/次范围内
    - 死亡必须有前置事件（血量/状态铺垫）
    - 秘密揭露必须满足触发条件
    - 情感转变需要3+事件积累

  # 软性约束（特殊情况可打破）
  soft_rules:
    - 对话风格符合人设
    - 行为逻辑符合当前目标
    - 情绪反应符合性格基底

  # AI生成边界
  ai_boundaries:
    can_generate:
      - 日常对话内容
      - 情绪反应描述
      - 行为动机解释
      - 场景细节补充
    cannot_generate:
      - 新的核心秘密
      - 超出范围的能力表现
      - 与主线矛盾的事实
      - 未解锁的信息透露
```

---

## 第二章：行为动作词表

### 2.0 action_id 标准词表

所有 NPC 行为、事件触发、日志记录必须使用以下标准化的 action_id：

```yaml
# ============ 标准行为词表 ============
action_vocabulary:

  # ===== 移动类 =====
  movement:
    travel:           # 普通移动（需要 travel_time）
    teleport:         # 瞬移（传送阵等）
    escort:           # 护送移动（带人）
    flee:             # 逃跑
    pursue:           # 追击
    patrol:           # 巡逻（循环路径）
    return_home:      # 返回常驻地点

  # ===== 修炼类 =====
  cultivation:
    meditate:         # 打坐修炼（恢复灵力、增长修为）
    breakthrough:     # 突破（境界提升尝试）
    refine_body:      # 炼体
    practice_skill:   # 修炼功法/武技
    absorb_resource:  # 吸收灵物/丹药

  # ===== 社交类 =====
  social:
    talk:             # 普通对话
    deep_talk:        # 深入交谈（消耗时间，影响关系）
    give_gift:        # 赠送礼物
    ask_help:         # 请求帮助
    offer_help:       # 提供帮助
    confess:          # 表白/坦白
    argue:            # 争吵
    comfort:          # 安慰
    apologize:        # 道歉
    threaten:         # 威胁
    negotiate:        # 谈判

  # ===== 战斗类 =====
  combat:
    attack:           # 普通攻击
    defend:           # 防御
    cast_spell:       # 施法
    use_item:         # 使用道具（战斗中）
    retreat:          # 撤退
    surrender:        # 投降
    ambush:           # 伏击

  # ===== 日常类 =====
  daily:
    rest:             # 休息
    eat:              # 进食
    sleep:            # 睡眠
    work:             # 工作/执行任务
    shop:             # 购物
    craft:            # 制作（炼丹、炼器等）
    gather:           # 采集
    explore:          # 探索

  # ===== 事件响应类 =====
  response:
    observe:          # 观察（不介入）
    intervene:        # 介入
    report:           # 上报
    ignore:           # 忽视
    join:             # 加入
    witness:          # 见证（被动在场）

  # ===== 特殊/剧情类 =====
  special:
    trigger_event:    # 触发事件
    reveal_secret:    # 揭露秘密
    make_choice:      # 做出选择
    transform:        # 状态转变（黑化、觉醒等）
    die:              # 死亡
    disappear:        # 消失/失踪

# ============ 动作参数模板 ============
action_params:
  travel:
    from_location: location_id    # 出发地
    to_location: location_id      # 目的地
    travel_time: int              # 时辰数
    companions: [character_id]    # 同行者

  talk:
    target: character_id          # 对话对象
    topic: topic_id               # 话题
    duration: int                 # 持续时段数
    tone: enum                    # 语气 [friendly, neutral, hostile, formal]

  give_gift:
    target: character_id
    item_id: item_id
    is_secret: bool               # 是否私下赠送

  combat:
    target: character_id | group_id
    skill_used: skill_id
    outcome: enum                 # [victory, defeat, draw, interrupted]

# ============ 日志记录格式 ============
action_log_format:
  timestamp: absolute_tick        # 绝对时间刻
  actor: character_id
  action_id: action_vocabulary.*  # 必须来自词表
  params: {}                      # 动作参数
  result: {}                      # 执行结果
  witnesses: [character_id]       # 目击者列表
```

---

## 第三章：NPC 决策系统

### 3.0 决策算法框架

```python
class NPCDecisionEngine:
    """NPC 自主决策引擎"""

    def __init__(self, character: Character):
        self.char = character
        self.weights = character.personality_core.decision_weights

    def decide_action(self, context: Context) -> Action:
        """
        核心决策流程：
        1. 收集可用行动
        2. 计算每个行动的效用分数
        3. 应用性格权重
        4. 检查嫉妒/情绪修正
        5. 随机扰动 + 选择
        """
        available_actions = self._get_available_actions(context)
        scored_actions = []

        for action in available_actions:
            base_score = self._calculate_base_utility(action, context)
            weighted_score = self._apply_personality_weights(base_score, action)
            final_score = self._apply_emotional_modifiers(weighted_score, action)
            scored_actions.append((action, final_score))

        return self._select_action(scored_actions)

    def _calculate_base_utility(self, action: Action, ctx: Context) -> float:
        """计算行动的基础效用"""
        utility = 0.0

        # 目标达成度
        if action.advances_goal(self.char.current_goal):
            utility += 30

        # 安全性
        risk = action.risk_level
        utility -= risk * self.weights.get('self_preservation', 0.5) * 20

        # 社交收益
        if action.affects_relationship:
            target = action.target_character
            rel = self.char.get_relationship(target)
            if action.is_positive:
                utility += rel.affection * 0.1
            else:
                utility -= rel.trust * 0.2

        return utility

    def _apply_personality_weights(self, score: float, action: Action) -> float:
        """应用性格权重"""
        # 映射 action 类型到性格维度
        weight_mapping = {
            'protect_player': ['defend', 'intervene', 'escort'],
            'seek_recognition': ['breakthrough', 'practice_skill', 'report'],
            'maintain_image': ['talk', 'help', 'formal'],
            'loyalty': ['follow', 'obey', 'support'],
            'jealousy_suppress': ['congratulate', 'help_rival'],
        }

        for trait, actions in weight_mapping.items():
            if action.action_id in actions:
                weight = self.weights.get(trait, 0.5)
                score *= (0.5 + weight)  # 0.5~1.5 倍修正

        return score

    def _apply_emotional_modifiers(self, score: float, action: Action) -> float:
        """应用情绪修正（含嫉妒系统）"""
        emotion = self.char.emotional_state

        # ===== 嫉妒阈值系统 =====
        jealousy = getattr(self.char, 'jealousy', 0)

        if jealousy >= 90:
            # 危险边缘：极端行为解锁
            if action.action_id in ['betray', 'sabotage', 'attack']:
                score *= 2.0
            if action.action_id in ['help_rival', 'congratulate']:
                score *= 0.1

        elif jealousy >= 70:
            # 可能被利用：负面行为倾向上升
            if action.is_harmful_to_rival:
                score *= 1.5
            if action.is_helpful_to_rival:
                score *= 0.3

        elif jealousy >= 50:
            # 开始回避：消极行为
            if action.involves_rival:
                score *= 0.6

        elif jealousy >= 30:
            # 偶尔流露：轻微影响
            if action.involves_rival:
                score *= 0.9

        # ===== 其他情绪修正 =====
        emotion_modifiers = {
            'angry': {'attack': 1.3, 'forgive': 0.5},
            'scared': {'flee': 1.5, 'confront': 0.3},
            'sad': {'isolate': 1.2, 'socialize': 0.7},
            'grateful': {'help': 1.4, 'refuse': 0.4},
        }

        if emotion.current in emotion_modifiers:
            mods = emotion_modifiers[emotion.current]
            for action_type, modifier in mods.items():
                if action_type in action.action_id:
                    score *= modifier

        return score

    def _select_action(self, scored_actions: List[Tuple[Action, float]]) -> Action:
        """带随机扰动的选择"""
        import random

        # 添加随机扰动（10%）
        perturbed = [
            (action, score * random.uniform(0.9, 1.1))
            for action, score in scored_actions
        ]

        # 按分数排序
        perturbed.sort(key=lambda x: x[1], reverse=True)

        # 70% 选最优，30% 从前三选
        if random.random() < 0.7 or len(perturbed) < 3:
            return perturbed[0][0]
        else:
            top_3 = perturbed[:3]
            weights = [s for _, s in top_3]
            total = sum(weights)
            weights = [w / total for w in weights]
            return random.choices([a for a, _ in top_3], weights=weights)[0]


# ============ 嫉妒值变化触发器 ============
jealousy_triggers = {
    # 触发条件 -> 嫉妒值变化
    'player_praised_by_master': +10,
    'player_breakthrough': +15,
    'player_gets_rare_resource': +8,
    'player_defeats_rival': +12,
    'player_promoted': +10,

    # 降低嫉妒的行为
    'player_shows_concern': -5,
    'player_asks_for_help': -10,   # 被需要感
    'player_shares_resource': -8,
    'player_publicly_credits': -12,
    'player_fails_publicly': -5,   # 不那么完美了

    # 时间衰减
    'monthly_decay': -2,           # 每月自然衰减
}

# ============ 嫉妒阈值行为对照表 ============
jealousy_behavior_table = """
| 嫉妒值 | 外在表现 | 可能行为 | 风险等级 |
|--------|----------|----------|----------|
| 0-29   | 正常     | 正常社交、真心帮助 | 无 |
| 30-49  | 复杂情绪 | 偶尔酸言酸语、眼神闪躲 | 低 |
| 50-69  | 回避     | 找借口不见面、消极配合 | 中 |
| 70-89  | 被利用   | 可能接受敌对势力接触、泄露信息 | 高 |
| 90-100 | 危险边缘 | 主动背叛、破坏、暗害 | 极高 |
"""
```

---

## 第四章：核心角色

### 2.1 阿檀（沈檀儿）

#### 基础信息

```yaml
id: atan
name: 沈檀儿
nickname: 阿檀
gender: 女
birthday: 雪月初七  # 用于周年事件
initial_age: 16
lifespan_base: 80  # 凡人寿命
```

#### 外貌

```
清秀但不算绝色。常年流浪让她皮肤略显粗糙，但眼睛很亮。
习惯把头发扎成马尾，干净利落。
笑起来有两个浅浅的梨涡。
身量不高，看起来弱不禁风，实际上很能吃苦。
```

#### 性格基底（不可AI篡改）

```yaml
personality_core:
  # 表面性格
  surface:
    - 温柔体贴，总是照顾别人
    - 乐观开朗，很少抱怨
    - 善解人意，懂得察言观色

  # 内心驱动
  inner:
    - 极度害怕被抛弃（童年阴影）
    - 自卑，觉得自己配不上玩家
    - 倔强，一旦决定的事不会改变

  # 隐藏层（需解锁）
  hidden:
    - 有修炼天赋，但一直在压制
    - 害怕如果自己变强，和玩家的关系会改变
    - 对于"家"有执念，渴望稳定的归属

  # 决策权重（影响AI生成行为选择）
  decision_weights:
    protect_player: 0.9      # 保护玩家的倾向
    self_preservation: 0.3   # 自我保护倾向
    follow_rules: 0.5        # 遵守规则倾向
    seek_truth: 0.4          # 追求真相倾向
    loyalty: 0.95            # 忠诚度
```

#### 日程表

```yaml
schedule:
  # 默认日程（杂役弟子期）
  default:
    morning:
      location: kitchen
      activity: 准备早膳
      interruptible: true
    afternoon:
      location: herb_garden
      activity: 采药打杂
      interruptible: true
    evening:
      location: player_residence
      activity: 等待/陪伴玩家
      interruptible: false  # 优先级高
    night:
      location: servant_quarters
      activity: 休息
      interruptible: false

  # 条件覆盖
  overrides:
    - condition: "player.injured == true"
      all_slots:
        location: player_residence
        activity: 照顾玩家
        priority: 100

    - condition: "self.realm >= '练气初期'"
      afternoon:
        location: practice_ground
        activity: 修炼
```

#### 互动接口（事件触发点）

```yaml
interaction_points:
  # 主动对话入口
  dialogue_triggers:
    daily_greeting:
      available: "time_slot == 'morning' and location == 'kitchen'"
      topics: [daily_chat, ask_wellbeing, give_gift]

    evening_talk:
      available: "time_slot == 'evening' and location == 'player_residence'"
      topics: [deep_talk, share_secret, plan_future]

    emergency:
      available: "self.emotional_state in ['worried', 'scared', 'hurt']"
      topics: [comfort, ask_reason, promise]

  # 事件响应
  event_responses:
    player_injured:
      reaction: "立刻放下手中事情赶来"
      relationship_change: {concern: +5}
      memory_tag: "玩家受伤"

    player_breakthrough:
      reaction: "由衷高兴，但有一丝复杂情绪"
      relationship_change: {affection: +3, hidden_anxiety: +2}
      memory_tag: "玩家突破"

    player_with_other_woman:
      reaction: "根据好感度：低-无所谓，中-有点在意，高-醋意"
      relationship_change: "conditional"
      memory_tag: "玩家与其他女子"

    being_ignored:
      threshold: 30  # 连续30天未互动
      reaction: "情绪低落，不再主动找玩家"
      relationship_change: {trust: -10, affection: -5}
      memory_tag: "被忽视"

  # 特殊互动
  special_interactions:
    confession_available:
      condition: "affection >= 80 and trust >= 70 and shared_memories >= 5"
      event_id: "atan_confession"

    secret_reveal:
      condition: "trust >= 85 and event_flag('atan_awakening_hint')"
      reveals: "hidden_talent"
```

#### 时间节点

```yaml
time_nodes:
  # 生命周期事件
  lifecycle:
    age_20:
      year: 4  # 开局后第4年
      event: "成年礼，可以正式拜入门派"
      if_not_cultivator: "开始担忧寿命问题"

    age_30:
      year: 14
      event: "若仍是凡人，明显衰老"
      dialogue_change: "开始谈论来世"

    age_50:
      year: 34
      event: "凡人暮年"
      death_risk: "natural_aging"

  # 修炼瓶颈
  cultivation_bottlenecks:
    qi_refining_9:
      max_stuck_years: 10
      failure_consequence: "foundation_damaged"
      breakthrough_support:
        - player_help: +30% success
        - rare_pill: +20% success

    foundation_building:
      max_stuck_years: 20
      failure_consequence: "cultivation_waste"
      requires: "special_event_chain"

  # 关键决策点
  decision_points:
    year_2:
      event: "灵根觉醒机会"
      choice:
        accept: "开始修炼之路，关系动态变化"
        refuse: "保持现状，但错过机缘"
      player_can_influence: true

    year_5:
      condition: "affection < 40"
      event: "有人向阿檀示好"
      choice:
        accept_other: "与玩家渐行渐远"
        refuse_other: "继续等待玩家"
      player_can_influence: true
```

#### 记忆结构

```yaml
memory_schema:
  # 核心记忆（永久保留）
  core_memories:
    - id: first_meeting
      content: "与玩家第一次相遇的情形"
      emotional_weight: 10
      tags: [origin, bond]

    - id: player_protected_her
      content: "玩家为她挨打的那天"
      emotional_weight: 9
      tags: [sacrifice, gratitude]

    - id: arriving_qingyun
      content: "来到青云门的期待与不安"
      emotional_weight: 7
      tags: [new_beginning, hope]

  # 动态记忆
  dynamic_memories:
    max_count: 50
    priority_factors:
      - emotional_intensity
      - recency
      - player_involvement

    compression_rules:
      after_100_days: "相似事件合并为'那段时间...'"
      after_1_year: "只保留最重要的3件事"

  # 情感账本
  emotional_ledger:
    positive_balance: 0  # 正面事件积累
    negative_balance: 0  # 负面事件积累
    last_major_event: null
    days_since_interaction: 0
```

#### 结局路线

```yaml
endings:
  dao_lv:  # 道侣
    conditions:
      affection: ">= 90"
      trust: ">= 85"
      shared_crisis: ">= 3"
      confession_event: completed
    description: "并肩修仙，不离不弃"
    epilogue_variant: [happy, bittersweet, tragic]

  separation:  # 分离
    conditions:
      affection: "< 50"
      trust: "< 40"
      ignored_days: "> 100"
    description: "和平分手或不欢而散"
    epilogue_variant: [peaceful, resentful, regretful]

  sacrifice:  # 牺牲
    conditions:
      affection: ">= 70"
      event_flag: "atan_sacrifice_trigger"
      player_in_mortal_danger: true
    description: "为救玩家而死"
    epilogue_variant: [heroic, preventable]

  darkened:  # 黑化
    conditions:
      trust: "< 20"
      event_flag: "atan_betrayal_seed"
      enemy_contact: true
    description: "被仇人利用，站在对立面"
    epilogue_variant: [redeemed, fallen]
```

---

### 2.2 师父·云隐子

#### 基础信息

```yaml
id: master_yunyin
name: 云隐子
real_name: 秦远（极少人知道）
gender: 男
apparent_age: 40
actual_age: 312
realm: 金丹期大圆满
position: 青云门长老，云霞峰峰主
lifespan_remaining: ~200年  # 金丹期寿命约500年
```

#### 外貌

```
面容清癯，两鬓微霜，目光深邃。
常年穿一身洗得发白的青袍，不修边幅。
看起来像个落魄的中年文士，毫无高人气派。
但出手时，眼神会变得锐利如剑。
```

#### 性格基底

```yaml
personality_core:
  surface:
    - 寡言少语，经常发呆
    - 对徒弟严格，少有夸赞
    - 不通人情世故，常被其他长老嘲笑

  inner:
    - 极重情义，只是不善表达
    - 对自己要求极高，所以对徒弟也高要求
    - 内心柔软，见不得弱者受欺

  hidden:
    - 年轻时经历过刻骨铭心的往事
    - 选择玩家为徒，不只是因为天赋
    - 他的过去和玩家的身世可能有关联

  decision_weights:
    protect_disciple: 0.85
    follow_sect_rules: 0.6
    seek_truth: 0.7
    revenge_old_enemy: 0.4  # 压制着
    self_sacrifice: 0.8
```

#### 日程表

```yaml
schedule:
  default:
    morning:
      location: cloud_peak_top
      activity: 吐纳修炼
      interruptible: false  # 修炼时不可打扰
    afternoon:
      location: varies  # 门派事务
      activity: 处理杂务/闭关
      interruptible: "only_emergency"
    evening:
      location: yunxia_hall
      activity: 可能指点弟子
      interruptible: true
    night:
      location: personal_cave
      activity: 参悟/回忆
      interruptible: false

  overrides:
    - condition: "calendar.is_teaching_day"
      afternoon:
        location: practice_ground
        activity: 指导弟子修炼

    - condition: "player.in_danger and danger_level >= 'serious'"
      all_slots:
        activity: 赶往玩家位置
        priority: 999
```

#### 互动接口

```yaml
interaction_points:
  dialogue_triggers:
    formal_teaching:
      available: "calendar.is_teaching_day and time_slot == 'afternoon'"
      topics: [ask_cultivation, report_progress, seek_guidance]
      tone: "严肃但耐心"

    private_audience:
      available: "player.has_appointment or urgent_matter"
      topics: [personal_matter, sect_issue, request_help]
      tone: "根据话题调整"

    rare_opening:
      available: "trust >= 70 and random_chance(0.1)"
      topics: [ask_past, deep_philosophy, share_wine]
      tone: "难得的放松"

  event_responses:
    player_in_danger:
      reaction: "评估威胁等级，决定是否出手"
      threshold: "danger >= 'life_threatening' or trust >= 60"
      action: "暗中保护或直接救援"

    player_breaks_rules:
      reaction: "根据严重程度和动机判断"
      outcomes:
        minor: "训斥但不惩罚"
        major: "惩罚但给机会"
        severe: "可能逐出师门（极端情况）"

    player_asks_about_past:
      reaction: "沉默或转移话题"
      unlock_condition: "trust >= 80 and specific_event_triggered"

  special_interactions:
    inheritance_transmission:
      condition: "player.realm >= '筑基中期' and trust >= 85"
      event_id: "master_true_teaching"
      content: "传授真正的绝学"

    past_revealed:
      condition: "story_flag('truth_seeker_phase_3') and relationship >= 'father_son'"
      reveals: ["real_name", "tragic_past", "connection_to_player"]
```

#### 时间节点

```yaml
time_nodes:
  cultivation_crisis:
    year_range: [5, 15]  # 开局后5-15年间可能发生
    event: "突破元婴失败的旧伤复发"
    consequence:
      minor: "闭关疗伤3个月"
      major: "修为倒退，寿命缩短"
      critical: "需要玩家寻找特殊灵药"

  old_enemy_returns:
    trigger: "story_flag('revenge_phase_3')"
    event: "过去的仇人找上门"
    player_involvement: "必须在场"

  succession_decision:
    year: 20  # 开局后约20年
    condition: "player.realm >= '金丹期'"
    event: "考虑传位或让玩家独立"

  death_flags:
    natural_death:
      year_range: [100, 200]
      condition: "no_breakthrough and no_life_extension"

    sacrifice_death:
      condition: "player_in_mortal_danger and no_other_way"
      event_chain: "master_final_protection"

    peaceful_passing:
      condition: "all_resolved and player_grown"
      event_chain: "master_peaceful_end"
```

#### 核心秘密系统

```yaml
secrets:
  level_1:  # 表层秘密
    content: "对玩家格外关照的真正原因"
    unlock_trust: 50
    hint_events: ["意味深长的目光", "莫名的叹息"]

  level_2:  # 深层秘密
    content: "三百年前的那个人是谁"
    unlock_trust: 75
    requires_event: "find_old_portrait"

  level_3:  # 核心秘密
    content: "与玩家父母的关联"
    unlock_trust: 90
    requires_event_chain: ["truth_phase_4", "master_confession"]
```

---

### 2.3 仇人·玄影

#### 基础信息

```yaml
id: enemy_xuanying
name: 玄影
real_name: 不详（有待揭露）
gender: 男
apparent_age: 30
actual_age: 不详
realm: 元婴期初期
position: 幽冥教长老
```

#### 外貌

```
面容俊美，似笑非笑。
穿黑衣，声音低沉好听。
眼神深处有一丝不易察觉的疯狂。
初见让人觉得亲和，久处会感到彻骨的寒意。
```

#### 性格基底

```yaml
personality_core:
  surface:
    - 彬彬有礼，风度翩翩
    - 对敌人也保持微笑
    - 做事不紧不慢，胸有成竹

  inner:
    - 极度执念于某个目标
    - 把所有人当作棋子
    - 对弱者有种病态的"怜悯"

  hidden:
    - 他的执念和玩家的身世有关
    - 他并非纯粹的恶人，有自己的"正义"
    - 他的过去和某个被掩埋的真相有关

  decision_weights:
    achieve_goal: 0.95
    preserve_self: 0.7
    show_mercy: 0.2  # 偶尔
    enjoy_game: 0.6  # 喜欢"玩弄"
```

#### 行为模式

```yaml
behavior_patterns:
  # 他不会主动杀死玩家（初期）
  player_interactions:
    early_game:
      stance: "观察者/试探者"
      may_help: true  # 出于目的
      will_kill: false

    mid_game:
      stance: "对手/信息源"
      reveals_hints: true
      confrontation: "philosophical"

    late_game:
      stance: "最终对决或...?"
      flexible_ending: true

  # 出场规律
  appearance_pattern:
    frequency: "每个主要阶段1-2次"
    style: "神秘出现，适时离开"
    never: "不会在玩家绝对劣势时赶尽杀绝"
```

#### 互动接口

```yaml
interaction_points:
  encounter_triggers:
    mysterious_helper:
      phase: "revenge_phase_1"
      context: "玩家陷入困境时出现"
      identity: hidden
      purpose: "观察/试探"

    first_revelation:
      phase: "revenge_phase_2"
      trigger: "jade_pendant_activated"
      reaction: "露出真实身份"

    philosophical_debate:
      phase: "revenge_phase_3"
      context: "双方都有所成长"
      topics: [justice, truth, past]

    final_confrontation:
      phase: "revenge_phase_5"
      outcomes: [kill, spare, ally, mutual_destruction]

  information_reveals:
    jade_pendant_origin:
      trust_irrelevant: true  # 他主动透露
      timing: "revenge_phase_2"

    parents_truth_partial:
      timing: "revenge_phase_3"
      content: "你父母不是你想的那样单纯"

    full_truth:
      timing: "revenge_phase_5"
      condition: "player chooses to listen"
```

#### 时间节点

```yaml
time_nodes:
  appearance_schedule:
    year_1_3:
      frequency: 0-1次
      role: "神秘人物"

    year_4_7:
      frequency: 1-2次
      role: "真相的一部分"

    year_8_15:
      frequency: 2-3次
      role: "复杂的对手"

    year_15_plus:
      frequency: "根据剧情"
      role: "最终抉择"

  power_scaling:
    initial: "元婴初期（碾压玩家）"
    year_10: "可能突破（拉大差距）"
    year_20: "取决于剧情走向"
```

---

### 2.4 大师兄·苏云帆

#### 基础信息

```yaml
id: senior_suyunfan
name: 苏云帆
gender: 男
apparent_age: 25
actual_age: 83
realm: 筑基期大圆满（卡瓶颈）
position: 云隐子座下大弟子
```

#### 性格基底

```yaml
personality_core:
  surface:
    - 温和有礼，关照师弟师妹
    - 能力出众，处事公正
    - 是师门的主心骨

  inner:
    - 争强好胜，只是藏得好
    - 对自己要求极高，不容许失败
    - 渴望得到师父的认可

  hidden:
    - 多年卡在筑基大圆满，心生焦虑
    - 对玩家的天赋暗自嫉妒
    - 在巨大压力下可能做出什么选择？

  decision_weights:
    help_juniors: 0.7
    seek_recognition: 0.8
    maintain_image: 0.85
    jealousy_suppress: 0.6  # 能否压制嫉妒
    righteousness: 0.65
```

#### 互动接口

```yaml
interaction_points:
  dialogue_triggers:
    daily_guidance:
      available: "player.realm < '筑基中期'"
      topics: [cultivation_tips, sect_rules, resource_info]
      tone: "亲切大哥"

    realm_discussion:
      available: "player.realm >= '筑基中期'"
      topics: [compare_notes, share_insights]
      tone: "根据嫉妒值变化"

    crisis_moment:
      available: "self.jealousy >= 70 or self.desperation >= 80"
      topics: [confession, plea, confrontation]

  jealousy_system:
    triggers:
      player_praised_by_master: +10
      player_breakthrough: +15
      player_gets_rare_resource: +8
      player_shows_concern: -5
      player_asks_for_help: -10  # 被需要感

    thresholds:
      30: "偶尔流露复杂情绪"
      50: "开始回避玩家"
      70: "可能被人利用"
      90: "危险边缘"
```

#### 分支路线

```yaml
route_branches:
  noble_brother:
    condition: "jealousy < 50 at year_10"
    development:
      - "克服心魔，真心祝福玩家"
      - "可能在玩家帮助下突破"
      - "成为可靠盟友"

  fallen_brother:
    condition: "jealousy >= 70 and external_temptation"
    development:
      - "被敌对势力接触"
      - "做出背叛行为"
      - "可能悔悟，也可能一错到底"

  tragic_sacrifice:
    condition: "jealousy >= 50 but < 70 and crisis_event"
    development:
      - "关键时刻觉醒"
      - "以死谢罪或保护师门"
```

---

### 2.5 小师妹·林雪瑶

#### 基础信息

```yaml
id: junior_linxueyao
name: 林雪瑶
gender: 女
initial_age: 14
realm: 练气初期
position: 云隐子座下小弟子
origin: 灵虚宗老朋友托付
```

#### 性格基底

```yaml
personality_core:
  surface:
    - 活泼开朗，叽叽喳喳
    - 黏人，特别喜欢跟着玩家
    - 有点小迷糊，经常闯祸

  inner:
    - 比表面看起来聪明得多
    - 敏感，能察觉师门中的暗流
    - 害怕被抛弃，所以用活泼掩饰不安

  hidden:
    - 身世可能有秘密（灵虚宗托付的原因）
    - 对玩家是纯粹的依赖（家人，非恋爱）
```

#### 特殊定位

```yaml
narrative_role:
  primary: "温暖具象化"
  secondary: "情感锚点"
  tertiary: "玩家善良的来源"

  constraints:
    not_romance_option: true  # 她是"家人"
    high_emotional_impact: true  # 如果她死，玩家最痛

  protection_status:
    plot_armor_years: 5  # 前5年不会死
    after_year_5: "可能面临危险"
```

#### 时间节点

```yaml
time_nodes:
  growth_milestones:
    year_3:
      event: "从小女孩变成少女"
      personality_shift: "更加成熟但保持天真"

    year_7:
      event: "遭遇危机（可能）"
      outcomes: [saved, injured, worse]

    year_10:
      event: "成长为独立的修士"
      relationship: "从黏人变成互相支持"
```

---

## 第三章：次要角色模板

### 3.1 青云门角色

```yaml
characters:
  qingxu_zhenren:
    id: sect_master
    name: 清虚真人
    position: 青云门掌门
    realm: 化神期
    personality: 城府极深，面上和蔼，实则算计
    secret: 知道一些关于玩家身世的事
    interaction_frequency: low
    event_triggers:
      - "重大门派事务"
      - "玩家达到金丹期"
      - "外敌入侵"

  luo_tianming:
    id: elder_luo
    name: 洛天明
    position: 执法长老
    realm: 金丹期
    personality: 刚正不阿，嫉恶如仇
    relationship_with_master: 年轻时的挚友
    secret: 知道云隐子的过去
    interaction_frequency: medium

  zhao_yuanzhen:
    id: elder_zhao
    name: 赵元真
    position: 另一峰门长老
    realm: 金丹期
    personality: 嫉贤妒能，手段阴险
    role: 门派内部阻力来源
    interaction_frequency: medium
    event_triggers:
      - "玩家获得重要资源"
      - "门派内部竞争"
```

### 3.2 其他势力角色

```yaml
characters:
  xiao_yichen:
    id: wanjian_genius
    name: 萧逸尘
    position: 万剑宗天才弟子
    realm: 与玩家相近（动态）
    personality: 只爱剑，不通人情
    relationship: "可友可敌，看玩家选择"
    event_pool: [sword_competition, chance_encounter, alliance_proposal]

  yueji:
    id: youming_yueji
    name: 月姬
    position: 玄影的师妹
    realm: 元婴期（隐藏）
    personality: 冷艳，看不透
    secret: 可能知道玩家父母的事
    appearance_timing: "关键时刻"
```

---

## 第四章：关系网络系统

### 4.1 关系图谱

```
                    【清虚真人】(掌门)
                         │
                    知道秘密？
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
【赵元真】(对立)    【云隐子】(师父)    【洛天明】(友)
                    ／    │    ＼
                   ／     │     ＼
            【苏云帆】  【玩家】  【林雪瑶】
             (大师兄)     │      (小师妹)
                复杂      │
                         │
                    ┌────┴────┐
                    │         │
                【阿檀】    【身世】
                 (羁绊)       │
                              │
                         ┌────┴────┐
                         │         │
                     【玄影】    【真相】
                      (仇人)     (父母？)
                         │
                    ┌────┴────┐
                    │         │
                【月姬】    【幽冥教】
```

### 4.2 关系值系统

```yaml
relationship_dimensions:
  trust:       # 信任度 0-100
    description: "相信对方会履行承诺"
    decay_rate: 0.5/month  # 无互动时缓慢下降

  affection:   # 好感度 0-100
    description: "喜欢对方的程度"
    decay_rate: 0.3/month

  respect:     # 尊敬度 0-100
    description: "认可对方的能力和品格"
    decay_rate: 0.2/month

  fear:        # 畏惧度 0-100
    description: "害怕对方的程度"
    decay_rate: 1.0/month  # 恐惧消退较快

  # 特殊维度
  debt:        # 恩情/仇恨
    positive: "欠玩家人情"
    negative: "玩家欠他人情"
    no_decay: true  # 恩怨不会自然消退
```

### 4.3 关系动态公式

```python
def calculate_relationship_change(event, npc, player):
    """计算关系值变化"""
    base_change = event.relationship_impact

    # 性格修正
    personality_modifier = npc.decision_weights.get(event.type, 1.0)

    # 历史修正
    history_modifier = 1.0
    if similar_events := npc.find_similar_memories(event):
        # 重复行为效果递减
        history_modifier = 1.0 / (1 + len(similar_events) * 0.2)

    # 情绪修正
    emotion_modifier = npc.current_emotion.sensitivity

    # 最终变化
    final_change = base_change * personality_modifier * history_modifier * emotion_modifier

    # 硬性上限
    return clamp(final_change, -20, +20)
```

---

## 第五章：角色记忆系统

### 5.1 记忆数据结构

```yaml
character_memory:
  # 基础信息
  id: unique_id
  name: 显示名

  # 与玩家的关系数值
  relationship:
    trust: 50
    affection: 50
    respect: 50
    fear: 0
    debt: 0

  # 态度标签（可叠加）
  attitude_tags:
    - "视如亲人"
    - "暗生情愫"
    # ...

  # 核心记忆（永久）
  core_memories:
    - event_id: first_meeting
      timestamp: year_1_month_1
      emotional_weight: 10
      summary: "第一次见面时..."

  # 动态记忆（会压缩）
  recent_memories:
    - event_id: xxx
      timestamp: xxx
      importance: 1-10
      compressed: false

  # 情感状态
  emotional_state:
    current: neutral
    intensity: 0
    duration: 0
    cause: null

  # 未解决事项
  unresolved:
    promises: []  # 玩家的承诺
    debts: []     # 恩怨
    questions: [] # 想问的事

  # 秘密状态
  secrets:
    level_1_revealed: false
    level_2_revealed: false
    level_3_revealed: false
```

### 5.2 记忆压缩算法

```python
def compress_memories(npc, current_date):
    """定期压缩记忆，保持重要的、丢弃琐碎的"""
    memories = npc.recent_memories

    for memory in memories:
        age_days = (current_date - memory.timestamp).days

        if age_days > 365:  # 超过1年
            if memory.importance < 7:
                # 低重要性记忆融合
                merge_into_period_summary(memory)
            else:
                # 高重要性记忆保留但简化
                memory.summary = ai_summarize(memory.details)
                memory.details = None

        elif age_days > 100:  # 超过100天
            if memory.importance < 5:
                # 非常低重要性直接丢弃
                memories.remove(memory)
```

---

## 第六章：AI生成指南

### 6.1 对话生成约束

```yaml
dialogue_constraints:
  # 全局约束
  global:
    - 不透露未解锁的秘密
    - 不做出与人设矛盾的表态
    - 不使用超出时代的词汇
    - 记住最近的互动历史

  # 角色特定
  atan:
    tone: "温柔但不卑微"
    never_say: ["我不配", "你抛弃我吧"]  # 除非极端情况
    often_use: ["你...吃饭了吗", "我等你"]
    emotional_range: [关心, 担忧, 开心, 委屈]

  master_yunyin:
    tone: "严肃简洁"
    never_say: ["我为你骄傲"]  # 除非超重大时刻
    often_use: ["自己悟", "修炼去", "还不够"]
    emotional_range: [严厉, 沉默, 欣慰(隐藏)]

  enemy_xuanying:
    tone: "优雅危险"
    never_say: ["我要杀了你"]  # 他更喜欢玩味
    often_use: ["有意思", "你让我想起...", "不急"]
    emotional_range: [玩味, 认真, 疯狂(隐藏)]
```

### 6.2 行为生成约束

```yaml
behavior_constraints:
  # 决策时必须考虑
  decision_factors:
    - 当前目标
    - 性格权重
    - 与玩家关系
    - 情绪状态
    - 周围环境

  # 禁止的行为
  forbidden_behaviors:
    all_npcs:
      - 无缘无故攻击玩家
      - 突然性格大变
      - 透露不该知道的信息

    atan:
      - 主动离开玩家（除非关系破裂）
      - 对玩家冷漠（除非受伤太深）

    master:
      - 当众夸奖玩家（除非超级大事）
      - 放弃徒弟（除非极端背叛）
```

---

*本文档定义了核心角色的完整规格，包括人设、行为规则、互动接口和时间节点。所有NPC的行为必须在此框架内生成。*

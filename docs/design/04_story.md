# 剧情设计文档

## 核心理念

**事件池驱动，不是线性剧本。**

玩家在活的世界中探索，剧情通过事件自然发生，而不是按顺序推进。

核心原则：
- 主矛盾有阶段，但没有固定顺序
- 事件可以被错过，错过有后果
- 多条线索并行，玩家决定追哪条
- 情感积累比剧情推进更重要

---

## 一、主矛盾体系

### 1.1 三条主矛盾线

```yaml
仇人线 (Revenge):
  核心冲突: 玄影杀了玩家父母，玩家要复仇还是放下
  情感核心: 仇恨、执念、真相的复杂性
  最终问题: 复仇之后，你是谁？

阿檀线 (Bond):
  核心冲突: 凡人与修士的时间差，在一起还是放手
  情感核心: 羁绊、牺牲、陪伴的代价
  最终问题: 为了她，你愿意放弃什么？

真相线 (Truth):
  核心冲突: 世界的真相（灵气衰竭、轮回秘密）
  情感核心: 渺小、觉醒、超脱
  最终问题: 知道真相后，你还要继续吗？
```

### 1.2 主矛盾阶段

每条主矛盾线有独立的阶段，玩家行动推进阶段，时间流逝也会推进（被动推进）。

```yaml
仇人线阶段:
  phase_0_dormant:
    名称: 潜伏
    状态: 玄影在暗处，玩家不知道他存在
    触发进入下阶段:
      - 事件"玄影初遇"触发
      - 或：发现玉佩线索
    被动推进: 第5年自动进入phase_1

  phase_1_aware:
    名称: 显露
    状态: 玩家知道仇人存在，但不知道全貌
    触发进入下阶段:
      - 事件"真相揭露"触发
      - 或：师父告知真相
    被动推进: 仇人线索积累>=3

  phase_2_conflict:
    名称: 冲突
    状态: 双方有过交手，仇恨明确
    触发进入下阶段:
      - 事件"师父受伤"触发
      - 或：玩家主动追杀
    被动推进: 第15年自动升级（玄影主动出击）

  phase_3_climax:
    名称: 决战
    状态: 最终对决窗口开启
    触发进入下阶段:
      - 事件"最终对决"完成
    被动推进: 第30年强制触发

  phase_4_resolution:
    名称: 结局
    状态: 仇人死/和解/逃脱/玩家死
    变体: 根据选择分支

阿檀线阶段:
  phase_0_childhood:
    名称: 青梅竹马
    状态: 相依为命，情感纯粹
    触发进入下阶段:
      - 事件"灵根发现"触发
      - 或：relationship.affection >= 60

  phase_1_budding:
    名称: 情愫暗生
    状态: 开始有超越友情的东西
    触发进入下阶段:
      - 事件"心意相通"触发
      - 或：relationship.affection >= 80

  phase_2_crisis:
    名称: 危机考验
    状态: 阿檀遇险/生病/被威胁
    触发进入下阶段:
      - 危机解决
      - 或：阿檀受到不可逆伤害

  phase_3_choice:
    名称: 命运抉择
    状态: 必须做出选择
    触发条件:
      - 阿檀不修炼且年龄>40
      - 或：玩家长期闭关导致疏远
      - 或：主动触发告白事件

  phase_4_ending:
    名称: 结局
    变体:
      - 道侣
      - 分离（但互相挂念）
      - 阿檀老去/死亡
      - 阿檀成为修士（活得久）
      - 破裂（信任崩溃）

真相线阶段:
  phase_0_ignorant:
    名称: 无知
    状态: 不知道世界有更深的秘密
    触发进入下阶段:
      - 发现灵气衰竭线索
      - 或：触发轮回记忆碎片

  phase_1_suspicious:
    名称: 疑惑
    状态: 开始怀疑世界不对劲
    线索收集: [灵气衰竭, 师父过去, 轮回迹象]
    触发进入下阶段:
      - 线索>=2

  phase_2_investigating:
    名称: 追查
    状态: 主动调查真相
    触发进入下阶段:
      - 发现关键证据
      - 或：遇到知情者

  phase_3_revelation:
    名称: 揭露
    状态: 知道了真相
    可能的真相:
      - 灵气衰竭是人为（飞升者抽取）
      - 轮回被操控
      - 这个世界是"养殖场"

  phase_4_transcend:
    名称: 超脱
    状态: 面对真相后的选择
    变体:
      - 打破命运
      - 接受命运
      - 成为新的操控者
```

---

## 二、事件池设计

### 2.1 事件池结构

```yaml
事件池层级:
  daily_pool:     # 日常事件（高频低冲击）
  opportunity_pool:  # 机缘事件（中频中冲击）
  critical_pool:  # 关键事件（低频高冲击）

事件与主矛盾关联:
  每个事件标记所属主矛盾线和推进效果
  同一阶段可以有多个入口事件
  玩家可以从不同场景进入同一剧情节点
```

### 2.2 关键事件定义

#### 仇人线事件

```yaml
# ========== 仇人线：phase_0 → phase_1 ==========

event_玄影初遇:
  id: "revenge_001"
  name: "神秘黑衣人"
  storyline: revenge
  phase_trigger: "phase_0 → phase_1"
  tier: critical

  # 触发窗口
  window:
    time:
      year_min: 1
      year_max: 8
    locations:
      - 矿洞节点
      - 护送任务路段
      - 危险秘境

  # 前置条件
  preconditions:
    player:
      realm_min: 练气3
      injury_state: "!dying"
    flags_absent:
      - 玄影已见面

  # 触发方式（多入口）
  triggers:
    - type: location_enter
      locations: [矿洞节点]
      chance: 0.3
    - type: quest_complete
      quest: "护送任务"
      chance: 0.5
    - type: time_window
      check_interval: monthly
      base_chance: 0.1

  # 事件效果
  effects:
    set_flags:
      - 玄影已见面
    schedule_followups:
      - event_id: revenge_002_玄影再现
        delay_min: 180d
        delay_max: 540d

  # 事件变体
  variants:
    - id: rescue
      condition: "玩家主动救助"
      ai_tags: [感激, 隐匿身份, 欲言又止]
      extra_effects:
        relationship:
          - npc: 玄影
            changes: {mystery: +15, trust: +5}

    - id: observe
      condition: "玩家旁观"
      ai_tags: [打量, 警惕, 自行脱困]

    - id: hostile
      condition: "玩家敌意"
      ai_tags: [冷笑, 威压, 警告]

  # 叙事资源
  narrative:
    opening: |
      你在{location}行走时，听到前方传来打斗声。
      循声望去，只见一个黑衣人正与数人缠斗。
      那人身法诡异，面容却带着淡淡的笑意，似乎并不把对手放在眼里。
    ai_constraints:
      - 不要透露玄影真实身份
      - 不要提及玉佩（除非玩家主动展示）
      - 保持悬念感

  # 过期处理
  expiry: year_8
  expiry_consequence:
    description: "错过初遇，玄影主动现身"
    trigger_event: revenge_001b_玄影主动接触

# ----------

event_玄影再现:
  id: "revenge_002"
  name: "故人重逢"
  storyline: revenge
  tier: critical

  window:
    time:
      year_min: 2
      year_max: 12
    locations: any  # 任何地点都可能

  preconditions:
    flags_required:
      - 玄影已见面
    flags_absent:
      - 玄影真实身份暴露

  triggers:
    - type: scheduled  # 由上一个事件调度
    - type: random
      daily_chance: 0.02
      condition: "玩家境界 >= 筑基"

  variants:
    - id: warning
      condition: "玩家变强了"
      ai_tags: [赞赏, 暗示, 若有所指]
      narrative_hint: "玄影提到玩家的玉佩，语气意味深长"

    - id: test
      condition: "玄影想试探"
      ai_tags: [考验, 出手, 点到为止]

# ========== 仇人线：phase_1 → phase_2 ==========

event_真相揭露:
  id: "revenge_010"
  name: "血海深仇"
  storyline: revenge
  phase_trigger: "phase_1 → phase_2"
  tier: critical

  window:
    time:
      year_min: 5
      year_max: 20

  preconditions:
    flags_required:
      - 玄影已见面
    storyline_phase:
      revenge: phase_1
    any_of:
      - flags: [找到父母遗物]
      - flags: [师父透露真相]
      - flags: [玄影主动坦白]

  triggers:
    - type: flag_set
      flag: 找到父母遗物
    - type: relationship_threshold
      npc: 师父
      dimension: trust
      threshold: 80
    - type: event_chain
      previous: revenge_005_父母遗物

  effects:
    set_flags:
      - 知道玄影是仇人
      - 玄影真实身份暴露
    relationship:
      - npc: 玄影
        changes: {trust: -100, hatred: +50}

  variants:
    - id: from_evidence
      condition: "通过遗物发现"
      ai_tags: [震惊, 愤怒, 不敢置信]

    - id: from_master
      condition: "师父告知"
      ai_tags: [沉痛, 责任, 往事]

    - id: from_enemy
      condition: "玄影主动坦白"
      ai_tags: [嘲讽, 挑衅, 傲慢]

# ========== 仇人线：phase_2 → phase_3 ==========

event_师父受伤:
  id: "revenge_020"
  name: "护徒之伤"
  storyline: revenge
  phase_trigger: "phase_2 → phase_3"
  tier: critical
  interrupt: true  # 强制打断玩家当前行动

  window:
    time:
      year_min: 8
      year_max: 25

  preconditions:
    flags_required:
      - 玄影真实身份暴露
    npc_states:
      师父: alive
    storyline_phase:
      revenge: phase_2

  triggers:
    - type: time_window
      check_interval: monthly
      base_chance: 0.05
      urgency_multiplier: 1.5  # 越接近过期概率越高
    - type: player_action
      action: "主动追杀玄影"
      consequence: "玄影反击"

  effects:
    set_flags:
      - 师父重伤
    npc_state_change:
      师父:
        health: critical
        can_die: true  # 如果不治疗会死
    schedule_followups:
      - event_id: revenge_021_师父遗言
        delay: 3d
        condition: "师父未被救治"

  narrative:
    opening: |
      那一剑，本是冲你而来。
      师父挡在了前面。
      金丹碎裂的声音，像是什么东西永远地破碎了。
    ai_constraints:
      - 场景要悲壮但不煽情
      - 师父的话要少而有力
      - 给玩家选择的空间
```

#### 阿檀线事件

```yaml
# ========== 阿檀线：phase_0 → phase_1 ==========

event_灵根发现:
  id: "bond_001"
  name: "意外的天赋"
  storyline: bond
  phase_trigger: "phase_0 → phase_1"
  tier: critical

  window:
    time:
      year_min: 0.5
      year_max: 3

  preconditions:
    npc_states:
      阿檀: alive
    flags_absent:
      - 阿檀灵根已测

  triggers:
    - type: time_window
      check_interval: weekly
      base_chance: 0.1
    - type: event_chain
      previous: bond_000_宗门测试日

  effects:
    set_flags:
      - 阿檀有灵根
      - 阿檀灵根已测

  # 这是一个选择事件
  choices:
    - id: go_lingxu
      label: "让她去灵虚宗"
      description: "对她的未来好，但要分开"
      effects:
        set_flags: [阿檀去灵虚宗]
        relationship:
          - npc: 阿檀
            changes: {affection: -5, respect: +10}
        schedule: event_bond_010_灵虚重逢

    - id: stay_qingyun
      label: "让她留在青云门"
      description: "在一起，但修炼受限"
      effects:
        set_flags: [阿檀留青云门]
        relationship:
          - npc: 阿檀
            changes: {affection: +10, dependency: +5}

    - id: her_choice
      label: "让她自己决定"
      description: "尊重她的选择"
      effects:
        # 由阿檀的性格和关系值决定
        npc_decision:
          npc: 阿檀
          factors:
            - relationship.affection > 70: stay (0.7)
            - relationship.dependency > 60: stay (0.8)
            - default: go (0.5)

# ========== 阿檀线：关系触发事件 ==========

event_心意相通:
  id: "bond_020"
  name: "无言的默契"
  storyline: bond
  phase_trigger: "phase_1 → phase_2"
  tier: opportunity

  window:
    time:
      year_min: 2

  preconditions:
    relationship:
      阿檀:
        affection: ">=75"
        trust: ">=60"
    flags_absent:
      - 与阿檀表白

  triggers:
    - type: relationship_threshold
      npc: 阿檀
      dimension: affection
      threshold: 80
    - type: location_together
      npc: 阿檀
      locations: [后山溪边, 山顶, 月下]
      time_slots: [evening, night]

  narrative:
    opening: |
      月光下，你们并肩而坐。
      谁也没说话，但好像什么都说了。

# ========== 阿檀线：危机事件 ==========

event_阿檀遇险:
  id: "bond_030"
  name: "危机"
  storyline: bond
  phase_trigger: "phase_2 触发"
  tier: critical
  interrupt: true

  window:
    time:
      year_min: 5
      year_max: 20

  preconditions:
    npc_states:
      阿檀: alive
    storyline_phase:
      bond: ">=phase_1"

  triggers:
    - type: storyline_progress
      storyline: revenge
      phase: phase_2  # 仇人开始报复时，阿檀可能被牵连
    - type: random
      yearly_chance: 0.15
      condition: "阿檀境界 < 玩家境界-2"

  variants:
    - id: kidnapped
      condition: "仇人线active"
      description: "被玄影手下抓走"
      effects:
        set_flags: [阿檀被绑架]
        schedule:
          - event_id: bond_031_营救阿檀
            delay: 7d
            expiry: 30d  # 30天内必须救，否则...

    - id: injured
      condition: "宗门有变"
      description: "宗门混乱中受伤"
      effects:
        npc_state_change:
          阿檀:
            health: injured

    - id: illness
      condition: "阿檀未修炼 && 年龄>30"
      description: "凡人身体开始衰弱"
      effects:
        set_flags: [阿檀生病]
        schedule:
          - event_id: bond_032_阿檀重病
            delay: 365d
            condition: "仍未修炼"
```

#### 真相线事件

```yaml
# ========== 真相线：线索事件 ==========

event_灵气异常:
  id: "truth_001"
  name: "灵气稀薄"
  storyline: truth
  tier: daily

  window:
    time:
      year_min: 3

  triggers:
    - type: location_enter
      locations: [偏僻区域, 废弃矿洞, 枯竭灵脉]
    - type: cultivation_attempt
      result: "效率异常低"

  effects:
    set_flags: [发现灵气异常]
    add_clue:
      storyline: truth
      clue: "某些区域灵气稀薄"

  narrative:
    hint: "你感觉这里的灵气...好像比以前淡了。"

# ----------

event_师父往事:
  id: "truth_010"
  name: "尘封的过去"
  storyline: truth
  tier: opportunity

  window:
    time:
      year_min: 5

  preconditions:
    relationship:
      师父:
        trust: ">=70"
    flags_absent:
      - 知道师父过去

  triggers:
    - type: relationship_threshold
      npc: 师父
      dimension: trust
      threshold: 80
    - type: npc_state
      npc: 师父
      condition: "mood = melancholy"
    - type: time_special
      event: "师父故友忌日"

  effects:
    set_flags: [知道师父过去]
    add_clue:
      storyline: truth
      clue: "师父年轻时有一个至交好友"

  narrative:
    hint: |
      师父喝了点酒，难得地说起往事。
      "很多年前，有个人为我挡了一剑..."

# ========== 真相线：揭露事件 ==========

event_世界真相:
  id: "truth_100"
  name: "残酷的真相"
  storyline: truth
  phase_trigger: "phase_2 → phase_3"
  tier: critical

  preconditions:
    clue_count:
      storyline: truth
      min: 3
    player:
      realm_min: 金丹

  triggers:
    - type: clue_threshold
      storyline: truth
      count: 5
    - type: location_enter
      locations: [上古遗迹, 禁地深处]

  effects:
    set_flags: [知道世界真相]

  narrative:
    revelation: |
      原来，这一切都是...
      飞升者在抽取大陆灵气。
      每一个"成功飞升"的人，都在掠夺这个世界的未来。
      而我们，不过是被圈养的牲畜。
```

### 2.3 被忽略的后果

```yaml
事件过期处理:
  event_玄影初遇:
    expiry: year_8
    consequence:
      description: "玄影主动现身，但态度更傲慢"
      trigger_event: revenge_001b_玄影主动接触
      relationship_penalty:
        玄影: {respect: -10}  # 他认为你不值一提

  event_师父受伤:
    expiry: year_25
    consequence:
      description: "玄影直接对玩家动手，师父来救但更惨"
      world_state_change:
        师父: dead
        set_flags: [师父阵亡]
      player_state:
        karma: -20  # 因果加深

  event_营救阿檀:
    expiry: 30d
    consequence:
      description: "营救失败"
      variants:
        - condition: "玄影线active"
          result: "阿檀被玄影作为要挟，受到伤害"
          effects:
            npc_state: {阿檀: permanently_injured}
            relationship: {阿檀: {trust: -30}}
        - condition: "其他"
          result: "阿檀自己逃脱，但对玩家失望"
          effects:
            relationship: {阿檀: {affection: -20, trust: -20}}

世界态势自动演化:
  每季度检查:
    - 仇人线phase_2且玩家未追杀 → 玄影势力扩张
    - 真相线phase_1且无进展 → 灵气衰竭恶化
    - 阿檀线无互动超过1年 → 关系疏远

  每年检查:
    - 宗门大事件roll
    - 势力消长结算
    - NPC命运变化
```

---

## 三、线索散布系统

### 3.1 线索定义

```yaml
clue_system:
  仇人线线索:
    - id: clue_jade_reaction
      name: "玉佩反应"
      description: "遇到玄影时玉佩微微发热"
      discovery_events: [revenge_001, revenge_002]
      weight: 1

    - id: clue_parent_past
      name: "父母往事"
      description: "从遗物/他人口中得知父母的事"
      discovery_events: [revenge_005, truth_010]
      weight: 2

    - id: clue_enemy_identity
      name: "仇人身份"
      description: "确认玄影就是凶手"
      discovery_events: [revenge_010]
      weight: 3
      收束条件: "此线索触发真相揭露"

  真相线线索:
    - id: clue_qi_decline
      name: "灵气衰退"
      description: "多处发现灵气变薄"
      discovery_count: 3  # 需要发现3次
      weight: 1

    - id: clue_master_secret
      name: "师父的秘密"
      description: "师父似乎知道什么"
      discovery_events: [truth_010]
      weight: 2

    - id: clue_reincarnation
      name: "轮回迹象"
      description: "似曾相识的感觉"
      discovery_events: [truth_050]
      weight: 2

    - id: clue_world_truth
      name: "世界真相"
      description: "飞升者的秘密"
      discovery_events: [truth_100]
      weight: 5
      收束条件: "此线索触发真相揭露"

  收束规则:
    仇人线: "线索权重总和>=5 且 包含'仇人身份' → 可触发决战"
    真相线: "线索权重总和>=8 且 包含'世界真相' → 可触发超脱选择"
```

### 3.2 线索散布点

```yaml
线索散布:
  玉佩相关:
    位置: [玄影身边, 父母遗物, 古老典籍]
    触发: 主动检查/特定事件

  灵气衰竭:
    位置: [偏远地区, 废弃宗门, 枯竭灵脉, 老修士口中]
    触发: 探索/修炼失败/对话

  师父过去:
    位置: [师父住所, 师父酒后, 故友忌日, 旧物]
    触发: 关系提升/特殊时间

  轮回记忆:
    位置: [梦境, 似曾相识的场景, 特定NPC反应]
    触发: 多周目累积/特殊条件
```

---

## 四、隐藏线设计

### 4.1 灵气衰竭线

```yaml
隐藏线_灵气衰竭:
  阶段:
    1. 察觉异常（日常事件散布）
    2. 收集证据（多个线索）
    3. 追查真相（关键NPC/地点）
    4. 揭露（发现飞升者的秘密）
    5. 抉择（接受/反抗/利用）

  线索散布点:
    - 偏远地区修炼效率低（日常）
    - 老修士感叹"不如从前"（对话）
    - 废弃宗门的枯竭灵脉（探索）
    - 高阶修士的闭门讨论（偷听/关系）
    - 古籍记载的"灵气之海"（藏经阁）
    - 飞升者留下的阵法（秘境）

  收束条件:
    - 线索>=5
    - 境界>=元婴
    - 触发"禁地深处"事件

  对世界的影响:
    - 灵气衰竭进度条（后台计算）
    - 每10年恶化一次
    - 影响：修炼效率、渡劫成功率、某些区域荒废
```

### 4.2 轮回秘密线

```yaml
隐藏线_轮回:
  阶段:
    1. 似曾相识（偶发）
    2. 梦境碎片（触发）
    3. NPC异常反应（长期NPC）
    4. 发现真相（多周目）
    5. 打破/接受（最终选择）

  触发条件:
    - 第一周目：极少暗示
    - 第二周目：明显迹象
    - 第三周目：可以主动追查

  线索散布点:
    - 梦中的陌生场景（睡眠事件）
    - 某些NPC初见时的异样表情
    - "我们是不是在哪见过"（对话选项）
    - 轮回阵法的痕迹（秘境）
    - 操控者的线索（真相线收束）

  收束条件:
    - 周目>=2
    - 线索>=4
    - 找到轮回阵法
```

### 4.3 师父过去线

```yaml
隐藏线_师父:
  阶段:
    1. 师父的沉默（日常）
    2. 偶然的往事（关系提升）
    3. 故友的秘密（特殊事件）
    4. 玩家的关联（真相）
    5. 继承/理解（师父死后）

  线索散布点:
    - 师父看玉佩时的表情
    - 师父提到的"老朋友"
    - 师父故友忌日的独饮
    - 师父住所的旧照/信件
    - 其他长辈的暗示

  收束条件:
    - 与师父关系.trust >= 80
    - 触发"师父往事"事件
    - 或：师父临终时告知

  对玩家的影响:
    - 理解师父选择自己的原因
    - 可能获得师父真传
    - 情感更深厚
```

---

## 五、结局系统

### 5.1 结局条件矩阵

```yaml
结局类型:
  主线结局:
    复仇完成:
      condition: "玄影死亡 && 玩家存活"
      变体:
        - 孤独终老（无羁绊）
        - 携手归隐（有道侣）
        - 执掌宗门（声望高）

    原谅放下:
      condition: "玄影存活 && 玩家选择放下"
      变体:
        - 玄影洗心革面
        - 玄影死于他人
        - 玄影再为恶（玩家需再面对）

    万劫不复:
      condition: "玩家走火入魔 || 堕入魔道"
      变体:
        - 被阿檀所杀
        - 杀死阿檀
        - 成为新的玄影

    轮回再起:
      condition: "玩家死亡"
      效果: 开启下一周目

  隐藏结局:
    超脱:
      condition:
        - 真相线phase_4
        - 打破轮回阵法
        - karma >= 50 || 特殊选择
      描述: "跳出命运的循环"

    操控者:
      condition:
        - 真相线phase_4
        - 选择控制轮回
        - karma <= -50
      描述: "成为新的幕后黑手"

    圆满:
      condition:
        - 仇人线和解
        - 阿檀线道侣
        - 师门线传承
        - karma >= 30
      描述: "难得的圆满结局"
```

### 5.2 结局分数计算

```yaml
结局评价:
  羁绊分:
    - 阿檀结局好: +30
    - 师门传承: +20
    - 有生死之交: +15
    - 无人相伴: -20

  因果分:
    - karma值直接影响
    - 正karma: 温暖结局权重增加
    - 负karma: 悲剧结局权重增加

  真相分:
    - 发现世界真相: +20
    - 打破轮回: +50
    - 无知无觉: 0

  综合评价:
    - S级: 总分>=100（极难达成）
    - A级: 总分>=70
    - B级: 总分>=40
    - C级: 总分>=0
    - D级: 总分<0（悲剧向）
```

---

## 六、剧情设计原则

### 6.1 核心原则

```yaml
1. 事件驱动而非剧本驱动:
   - 没有"必须按顺序发生"的剧情
   - 玩家可以错过任何事件
   - 错过有后果，但不是游戏失败

2. 选择真的有重量:
   - 不存在"正确答案"
   - 每个选择都有代价
   - 后果可能延迟很久才显现

3. 角色高于阴谋:
   - 玄影不是符号化的反派
   - 每个NPC都有自己的动机
   - 复杂的人心比复杂的阴谋更重要

4. 遗憾是好的叙事:
   - 不是所有人都能救
   - 不是所有事都能圆满
   - 遗憾才让人记住

5. 时间是残酷的:
   - 闭关十年，世界变了
   - 阿檀不修炼，她会老
   - 机缘错过就是错过
```

### 6.2 情感节奏

```yaml
情感节奏:
  前期（1-5年）:
    - 温暖为主
    - 建立羁绊
    - 小危机小成长
    - 让玩家开始在乎

  中期（5-15年）:
    - 冲突增加
    - 真相浮现
    - 重大选择
    - 情感高峰

  后期（15年+）:
    - 承担后果
    - 最终对决
    - 结局收束
    - 情感释放

  每个阶段保证:
    - 至少1次情感高峰
    - 至少1次重大选择
    - 至少1次失去/获得
```

---

*本文档定义了游戏的剧情系统。核心原则：事件池驱动叙事，玩家选择塑造命运，时间是最残酷的敌人。*

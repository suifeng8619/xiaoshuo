# 世界观设计文档

> 版本: 2.0 - 活世界架构
> 本文档定义世界设定、地理节点、资源经济和场景规则

---

## 第一章：核心理念

这个世界的核心不是"修仙"，而是"人"。

修仙只是背景，真正驱动故事的是：
- 人与人之间的羁绊
- 无法挽回的遗憾
- 必须做出的选择
- 时间带来的改变

---

## 第二章：天元大陆

### 2.1 大陆概览

天元大陆，一片被灵气笼罩的广袤土地。

凡人在这片土地上繁衍生息，而修仙者则追寻长生大道。两个世界看似平行，却又紧密交织——每个修仙者都曾是凡人，每个凡人都可能踏入仙途。

### 2.2 地理格局（宏观）

```
                    【北域·苦寒之地】
                         │
                    ┌────┴────┐
                    │ 万剑峰  │ ← 万剑宗
                    └────┬────┘
                         │
    【西域·荒漠】────┬────┼────┬────【东域·沃土】
                    │    │    │
               ┌────┴────┼────┴────┐
               │         │         │
          幽冥渊      天机城      青云山
          (魔道)     (散修)      (正道)
               │         │         │
               └────┬────┼────┬────┘
                    │    │    │
                    └────┴────┘
                         │
                    【南域·水乡】
```

### 2.3 区域基础属性

```yaml
regions:
  east_domain:
    name: 东域
    description: 灵气最为充沛，正道宗门多聚于此
    base_spirit_density: 1.0  # 基准值
    danger_level: low
    primary_resources: [spirit_stone, herbs, beast_cores]
    factions: [qingyun_sect, lingxu_sect, dazhou_kingdom]

  west_domain:
    name: 西域
    description: 荒漠戈壁，灵气稀薄但藏有上古遗迹
    base_spirit_density: 0.4
    danger_level: high
    primary_resources: [ancient_artifacts, rare_minerals]
    factions: [youming_cult, wandering_cultivators]

  north_domain:
    name: 北域
    description: 苦寒之地，万剑宗独踞于此
    base_spirit_density: 0.7
    danger_level: medium
    primary_resources: [sword_grass, cold_iron, ice_crystals]
    factions: [wanjian_sect]

  south_domain:
    name: 南域
    description: 水网密布，物产丰饶
    base_spirit_density: 0.8
    danger_level: low
    primary_resources: [water_herbs, fish, jade]
    factions: [small_sects, mortal_kingdoms]

  center_domain:
    name: 中域
    description: 天机城，大陆的十字路口
    base_spirit_density: 0.6
    danger_level: medium
    primary_resources: [trade_goods, information]
    factions: [tianji_pavilion, various]
```

---

## 第三章：地理节点系统

### 3.1 节点类型定义

```yaml
location_types:
  sect:
    description: 宗门驻地
    typical_features:
      - 灵气充沛
      - 有防护阵法
      - 有NPC日程表
    examples: [qingyun_sect, wanjian_sect]

  city:
    description: 城镇
    typical_features:
      - 可交易
      - 有任务发布
      - 凡人与修士混居
    examples: [tianji_city, eastern_capital]

  wild:
    description: 野外区域
    typical_features:
      - 有随机遭遇
      - 可采集资源
      - 可能有妖兽
    examples: [qingfeng_forest, broken_valley]

  secret_realm:
    description: 秘境
    typical_features:
      - 定期开启
      - 高风险高回报
      - 有特殊规则
    examples: [ancient_cave, sword_tomb]

  dwelling:
    description: 个人居所
    typical_features:
      - 可休息恢复
      - 存放物品
      - 安全
    examples: [player_cave, atan_quarters]
```

### 3.2 核心节点定义

#### 青云门区域

```yaml
qingyun_sect:
  id: qingyun_main
  name: 青云门
  type: sect
  parent_region: east_domain

  # 基础属性
  spirit_density: 1.2  # 高于区域平均
  danger_level: none   # 门派内部安全
  access_requirement: sect_member

  # 子节点
  sub_locations:
    yunxia_peak:
      id: yunxia_peak
      name: 云霞峰
      description: 云隐子所在的山峰
      spirit_density: 1.3
      npcs: [master_yunyin, senior_suyunfan, junior_linxueyao]
      available_actions:
        - type: train
          description: 修炼
          spirit_bonus: 1.2
        - type: seek_teaching
          description: 求教师父
          available_when: "calendar.is_teaching_day"
        - type: spar
          description: 与同门切磋
          available_when: "time_slot in ['afternoon', 'evening']"

    main_hall:
      id: main_hall
      name: 大殿
      description: 门派议事之处
      spirit_density: 1.0
      npcs: [sect_master, various_elders]
      available_actions:
        - type: attend_meeting
          description: 参加门派会议
          available_when: "has_summons"
        - type: receive_mission
          description: 领取任务
          available_when: "time_slot == 'morning'"

    practice_ground:
      id: practice_ground
      name: 演武场
      description: 弟子修炼比斗之处
      spirit_density: 0.9
      available_actions:
        - type: train_combat
          description: 修炼武技
        - type: challenge
          description: 挑战同门
          available_when: "time_slot == 'afternoon'"
        - type: watch_spar
          description: 观摩比斗

    library:
      id: library
      name: 藏经阁
      description: 存放功法典籍之处
      spirit_density: 1.0
      access_requirement: "player.contribution >= 100"
      available_actions:
        - type: browse_techniques
          description: 查阅功法
          cost: {contribution: 10}
        - type: copy_technique
          description: 抄录功法
          cost: {contribution: 50, time: 3_days}

    herb_garden:
      id: herb_garden
      name: 药园
      description: 种植灵药之处
      spirit_density: 1.1
      available_actions:
        - type: gather_herbs
          description: 采集灵药
          yields: [low_grade_herbs]
          available_when: "has_herb_duty or contribution >= 50"

    market:
      id: sect_market
      name: 坊市
      description: 门派内部交易区
      available_actions:
        - type: buy
          description: 购买物品
          inventory: sect_basic_goods
        - type: sell
          description: 出售物品
        - type: trade_contribution
          description: 贡献点兑换

    kitchen:
      id: kitchen
      name: 膳房
      description: 准备饮食之处
      npcs: [atan]  # 阿檀在此工作
      available_actions:
        - type: eat
          description: 用餐
          effect: {stamina: +20}
        - type: talk
          description: 闲谈
          available_when: "time_slot == 'morning'"

    servant_quarters:
      id: servant_quarters
      name: 杂役住所
      description: 杂役弟子居住之处
      npcs: [atan]
      available_actions:
        - type: visit
          description: 探访
          available_when: "time_slot in ['evening', 'night']"

  # ============ 节点间距离 ============
  # 单位：时辰（1时辰 = 2小时现实时间，1天 = 8时辰 = 4时段）
  # 跨日规则见下方 travel_rules
  travel_times:
    yunxia_peak_to_main_hall: 2      # 2时辰
    yunxia_peak_to_practice_ground: 1
    main_hall_to_library: 1
    practice_ground_to_herb_garden: 2
    herb_garden_to_market: 1
    market_to_kitchen: 1
    kitchen_to_servant_quarters: 1

  # 补充节点
  additional_locations:
    player_cave:
      id: player_cave
      name: 玩家洞府
      description: 玩家在青云门内的居所
      aliases: [我的洞府, 住处]
      spirit_density: 1.0
      travel_from_main_hall: 3
      available_actions:
        - type: meditate
          description: 打坐修炼
        - type: rest
          description: 休息
        - type: store
          description: 存放物品

    back_mountain:
      id: back_mountain
      name: 后山
      description: 青云门后方山区
      aliases: [山后, 后峰]
      spirit_density: 0.9
      danger_level: low
      travel_from_main_hall: 4

    back_mountain_stream:
      id: back_mountain_stream
      name: 后山溪边
      parent: back_mountain
      description: 幽静的溪流边
      aliases: [溪边, 小溪]
      travel_from_back_mountain: 1
      available_actions:
        - type: wash_clothes
          description: 浆洗衣物
        - type: fetch_water
          description: 打水
        - type: rest
          description: 休息发呆

    cloud_peak_top:
      id: cloud_peak_top
      name: 云峰顶
      parent: yunxia_peak
      description: 师父常在此处观云悟道
      aliases: [山顶, 峰顶, 最高处]
      spirit_density: 1.5
      travel_from_yunxia_peak: 1
      note: 重要对话场景

# ============ 旅行规则 ============
travel_rules:
  unit: 时辰  # 所有 travel_time 的单位
  unit_real_world: 2小时

  # 跨时段规则
  cross_slot_calculation: |
    remaining_in_slot = slot_end_tick - current_tick
    if travel_time <= remaining_in_slot:
        # 当前时段内完成
        arrive_in_current_slot()
    else:
        # 溢出到下一时段
        overflow = travel_time - remaining_in_slot
        advance_slots(ceil(overflow / 2))  # 每时段2时辰

  # 跨日规则
  cross_day_rules:
    threshold: 8  # 超过8时辰（1日）视为长途旅行
    treatment: |
      if travel_time >= 8:
          enter_long_action_mode()
          simulate_day_by_day()  # 逐日结算
      else:
          normal_travel()

  # 夜间移动惩罚
  night_travel:
    speed_modifier: 0.5   # 夜间移动速度减半
    danger_modifier: 1.5  # 危险遭遇概率增加
    exception: "筑基以上或有照明法器"

  # 移动方式修正
  modifiers:
    walk: 1.0      # 基准
    fly: 0.2       # 飞行速度是步行5倍
    teleport: 0    # 瞬移（需要传送阵或特殊法器）
```

#### 外部区域

```yaml
qingfeng_forest:
  id: qingfeng_forest
  name: 青风林
  type: wild
  parent_region: east_domain

  spirit_density: 0.8
  danger_level: low
  recommended_realm: "练气期"
  travel_time_from_qingyun: 4  # 4时辰（步行）

  # 区域特性
  features:
    - 初级妖兽出没
    - 可采集低阶灵草
    - 适合新手历练

  # 可用行动
  available_actions:
    - type: explore
      description: 探索林区
      possible_outcomes:
        - encounter_beast: 40%
        - find_herb: 30%
        - find_nothing: 20%
        - discover_secret: 10%

    - type: hunt
      description: 猎杀妖兽
      targets: [wild_boar, spirit_fox, wind_wolf]
      danger: low
      rewards: [beast_cores, pelts]

    - type: gather
      description: 采集灵草
      yields: [spirit_grass, moonflower]
      skill_required: herb_gathering_basic

  # 随机事件池
  random_events:
    - id: lost_disciple
      probability: 0.05
      description: 遇到迷路的同门

    - id: hidden_cave
      probability: 0.02
      description: 发现隐藏洞穴
      requires: "player.perception >= 30"

    - id: beast_tide
      probability: 0.01
      description: 遭遇兽潮
      danger: high

tianji_city:
  id: tianji_city
  name: 天机城
  type: city
  parent_region: center_domain

  spirit_density: 0.6
  danger_level: none  # 城内禁止斗法
  travel_time_from_qingyun: 10  # 10时辰（步行，跨日）

  sub_locations:
    auction_house:
      name: 万宝楼
      description: 大陆最大的拍卖行
      available_actions:
        - type: auction
          description: 参与拍卖
          schedule: "每月十五"
        - type: consign
          description: 寄售物品
          fee: 10%

    info_hall:
      name: 情报阁
      description: 出售各种消息
      available_actions:
        - type: buy_info
          description: 购买情报
          categories: [npc_whereabouts, secret_realm_info, faction_news]

    inn:
      name: 云来客栈
      description: 住宿休息之处
      available_actions:
        - type: rest
          description: 休息
          cost: {spirit_stone: 5}
          effect: {hp: full, stamina: full}
        - type: eavesdrop
          description: 打探消息
          possible_outcomes: [rumors, quest_hints, nothing]

    black_market:
      name: 黑市
      description: 地下交易场所
      access_requirement: "reputation.underworld >= 20"
      available_actions:
        - type: trade_forbidden
          description: 交易禁物
          risk: "被发现则声望下降"
```

### 3.3 秘境节点

```yaml
sword_tomb:
  id: sword_tomb
  name: 剑冢
  type: secret_realm

  # 开启条件
  opening_rules:
    frequency: "每50年开启一次"
    duration: "开启7天"
    next_opening: "year_3_month_6"  # 开局后第3年
    entry_requirement: "realm <= '筑基大圆满'"

  # 内部结构
  layers:
    outer_ring:
      danger: medium
      rewards: [common_sword_techniques]
      encounters: [sword_puppets]

    middle_ring:
      danger: high
      rewards: [rare_sword_techniques, spirit_swords]
      encounters: [sword_spirits]

    core:
      danger: extreme
      rewards: [legendary_inheritance]
      encounters: [ancient_sword_soul]
      accessible_to: "前100名进入者"

  # 特殊规则
  special_rules:
    - "内部时间流速不同（1天=外界7天）"
    - "死亡为真实死亡"
    - "可以组队但奖励分配"
    - "离开后30天内不可再入"
```

### 3.4 补充节点（路段、秘境入口、危险区域）

```yaml
# ============ 路段节点（用于护送/旅行事件）============
escort_routes:
  qingyun_to_tianji_route:
    id: qingyun_to_tianji_route
    type: route
    name: 青云门至天机城商路
    aliases: [护送路段, 商路]
    waypoints: [qingyun_sect, qingfeng_forest, broken_valley, tianji_city]
    total_travel_time: 10  # 时辰
    danger_zones: [broken_valley]

  qingyun_to_sword_tomb_route:
    id: qingyun_to_sword_tomb_route
    type: route
    name: 青云门至剑冢之路
    aliases: [北上之路, 剑冢路]
    waypoints: [qingyun_sect, north_pass, sword_tomb]
    total_travel_time: 20
    danger_zones: [north_pass]

# ============ 秘境入口 ============
secret_realm_entrances:
  sword_tomb_entrance:
    id: sword_tomb_entrance
    type: entrance
    name: 剑冢入口
    aliases: [剑冢门户, 危险秘境入口]
    parent: sword_tomb
    travel_time_from_qingyun: 20
    access_condition: "需要门派令牌或特殊机缘"

  ancient_cave_entrance:
    id: ancient_cave_entrance
    type: entrance
    name: 上古洞府入口
    aliases: [古洞入口, 遗迹入口]
    travel_time_from_qingyun: 15
    access_condition: "需要特定钥匙或阵法知识"

# ============ 危险区域节点 ============
danger_zones:
  broken_valley:
    id: broken_valley
    type: wild
    name: 断魂谷
    aliases: [断谷, 凶险之地]
    travel_time_from_qingyun: 8
    danger_level: medium
    spirit_density: 0.5
    note: "通往天机城的必经之路，常有匪类出没"

  north_pass:
    id: north_pass
    type: wild
    name: 北境隘口
    aliases: [危险山口, 妖兽出没处]
    travel_time_from_qingyun: 12
    danger_level: high
    spirit_density: 0.6
    note: "通往剑冢的必经之路，常有妖兽出没"

  demon_forest:
    id: demon_forest
    type: wild
    name: 幽冥林
    aliases: [黑森林, 魔林]
    travel_time_from_qingyun: 15
    danger_level: extreme
    spirit_density: 0.3
    note: "幽冥宗势力范围边缘"

  abandoned_mine:
    id: abandoned_mine
    type: wild
    name: 废弃矿洞
    aliases: [矿洞, 旧矿, 矿洞节点]
    travel_time_from_qingyun: 6
    danger_level: medium
    note: "可能有宝藏也可能有危险"

# ============ 特殊虚拟节点 ============
special_locations:
  in_transit:
    id: in_transit
    type: special
    name: 旅途中
    description: 长途旅行时的虚拟位置

  personal_cave:
    id: personal_cave
    type: special
    name: 个人洞府
    aliases: [我的洞府, 闭关处, player_residence]
    description: 玩家的私人空间，闭关/休息时的抽象位置
    note: "与player_cave区分：player_cave是青云门内的具体洞府，personal_cave是抽象概念"
```

### 3.5 节点导航规则

```yaml
navigation_rules:
  # 移动消耗
  travel_cost:
    same_location: 0  # 同一地点内子区域
    nearby: 1         # 相邻节点
    distant: "根据距离计算"
    cross_region: "需要飞行法器或传送阵"

  # 移动方式
  travel_methods:
    walk:
      speed: 1
      cost: stamina
      available: always

    fly:
      speed: 5
      cost: spirit_power
      requires: "realm >= '筑基中期' or flying_artifact"

    teleport:
      speed: instant
      cost: {spirit_stone: 100}
      requires: "teleport_token or sect_privilege"

  # 危险区域
  dangerous_travel:
    wild_areas:
      encounter_chance: 0.3
      encounter_types: [beast, bandit, weather]

    forbidden_zones:
      requires: special_permission
      danger: extreme
```

---

## 第四章：资源经济系统

### 4.1 货币体系

```yaml
currency:
  spirit_stone:
    tiers:
      low_grade:
        value: 1
        description: 下品灵石
        common_use: 日常消费

      mid_grade:
        value: 100
        description: 中品灵石
        common_use: 大宗交易

      high_grade:
        value: 10000
        description: 上品灵石
        common_use: 宗门级交易
        rarity: rare

  # 其他货币
  contribution_points:
    description: 宗门贡献点
    earned_by: [missions, sect_duties, donations]
    used_for: [techniques, resources, privileges]
    non_tradeable: true

  reputation:
    description: 各势力声望
    types: [qingyun, wanjian, youming, mortal]
    affects: [access, prices, quests]
```

### 4.2 资源类型

```yaml
resources:
  # 修炼资源
  cultivation_resources:
    spirit_herbs:
      grades: [common, uncommon, rare, epic, legendary]
      use: [alchemy, direct_consumption, trade]
      gather_locations: [herb_garden, wild_areas, secret_realms]
      respawn_time: "根据品阶1天-1年"

    beast_cores:
      description: 妖兽内丹
      use: [alchemy, equipment_upgrade, direct_absorption]
      obtain_from: [hunting, purchase, quest_rewards]

    spirit_ores:
      description: 灵矿
      use: [forging, formation, trade]
      obtain_from: [mining, purchase]

  # 消耗品
  consumables:
    pills:
      categories:
        healing: [recovery_pill, blood_pill]
        cultivation: [qi_gathering_pill, foundation_pill]
        combat: [berserker_pill, defense_pill]
        special: [detox_pill, disguise_pill]

    talismans:
      categories:
        offensive: [fireball_talisman, lightning_talisman]
        defensive: [shield_talisman, escape_talisman]
        utility: [light_talisman, storage_talisman]

  # 装备
  equipment:
    categories:
      weapons: [swords, sabers, flying_swords]
      armor: [robes, inner_armor]
      accessories: [rings, pendants, bracelets]
      artifacts: [flying_artifacts, storage_bags]

    grades: [mortal, spirit, earth, heaven]
```

### 4.3 经济循环

```yaml
economy_flow:
  # 收入来源
  income_sources:
    passive:
      - name: 门派月例
        amount: "50下品灵石/月"
        requirement: sect_member

      - name: 修炼补贴
        amount: "根据境界10-500下品灵石/月"
        requirement: inner_disciple

    active:
      - name: 完成任务
        amount: "variable"
        source: sect_missions

      - name: 猎杀妖兽
        amount: "根据妖兽等级"
        source: hunting

      - name: 采集贩卖
        amount: "variable"
        source: gathering

      - name: 参与事件
        amount: "variable"
        source: story_events

  # 支出项目
  expenses:
    fixed:
      - name: 修炼消耗
        amount: "根据境界30-300下品灵石/月"
        mandatory: true

      - name: 食宿
        amount: "10下品灵石/月"
        mandatory: "if not sect_provided"

    optional:
      - name: 购买丹药
        typical: "100-1000下品灵石/次"

      - name: 学习功法
        typical: "贡献点或任务"

      - name: 装备升级
        typical: "根据品阶"

  # 经济阶层（参考）
  economic_tiers:
    poor:
      monthly_income: "< 100下品灵石"
      description: "勉强维持修炼"

    average:
      monthly_income: "100-500下品灵石"
      description: "稳定修炼，偶尔购买丹药"

    wealthy:
      monthly_income: "500-2000下品灵石"
      description: "资源充足，可以冲击瓶颈"

    rich:
      monthly_income: "> 2000下品灵石"
      description: "可以资助他人，影响门派决策"
```

### 4.4 特殊资源

```yaml
special_resources:
  breakthrough_resources:
    foundation_building_pill:
      description: 筑基丹
      rarity: extremely_rare
      price: "500中品灵石（有价无市）"
      effect: "筑基成功率+30%"
      quest_obtainable: true

    golden_core_catalyst:
      description: 凝丹灵液
      rarity: legendary
      price: "不可购买"
      effect: "金丹品质提升"
      obtain: "秘境或任务"

  plot_items:
    jade_pendant:
      description: 玩家的玉佩
      tradeable: false
      use: "触发身世相关剧情"

    master_sword:
      description: 师父的佩剑
      tradeable: false
      use: "特定剧情触发"
```

---

## 第五章：修仙体系

### 5.1 境界划分

```yaml
cultivation_realms:
  qi_refining:
    name: 练气期
    levels: [1, 2, 3, 4, 5, 6, 7, 8, 9]
    lifespan: 150-200年
    abilities:
      - 感应灵气
      - 基础法术
      - 轻身术（低空飞行）
    breakthrough_to_next:
      requirement: "筑基丹或天赋异禀"
      success_rate: "10%（无丹药）/40%（有丹药）"
      failure_consequence: "重伤，修为倒退"

  foundation_building:
    name: 筑基期
    levels: [初期, 中期, 后期, 大圆满]
    lifespan: 300-500年
    abilities:
      - 御剑飞行
      - 神识外放
      - 中阶法术
    breakthrough_to_next:
      requirement: "悟道机缘 + 资源充足"
      success_rate: "5%基础"
      failure_consequence: "走火入魔风险"

  golden_core:
    name: 金丹期
    levels: [初期, 中期, 后期, 大圆满]
    lifespan: 800-1000年
    abilities:
      - 金丹法力
      - 领域雏形
      - 高阶法术
    title: 真人
    social_status: 宗门长老级

  nascent_soul:
    name: 元婴期
    levels: [初期, 中期, 后期, 大圆满]
    lifespan: 2000-3000年
    abilities:
      - 元婴出窍
      - 法则领悟
      - 空间法则初探
    title: 老祖
    social_status: 一方势力顶梁柱

  deity_transformation:
    name: 化神期
    lifespan: 5000年以上
    abilities:
      - 化神通
      - 天地法则
    title: 传说
    social_status: 大陆屈指可数

  tribulation:
    name: 渡劫期
    lifespan: 万年以上
    abilities:
      - 引动天劫
      - 近乎规则
    title: 老怪物

  mahayana:
    name: 大乘期
    lifespan: 不知其极
    abilities:
      - 几乎全能
      - 可飞升
    title: 神话
```

### 5.2 修炼道路

```yaml
cultivation_paths:
  sword_cultivation:
    name: 剑修
    representative: 万剑宗
    advantages:
      - 战力强，同阶少有敌手
      - 专精单一，突破较快
    disadvantages:
      - 心境要求高，执念太深易入魔
      - 手段单一
    special_abilities: [剑气外放, 剑域, 万剑归宗]

  pill_cultivation:
    name: 丹修
    representative: 灵药阁
    advantages:
      - 丹药无数
      - 朋友遍天下
      - 经济优势
    disadvantages:
      - 战力较弱
      - 需要同伴保护
    special_abilities: [炼丹, 识药, 丹毒]

  talisman_cultivation:
    name: 符修
    advantages:
      - 手段多样
      - 出其不意
    disadvantages:
      - 消耗极大
      - 持久力差
    special_abilities: [画符, 符阵, 符兵]

  body_cultivation:
    name: 体修
    advantages:
      - 防御惊人
      - 越战越勇
    disadvantages:
      - 突破艰难
      - 修炼痛苦
    special_abilities: [金刚不坏, 力量爆发, 肉身成圣]

  soul_cultivation:
    name: 魂修
    advantages:
      - 神出鬼没
      - 防不胜防
    disadvantages:
      - 被视为邪道
      - 容易被围攻
    special_abilities: [神魂攻击, 夺舍, 傀儡术]
```

### 5.3 功法与技能

```yaml
techniques:
  grades:
    mortal: 凡品
    spirit: 灵品
    profound: 玄品
    earth: 地品
    heaven: 天品

  attributes:
    elements: [金, 木, 水, 火, 土]
    special: [阴, 阳, 无属性]

  conflicts:
    description: 某些功法不可兼修
    examples:
      - [pure_yang_art, pure_yin_art]
      - [buddhist_art, demonic_art]

  skill_types:
    combat_skills:
      description: 战斗技能
      examples: [剑法, 拳法, 法术]
      upgrade_by: 使用和修炼

    life_skills:
      description: 生活技能
      examples: [炼丹, 炼器, 阵法, 采药]
      upgrade_by: 实践和学习
```

---

## 第六章：势力格局

### 6.1 正道三宗

```yaml
qingyun_sect:
  name: 青云门
  location: 东域青云山
  realm_strength: 化神期（掌门）
  characteristics:
    - 历史悠久，底蕴深厚
    - 注重心性修养
    - 表面平和，内部派系林立
  rules:
    - 尊师重道
    - 同门不可相残
    - 不可滥杀无辜
  leader: 清虚真人
  philosophy: "道法自然，心正则仙途正"
  player_relation: 玩家所属门派

wanjian_sect:
  name: 万剑宗
  location: 北域万剑峰
  realm_strength: 化神期巅峰（宗主）
  characteristics:
    - 剑修圣地
    - 战力第一
    - 规矩森严，像军队
  rules:
    - 剑不离身
    - 战不退缩
    - 宗门之命高于一切
  leader: 剑尊
  philosophy: "剑之一道，唯快不破，唯心不移"

lingxu_sect:
  name: 灵虚宗
  location: 东域灵虚山
  realm_strength: 化神期（掌门）
  characteristics:
    - 女修居多
    - 擅长幻术和治愈
    - 空灵出尘
  rules:
    - 不可入魔道
    - 不可修邪功
  leader: 灵虚仙子
  philosophy: "红尘炼心，虚极静笃"
```

### 6.2 魔道之首

```yaml
youming_cult:
  name: 幽冥教
  location: 西域幽冥渊
  realm_strength: 化神期（教主，据说在冲击渡劫）
  characteristics:
    - 功法诡异
    - 手段残忍
    - 内部倾轧严重
  rules: 实力为尊，没有规矩
  leader: 幽冥老祖
  philosophy: "天道不仁，我命由我"

  note: |
    魔道不等于邪恶。只是修炼理念不同，更注重突破自我，
    不受世俗道德束缚。但这条路确实容易走偏。
```

### 6.3 其他势力

```yaml
other_factions:
  wandering_cultivators:
    name: 散修
    description: 没有门派的修士
    characteristics:
      - 自由但孤独
      - 资源匮乏
      - 往往需要冒险搏命

  cultivation_families:
    name: 修仙世家
    description: 血脉传承的修仙家族
    characteristics:
      - 资源丰富
      - 规矩多
      - 家族利益高于个人

  mortal_kingdoms:
    name: 凡人王朝
    description: 大周王朝统治凡人世界
    characteristics:
      - 修士一般不干涉凡人事务
      - 凡人权贵会供养修士
```

---

## 第七章：时间与轮回

### 7.1 修士寿命

```yaml
lifespan_table:
  qi_refining: "150-200年"
  foundation_building: "300-500年"
  golden_core: "800-1000年"
  nascent_soul: "2000-3000年"
  deity_transformation: "5000年以上"
  tribulation: "万年以上"
  mahayana: "不知其极"
```

### 7.2 时间的残酷

这是游戏情感的重要来源。

- 你闭关十年突破筑基，出来后青梅竹马已经嫁人
- 你的凡人朋友一个个老去，你却还是少年模样
- 你的仇人寿命将尽，等你有能力报仇时，他已油尽灯枯
- 你苦苦追寻的人，早已飞升离去

时间让一切变得复杂。不是所有事都能等，不是所有人都能陪你走到最后。

### 7.3 轮回设定

```yaml
reincarnation:
  normal_mortals:
    process: 魂归幽冥，转世投胎，前尘尽忘
    memory: none

  cultivators:
    process: 执念太深，可能保留一丝记忆
    memory: "似曾相识的形式"
    effects:
      - 某些人某些事，总觉得在哪见过
      - 某些选择，会下意识做出
      - 某些人对你态度奇怪（上辈子有纠葛）

  game_implication:
    description: 玩家死亡后重新开始的设定基础
    note: 轮回不是简单的"读档"，而是带着因果的重新开始
```

---

## 第八章：世界的真相（隐藏设定）

以下内容玩家在游戏初期不会知道，但会随着剧情逐渐揭露：

```yaml
hidden_truths:
  spirit_qi_decline:
    summary: 灵气在衰减
    detail: |
      天元大陆的灵气正在缓慢枯竭。
      千年前化神期遍地走，如今化神期屈指可数。
      大宗门对此讳莫如深。
    unlock_phase: "truth_phase_3"

    # ============ 灵气衰退数值化 ============
    quantified_decline:
      # 历史基准（千年前=1.0）
      historical_baseline: 1.0

      # 当前（游戏开始时）全大陆平均灵气密度
      current_global_density: 0.65

      # 年度衰减率
      annual_decay_rate: 0.002  # 每年衰减0.2%

      # 分阶段灵气等级表
      spirit_levels:
        level_5_flourishing:
          density_range: [0.9, 1.0+]
          era: "千年前"
          characteristics:
            - 化神期常见
            - 天材地宝遍地
            - 灵兽众多
            - 修炼速度约为当今2倍
          breakthrough_modifier: 1.5  # 突破成功率修正

        level_4_prosperous:
          density_range: [0.7, 0.9)
          era: "五百年前"
          characteristics:
            - 金丹期为主流强者
            - 资源仍算丰富
            - 小型秘境常开
          breakthrough_modifier: 1.2

        level_3_declining:
          density_range: [0.5, 0.7)
          era: "当今（游戏时期）"
          characteristics:
            - 筑基期已是中坚力量
            - 资源紧张，争夺激烈
            - 秘境开放间隔变长
            - 天才出现率下降
          breakthrough_modifier: 1.0  # 基准

        level_2_barren:
          density_range: [0.3, 0.5)
          era: "未来预测（500年后）"
          characteristics:
            - 练气期为主
            - 筑基成功率大幅下降
            - 宗门衰落
          breakthrough_modifier: 0.7

        level_1_desolate:
          density_range: [0.1, 0.3)
          era: "末法时代"
          characteristics:
            - 修仙传承断绝
            - 灵脉枯竭
            - 几近凡人世界
          breakthrough_modifier: 0.3

        level_0_extinct:
          density_range: [0, 0.1)
          era: "灭世"
          characteristics:
            - 无法修炼
            - 修士退化为凡人
          breakthrough_modifier: 0

      # 区域差异修正（叠加全局衰退）
      regional_modifiers:
        east_domain: 1.0      # 基准
        south_domain: 0.95
        center_domain: 0.85
        north_domain: 0.80
        west_domain: 0.55     # 衰退最严重

      # 特殊地点抗衰减
      spirit_veins:
        major_veins:
          examples: [青云山灵脉, 万剑峰剑气, 灵虚山阵法]
          resistance: 0.8     # 只承受全局衰退的80%
        minor_veins:
          examples: [各小宗门灵脉]
          resistance: 1.0     # 无抗性
        secret_realms:
          examples: [剑冢, 上古洞府]
          resistance: 0.0     # 完全隔绝衰退（内部灵气恒定）

      # 游戏机制影响
      gameplay_effects:
        cultivation_speed:
          formula: "base_speed * region_density * (1 - (current_year * annual_decay_rate))"

        breakthrough_success:
          formula: "base_rate * breakthrough_modifier * personal_factors"

        resource_spawn:
          formula: "base_rate * (region_density / 0.65)"  # 以当今为基准

        beast_activity:
          formula: "base_activity * region_density"  # 灵气低则妖兽少

      # 剧情触发条件
      story_triggers:
        notice_decline:
          condition: "wisdom >= 60 or elder_npc_hint"
          unlock: "可以感知到灵气在变淡"

        understand_cause:
          condition: "truth_phase_3 completed"
          unlock: "理解衰退的根本原因"

        find_solution_hint:
          condition: "truth_phase_4 completed"
          unlock: "可能的逆转方法线索"

  ascension_truth:
    summary: 飞升的真相
    detail: |
      没有人知道飞升之后去了哪里。
      有人说是更高的仙界，有人说是虚无，有人说是陷阱。
    unlock_phase: "truth_phase_4"

  reincarnation_master:
    summary: 轮回的主宰
    detail: |
      轮回不是自然规律，而是有人在操控。
      这个"人"是谁？目的是什么？
    unlock_phase: "truth_phase_5"

  player_origin:
    summary: 玩家的身世
    detail: |
      玩家不是普通的孤儿。
      玉佩的秘密将揭开一段被掩埋的历史。
    unlock_phase: "revenge_phase_3"
```

---

## 第九章：世界规则

### 9.1 铁律

```yaml
iron_laws:
  realm_suppression:
    rule: 高两个大境界可以碾压
    detail: |
      高一个大境界，优势明显但可以战。
      同境界内，看天赋、功法、战斗经验。

  karma:
    rule: 因果不虚
    detail: |
      杀人者终被杀。这不是诅咒，是这个世界的运行法则。
      修士修到高处，因果业力会成为心魔，阻碍突破。

  irreversibility:
    rule: 不可逆转
    detail: |
      死了就是死了，没有复活术。
      时间不能倒流，说过的话做过的事无法收回。

  heaven_way:
    rule: 天道无情
    detail: |
      没有谁是主角。实力不够强，就会死。
      选择错了，就要承担后果。
```

### 9.2 灰色地带

```yaml
gray_areas:
  good_evil:
    description: 正魔之分不是绝对的善恶
    detail: 正道也有恶人，魔道也有真性情

  complicated_relations:
    description: 恩怨纠缠
    detail: |
      很少有纯粹的坏人。
      你的仇人也许有自己的苦衷，
      你的恩人也许别有目的。

  dilemmas:
    description: 两难抉择
    detail: |
      常常没有"正确答案"。
      救这个就要牺牲那个，
      成全别人就要委屈自己。
```

---

## 附录：常识速查

### A. 灵石购买力参考

```yaml
purchasing_power:
  low_grade_stone_1:
    equivalent: 普通凡人1月生活费
    can_buy: [5斤米, 1件布衣, 1晚普通客栈]

  low_grade_stone_10:
    equivalent: 练气修士1月基本消耗
    can_buy: [1瓶回气丹, 1本凡品功法, 10天客栈住宿]

  low_grade_stone_100:
    equivalent: 筑基修士1月基本消耗
    can_buy: [1把灵品下等飞剑, 1瓶灵品丹药, 1件下品法袍]

  mid_grade_stone_1:
    equivalent: 100下品灵石
    can_buy: [1把灵品中等武器, 一季度闭关资源]

  mid_grade_stone_500:
    equivalent: 筑基丹市价（有价无市）
```

### B. 修炼日常

```yaml
daily_cultivation:
  routine:
    morning: 吐纳修炼
    noon: 悟道参禅
    afternoon: 修炼武技
    night: 打坐固境

  breakthrough:
    short_retreat: 数日（小境界）
    medium_retreat: 数月（大境界）
    long_retreat: 数十年（重大境界）
```

### C. 礼仪称呼

```yaml
forms_of_address:
  peers: [道友, 师兄, 师姐, 师弟, 师妹]
  elders: [前辈, 师叔, 师伯, 真人]
  juniors: [小友, 贤侄]
  enemies: [妖人, 邪修]
  humble: [在下, 小道, 某]
```

---

*本文档定义了游戏世界的完整规格，包括地理节点、资源经济和世界规则。所有场景、事件、经济系统都必须在此框架内运作。*

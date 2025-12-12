# 正式开发任务列表（给 Claude Code 执行）

> 目标：把 `docs/design/*` 的“活世界”设计逐步落到 `engine/` 主线，实现 **时间推进 → NPC 日程 → 事件池 → 关系/记忆 → AI叙事** 的最小闭环。  
> 约束：保持主线先单 Claude（`engine/ai.py`），`prototype/` 继续作为实验区；一切硬规范以 `docs/design/06_specifications.md` 为准。

---

## Phase 0：基线与工具链（已完成也要复核）

### T0.1 复核密钥与扫描链路
**范围**：`.pre-commit-config.yaml`, `prototype/ai_engine.py`, `engine/ai.py`  
**步骤**
1. 【人工】在 evolink 控制台确认旧 `EVOLINK_API_KEY` 已作废/轮换，新 key 仅通过环境变量注入；完成后在对应 issue 上标记 done。
2. 【ClaudeCode】运行代码侧扫描（`rg "sk-" -S` 等）确认仓库无任何明文 key。
3. 【ClaudeCode】确认 pre-commit 已安装并能拦截 `sk-` 类密钥（可用临时文件模拟提交验证）。
**验证**
- `rg "sk-" -S` 无结果。
- 试提交一个包含 `sk-xxx` 的文件应被 pre-commit 阻止。

### T0.2 复核可运行性
**范围**：`requirements.txt`, `run.py`, `prototype/*`  
**步骤**
1. 新环境 `pip install -r requirements.txt`。
2. 验证三种入口：
   - `python run.py --mock`
   - `python -m prototype.atan`
   - `python -m prototype.atan_hybrid`
**验证**
- 三个入口均能启动到交互提示，无 ImportError/路径错误。

---

> **执行顺序要求（Phase 1–3）**：依赖链为  
> `T1.1 → T1.2 → T1.3 → T2.1 → T2.2 → T3.1 → T3.2 → T3.3`。  
> 必须严格按编号顺序推进；每个任务的“验证”通过后再开始下一项，不要并行或跳做。

## Phase 1：时间系统与世界基础骨架

### T1.1 新增 `GameTime` 与时间换算工具
**文件**：新增 `engine/time.py`，必要时更新 `engine/__init__.py`  
**步骤**
1. 按 `06_specifications.md` 的时间单位定义实现 `GameTime`（年/月/日/时段/时辰 tick/absolute_tick）。
2. 提供：
   - `from_absolute_tick()` / `to_absolute_tick()`
   - `advance_ticks(n)`（推进时辰）
   - `current_slot()` / `slot_remaining_ticks()`
3. 写清楚边界：跨时段、跨日、跨月、跨年。
**验证**
- 加最小单测 `tests/test_time.py`（如无 tests/ 先创建）。
- 断言：
  - 8 ticks = 1 日；240 ticks = 1 月；2880 ticks = 1 年。
  - `advance_ticks` 跨日后 `day+1` 且 slot 重置。

### T1.2 TimeSystem：世界时间推进与日结算钩子
**文件**：新增 `engine/time_system.py`  
**步骤**
1. 包装 `GameTime`，提供 `advance(action_time_cost)`。
2. 在跨日时触发 `on_day_end` 钩子（先空实现，Phase 3/4 填充）。
3. 暴露事件：`time_advanced`, `day_ended`（给 EventBus 使用）。
**验证**
- 运行 `python -c "from engine.time_system import TimeSystem; ..."`  
  模拟推进 10 ticks，确保触发 1 次 `day_ended`。

### T1.3 WorldState 升级：存储时间与位置
**文件**：`engine/state.py`, `engine/game.py`  
**步骤**
1. 在 `GameState.paths` 中新增/统一 `world_state.json` 的结构：包含 `current_time`（absolute_tick 或结构体）与 `player_location`。
2. `Game.start()` 初始化 `TimeSystem` 与 `WorldState`。
3. 任何行动结果都必须推进时间并写回 state。
**验证**
- 启动主游戏 mock 模式，执行几个指令后检查 `data/world_state.json`：
  - `current_time` 单调递增。
  - 位置变化能持久化。

---

## Phase 2：地点图与世界管理器

### T2.1 最小地点/区域配置落地
**文件**：新增 `config/world.yaml`（或 `locations.yaml`）  
**步骤**
1. 从 `01_world.md` 抽取最小可运行集：
   - 至少包含 starter 区域 + 2-3 个相邻节点 + travel_time（单位时辰）。
2. 保持 ID 命名与词表规范。
**验证**
- `scripts/validate_configs.py`（Phase 6）可通过该配置。

### T2.2 WorldManager：空间、可达性、旅行时间
**文件**：新增 `engine/world.py`  
**步骤**
1. 读取 `config/world.yaml` 构建节点图。
2. 提供：
   - `get_location(location_id)`
   - `can_travel(from_id, to_id)`
   - `get_travel_time(from_id, to_id, mode="walk")`
3. 与 `TimeSystem` 对接：旅行行动消耗时辰并触发跨日钩子。
**验证**
- 主游戏中执行 `move`（或新增临时命令）：
  - 旅行时间消耗符合配置。
  - 跨日旅行会触发 day_end。

---

## Phase 3：EventBus 与 NPC 日程

### T3.1 EventBus：发布/订阅基础设施
**文件**：新增 `engine/event_bus.py`  
**步骤**
1. 实现轻量同步 EventBus：`subscribe(event, handler)`、`publish(event, payload)`。
2. World/Time/NPC/Event 系统都通过 EventBus 通信。
**验证**
- 单测：订阅 `day_ended`，推进时间后 handler 被调用 1 次。

### T3.2 NPC 配置与 CharacterManager
**文件**：新增 `config/npcs.yaml`，新增 `engine/characters.py`  
**步骤**
1. 从 `02_characters.md` 抽取核心 NPC 的最小字段：
   - `npc_id`, `name`, `personality_core`, `home_location`, `schedule`, `initial_relationship`。
2. CharacterManager 负责：
   - 加载/存储 NPC
   - 查询当前场景 NPC
   - 提供给 AI 的 `npc_context`。
**验证**
- 启动游戏后 `CharacterManager.all_npcs()` 返回配置里的 NPC。

### T3.3 NPCScheduleEngine：按时段执行日程
**文件**：新增 `engine/schedule.py`  
**步骤**
1. 按 `03_systems.md` 设计实现：
   - `execute_slot(npc, slot, world_state)`
   - 打断规则（优先级、强制事件等先简化）。
2. 在 `TimeSystem.on_day_end` 或每 slot 推进时调用 NPC 日程。
**验证**
- 模拟推进 1 天，检查 NPC 位置/状态按 schedule 更新。
- 输出调试日志（可关）确认执行顺序。

---

## Phase 4：事件池（核心）与剧情阶段标记

### T4.1 事件配置最小集
**文件**：新增 `config/events.yaml`  
**步骤**
1. 【人工/设计审】先通读 `04_story.md`，筛出真正“事件池式”的可复用事件，剔除线性剧本/固定剧情节点，形成候选清单（5–10 条）。
2. 将候选事件落到 `config/events.yaml`（daily/opportunity/critical 各至少 1）。
3. 每个事件含：`id`, `tier`, `window(time/locations)`, `conditions`, `effects`, `interrupt`。
**验证**
- 配置通过 validator；引用的 location/npc/flag ID 全存在。

### T4.2 EventManager：触发检查与选择算法
**文件**：新增 `engine/events.py`  
**步骤**
1. 实现事件池索引与 `check_triggers(world_state, time, flags)`。
2. 选择算法按 `03_systems.md`（先简化：优先级 + 随机权重）。
3. 事件效果写回：flags/关系/世界状态。
**验证**
- 离线模拟：在满足条件的时间/地点推进时，事件能触发且仅触发一次。
- 事件 effects 能被持久化到 `GameState`。

### T4.3 StoryPhase/Flags：阶段标记系统
**文件**：新增 `engine/story.py` 或并入 `events.py`  
**步骤**
1. 实现 flag set/clear/check 与 compound flags。
2. 被事件/时间推进更新；供触发条件查询。
**验证**
- 单测：flag 操作与复合条件判断正确。

---

## Phase 5：关系系统与记忆系统（与原型对齐）

### T5.1 RelationshipSystem：多维度关系与衰减
**文件**：新增 `engine/relationships.py`  
**步骤**
1. 按 `03_systems.md`/`06_specifications.md` 实现 trust/affection/respect/fear 等维度。
2. 每日衰减接入 `TimeSystem.on_day_end`。
3. 提供 `apply_change(npc_id, delta, reason)`，单次变化限制守护栏。
**验证**
- 模拟推进 30 天无互动，关系按月衰减率累计下降。
- 单次事件导致的关系变化被 clamp 到规定范围。

### T5.2 NPC MemorySystem：存储、检索、压缩（主线版）
**文件**：新增 `engine/npc_memory.py`；改造 `engine/memory.py`  
**步骤**
1. 复用原型里的记忆结构（core/recent/summaries）但去掉实验字段。
2. 提供：
   - `add_memory(event, emotion, importance, time)`
   - `retrieve_relevant(query, k)`
   - `should_summarize()` + `summarize_with_ai()`（先用单 Claude 或模板）。
3. `MemoryManager.build_context()` 增加“相关 NPC 记忆摘要”段落。
**验证**
- 与 NPC 对话 5 次后，`recent_memories` 有记录。
- 达到阈值时触发总结并写入 summaries。

---

## Phase 6：AI 输出验证与配置校验

### T6.1 AIValidator：白名单与一致性检查（最小可用）
**文件**：新增 `engine/validator.py`  
**步骤**
1. 在 AI 输出后做轻量校验：
   - 不引入不存在的 npc/location/item/skill ID
   - 不突破硬规则（死亡复活、时间倒流等先做关键项）
2. 违规时降级：改用模板或截断违规句。
**验证**
- 构造包含非法 ID 的 AI 输出，validator 能捕获并降级。

### T6.2 Config Validator 脚本 + CI
**文件**：新增 `scripts/validate_configs.py`，新增 `.github/workflows/ci.yaml`（如已有就补）  
**步骤**
1. 用 pydantic/JSONSchema 校验 `config/*.yaml` 与新 world/npcs/events。
2. CI 中强制跑 validator。
**验证**
- `python scripts/validate_configs.py` 全绿。
- 提交一个野生 ID 配置，CI 失败。

---

## Phase 7：端到端模拟与回归

### T7.1 离线世界模拟器
**文件**：新增 `scripts/simulate_world.py`  
**步骤**
1. 无 AI 模式下随机执行行动 N 天（移动/修炼/休息/对话 stub）。
2. 检查不变量：
   - 时间单调递增
   - NPC 位置可达且不跳图
   - 事件不重复触发
**验证**
- 运行 `python scripts/simulate_world.py --days 30` 无崩溃、输出 invariants 报告为 OK。

### T7.2 最小测试集
**文件**：`tests/`  
**步骤**
1. TimeSystem、EventBus、EventManager、Relationship 衰减四类核心逻辑至少各 1-2 个单测。
**验证**
- `pytest` 全绿。

---

## 最终交付检查（每个 Phase 合并前都跑）
1. `python scripts/validate_configs.py`
2. `pytest`（若 tests 已建立）
3. `python scripts/simulate_world.py --days 7`
4. 手动跑主游戏 mock：执行 move/talk/cultivate 三类指令各一次，确认：
   - 时间推进正确
   - NPC 日程与事件池有输出
   - AI 叙事未引入非法实体

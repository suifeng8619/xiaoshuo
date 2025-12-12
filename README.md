# 仙途 - 文字修仙RPG

> 核心目标：通过AI让玩家真正"在乎"虚拟角色

## 项目定位

这是一个**活的世界**，不是剧本式的固定场景：
- NPC有自己的作息和生活
- 时间在流逝，关系在变化
- 相遇是自然发生的，不是预设触发

## 当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| prototype/ | **开发中** | 情感验证原型（阿檀） |
| engine/ | 框架就绪 | 游戏引擎（规则、状态、AI） |
| config/ | MVP | 基础配置（场景、技能、怪物） |
| docs/design/ | 完成 | 6份设计文档 |

## 快速开始

### 安装

```bash
git clone https://github.com/suifeng8619/xiaoshuo.git
cd xiaoshuo
pip install -r requirements.txt
```

### 运行原型（情感验证）

```bash
# 混合AI版（三大模型路由）
export EVOLINK_API_KEY=your_key
python -m prototype.atan_hybrid

# 单AI版（Anthropic Claude）
export ANTHROPIC_API_KEY=your_key
python -m prototype.atan
```

### 运行主游戏

```bash
# 真实AI模式（使用 evolink 混合路由）
export EVOLINK_API_KEY=your_key
python run.py

# 模拟模式（不消耗API，测试用）
python run.py --mock
```

## 项目结构

```
xiaoshuo/
├── prototype/           # 情感验证原型（实验区）
│   ├── ai_engine.py    # 混合AI引擎（Claude+GPT路由）
│   ├── atan_hybrid.py  # 阿檀 - 混合AI版
│   └── atan.py         # 阿檀 - 单AI版
├── engine/              # 游戏引擎（主线）
│   ├── game.py         # 主循环、命令解析
│   ├── state.py        # 状态管理
│   ├── rules.py        # 规则引擎
│   ├── memory.py       # AI上下文构建
│   └── ai.py           # Claude API封装
├── config/              # YAML配置
│   ├── realms.yaml     # 修仙境界
│   ├── skills.yaml     # 技能定义
│   ├── monsters.yaml   # 怪物配置
│   └── scenes.yaml     # 场景配置
├── docs/design/         # 设计文档
└── data/                # 运行时存档（不提交）
```

## 设计文档

按重要性排序：

1. **[03_systems.md](docs/design/03_systems.md)** - 活世界的运行规则
2. **[05_architecture.md](docs/design/05_architecture.md)** - 技术架构
3. **[06_specifications.md](docs/design/06_specifications.md)** - 硬规范（时间、ID等）
4. **[01_world.md](docs/design/01_world.md)** - 世界观
5. **[02_characters.md](docs/design/02_characters.md)** - 角色设计
6. **[04_story.md](docs/design/04_story.md)** - 事件系统

详见 [docs/index.md](docs/index.md)

## AI架构

### 主线 & 实验区（统一使用 evolink.ai）

主线和原型现在都使用 evolink 混合路由，环境变量：`EVOLINK_API_KEY`

| 任务类型 | 首选模型 | 原因 |
|---------|---------|------|
| 对话/情感 | Claude Opus 4.5 | 角色扮演稳定、情感细腻 |
| 叙事/战斗 | GPT 5.1 | 创意强、画面感好 |
| 记忆/推理 | GPT 5.1 Thinking | 深度思考能力 |

**注意**：`prototype/atan.py` 仍使用原生 Anthropic API（`ANTHROPIC_API_KEY`）

## 开发规范

- 中文注释和文档
- NPC对话用「」，环境描写用【】
- 角色情感真实自然，不过度戏剧化
- 详见 [CLAUDE.md](CLAUDE.md)

## License

MIT

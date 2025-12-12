# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

文字修仙RPG游戏（仙途），核心目标：通过AI让玩家真正"在乎"虚拟角色。

**核心设计理念**：我们要做的是一个**活的世界**，不是剧本式的固定场景。NPC有自己的作息，时间在流逝，相遇是自然发生的。

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行混合AI原型（实验区，三大模型路由）
python -m prototype.atan_hybrid
# 需要设置环境变量：export EVOLINK_API_KEY=your_key

# 运行单AI原型（实验区，使用 Anthropic Claude）
python -m prototype.atan
# 需要设置环境变量：export ANTHROPIC_API_KEY=your_key

# 运行主游戏框架（主线，混合AI路由）
python run.py
# 需要设置环境变量：export EVOLINK_API_KEY=your_key

python run.py --mock  # 模拟模式，不消耗API
```

## 混合AI引擎（evolink.ai）

**API配置**：
- 环境变量：`EVOLINK_API_KEY`
- Claude格式：`https://api.evolink.ai/v1/messages`（Anthropic原生）
- GPT格式：`https://api.evolink.ai/v1/chat/completions`（OpenAI兼容）

**三大模型路由**：

| 任务类型 | 首选模型 | 原因 |
|---------|---------|------|
| 对话/情感 | Claude Opus 4.5 | 角色扮演稳定、情感细腻 |
| 叙事/战斗 | GPT 5.1 | 创意强、画面感好 |
| 记忆/推理 | GPT 5.1 Thinking | 深度思考能力 |

**禁用模型**：Gemini 2.5（质量差）

## 架构

```
xiaoshuo/
├── prototype/           # 情感验证原型（当前开发重点）
│   ├── ai_engine.py    # 混合AI引擎（Claude+GPT路由）
│   └── atan_hybrid.py  # 阿檀角色原型
├── engine/              # 游戏引擎框架
│   ├── game.py         # 主循环、命令解析
│   ├── state.py        # 状态管理（Character, NPC, Quest）
│   ├── rules.py        # 规则引擎（战斗、修炼、境界）
│   ├── memory.py       # AI上下文构建
│   └── ai.py           # 混合AI封装（evolink路由）
├── config/              # YAML配置（修炼、技能、怪物、场景）
├── data/                # 运行时JSON数据
└── docs/design/         # 设计文档
```

## 核心设计文档

按重要性排序：

1. **`docs/design/03_systems.md`** - 最重要！定义活世界的运行规则（时间、关系、记忆系统）
2. **`docs/design/05_architecture.md`** - 技术架构（WorldManager, TimeSystem, EventBus）
3. **`docs/design/01_world.md`** - 天元大陆世界观、修仙体系
4. **`docs/design/02_characters.md`** - NPC人设（阿檀、师父等）

`docs/design/04_story.md` 是剧情大纲，但与"活世界"理念有冲突，需要改造成"事件池"而非线性剧本。

## 代码风格

- 中文注释和文档
- NPC对话用「」，环境描写用【】
- 角色情感真实自然，不过度戏剧化

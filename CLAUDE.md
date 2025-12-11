# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个文字修仙RPG游戏（仙途），核心目标是通过AI让玩家真正"在乎"虚拟角色。

**设计理念**：修仙只是背景，真正驱动故事的是人与人之间的羁绊、无法挽回的遗憾、必须做出的选择。

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主游戏（需要ANTHROPIC_API_KEY）
python3 run.py

# 模拟模式（不消耗API）
python3 run.py --mock

# 运行情感原型（阿檀）
python3 prototype/atan.py

# 运行混合AI版本
python3 prototype/atan_hybrid.py
```

**环境变量**：
- `ANTHROPIC_API_KEY` - Claude API（必需，情感对话）
- `OPENAI_API_KEY` - GPT API（可选，创意叙事）
- `GOOGLE_API_KEY` - Gemini API（可选，长期记忆）

## 架构

```
xiaoshuo/
├── engine/           # 核心游戏引擎
│   ├── game.py      # 主游戏循环、命令解析
│   ├── state.py     # 游戏状态管理（Character, NPC, Quest等）
│   ├── rules.py     # 规则引擎（战斗、修炼、境界）
│   ├── memory.py    # AI上下文构建
│   └── ai.py        # Claude API封装
├── prototype/        # 情感验证原型
│   ├── atan.py      # 阿檀角色原型（单AI）
│   ├── atan_hybrid.py # 混合AI版本
│   └── ai_engine.py  # 混合AI引擎（Claude+GPT+Gemini）
├── config/           # YAML配置（修炼、技能、怪物、场景、任务）
├── data/             # 运行时数据（JSON存档）
└── docs/design/      # 设计文档（世界观、角色、系统、剧情、架构）
```

## 混合AI引擎路由策略

| 任务类型 | 首选AI | 原因 |
|---------|-------|------|
| 对话/情感 | Claude | 角色扮演稳定、情感细腻 |
| 叙事/战斗 | GPT | 创意强、画面感好 |
| 记忆总结 | Gemini | 1M上下文窗口 |

## 关键设计文档

- `docs/design/01_world.md` - 天元大陆世界观、修仙体系
- `docs/design/02_characters.md` - 核心NPC人设（阿檀、师父、仇人等）
- `docs/design/03_systems.md` - 时间、关系、记忆、轮回系统
- `docs/design/05_architecture.md` - 技术架构与实现计划

## 代码风格

- 中文注释和文档
- NPC对话用「」，环境描写用【】
- 角色情感要真实自然，不要过度戏剧化

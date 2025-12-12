# 设计文档索引

本目录包含仙途项目的所有设计文档。

## 阅读顺序

如果你是新加入的开发者，建议按以下顺序阅读：

1. **[06_specifications.md](design/06_specifications.md)** - 硬规范源
   - 时间系统定义（权威）
   - ID命名规范
   - AI边界规则
   - 跨模块引用的唯一真相

2. **[03_systems.md](design/03_systems.md)** - 核心系统设计
   - 时间系统
   - 关系系统
   - 记忆系统
   - NPC日程
   - 事件触发

3. **[05_architecture.md](design/05_architecture.md)** - 技术架构
   - WorldManager
   - TimeSystem
   - EventBus
   - 数据流

4. **[01_world.md](design/01_world.md)** - 世界观
   - 天元大陆
   - 修仙体系
   - 地点系统

5. **[02_characters.md](design/02_characters.md)** - 角色设计
   - 阿檀
   - 师父
   - 其他NPC

6. **[04_story.md](design/04_story.md)** - 事件系统
   - 事件池设计
   - 触发条件
   - 剧情节点

## 文档职责

| 文档 | 职责 | 权威性 |
|------|------|--------|
| 06_specifications | 硬规范定义 | **最高** - 其他文档引用此处 |
| 03_systems | 系统设计逻辑 | 高 - 实现参考 |
| 05_architecture | 代码架构 | 高 - 开发指南 |
| 01_world | 世界观内容 | 中 - 内容创作参考 |
| 02_characters | 角色内容 | 中 - NPC创作参考 |
| 04_story | 事件内容 | 中 - 剧情创作参考 |

## 规范冲突处理

如果发现文档间有矛盾：
1. **06_specifications.md 为准** - 它是唯一真相源
2. 修复其他文档中的错误描述
3. 不要在多处重复定义同一规则

## 实现状态

详见 [实现状态表](#实现状态表)

### 实现状态表

| 模块 | 文档位置 | 代码位置 | 状态 |
|------|---------|---------|------|
| TimeSystem | 03_systems.md, 06_specifications.md | engine/（待实现） | 设计完成 |
| NPC Schedule | 03_systems.md | engine/（待实现） | 设计完成 |
| EventBus | 05_architecture.md | engine/（待实现） | 设计完成 |
| RelationshipSystem | 03_systems.md | engine/（待实现） | 设计完成 |
| MemorySystem | 03_systems.md | prototype/atan*.py | **原型验证中** |
| AI Router | CLAUDE.md | prototype/ai_engine.py | **原型验证中** |
| Rules Engine | - | engine/rules.py | 框架就绪 |
| State Manager | - | engine/state.py | 框架就绪 |
| Save/Load | - | engine/game.py | 框架就绪 |
| Config Validator | 06_specifications.md | scripts/（待实现） | 设计完成 |

### 状态说明

- **设计完成**：文档已定义，代码待实现
- **原型验证中**：在 prototype/ 实验，尚未迁移到主线
- **框架就绪**：基础代码存在，需要与设计对齐
- **已实现**：代码完成且与文档一致

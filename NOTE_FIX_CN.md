# KARMA 代码修复说明（中文版）

本文档记录了 refactor 分支对 NOTE_CN.md 中论文与代码差异的修复情况。

---

## 已修复的差异

### 1. LLM 模型配置 ✅

**对应 NOTE_CN.md 差异 #4**

**问题**：代码使用 `gpt-4o-mini` 和 `all-mpnet-base-v2`，论文声明使用 `GPT-4o` 和 `text-embedding-3-large`。

**修复文件**：
- `configs/api.yaml`
- `configs/default.yaml`
- `karma/config.py`（`APIConfig` 新增 `embedding_model_name` 字段）

**修复内容**：
```yaml
# configs/api.yaml
api:
  model_name: "gpt-4o"
  embedding_model_name: "text-embedding-3-large"
```

现在配置与论文完全一致。

---

### 2. 短时记忆向量检索 ✅

**对应 NOTE_CN.md 差异 #2**

**问题**：
- 短时记忆仅为扁平文本，无向量检索
- 召回仅用物体类型名做关键词匹配，不是 Top-K 向量召回
- 无多模态嵌入、无图像存储、无 VLM 状态

**修复文件**：
- `karma/memory/short_term.py`（新建）
- `karma/memory/__init__.py`（新建）

**修复内容**：

实现 `ShortTermMemory` 类，对齐论文第四节 B 的缓存一致性协议：

- **结构化缓存单元** `MemoryUnit`：包含 object_id、object_type、position、state、image_path、timestamp、frequency
- **多模态嵌入**：`_get_embeddings()` 优先使用 OpenAI `text-embedding-3-large`，回退到 TF-IDF 词向量
- **Top-K 向量召回** `recall(query, top_k)`：对整个短时记忆池做余弦相似度检索，返回 Top-K 最相似的记忆单元
- **ID 合并逻辑**：相同 object_id 的单元会替换旧单元（`frequency` 增加）
- **LRU 淘汰**：超过 `max_size=100` 时保留最新的条目
- **Prompt 文本生成** `to_prompt_text(query, top_k)`：将召回结果格式化为 LLM 可读的文本

```python
# 使用示例
stm = ShortTermMemory(max_size=100, embedding_model="text-embedding-3-large")
stm.add("Apple_1", "Apple", (1.0, 0.9, -0.5), state="clean")
results = stm.recall("wash apple", top_k=3)  # 向量余弦相似度 Top-K 召回
```

---

### 3. 长时记忆图结构（3D Scene Graph）✅

**对应 NOTE_CN.md 差异 #1**

**问题**：
- 长时记忆实现为扁平 3×3 网格，无层级、无邻接边
- 无图结构、无 Area 节点、无拓扑关系

**修复文件**：
- `karma/memory/long_term.py`（新建）
- `karma/memory/__init__.py`（新建）
- `karma/config.py`（`MemoryConfig` 新增配置字段）
- `configs/default.yaml`

**修复内容**：

实现完整的 3D Scene Graph（3DSG）三层结构，对齐论文第四节 A：

```
Floor (floor_1)
  └── Area (area_0, area_1, ...)
        └── Object (Apple_1, Fridge_1, ...)
```

- **FloorNode**：顶层楼层容器
- **AreaNode**：区域节点，包含 `name`、`area_type`、`position`、`contains: [object_id]`、`adjacent_node_ids`
- **ObjectNode**：物体节点，包含 `object_type`、`position`、`pickupable=False`、`properties`
- **拓扑邻接边** `add_area_edge()`：显式编码相邻区域关系
- **BFS 路径搜索** `find_path(start, end)`：基于拓扑图的最短路径
- **自动邻接构建** `_build_adjacency_from_proximity(threshold=3.0)`：基于距离自动建立邻接边

```python
# 使用示例
ltm = LongTermMemory()
ltm.graph.add_area("area_0", "Kitchen", "room", (1.0, 0, -1.5))
ltm.graph.add_area("area_1", "LivingRoom", "room", (-1.0, 0, 0.0))
ltm.graph.add_area_edge("area_0", "area_1")  # 拓扑邻接
ltm.graph.add_object("Apple_1", "Apple", "Apple", "area_0", (1.0, 0.9, -1.5))
path = ltm.graph.find_path("area_0", "area_1")  # BFS: ["area_0", "area_1"]
```

---

### 4. 探索策略优化（基于图的导航）✅

**对应 NOTE_CN.md 差异 #11**

**问题**：`Explore()` 使用暴力穷举搜索 8 个预定义位置，未使用空间结构规划探索路径。

**修复文件**：
- `karma/agents/navigation.py`（修改 `NavigationController.explore()`）
- `karma/agents/robot.py`（修改 `Robot.explore()`，新增长时记忆属性）

**修复内容**：

- `NavigationController.explore()` 新增 `long_term_memory` 和 `current_position` 参数
- 当长时记忆（3DSG）可用时，调用 `LongTermMemory.get_exploration_order()` 获取图引导的探索顺序
- 探索顺序使用 BFS 从最近区域出发，优先探索包含目标物体类型的区域
- `Robot.explore()` 会自动使用已设置的长时记忆（`robot._long_term_memory`）

```python
# 使用示例
ltm = LongTermMemory()
# ... 填充 3DSG ...
robot.set_long_term_memory(ltm)
robot.explore("Apple")  # 自动使用图引导探索
```

---

### 5. 长时记忆选择性召回（TaskDecomposer 集成）✅

**对应 NOTE_CN.md 差异 #5**

**问题**：长时记忆全量文本注入 prompt，无向量检索，无 Top-K 选择。

**修复文件**：
- `karma/planning/task_decomposer.py`（修改 `build_messages()` 和 `decompose()`）
- `karma/config.py`（新增 `long_term_max_areas`、`short_term_recall_top_k` 配置）
- `configs/default.yaml`

**修复内容**：

- `TaskDecomposer.build_messages()` 不再从静态 `prompts/long_term_memory.txt` 读取，而是动态构建 `LongTermMemory`
- 长时记忆调用 `to_prompt_text(query=task_description)` 实现基于任务描述的选择性召回
- 短时记忆通过 `ShortTermMemory.to_prompt_text(query, top_k=3)` 实现 Top-K 向量召回
- 新增 `current_position` 参数支持位置感知的召回
- 支持 `use_short_term_memory` 标志控制是否启用短时记忆召回

```python
decomposer = TaskDecomposer()
messages = decomposer.build_messages(
    task_description="Wash the apple",
    paths=path_resolver,
    use_short_term_memory=True,
    current_position=(0.0, 0.0, 0.0),
)
```

---

## 修复汇总表

| # | 差异 | 严重程度 | 状态 | 修复文件 |
|---|---|---|---|---|
| 1 | 长时记忆：扁平网格 → 3D Scene Graph | 严重 | ✅ 已修复 | `karma/memory/long_term.py` |
| 2 | 短时记忆：文本匹配 → 向量缓存 Top-K | 严重 | ✅ 已修复 | `karma/memory/short_term.py` |
| 3 | 替换策略：追加截断 → LRU + merge | 严重 | ✅ 已修复 | `short_term.py` 内置 |
| 4 | LLM 模型：mini → 完整版 | 高 | ✅ 已修复 | `configs/api.yaml`、`karma/config.py` |
| 5 | 长时召回：全文注入 → 选择性召回 | 高 | ✅ 已修复 | `karma/planning/task_decomposer.py` |
| 11 | 探索策略：暴力搜索 → 图引导导航 | 高 | ✅ 已修复 | `karma/agents/navigation.py`、`robot.py` |
| 12 | 未使用动作 | 低 | ⏳ 未修改 | 可选 |
| 15 | 硬编码路径 | 中 | ✅ 已解决 | 通过 PathResolver 解决 |

---

## 未修复的差异（后续工作）

以下差异因工作量或依赖关系较大，暂未修改：

| # | 差异 | 说明 |
|---|---|---|
| 3 | W-TinyLFU 替换策略 | 当前使用 LRU + merge，可作为后续优化 |
| 6 | VLM 状态分析集成 | 当前短时记忆包含 state 字段但未在召回中深度使用 |
| 7 | ALFRED-L 数据集 | 数据集文件存在但未集成到执行流程 |
| 8 | 评估指标 | 无 SR、MRA、MHR、RE、RT 计算代码 |
| 9 | 基线方法 | CAPEAM、HELPER、LoTa-Bench 未实现 |
| 10 | 真实机器人部署 | UR3 + Cartographer 等无代码 |

---

*2026-04-04 由 Claude Code 修改，记录 refactor 分支对论文与代码差异的修复。*

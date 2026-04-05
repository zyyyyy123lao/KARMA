# KARMA: Paper vs. Code — Differences & Fixes

This document covers discrepancies between the published ICRA 2025 paper and the original codebase, plus the fixes applied in the `refactor` branch.

---

## Summary

| # | Aspect | Paper | Original Code | Status |
|---|--------|-------|--------------|--------|
| 1 | Long-term memory | 3D Scene Graph with topological edges | Flat 3×3 grid, no graph | **Fixed** |
| 2 | Short-term memory retrieval | Multi-modal vector embedding, Top-K cosine | Single-match text similarity | **Fixed** |
| 3 | Memory replacement | W-TinyLFU + Bloom filter | Append + timestamp truncation | LRU + merge (partial) |
| 4 | LLM model | GPT-4o + text-embedding-3-large | GPT-4o-mini + all-mpnet-base-v2 | **Fixed** |
| 5 | Long-term memory recall | Vector retrieval, Top-K selected | Full text injection | **Fixed** |
| 6 | Visual state analysis | Tightly integrated in memory unit | Post-hoc, disconnected | Not fixed |
| 7 | Dataset | 48-task ALFRED-L | Only 4 experience examples | Not fixed |
| 8 | Evaluation metrics | SR, MRA, MHR, RE, RT | No evaluation code | Not fixed |
| 9 | Baselines | CAPEAM, HELPER, LoTa-Bench | None | Not fixed |
| 10 | Real-world deployment | UR3 + Cartographer | No code | Not applicable |
| 11 | Exploration strategy | Graph-informed navigation | Brute-force sequential | **Fixed** |
| 12 | Skill implementations | All skills functional | Some unused/dead code | Not fixed |
| 13 | FIFO merge improvement | ID-based queue replacement | Dict last-write-wins | LRU + merge (partial) |
| 14 | Third-party camera | Not in paper | Added for top-view | Accepted |
| 15 | Path configuration | Not discussed | Hardcoded paths | **Fixed** (PathResolver) |

---

## Key Differences (Original Code)

### Long-Term Memory (#1)
**Paper**: 3D Scene Graph — Floor → Area nodes (with adjacency edges) → Object nodes. Explicit topological graph for navigation.

**Code**: Flat list of 9 grid centers. No area IDs, no adjacency edges, no graph traversal.

### Short-Term Memory (#2)
**Paper**: Each unit = (world coords, VLM state, image). Full pool vectorized via multi-modal embedding. Recall = cosine similarity over all units, Top-K selected.

**Code**: Flat `(objectType, position, objectId)` tuples. No image, no vector, no cosine similarity. Retrieval = keyword match on object type name only.

### Memory Replacement (#3)
**Paper**: W-TinyLFU — window segment + main segment, counting Bloom filter for frequency.

**Code**: Append new entries, truncate to 100 most recent (timestamp-based LRU). No frequency tracking, no Bloom filter.

### LLM Model (#4)
**Paper**: GPT-4o + text-embedding-3-large.

**Code**: GPT-4o-mini + all-mpnet-base-v2.

### Long-Term Recall (#5)
**Paper**: Vector retrieval — top-K most similar memories selected.

**Code**: Full `long_term_memory.txt` injected as plain text every time. No vector search.

### Exploration (#11)
**Paper**: 3DSG topology enables efficient, planned exploration paths.

**Code**: Fixed list of 8 positions searched sequentially. No spatial planning.

---

## Fixes Applied (Refactor Branch)

### #1 — 3D Scene Graph → `karma/memory/long_term.py`

Full 3DSG structure implemented: `FloorNode` → `AreaNode` (with `adjacent_node_ids`) → `ObjectNode`. BFS path finding between areas. Auto-builds adjacency from proximity.

```python
ltm = LongTermMemory()
ltm.graph.add_area("area_0", "Kitchen", "room", (1.0, 0, -1.5))
ltm.graph.add_area_edge("area_0", "area_1")  # topological edge
path = ltm.graph.find_path("area_0", "area_1")  # BFS
```

### #2 — Vector Cache → `karma/memory/short_term.py`

`ShortTermMemory` class: structured `MemoryUnit` (object_id, type, position, state, image_path, timestamp, frequency). OpenAI `text-embedding-3-large` for vectorization. `recall(query, top_k)` returns cosine Top-K matches. LRU eviction + ID-merge on conflict.

```python
stm = ShortTermMemory(max_size=100)
stm.add("Apple_1", "Apple", (1.0, 0.9, -0.5), state="clean")
results = stm.recall("wash apple", top_k=3)  # vector cosine Top-K
```

### #4 — Model Upgrade → `configs/api.yaml`, `karma/config.py`

Config updated to `model_name: "gpt-4o"` and `embedding_model_name: "text-embedding-3-large"`.

### #5 — Selective Recall → `karma/planning/task_decomposer.py`

`TaskDecomposer.build_messages()` now dynamically builds long-term memory via `to_prompt_text(query)`. Short-term via `ShortTermMemory.to_prompt_text(query, top_k=3)`. No more static file injection.

### #11 — Graph-Guided Exploration → `karma/agents/navigation.py`

`NavigationController.explore()` accepts `long_term_memory` and `current_position`. When 3DSG is available, calls `get_exploration_order()` to prioritize areas containing the target object.

```python
robot.set_long_term_memory(ltm)
robot.explore("Apple")  # graph-guided order
```

### #15 — Path Configuration → `karma/utils/path.py`

`PathResolver` replaces all hardcoded `/home/user/wzx/karma/`. Config-driven relative paths. `configs/default.yaml` centralizes all path settings.

---

## Remaining Work

- W-TinyLFU replacement policy (currently LRU + merge)
- VLM state analysis integrated into memory pipeline
- ALFRED-L dataset integration
- SR / MRA / MHR / RE / RT evaluation code
- Baseline methods (CAPEAM, HELPER, LoTa-Bench)
- Real-world UR3 + Cartographer deployment

---


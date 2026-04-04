# KARMA: Paper vs. Code Inconsistencies

This document details discrepancies and gaps between the published KARMA paper (*KARMA: Augmenting Embodied AI Agents with Long-and-Short Term Memory Systems*, ICRA 2025) and the actual codebase at `d:\KARMA`.

---

## 1. Long-Term Memory: 3D Scene Graph vs. Simple Area List

### Paper (Section IV-A)
Long-term memory is described as a **3D Scene Graph (3DSG)** with a hierarchical structure:

- **Three-level hierarchy**: Floor → Area nodes (evenly distributed in reachable regions) → Object nodes (attached to area nodes)
- Area nodes include: `name`, `type: Area`, `contains: [...]`, `adjacent nodes: [...]`, `position: [x, y, z]`
- Edges between adjacent area nodes are explicitly encoded as `{node 1 ↔ node 2, node 1 ↔ node 8}`
- The paper explicitly states the 3DSG uses a **topological graph** structure with sparse nodes to mitigate accumulated drift errors vs. dense semantic maps
- Only **immovable/pickupable=False** objects are stored as object nodes with detailed attributes (volume, 3D position)
- 3DSG is built incrementally via environment exploration

### Code (`longterm_save.py` + `execute_LLM_plan.py`)
Long-term memory is implemented as a **flat list of spatial regions**, NOT a graph:

- `get_divided_positions()` divides reachable space into a **3×3 grid** (9 fixed centers), not a topological graph
- `get_static_objects_in_regions()` assigns static objects to the nearest grid center
- The output `longterm_memory.json` contains only `{center: [(objectType, position), ...]}`, **no adjacency information**
- The `prompts/long_term_memory.txt` output is: `"center (-1.0, 0.00, -1.5) has {Cabinet, Cabinet, ...}"` — flat, no edges or topology
- **No graph structure whatsoever**: no floors, no area nodes with IDs, no adjacent node relationships, no object volume attributes

### Impact
The paper's 3DSG with explicit topological edges is the central architectural claim of long-term memory. The code stores only a 9-region flat partition with no graph traversal capability. The adjacency information that enables efficient navigation and the hierarchical structure that enables incremental growth are both entirely absent.

---

## 2. Short-Term Memory: Cache with Vector Embedding vs. File-Based Text Matching

### Paper (Section IV-B)
Short-term memory follows a **cache/coherence protocol**:

- Each memory unit = (world coordinates, VLM-generated state, raw image) — a **structured cache line**
- Memory units are **vectorized** via a pre-trained **multi-modality embedding model** (text+image → vector)
- Recall uses **vector similarity** (cosine distance) over the full short-term memory pool
- **Top-K** most similar memory units are retrieved based on cosine distance to the embedded instruction
- Only **one unit of short-term memory** is selected per query in the extended prompt

### Code (`query_with_short_term_memory.py`)
Short-term memory is **NOT** a vector cache:

- `memory3.json` stores only `(objectType, position, objectId)` — **no image, no VLM-generated state** (state is added later in a hacky post-process)
- No multi-modality embedding model is used for short-term memory recall
- No cosine similarity over short-term memory vectors
- Retrieval is **single-best**: only **one** matching item is selected (not Top-K, though the code structure implies K=1)
- The retrieval actually works by: (1) extracting the task noun from `instruction.txt` via string parsing, then (2) computing cosine similarity between the task noun and `memory3.json` object types — **not the full memory unit**, just the object type name
- No raw image is stored in or retrieved from short-term memory
- The `state` field is added to `memory3.json` only via a post-hoc `update_memory_with_state()` call, after the retrieval step, meaning **retrieval never uses state**

### Impact
The paper's short-term memory is a vectorized multi-modal cache. The code implements a simple text-similarity lookup over an object list. The multi-modality embedding, image storage, and Top-K vector recall are all missing.

---

## 3. Memory Replacement Policy: W-TinyLFU vs. Merge-Then-Append

### Paper (Section IV-D)
Short-term memory replacement uses **W-TinyLFU** (Window TinyLFU):

- Two segments: **window segment** + **main segment** (with protection and elimination sub-segments, both LRU)
- **Counting Bloom filter** for frequency counting
- Global counter reset: when counter reaches threshold W, all counters are halved (`ci ← ci/2`)
- Comparison happens among all units in window segment and elimination segment to pick the minimal-frequency eviction candidate
- Paper evaluates FIFO and W-TinyLFU on `ALFRED-R` dataset, showing W-TinyLFU achieves higher memory hit rate

### Code (`memory_save.py` + `execute_LLM_plan.py`)
No W-TinyLFU, no FIFO, no frequency counting, no Bloom filter:

- `compare_objects_location()` simply **appends** new position-differing objects to `memory3.json`
- If `memory3.json` exceeds `max_objects=100`, it keeps the **most recent** entries (sorted by `timestamp` in a **Reverse-LRU** style, not frequency-based)
- There is **no merging of same object ID** unless explicitly checking before appending (the merge comment exists in code but the actual `compare_objects_location()` only appends and truncates by recency)
- No counting Bloom filter, no frequency statistics, no window/main segment structure

### Impact
W-TinyLFU is a core contribution of the paper (Section IV-D). The code implements a naive timestamp-based truncation with no frequency tracking, no Bloom filter, and no W-TinyLFU structure whatsoever.

---

## 4. LLM Model: ChatGPT-4o vs. GPT-4o-mini

### Paper (Section V-A)
> "we leverage **ChatGPT-4o** as the high-level task planner"

> "we utilize OpenAI's **text-embedding-3-large** model for memory recall"

### Code (`llm_as_planner.py`)
```python
response = openai.ChatCompletion.create(
    model="gpt-4o-mini-2024-07-18",  # NOT gpt-4o
    ...
)
```
And in `query_with_short_term_memory.py`:
```python
model = SentenceTransformer('all-mpnet-base-v2')  # NOT text-embedding-3-large
```

### Impact
The code uses significantly cheaper/smaller models: GPT-4o-mini instead of GPT-4o, and `all-mpnet-base-v2` instead of `text-embedding-3-large`. This likely affects the quality of both planning and memory recall, contradicting the paper's stated configuration.

---

## 5. Long-Term Memory Embedding: Full Text vs. Vector Retrieval

### Paper (Section IV-C)
> "KARMA retrieves the **top-K most similar memories** — those with the smallest cosine distance to the embedding of the input instruction"

Both long-term and short-term memory use **vector embedding** for retrieval. The planner prompt includes:
- Full long-term memory text (entire 3DSG)
- **Top-K** short-term memory units (via vector similarity)

### Code (`llm_as_planner.py`)
- Long-term memory: `long_term_memory.txt` is **directly injected as plain text** into the prompt — **no vector retrieval**, the entire memory is included regardless of relevance
- Short-term memory: **only one** (K=1) best match is injected — not Top-K
- The similarity flag logic uses **keyword matching** (`similarity_report`) instead of vector similarity

### Impact
The paper's retrieval-augmented approach (vector similarity + Top-K selection) is partially implemented: full long-term memory is always included, short-term memory uses a single-match instead of Top-K, and the matching is keyword-based rather than embedding-based.

---

## 6. Visual State Analysis: Task-Specific VLM vs. Generic Post-Hoc Analysis

### Paper (Section IV-B)
> "the VLM is fed **both the task and the image** to handle multiple objects in the image"

The vision-language model is tightly integrated into the short-term memory pipeline:
1. Image captured → VLM analyzes → extracts **state of Object of Interest (OOI)**
2. State is part of the memory unit `(world coordinates, state, image)`

### Code (`execute_LLM_plan.py` + `query_with_short_term_memory.py`)
- `analyze_image()` is called **after** `PutObject` action completes
- The VLM prompt asks for object state classification (cleaned/sliced/etc.), but this happens **too late** to be part of the memory unit that would guide the current task
- The analyzed state is written to `analysis_results.json` and **only later** merged back into `memory3.json` via `update_memory_with_state()`
- The state analysis is **not task-specific**: the task description is passed, but the short-term memory retrieval for the NEXT task uses **only object type** similarity, not state
- No raw image is stored alongside the memory unit

### Impact
The paper integrates VLM state analysis as a core part of the short-term memory unit. The code performs a disconnected, post-hoc visual analysis whose results are not effectively used in the retrieval pipeline.

---

## 7. Dataset: ALFRED-L (48 tasks) vs. Single JSON Files

### Paper (Section V-A)
ALFRED-L dataset:
- **48 high-level instructions** total: 15 Simple + 15 Composite + 18 Complex tasks
- `ALFRED-R` (a separate dataset) for evaluating memory replacement policy
- Dataset described as supplementary material

### Code (`ALFRED_L/`)
- `simple_tasks.json`, `composite_tasks.json`, `complex_tasks.json` exist but **are never loaded or used** anywhere in the codebase
- No dataset loading, splitting, or evaluation pipeline
- `experience/experience.json` has only **4 hand-crafted examples** — far fewer than the 48-task dataset

### Impact
The paper's evaluation uses a structured 48-task dataset with clear categorization. The code's dataset files are present but completely disconnected from the execution pipeline, and the experience pool has only 4 examples.

---

## 8. Evaluation Metrics: Full Suite vs. No Evaluation Code

### Paper (Section V-B)
Four metrics are evaluated:
- **Success Rate (SR)**: task fully completed
- **Memory Retrieval Accuracy (MRA)**: binary, memory successfully retrieved
- **Memory Hit Rate (MHR)**: hit ratio for short-term memory
- **Reduced Exploration (RE)**: exploration attempts reduced
- **Reduced Time (RT)**: time saved during execution

Results are reported in Table I and Table II, with ablation studies.

### Code
- **No evaluation code whatsoever**: no SR calculation, no MRA, no MHR, no RE, no RT
- No success/failure detection
- No metric logging or reporting
- The `logs/` directory stores task descriptions and generated functions but no evaluation results

### Impact
The paper presents quantitative results demonstrating 1.3×–2.3× improvements. None of these metrics are computed in the codebase.

---

## 9. Baseline Comparisons: CAPEAM, HELPER, LoTa-Bench vs. Not Implemented

### Paper (Section V-A)
KARMA is compared against:
- **CAPEAM**: context-aware planning + environment-aware memory
- **HELPER**: retrieval-augmented prompts with scalable external memory
- **LoTa-Bench**: probability-based skill selection

### Code
- None of these baseline methods are implemented or referenced in the code
- The code only implements KARMA itself

### Impact
The paper's key contribution — outperforming state-of-the-art baselines by significant margins — cannot be validated because the baselines are not present.

---

## 10. Real-World Deployment: Mobile Manipulation Robot vs. No Deployment Code

### Paper (Section VI-B)
KARMA is deployed on a real robot:
- **UR3 robotic arm** + six-wheeled chassis
- **Google Cartographer** SLAM for navigation
- **LangSAM** for object segmentation and semantic matching
- **AnyGrasp** for grasp planning

### Code
- No real-world deployment code, no SLAM integration, no hardware interfaces
- Only AI2-THOR simulation is present

### Impact
The paper's plug-and-play real-world deployment claim (Section I) with detailed system integration (Section VI-B) has no corresponding code.

---

## 11. Exploration Strategy: Semantic Map Navigation vs. Brute-Force Point-by-Point

### Paper (Section IV-A)
Long-term memory enables **informed navigation**: agent knows area topology, so it can plan efficient exploration paths and avoid redundant exploration.

### Code (`execute_LLM_plan.py`)
`Explore()` and `ExploreObject()` use **brute-force sequential search**:
- Iterates through a fixed list of `(8)` predefined positions
- At each position, checks if target is within 1.5m distance
- Does NOT use long-term memory spatial structure to plan exploration order
- The `available_positions` list in the generated code is hardcoded, not derived from the 3DSG/topological graph

### Impact
Despite the paper's claim that the 3DSG enables efficient navigation, the exploration code ignores spatial structure entirely and performs exhaustive point-by-point search.

---

## 12. Action Set: Paper Lists `DropHandObject`, `PushObject`, `PullObject` vs. Not Used

### Code (`execute_LLM_plan.py`)
The `robots` definition includes: `['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'SwitchOn', 'SwitchOff', 'PickupObject', 'PutObject', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject']`

However:
- `DropHandObject` is **never called** anywhere in the codebase
- `PushObject` and `PullObject` are defined in `resources/actions.py` but **never implemented** in `execute_LLM_plan.py`
- `GoToObject_with_memory()` and `GoToObject_next_time()` are **never called** from generated task functions (the generated code only uses `GoToObject`, `Explore`, `PickupObject`, `PutObject`, `SwitchOn/Off`, etc.)

### Impact
Several declared skills are unused or unimplemented. The multi-version navigation functions (`GoToObject_next_time`, `GoToObject_with_memory`) designed to utilize different memory sources are dead code.

---

## 13. FIFO Improvement (Merging) Described in Paper vs. Not in Code

### Paper (Section IV-D)
> "We improve the FIFO policy by adding a **merging option**. When a new memory unit needs to join the queue, we first check all memory units for a **matching object's ID**. If a match is found, the new unit will replace the existing one."

### Code (`memory_save.py`)
The comment in `compare_objects_location()` mentions merging:
```python
# The merging approach: if object_id already exists, update position
# But the actual implementation just appends and truncates:
merged_data = output_data + differences
unique_objects = {}
for obj in merged_data:
    obj_id = obj['objectId']
    unique_objects[obj_id] = obj  # Later entries overwrite earlier ones by objectId
```
The `unique_objects` dict does implement ID-based deduplication (last-write-wins), which is effectively the merge. However:
- The merge only happens by object ID — **no state merging logic**
- No timestamp or recency management beyond the 100-entry cap
- The FIFO-with-merge described in the paper (a proper queue where existing entries are replaced by matching ID) is only approximately implemented

---

## 14. Third-Party Camera (Top-Down View) vs. Paper's Approach

### Code (`execute_LLM_plan.py`)
```python
event = c.step(action="GetMapViewCameraProperties")
event = c.step(action="AddThirdPartyCamera", **event.metadata["actionReturn"])
```
A top-down third-party camera is explicitly added to the AI2-THOR scene. This is used to generate bird's-eye view videos.

### Paper
Does not mention using a third-party camera. The paper discusses agent first-person view and the 3DSG reconstruction approach, but no explicit top-down surveillance camera.

### Impact
Minor — this is an auxiliary visualization feature, not a core architectural component. However, it is not mentioned in the paper.

---

## 15. Hardcoded Paths: `/home/user/wzx/karma/` Throughout

The code contains hardcoded absolute paths throughout:
- `llm_as_planner.py`: `/home/user/wzx/karma/...`
- `execute_LLM_plan.py`: `/home/user/wzx/karma/...`
- `query_with_short_term_memory.py`: `/home/user/wzx/karma/...`
- `longterm_save.py`: `/home/user/wzx/karma/...`
- `mapping.py`: `/home/user/wzx/karma/...`

This makes the code completely non-portable. The paper does not discuss portability or deployment configuration, but this is a practical issue for reproducing results.

---

## Summary Table

| # | Aspect | Paper (Claimed) | Code (Actual) | Severity |
|---|---|---|---|---|
| 1 | Long-term memory structure | 3D Scene Graph with topological edges, 3-level hierarchy | Flat 3×3 grid, no graph, no adjacency | **Critical** |
| 2 | Short-term memory retrieval | Multi-modality vector embedding, Top-K cosine similarity | Single-match text similarity over object types only | **Critical** |
| 3 | Memory replacement policy | W-TinyLFU with Bloom filter + frequency counting | Naive append + timestamp-based truncation | **Critical** |
| 4 | LLM model | GPT-4o + text-embedding-3-large | GPT-4o-mini + all-mpnet-base-v2 | **High** |
| 5 | Long-term memory recall | Vector retrieval, Top-K selected | Full text injection, no vector search | **High** |
| 6 | Visual state analysis | Integrated into short-term memory unit pipeline | Post-hoc analysis disconnected from retrieval | **High** |
| 7 | Dataset | 48-task ALFRED-L + ALFRED-R for replacement eval | 4 hand-crafted examples in experience.json | **High** |
| 8 | Evaluation metrics | SR, MRA, MHR, RE, RT with tables | Zero evaluation code | **Critical** |
| 9 | Baselines | CAPEAM, HELPER, LoTa-Bench implemented | None implemented | **High** |
| 10 | Real-world deployment | UR3 arm + Cartographer SLAM + LangSAM + AnyGrasp | No deployment code | **Medium** |
| 11 | Exploration strategy | Graph-informed efficient navigation | Brute-force sequential search | **High** |
| 12 | Skill implementations | All skills functional | Some unused, multi-version nav dead code | **Low** |
| 13 | FIFO merge improvement | Queue with ID-based replacement | Approximate via dict last-write-wins | **Low** |
| 14 | Third-party camera | Not mentioned | Added for top-view video generation | **Low** |
| 15 | Path configuration | Not discussed | Hardcoded `/home/user/wzx/karma/` everywhere | **Medium** |

---

*Generated on 2026-04-03 by Claude Code analysis of the KARMA repository against the ICRA 2025 paper.*

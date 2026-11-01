# 双脑记忆系统：从神经机制到多模型模拟方案

**Dual-Brain Memory System: From Neural Mechanisms to a Multi-Model Simulation Approach**  
Version 2.1 · 2026

> **状态：思路稿。**  
> 本仓库记录的是一条构建思路，不是已落地的框架、产品，也不是经过验证的实践。文档讨论记忆、关系与多模型分工可以如何组织，不声称已经给出完整架构或实现。`runtime/` 只是对部分契约的参考探针，不代表框架本身。

> **Status: a conceptual note.**  
> This repository records a line of thinking, not a framework, product, or validated practice. It explores how memory, relationships, and multi-model division might be organized; it does not claim a complete architecture or implementation. The `runtime/` directory is a small reference probe for selected contracts, not the framework itself.

## 我们要解决的问题

今天的大模型不是“记不住”，而是**记住了也不会用**。

1. **上下文越大，判断越差。**  
   把更多历史塞进上下文，不会让模型更懂当前情况；它会被无关信息稀释，被相似但不相干的内容带偏。缺的不是“更多记忆”，而是“此刻真正相关的那几块”。

2. **现有记忆方案记的是对话，不是关系。**  
   向量库能回答“哪段话最像”，但回答不了：这个人是谁、个体与他是什么关系、共同经历过什么、哪些是事实、哪些是解释、哪些承诺还没履行。人物与事件的对应，才是关系与记忆的原点。

3. **模型没有跨时间的连续身份。**  
   每次对话从零开始，记得的只是“这次说了什么”，不是“彼此之间发生过什么”。陪伴型产品最需要的不是更多知识，而是记得关系、记得承诺、记得共同经历。

4. **记忆不可审计。**  
   来源不明、转述当亲历、解释覆盖事实、冲突被平均、遗忘与删除不分。一个不能说明“凭什么记得”的系统，无法承担长期关系。

5. **多模型协作容易变成委员会。**  
   后台都能建议、都能行动，最后没人对后果负责。分工不是目的；分工之后仍然只有一个整合与决策中心，才是目的。

## Documents

| Language | HTML | PDF |
|---|---|---|
| 中文 | [dual-brain-memory-system-v2.1-zh.html](docs/zh/dual-brain-memory-system-v2.1-zh.html) | [dual-brain-memory-system-v2.1-zh.pdf](docs/zh/dual-brain-memory-system-v2.1-zh.pdf) |
| English | [dual-brain-memory-system-v2.1-en.html](docs/en/dual-brain-memory-system-v2.1-en.html) | [dual-brain-memory-system-v2.1-en.pdf](docs/en/dual-brain-memory-system-v2.1-en.pdf) |

## Reference Implementation (Reference Only)

This repository includes the scripts used to build the documents and a small in-memory reference implementation. They are included for transparency and reproducibility — **not** as a production system.

| Path | Purpose |
|---|---|
| `source/zh/build.py` | Build the Chinese HTML from `source/zh/parts` |
| `source/en/build.py` | Build the English HTML from `source/en/parts` |
| `source/zh/parts/` | Chinese source fragments |
| `source/en/parts/` | English source fragments |
| `runtime/` | In-memory reference implementation |
| `docs/zh/`, `docs/en/` | Built HTML / PDF |

`runtime/` contains the executable counterpart of selected contracts:

- `state_params.py` — event-derived state → bounded runtime parameters
- `memory.py` — retrieval, `ContextPacket`, `omitted`, budget
- `ledger.py` — evidence ledger, version chain, retention
- `constitution.py` — proposals, co-signature, ratification ledger
- `segmentation.py` — event boundaries
- `relationship.py` — multi-dimensional relationships, affect/trust separation
- `reliability.py` — source reliability
- `simulation.py` / `primitives.py` — compositional replay and primitive library
- `graph_retrieval.py` — lightweight association index
- `pipeline.py` — end-to-end audit trace

```bash
cd runtime
python3 -m unittest -v      # 128 tests
python3 pipeline.py         # end-to-end JSON with audit trace
```

## What this is not

- It is **not** a framework: the document describes a line of thinking, not a complete architecture.
- It is **not** a product or a validated practice; no production deployment is claimed.
- It is **not** a clinical or neuroscience claim; neuroscience is used to explain design rationale.
- The `runtime/` code is **not** a production system: no real persistence, signing keys, distributed writer, or production-grade ratification ledger.
- The API and schema are **not stable**; they exist to make selected contracts testable and reviewable.
- The repository does **not** include the GitHub token, QA renders, or temporary build artifacts.

## License

No open-source license is granted in this release; all rights reserved. Contact the author for reuse.

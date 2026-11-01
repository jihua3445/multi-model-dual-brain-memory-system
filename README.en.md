# Dual-Brain Memory System: From Neural Mechanisms to a Multi-Model Simulation Approach

**双脑记忆系统：从神经机制到多模型模拟方案**  
Version 2.1 · 2026

> **Status: a conceptual note.**  
> This repository records a line of thinking, not a framework, product, or validated practice. It explores how memory, relationships, and multi-model division might be organized; it does not claim a complete architecture or implementation. `runtime/` is a small reference probe for selected contracts, not the framework itself.

[中文 README](README.md)

## Why this project

**1. A single model cannot hold “one continuous person.”**  
A person’s continuity is not one conversation; it is long-term relationships, commitments, and shared experience. Stuffing the entire history into context is expensive and dilutes judgment; vector retrieval only returns “similar fragments,” not who this person is, what relationship the individual has with them, or what was promised. This project asks whether the integrating center can read only a small slice each round and still judge well.

**2. The reason for memory is relationship, not archiving.**  
Humans are social animals; memory helps the individual understand their relationships and position. Shared experience links persons and events: seeing a person evokes the event; recalling the event evokes the people involved. The person–event correspondence is the origin of relationships and the reason memory exists. Indifferent relationships fade; close or hostile ones deepen; commitments persist; interpretations can be revised. A store organized only by time/frequency is a log, not “remembering a person.”

**3. Multiple models are not multiple agents; they are organs of one individual.**  
Most agent frameworks split tasks among agents with their own goals, tools, and actions, then negotiate like a committee. This project explores another structure: multiple models as functional units handling person recognition, memory retrieval, relationship judgment, and context assembly; they prepare context but do not decide for the individual; there is one integrating center. The point is not “many,” but “many yet one.”

**4. What is missing is not memory, but relational continuity.**  
Current systems store dialogue rather than person–event–relationship; retrieve similarity without separating fact, interpretation, and commitment; serve a single task rather than a relationship over time; and drift into committees with no single accountable center. This project targets relational and judgmental continuity, not another larger vector store.

**5. The hypothesis.**  
If memory is organized by person–event–relationship; if context contains only the relational and commitment slice needed now; if the backend only prepares context and never advises or decides; and if multiple models divide the work under one integrating center; then a model ensemble may exhibit a continuous individual at small context, rather than meeting the world anew each time. This is a hypothesis, not a framework, product, or validated practice.

## Documents

| Language | HTML | PDF |
|---|---|---|
| 中文 | [双脑记忆系统-从神经机制到多模型模拟方案.html](docs/zh/双脑记忆系统-从神经机制到多模型模拟方案.html) | [双脑记忆系统-从神经机制到多模型模拟方案.pdf](docs/zh/双脑记忆系统-从神经机制到多模型模拟方案.pdf) |
| English | [dual-brain-memory-system-v2.1-en.html](docs/en/dual-brain-memory-system-v2.1-en.html) | [dual-brain-memory-system-v2.1-en.pdf](docs/en/dual-brain-memory-system-v2.1-en.pdf) |

Read online: <https://jihua3445.github.io/dual-brain-memory-system-from-neural-mechanisms-to-multi-model-simulation/>

## Reference Implementation (Reference Only)

This repository includes the build scripts and an in-memory reference implementation for transparency and reproducibility — **not** a production system.

| Path | Purpose |
|---|---|
| `source/zh/build.py` | Build Chinese HTML from `source/zh/parts` |
| `source/en/build.py` | Build English HTML from `source/en/parts` |
| `source/zh/parts/` | Chinese source fragments |
| `source/en/parts/` | English source fragments |
| `runtime/` | In-memory reference implementation |
| `docs/zh/`, `docs/en/` | Built HTML / PDF |

```bash
cd runtime
python3 -m unittest -v      # 128 tests
python3 pipeline.py         # end-to-end JSON with audit trace
```

## What this is not

- Not a framework: the document describes a line of thinking, not a complete architecture.
- Not a product or validated practice; no production deployment is claimed.
- Not a clinical or neuroscience claim; neuroscience explains design rationale.
- `runtime/` is not a production system: no real persistence, signing keys, distributed writer, or production-grade ratification ledger.
- The API and schema are unstable; they exist to make selected contracts testable and reviewable.
- The repository contains no GitHub token, QA renders, or temporary build artifacts.

## License

MIT License. See [LICENSE](LICENSE).

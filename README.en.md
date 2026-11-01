[简体中文](README.md) | **English**

# Multi-Model Dual-Brain Memory System

**From Neural Mechanisms to a Multi-Model Simulation Approach**

Version 2.1 · 2026

> **Status: a conceptual note.**  
> This repository records a line of thinking, not a framework, product, or validated practice. It explores how memory, relationships, and multi-model division might be organized; it does not claim a complete architecture or implementation. `runtime/` is a small reference probe for selected contracts, not the framework itself.

> **Document title note:** The HTML/PDF documents retain their original title, *Dual-Brain Memory System: From Neural Mechanisms to a Multi-Model Simulation Approach*; the repository uses the shorter project name.

## Why this project

**1. A single model cannot hold “one continuous person.”**  
A person’s continuity is not one conversation; it is long-term relationships, commitments, and shared experience. Stuffing the entire history into context is expensive and dilutes judgment; vector retrieval only returns “similar fragments,” not who this person is, what relationship the individual has with them, or what was promised. This project asks whether the Main Brain can read only a small ContextPacket each round and still judge well.

**2. The reason for memory is relationship, not archiving.**  
Humans are social animals; memory helps the individual understand their relationships and position. Shared experience links persons and events: seeing a person evokes the event; recalling the event evokes the people involved. The person–event correspondence is the origin of relationships and the reason memory exists. Relationship is not one dimension: within relationship dimensions, retention depends only on emotional intensity, not on trust; low emotional intensity makes related memories fade, while close or hostile relationships deepen them. Trust and capacity govern commitment; boundaries are maintained separately. Closeness is not trustworthiness. Commitments persist; interpretations can be revised. Retention is not time/frequency alone: reliable retrieval raises stability, emotional intensity governs memory strength, future utility and relationship strength also modulate it; open commitments are exempt from decay. A store that keeps only dialogue and is not organized by relationship is a log, not “remembering a person.”

**3. Multiple models are not multiple agents; they are organs of one individual.**  
Most agent frameworks split tasks among agents with their own goals, tools, and actions, then negotiate like a committee. This project explores another structure: multiple models as functional units handling person recognition, memory retrieval, relationship judgment, and context assembly; they prepare context but do not decide for the individual; there is one integrating center — an attribute of the whole organism, not of the Main Brain process. The point is not “many,” but “many yet one.”

**4. What is missing is not memory, but relational continuity.**  
Current systems store dialogue rather than person–event–relationship; retrieve similarity without separating fact, interpretation, and commitment; serve a single task rather than a relationship over time; and drift into committees with no single accountable center. This project targets relational and judgmental continuity, not another larger vector store.

**5. The hypothesis.**  
If memory is organized by person–event–relationship; if context contains only the relational and commitment slice needed now; if the backend only prepares context and never advises or decides; and if multiple models divide the work under one integrating center; then a model ensemble may exhibit a continuous individual at small context, rather than meeting the world anew each time. This is a hypothesis, not a framework, product, or validated practice.

## Documents

| Language | HTML | PDF |
|---|---|---|
| Chinese | [Chinese HTML](https://jihua3445.github.io/multi-model-dual-brain-memory-system/zh/双脑记忆系统-从神经机制到多模型模拟方案.html) | [Chinese PDF](https://jihua3445.github.io/multi-model-dual-brain-memory-system/zh/双脑记忆系统-从神经机制到多模型模拟方案.pdf) |
| English | [dual-brain-system-v2.1-en.html](https://jihua3445.github.io/multi-model-dual-brain-memory-system/en/dual-brain-system-v2.1-en.html) | [dual-brain-system-v2.1-en.pdf](https://jihua3445.github.io/multi-model-dual-brain-memory-system/en/dual-brain-system-v2.1-en.pdf) |

Read online: <https://jihua3445.github.io/multi-model-dual-brain-memory-system/>

## Reference Implementation (Reference Only)

This repository includes the build scripts and an in-memory reference implementation for transparency and reproducibility — **not** a production system.

**Model-agnostic.** The reference implementation calls no vendor API. The contracts can be paired with OpenAI, Anthropic, Google, DeepSeek, Qwen, Llama, Mistral, or local models; none is required or endorsed.

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

MIT License. See [LICENSE](https://github.com/jihua3445/multi-model-dual-brain-memory-system/blob/main/LICENSE).

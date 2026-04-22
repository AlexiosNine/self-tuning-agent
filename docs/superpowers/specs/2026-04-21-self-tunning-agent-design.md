# Self Tunning Agent Design

## Overview

Build a self-optimizing question-answering agent using a harness-based approach. The system evaluates its own performance from both offline benchmarks and online user feedback, then iteratively improves prompt strategy, RAG strategy, and tool-calling strategy. It also collects and curates high-quality data for future model fine-tuning.

## Goals

- Build a QA-focused self-optimizing agent
- Support offline benchmark evaluation and online feedback loops
- Optimize three layers of behavior: prompt, RAG, and tool strategy
- Use task-specific evaluation criteria for different question types
- Support multiple model providers
- Collect and prepare fine-tuning datasets from production and human annotations
- Establish project-level AI collaboration rules before implementation

## Non-Goals

- End-to-end model fine-tuning execution in the first phase
- Distributed event-driven architecture
- Large-scale production serving infrastructure
- Multi-agent swarms as the core runtime model

## Chosen Architecture

We use a three-layer architecture:

1. Agent Runtime
2. Evaluation Engine
3. Harness Orchestrator

This structure keeps execution, evaluation, and optimization separated so each layer can evolve independently.

## Core Architecture

### 1. Agent Runtime

The Agent Runtime handles question answering under the currently active strategy version.

Responsibilities:
- Abstract multiple model providers
- Load a specific strategy version
- Apply prompt strategy
- Apply RAG strategy
- Apply tool-calling strategy
- Produce answers and runtime traces for evaluation

Main subcomponents:
- `ModelProvider` interface
  - `ClaudeProvider`
  - `OpenAIProvider`
  - `LocalProvider`
- `PromptStrategy`
- `RAGStrategy`
- `ToolStrategy`

The runtime must be strategy-driven rather than hardcoded so the harness can swap behaviors without changing application code.

### 2. Evaluation Engine

The Evaluation Engine is an abstract evaluation layer, not just an automatic scorer.

Responsibilities:
- Evaluate answer quality using pluggable evaluators
- Support automatic evaluation
- Support user feedback ingestion
- Support expert annotation ingestion
- Aggregate signals from multiple sources
- Route different tasks to different evaluation criteria

Main abstractions:
- `Evaluator` interface
- `AutoEvaluator`
- `HumanEvaluator`
- `HybridEvaluator`

Key design point:
The evaluation layer must treat expert labels and user feedback as first-class signals. Automatic scoring is fast but imperfect; human-labeled data is slower but more authoritative.

### 3. Harness Orchestrator

The Harness Orchestrator manages optimization and release flow.

Responsibilities:
- Manage strategy versions
- Trigger optimization when enough evidence is available
- Generate candidate strategies
- Run offline benchmark evaluation
- Promote passing candidates to canary
- Promote successful canaries to production
- Roll back weak candidates

Optimization release flow:
- `draft`
- `offline_eval`
- `canary`
- `production`
- `rejected`
- `rollback`

This gives the system a controlled path from idea to production strategy.

## Evaluation Model

The system uses task-specific evaluation instead of one universal metric.

Question categories:
- Factual questions
- Reasoning questions
- Creative/open-ended questions

Evaluation examples:
- Factual: factual accuracy, citation alignment, hallucination rate
- Reasoning: logical consistency, step completeness, conclusion correctness
- Creative: relevance, coherence, usefulness, diversity where appropriate

Signal sources:
- Offline benchmark scores
- Online user feedback
- Expert annotations
- Hybrid sampled review

Signal handling principles:
- Automatic evaluation covers large volume
- Human evaluation calibrates the system
- Expert labels define high-confidence reference data
- User feedback acts as broad but noisy real-world signal

## Strategy Versioning

Strategies are stored as versioned artifacts.

Example structure:

```text
strategies/
  v001/
    prompt.yaml
    rag_config.yaml
    tool_config.yaml
    metadata.json
  v002/
  current -> v001/
  canary -> v002/
```

Each version includes:
- Prompt configuration
- RAG configuration
- Tool strategy configuration
- Metadata such as parent version, creation reason, evaluation summary, and promotion state

This allows traceability, rollback, and controlled experimentation.

## Optimization Loop

Optimization is data-driven rather than purely time-driven.

Trigger conditions include:
- Minimum sample count reached
- Enough human annotations collected
- Performance drop detected
- Benchmark drift detected

Optimization loop:
1. Collect evaluation results
2. Analyze failure patterns
3. Generate strategy mutations
4. Validate on offline benchmarks
5. Send passing candidate to canary
6. Observe online metrics
7. Promote or roll back

### Agent-assisted optimization

The optimization process may use agent capabilities to analyze failures and propose improvements.

Examples:
- Analyze failed QA cases and cluster common issues
- Suggest prompt rewrites based on systematic failure patterns
- Recommend RAG parameter changes based on retrieval misses
- Review strategy diffs before promotion

These agents assist the optimizer, but the harness remains the source of truth for version transitions.

## Dataset Curation for Fine-tuning

In addition to short-term strategy optimization, the system builds fine-tuning datasets for future long-term model improvement.

### Dataset layers

```text
datasets/
  raw/
    conversations/
    evaluations/
    annotations/
  processed/
    finetuning/
    benchmark/
  metadata/
```

### Data sources

- Production conversations
- Offline benchmark runs
- Expert annotations
- User feedback
- Synthetic augmentation where explicitly allowed

### Dataset flow

1. Collect raw conversations and evaluation signals
2. Filter for quality and safety
3. Remove or mask sensitive data
4. Normalize to internal schema
5. Convert to provider-specific fine-tuning formats
6. Split into train, validation, and test sets
7. Produce dataset stats and quality reports

### Quality rules

High-quality samples are selected using combined signals such as:
- Strong automatic evaluation score
- Positive expert annotation
- Positive user feedback where available
- No known error markers
- No PII leakage
- No duplicate or low-value content

Low-quality samples are not used for fine-tuning, but may be used for failure analysis.

## Fine-tuning Dataset Formats

The system keeps one internal canonical format and derives provider-specific outputs.

### Internal canonical format

```json
{
  "id": "qa_001",
  "task_type": "factual",
  "question": "什么是 Docker 容器？",
  "answer": "Docker 容器是一种轻量级的虚拟化技术...",
  "context": null,
  "metadata": {
    "auto_eval_score": 0.92,
    "human_annotation": "positive",
    "user_feedback": "thumbs_up",
    "strategy_version": "v001",
    "timestamp": "2026-04-21T10:30:00Z"
  }
}
```

### OpenAI-style output

```jsonl
{"messages": [
  {"role": "system", "content": "你是一个专业的问答助手，擅长回答技术问题。"},
  {"role": "user", "content": "什么是 Docker 容器？"},
  {"role": "assistant", "content": "Docker 容器是一种轻量级的虚拟化技术..."}
]}
```

### Anthropic-style output

```jsonl
{"system": "你是一个专业的问答助手，擅长回答技术问题。", "messages": [
  {"role": "user", "content": "什么是 Docker 容器？"},
  {"role": "assistant", "content": "Docker 容器是一种轻量级的虚拟化技术..."}
]}
```

The internal format is the source of truth. Provider-specific formats are generated views.

## Project Structure

The project should start by defining project-level agent instructions and rules before application code.

```text
self_tunning/
  CLAUDE.md
  .claude/
    rules/
      architecture.md
      coding-style.md
      testing.md
      data-handling.md

  src/
    agent/
      runtime.py
      providers/
        base.py
        claude.py
        openai.py
        local.py
      strategies/
        prompt.py
        rag.py
        tool.py

    evaluation/
      engine.py
      evaluators/
        base.py
        auto.py
        human.py
        hybrid.py
      classifiers/
        task_classifier.py
      aggregator.py

    harness/
      orchestrator.py
      optimizer.py
      version_manager.py
      trigger.py

    dataset/
      builder.py
      quality_filter.py
      augmentation.py
      converter.py

    common/
      config.py
      logging.py
      types.py

  strategies/
  datasets/
  benchmarks/
  tests/
  config.yaml
  pyproject.toml
```

## Project-level AI Rules

### `CLAUDE.md`

This file defines the project’s working contract for future AI-assisted development.

It should cover:
- Project purpose
- Three-layer architecture boundaries
- Strategy versioning principles
- Evaluation signal hierarchy
- Dataset schema expectations
- Requirement to preserve separation between execution, evaluation, and orchestration

### `.claude/rules/architecture.md`

Defines:
- Layer boundaries
- Interface-first design
- No cross-layer shortcuts
- Strategy plug-in model
- Evaluation abstraction rules

### `.claude/rules/coding-style.md`

Defines:
- Python code style
- Typing expectations
- Immutability preference where applicable
- File size and cohesion rules

### `.claude/rules/testing.md`

Defines:
- TDD requirement
- Per-layer testing responsibilities
- Mock boundaries across layers
- Coverage target

### `.claude/rules/data-handling.md`

Defines:
- PII handling
- Annotation ingestion rules
- Dataset quality thresholds
- Canonical vs derived dataset formats

## Error Handling

Error handling should follow layer ownership.

- Agent Runtime handles provider failures, tool invocation failures, and retrieval failures
- Evaluation Engine handles missing labels, inconsistent evaluator outputs, and delayed human review
- Harness Orchestrator handles promotion failures, benchmark run failures, and rollback decisions
- Dataset pipeline handles malformed records, schema drift, duplication, and unsafe data content

Errors must be observable and attributable to one layer. Silent cross-layer fallback should be avoided.

## Testing Strategy

Testing must cover all major layers independently and together.

Required test types:
- Unit tests for providers, strategies, evaluators, version management, and converters
- Integration tests for runtime-evaluation-harness flow
- Dataset tests for format conversion, filtering, and splitting
- End-to-end harness tests for offline-to-canary promotion logic

Key test cases:
- Switching strategy versions changes runtime behavior correctly
- Human annotations are ingested and reflected in aggregated evaluation
- Failed canary triggers rollback
- High-quality records enter fine-tuning datasets
- Unsafe or low-quality records are excluded from fine-tuning datasets

## Security and Data Safety

Because the system uses production conversations and annotations, data handling rules are mandatory.

Requirements:
- Strip or mask PII before processed dataset generation
- Track provenance of training examples
- Keep raw and processed datasets separate
- Prevent strategy metadata from exposing secrets or user content unnecessarily
- Maintain auditable logs for promotions and rollbacks

## Implementation Sequence

Recommended implementation order:
1. Create `CLAUDE.md` and `.claude/rules/`
2. Define shared types and interfaces
3. Implement strategy version management
4. Implement basic agent runtime with one provider
5. Implement evaluation abstractions and one automatic evaluator
6. Add human feedback ingestion path
7. Implement harness orchestration and promotion flow
8. Implement dataset builder and format conversion
9. Add multi-provider support
10. Add agent-assisted optimization helpers

## Success Criteria

The design succeeds when the project can:
- Answer questions through a versioned strategy runtime
- Evaluate responses using both automatic and human signals
- Promote and roll back strategies safely
- Support multiple model providers through one abstraction
- Produce reusable fine-tuning datasets in canonical and derived formats
- Evolve under clearly defined project AI rules

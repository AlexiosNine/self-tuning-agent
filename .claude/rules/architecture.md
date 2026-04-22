# Architecture

- Do not bypass layer boundaries.
- Agent runtime never promotes versions.
- Evaluation engine never mutates strategy files.
- Harness orchestrator is the only layer allowed to promote or roll back versions.
- Shared contracts belong in `src/common/types.py`.

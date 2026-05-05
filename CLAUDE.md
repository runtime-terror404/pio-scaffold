## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## pio-scaffold

The unified PlatformIO scaffolding CLI (replacing `pio-pico2` and `pio-stm`). The full architecture spec lives in `proposed_architecture.md`.

Rules:
- Before starting any work on the unified pio-scaffold tool, read `proposed_architecture.md` first
- Do not modify the legacy `pio-pico2` or `pio-stm` scripts — they will be removed once the unified tool replaces them

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## pio-scaffold

The unified PlatformIO scaffolding CLI. Entry point: `./pio-scaffold` → `pio_scaffold/` package.

Rules:
- Before making changes, read `pio_scaffold/platforms.py` for the platform/board registry and `pio_scaffold/generators.py` for file generation logic
- Full usage docs in `README.md`
- The CLI is built with Typer; use `pathlib.Path` (not `os.path`) throughout

### Post-test bug fixes (2026-05-05)

Five bugs fixed after integration testing (commits `0a1a6da` and `dea4c31` on main, not yet pushed):

1. **Preset merge** — `_merge_config` in cli.py now filters `None` from both sides. CLI params that overlap with preset keys use `None` defaults; real defaults applied via `setdefault` after merge + None-stripping pass. Without the strip, `setdefault` skips keys that exist with value `None`.

2. **`stm32_cpp` template** — now generates `#include "stm32f4xx_hal.h"` + `int main(void)` with `HAL_Init()`, family-aware from `config["mcu_family"]`.

3. **`pico2_cpp` template** — branches on `config.get("framework")`: `pico-sdk` → `<pico/stdlib.h>` + `int main()`, `arduino` → dual-core setup/loop. Core comments use "M0+" for RP2040 (`board == "pico"`) and "M33" for RP2350.

4. **`parse_hclk_from_ioc`** — returns `Optional[int]` (`None` when field missing, was ambiguously 100000000).

5. **`hclk_comment`** — was dead code; now interpolated into `swo_trace.py` header comment.

6. **Two regressions** from the preset fix (None defaults + setdefault interaction) fixed by stripping `None`-valued keys from config before `setdefault` in both pico2 and stm32 commands.

### INI generation fixes (2026-05-28)

Commit `c32e686` fixed two generated `platformio.ini` issues:

1. **STM32: missing `platform` and named env** — `_generate_ini_stm32` now emits `platform = ststm32` in `[env]` (was missing entirely, so builds failed) and adds a named `[env:{board_id}]` section (e.g. `[env:genericSTM32F411CE]`) so the VS Code extension recognizes the project.

2. **Pico2 `[env:dap]`: removed `upload_protocol` and `debug_tool`** — both were `cmsis-dap`. The `upload_protocol` triggered a separate `.pio/build/dap/` compilation that hit an `arm-none-eabi-gcc` segfault on the earlephilhower toolchain; `debug_tool` was never used and just added noise. The env is now a clean placeholder with `; upload_protocol = cmsis-dap` commented out. Users can uncomment when their toolchain is stable.

### STM32 dead src/main.cpp + INSTRUCTIONS.md (2026-06-03)

Two changes to keep AI assistants from writing Arduino code in STM32 HAL projects:

1. **STM32 no longer generates `src/main.cpp`** — `write_project` skips it when `platform.key == "stm32"`. The INI already sets `src_dir = Core/Src`, so PlatformIO compiles CubeMX code from `Core/Src/`, not `src/`. The old `src/main.cpp` was dead code that AI assistants (Claude Code, etc.) saw and assumed was the entry point — they'd write Arduino-style code there oblivious to the actual HAL sources.

2. **`INSTRUCTIONS.md` generated for all platforms** — `generate_instructions_md()` in generators.py produces platform-appropriate project guidance:
   - **STM32**: explains CubeMX → PlatformIO conversion, `Core/Src`/`Core/Inc` layout, STM32Cube HAL framework (not Arduino), pio-hunt skill with HAL-compatibility caveat
   - **Pico2**: standard PlatformIO layout, framework-appropriate guidance, pio-hunt skill
   - Added to `GITIGNORE_CONTENT` so it stays local-only when `--git` is used

### Known issues (not yet fixed)

- None currently.

### README sync + install.sh robustness (2026-05-28)

After the INI fixes (`c32e686`) and venv migration, the README had drifted from the code in several places. All synced:

- **Install sections** — replaced old `pip install --user` + symlink descriptions with venv + launcher flow (one-liner, installer steps, manual install)
- **typer version** — `≥0.15` → `≥0.9.0` (matches `requirements.txt`)
- **pico2 INI example** — `[env:dap]` now shows `upload_protocol` commented out and `debug_tool` removed
- **stm32 INI example** — added `platform = ststm32` and `[env:genericSTM32F411CE]` named section
- **stm32 generated file tree** — `[env] stm32cube config` → `[env] + [env:{board_id}]`; "Arduino boilerplate" → "HAL boilerplate"
- **pico2 generated file tree** — now mentions pico-sdk alongside Arduino

**install.sh fixes:**

1. **Dirty git state on update** — the old `git pull --ff-only` failed when local files were modified (e.g. old `install.sh` vs new, untracked `requirements.txt`). Now does `git fetch` → `git reset --hard origin/main` → `git clean -fd` → `git merge --ff-only`. The reset + clean nuke local modifications so the merge always succeeds.

2. **Python upgrade detection** — if the venv's Python version (`pyvenv.cfg`) differs from the host Python, the venv is rebuilt. Survives future 3.14→3.15 upgrades.

3. **requirements.txt staleness** — if `requirements.txt` is newer than the venv, deps are reinstalled. Otherwise skips pip entirely.

4. **Fresh-install edge case** — creating a new venv now sets `FORCE_VENV=1` so deps get installed (was 0, causing "skipped" on an empty venv).

### Commit message / file-writing gotcha

Do NOT use shell heredocs for git commit messages or file writes on this machine — the user's zsh syntax-highlighting plugin injects ANSI color codes into piped content. This also breaks the `Edit` tool (old_string won't match because invisible color codes are embedded in the file). Workarounds:

- **Commit messages**: Use `Write` to a temp file then `git commit -F <file>`. Never add `Co-Authored-By: Claude` — the user does not want it.
- **File edits**: If Edit fails with "String to replace not found" on text you can see in the file, the file likely has ANSI codes. Use `Write` to rewrite the whole file cleanly, or strip with `sed` first.

### Venv migration (2026-05-24)

Arch upgraded Python 3.13 → 3.14, which orphaned all `--user` packages (version-specific site-packages) and also enforced PEP 668 — `pip install --user` is now completely blocked. Two changes fixed this permanently:

1. **`requirements.txt`** — pins `typer>=0.9.0` (the sole Python dependency)
2. **`install.sh`** — instead of `pip install --user typer`, the script now creates `.venv/` inside `$INSTALL_DIR`, installs deps from `requirements.txt`, and writes a standalone launcher at `$BIN_DIR/pio-scaffold` (no longer a symlink). The launcher uses the venv's Python shebang and injects `$INSTALL_DIR` into `sys.path` so the venv can find `pio_scaffold`.

This survives future Python upgrades because the venv bundles its own Python binary.

### Install/update flow

The README's `install.sh` clones to `~/.local/share/pio-scaffold`, creates a `.venv` there with dependencies, and writes a standalone launcher to `~/.local/bin/pio-scaffold`. Re-running the script pulls updates and re-installs deps. Test artifacts (`report.md`, `report copy.md`) are gitignored via `report*.md`.

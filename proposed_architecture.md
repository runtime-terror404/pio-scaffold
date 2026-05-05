# Unified PIO Scaffold CLI — Proposed Architecture

## Context

Two standalone scripts (`pio-pico2` and `pio-stm`) do similar things — scaffold PlatformIO projects — but are completely separate with no shared logic. The goal is a single CLI tool that covers both platforms, adds an interactive wizard mode, and is extensible for future platforms and features.

## Tech Stack

- **CLI framework**: Typer (type-hinted, modern, built on click)
- **Templating**: string formatting (no Jinja2 dependency needed at this scale)
- **Python**: 3.8+ (for `typing` support)

## Tool Name

`pio-scaffold` — single entry point, symlinked/installed into PATH.

---

## Architecture

```
/home/divine/Projects/scripts/
├── pio-scaffold          # top-level entry script (shebang python3)
├── pio_scaffold/         # package directory
│   ├── __init__.py
│   ├── cli.py            # Typer app definition + root command
│   ├── wizard.py         # Interactive Q&A flow (no-args mode)
│   ├── platforms.py      # Platform definitions (Pico2, STM32, extensible)
│   ├── generators.py     # File generators (ini, cpp, extras)
│   └── templates.py      # Template constants (cpp boilerplate strings)
```

### Module Responsibilities

**`cli.py`** — Typer app entry point
- Root command: if no args → launch wizard, else show help
- `pico2` subcommand: flags for board variant, framework, envs, git, libs
- `stm32` subcommand: flags for .ioc path, debug probe, git, libs
- `presets` subcommand group: `save`, `list`, `load`, `delete`
- Global flags: `--dry-run` (preview only), `--yes` (skip confirmations)

**`wizard.py`** — Interactive mode
- Ask platform → pico2 / stm32
- Ask board variant (for pico2: WeAct, Official Pico2, custom; for stm32: auto from .ioc)
- Ask framework preference
- Ask environments (USB, DAP, both)
- Ask if git init
- Ask if CI template
- Ask library dependencies
- Show summary, confirm, then generate

**`platforms.py`** — Platform data classes
- `Platform` base dataclass with fields: name, boards, frameworks, default_envs, debug_probes
- `Pico2Platform`: RP2350 variants, earlephilhower core, USB/DAP envs
- `STM32Platform`: genericSTM32xx mapping, stm32cube framework, ST-Link/J-Link/DAP probes
- `get_platform(name)` registry function for easy extension

**`generators.py`** — All file output logic
- `generate_ini(platform, config)` → platformio.ini string
- `generate_main_cpp(platform, config)` → src/main.cpp string
- `generate_extras(platform, config)` → dict of {filename: content} (SWO scripts, etc.)
- `generate_gitignore(config)` → .gitignore string
- `generate_ci(platform)` → .github/workflows/pio_build.yml string

**`templates.py`** — String constants
- CPP boilerplate for pico2 (dual-core skeleton)
- CPP boilerplate for stm32 (single-core skeleton)
- Each template accepts a `config` dict for customization (board pins, etc.)

---

## New Features (Beyond Current Scripts)

### Core Features
1. **Interactive wizard** — no-args launches guided setup
2. **`--dry-run`** — print what would be generated without touching disk
3. **Board variants** — pico2 supports WeAct, Official Pico2, Pimoroni, etc.
4. **Debug probe selection** — ST-Link / CMSIS-DAP / J-Link / Picoprobe

### Quality of Life
5. **Git init** — `--git` flag creates .gitignore + optional initial commit
6. **Library injection** — `--libs "Adafruit NeoPixel,Wire"` adds to lib_deps
7. **Monitor speed** — `--baud 9600` / `--baud 115200` flag
8. **`--yes` flag** — skip confirmation prompts for scripting

### Extras
9. **CI template** — `--ci` generates GitHub Actions workflow (pio run on push)
10. **Config presets** — save/load named presets for recurring setups (`pio-scaffold presets save my-stm32-f411`, `pio-scaffold presets load my-stm32-f411`)
11. **Platform extensibility** — registry pattern so adding ESP32/nRF52/etc. later is just a new dataclass + template

---

## CLI Surface

```
pio-scaffold                          # interactive wizard (no args)
pio-scaffold pico2 [OPTIONS]          # scaffold RP2350/Pico2 project
pio-scaffold stm32 [OPTIONS]          # scaffold STM32 from .ioc
pio-scaffold presets save NAME        # save current config as preset
pio-scaffold presets load NAME        # load and apply a preset
pio-scaffold presets list             # list saved presets
pio-scaffold presets delete NAME      # remove a preset
```

### `pico2` subcommand options

| Flag | Default | Description |
|------|---------|-------------|
| `--board` | weact | Board variant: weact, official, pimoroni, custom |
| `--framework` | arduino | Framework: arduino, pico-sdk |
| `--core` | earlephilhower | Arduino core: earlephilhower, mbed |
| `--envs` | usb,dap | Environments: usb, dap |
| `--baud` | 115200 | Serial monitor speed |
| `--libs` | none | Comma-separated lib_deps |
| `--git` | false | Initialize git repo |
| `--ci` | false | Generate GitHub Actions CI |
| `--dry-run` | false | Preview without creating files |
| `--yes` | false | Skip confirmation |

### `stm32` subcommand options

| Flag | Default | Description |
|------|---------|-------------|
| `--ioc` | auto-detect | Path to .ioc file |
| `--debug` | stlink | Debug probe: stlink, cmsis-dap, jlink |
| `--swo` | true | Generate SWO trace script |
| `--baud` | 115200 | Serial monitor speed |
| `--libs` | none | Comma-separated lib_deps |
| `--git` | false | Initialize git repo |
| `--ci` | false | Generate GitHub Actions CI |
| `--dry-run` | false | Preview without creating files |
| `--yes` | false | Skip confirmation |

---

## Files to Create

1. `/home/divine/Projects/scripts/pio-scaffold` — entry script (chmod +x)
2. `/home/divine/Projects/scripts/pio_scaffold/__init__.py`
3. `/home/divine/Projects/scripts/pio_scaffold/cli.py`
4. `/home/divine/Projects/scripts/pio_scaffold/wizard.py`
5. `/home/divine/Projects/scripts/pio_scaffold/platforms.py`
6. `/home/divine/Projects/scripts/pio_scaffold/generators.py`
7. `/home/divine/Projects/scripts/pio_scaffold/templates.py`

## Files to Remove (after migration)

- `/home/divine/Projects/scripts/pio-pico2`
- `/home/divine/Projects/scripts/pio-stm`

## Preset Storage

Presets saved to `~/.config/pio-scaffold/presets.json`. Simple JSON file, one preset per key. No external config library needed.

---

## Additional Features (from review)

These slot into the existing architecture above — no conflicts, no new modules needed.

### 1. `--name` and `--output` flags (cli.py)
Allow overriding the project name (default: `os.getcwd()` basename) and target directory (default: cwd).
```
pio-scaffold pico2 --name my-blink --output ~/projects/
```
Both flags apply to all subcommands and the wizard. Adds two Typer options to the root app.

### 2. Dependency checking (cli.py — pre-flight)
Before any generation, verify `pio` is on PATH. If missing, print a clear error and exit rather than letting the subprocess stack trace.
```
Error: 'pio' command not found. Install PlatformIO: https://platformio.org/install
```
Single `shutil.which("pio")` check at the top of the main command callback.

### 3. pathlib throughout (all modules)
Use `pathlib.Path` instead of `os.path` / `os.getcwd()` / string concatenation for all filesystem operations. Stdlib, Python 3.6+, handles Windows/Linux separators automatically. Implementation detail, not a user-facing feature.

### 4. Data logging via monitor_filters (generators.py → generate_ini)
Add `monitor_filters = time, log2file` to the generated `platformio.ini` env section. This timestamps serial output and writes it to a log file automatically — costs nothing, saves beginners from discovering these filters exist.
- Controlled by a `--log` flag (default: true, since it's harmless)
- When enabled, adds the line to the common env section

### 5. Dynamic SWO clock (generators.py → generate_extras for stm32)
Instead of hardcoding `-traceclk 100000000` in the SWO script, parse `RCC.HCLKFreq_Value` from the `.ioc` file and use the actual HCLK frequency. Prevents garbled SWO output when the user has a non-default clock config.
- Add `parse_hclk_from_ioc(ioc_path)` helper to platforms.py (stm32 section)
- Use the parsed value or fall back to 100000000 with a comment that it's a default

### 6. Multiple .ioc handling (wizard.py + cli.py stm32 subcommand)
When `--ioc` is not specified and auto-detect finds multiple `.ioc` files, present a numbered picker instead of silently grabbing the first one.
```
Found 3 .ioc files:
  [1] nucleo-f411re.ioc
  [2] nucleo-f411re-USB.ioc
  [3] nucleo-f411re-backup.ioc
Select one [1]:
```
Logic lives in the stm32 subcommand callback and the wizard's platform-selection step.

### 7. RP2040 board support (platforms.py + cli.py)
Extend the `--board` flag for pico2 to include RP2040 variants:
- `pico` → original Raspberry Pi Pico (RP2040, `board = pico`)
- `pico2` → official Pico 2 (RP2350)
- `weact` → WeAct RP2350A (current default)

The platform dataclass already supports board variants — just add the entries.

---

## Updated CLI Surface (additions bolded)

### New global flags
| Flag | Default | Description |
|------|---------|-------------|
| **`--name`** | cwd basename | Project name |
| **`--output`** | cwd | Target directory |
| `--dry-run` | false | Preview without creating files |
| `--yes` | false | Skip confirmation |

### Updated `pico2` subcommand options
| Flag | Default | Description |
|------|---------|-------------|
| `--board` | weact | **Now: pico, pico2, weact, official, pimoroni, custom** |
| `--framework` | arduino | Framework: arduino, pico-sdk |
| `--core` | earlephilhower | Arduino core: earlephilhower, mbed |
| `--envs` | usb,dap | Environments: usb, dap |
| `--baud` | 115200 | Serial monitor speed |
| **`--log`** | true | Add timestamp + log2file monitor filters |
| `--libs` | none | Comma-separated lib_deps |
| `--git` | false | Initialize git repo |
| `--ci` | false | Generate GitHub Actions CI |
| `--dry-run` | false | Preview without creating files |
| `--yes` | false | Skip confirmation |

### Updated `stm32` subcommand options
| Flag | Default | Description |
|------|---------|-------------|
| `--ioc` | auto-detect | Path to .ioc file **(now handles multiple with picker)** |
| `--debug` | stlink | Debug probe: stlink, cmsis-dap, jlink |
| `--swo` | true | Generate SWO trace script **(now parses HCLK from .ioc)** |
| `--baud` | 115200 | Serial monitor speed |
| **`--log`** | true | Add timestamp + log2file monitor filters |
| `--libs` | none | Comma-separated lib_deps |
| `--git` | false | Initialize git repo |
| `--ci` | false | Generate GitHub Actions CI |
| `--dry-run` | false | Preview without creating files |
| `--yes` | false | Skip confirmation |

### Updated module list

```
pio_scaffold/
├── __init__.py
├── cli.py            # + --name, --output, --log, dependency check, multi-ioc picker
├── wizard.py         # + multi-ioc handling, board variants including RP2040
├── platforms.py      # + parse_hclk_from_ioc(), RP2040 board entries
├── generators.py     # + monitor_filters in ini, dynamic traceclk in SWO
└── templates.py
```

---

## Verification

1. Run `./pio-scaffold` (no args) → interactive wizard launches
2. Run `./pio-scaffold pico2 --dry-run` → prints files it would create
3. Run `./pio-scaffold pico2 --yes` in a temp dir → creates full pico2 project, verify `platformio.ini` and `src/main.cpp`
4. Run `./pio-scaffold stm32 --dry-run` from a CubeMX project dir → prints files
5. Run `./pio-scaffold stm32 --yes` in a CubeMX project dir → creates platformio.ini with correct folder routing + SWO script
6. Run `./pio-scaffold presets save test` and `./pio-scaffold presets list` → preset appears
7. Run `./pio-scaffold pico2 --git --ci --dry-run` → shows .gitignore and CI workflow in output

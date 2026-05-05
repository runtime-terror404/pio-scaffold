# pio-scaffold

Unified PlatformIO project scaffolding CLI. Generates ready-to-build PlatformIO projects for **Raspberry Pi Pico / RP2350 / RP2040** and **STM32 (CubeMX / CubeIDE)** from a single tool.

## Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.8+ | Runtime (uses `typing`, `pathlib`, `dataclasses`) |
| **typer** | ≥0.15 | CLI framework (`pip install typer`) |
| **PlatformIO Core** | any | `pio` must be on PATH ([install guide](https://platformio.org/install)) |
| **git** | any | Only if using `--git` flag (optional) |

## Installation

### One-liner (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/<USER>/scripts/main/install.sh | sh
```

The script checks dependencies, installs typer if missing, clones the repo to `~/.local/share/pio-scaffold`, symlinks the binary into `~/.local/bin`, and verifies the install by printing `--help`. It's safe to re-run — it pulls updates if already cloned.

After installation, restart your shell or run:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

### What the installer does

1. Verifies **Python 3.8+** — aborts if missing or too old
2. Verifies **git** — aborts if missing
3. Installs **typer** via `pip install --user` if not already present
4. Checks for **PlatformIO CLI** (`pio`) — warns if missing, but does not abort (you can install it after)
5. Clones the repo to `~/.local/share/pio-scaffold` (or `git pull` if already cloned)
6. Symlinks `pio-scaffold` → `~/.local/bin/pio-scaffold`
7. Checks whether `~/.local/bin` is in `PATH` — prints a warning with the line to add to `~/.bashrc`/`~/.zshrc` if not
8. Runs `pio-scaffold --help` to verify the install worked
9. Reminds you to install PlatformIO if `pio` wasn't found in step 4

### PlatformIO

The installer does **not** install PlatformIO — you need that separately:

```bash
pip install platformio
# or: https://platformio.org/install
```

### Manual install

```bash
git clone https://github.com/<USER>/scripts.git ~/.local/share/pio-scaffold
chmod +x ~/.local/share/pio-scaffold/pio-scaffold
ln -s ~/.local/share/pio-scaffold/pio-scaffold ~/.local/bin/pio-scaffold
pip install typer platformio
```

Verify:

```bash
pio-scaffold --help
```

## Quick Start

```bash
# Interactive wizard (no arguments)
pio-scaffold

# Scaffold a Pico2 project with defaults in one command
pio-scaffold pico2 --yes

# Preview what would be generated without touching disk
pio-scaffold pico2 --dry-run

# Scaffold an STM32 project from a CubeMX directory
cd my-stm32-project/   # contains nucleo-f411re.ioc
pio-scaffold stm32 --yes
```

## CLI Reference

### Global flags

These apply to all commands and the wizard:

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--name TEXT` | — | cwd basename | Project name |
| `--output PATH` | `-o` | `.` | Target output directory |
| `--dry-run` | — | false | Print files that would be created, don't touch disk |
| `--yes` | `-y` | false | Skip all confirmation prompts (non-interactive mode) |
| `--preset TEXT` | `-p` | none | Load configuration from a saved preset |

### `pio-scaffold` (no subcommand)

Launches the interactive wizard. The wizard walks you through platform selection, board variant, framework, debug probe, and all other options, then shows a summary before generating files.

### `pio-scaffold pico2`

Scaffold a Raspberry Pi Pico / RP2350 / RP2040 project.

```
pio-scaffold pico2 [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--board TEXT` | `-b` | `weact` | Board variant (see table below) |
| `--framework TEXT` | `-f` | `arduino` | Framework: `arduino`, `pico-sdk` |
| `--core TEXT` | `-c` | `earlephilhower` | Arduino core: `earlephilhower`, `mbed` |
| `--envs TEXT` | `-e` | `usb,dap` | Environments (comma-separated): `usb`, `dap` |
| `--baud INT` | — | `115200` | Serial monitor baud rate |
| `--log` / `--no-log` | — | `--log` | Add `monitor_filters = time, log2file` |
| `--libs TEXT` | `-l` | none | Comma-separated `lib_deps` (e.g. `"Adafruit NeoPixel, Wire"`) |
| `--git` | — | false | Initialize git repo + create `.gitignore` + initial commit |
| `--ci` | — | false | Generate `.github/workflows/pio_build.yml` |
| `--dry-run` | — | false | Preview without writing files |
| `--yes` | `-y` | false | Skip confirmation prompt |
| `--name TEXT` | — | dir basename | Project name |
| `--output PATH` | `-o` | `.` | Target output directory |
| `--preset TEXT` | `-p` | none | Load from saved preset |

#### Board variants

| `--board` | Chip | PlatformIO `board` | Notes |
|-----------|------|---------------------|-------|
| `weact` | RP2350A | `rpipico2` | WeAct RP2350A (default) |
| `pico2` | RP2350 | `rpipico2` | Official Raspberry Pi Pico 2 |
| `pico` | RP2040 | `pico` | Original Raspberry Pi Pico |
| `official` | RP2350 | `rpipico2` | Alias for official Pico 2 |
| `pimoroni` | RP2350 | `pimoroni_pico2` | Pimoroni Pico Plus 2 |
| `custom` | RP2350 | `rpipico2` | Custom RP2350 board (16 MB flash) |

All boards use `board_build.core = earlephilhower` and the [maxgerhardt/platform-raspberrypi](https://github.com/maxgerhardt/platform-raspberrypi.git) platform.

### `pio-scaffold stm32`

Scaffold an STM32 project from a CubeMX `.ioc` file.

```
pio-scaffold stm32 [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--ioc PATH` | — | auto-detect | Path to `.ioc` file (auto-detected from output dir if omitted) |
| `--debug TEXT` | `-d` | `stlink` | Debug probe (see table below) |
| `--swo` / `--no-swo` | — | `--swo` | Generate SWO trace script with dynamic HCLK |
| `--baud INT` | — | `115200` | Serial monitor baud rate |
| `--log` / `--no-log` | — | `--log` | Add `monitor_filters = time, log2file` |
| `--libs TEXT` | `-l` | none | Comma-separated `lib_deps` |
| `--git` | — | false | Initialize git repo + create `.gitignore` + initial commit |
| `--ci` | — | false | Generate `.github/workflows/pio_build.yml` |
| `--dry-run` | — | false | Preview without writing files |
| `--yes` | `-y` | false | Skip confirmation prompt |
| `--name TEXT` | — | `.ioc` stem | Project name |
| `--output PATH` | `-o` | `.` | Target output directory |
| `--preset TEXT` | `-p` | none | Load from saved preset |

#### Debug probes

| `--debug` | Upload protocol | Debug tool | OpenOCD interface |
|-----------|-----------------|------------|-------------------|
| `stlink` | `stlink` | `stlink` | `interface/stlink.cfg` |
| `cmsis-dap` | `cmsis-dap` | `cmsis-dap` | `interface/cmsis-dap.cfg` |
| `jlink` | `jlink` | `jlink` | `interface/jlink.cfg` |

#### .ioc handling

When `--ioc` is not specified, `pio-scaffold` auto-detects `.ioc` files in the output directory:

- **No `.ioc` files**: warns and uses defaults (`genericSTM32F411CE` / `stm32f4x`)
- **One `.ioc` file**: uses it automatically
- **Multiple `.ioc` files**: presents a numbered picker (use `--yes` to auto-select the first)

The `.ioc` file is parsed for:
- `Mcu.UserName` → maps to PlatformIO `genericSTM32XXXXXX` board ID and `stm32{fam}x` family
- `RCC.HCLKFreq_Value` → used as `-traceclk` in the SWO script (falls back to 100000000 with a comment if not found)

### `pio-scaffold presets`

Save, load, list, and delete named configuration presets. Presets are stored in `~/.config/pio-scaffold/presets.json`.

```bash
# Save a preset
pio-scaffold presets save my-pico2 --board weact --platform pico2 --baud 115200

# List saved presets
pio-scaffold presets list

# Load a preset (prints JSON)
pio-scaffold presets load my-pico2

# Use a preset when scaffolding
pio-scaffold pico2 --preset my-pico2 --yes

# Delete a preset
pio-scaffold presets delete my-pico2
pio-scaffold presets delete my-pico2 --force   # skip confirmation
```

Presets store: `platform`, `board`, `framework`, `baud`, and `libs`. CLI flags always take precedence over preset values — you can use a preset as a base and override individual options.

## Files Generated

### pico2 projects

```
project-dir/
├── platformio.ini          # [env] + [env:usb] + [env:dap]
└── src/
    └── main.cpp            # Dual-core Arduino boilerplate (setup/loop + setup1/loop1)
```

With `--git`:
```
├── .gitignore              # .pio/, .vscode/ build artifacts, __pycache__
```

With `--ci`:
```
└── .github/
    └── workflows/
        └── pio_build.yml   # GitHub Actions: pio run on push/PR
```

### stm32 projects

```
project-dir/
├── platformio.ini          # [platformio] folder routing + [env] stm32cube config
├── swo_trace.py            # OpenOCD SWO trace custom target (unless --no-swo)
└── src/
    └── main.cpp            # Single-core Arduino boilerplate
```

With `--git`: same `.gitignore` as above.  
With `--ci`: same `.github/workflows/pio_build.yml` as above.

### platformio.ini contents

**pico2** (`pio-scaffold pico2 --board weact`):
```ini
[env]
platform = https://github.com/maxgerhardt/platform-raspberrypi.git
board = rpipico2
framework = arduino
board_build.core = earlephilhower
board_upload.maximum_size = 16777216
monitor_speed = 115200
monitor_filters = time, log2file

; Default environment: Flashes via USB-C (1200bps touch)
[env:usb]

; Debug environment: Flashes via SWD DAPLink
[env:dap]
upload_protocol = cmsis-dap
debug_tool = cmsis-dap
```

**stm32** (`pio-scaffold stm32` in CubeMX dir):
```ini
[platformio]
src_dir = Core/Src
include_dir = Core/Inc

[env]
board = genericSTM32F411CE
framework = stm32cube
upload_protocol = stlink
debug_tool = stlink
monitor_speed = 115200
monitor_filters = time, log2file
extra_scripts = swo_trace.py
```

### SWO trace script (`swo_trace.py`)

Generated for STM32 projects (unless `--no-swo`). Parses `RCC.HCLKFreq_Value` from the `.ioc` file to set the correct `-traceclk` frequency. Registers a `swo_trace` custom target in PlatformIO that streams ITM SWO debug output via OpenOCD.

## Interactive Wizard

Running `pio-scaffold` without arguments launches a guided setup:

```
=== pio-scaffold interactive wizard ===

Select target platform:
  [1] pico2
  [2] stm32
Select [1]:

Project name [my-project]:
Output directory [/home/user/projects]:

Select board variant:
  [1] WeAct RP2350A (weact)
  [2] Official Raspberry Pi Pico 2 (RP2350) (pico2)
  [3] Original Raspberry Pi Pico (RP2040) (pico)
  [4] Raspberry Pi Pico 2 (official) (official)
  [5] Pimoroni Pico Plus 2 (pimoroni)
  [6] Custom RP2350 board (custom)
Select [1]:

Select framework:
  [1] arduino
  [2] pico-sdk
Select [1]:

...

--- Configuration Summary ---
  Platform:   Raspberry Pi Pico / RP2350 / RP2040
  Board:      WeAct RP2350A
  Framework:  arduino
  Envs:       usb, dap
  ...

Proceed with these settings? [Y/n]:
```

## Dependency Check

Before generating anything, `pio-scaffold` verifies that `pio` is on `PATH`. If missing, it exits with:

```
Error: 'pio' command not found. Install PlatformIO: https://platformio.org/install
```

## Arch Linux Install Note

On Arch Linux, install PlatformIO via:

```bash
yay -S platformio
# or
sudo pacman -S platformio
```

## Examples

```bash
# Minimal Pico2 project, USB-only, accept defaults
pio-scaffold pico2 --yes

# RP2040 (original Pico) with custom name and output dir
pio-scaffold pico2 --board pico --name my-blink --output ~/projects/ --yes

# Pico2 with git, CI, custom baud, and libraries
pio-scaffold pico2 --git --ci --baud 9600 --libs "Adafruit NeoPixel, Wire" --yes

# STM32 from a specific .ioc file, J-Link debug probe
pio-scaffold stm32 --ioc my-board.ioc --debug jlink --yes

# STM32 without SWO trace, no log filters
pio-scaffold stm32 --no-swo --no-log --yes

# Preview everything before committing
pio-scaffold pico2 --git --ci --libs "Wire, SPI" --dry-run

# DAP-only environment (no USB)
pio-scaffold pico2 --envs dap --yes

# Load a preset but override the baud rate
pio-scaffold pico2 --preset my-pico2 --baud 9600 --yes
```

## Environment Variables

None required. Presets are stored at `~/.config/pio-scaffold/presets.json` (created automatically on first `presets save`).

## Differences from Legacy Scripts

`pio-scaffold` replaces `pio-pico2` and `pio-stm`. Key differences:

| | Legacy scripts | pio-scaffold |
|---|---|---|
| Entry point | Two separate scripts | Single `pio-scaffold` CLI |
| Discovery | Must know script names | `--help` shows everything |
| Pre-flight | None | Checks `pio` on PATH |
| Board variants | WeAct only (pico2) | 6 variants including RP2040 |
| .ioc handling | First match only | Picker for multiple files |
| `--dry-run` | Not available | Full preview support |
| Presets | Not available | Save/load/list/delete |
| Git init | Manual | `--git` flag |
| CI workflow | Manual | `--ci` flag |
| Libs | Manual after | `--libs` flag |
| SWO HCLK | Hardcoded 100 MHz | Parsed from `.ioc` |
| Monitor filters | Not included | `monitor_filters = time, log2file` |
| Output dir | cwd only | `--output` / `-o` flag |

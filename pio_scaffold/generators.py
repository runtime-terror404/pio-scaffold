from __future__ import annotations

from pathlib import Path

from .platforms import Platform, parse_hclk_from_ioc
from .templates import pico2_cpp, stm32_cpp

GITIGNORE_CONTENT = """.pio/
.vscode/.browse.c_cpp.db*
.vscode/c_cpp_properties.json
.vscode/launch.json
.vscode/ipch/
__pycache__/
*.pyc
INSTRUCTIONS.md
"""

CI_CONTENT = """name: PlatformIO CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
            ~/.platformio/.cache
          key: ${{ runner.os }}-pio
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install PlatformIO
        run: pip install platformio
      - name: Build
        run: pio run
"""


def generate_ini(platform: Platform, config: dict) -> str:
    if platform.key == "pico2":
        return _generate_ini_pico2(platform, config)
    elif platform.key == "stm32":
        return _generate_ini_stm32(platform, config)
    else:
        raise ValueError(f"Unsupported platform: {platform.key}")


def _generate_ini_pico2(platform: Platform, config: dict) -> str:
    board = platform.boards[config.get("board", "weact")]
    framework = config.get("framework", "arduino")
    core = config.get("core", "earlephilhower")
    baud = config.get("baud", 115200)
    log = config.get("log", True)
    board_id = board.extra_ini.get("board", "rpipico2")
    max_size = board.upload_maximum_size

    lines = ["[env]"]
    lines.append("platform = https://github.com/maxgerhardt/platform-raspberrypi.git")
    lines.append(f"board = {board_id}")
    lines.append(f"framework = {framework}")
    if core:
        lines.append(f"board_build.core = {core}")
    if max_size:
        lines.append(f"board_upload.maximum_size = {max_size}")
    lines.append(f"monitor_speed = {baud}")
    if log:
        lines.append("monitor_filters = time, log2file")
    libs = config.get("libs", [])
    if libs:
        lines.append(f"lib_deps = {', '.join(libs)}")
    lines.append("")

    envs = config.get("envs", ["usb", "dap"])
    if "usb" in envs:
        lines.append("; Default environment: Flashes via USB-C (1200bps touch)")
        lines.append("[env:usb]")
        lines.append("")
    if "dap" in envs:
        lines.append("; Debug environment: Flashes via SWD DAPLink")
        lines.append("[env:dap]")
        lines.append("; upload_protocol = cmsis-dap")
        lines.append("")

    return "\n".join(lines)


def _generate_ini_stm32(platform: Platform, config: dict) -> str:
    ioc_path = config.get("ioc")
    board_id = config.get("board_id", "genericSTM32F411CE")
    debug = config.get("debug", "stlink")
    baud = config.get("baud", 115200)
    log = config.get("log", True)
    swo = config.get("swo", True)

    from .platforms import DebugProbe

    probe = platform.debug_probes.get(debug, platform.debug_probes["stlink"])

    lines = ["[platformio]"]
    lines.append(f"src_dir = {config.get('src_dir', 'Core/Src')}")
    lines.append(f"include_dir = {config.get('include_dir', 'Core/Inc')}")
    lines.append("")

    lines.append("[env]")
    lines.append("platform = ststm32")
    lines.append(f"board = {board_id}")
    lines.append("framework = stm32cube")
    lines.append(f"upload_protocol = {probe.upload_protocol}")
    lines.append(f"debug_tool = {probe.debug_tool}")
    lines.append(f"monitor_speed = {baud}")
    if log:
        lines.append("monitor_filters = time, log2file")
    libs = config.get("libs", [])
    if libs:
        lines.append(f"lib_deps = {', '.join(libs)}")
    if swo:
        lines.append("extra_scripts = swo_trace.py")
    lines.append("")

    lines.append(f"[env:{board_id}]")
    lines.append("")

    return "\n".join(lines)


def generate_main_cpp(platform: Platform, config: dict) -> str:
    if platform.key == "pico2":
        return pico2_cpp(config)
    elif platform.key == "stm32":
        return stm32_cpp(config)
    else:
        raise ValueError(f"Unsupported platform: {platform.key}")


def generate_extras(platform: Platform, config: dict) -> dict[str, str]:
    extras: dict[str, str] = {}
    if platform.key == "stm32" and config.get("swo", True):
        extras["swo_trace.py"] = _generate_swo_script(platform, config)
    return extras


def _generate_swo_script(platform: Platform, config: dict) -> str:
    mcu_family = config.get("mcu_family", "f4")
    probe_id = config.get("debug", "stlink")
    probe = platform.debug_probes.get(probe_id, platform.debug_probes["stlink"])

    ioc_path = config.get("ioc")
    if ioc_path:
        hclk = parse_hclk_from_ioc(ioc_path)
        if hclk is None:
            hclk = 100000000
            hclk_comment = " (default — RCC.HCLKFreq_Value not found in .ioc)"
        else:
            hclk_comment = f" (parsed from .ioc: {hclk} Hz)"
    else:
        hclk = 100000000
        hclk_comment = " (default — no .ioc provided)"

    interface = probe.openocd_interface
    target = probe.openocd_target_fmt.format(fam=mcu_family)
    tpiu_prefix = f"stm32{mcu_family}x"

    return f'''Import("env")

# OpenOCD SWO trace — HCLK={hclk}{hclk_comment}
openocd_cmd = 'openocd -c "debug_level 1" -f {interface} -f {target} -c "init; reset halt; {tpiu_prefix}.tpiu configure -protocol uart -traceclk {hclk} -output /dev/stdout -formatter off; {tpiu_prefix}.tpiu enable; itm port 0 on; resume"'

env.AddCustomTarget(
    name="swo_trace",
    dependencies=None,
    actions=[openocd_cmd],
    title="Start SWO Monitor",
    description="Streams SWO debug data via OpenOCD"
)
'''


def generate_gitignore() -> str:
    return GITIGNORE_CONTENT


def generate_ci() -> str:
    return CI_CONTENT


def generate_instructions_md(platform: Platform, config: dict) -> str:
    if platform.key == "stm32":
        return _instructions_stm32(config)
    elif platform.key == "pico2":
        return _instructions_pico2(config)
    else:
        raise ValueError(f"Unsupported platform: {platform.key}")


def _instructions_stm32(config: dict) -> str:
    board_id = config.get("board_id", "genericSTM32F411CE")
    return f"""# Project Context

This project was scaffolded by [pio-scaffold](https://github.com/runtime-terror404/pio-scaffold) — a CLI
that converts STM32CubeMX projects into PlatformIO projects.

## Project structure

- **`platformio.ini`** — Read this first. It defines the build config, board,
  framework, and dependencies. `src_dir` and `include_dir` point to the
  CubeMX-generated source tree.
- **`Core/Src/`** — Main source directory (CubeMX HAL code lives here)
- **`Core/Inc/`** — Main include directory (CubeMX HAL headers live here)
- **`swo_trace.py`** — OpenOCD SWO trace script (if enabled)

## Framework

This project uses **STM32Cube HAL** (`framework = stm32cube`,
`board = {board_id}`). Write HAL APIs — `HAL_GPIO_WritePin()`,
`HAL_UART_Transmit()`, `HAL_Delay()`, etc. — not Arduino-style code.
Do not use `setup()`/`loop()`, `digitalWrite()`, or `Serial` unless the user
explicitly asks to switch frameworks.

## Adding libraries

Use `lib_deps` in `platformio.ini`. To find libraries, use the **pio-hunt**
skill — but verify findings are HAL-compatible, not Arduino-only. Many
PlatformIO libraries target Arduino; they won't work here without porting.

## Build

```bash
pio run
pio run --target upload
```
"""


def _instructions_pico2(config: dict) -> str:
    framework = config.get("framework", "arduino")
    return f"""# Project Context

This project was scaffolded by [pio-scaffold](https://github.com/runtime-terror404/pio-scaffold).

## Project structure

- **`platformio.ini`** — Read this first. It defines the build config, board,
  framework, and dependencies.
- **`src/main.cpp`** — Main source file

## Framework

This project uses **{framework}** framework. Standard PlatformIO / {framework}
conventions apply.

## Adding libraries

Use `lib_deps` in `platformio.ini`. To find libraries, use the **pio-hunt**
skill — it searches the PlatformIO registry for compatible, well-rated
libraries.

## Build

```bash
pio run
pio run --target upload
```
"""


def write_project(platform: Platform, config: dict, dry_run: bool = False) -> list[Path]:
    output_dir = Path(config.get("output", "."))
    created: list[Path] = []

    def _write(path: Path, content: str):
        created.append(path)
        if dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    # platformio.ini
    _write(output_dir / "platformio.ini", generate_ini(platform, config))

    # INSTRUCTIONS.md — project guidance for AI assistants
    _write(output_dir / "INSTRUCTIONS.md", generate_instructions_md(platform, config))

    # src/main.cpp — only for pico2 (STM32 uses CubeMX sources in Core/Src)
    if platform.key != "stm32":
        _write(output_dir / "src" / "main.cpp", generate_main_cpp(platform, config))

    # Extra files (SWO script, etc.)
    for filename, content in generate_extras(platform, config).items():
        _write(output_dir / filename, content)

    # .gitignore
    if config.get("git"):
        _write(output_dir / ".gitignore", generate_gitignore())

    # GitHub Actions CI
    if config.get("ci"):
        workflows_dir = output_dir / ".github" / "workflows"
        _write(workflows_dir / "pio_build.yml", generate_ci())

    return created

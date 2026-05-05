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
        lines.append("upload_protocol = cmsis-dap")
        lines.append("debug_tool = cmsis-dap")
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

    # CubeMX folder routing
    src_dir = config.get("src_dir", "Core/Src")
    include_dir = config.get("include_dir", "Core/Inc")
    lines.append(f"src_dir = {src_dir}")
    lines.append(f"include_dir = {include_dir}")
    lines.append("")

    lines.append("[env]")
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
        # If hclk is the default, add a comment
        if hclk == 100000000:
            hclk_comment = "  # default HCLK (no RCC.HCLKFreq_Value found in .ioc)"
        else:
            hclk_comment = "  # parsed from RCC.HCLKFreq_Value in .ioc"
    else:
        hclk = 100000000
        hclk_comment = "  # default (no .ioc provided)"

    interface = probe.openocd_interface
    target = probe.openocd_target_fmt.format(fam=mcu_family)
    tpiu_prefix = f"stm32{mcu_family}x"

    return f'''Import("env")

# OpenOCD SWO trace — dynamic HCLK from .ioc
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

    # src/main.cpp
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

from __future__ import annotations

import sys
from pathlib import Path

from .platforms import (
    Platform,
    PICO2_BOARDS,
    STM32_DEBUG_PROBES,
    find_ioc_files,
    get_platform,
    list_platforms,
    parse_mcu_from_ioc,
)


def _prompt(prompt: str, default: str = "") -> str:
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    return input(f"{prompt}: ").strip()


def _confirm(prompt: str, default: bool = True) -> bool:
    yn = "Y/n" if default else "y/N"
    answer = input(f"{prompt} [{yn}]: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _pick_numbered(items: list[str], prompt: str, default: int = 1) -> int:
    print(f"\n{prompt}")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    while True:
        choice = input(f"Select [{default}]: ").strip()
        if not choice:
            return default
        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                return idx
            print(f"  Enter 1-{len(items)}")
        except ValueError:
            print(f"  Enter a number 1-{len(items)}")


def run_wizard() -> tuple[Platform, dict]:
    print("=== pio-scaffold interactive wizard ===\n")

    # ── Platform selection ──────────────────────────────────────────────
    platforms = list_platforms()
    idx = _pick_numbered(platforms, "Select target platform:")
    platform_key = platforms[idx - 1]
    platform = get_platform(platform_key)

    config: dict = {}

    # ── Project name ────────────────────────────────────────────────────
    default_name = Path.cwd().name
    config["name"] = _prompt("Project name", default_name)
    config["output"] = _prompt("Output directory", str(Path.cwd()))

    # ── Platform-specific questions ─────────────────────────────────────
    if platform.key == "pico2":
        _wizard_pico2(platform, config)
    elif platform.key == "stm32":
        _wizard_stm32(platform, config)

    # ── Common options ──────────────────────────────────────────────────
    libs = _prompt("Library dependencies (comma-separated, or empty)", "")
    config["libs"] = [lib.strip() for lib in libs.split(",") if lib.strip()]

    config["git"] = _confirm("Initialize git repository?", False)
    config["ci"] = _confirm("Generate GitHub Actions CI?", False)

    # ── Summary & confirm ───────────────────────────────────────────────
    print("\n--- Configuration Summary ---")
    print(f"  Platform:   {platform.name}")
    if platform.key == "pico2":
        board = platform.boards.get(config.get("board", "weact"))
        print(f"  Board:      {board.name if board else config.get('board')}")
        print(f"  Framework:  {config.get('framework', 'arduino')}")
        print(f"  Envs:       {', '.join(config.get('envs', ['usb', 'dap']))}")
    elif platform.key == "stm32":
        ioc = config.get("ioc")
        print(f"  .ioc file:  {ioc.name if ioc else 'none'}")
        debug = config.get("debug", "stlink")
        probe = platform.debug_probes.get(debug)
        print(f"  Debug:      {probe.name if probe else debug}")
        print(f"  SWO trace:  {config.get('swo', True)}")
    print(f"  Baud:       {config.get('baud', 115200)}")
    print(f"  Log:        {config.get('log', True)}")
    print(f"  Libs:       {', '.join(config.get('libs', [])) or 'none'}")
    print(f"  Git:        {config.get('git', False)}")
    print(f"  CI:         {config.get('ci', False)}")
    print(f"  Output:     {config.get('output', '.')}")
    print()

    if not _confirm("Proceed with these settings?"):
        print("Aborted.")
        sys.exit(0)

    return platform, config


def _wizard_pico2(platform: Platform, config: dict):
    # Board selection
    board_ids = list(platform.boards.keys())
    board_names = [f"{b.name} ({b.id})" for b in platform.boards.values()]
    idx = _pick_numbered(board_names, "Select board variant:")
    config["board"] = board_ids[idx - 1]

    # Framework
    idx = _pick_numbered(platform.frameworks, "Select framework:")
    config["framework"] = platform.frameworks[idx - 1]

    # Arduino core (only if arduino framework)
    if config["framework"] == "arduino":
        cores = ["earlephilhower", "mbed"]
        idx = _pick_numbered(cores, "Select Arduino core:")
        config["core"] = cores[idx - 1]

    # Environments
    print("\nEnvironments to generate:")
    print("  [1] USB only")
    print("  [2] DAP only")
    print("  [3] Both USB + DAP")
    choice = input("Select [3]: ").strip() or "3"
    env_map = {"1": ["usb"], "2": ["dap"], "3": ["usb", "dap"]}
    config["envs"] = env_map.get(choice, ["usb", "dap"])

    # Baud
    baud = _prompt("Serial monitor baud rate", "115200")
    config["baud"] = int(baud)

    # Log
    config["log"] = _confirm("Add monitor_filters (timestamp + log2file)?", True)


def _wizard_stm32(platform: Platform, config: dict):
    # Find .ioc files
    cwd = Path(config.get("output", "."))
    ioc_files = find_ioc_files(cwd)

    if not ioc_files:
        print("\n[WARNING] No .ioc file found in output directory.")
        print("You can specify one later with --ioc, or generate from CubeMX first.")
        ioc_path = None
    elif len(ioc_files) == 1:
        ioc_path = ioc_files[0]
        print(f"\nFound .ioc file: {ioc_path.name}")
    else:
        items = [f"{f.name}" for f in ioc_files]
        idx = _pick_numbered(items, f"Found {len(ioc_files)} .ioc files. Select one:")
        ioc_path = ioc_files[idx - 1]

    if ioc_path:
        config["ioc"] = ioc_path
        try:
            mcu_name, board_id, mcu_family = parse_mcu_from_ioc(ioc_path)
            config["board_id"] = board_id
            config["mcu_family"] = mcu_family
            print(f"  MCU: {mcu_name}  →  Board: {board_id}  Family: stm32{mcu_family}x")
        except ValueError as e:
            print(f"  [WARNING] {e}")

    # Debug probe
    probe_ids = list(platform.debug_probes.keys())
    probe_names = [f"{p.name}" for p in platform.debug_probes.values()]
    idx = _pick_numbered(probe_names, "Select debug probe:")
    config["debug"] = probe_ids[idx - 1]

    # SWO
    config["swo"] = _confirm("Generate SWO trace script?", True)

    # Baud
    baud = _prompt("Serial monitor baud rate", "115200")
    config["baud"] = int(baud)

    # Log
    config["log"] = _confirm("Add monitor_filters (timestamp + log2file)?", True)

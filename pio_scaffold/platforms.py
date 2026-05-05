from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Board:
    id: str
    name: str
    core: Optional[str] = None
    upload_maximum_size: Optional[int] = None
    extra_ini: dict[str, str] = field(default_factory=dict)


@dataclass
class DebugProbe:
    id: str
    name: str
    upload_protocol: str
    debug_tool: str
    openocd_interface: str = ""
    openocd_target_fmt: str = "stm32{fam}x.cfg"


@dataclass
class Platform:
    name: str
    key: str
    boards: dict[str, Board] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    default_envs: list[str] = field(default_factory=list)
    debug_probes: dict[str, DebugProbe] = field(default_factory=dict)


# ── Pico2 Platform ──────────────────────────────────────────────────────────

PICO2_BOARDS = {
    "weact": Board(
        id="weact",
        name="WeAct RP2350A",
        core="earlephilhower",
        upload_maximum_size=16777216,
    ),
    "pico2": Board(
        id="pico2",
        name="Official Raspberry Pi Pico 2 (RP2350)",
        core="earlephilhower",
        upload_maximum_size=16777216,
        extra_ini={"board": "rpipico2"},
    ),
    "pico": Board(
        id="pico",
        name="Original Raspberry Pi Pico (RP2040)",
        core="earlephilhower",
        extra_ini={"board": "pico"},
    ),
    "official": Board(
        id="official",
        name="Raspberry Pi Pico 2 (official)",
        core="earlephilhower",
        upload_maximum_size=16777216,
        extra_ini={"board": "rpipico2"},
    ),
    "pimoroni": Board(
        id="pimoroni",
        name="Pimoroni Pico Plus 2",
        core="earlephilhower",
        upload_maximum_size=16777216,
        extra_ini={"board": "pimoroni_pico2"},
    ),
    "custom": Board(
        id="custom",
        name="Custom RP2350 board",
        core="earlephilhower",
        upload_maximum_size=16777216,
    ),
}

PICO2_PLATFORM = Platform(
    name="Raspberry Pi Pico / RP2350 / RP2040",
    key="pico2",
    boards=PICO2_BOARDS,
    frameworks=["arduino", "pico-sdk"],
    default_envs=["usb", "dap"],
)

# ── STM32 Platform ──────────────────────────────────────────────────────────

STM32_DEBUG_PROBES = {
    "stlink": DebugProbe(
        id="stlink",
        name="ST-Link (built-in Nucleo/Discovery)",
        upload_protocol="stlink",
        debug_tool="stlink",
        openocd_interface="interface/stlink.cfg",
    ),
    "cmsis-dap": DebugProbe(
        id="cmsis-dap",
        name="CMSIS-DAP",
        upload_protocol="cmsis-dap",
        debug_tool="cmsis-dap",
        openocd_interface="interface/cmsis-dap.cfg",
    ),
    "jlink": DebugProbe(
        id="jlink",
        name="J-Link (Segger)",
        upload_protocol="jlink",
        debug_tool="jlink",
        openocd_interface="interface/jlink.cfg",
    ),
}

STM32_PLATFORM = Platform(
    name="STM32 (CubeMX / CubeIDE)",
    key="stm32",
    frameworks=["stm32cube"],
    debug_probes=STM32_DEBUG_PROBES,
)


def get_platform(name: str) -> Platform:
    registry = {"pico2": PICO2_PLATFORM, "stm32": STM32_PLATFORM}
    if name not in registry:
        raise ValueError(f"Unknown platform: {name}. Choose: {', '.join(registry)}")
    return registry[name]


def list_platforms() -> list[str]:
    return ["pico2", "stm32"]


# ── .ioc helpers ────────────────────────────────────────────────────────────

_IOC_MCU_RE = re.compile(r"^Mcu\.UserName=(.+)$", re.MULTILINE)
_IOC_HCLK_RE = re.compile(r"^RCC\.HCLKFreq_Value=(\d+)", re.MULTILINE)
_STM32_FAMILY_RE = re.compile(r"(STM32[A-Z0-9]{6})")


def find_ioc_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.ioc"))


def parse_mcu_from_ioc(ioc_path: Path) -> tuple[str, str, str]:
    """Return (mcu_name, board_id, mcu_family) from a .ioc file."""
    content = ioc_path.read_text(encoding="utf-8", errors="replace")

    mcu_match = _IOC_MCU_RE.search(content)
    if not mcu_match:
        raise ValueError(f"No Mcu.UserName found in {ioc_path}")

    mcu_name = mcu_match.group(1).strip()
    family_match = _STM32_FAMILY_RE.search(mcu_name)
    if family_match:
        clean_mcu = family_match.group(1)
        board_id = f"generic{clean_mcu}"
        mcu_family = clean_mcu[5:7].lower()
    else:
        board_id = "genericSTM32F411CE"
        mcu_family = "f4"

    return mcu_name, board_id, mcu_family


def parse_hclk_from_ioc(ioc_path: Path) -> Optional[int]:
    """Parse RCC.HCLKFreq_Value from .ioc; None if not found."""
    content = ioc_path.read_text(encoding="utf-8", errors="replace")
    hclk_match = _IOC_HCLK_RE.search(content)
    if hclk_match:
        return int(hclk_match.group(1))
    return None

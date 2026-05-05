from __future__ import annotations


def pico2_cpp(config: dict | None = None) -> str:
    config = config or {}
    framework = config.get("framework", "arduino")
    board = config.get("board", "weact")
    core_name = "M0+" if board == "pico" else "M33"

    if framework == "pico-sdk":
        return f"""#include <pico/stdlib.h>

int main() {{
    while (true) {{
    }}
    return 0;
}}
"""

    return f"""#include <Arduino.h>

// ==========================================
// CORE 0 — runs on the first {core_name} core
// ==========================================
// setup(): runs once at boot — put init code here (pins, serial, peripherals)
void setup() {{
}}

// loop(): runs repeatedly after setup() — put your main logic here
void loop() {{
}}

// ==========================================
// CORE 1 — runs on the second {core_name} core
// ==========================================
// setup1(): runs once at boot on core 1 — init core-1 resources here
void setup1() {{
}}

// loop1(): runs repeatedly on core 1 — put concurrent tasks here
void loop1() {{
}}
"""


def stm32_cpp(config: dict | None = None) -> str:
    config = config or {}
    mcu_family = config.get("mcu_family", "f4")
    return f"""#include "stm32{mcu_family}xx_hal.h"

int main(void) {{
    HAL_Init();
    while (1) {{
    }}
}}
"""

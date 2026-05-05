from __future__ import annotations


def pico2_cpp(config: dict | None = None) -> str:
    config = config or {}
    return """#include <Arduino.h>

// ==========================================
// CORE 0 — runs on the first M33 core
// ==========================================
// setup(): runs once at boot — put init code here (pins, serial, peripherals)
void setup() {
}

// loop(): runs repeatedly after setup() — put your main logic here
void loop() {
}

// ==========================================
// CORE 1 — runs on the second M33 core
// ==========================================
// setup1(): runs once at boot on core 1 — init core-1 resources here
void setup1() {
}

// loop1(): runs repeatedly on core 1 — put concurrent tasks here
void loop1() {
}
"""


def stm32_cpp(config: dict | None = None) -> str:
    config = config or {}
    return """#include <Arduino.h>

// setup(): runs once at boot — put init code here (pins, serial, peripherals)
void setup() {
}

// loop(): runs repeatedly after setup() — put your main logic here
void loop() {
}
"""

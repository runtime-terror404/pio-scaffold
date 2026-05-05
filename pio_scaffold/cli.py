from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from .generators import write_project
from .platforms import (
    PICO2_BOARDS,
    STM32_DEBUG_PROBES,
    find_ioc_files,
    get_platform,
    list_platforms,
    parse_mcu_from_ioc,
)
from .wizard import run_wizard

app = typer.Typer(name="pio-scaffold", help="Unified PlatformIO project scaffolding CLI")

presets_app = typer.Typer(help="Manage configuration presets")
app.add_typer(presets_app, name="presets")

PRESETS_DIR = Path.home() / ".config" / "pio-scaffold"
PRESETS_FILE = PRESETS_DIR / "presets.json"


def _load_presets() -> dict:
    if not PRESETS_FILE.exists():
        return {}
    return json.loads(PRESETS_FILE.read_text())


def _save_presets(presets: dict):
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2))


def _check_pio():
    if not shutil.which("pio"):
        typer.echo(
            "Error: 'pio' command not found. Install PlatformIO: https://platformio.org/install",
            err=True,
        )
        raise typer.Exit(code=1)


def _pick_ioc(glob_dir: Path, specified: Optional[Path], yes: bool) -> Optional[Path]:
    if specified:
        if not specified.exists():
            typer.echo(f"Error: .ioc file not found: {specified}", err=True)
            raise typer.Exit(code=1)
        return specified.resolve()

    ioc_files = find_ioc_files(glob_dir)
    if not ioc_files:
        typer.echo("Warning: No .ioc file found. Use --ioc to specify one.")
        return None

    if len(ioc_files) == 1:
        return ioc_files[0]

    if yes:
        typer.echo(f"Warning: Multiple .ioc files found, using first: {ioc_files[0].name}")
        return ioc_files[0]

    typer.echo(f"Found {len(ioc_files)} .ioc files:")
    for i, f in enumerate(ioc_files, 1):
        typer.echo(f"  [{i}] {f.name}")

    while True:
        choice = input(f"Select one [1]: ").strip()
        if not choice:
            return ioc_files[0]
        try:
            idx = int(choice)
            if 1 <= idx <= len(ioc_files):
                return ioc_files[idx - 1]
        except ValueError:
            pass
        typer.echo(f"Enter 1-{len(ioc_files)}")


def _merge_config(cli_config: dict, preset_config: dict) -> dict:
    """Merge CLI config over preset config — CLI values take precedence."""
    merged = {**preset_config, **{k: v for k, v in cli_config.items() if v is not None}}
    return merged


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    name: str = typer.Option(None, "--name", help="Project name (default: directory basename)"),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Target output directory"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview files without writing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    preset: Optional[str] = typer.Option(
        None, "--preset", "-p", help="Load configuration from a saved preset"
    ),
):
    _check_pio()

    # If a subcommand was invoked, let Typer handle it
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand → launch wizard
    platform, config = run_wizard()
    config.setdefault("name", name or Path.cwd().name)
    config.setdefault("output", str(output.resolve()))
    config.setdefault("log", True)

    _execute(platform, config, dry_run, yes)


def _execute(platform, config: dict, dry_run: bool, yes: bool):
    if dry_run:
        typer.echo("\n=== DRY RUN — no files will be written ===\n")

    if not yes and not dry_run:
        typer.echo(f"\nAbout to create project in: {config.get('output', '.')}")
        answer = input("Continue? [Y/n]: ").strip().lower()
        if answer and answer not in ("y", "yes"):
            typer.echo("Aborted.")
            raise typer.Exit(0)

    created = write_project(platform, config, dry_run=dry_run)

    typer.echo(f"\n{'Would create' if dry_run else 'Created'} {len(created)} file(s):")
    for f in created:
        typer.echo(f"  {'[DRY RUN]' if dry_run else '  + '} {f}")

    if not dry_run and config.get("git"):
        _maybe_git_init(Path(config.get("output", ".")), config.get("name", ""))

    if not dry_run:
        typer.echo(f"\n[SUCCESS] Project scaffolded successfully!")
        typer.echo("Type 'code .' to open the project.")


def _maybe_git_init(output_dir: Path, project_name: str):
    import subprocess

    repo = output_dir.resolve()
    if (repo / ".git").exists():
        return

    try:
        subprocess.run(
            ["git", "init", str(repo)],
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "add", "-A"],
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", f"Initial scaffold: {project_name}"],
            capture_output=True,
            text=True,
        )
        typer.echo("  + Git repository initialized + initial commit")
    except Exception:
        typer.echo("  Warning: git init failed (git may not be installed)")


# ── pico2 subcommand ────────────────────────────────────────────────────────

@app.command()
def pico2(
    ctx: typer.Context,
    board: str = typer.Option(
        "weact", "--board", "-b", help="Board variant: pico, pico2, weact, official, pimoroni, custom"
    ),
    framework: str = typer.Option(
        "arduino", "--framework", "-f", help="Framework: arduino, pico-sdk"
    ),
    core: Optional[str] = typer.Option(
        None, "--core", "-c", help="Arduino core: earlephilhower, mbed"
    ),
    envs: str = typer.Option(
        "usb,dap", "--envs", "-e", help="Environments (comma-separated): usb, dap"
    ),
    baud: int = typer.Option(115200, "--baud", help="Serial monitor baud rate"),
    log: bool = typer.Option(True, "--log/--no-log", help="Add monitor_filters (timestamp + log2file)"),
    libs: Optional[str] = typer.Option(
        None, "--libs", "-l", help="Comma-separated lib_deps"
    ),
    git: bool = typer.Option(False, "--git", help="Initialize git repository"),
    ci: bool = typer.Option(False, "--ci", help="Generate GitHub Actions CI workflow"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview files without writing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    name: str = typer.Option(None, "--name", help="Project name (default: directory basename)"),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Target output directory"
    ),
    preset: Optional[str] = typer.Option(
        None, "--preset", "-p", help="Load configuration from a saved preset"
    ),
):
    _check_pio()
    platform = get_platform("pico2")

    board_ids = list(PICO2_BOARDS.keys())
    if board not in board_ids:
        typer.echo(f"Error: unknown board '{board}'. Choose: {', '.join(board_ids)}", err=True)
        raise typer.Exit(code=1)

    env_list = [e.strip() for e in envs.split(",") if e.strip() in ("usb", "dap")]
    if not env_list:
        typer.echo("Error: --envs must include 'usb' and/or 'dap'", err=True)
        raise typer.Exit(code=1)

    lib_list = [lib.strip() for lib in (libs or "").split(",") if lib.strip()]

    config = {
        "board": board,
        "framework": framework,
        "core": core or "earlephilhower",
        "envs": env_list,
        "baud": baud,
        "log": log,
        "libs": lib_list,
        "git": git,
        "ci": ci,
        "name": name or output.resolve().name,
        "output": str(output.resolve()),
    }

    if preset:
        presets_data = _load_presets()
        if preset in presets_data:
            config = _merge_config(config, presets_data[preset])
        else:
            typer.echo(f"Warning: preset '{preset}' not found, ignoring.")

    _execute(platform, config, dry_run, yes)


# ── stm32 subcommand ────────────────────────────────────────────────────────

@app.command()
def stm32(
    ctx: typer.Context,
    ioc: Optional[Path] = typer.Option(
        None, "--ioc", help="Path to .ioc file (auto-detected if omitted)"
    ),
    debug: str = typer.Option(
        "stlink", "--debug", "-d", help="Debug probe: stlink, cmsis-dap, jlink"
    ),
    swo: bool = typer.Option(True, "--swo/--no-swo", help="Generate SWO trace script"),
    baud: int = typer.Option(115200, "--baud", help="Serial monitor baud rate"),
    log: bool = typer.Option(True, "--log/--no-log", help="Add monitor_filters (timestamp + log2file)"),
    libs: Optional[str] = typer.Option(
        None, "--libs", "-l", help="Comma-separated lib_deps"
    ),
    git: bool = typer.Option(False, "--git", help="Initialize git repository"),
    ci: bool = typer.Option(False, "--ci", help="Generate GitHub Actions CI workflow"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview files without writing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    name: str = typer.Option(None, "--name", help="Project name (default: directory basename)"),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Target output directory"
    ),
    preset: Optional[str] = typer.Option(
        None, "--preset", "-p", help="Load configuration from a saved preset"
    ),
):
    _check_pio()
    platform = get_platform("stm32")

    if debug not in STM32_DEBUG_PROBES:
        valid = ", ".join(STM32_DEBUG_PROBES.keys())
        typer.echo(f"Error: unknown debug probe '{debug}'. Choose: {valid}", err=True)
        raise typer.Exit(code=1)

    output_resolved = output.resolve()
    glob_dir = output_resolved if output_resolved.is_dir() else output_resolved.parent

    selected_ioc = _pick_ioc(glob_dir, ioc, yes)

    board_id = "genericSTM32F411CE"
    mcu_family = "f4"
    mcu_name = "unknown"
    src_dir = "Core/Src"
    include_dir = "Core/Inc"

    if selected_ioc:
        try:
            mcu_name, board_id, mcu_family = parse_mcu_from_ioc(selected_ioc)
            typer.echo(f"Parsed .ioc: MCU={mcu_name}  Board={board_id}  Family=stm32{mcu_family}x")
        except ValueError as e:
            typer.echo(f"Warning: {e}")

        ioc_name = selected_ioc.stem
        if not any(gi.name == f"{ioc_name}.ioc" for gi in glob_dir.glob("*.ioc")):
            ioc_name = glob_dir.name
    else:
        ioc_name = glob_dir.name

    lib_list = [lib.strip() for lib in (libs or "").split(",") if lib.strip()]

    config = {
        "ioc": selected_ioc,
        "board_id": board_id,
        "mcu_family": mcu_family,
        "debug": debug,
        "swo": swo,
        "baud": baud,
        "log": log,
        "libs": lib_list,
        "git": git,
        "ci": ci,
        "name": name or ioc_name,
        "output": str(output_resolved),
        "src_dir": src_dir,
        "include_dir": include_dir,
    }

    if preset:
        presets_data = _load_presets()
        if preset in presets_data:
            config = _merge_config(config, presets_data[preset])
        else:
            typer.echo(f"Warning: preset '{preset}' not found, ignoring.")

    _execute(platform, config, dry_run, yes)


# ── presets subcommand group ────────────────────────────────────────────────

@presets_app.command("save")
def presets_save(
    name: str = typer.Argument(..., help="Preset name to save as"),
    board: Optional[str] = typer.Option(
        None, "--board", "-b", help="Board variant"
    ),
    framework: Optional[str] = typer.Option(
        None, "--framework", "-f", help="Framework"
    ),
    platform: str = typer.Option(
        "pico2", "--platform", help="Target platform: pico2, stm32"
    ),
    baud: int = typer.Option(115200, "--baud", help="Serial monitor baud rate"),
    libs: Optional[str] = typer.Option(
        None, "--libs", "-l", help="Comma-separated lib_deps"
    ),
):
    presets = _load_presets()
    if name in presets:
        typer.echo(f"Preset '{name}' already exists. Use another name or delete it first.")
        raise typer.Exit(code=1)

    lib_list = [lib.strip() for lib in (libs or "").split(",") if lib.strip()]

    presets[name] = {
        "platform": platform,
        "board": board,
        "framework": framework,
        "baud": baud,
        "libs": lib_list,
    }
    _save_presets(presets)
    typer.echo(f"Preset '{name}' saved.")


@presets_app.command("load")
def presets_load(
    name: str = typer.Argument(..., help="Preset name to load"),
):
    presets = _load_presets()
    if name not in presets:
        typer.echo(f"Preset '{name}' not found.", err=True)
        presets_list_impl()
        raise typer.Exit(code=1)
    typer.echo(json.dumps(presets[name], indent=2))


@presets_app.command("list")
def presets_list():
    presets_list_impl()


@presets_app.command("delete")
def presets_delete(
    name: str = typer.Argument(..., help="Preset name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    presets = _load_presets()
    if name not in presets:
        typer.echo(f"Preset '{name}' not found.", err=True)
        raise typer.Exit(code=1)
    if not force:
        answer = input(f"Delete preset '{name}'? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            typer.echo("Aborted.")
            return
    del presets[name]
    _save_presets(presets)
    typer.echo(f"Preset '{name}' deleted.")


def presets_list_impl():
    presets = _load_presets()
    if not presets:
        typer.echo("No presets saved.")
        return
    typer.echo("Saved presets:")
    for name, cfg in sorted(presets.items()):
        platform = cfg.get("platform", "?")
        board = cfg.get("board", "default")
        baud = cfg.get("baud", 115200)
        libs = ", ".join(cfg.get("libs", [])) or "none"
        typer.echo(f"  {name}")
        typer.echo(f"    platform={platform}  board={board}  baud={baud}  libs={libs}")


if __name__ == "__main__":
    app()

#!/usr/bin/env bash
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/<USER>/scripts.git"   # TODO: update after first push
INSTALL_DIR="${HOME}/.local/share/pio-scaffold"
BIN_DIR="${HOME}/.local/bin"
BIN_NAME="pio-scaffold"

# ── Colors ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { printf "${GREEN}[+]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err()   { printf "${RED}[x]${NC} %s\n" "$*" >&2; }

abort() {
    err "$*"
    err "Installation aborted."
    exit 1
}

# ── Pre-flight checks ─────────────────────────────────────────────────────

info "pio-scaffold installer"

# Python 3.8+
if ! command -v python3 >/dev/null 2>&1; then
    abort "python3 not found. Install Python 3.8+ first: https://www.python.org/downloads/"
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    abort "Python 3.8+ required, found ${PY_VERSION}."
fi
info "Python ${PY_VERSION} — OK"

# Git
if ! command -v git >/dev/null 2>&1; then
    abort "git not found. Install git first: sudo apt install git / sudo pacman -S git"
fi
info "git — OK"

# ── Install typer ─────────────────────────────────────────────────────────

if ! python3 -c "import typer" >/dev/null 2>&1; then
    warn "typer not installed. Installing..."
    python3 -m pip install --user typer || abort "Failed to install typer. Try: pip install typer"
    info "typer installed"
else
    info "typer — OK ($(python3 -c 'import typer; print(typer.__version__)'))"
fi

# ── Check PlatformIO ──────────────────────────────────────────────────────

if ! command -v pio >/dev/null 2>&1; then
    warn "PlatformIO CLI (pio) not found."
    warn "Install it from: https://platformio.org/install"
    warn "Or: pip install platformio"
    warn "pio-scaffold will not work without PlatformIO."
else
    info "pio — OK"
fi

# ── Clone / update repo ───────────────────────────────────────────────────

if [ -d "${INSTALL_DIR}" ]; then
    info "Updating existing installation at ${INSTALL_DIR}..."
    git -C "${INSTALL_DIR}" pull --ff-only || warn "git pull failed — continuing with existing checkout"
else
    info "Cloning ${REPO_URL} → ${INSTALL_DIR}..."
    mkdir -p "$(dirname "${INSTALL_DIR}")"
    git clone "${REPO_URL}" "${INSTALL_DIR}" || abort "Failed to clone repo. Check the URL: ${REPO_URL}"
fi

# ── Symlink into PATH ────────────────────────────────────────────────────

mkdir -p "${BIN_DIR}"

if [ -L "${BIN_DIR}/${BIN_NAME}" ] || [ -f "${BIN_DIR}/${BIN_NAME}" ]; then
    info "Removing existing ${BIN_NAME} symlink..."
    rm -f "${BIN_DIR}/${BIN_NAME}"
fi

ln -s "${INSTALL_DIR}/pio-scaffold" "${BIN_DIR}/${BIN_NAME}"
chmod +x "${INSTALL_DIR}/pio-scaffold"
info "Linked ${INSTALL_DIR}/pio-scaffold → ${BIN_DIR}/${BIN_NAME}"

# ── PATH check ────────────────────────────────────────────────────────────

if ! echo "${PATH}" | tr ':' '\n' | grep -qxF "${BIN_DIR}"; then
    warn "${BIN_DIR} is not in your PATH."
    warn "Add this to your ~/.bashrc or ~/.zshrc:"
    warn ""
    warn "  export PATH=\"\${HOME}/.local/bin:\${PATH}\""
    warn ""
fi

# ── Verify ────────────────────────────────────────────────────────────────

export PATH="${BIN_DIR}:${PATH}"

if command -v pio-scaffold >/dev/null 2>&1; then
    info "Installation complete!"
    pio-scaffold --help
    echo ""
    info "Run 'pio-scaffold' to start the interactive wizard."
else
    warn "Installed but pio-scaffold not on current PATH."
    warn "Restart your shell or run: export PATH=\"${BIN_DIR}:\${PATH}\""
fi

# ── Reminder ──────────────────────────────────────────────────────────────

warn "Remember: PlatformIO must be installed separately if you haven't already:"
echo "  pip install platformio"
echo "  # or: https://platformio.org/install"

#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# whatsapp-osint — One-Command Installer
# 🕵️‍♂️ WhatsApp Beacon (OSINT Tracker)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jasperan/whatsapp-osint/master/install.sh | bash
# ============================================================

REPO_URL="https://github.com/jasperan/whatsapp-osint.git"
PROJECT="whatsapp-osint"
BRANCH="master"
INSTALL_DIR="${PROJECT_DIR:-$(pwd)/$PROJECT}"

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}→${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
fail()    { echo -e "${RED}✗ $1${NC}"; exit 1; }
command_exists() { command -v "$1" &>/dev/null; }

print_banner() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  whatsapp-osint${NC}"
    echo -e "  🕵️‍♂️ WhatsApp Beacon (OSINT Tracker)"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

clone_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        warn "Directory $INSTALL_DIR already exists"
        info "Pulling latest changes..."
        (cd "$INSTALL_DIR" && git pull origin "$BRANCH" 2>/dev/null) || true
    else
        info "Cloning repository..."
        git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || fail "Clone failed. Check your internet connection."
    fi
    success "Repository ready at $INSTALL_DIR"
}

check_prereqs() {
    info "Checking prerequisites..."
    command_exists git || fail "Git is required — https://git-scm.com/"
    success "Git $(git --version | cut -d' ' -f3)"

    PYTHON=""
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            major=${ver%%.*}
            minor=${ver##*.}
            if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
                PYTHON="$cmd"
                break
            fi
        fi
    done
    [ -n "$PYTHON" ] || fail "Python 3.8+ is required — https://www.python.org/downloads/"
    success "Python $($PYTHON --version | cut -d' ' -f2)"
}

install_deps() {
    cd "$INSTALL_DIR"
    info "Creating virtual environment..."
    $PYTHON -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate

    info "Installing dependencies..."
    pip install --upgrade pip -q 2>/dev/null
    pip install -r requirements.txt -q
    success "Dependencies installed"
}

main() {
    print_banner
    check_prereqs
    clone_repo
    install_deps
    print_done
}

print_done() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}Installation complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Location:${NC}  $INSTALL_DIR"
    echo -e "  ${BOLD}Activate:${NC}  source $INSTALL_DIR/.venv/bin/activate"
    echo ""
}

main "$@"

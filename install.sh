#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# whatsapp-osint — One-Command Installer
# 🕵️‍♂️ WhatsApp Beacon (OSINT Tracker)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jasperan/whatsapp-osint/master/install.sh | bash
#
# Override install location:
#   PROJECT_DIR=/opt/myapp curl -fsSL ... | bash
#
# Override repo/branch for testing:
#   REPO_URL=/path/to/local/clone BRANCH=master bash install.sh
# ============================================================

REPO_URL="${REPO_URL:-https://github.com/jasperan/whatsapp-osint.git}"
PROJECT="${PROJECT:-whatsapp-osint}"
BRANCH="${BRANCH:-master}"
INSTALL_DIR="${PROJECT_DIR:-$(pwd)/$PROJECT}"
PKG_MANAGER=""
PACKAGE_INDEX_READY=0
PYTHON=""
BROWSER_PATH=""

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
is_linux() { [ "$(uname -s)" = "Linux" ]; }

print_banner() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  whatsapp-osint${NC}"
    echo -e "  🕵️‍♂️ WhatsApp Beacon (OSINT Tracker)"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

run_as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command_exists sudo; then
        sudo "$@"
    else
        fail "Automatic system package installation needs sudo. Install sudo or rerun this script as root."
    fi
}

detect_package_manager() {
    if [ -n "$PKG_MANAGER" ]; then
        return 0
    fi

    for candidate in apt-get dnf yum pacman zypper apk; do
        if command_exists "$candidate"; then
            PKG_MANAGER="$candidate"
            return 0
        fi
    done

    return 1
}

prepare_package_index() {
    detect_package_manager || fail "Could not detect a supported package manager on this Linux system."

    if [ "$PACKAGE_INDEX_READY" -eq 1 ]; then
        return 0
    fi

    case "$PKG_MANAGER" in
        apt-get)
            info "Updating apt package index..."
            run_as_root env DEBIAN_FRONTEND=noninteractive apt-get update -y
            ;;
        pacman)
            info "Updating pacman package index..."
            run_as_root pacman -Sy --noconfirm
            ;;
        zypper)
            info "Refreshing zypper package metadata..."
            run_as_root zypper --gpg-auto-import-keys --non-interactive refresh
            ;;
        apk)
            info "Updating apk package index..."
            run_as_root apk update
            ;;
        dnf|yum)
            ;;
    esac

    PACKAGE_INDEX_READY=1
}

install_system_packages() {
    detect_package_manager || fail "Could not detect a supported package manager on this Linux system."
    prepare_package_index

    case "$PKG_MANAGER" in
        apt-get)
            run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
            ;;
        dnf)
            run_as_root dnf install -y "$@"
            ;;
        yum)
            run_as_root yum install -y "$@"
            ;;
        pacman)
            run_as_root pacman -S --noconfirm --needed "$@"
            ;;
        zypper)
            run_as_root zypper --non-interactive install "$@"
            ;;
        apk)
            run_as_root apk add --no-cache "$@"
            ;;
        *)
            fail "Unsupported package manager: $PKG_MANAGER"
            ;;
    esac
}

pick_python() {
    PYTHON=""
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            ver=$($cmd -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")' 2>/dev/null) || continue
            major=${ver%%.*}
            minor=${ver##*.}
            if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; }; then
                PYTHON="$cmd"
                return 0
            fi
        fi
    done

    return 1
}

ensure_git() {
    if command_exists git; then
        success "Git $(git --version | cut -d' ' -f3)"
        return 0
    fi

    is_linux || fail "Git is required — https://git-scm.com/"
    info "Git not found. Installing it..."
    install_system_packages git
    command_exists git || fail "Git installation failed."
    success "Git $(git --version | cut -d' ' -f3)"
}

ensure_python() {
    if pick_python; then
        success "Python $($PYTHON --version | cut -d' ' -f2)"
        return 0
    fi

    is_linux || fail "Python 3.8+ is required — https://www.python.org/downloads/"
    info "Python 3.8+ not found. Installing it..."
    detect_package_manager || fail "Could not detect a supported package manager to install Python."

    case "$PKG_MANAGER" in
        apt-get)
            install_system_packages python3 python3-venv python3-pip
            ;;
        dnf|yum)
            install_system_packages python3 python3-pip
            ;;
        pacman)
            install_system_packages python python-pip
            ;;
        zypper)
            install_system_packages python3 python3-pip python3-virtualenv
            ;;
        apk)
            install_system_packages python3 py3-pip py3-virtualenv
            ;;
    esac

    pick_python || fail "Python installation failed."
    success "Python $($PYTHON --version | cut -d' ' -f2)"
}

ensure_venv_support() {
    detect_package_manager || return 1

    case "$PKG_MANAGER" in
        apt-get)
            install_system_packages python3-venv
            ;;
        zypper)
            install_system_packages python3-virtualenv
            ;;
        apk)
            install_system_packages py3-virtualenv
            ;;
        dnf|yum|pacman)
            # python3/python package usually includes venv support here
            ;;
    esac
}

detect_browser_binary() {
    local candidate

    for candidate in google-chrome google-chrome-stable chromium chromium-browser chrome; do
        if command_exists "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done

    for candidate in \
        /usr/bin/google-chrome \
        /usr/bin/google-chrome-stable \
        /usr/bin/chromium \
        /usr/bin/chromium-browser \
        /snap/bin/chromium \
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

install_browser_linux() {
    detect_package_manager || fail "Could not detect a supported package manager to install Chrome/Chromium."
    info "Chrome/Chromium not found. Trying to install it with $PKG_MANAGER..."

    case "$PKG_MANAGER" in
        apt-get)
            prepare_package_index

            if apt-cache show chromium >/dev/null 2>&1; then
                if install_system_packages chromium; then
                    return 0
                fi
            fi

            if [ "$(uname -m)" = "x86_64" ] || [ "$(uname -m)" = "amd64" ]; then
                local tmpdeb
                tmpdeb=$(mktemp /tmp/google-chrome-stable.XXXXXX.deb)
                info "Installing Google Chrome from the official Debian package..."
                curl -fsSL -o "$tmpdeb" https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
                    || fail "Could not download the Google Chrome package."

                if ! run_as_root dpkg -i "$tmpdeb"; then
                    run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -f -y
                fi
                rm -f "$tmpdeb"
                return 0
            fi

            if command_exists snap; then
                info "Installing Chromium via snap..."
                run_as_root snap install chromium || true
                return 0
            fi
            ;;
        dnf|yum|pacman|zypper|apk)
            install_system_packages chromium
            ;;
    esac
}

ensure_browser() {
    if BROWSER_PATH=$(detect_browser_binary); then
        success "Chrome/Chromium detected at $BROWSER_PATH"
        return 0
    fi

    if ! is_linux; then
        warn "Automatic browser installation currently targets Linux. Install Chrome or Chromium manually before first run."
        return 0
    fi

    install_browser_linux

    if BROWSER_PATH=$(detect_browser_binary); then
        success "Chrome/Chromium ready at $BROWSER_PATH"
        return 0
    fi

    fail "Could not install Chrome/Chromium automatically. Install it manually, then rerun the installer or use --chrome-binary-path when launching the tool."
}

clone_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        warn "Directory $INSTALL_DIR already exists"
        info "Pulling latest changes..."
        (cd "$INSTALL_DIR" && git pull origin "$BRANCH" 2>/dev/null) || true
    elif [ -d "$INSTALL_DIR" ]; then
        fail "Directory $INSTALL_DIR already exists but is not a git checkout. Choose a different PROJECT_DIR."
    else
        info "Cloning repository..."
        git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || fail "Clone failed. Check your internet connection."
    fi
    success "Repository ready at $INSTALL_DIR"
}

check_prereqs() {
    info "Checking prerequisites..."
    ensure_git
    ensure_python
}

install_deps() {
    cd "$INSTALL_DIR"

    if [ ! -d ".venv" ]; then
        info "Creating virtual environment..."
        if ! "$PYTHON" -m venv .venv; then
            warn "Python venv support is missing. Trying to install it..."
            if is_linux; then
                ensure_venv_support
                "$PYTHON" -m venv .venv || fail "Could not create the virtual environment."
            else
                fail "Could not create the virtual environment."
            fi
        fi
    else
        info "Using existing virtual environment..."
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate

    info "Installing the package and runtime dependencies..."
    python -m pip install --upgrade pip setuptools wheel -q
    python -m pip install -e . -q
    success "Package installed in $INSTALL_DIR/.venv"
}

print_done() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}Installation complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Location:${NC}  $INSTALL_DIR"
    echo -e "  ${BOLD}Browser:${NC}   ${BROWSER_PATH:-Install Chrome/Chromium manually if needed}"
    echo -e "  ${BOLD}Activate:${NC}  source $INSTALL_DIR/.venv/bin/activate"
    echo -e "  ${BOLD}Run:${NC}       whatsapp-beacon -u \"Target Name\""
    echo -e "  ${BOLD}Analytics:${NC} whatsapp-beacon --analytics"
    echo ""
}

main() {
    print_banner
    check_prereqs
    clone_repo
    install_deps
    ensure_browser
    print_done
}

main "$@"

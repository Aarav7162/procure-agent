"""
procure/display.py
------------------
Claude Code terminal aesthetic: clean box-drawing characters, minimal typography,
no decorative noise, precise status badges, and animated spinners.
"""
import sys
import time
import shutil
import threading
from typing import List, Optional

try:
    import colorama
    colorama.init(autoreset=True)
except ImportError:
    pass

# ANSI Color Codes
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
WHITE = "\033[37m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def c_green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"

def c_red(text: str) -> str:
    return f"{RED}{text}{RESET}"

def c_yellow(text: str) -> str:
    return f"{YELLOW}{text}{RESET}"

def c_cyan(text: str) -> str:
    return f"{CYAN}{text}{RESET}"

def c_dim(text: str) -> str:
    return f"{DIM}{text}{RESET}"

def c_bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"

def c_adversary() -> str:
    return f"{RED}[ADVERSARY]{RESET}"


class Spinner:
    """Live inline terminal spinner matching Claude Code style."""
    def __init__(self, message: str):
        self.message = message
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def _spin(self):
        idx = 0
        while self.running:
            frame = SPINNER_FRAMES[idx % len(SPINNER_FRAMES)]
            # Overwrite line
            sys.stdout.write(f"\r  {CYAN}{frame}{RESET} {self.message}   ")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self, success: bool = True, final_text: Optional[str] = None):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.2)
        # Clear line
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        if final_text is None:
            final_text = self.message

        if success:
            print(f"  {GREEN}✓{RESET} {final_text}")
        else:
            print(f"  {RED}✗{RESET} {final_text}")


def render_header(title: str, version: str, budget_str: str, mode: str):
    """Renders the top box-drawing header."""
    w = max(55, min(80, shutil.get_terminal_size((80, 24)).columns - 4))
    inner_text = f"  {title}  v{version}  ·  Budget: {budget_str}  ·  {mode}  "
    pad = w - len(inner_text)
    left_pad = " " * (pad // 2)
    right_pad = " " * (pad - len(left_pad))

    top_border = "┌" + "─" * w + "┐"
    bot_border = "└" + "─" * w + "┘"
    content_line = f"│{left_pad}{BOLD}{title}{RESET}  v{version}  ·  Budget: {c_green(budget_str)}  ·  {c_cyan(mode)}{right_pad}│"

    print()
    print(f"  {top_border}")
    print(f"  {content_line}")
    print(f"  {bot_border}")


def render_worker_header(worker_id: str, status: str, rep_str: str, n_str: str, paypal_str: str):
    """Renders the seller worker CLI top box-drawing header."""
    w = 55
    top_border = "┌" + "─" * w + "┐"
    bot_border = "└" + "─" * w + "┘"
    line1 = f"│  {BOLD}ProcureAgent Worker{RESET}  v1.0  ·  {c_cyan(worker_id):<21}│"
    line2 = f"│  Status: {c_green(status):<8} ·  Reputation: {rep_str}  ·  N={n_str:<8}│"
    line3 = f"│  PayPal: {c_dim(paypal_str):<45}│"

    print()
    print(f"  {top_border}")
    print(f"  {line1}")
    print(f"  {line2}")
    print(f"  {line3}")
    print(f"  {bot_border}")


def mask_email(email: str) -> str:
    """Masks paypal email for executive privacy."""
    if not email or "@" not in email:
        return email
    user, domain = email.split("@", 1)
    if len(user) <= 4:
        masked_user = user[:1] + "***"
    else:
        masked_user = user[:5] + "***" + user[-4:]
    return f"{masked_user}@{domain}"


def render_table(title: str, headers: List[str], rows: List[List[str]], col_widths: Optional[List[int]] = None):
    """Renders a clean box-drawing table."""
    if not col_widths:
        col_widths = []
        for i in range(len(headers)):
            w = len(headers[i])
            for r in rows:
                if i < len(r):
                    # Strip ANSI lengths
                    plain = r[i].replace(CYAN, "").replace(GREEN, "").replace(RED, "").replace(YELLOW, "").replace(WHITE, "").replace(BOLD, "").replace(DIM, "").replace(RESET, "")
                    w = max(w, len(plain))
            col_widths.append(w + 2)

    total_w = sum(col_widths) + len(col_widths) + 1

    # Top border
    top = "┌" + "─" * (total_w - 2) + "┐"
    print(f"\n  {top}")
    print(f"  │ {BOLD}{title:<{total_w-4}}{RESET} │")

    # Header separator
    header_sep = "├" + "┬".join("─" * w for w in col_widths) + "┤"
    print(f"  {header_sep}")

    # Header row
    h_row = "│" + "│".join(f" {headers[i]:<{col_widths[i]-1}}" for i in range(len(headers))) + "│"
    print(f"  {h_row}")

    # Row separator
    row_sep = "├" + "┼".join("─" * w for w in col_widths) + "┤"
    print(f"  {row_sep}")

    # Data rows
    for r in rows:
        formatted_cells = []
        for i in range(len(headers)):
            val = r[i] if i < len(r) else ""
            plain = val.replace(CYAN, "").replace(GREEN, "").replace(RED, "").replace(YELLOW, "").replace(WHITE, "").replace(BOLD, "").replace(DIM, "").replace(RESET, "")
            diff = len(val) - len(plain)
            formatted_cells.append(f" {val:<{col_widths[i]-1 + diff}}")
        print(f"  │" + "│".join(formatted_cells) + "│")

    # Bottom border
    bot = "└" + "┴".join("─" * w for w in col_widths) + "┘"
    print(f"  {bot}")


def render_rule_separator(text: Optional[str] = None):
    """Draws a clean divider line."""
    if text:
        w = max(40, len(text) + 6)
        print(f"  {DIM}{'─' * 3} {text} {'─' * (w - len(text) - 5)}{RESET}")
    else:
        print(f"  {DIM}{'─' * 45}{RESET}")


#!/usr/bin/env python3
# =============================================================================
#  ₿ CRYPTO WALLET TRACKER — Interactive TUI App
#  Supports: Bitcoin (BTC) · Ethereum (ETH)
#  Chain auto-detected from address format — No API key required
#  Run: python3 btc_tracker.py
#  Requires: pip install requests
# =============================================================================

import re
import sys
import os
import csv
import threading
import time
import itertools
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    print("Missing dependency: run  pip install requests")
    sys.exit(1)

# ── ANSI styles ───────────────────────────────────────────────────────────────
RESET  = "\033[0m";  BOLD  = "\033[1m";  DIM   = "\033[2m"
RED    = "\033[0;31m"; GREEN = "\033[0;32m"
CYAN   = "\033[0;36m"; WHITE = "\033[1;37m"
GOLD   = "\033[38;5;220m"
BLUE   = "\033[38;5;39m"

# ── helpers ───────────────────────────────────────────────────────────────────
def clear_screen() -> None:
    os.system("clear")

def press_enter() -> None:
    input(f"\n{DIM}  Press [Enter] to continue...{RESET}")

def divider() -> None:
    print(f"{DIM}  {'─' * 68}{RESET}")

def print_header() -> None:
    clear_screen()
    print(f"{GOLD}{BOLD}")
    print(r"""
   ________  _____    _____   _______ ___ _       __
  / ____/ / / /   |  /  _/ | / / ___//   | |     / /
 / /   / /_/ / /| |  / //  |/ /\__ \/ /| | | /| / / 
/ /___/ __  / ___ |_/ // /|  /___/ / ___ | |/ |/ /  
\____/_/ /_/_/  |_/___/_/ |_//____/_/  |_|__/|__/   

                        Developer: A Russian Boy
    """)
    print(f"{RESET}")
    print(f"  {DIM}Supports {GOLD}₿ Bitcoin{RESET}{DIM} · {BLUE}Ξ Ethereum{RESET}{DIM}  ·  No API key required  ·  Auto chain detection{RESET}")
    divider()
    print()


class Spinner:
    """Context manager that shows an animated spinner while work runs."""

    def __init__(self, message: str = "Loading...") -> None:
        self.message = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self) -> None:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        for frame in itertools.cycle(frames):
            if self._stop.is_set():
                break
            print(f"\r  {CYAN}{frame}{RESET}  {self.message}", end="", flush=True)
            time.sleep(0.08)
        print(f"\r{' ' * 72}\r", end="", flush=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


# ── date helpers ──────────────────────────────────────────────────────────────
def validate_date_format(raw: str) -> bool:
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):
        return False
    mm, dd, _ = raw.split("/")
    return 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31

def parse_date(raw: str) -> int:
    """Return UTC midnight timestamp for mm/dd/yyyy."""
    mm, dd, yyyy = raw.split("/")
    dt = datetime(int(yyyy), int(mm), int(dd), tzinfo=timezone.utc)
    return int(dt.timestamp())

def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m/%Y %H:%M:%S")

def fmt_date_short(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m/%Y %H:%M")

def iso_to_ts(iso: str) -> int:
    iso = iso.rstrip("Z")
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp())


# ── conversions ───────────────────────────────────────────────────────────────
def satoshi_to_btc(sats: int) -> str:
    return f"{sats / 1e8:.8f}"

def wei_to_eth(wei: int) -> str:
    return f"{int(wei) / 1e18:.8f}"


# ── chain auto-detection ──────────────────────────────────────────────────────
def detect_chain(addr: str) -> str:
    if re.fullmatch(r"(1|3|bc1)[a-zA-Z0-9]{20,90}", addr):
        return "BTC"
    if re.fullmatch(r"0x[a-fA-F0-9]{40}", addr):
        return "ETH"
    return "UNKNOWN"


# ── step 1: wallet input ──────────────────────────────────────────────────────
def input_wallet() -> tuple[str, str]:
    print_header()
    print(f"  {BOLD}{WHITE}STEP 1 of 3 — Wallet Address{RESET}\n")
    print("  Enter a Bitcoin or Ethereum address.")
    print(f"  {DIM}The chain will be detected automatically from the address format.{RESET}\n")
    print(f"  {DIM}  BTC: starts with 1 / 3 / bc1   ·   ETH: starts with 0x{RESET}\n")
    divider()
    print()

    while True:
        wallet = input(f"  {CYAN}Wallet address:{RESET} ").strip()
        if not wallet:
            print(f"  {RED}Address cannot be empty. Try again.{RESET}\n")
            continue

        chain = detect_chain(wallet)
        if chain == "UNKNOWN":
            print(f"  {RED}Unrecognized address format.{RESET}")
            print(f"  {DIM}  BTC: 1... / 3... / bc1...{RESET}")
            print(f"  {DIM}  ETH: 0x followed by 40 hex characters{RESET}\n")
            continue

        chain_label = f"{GOLD}₿ Bitcoin (BTC){RESET}" if chain == "BTC" else f"{BLUE}Ξ Ethereum (ETH){RESET}"
        print(f"  {GREEN}✔{RESET}  Chain detected: {chain_label}\n")

        # Live validation
        if chain == "BTC":
            url = f"https://blockstream.info/api/address/{wallet}"
            with Spinner("Validating on Blockstream..."):
                try:
                    r = requests.get(url, timeout=15)
                    data = r.json() if r.ok else None
                except Exception:
                    data = None
            if not data:
                print(f"  {RED}Could not validate address. Check your connection or address.{RESET}\n")
                continue
            tx_total = data.get("chain_stats", {}).get("tx_count", 0) + \
                       data.get("mempool_stats", {}).get("tx_count", 0)
        else:
            url = f"https://eth.blockscout.com/api/v2/addresses/{wallet}"
            with Spinner("Validating on Blockscout..."):
                try:
                    r = requests.get(url, timeout=15)
                    data = r.json() if r.ok else None
                except Exception:
                    data = None
            if not data or not data.get("hash"):
                print(f"  {RED}Address not found on Ethereum mainnet.{RESET}\n")
                continue
            tx_total = data.get("transaction_count", "unknown")

        print(f"  {GREEN}✔{RESET}  Valid address — transactions on-chain: {BOLD}{tx_total}{RESET}\n")
        time.sleep(0.5)
        return wallet, chain


# ── step 2: date range ────────────────────────────────────────────────────────
def input_dates(wallet: str, chain: str) -> tuple[str, str, int, int]:
    print_header()
    print(f"  {BOLD}{WHITE}STEP 2 of 3 — Date Range{RESET}\n")
    chain_label = f"{GOLD}₿ Bitcoin{RESET}" if chain == "BTC" else f"{BLUE}Ξ Ethereum{RESET}"
    print(f"  {BOLD}Chain  :{RESET} {chain_label}")
    print(f"  {BOLD}Wallet :{RESET} {wallet}\n")
    print("  Specify the date range to filter transactions.")
    print(f"  {DIM}Format: mm/dd/yyyy   Example: 01/15/2024{RESET}\n")
    divider()
    print()

    while True:
        from_raw = input(f"  {CYAN}From (mm/dd/yyyy):{RESET} ").strip()
        if not validate_date_format(from_raw):
            print(f"  {RED}Wrong format. Use mm/dd/yyyy (e.g. 01/15/2024).{RESET}\n")
            continue
        try:
            from_ts = parse_date(from_raw)
            print(f"  {GREEN}✔{RESET}  Start date accepted.\n")
            break
        except Exception:
            print(f"  {RED}Could not parse date. Try again.{RESET}\n")

    while True:
        to_raw = input(f"  {CYAN}To   (mm/dd/yyyy):{RESET} ").strip()
        if not validate_date_format(to_raw):
            print(f"  {RED}Wrong format. Use mm/dd/yyyy (e.g. 12/31/2024).{RESET}\n")
            continue
        try:
            to_ts = parse_date(to_raw) + 86399
        except Exception:
            print(f"  {RED}Could not parse date. Try again.{RESET}\n")
            continue
        if from_ts > to_ts:
            print(f"  {RED}End date must be after the start date. Try again.{RESET}\n")
            continue
        print(f"  {GREEN}✔{RESET}  End date accepted.\n")
        break

    time.sleep(0.5)
    return from_raw, to_raw, from_ts, to_ts


# ── step 2b: fetch limit ──────────────────────────────────────────────────────
def input_limit(wallet: str, chain: str,
                from_raw: str, to_raw: str) -> Optional[int]:
    print_header()
    print(f"  {BOLD}{WHITE}STEP 3 of 4 — Fetch Limit{RESET}\n")
    chain_label = f"{GOLD}₿ Bitcoin{RESET}" if chain == "BTC" else f"{BLUE}Ξ Ethereum{RESET}"
    print(f"  {BOLD}Chain  :{RESET} {chain_label}")
    print(f"  {BOLD}Wallet :{RESET} {wallet}")
    print(f"  {BOLD}Range  :{RESET} {from_raw} → {to_raw}\n")

    if chain == "BTC":
        print(f"  Set a maximum number of {BOLD}pages{RESET} to fetch.")
        print(f"  {DIM}Each page contains up to 25 transactions (Blockstream).{RESET}")
        prompt = f"  {CYAN}Max pages (Enter = no limit):{RESET} "
    else:
        print(f"  Set a maximum number of {BOLD}transactions{RESET} to fetch.")
        print(f"  {DIM}Each batch contains up to 50 transactions (Blockscout).{RESET}")
        prompt = f"  {CYAN}Max transactions (Enter = no limit):{RESET} "

    print(f"  {DIM}Press Enter to fetch everything in the date range.{RESET}\n")
    divider()
    print()

    while True:
        raw = input(prompt).strip()
        if raw == "":
            print(f"  {GREEN}✔{RESET}  No limit — fetching all transactions in range.\n")
            time.sleep(0.5)
            return None
        if raw.isdigit() and int(raw) > 0:
            limit = int(raw)
            label = "pages" if chain == "BTC" else "transactions"
            print(f"  {GREEN}✔{RESET}  Limit set to {BOLD}{limit}{RESET} {label}.\n")
            time.sleep(0.5)
            return limit
        print(f"  {RED}Enter a positive number or press Enter for no limit.{RESET}\n")


# ── step 4: confirm ───────────────────────────────────────────────────────────
def confirm_and_run(wallet: str, chain: str,
                    from_raw: str, to_raw: str,
                    from_ts: int, to_ts: int,
                    limit: Optional[int]) -> None:
    print_header()
    print(f"  {BOLD}{WHITE}STEP 4 of 4 — Review & Confirm{RESET}\n")
    chain_label = f"{GOLD}₿ Bitcoin (BTC){RESET}" if chain == "BTC" else f"{BLUE}Ξ Ethereum (ETH){RESET}"
    limit_label = f"{limit} {'pages' if chain == 'BTC' else 'transactions'}" if limit else "no limit"
    print(f"  {BOLD}Chain      :{RESET} {chain_label}")
    print(f"  {BOLD}Wallet     :{RESET} {wallet}")
    print(f"  {BOLD}From       :{RESET} {from_raw}")
    print(f"  {BOLD}To         :{RESET} {to_raw}")
    print(f"  {BOLD}Limit      :{RESET} {limit_label}")
    print()
    divider()
    print()
    print(f"  {GOLD}[Y]{RESET}  Start tracking")
    print(f"  {GOLD}[N]{RESET}  Back to main menu")
    print()
    choice = input(f"  {CYAN}Your choice:{RESET} ").strip().lower()
    if choice in ("y", "yes"):
        if chain == "BTC":
            run_btc_tracker(wallet, from_raw, to_raw, from_ts, to_ts, limit)
        else:
            run_eth_tracker(wallet, from_raw, to_raw, from_ts, to_ts, limit)
    else:
        main_menu()


# ── report helpers ────────────────────────────────────────────────────────────
def build_report_header(chain: str, wallet: str, from_raw: str, to_raw: str) -> list[str]:
    if chain == "BTC":
        title   = "₿  BITCOIN WALLET TRACKER — TRANSACTION REPORT"
        src_lbl = "Bitcoin (BTC) — Blockstream.info"
    else:
        title   = "Ξ  ETHEREUM WALLET TRACKER — TRANSACTION REPORT"
        src_lbl = "Ethereum (ETH) — Blockscout.com"

    lines = [
        "╔══════════════════════════════════════════════════════════════════════╗",
        f"║{title.center(70)}║",
        "╚══════════════════════════════════════════════════════════════════════╝",
        "",
        f"  {'Chain :':<12} {src_lbl}",
        f"  {'Wallet :':<12} {wallet}",
        f"  {'Range :':<12} {from_raw} → {to_raw}",
        f"  {'Generated:':<12} {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
    ]
    return lines

def build_table_header(amount_col: str) -> list[str]:
    border_top = "┌──────┬─────────────────────┬──────────┬──────────────────┬──────────────────────────────────────────────────────────────────┐"
    header_row = f"│ {'N°':<4} │ {'DATE & TIME':<19} │ {'TYPE':<8} │ {amount_col:<16} │ {'TXID/HASH':<64} │"
    border_mid = "├──────┼─────────────────────┼──────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤"
    return [border_top, header_row, border_mid]

def build_summary(total: int, total_in: str, total_out: str,
                  net_bal: str, symbol: str) -> list[str]:
    w = 30
    return [
        "┌───────────────────────────────────────────────────────┐",
        "│                      SUMMARY                         │",
        "├───────────────────────────────────────────────────────┤",
        f"│  {'Total transactions  :':<22} {f'{total}':<{w}} │",
        f"│  {'Total IN   (+)      :':<22} {f'{total_in} {symbol}':<{w}} │",
        f"│  {'Total OUT  (-)      :':<22} {f'{total_out} {symbol}':<{w}} │",
        "├───────────────────────────────────────────────────────┤",
        f"│  {'NET BALANCE         :':<22} {f'{net_bal} {symbol}':<{w}} │",
        "└───────────────────────────────────────────────────────┘",
        "",
    ]


# ── BTC tracker ───────────────────────────────────────────────────────────────
def run_btc_tracker(wallet: str, from_raw: str, to_raw: str,
                    from_ts: int, to_ts: int,
                    max_pages: Optional[int] = None) -> None:
    slug = wallet[:10]
    outfile = f"btc_report_{slug}_{from_raw.replace('/', '-')}_{to_raw.replace('/', '-')}.csv"

    print_header()
    print(f"  {BOLD}{WHITE}TRACKING {GOLD}₿ BITCOIN{WHITE} WALLET{RESET}\n")
    print(f"  {BOLD}Wallet :{RESET} {GOLD}{wallet}{RESET}")
    print(f"  {BOLD}Range  :{RESET} {from_raw} → {to_raw}\n")
    divider(); print()

    all_txs: list[dict] = []
    last_txid = ""
    page = 0
    done = False

    while not done:
        page += 1
        url = f"https://blockstream.info/api/address/{wallet}/txs"
        if last_txid:
            url += f"/chain/{last_txid}"

        with Spinner(f"Fetching page {page}..."):
            try:
                r = requests.get(url, timeout=20)
                batch = r.json() if r.ok else []
            except Exception:
                batch = []

        if not batch:
            if page == 1:
                print(f"  {RED}Network error on page {page}.{RESET}")
            break

        in_range = [
            tx for tx in batch
            if tx.get("status", {}).get("confirmed")
            and from_ts <= tx["status"]["block_time"] <= to_ts
        ]
        all_txs.extend(in_range)

        confirmed_times = [tx["status"]["block_time"] for tx in batch if tx.get("status", {}).get("confirmed")]
        oldest = min(confirmed_times) if confirmed_times else 0
        last_txid = batch[-1]["txid"]

        print(f"  {GREEN}✔{RESET}  Page {page}: {len(batch)} fetched · {len(in_range)} match date range")

        if oldest and oldest < from_ts:
            done = True
        if len(batch) < 25:
            done = True
        if max_pages and page >= max_pages:
            done = True

    total = len(all_txs)
    print(f"\n  {GOLD}{BOLD}{total} transaction(s) found in range.{RESET}\n")
    divider(); print()
    print(f"  {CYAN}Building report...{RESET}\n")
    time.sleep(0.5)

    report_lines: list[str] = []
    report_lines.extend(build_report_header("BTC", wallet, from_raw, to_raw))

    if total == 0:
        report_lines.append("  No transactions found in the selected date range.")
        report_lines.append("")
    else:
        sorted_txs = sorted(all_txs, key=lambda tx: tx["status"]["block_time"])
        report_lines.extend(build_table_header("AMOUNT (BTC)"))

        total_in = 0
        total_out = 0

        for idx, tx in enumerate(sorted_txs, 1):
            bt      = tx["status"]["block_time"]
            txid    = tx["txid"]
            tx_date = fmt_date(bt)

            rcv = sum(
                o["value"] for o in tx.get("vout", [])
                if o.get("scriptpubkey_address") == wallet
            )
            snd = sum(
                i["prevout"]["value"] for i in tx.get("vin", [])
                if i.get("prevout", {}).get("scriptpubkey_address") == wallet
            )

            if snd > 0 and rcv > 0:
                net = rcv - snd
                if net >= 0:
                    tipo, amt = "IN(net)", net;  total_in  += net
                else:
                    tipo, amt = "OUT(net)", -net; total_out += -net
            elif rcv > 0:
                tipo, amt = "IN",  rcv; total_in  += rcv
            else:
                tipo, amt = "OUT", snd; total_out += snd

            btc_amt = satoshi_to_btc(amt)
            report_lines.append(
                f"│ {str(idx) + '.':<4} │ {tx_date:<19} │ {tipo:<8} │ {btc_amt:<16} │ {txid:<64} │"
            )

        report_lines.append("└──────┴─────────────────────┴──────────┴──────────────────┴──────────────────────────────────────────────────────────────────┘")
        report_lines.append("")

        in_btc  = satoshi_to_btc(total_in)
        out_btc = satoshi_to_btc(total_out)
        bal     = total_in - total_out
        bal_btc = ("+" if bal >= 0 else "") + satoshi_to_btc(abs(bal))
        report_lines.extend(build_summary(total, in_btc, out_btc, bal_btc, "BTC"))

        # Timeline
        report_lines += [
            "┌───────────────────────────────────────────────────────┐",
            "│               TRANSACTION TIMELINE                   │",
            "└───────────────────────────────────────────────────────┘",
            "",
        ]
        for idx, tx in enumerate(sorted_txs, 1):
            bt       = tx["status"]["block_time"]
            txid_s   = tx["txid"][:20]
            tx_date  = fmt_date_short(bt)
            rcv = sum(o["value"] for o in tx.get("vout", []) if o.get("scriptpubkey_address") == wallet)
            snd = sum(i["prevout"]["value"] for i in tx.get("vin", []) if i.get("prevout", {}).get("scriptpubkey_address") == wallet)
            if snd > 0 and rcv > 0:
                net = rcv - snd
                tipo, amt = ("IN ", net) if net >= 0 else ("OUT", -net)
            elif rcv > 0:
                tipo, amt = "IN ", rcv
            else:
                tipo, amt = "OUT", snd
            btc_amt = satoshi_to_btc(amt)
            arrow = "───▶" if tipo.strip() == "IN" else "◀───"
            sign  = "+" if tipo.strip() == "IN" else "-"
            report_lines.append(f"  {idx:3d}.  {tx_date}  [{txid_s}...]  {arrow}  {sign}{btc_amt} BTC")
            if idx < total:
                report_lines.append("              │")
        report_lines.append("")

    report_lines += [
        "══════════════════════════════════════════════════════════════════════",
        f"  End of report  —  https://blockstream.info/address/{wallet}",
        "══════════════════════════════════════════════════════════════════════",
    ]

    report_text = "\n".join(report_lines)
    print(report_text)

    BTC_FIELDS = ["n", "date_time", "txid", "block_height", "type",
                  "received_btc", "sent_btc", "amount_btc", "fee_btc", "from", "to"]

    sorted_txs_for_csv = sorted(all_txs, key=lambda tx: tx["status"]["block_time"]) if all_txs else []
    with open(outfile, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BTC_FIELDS)
        w.writeheader()
        for idx, tx in enumerate(sorted_txs_for_csv, 1):
            bt           = tx["status"]["block_time"]
            block_height = tx["status"].get("block_height", "")
            fee_sats     = tx.get("fee", 0)
            rcv = sum(o["value"] for o in tx.get("vout", []) if o.get("scriptpubkey_address") == wallet)
            snd = sum(i["prevout"]["value"] for i in tx.get("vin", []) if i.get("prevout", {}).get("scriptpubkey_address") == wallet)
            if snd > 0 and rcv > 0:
                net = rcv - snd
                tipo, amt = ("IN(net)", net) if net >= 0 else ("OUT(net)", -net)
            elif rcv > 0:
                tipo, amt = "IN",  rcv
            else:
                tipo, amt = "OUT", snd
            w.writerow({
                "n":            idx,
                "date_time":    datetime.fromtimestamp(bt, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "txid":         tx["txid"],
                "block_height": block_height,
                "type":         tipo,
                "received_btc": satoshi_to_btc(rcv),
                "sent_btc":     satoshi_to_btc(snd),
                "amount_btc":   satoshi_to_btc(amt),
                "fee_btc":      satoshi_to_btc(fee_sats),
                "from":         "; ".join(dict.fromkeys(
                                    i["prevout"]["scriptpubkey_address"]
                                    for i in tx.get("vin", [])
                                    if i.get("prevout", {}).get("scriptpubkey_address")
                                )),
                "to":           "; ".join(dict.fromkeys(
                                    o["scriptpubkey_address"]
                                    for o in tx.get("vout", [])
                                    if o.get("scriptpubkey_address")
                                )),
            })

    post_run_menu(outfile)


# ── ETH tracker ───────────────────────────────────────────────────────────────
def run_eth_tracker(wallet: str, from_raw: str, to_raw: str,
                    from_ts: int, to_ts: int,
                    max_txs: Optional[int] = None) -> None:
    slug = wallet[:10]
    outfile = f"eth_report_{slug}_{from_raw.replace('/', '-')}_{to_raw.replace('/', '-')}.csv"

    print_header()
    print(f"  {BOLD}{WHITE}TRACKING {BLUE}Ξ ETHEREUM{WHITE} WALLET{RESET}\n")
    print(f"  {BOLD}Wallet :{RESET} {BLUE}{wallet}{RESET}")
    print(f"  {BOLD}Range  :{RESET} {from_raw} → {to_raw}\n")
    divider(); print()

    all_txs: list[dict] = []
    next_params: Optional[dict] = None
    done = False

    while not done:
        base_url = f"https://eth.blockscout.com/api/v2/addresses/{wallet}/transactions"
        params: dict = {"filter": "to | from"}
        if next_params:
            params.update(next_params)

        with Spinner("Fetching batch..."):
            try:
                r = requests.get(base_url, params=params, timeout=20)
                data = r.json() if r.ok else {}
            except Exception:
                data = {}

        items = data.get("items", [])
        if not items:
            break

        in_range = [
            tx for tx in items
            if from_ts <= iso_to_ts(tx["timestamp"]) <= to_ts
        ]
        all_txs.extend(in_range)
        print(f"  {GREEN}✔{RESET}  Batch: {len(items)} fetched · {len(in_range)} match date range")

        oldest_iso = items[-1].get("timestamp", "")
        if oldest_iso and iso_to_ts(oldest_iso) < from_ts:
            done = True

        if max_txs and len(all_txs) >= max_txs:
            all_txs = all_txs[:max_txs]
            done = True

        next_params = data.get("next_page_params")
        if not next_params:
            done = True

    total = len(all_txs)
    print(f"\n  {BLUE}{BOLD}{total} transaction(s) found in range.{RESET}\n")
    divider(); print()
    print(f"  {CYAN}Building report...{RESET}\n")
    time.sleep(0.5)

    report_lines: list[str] = []
    report_lines.extend(build_report_header("ETH", wallet, from_raw, to_raw))

    if total == 0:
        report_lines.append("  No transactions found in the selected date range.")
        report_lines.append("")
    else:
        sorted_txs = sorted(all_txs, key=lambda tx: tx["timestamp"])
        report_lines.extend(build_table_header("AMOUNT (ETH)"))

        total_in_wei  = 0
        total_out_wei = 0
        wallet_lc = wallet.lower()

        for idx, tx in enumerate(sorted_txs, 1):
            ts      = iso_to_ts(tx["timestamp"])
            txhash  = tx.get("hash", "")
            from_addr = tx.get("from", {}).get("hash", "").lower()
            value_wei = int(tx.get("value", "0"))
            tx_date = fmt_date(ts)

            if from_addr == wallet_lc:
                tipo = "OUT"; total_out_wei += value_wei
            else:
                tipo = "IN";  total_in_wei  += value_wei

            eth_amt = wei_to_eth(value_wei)
            report_lines.append(
                f"│ {str(idx) + '.':<4} │ {tx_date:<19} │ {tipo:<8} │ {eth_amt:<16} │ {txhash:<64} │"
            )

        report_lines.append("└──────┴─────────────────────┴──────────┴──────────────────┴──────────────────────────────────────────────────────────────────┘")
        report_lines.append("")

        in_eth  = wei_to_eth(total_in_wei)
        out_eth = wei_to_eth(total_out_wei)
        bal_wei = total_in_wei - total_out_wei
        bal_eth = ("+" if bal_wei >= 0 else "") + wei_to_eth(abs(bal_wei))
        report_lines.extend(build_summary(total, in_eth, out_eth, bal_eth, "ETH"))

        # Timeline
        report_lines += [
            "┌───────────────────────────────────────────────────────┐",
            "│               TRANSACTION TIMELINE                   │",
            "└───────────────────────────────────────────────────────┘",
            "",
        ]
        for idx, tx in enumerate(sorted_txs, 1):
            ts        = iso_to_ts(tx["timestamp"])
            txhash_s  = tx.get("hash", "")[:20]
            from_addr = tx.get("from", {}).get("hash", "").lower()
            value_wei = int(tx.get("value", "0"))
            tx_date   = fmt_date_short(ts)
            eth_amt   = wei_to_eth(value_wei)

            if from_addr == wallet_lc:
                report_lines.append(f"  {idx:3d}.  {tx_date}  [{txhash_s}...]  ◀───  -{eth_amt} ETH")
            else:
                report_lines.append(f"  {idx:3d}.  {tx_date}  [{txhash_s}...]  ───▶  +{eth_amt} ETH")
            if idx < total:
                report_lines.append("              │")
        report_lines.append("")

    report_lines += [
        "══════════════════════════════════════════════════════════════════════",
        f"  End of report  —  https://eth.blockscout.com/address/{wallet}",
        "══════════════════════════════════════════════════════════════════════",
    ]

    report_text = "\n".join(report_lines)
    print(report_text)

    ETH_FIELDS = ["n", "date_time", "txhash", "block", "type", "amount_eth",
                  "from", "to", "fee_eth", "gas_used", "gas_price_gwei",
                  "status", "method"]

    sorted_txs_for_csv = sorted(all_txs, key=lambda tx: tx["timestamp"]) if all_txs else []
    wallet_lc_csv = wallet.lower()
    with open(outfile, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ETH_FIELDS)
        w.writeheader()
        for idx, tx in enumerate(sorted_txs_for_csv, 1):
            ts        = iso_to_ts(tx["timestamp"])
            from_addr = tx.get("from", {}).get("hash", "")
            to_addr   = (tx.get("to") or {}).get("hash", "")
            value_wei = int(tx.get("value", "0"))
            fee_wei   = int((tx.get("fee") or {}).get("value", "0"))
            gas_used  = tx.get("gas_used", "")
            gas_price = tx.get("gas_price", "")
            gas_price_gwei = f"{int(gas_price) / 1e9:.4f}" if gas_price else ""
            tipo = "OUT" if from_addr.lower() == wallet_lc_csv else "IN"
            w.writerow({
                "n":              idx,
                "date_time":      tx["timestamp"],
                "txhash":         tx.get("hash", ""),
                "block":          tx.get("block", ""),
                "type":           tipo,
                "amount_eth":     wei_to_eth(value_wei),
                "from":           from_addr,
                "to":             to_addr,
                "fee_eth":        wei_to_eth(fee_wei),
                "gas_used":       gas_used,
                "gas_price_gwei": gas_price_gwei,
                "status":         tx.get("status", ""),
                "method":         tx.get("method", ""),
            })

    post_run_menu(outfile)


# ── post-run menu ─────────────────────────────────────────────────────────────
def post_run_menu(outfile: str) -> None:
    print()
    print(f"  {GREEN}{BOLD}✔  Report saved to: {outfile}{RESET}")
    print()
    divider(); print()
    print(f"  {GOLD}[T]{RESET}  Track another wallet")
    print(f"  {GOLD}[Q]{RESET}  Quit")
    print()
    choice = input(f"  {CYAN}Your choice:{RESET} ").strip().lower()
    if choice == "t":
        main_menu()
    else:
        quit_app()


# ── about ─────────────────────────────────────────────────────────────────────
def show_about() -> None:
    print_header()
    print(f"  {BOLD}{WHITE}ABOUT{RESET}\n")
    print(f"  {GOLD}Crypto Wallet Tracker{RESET} fetches on-chain transactions for")
    print("  Bitcoin and Ethereum addresses within a custom date range.\n")
    print(f"  {BOLD}Supported chains :{RESET}")
    print(f"    {GOLD}₿ Bitcoin{RESET}   — via Blockstream.info (mainnet)")
    print(f"    {BLUE}Ξ Ethereum{RESET}  — via Blockscout.com public API (mainnet)\n")
    print(f"  {BOLD}Chain detection  :{RESET} Automatic from address format")
    print(f"  {BOLD}Output           :{RESET} .csv report saved in current directory")
    print(f"  {BOLD}Privacy          :{RESET} Read-only API calls — nothing is stored\n")
    print(f"  {DIM}Address formats accepted:{RESET}")
    print(f"  {DIM}  BTC → 1... / 3... / bc1...{RESET}")
    print(f"  {DIM}  ETH → 0x... (42 hex chars){RESET}\n")
    divider()
    press_enter()


def quit_app() -> None:
    print_header()
    print(f"  {GOLD}Thanks for using Crypto Wallet Tracker. Goodbye!{RESET}\n")
    sys.exit(0)


# ── main menu ─────────────────────────────────────────────────────────────────
def main_menu() -> None:
    while True:
        print_header()
        print(f"  {BOLD}{WHITE}MAIN MENU{RESET}\n")
        print(f"  {GOLD}[1]{RESET}  Track a wallet")
        print(f"  {GOLD}[2]{RESET}  About & info")
        print(f"  {GOLD}[Q]{RESET}  Quit")
        print()
        divider()
        choice = input(f"\n  {CYAN}Choose an option:{RESET} ").strip().lower()
        if choice == "1":
            wallet, chain = input_wallet()
            from_raw, to_raw, from_ts, to_ts = input_dates(wallet, chain)
            limit = input_limit(wallet, chain, from_raw, to_raw)
            confirm_and_run(wallet, chain, from_raw, to_raw, from_ts, to_ts, limit)
        elif choice == "2":
            show_about()
        elif choice == "q":
            quit_app()
        else:
            print(f"\n  {RED}Invalid option. Please try again.{RESET}")
            time.sleep(1)


# ── entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n  {GOLD}Interrupted. Goodbye!{RESET}\n")
        sys.exit(0)

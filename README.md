<div align="center">

```
██╗  ██╗ █████╗ ████████╗ ██████╗ ███╗   ██╗ █████╗  ██████╗  █████╗ ██████╗ ██╗
██║ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║██╔══██╗██╔════╝ ██╔══██╗██╔══██╗██║
█████╔╝ ███████║   ██║   ██║   ██║██╔██╗ ██║███████║██║  ███╗███████║██████╔╝██║
██╔═██╗ ██╔══██║   ██║   ██║   ██║██║╚██╗██║██╔══██║██║   ██║██╔══██║██╔══██╗██║
██║  ██╗██║  ██║   ██║   ╚██████╔╝██║ ╚████║██║  ██║╚██████╔╝██║  ██║██║  ██║██║
╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
```

**A terminal-native personal productivity suite**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Textual](https://img.shields.io/badge/TUI-Textual-1DB954?style=flat-square)](https://textual.textualize.io)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://github.com)
[![Storage](https://img.shields.io/badge/Storage-Local%20JSON-F7DF1E?style=flat-square)](https://github.com)
[![License](https://img.shields.io/badge/License-Personal-red?style=flat-square)](https://github.com)

</div>

---

## Overview

Katonagari is a fully offline, keyboard-driven productivity app built with [Textual](https://textual.textualize.io). It bundles two tools into one terminal interface:

- **Pomodoro** — focus timer with session logging, streaks, and weekly analytics
- **Finance** — personal ledger with multi-account tracking, transfers, and burn rate analysis

Everything persists to local JSON files. No accounts, no cloud, no subscriptions.

---

## Features

### ⏱ Pomodoro

| Feature | Details |
|---|---|
| Timer | 25 / 50 / 60 min focus blocks |
| Controls | Start · Pause · Resume · End (keyboard-only) |
| Subjects | Coding · Math · Reading (radio selection) |
| Session log | Per-session history in the timer view |
| Overview | Daily goal ring, streak counter, weekly heatmap, best-day stats, all-time totals |
| Persistence | Auto-saves completed sessions to `databases/pomodoro.json` |

### 💳 Finance

| Feature | Details |
|---|---|
| Accounts | Bank · E-Wallet · Cash · Other — live balances |
| Transactions | Add / delete per-account with category tagging |
| Transfers | Move funds between accounts, full history log |
| Overview | Net worth, monthly income/expenses, save rate |
| Analysis | 1M / 3M / 6M periods — burn rate, runway, income volatility, spending by category, biggest movers |

### 🔐 Launcher

Password-protected `.bat` hub for launching projects. Logs all auth events and supports in-session password changes.

---

## Project Structure

```
katonagari/
├── app.py                      # Entry point — screen bindings (F / P)
├── Katonagari.bat              # Secure launcher (Windows)
├── launcher.log                # Auth & launch activity log
│
├── screens/
│   ├── pomodoroScreen.py       # Pomodoro screen container
│   └── financeScreen.py        # Finance screen + tab layout
│
├── widgets/
│   ├── pomodoro/
│   │   ├── timer.py            # Core timer widget (state machine + tick loop)
│   │   └── overview.py         # Stats cards, heatmap, recent sessions
│   └── finance/
│       ├── overview.py         # Net worth dashboard
│       ├── log.py              # Per-account transaction log + balance history
│       ├── account.py          # Account cards, add/transfer/delete modals
│       └── analysis.py         # Burn rate, income stability, category spend
│
├── services/
│   ├── pomodoroService.py      # Session data layer + stats engine
│   └── financeService.py       # Finance data layer + formatters
│
└── databases/
    ├── pomodoro.json           # Focus sessions + config
    └── finance.json            # Accounts, transactions, transfers
```

---

## Setup

**Prerequisites:** Python 3.11+, Windows (for the `.bat` launcher)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/katonagari.git
cd katonagari

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install textual

# 4a. Run directly
python app.py

# 4b. Or launch via the secure hub
Katonagari.bat
```

---

## Keybindings

### Global

| Key | Action |
|---|---|
| `F` | Switch to Finance screen |
| `P` | Switch to Pomodoro screen |
| `Ctrl+P` | Open command palette |

### Pomodoro Timer

| Key | Action |
|---|---|
| `S` | Start session |
| `P` | Pause |
| `R` | Resume |
| `E` | End & save session |

### Finance — Log

| Key | Action |
|---|---|
| `A` | Add transaction |
| `D` | Delete selected row |
| `Ctrl+S` | Save (in modal) |
| `Esc` | Cancel (in modal) |

### Finance — Accounts

| Key | Action |
|---|---|
| `N` | New account |
| `T` | Transfer between accounts |
| `X` | Delete account |
| `R` | Refresh all |

---

## Data Format

```json
// databases/pomodoro.json
{
  "meta": { "daily_goal_minutes": 120, "focus_duration": 25 },
  "sessions": [
    {
      "date": "2026-03-20", "start": "09:30",
      "duration": 25, "type": "Focus",
      "subject": "Coding", "completed": true
    }
  ]
}
```

```json
// databases/finance.json
{
  "meta": {
    "accounts": [{ "id": "seabank", "name": "Seabank", "type": "Bank", "amount": 140236 }],
    "investments": 0, "debt": 0
  },
  "transactions": [
    { "date": "2026-03-20", "desc": "Salary", "cat": "Income", "amount": 5000000, "account": "seabank" }
  ],
  "transfers": []
}
```

---

## Roadmap

- [ ] Pomodoro Analysis tab *(UI placeholder already in place)*
- [ ] Goal & break duration settings screen
- [ ] Additional project slots in the launcher (Project 2, Project 3)
- [ ] Export sessions to CSV

---

> **Note:** The `.bat` launcher stores the password in plaintext. For personal local use only.

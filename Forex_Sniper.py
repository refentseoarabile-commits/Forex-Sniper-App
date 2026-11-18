#!/usr/bin/env python
# coding: utf-8

# In[5]:





# In[ ]:


import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf
import pandas as pd
import numpy as np
import requests


# ============================================================
# FOREX SNIPER
# Professional market monitor - no wolf imagery
# ============================================================

BG = "#080D13"
SIDEBAR = "#0B131D"
PANEL = "#111B27"
PANEL2 = "#182638"
WHITE = "#F1F5F9"
GREY = "#9AAABD"
GREEN = "#19D69A"
RED = "#FF626D"
GOLD = "#F5BD55"
BLUE = "#50A9FF"

REFRESH_SECONDS = 60


# ============================================================
# SYMBOL DATABASE
# ============================================================

CATEGORIES = {
    "FOREX MAJORS": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "USD/CHF": "CHF=X",
        "AUD/USD": "AUDUSD=X",
        "NZD/USD": "NZDUSD=X",
        "USD/CAD": "CAD=X",
    },

    "FOREX MINORS": {
        "EUR/GBP": "EURGBP=X",
        "EUR/JPY": "EURJPY=X",
        "GBP/JPY": "GBPJPY=X",
        "EUR/AUD": "EURAUD=X",
        "GBP/CHF": "GBPCHF=X",
        "AUD/JPY": "AUDJPY=X",
        "EUR/CHF": "EURCHF=X",
        "GBP/AUD": "GBPAUD=X",
        "AUD/NZD": "AUDNZD=X",
        "EUR/CAD": "EURCAD=X",
        "GBP/CAD": "GBPCAD=X",
        "NZD/JPY": "NZDJPY=X",
    },

    "EXOTIC FOREX": {
        "USD/ZAR": "USDZAR=X",
        "EUR/ZAR": "EURZAR=X",
        "GBP/ZAR": "GBPZAR=X",
        "USD/MXN": "USDMXN=X",
        "USD/TRY": "USDTRY=X",
        "USD/SGD": "USDSGD=X",
        "USD/CNH": "USDCNH=X",
        "USD/PLN": "USDPLN=X",
        "USD/SEK": "USDSEK=X",
        "USD/NOK": "USDNOK=X",
    },

    "PRECIOUS METALS": {
        "GOLD XAU/USD": "GC=F",
        "SILVER XAG/USD": "SI=F",
        "PLATINUM XPT/USD": "PL=F",
        "PALLADIUM XPD/USD": "PA=F",
    },

    "INDICES": {
        "NAS100": "NQ=F",
        "US30": "YM=F",
        "US500": "ES=F",
        "GER40": "^GDAXI",
        "UK100": "^FTSE",
        "FRA40": "^FCHI",
        "JPN225": "^N225",
        "AUS200": "^AXJO",
        "HK50": "^HSI",
        "VIX": "^VIX",
    },

    "ENERGY": {
        "USOIL": "CL=F",
        "UKOIL": "BZ=F",
        "NATGAS": "NG=F",
    }
}

SYMBOLS = {}

for category, items in CATEGORIES.items():
    SYMBOLS.update(items)


# ============================================================
# MARKET ANALYSIS
# ============================================================

def analyse_symbol(symbol):

    ticker = SYMBOLS[symbol]

    data = yf.download(
        ticker,
        period="10d",
        interval="1h",
        progress=False,
        auto_adjust=True,
        threads=False
    )

    if data.empty or len(data) < 55:
        raise ValueError("Insufficient market data")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    close = data["Close"].astype(float)
    high = data["High"].astype(float)
    low = data["Low"].astype(float)

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    change = close.diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    avg_gain = gains.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = losses.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)

    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = true_range.rolling(14).mean()

    price = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])
    rsi_value = float(rsi.iloc[-1])
    atr_value = float(atr.iloc[-1])

    if not np.isfinite(atr_value) or atr_value <= 0:
        raise ValueError("Volatility unavailable")

    if e20 > e50 and rsi_value >= 55:
        direction = "BULLISH"
    elif e20 < e50 and rsi_value <= 45:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    # EDUCATIONAL PAPER-TRADING REFERENCES ONLY

    simulated_entry = price
    simulated_sl = None
    simulated_tp = None

    if direction == "BULLISH":
        simulated_sl = price - (1.5 * atr_value)
        simulated_tp = price + (2.0 * atr_value)

    elif direction == "BEARISH":
        simulated_sl = price + (1.5 * atr_value)
        simulated_tp = price - (2.0 * atr_value)

    return {
        "symbol": symbol,
        "price": price,
        "direction": direction,
        "entry": simulated_entry,
        "sl": simulated_sl,
        "tp": simulated_tp,
        "rsi": rsi_value,
        "ema20": e20,
        "ema50": e50,
        "atr": atr_value,
        "updated": datetime.now().strftime("%H:%M:%S")
    }


# ============================================================
# MAIN APPLICATION
# ============================================================

class ForexSniper:

    def __init__(self, root):

        self.root = root
        self.root.title("FOREX SNIPER")
        self.root.geometry("1450x850")
        self.root.minsize(1100, 650)
        self.root.configure(bg=BG)

        self.results = {}
        self.scanning = False
        self.calendar_busy = False

        self.setup_style()
        self.build_layout()
        self.show_page("home")

        self.root.after(1000, self.scan_all)
        self.root.after(2500, self.load_calendar)

    # --------------------------------------------------------
    # STYLE
    # --------------------------------------------------------

    def setup_style(self):

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=PANEL,
            foreground=WHITE,
            fieldbackground=PANEL,
            rowheight=31,
            borderwidth=0,
            font=("Segoe UI", 9)
        )

        style.configure(
            "Treeview.Heading",
            background=PANEL2,
            foreground=WHITE,
            font=("Segoe UI", 9, "bold")
        )

        style.map(
            "Treeview",
            background=[("selected", "#24496A")],
            foreground=[("selected", WHITE)]
        )

    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    def build_layout(self):

        self.sidebar = tk.Frame(
            self.root,
            bg=SIDEBAR,
            width=210
        )

        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # TEXT-ONLY BRANDING: NO WOLF IMAGE OR EMOJI

        tk.Frame(
            self.sidebar,
            bg=BLUE,
            height=3
        ).pack(fill="x", padx=22, pady=(38, 18))

        tk.Label(
            self.sidebar,
            text="FOREX",
            bg=SIDEBAR,
            fg=WHITE,
            font=("Segoe UI", 23, "bold")
        ).pack()

        tk.Label(
            self.sidebar,
            text="SNIPER",
            bg=SIDEBAR,
            fg=BLUE,
            font=("Segoe UI", 23, "bold")
        ).pack(pady=(0, 30))

        navigation = [
            ("HOME", "home"),
            ("DASHBOARD", "dashboard"),
            ("SIGNAL CENTRE", "signals"),
            ("ECONOMIC CALENDAR", "calendar")
        ]

        for label, page in navigation:

            tk.Button(
                self.sidebar,
                text=label,
                command=lambda p=page: self.show_page(p),
                bg="#142131",
                fg=WHITE,
                activebackground="#24496A",
                activeforeground=WHITE,
                relief="flat",
                bd=0,
                anchor="w",
                padx=18,
                pady=15,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2"
            ).pack(fill="x", padx=10, pady=4)

        tk.Label(
            self.sidebar,
            text="MARKET MONITOR\nPAPER MODE",
            bg=SIDEBAR,
            fg=GREY,
            font=("Segoe UI", 9)
        ).pack(side="bottom", pady=25)

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="right", fill="both", expand=True)

        self.pages = {
            name: tk.Frame(self.main, bg=BG)
            for name in [
                "home",
                "dashboard",
                "signals",
                "calendar"
            ]
        }

        self.build_home()
        self.build_dashboard()
        self.build_signals()
        self.build_calendar()

    def show_page(self, name):

        for page in self.pages.values():
            page.pack_forget()

        self.pages[name].pack(fill="both", expand=True)

    def heading(self, page, title, subtitle):

        tk.Label(
            page,
            text=title,
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w", padx=25, pady=(22, 3))

        tk.Label(
            page,
            text=subtitle,
            bg=BG,
            fg=GREY,
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=27, pady=(0, 15))

    def action_button(self, parent, label, command):

        return tk.Button(
            parent,
            text=label,
            command=command,
            bg=BLUE,
            fg="#07111B",
            activebackground=GREEN,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=9,
            cursor="hand2"
        )

    # --------------------------------------------------------
    # HOME PAGE
    # --------------------------------------------------------

    def build_home(self):

        page = self.pages["home"]

        tk.Frame(
            page,
            bg=BLUE,
            height=4,
            width=110
        ).pack(pady=(115, 25))

        tk.Label(
            page,
            text="FOREX SNIPER",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 42, "bold")
        ).pack()

        tk.Label(
            page,
            text="MARKET INTELLIGENCE",
            bg=BG,
            fg=GOLD,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=12)

        tk.Label(
            page,
            text="Forex  •  Gold  •  Silver  •  Indices  •  Energy",
            bg=BG,
            fg=GREY,
            font=("Segoe UI", 11)
        ).pack(pady=5)

        tk.Label(
            page,
            text="LIVE MARKET DATA MONITOR",
            bg=BG,
            fg=BLUE,
            font=("Segoe UI", 9, "bold")
        ).pack(pady=12)

        self.action_button(
            page,
            "OPEN DASHBOARD",
            lambda: self.show_page("dashboard")
        ).pack(pady=30)

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    def build_dashboard(self):

        page = self.pages["dashboard"]

        self.heading(
            page,
            "MARKET DASHBOARD",
            "Expanded currency, metal, index and energy watchlist"
        )

        metrics = tk.Frame(page, bg=BG)
        metrics.pack(fill="x", padx=20, pady=8)

        self.bull_label = self.metric(metrics, "BULLISH", "0", GREEN)
        self.bear_label = self.metric(metrics, "BEARISH", "0", RED)
        self.neutral_label = self.metric(metrics, "NEUTRAL", "0", GOLD)
        self.total_label = self.metric(
            metrics, "SYMBOLS", str(len(SYMBOLS)), WHITE
        )

        controls = tk.Frame(page, bg=BG)
        controls.pack(fill="x", padx=25, pady=10)

        self.action_button(
            controls,
            "SCAN NOW",
            self.scan_all
        ).pack(side="left")

        self.status = tk.Label(
            controls,
            text="Waiting for scan...",
            bg=BG,
            fg=GREY
        )
        self.status.pack(side="left", padx=15)

        category_frame = tk.Frame(page, bg=BG)
        category_frame.pack(fill="x", padx=25, pady=5)

        tk.Label(
            category_frame,
            text="FILTER:",
            bg=BG,
            fg=GREY,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(0, 8))

        self.category_var = tk.StringVar(value="ALL SYMBOLS")

        choices = ["ALL SYMBOLS"] + list(CATEGORIES.keys())

        self.category_box = ttk.Combobox(
            category_frame,
            textvariable=self.category_var,
            values=choices,
            state="readonly",
            width=22
        )
        self.category_box.pack(side="left")
        self.category_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_table()
        )

        frame = tk.Frame(page, bg=PANEL)
        frame.pack(fill="both", expand=True, padx=25, pady=10)

        columns = (
            "symbol", "price", "direction",
            "entry", "sl", "tp", "updated"
        )

        self.market_table = ttk.Treeview(
            frame,
            columns=columns,
            show="headings"
        )

        titles = {
            "symbol": "SYMBOL",
            "price": "LATEST PRICE",
            "direction": "READING",
            "entry": "SIM ENTRY",
            "sl": "SIM SL",
            "tp": "SIM TP",
            "updated": "UPDATED"
        }

        widths = {
            "symbol": 155,
            "price": 130,
            "direction": 120,
            "entry": 130,
            "sl": 130,
            "tp": 130,
            "updated": 100
        }

        for col in columns:
            self.market_table.heading(col, text=titles[col])
            self.market_table.column(
                col,
                width=widths[col],
                anchor="center"
            )

        self.market_table.pack(fill="both", expand=True)

        self.market_table.tag_configure("bull", foreground=GREEN)
        self.market_table.tag_configure("bear", foreground=RED)
        self.market_table.tag_configure("neutral", foreground=GOLD)
        self.market_table.tag_configure("error", foreground=GREY)

    def metric(self, parent, title, value, colour):

        card = tk.Frame(parent, bg=PANEL, padx=16, pady=13)
        card.pack(side="left", fill="x", expand=True, padx=5)

        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=GREY,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        label = tk.Label(
            card,
            text=value,
            bg=PANEL,
            fg=colour,
            font=("Segoe UI", 21, "bold")
        )
        label.pack(anchor="w")

        return label

    # --------------------------------------------------------
    # SIGNAL CENTRE
    # --------------------------------------------------------

    def build_signals(self):

        page = self.pages["signals"]

        self.heading(
            page,
            "SIGNAL CENTRE",
            "Inspect an instrument's latest market analysis"
        )

        selector = tk.Frame(page, bg=PANEL, padx=15, pady=15)
        selector.pack(fill="x", padx=25, pady=10)

        tk.Label(
            selector,
            text="SELECT SYMBOL",
            bg=PANEL,
            fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=8)

        self.selected_symbol = tk.StringVar(
            value="GOLD XAU/USD"
        )

        ttk.Combobox(
            selector,
            textvariable=self.selected_symbol,
            values=list(SYMBOLS.keys()),
            state="readonly",
            width=25
        ).pack(side="left", padx=10)

        self.action_button(
            selector,
            "ANALYSE",
            self.scan_selected
        ).pack(side="left", padx=10)

        self.signal_title = self.value_label(
            page, "GOLD XAU/USD", 23
        )

        self.signal_direction = self.value_label(
            page, "WAITING FOR ANALYSIS", 21, GOLD
        )

        self.entry_value = self.detail(page, "Simulated entry")
        self.sl_value = self.detail(page, "Simulated stop reference")
        self.tp_value = self.detail(page, "Simulated target reference")
        self.price_value = self.detail(page, "Latest price")
        self.rsi_value = self.detail(page, "RSI")
        self.atr_value = self.detail(page, "ATR")
        self.ema_value = self.detail(page, "EMA 20 / EMA 50")

        tk.Label(
            page,
            text="SIMULATION ONLY — NOT LIVE ORDER INSTRUCTIONS",
            bg=BG,
            fg=GOLD,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=30, pady=(20, 8))

        self.signal_note = tk.Label(
            page,
            text="Waiting for analysis.",
            bg=PANEL,
            fg=GREY,
            font=("Segoe UI", 10),
            justify="left",
            padx=15,
            pady=15,
            wraplength=900
        )
        self.signal_note.pack(fill="x", padx=30)

    def value_label(self, parent, text, size=13, colour=WHITE):

        label = tk.Label(
            parent,
            text=text,
            bg=BG,
            fg=colour,
            font=("Segoe UI", size, "bold")
        )
        label.pack(anchor="w", padx=30, pady=6)
        return label

    def detail(self, parent, title):

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=30, pady=4)

        tk.Label(
            row,
            text=title + ":",
            bg=BG,
            fg=GREY,
            width=29,
            anchor="w",
            font=("Segoe UI", 10)
        ).pack(side="left")

        label = tk.Label(
            row,
            text="Waiting...",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 11, "bold")
        )
        label.pack(side="left")
        return label

    # --------------------------------------------------------
    # CALENDAR
    # --------------------------------------------------------

    def build_calendar(self):

        page = self.pages["calendar"]

        self.heading(
            page,
            "ECONOMIC CALENDAR",
            "Economic events displayed in South African time"
        )

        self.action_button(
            page,
            "REFRESH CALENDAR",
            self.load_calendar
        ).pack(anchor="w", padx=25, pady=10)

        self.calendar_status = tk.Label(
            page,
            text="Calendar not loaded.",
            bg=BG,
            fg=GREY
        )
        self.calendar_status.pack(anchor="w", padx=25, pady=5)

        frame = tk.Frame(page, bg=PANEL)
        frame.pack(fill="both", expand=True, padx=25, pady=10)

        columns = ("time", "currency", "event", "impact")

        self.calendar_table = ttk.Treeview(
            frame,
            columns=columns,
            show="headings"
        )

        for col, title in {
            "time": "SOUTH AFRICAN TIME",
            "currency": "CURRENCY",
            "event": "EVENT",
            "impact": "IMPACT"
        }.items():
            self.calendar_table.heading(col, text=title)
            self.calendar_table.column(
                col,
                width=180,
                anchor="center"
            )

        self.calendar_table.column("event", width=450, anchor="w")
        self.calendar_table.pack(fill="both", expand=True)

    # --------------------------------------------------------
    # FORMATTING
    # --------------------------------------------------------

    @staticmethod
    def fmt(value):

        if value is None:
            return "N/A"

        return f"{value:.5f}"

    # --------------------------------------------------------
    # MARKET SCANNER
    # --------------------------------------------------------

    def scan_all(self):

        if self.scanning:
            return

        self.scanning = True
        self.status.config(text="Scanning all categories...")

        threading.Thread(
            target=self.scan_worker,
            daemon=True
        ).start()

    def scan_worker(self):

        results = {}

        for symbol in SYMBOLS:
            try:
                results[symbol] = analyse_symbol(symbol)
            except Exception as error:
                results[symbol] = {
                    "error": str(error)
                }

        self.root.after(
            0,
            lambda: self.finish_scan(results)
        )

    def finish_scan(self, results):

        self.scanning = False
        self.results = results

        bullish = 0
        bearish = 0
        neutral = 0

        for result in results.values():

            if "error" in result:
                continue

            if result["direction"] == "BULLISH":
                bullish += 1
            elif result["direction"] == "BEARISH":
                bearish += 1
            else:
                neutral += 1

        self.bull_label.config(text=str(bullish))
        self.bear_label.config(text=str(bearish))
        self.neutral_label.config(text=str(neutral))
        self.total_label.config(text=str(len(SYMBOLS)))

        self.status.config(
            text=(
                f"Updated {datetime.now().strftime('%H:%M:%S')} "
                f"• {len(results)} instruments checked"
            )
        )

        self.refresh_table()

        selected = self.selected_symbol.get()

        if selected in results and "error" not in results[selected]:
            self.display_signal(results[selected])

        self.root.after(
            REFRESH_SECONDS * 1000,
            self.scan_all
        )

    def refresh_table(self):

        for row in self.market_table.get_children():
            self.market_table.delete(row)

        category = self.category_var.get()

        if category == "ALL SYMBOLS":
            visible = list(SYMBOLS.keys())
        else:
            visible = list(CATEGORIES.get(category, {}).keys())

        for symbol in visible:

            result = self.results.get(symbol)

            if not result:
                continue

            if "error" in result:

                self.market_table.insert(
                    "",
                    "end",
                    values=(
                        symbol,
                        "Unavailable",
                        "NO DATA",
                        "N/A",
                        "N/A",
                        "N/A",
                        "-"
                    ),
                    tags=("error",)
                )
                continue

            direction = result["direction"]

            tag = (
                "bull" if direction == "BULLISH"
                else "bear" if direction == "BEARISH"
                else "neutral"
            )

            self.market_table.insert(
                "",
                "end",
                values=(
                    symbol,
                    self.fmt(result["price"]),
                    direction,
                    self.fmt(result["entry"]),
                    self.fmt(result["sl"]),
                    self.fmt(result["tp"]),
                    result["updated"]
                ),
                tags=(tag,)
            )

    # --------------------------------------------------------
    # SINGLE SYMBOL ANALYSIS
    # --------------------------------------------------------

    def scan_selected(self):

        symbol = self.selected_symbol.get()

        self.signal_direction.config(
            text="ANALYSING...",
            fg=GOLD
        )

        def worker():

            try:
                result = analyse_symbol(symbol)

                self.root.after(
                    0,
                    lambda: self.display_signal(result)
                )

            except Exception as error:

                self.root.after(
                    0,
                    lambda: self.signal_note.config(
                        text=f"Data unavailable: {error}"
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def display_signal(self, result):

        direction = result["direction"]

        colour = (
            GREEN if direction == "BULLISH"
            else RED if direction == "BEARISH"
            else GOLD
        )

        self.signal_title.config(text=result["symbol"])

        self.signal_direction.config(
            text=direction,
            fg=colour
        )

        self.entry_value.config(text=self.fmt(result["entry"]))
        self.sl_value.config(text=self.fmt(result["sl"]))
        self.tp_value.config(text=self.fmt(result["tp"]))
        self.price_value.config(text=self.fmt(result["price"]))
        self.rsi_value.config(text=f'{result["rsi"]:.2f}')
        self.atr_value.config(text=self.fmt(result["atr"]))

        self.ema_value.config(
            text=(
                f'{self.fmt(result["ema20"])} / '
                f'{self.fmt(result["ema50"])}'
            )
        )

        self.signal_note.config(
            text=(
                "Entry, SL and TP fields are educational paper-trading "
                "references calculated from downloaded prices and ATR. "
                "They are not broker quotes or live order instructions. "
                "Data may be delayed, incomplete or unavailable."
            )
        )

    # --------------------------------------------------------
    # ECONOMIC CALENDAR
    # --------------------------------------------------------

    def load_calendar(self):

        if self.calendar_busy:
            return

        self.calendar_busy = True

        self.calendar_status.config(
            text="Loading economic events..."
        )

        def worker():

            try:

                url = (
                    "https://nfs.faireconomy.media/"
                    "ff_calendar_thisweek.json"
                )

                response = requests.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                response.raise_for_status()
                events = response.json()

                self.root.after(
                    0,
                    lambda: self.display_calendar(events)
                )

            except Exception as error:

                self.root.after(
                    0,
                    lambda: self.calendar_status.config(
                        text=f"Calendar unavailable: {error}"
                    )
                )

            finally:
                self.calendar_busy = False

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def display_calendar(self, events):

        for row in self.calendar_table.get_children():
            self.calendar_table.delete(row)

        count = 0

        for event in events:

            try:

                date_text = event.get("date", "")

                dt = datetime.fromisoformat(
                    date_text.replace("Z", "+00:00")
                )

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))

                local = dt.astimezone(
                    ZoneInfo("Africa/Johannesburg")
                )

                self.calendar_table.insert(
                    "",
                    "end",
                    values=(
                        local.strftime("%d %b %Y %H:%M"),
                        event.get("country", "N/A"),
                        event.get("title", "Economic event"),
                        event.get("impact", "N/A")
                    )
                )

                count += 1

            except Exception:
                continue

        self.calendar_status.config(
            text=f"{count} events loaded • SAST"
        )


# ============================================================
# START FOREX SNIPER
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()
    app = ForexSniper(root)
    root.mainloop()


# In[ ]:





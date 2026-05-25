from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


OUT_DIR = Path(__file__).resolve().parent
TMP_DIR = Path(__file__).resolve().parents[2] / "tmp" / "pdfs" / "technical_analysis"
TMP_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUT_DIR / "technical_analysis_course_deck.pdf"
NOTES_PATH = OUT_DIR / "technical_analysis_course_notes.md"

W, H = landscape(letter)
BG = colors.HexColor("#F6F3EA")
INK = colors.HexColor("#182126")
MUTED = colors.HexColor("#62706D")
GREEN = colors.HexColor("#16806A")
BLUE = colors.HexColor("#2C5D85")
RED = colors.HexColor("#B44946")
GOLD = colors.HexColor("#B78628")
TEAL = colors.HexColor("#5EA99D")
PAPER = colors.HexColor("#FFFFFF")
LINE = colors.HexColor("#D7D0C1")


def series(n=260, seed=12, slope=0.12, volatility=1.8, start=50):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, volatility, n).cumsum()
    seasonal = np.sin(np.arange(n) / 8) * 5 + np.sin(np.arange(n) / 23) * 7
    return start + slope * np.arange(n) + noise + seasonal


def sma(values, n):
    return np.convolve(values, np.ones(n) / n, mode="valid")


def style_ax(ax, title):
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color="#182126")
    ax.grid(alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8, colors="#62706D")


def savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=170, facecolor="white")
    plt.close()


def make_charts():
    paths = {}

    x = np.arange(160)
    y = series(160, seed=4, slope=0.08, volatility=1.0, start=92)
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.plot(x, y, color="#182126", linewidth=2)
    support = np.percentile(y, 22)
    resistance = np.percentile(y, 82)
    ax.axhline(support, color="#16806A", linewidth=2.4)
    ax.axhline(resistance, color="#B44946", linewidth=2.4)
    ax.text(4, support + 0.8, "Support: buyers have shown up here", color="#16806A", fontsize=9, weight="bold")
    ax.text(4, resistance + 0.8, "Resistance: sellers have shown up here", color="#B44946", fontsize=9, weight="bold")
    ax.scatter([31, 73, 120], [y[31], y[73], y[120]], color="#16806A", s=42, zorder=5)
    ax.scatter([48, 93, 144], [y[48], y[93], y[144]], color="#B44946", s=42, zorder=5)
    style_ax(ax, "Example Screenshot: Support and Resistance Zones")
    paths["support_resistance"] = TMP_DIR / "support_resistance.png"
    savefig(paths["support_resistance"])

    y2 = series(220, seed=9, slope=0.18, volatility=0.9, start=46)
    x2 = np.arange(len(y2))
    ma20, ma50 = sma(y2, 20), sma(y2, 50)
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.plot(x2, y2, color="#182126", linewidth=1.8, label="Price")
    ax.plot(x2[19:], ma20, color="#2C5D85", linewidth=2.2, label="20-period SMA")
    ax.plot(x2[49:], ma50, color="#B78628", linewidth=2.2, label="50-period SMA")
    ax.fill_between(x2[49:], ma50, y2[49:], where=y2[49:] >= ma50, color="#16806A", alpha=0.12)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style_ax(ax, "Example Screenshot: Simple Moving Averages")
    paths["sma"] = TMP_DIR / "sma.png"
    savefig(paths["sma"])

    y3 = series(420, seed=7, slope=0.14, volatility=1.05, start=42)
    x3 = np.arange(len(y3))
    ma40, ma120 = sma(y3, 40), sma(y3, 120)
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.plot(x3, y3, color="#182126", linewidth=1.4, label="Weekly price")
    ax.plot(x3[39:], ma40, color="#2C5D85", linewidth=2, label="40-week SMA")
    ax.plot(x3[119:], ma120, color="#B78628", linewidth=2.2, label="120-week SMA")
    ax.annotate("Long-term uptrend: price mostly above rising major SMA", xy=(325, y3[325]), xytext=(205, max(y3) - 12),
                arrowprops=dict(arrowstyle="->", color="#16806A"), fontsize=9, color="#16806A", weight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style_ax(ax, "Weekly Chart View: Long-Term Trend Filter")
    paths["weekly_trend"] = TMP_DIR / "weekly_trend.png"
    savefig(paths["weekly_trend"])

    years = np.arange(2010, 2027)
    yearly = np.array([22, 25, 24, 29, 34, 38, 36, 44, 52, 61, 70, 66, 78, 91, 105, 118, 126])
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.plot(years, yearly, color="#182126", linewidth=2.2, marker="o")
    ax.plot(years[4:], sma(yearly, 5), color="#16806A", linewidth=2.5, label="5-year SMA")
    ax.annotate("Yearly chart asks: is the business/market making higher highs over cycles?", xy=(2022, 78), xytext=(2011, 108),
                arrowprops=dict(arrowstyle="->", color="#2C5D85"), fontsize=9, color="#2C5D85", weight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style_ax(ax, "Yearly Chart View: Secular Direction")
    paths["yearly_trend"] = TMP_DIR / "yearly_trend.png"
    savefig(paths["yearly_trend"])

    y4 = series(180, seed=21, slope=0.05, volatility=1.4, start=80)
    vol = np.abs(np.random.default_rng(22).normal(35, 10, len(y4))) + np.maximum(np.diff(np.r_[y4[0], y4]), 0) * 9
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 4.8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(y4, color="#182126", linewidth=1.8)
    ax1.axhline(np.percentile(y4, 76), color="#B44946", linewidth=2)
    style_ax(ax1, "Breakout Needs Volume Confirmation")
    ax2.bar(np.arange(len(vol)), vol, color=np.where(np.diff(np.r_[y4[0], y4]) >= 0, "#16806A", "#B44946"), alpha=0.75)
    ax2.axhline(np.mean(vol), color="#62706D", linewidth=1.4)
    style_ax(ax2, "Volume")
    paths["volume"] = TMP_DIR / "volume_confirmation.png"
    savefig(paths["volume"])

    y5 = series(220, seed=30, slope=0.04, volatility=1.2, start=100)
    delta = np.diff(y5, prepend=y5[0])
    gains = np.maximum(delta, 0)
    losses = np.maximum(-delta, 0)
    avg_gain = np.convolve(gains, np.ones(14) / 14, mode="valid")
    avg_loss = np.convolve(losses, np.ones(14) / 14, mode="valid")
    rsi = 100 - (100 / (1 + avg_gain / np.maximum(avg_loss, 0.001)))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 4.8), sharex=False, gridspec_kw={"height_ratios": [3, 1.4]})
    ax1.plot(y5, color="#182126", linewidth=1.8)
    style_ax(ax1, "Momentum Example: RSI")
    ax2.plot(np.arange(13, len(y5)), rsi, color="#2C5D85", linewidth=1.8)
    ax2.axhline(70, color="#B44946", linewidth=1.4)
    ax2.axhline(30, color="#16806A", linewidth=1.4)
    ax2.text(15, 72, "70: extended strength", fontsize=8, color="#B44946")
    ax2.text(15, 32, "30: possible exhaustion", fontsize=8, color="#16806A")
    ax2.set_ylim(0, 100)
    style_ax(ax2, "RSI")
    paths["rsi"] = TMP_DIR / "rsi.png"
    savefig(paths["rsi"])

    y6 = series(240, seed=44, slope=0.08, volatility=1.0, start=72)
    ema12 = np.zeros_like(y6)
    ema26 = np.zeros_like(y6)
    ema12[0] = y6[0]
    ema26[0] = y6[0]
    for i in range(1, len(y6)):
        ema12[i] = y6[i] * (2 / 13) + ema12[i - 1] * (1 - 2 / 13)
        ema26[i] = y6[i] * (2 / 27) + ema26[i - 1] * (1 - 2 / 27)
    macd = ema12 - ema26
    signal = np.zeros_like(macd)
    signal[0] = macd[0]
    for i in range(1, len(macd)):
        signal[i] = macd[i] * (2 / 10) + signal[i - 1] * (1 - 2 / 10)
    hist = macd - signal
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 4.8), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
    ax1.plot(y6, color="#182126", linewidth=1.8)
    style_ax(ax1, "Trend Momentum Example: MACD")
    ax2.bar(np.arange(len(hist)), hist, color=np.where(hist >= 0, "#16806A", "#B44946"), alpha=0.68)
    ax2.plot(macd, color="#2C5D85", linewidth=1.5, label="MACD")
    ax2.plot(signal, color="#B78628", linewidth=1.5, label="Signal")
    ax2.axhline(0, color="#62706D", linewidth=1)
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    style_ax(ax2, "MACD")
    paths["macd"] = TMP_DIR / "macd.png"
    savefig(paths["macd"])

    return paths


CHARTS = make_charts()


def para(c, text, x, y, w, h, size=18, color=INK, leading=None, bold=False):
    font = "Helvetica-Bold" if bold else "Helvetica"
    style = ParagraphStyle("p", fontName=font, fontSize=size, leading=leading or size * 1.22,
                           textColor=color, alignment=TA_LEFT)
    p = Paragraph(text, style)
    _, ah = p.wrap(w, h)
    p.drawOn(c, x, y + h - ah)
    return ah


def fit_title(c, text, x, y, w, max_size=39, min_size=25):
    size = max_size
    while size > min_size and stringWidth(text, "Helvetica-Bold", size) > w:
        size -= 1
    para(c, text, x, y, w, 64, size=size, bold=True, leading=size * 1.08)


def footer(c, n, section):
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    c.drawString(0.55 * inch, 0.32 * inch, section)
    c.drawRightString(W - 0.55 * inch, 0.32 * inch, str(n))


def header(c, title, subtitle=None):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.rect(0, H - 0.13 * inch, W, 0.13 * inch, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.rect(0, H - 0.19 * inch, 2.0 * inch, 0.06 * inch, stroke=0, fill=1)
    fit_title(c, title, 0.7 * inch, H - 1.05 * inch, W - 1.4 * inch)
    if subtitle:
        para(c, subtitle, 0.72 * inch, H - 1.42 * inch, W - 1.4 * inch, 32, size=14.5, color=MUTED)


def bullets(c, items, x, y, w, size=17, gap=11):
    cy = y
    for item in items:
        c.setFillColor(GREEN)
        c.circle(x + 6, cy + 9, 3, stroke=0, fill=1)
        used = para(c, item, x + 20, cy - 5, w - 20, 48, size=size, leading=size * 1.25)
        cy -= max(used + gap, 30)


def card(c, x, y, w, h, title, body, accent=GREEN):
    c.setFillColor(PAPER)
    c.setStrokeColor(LINE)
    c.roundRect(x, y, w, h, 6, stroke=1, fill=1)
    c.setFillColor(accent)
    c.rect(x, y + h - 0.11 * inch, w, 0.11 * inch, stroke=0, fill=1)
    para(c, title, x + 0.18 * inch, y + h - 0.42 * inch, w - 0.36 * inch, 24, size=13.8, bold=True)
    para(c, body, x + 0.18 * inch, y + 0.15 * inch, w - 0.36 * inch, h - 0.58 * inch, size=11.8, color=MUTED, leading=14.5)


def title_slide(c, n):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.rect(0, 0, W, 0.32 * inch, stroke=0, fill=1)
    para(c, "Technical Analysis<br/>Course Deck", 0.7 * inch, H - 1.85 * inch, W - 1.4 * inch, 110, size=42, bold=True, leading=45)
    para(c, "How to read yearly, weekly, and daily charts for trend, support/resistance, moving averages, volume, and momentum.", 0.75 * inch, H - 2.55 * inch, W - 1.5 * inch, 60, size=17, color=MUTED, leading=22)
    card(c, 0.75 * inch, 1.05 * inch, 2.65 * inch, 1.15 * inch, "Purpose", "Use charts to organize risk and timing, not to predict the future perfectly.", GREEN)
    card(c, 3.65 * inch, 1.05 * inch, 2.65 * inch, 1.15 * inch, "Best use", "Long-term trend context first, then weekly setup, then daily entry.", BLUE)
    card(c, 6.55 * inch, 1.05 * inch, 2.65 * inch, 1.15 * inch, "Rule", "Every chart idea needs an invalidation level and position-size plan.", GOLD)
    footer(c, n, "Technical analysis")


def section_slide(c, n, title, subtitle, section, accent):
    c.setFillColor(accent)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    para(c, section.upper(), 0.75 * inch, H - 1.1 * inch, W - 1.5 * inch, 25, size=13, color=colors.white, bold=True)
    para(c, title, 0.75 * inch, H - 2.35 * inch, W - 1.5 * inch, 90, size=42, color=colors.white, bold=True, leading=46)
    para(c, subtitle, 0.78 * inch, H - 3.1 * inch, W - 1.6 * inch, 70, size=17, color=colors.white, leading=23)
    footer(c, n, section)


def simple_slide(c, n, title, subtitle, items, section, image=None):
    header(c, title, subtitle)
    if image:
        bullets(c, items, 0.74 * inch, H - 2.05 * inch, 4.25 * inch, size=15.6, gap=9)
        c.drawImage(str(image), 5.12 * inch, 0.92 * inch, 4.35 * inch, 3.35 * inch, preserveAspectRatio=True, mask="auto")
    else:
        bullets(c, items, 0.82 * inch, H - 1.95 * inch, W - 1.65 * inch)
    footer(c, n, section)


def cards_slide(c, n, title, subtitle, cards, section):
    header(c, title, subtitle)
    cols = 3
    x0 = 0.65 * inch
    y0 = 0.88 * inch
    cw = (W - 1.3 * inch - 0.35 * inch * 2) / 3
    ch = 1.2 * inch
    for i, item in enumerate(cards):
        x = x0 + (i % cols) * (cw + 0.35 * inch)
        y = y0 + (1 - i // cols) * (ch + 0.32 * inch)
        card(c, x, y, cw, ch, item[0], item[1], item[2])
    footer(c, n, section)


SLIDES = [
    ("title",),
    ("simple", "Technical Analysis Is a Map", "A chart is not a crystal ball. It is a tool for structure.", [
        "Charts help identify trend, possible buying/selling zones, and risk levels.",
        "The same pattern can fail. That is why stops, sizing, and invalidation matter.",
        "Use higher timeframes to define direction, then lower timeframes for timing.",
        "For long-term investing, technical analysis should support fundamentals, not replace them.",
    ], "Mindset"),
    ("simple", "The Three-Timeframe Method", "Start big, then zoom in.", [
        "Yearly/monthly chart: secular direction and major market cycles.",
        "Weekly chart: primary trend, base patterns, and major support/resistance.",
        "Daily chart: entry timing, pullbacks, breakouts, and stop placement.",
        "If the yearly and weekly trend disagree, reduce size or wait for clarity.",
    ], "Mindset"),
    ("section", "Part 1: Trend", "Long-term trend tells you whether the wind is at your back.", "Trend", BLUE),
    ("simple", "How to Check the Yearly Chart", "The yearly chart removes noise and shows the big picture.", [
        "Look for higher highs and higher lows across several years.",
        "Compare price to a multi-year moving average, such as a 5-year SMA.",
        "Notice whether corrections recover quickly or break prior cycle lows.",
        "Use it for context, not exact entries.",
    ], "Trend", CHARTS["yearly_trend"]),
    ("simple", "How to Check the Weekly Chart", "The weekly chart is often the most useful long-term trading view.", [
        "A healthy long-term uptrend often holds above a rising 40-week or 50-week SMA.",
        "A flattening or falling major SMA says momentum may be changing.",
        "Weekly support/resistance levels are more important than noisy daily levels.",
        "Long-term investors can use weekly pullbacks to avoid emotional entries.",
    ], "Trend", CHARTS["weekly_trend"]),
    ("cards", "Trend Reading Checklist", "Use this before looking for indicators.", [
        ("Direction", "Are highs and lows rising, falling, or sideways?", BLUE),
        ("Slope", "Are major moving averages rising or falling?", GREEN),
        ("Location", "Is price above or below the main trend average?", GOLD),
        ("Age", "Is the trend early, mature, or extended?", TEAL),
        ("Damage", "Did price break an important prior low?", RED),
        ("Context", "Does the sector or market confirm the trend?", MUTED),
    ], "Trend"),
    ("section", "Part 2: Support and Resistance", "These zones help define where risk and reward may change.", "Levels", GREEN),
    ("simple", "Support and Resistance", "Think zones, not perfect lines.", [
        "Support is an area where buyers previously appeared.",
        "Resistance is an area where sellers previously appeared.",
        "The more visible the level, the more traders may react to it.",
        "A broken resistance level can become support; broken support can become resistance.",
    ], "Levels", CHARTS["support_resistance"]),
    ("simple", "How to Draw Levels", "Keep it simple and visible.", [
        "Use the weekly chart first, then refine on the daily chart.",
        "Mark obvious swing highs, swing lows, and gap zones.",
        "Prefer zones that were tested multiple times or caused strong reversals.",
        "Do not clutter the chart. Three to five major levels is usually enough.",
    ], "Levels"),
    ("simple", "Breakout vs. Pullback", "Two common ways traders use levels.", [
        "Breakout: price pushes above resistance, ideally with strong volume.",
        "Pullback: price returns to support or a moving average after an uptrend.",
        "False breakout: price moves through a level, then quickly falls back below it.",
        "A setup is incomplete without a stop and a risk/reward estimate.",
    ], "Levels"),
    ("section", "Part 3: Moving Averages", "Moving averages smooth noise and reveal trend behavior.", "Indicators", GOLD),
    ("simple", "Simple Moving Average", "An SMA is the average closing price over a chosen number of periods.", [
        "20-day SMA: short-term trend and pullback reference.",
        "50-day SMA: intermediate trend often watched by swing traders.",
        "200-day SMA: major long-term trend line on daily charts.",
        "40-week or 50-week SMA: long-term trend filter on weekly charts.",
    ], "Indicators", CHARTS["sma"]),
    ("simple", "How to Use SMA Without Overusing It", "The slope and price location matter more than tiny crossovers.", [
        "Bullish context: price above a rising major SMA.",
        "Caution context: price below a falling major SMA.",
        "Pullbacks to a rising SMA can be buy zones only if the trend remains intact.",
        "Moving averages lag. They confirm trend more than they predict reversals.",
    ], "Indicators"),
    ("simple", "Common SMA Signals", "Signals are useful only with context.", [
        "Golden cross: shorter average crosses above longer average.",
        "Death cross: shorter average crosses below longer average.",
        "Moving average stack: short above medium above long can show strong trend.",
        "Flat averages often mean chop; reduce expectations in sideways markets.",
    ], "Indicators"),
    ("section", "Part 4: Volume and Momentum", "Indicators should answer a question, not decorate a chart.", "Indicators", TEAL),
    ("simple", "Volume Confirmation", "Volume asks whether a move has participation.", [
        "Breakouts are more credible when volume is above average.",
        "Low-volume breakouts are more vulnerable to failure.",
        "Rising price with falling volume may show weakening demand.",
        "High-volume selloffs near support can warn that institutions are exiting.",
    ], "Indicators", CHARTS["volume"]),
    ("simple", "RSI: Relative Strength Index", "RSI measures momentum, not value.", [
        "Above 70 can mean strong momentum, not automatically a short signal.",
        "Below 30 can mean weakness or possible exhaustion, not automatically a buy.",
        "Bullish divergence: price makes a lower low while RSI makes a higher low.",
        "Use RSI with trend and levels, not by itself.",
    ], "Indicators", CHARTS["rsi"]),
    ("simple", "MACD", "MACD compares faster and slower moving averages.", [
        "MACD above zero often supports bullish trend momentum.",
        "MACD below zero often supports bearish trend momentum.",
        "Signal-line crosses can be late, so use them as confirmation.",
        "The histogram shows whether momentum is strengthening or weakening.",
    ], "Indicators", CHARTS["macd"]),
    ("cards", "Indicator Rules", "Avoid indicator overload.", [
        ("One trend tool", "Example: 50-day or 40-week SMA.", BLUE),
        ("One level tool", "Support, resistance, or anchored VWAP.", GREEN),
        ("One volume tool", "Volume vs. average volume.", TEAL),
        ("One momentum tool", "RSI or MACD, not five versions.", GOLD),
        ("One risk rule", "Stop and position size before entry.", RED),
        ("One journal", "Track what worked, failed, and why.", MUTED),
    ], "Indicators"),
    ("section", "Part 5: Long-Term Trend Workflow", "A repeatable chart routine for yearly and weekly analysis.", "Workflow", BLUE),
    ("simple", "Long-Term Trend Routine", "Do this once a week for watchlist names.", [
        "1. Start with the yearly/monthly chart: uptrend, downtrend, or range?",
        "2. Move to weekly: is price above a rising 40-week or 50-week SMA?",
        "3. Mark major weekly support/resistance and prior breakout areas.",
        "4. Check relative strength versus the market or sector.",
        "5. Only then use the daily chart for entry and stop placement.",
    ], "Workflow"),
    ("simple", "Weekly Trend Grades", "A simple scoring system keeps emotions lower.", [
        "A: price above rising 40-week SMA, higher highs/lows, strong relative strength.",
        "B: price above SMA but extended, choppy, or near resistance.",
        "C: sideways range with unclear SMA slope.",
        "D: price below falling SMA or making lower lows.",
        "Rule: prefer A/B for long ideas; avoid forcing trades in C/D.",
    ], "Workflow"),
    ("simple", "Entry Planning from the Daily Chart", "Daily charts are for timing, not deciding the whole thesis.", [
        "Buy near support only if the weekly trend remains healthy.",
        "For breakouts, require a close above resistance and volume confirmation.",
        "Place the stop where the setup is invalid, not where the loss feels comfortable.",
        "If the stop is too far away, reduce position size or skip the trade.",
    ], "Workflow"),
    ("cards", "Long-Term Trend Checklist", "Use this before buying or adding.", [
        ("Yearly", "Higher highs/lows across cycles?", BLUE),
        ("Weekly SMA", "Above a rising 40/50-week average?", GREEN),
        ("Support", "Nearest logical support level?", TEAL),
        ("Resistance", "Nearest overhead supply?", GOLD),
        ("Volume", "Accumulation or distribution signs?", RED),
        ("Plan", "Entry, stop, target, review date?", MUTED),
    ], "Workflow"),
    ("section", "Part 6: Practice", "The best chart education is repeated, written, and reviewed.", "Practice", GREEN),
    ("simple", "Practice 1: Mark a Weekly Chart", "Use a real charting site or paper chart after the lesson.", [
        "Pick one large, liquid stock or ETF.",
        "Switch to weekly candles and add a 40-week or 50-week SMA.",
        "Mark three support zones and three resistance zones.",
        "Write whether trend is A, B, C, or D and explain why.",
    ], "Practice"),
    ("simple", "Practice 2: Compare Timeframes", "The goal is to see how context changes interpretation.", [
        "On the yearly/monthly chart, describe the major trend.",
        "On the weekly chart, identify the current setup.",
        "On the daily chart, identify a possible entry and invalidation level.",
        "If the timeframes disagree, write what evidence would create clarity.",
    ], "Practice"),
    ("simple", "Practice 3: Indicator Discipline", "Use fewer tools and explain them better.", [
        "Create one chart with SMA, volume, and RSI only.",
        "For each indicator, write one sentence explaining what it says.",
        "Remove any indicator that does not change the decision.",
        "Save a screenshot before the trade and review it afterward.",
    ], "Practice"),
    ("simple", "Common Beginner Mistakes", "Most chart mistakes are behavior mistakes wearing technical clothing.", [
        "Drawing too many lines until every price looks important.",
        "Buying just because RSI is low while the trend is still broken.",
        "Chasing a breakout far above the breakout level.",
        "Ignoring earnings dates, market trend, or sector weakness.",
        "Moving stops lower because the trader does not want to be wrong.",
    ], "Practice"),
    ("simple", "Final Rule Set", "A simple technical-analysis rule book.", [
        "Trade in the direction of the higher-timeframe trend whenever possible.",
        "Buy near support or on confirmed breakouts, not in the middle of nowhere.",
        "Use moving averages as context, not magic signals.",
        "Require volume or momentum confirmation for important moves.",
        "Know the exit before the entry.",
    ], "Practice"),
]


def make_pdf():
    c = canvas.Canvas(str(PDF_PATH), pagesize=landscape(letter))
    for idx, slide in enumerate(SLIDES, 1):
        if slide[0] == "title":
            title_slide(c, idx)
        elif slide[0] == "section":
            _, title, subtitle, section, accent = slide
            section_slide(c, idx, title, subtitle, section, accent)
        elif slide[0] == "simple":
            _, title, subtitle, items, section, *rest = slide
            simple_slide(c, idx, title, subtitle, items, section, rest[0] if rest else None)
        elif slide[0] == "cards":
            _, title, subtitle, items, section = slide
            cards_slide(c, idx, title, subtitle, items, section)
        c.showPage()
    c.save()


def make_notes():
    text = f"""# Technical Analysis Course Notes

Generated deck: `{PDF_PATH.name}`

This deck is a separate technical-analysis course focused on reading long-term trend from yearly/monthly and weekly charts, then using daily charts for timing.

Included chart screenshot-style examples:

- Support and resistance zones
- Simple moving averages
- Yearly long-term trend
- Weekly long-term trend filter
- Breakout volume confirmation
- RSI momentum
- MACD momentum

Suggested teaching sequence:

- Session 1: mindset, three-timeframe method, trend
- Session 2: support/resistance and moving averages
- Session 3: volume, RSI, MACD, and indicator discipline
- Session 4: long-term trend workflow and practice exercises

Teaching reminder:

Charts do not remove risk. They help define where the idea is valid, where it is invalid, and whether the possible reward is worth the possible loss.
"""
    NOTES_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    make_pdf()
    make_notes()
    print(f"Wrote {PDF_PATH}")
    print(f"Wrote {NOTES_PATH}")
    print(f"Slides: {len(SLIDES)}")

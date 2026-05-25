from math import sin
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
TMP_DIR = Path(__file__).resolve().parents[2] / "tmp" / "pdfs"
TMP_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUT_DIR / "stock_market_trading_course_for_teens.pdf"
NOTES_PATH = OUT_DIR / "stock_market_trading_course_facilitator_notes.md"

W, H = landscape(letter)

BG = colors.HexColor("#F7F5EF")
INK = colors.HexColor("#17202A")
MUTED = colors.HexColor("#5F6B6D")
GREEN = colors.HexColor("#1E7F68")
BLUE = colors.HexColor("#2D5F8B")
RED = colors.HexColor("#B44D47")
GOLD = colors.HexColor("#B88928")
TEAL = colors.HexColor("#6BAFA4")
PAPER = colors.HexColor("#FFFFFF")
LINE = colors.HexColor("#D7D1C3")


def money(v):
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def build_charts():
    years = np.arange(0, 51)
    monthly = 150
    initial = 500
    r = 0.08 / 12
    balances = []
    bal = initial
    for m in range(51 * 12 + 1):
        if m % 12 == 0:
            balances.append(bal)
        bal = bal * (1 + r) + monthly
    plt.figure(figsize=(8, 4.5), dpi=160)
    plt.plot(years, balances[: len(years)], color="#1E7F68", linewidth=3)
    plt.fill_between(years, balances[: len(years)], color="#6BAFA4", alpha=0.25)
    plt.title("Starting early: $500 initial + $150/month at 8% example", fontsize=12)
    plt.xlabel("Years invested")
    plt.ylabel("Future value")
    plt.grid(alpha=0.2)
    plt.gca().yaxis.set_major_formatter(lambda x, pos: money(x))
    path = TMP_DIR / "compound_growth.png"
    plt.tight_layout()
    plt.savefig(path, transparent=False, facecolor="#FFFFFF")
    plt.close()

    x = np.arange(80)
    trend = 100 + x * 0.42
    noise = np.array([sin(i / 2.5) * 2.8 + sin(i / 6) * 4 for i in x])
    price = trend + noise
    ma10 = np.convolve(price, np.ones(10) / 10, mode="valid")
    ma30 = np.convolve(price, np.ones(30) / 30, mode="valid")
    plt.figure(figsize=(8, 4.5), dpi=160)
    plt.plot(x, price, color="#17202A", linewidth=2, label="Price")
    plt.plot(x[9:], ma10, color="#2D5F8B", linewidth=2, label="10-day moving avg")
    plt.plot(x[29:], ma30, color="#B88928", linewidth=2, label="30-day moving avg")
    plt.title("Technical analysis looks for trend, momentum, support, and risk levels", fontsize=12)
    plt.xlabel("Trading days")
    plt.ylabel("Price")
    plt.legend(frameon=False, loc="upper left", fontsize=9)
    plt.grid(alpha=0.18)
    path2 = TMP_DIR / "technical_trend.png"
    plt.tight_layout()
    plt.savefig(path2, transparent=False, facecolor="#FFFFFF")
    plt.close()

    plt.figure(figsize=(8, 4.5), dpi=160)
    labels = ["No hedge", "Protective put", "Covered call"]
    down = [-30, -12, -24]
    flat = [0, -4, 4]
    up = [30, 24, 10]
    pos = np.arange(len(labels))
    width = 0.24
    plt.bar(pos - width, down, width, label="Stock down", color="#B44D47")
    plt.bar(pos, flat, width, label="Stock flat", color="#B88928")
    plt.bar(pos + width, up, width, label="Stock up", color="#1E7F68")
    plt.axhline(0, color="#17202A", linewidth=1)
    plt.xticks(pos, labels)
    plt.ylabel("Illustrative outcome")
    plt.title("Options change the shape of risk and reward", fontsize=12)
    plt.legend(frameon=False, fontsize=9)
    plt.grid(axis="y", alpha=0.18)
    path3 = TMP_DIR / "options_payoff_shapes.png"
    plt.tight_layout()
    plt.savefig(path3, transparent=False, facecolor="#FFFFFF")
    plt.close()

    return path, path2, path3


CHART_COMPOUND, CHART_TECHNICAL, CHART_OPTIONS = build_charts()


def para(c, text, x, y, w, h, size=18, color=INK, leading=None, bold=False):
    font = "Helvetica-Bold" if bold else "Helvetica"
    style = ParagraphStyle(
        "p",
        fontName=font,
        fontSize=size,
        leading=leading or size * 1.25,
        textColor=color,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    p = Paragraph(text, style)
    aw, ah = p.wrap(w, h)
    p.drawOn(c, x, y + h - ah)
    return ah


def fit_title(c, text, x, y, w, max_size=40, min_size=26):
    size = max_size
    while size > min_size and stringWidth(text, "Helvetica-Bold", size) > w:
        size -= 1
    para(c, text, x, y, w, 65, size=size, bold=True, leading=size * 1.08)


def bullets(c, items, x, y, w, size=18, gap=13, color=INK):
    cy = y
    for item in items:
        c.setFillColor(GREEN)
        c.circle(x + 6, cy + 9, 3.1, stroke=0, fill=1)
        used = para(c, item, x + 20, cy - 5, w - 20, 48, size=size, color=color)
        cy -= max(used + gap, 32)
    return cy


def footer(c, n, section):
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawString(0.55 * inch, 0.32 * inch, section)
    c.drawRightString(W - 0.55 * inch, 0.32 * inch, f"{n}")


def header(c, title, subtitle=None, section=""):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.rect(0, H - 0.13 * inch, W, 0.13 * inch, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.rect(0, H - 0.19 * inch, 2.0 * inch, 0.06 * inch, stroke=0, fill=1)
    fit_title(c, title, 0.7 * inch, H - 1.08 * inch, W - 1.4 * inch)
    if subtitle:
        para(c, subtitle, 0.72 * inch, H - 1.48 * inch, W - 1.4 * inch, 34, size=15, color=MUTED)


def draw_card(c, x, y, w, h, title, body, accent=GREEN):
    c.setFillColor(PAPER)
    c.setStrokeColor(LINE)
    c.roundRect(x, y, w, h, 6, stroke=1, fill=1)
    c.setFillColor(accent)
    c.rect(x, y + h - 0.12 * inch, w, 0.12 * inch, stroke=0, fill=1)
    para(c, title, x + 0.22 * inch, y + h - 0.48 * inch, w - 0.44 * inch, 24, size=15, color=INK, bold=True)
    para(c, body, x + 0.22 * inch, y + 0.2 * inch, w - 0.44 * inch, h - 0.68 * inch, size=12.2, color=MUTED, leading=15.5)


def title_slide(c, n):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.rect(0, 0, W, 0.32 * inch, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.rect(0, 0.32 * inch, W, 0.08 * inch, stroke=0, fill=1)
    para(c, "Stock Market Investing and Trading<br/>Course", 0.7 * inch, H - 1.95 * inch, W - 1.4 * inch, 112, size=38, bold=True, leading=42)
    para(c, "A parent-led course for a 17-year-old: building wealth slowly, managing risk carefully, and understanding trading tools before risking real money.", 0.75 * inch, H - 2.72 * inch, W - 1.5 * inch, 74, size=17, color=MUTED, leading=23)
    draw_card(c, 0.75 * inch, 1.0 * inch, 2.55 * inch, 1.25 * inch, "Core message", "Financial education is a life skill. The goal is not quick money. The goal is better decisions.", GREEN)
    draw_card(c, 3.55 * inch, 1.0 * inch, 2.55 * inch, 1.25 * inch, "Time horizon", "Investing is measured in years. Swing trading is measured in days or weeks. Futures are advanced risk tools.", BLUE)
    draw_card(c, 6.35 * inch, 1.0 * inch, 2.55 * inch, 1.25 * inch, "Guardrails", "Start with learning, simulations, diversification, small position sizes, and written rules.", GOLD)
    footer(c, n, "Course overview")


def section_slide(c, n, title, subtitle, section, accent=GREEN):
    c.setFillColor(accent)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(colors.white)
    para(c, section.upper(), 0.75 * inch, H - 1.1 * inch, W - 1.5 * inch, 25, size=13, bold=True)
    para(c, title, 0.75 * inch, H - 2.35 * inch, W - 1.5 * inch, 90, size=42, bold=True, leading=46)
    para(c, subtitle, 0.78 * inch, H - 3.1 * inch, W - 1.6 * inch, 70, size=17, leading=23)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.22))
    for i in range(7):
        c.circle(W - (0.8 + i * 0.22) * inch, 0.8 * inch + i * 0.12 * inch, 9 + i * 5, stroke=0, fill=1)
    footer(c, n, section)


def simple_slide(c, n, title, subtitle, items, section, image=None):
    header(c, title, subtitle, section)
    if image:
        bullets(c, items, 0.75 * inch, H - 2.1 * inch, 4.2 * inch, size=16)
        c.drawImage(str(image), 5.15 * inch, 1.0 * inch, 4.2 * inch, 3.15 * inch, preserveAspectRatio=True, mask="auto")
    else:
        bullets(c, items, 0.85 * inch, H - 2.0 * inch, W - 1.65 * inch, size=18)
    footer(c, n, section)


def cards_slide(c, n, title, subtitle, cards, section):
    header(c, title, subtitle, section)
    x0, y0 = 0.65 * inch, 0.86 * inch
    cols = 3
    card_w = (W - 1.3 * inch - 0.36 * inch * (cols - 1)) / cols
    card_h = 1.22 * inch
    for idx, card in enumerate(cards):
        row = idx // cols
        col = idx % cols
        x = x0 + col * (card_w + 0.36 * inch)
        y = y0 + (1 - row) * (card_h + 0.32 * inch) if len(cards) > 3 else y0 + 0.7 * inch
        draw_card(c, x, y, card_w, card_h, card[0], card[1], card[2] if len(card) > 2 else GREEN)
    footer(c, n, section)


SLIDES = [
    ("title",),
    ("simple", "Before We Begin", "This is education, not personal financial advice.", [
        "A 17-year-old usually needs a parent or guardian involved for real accounts, depending on account type and broker rules.",
        "Use paper trading or tiny educational amounts first. The first goal is judgment, not profit.",
        "Never borrow money to invest or trade. Avoid margin, naked options, and oversized futures positions.",
        "Any strategy must answer: What can go wrong? How much can we lose? When do we stop?",
    ], "Safety first"),
    ("section", "Part 1: Money Foundations", "Why investing matters before we talk about charts, options, or futures.", "Foundation", GREEN),
    ("simple", "Saving vs. Investing", "Both matter, but they solve different problems.", [
        "Saving protects near-term needs: emergency fund, school costs, car repairs, and spending goals.",
        "Investing accepts uncertainty to pursue higher long-term growth.",
        "Money needed soon should usually be kept safer than money meant for 10, 20, or 40 years from now.",
        "Inflation quietly reduces purchasing power, so long-term money needs a plan to grow.",
    ], "Foundation"),
    ("simple", "The Long-Term Advantage", "Time turns small habits into serious optionality.", [
        "Example: $500 today plus $150 per month for 50 years at 8% grows to roughly $1.1 million before taxes and fees.",
        "Most of the ending value comes late, because compounding needs time.",
        "The powerful habit is regular investing, not perfect timing.",
        "A teenager has an asset adults cannot buy: decades.",
    ], "Foundation", CHART_COMPOUND),
    ("cards", "Five Core Ideas", "These ideas keep the whole course anchored.", [
        ("Ownership", "A stock is a piece of a business, not a lottery ticket.", GREEN),
        ("Compounding", "Returns can earn returns when money stays invested.", BLUE),
        ("Diversification", "Many holdings reduce single-company damage.", TEAL),
        ("Risk", "Higher potential return usually means more uncertainty.", RED),
        ("Behavior", "Patience, humility, and rules matter as much as analysis.", GOLD),
        ("Costs", "Fees, taxes, spreads, and mistakes reduce results.", MUTED),
    ], "Foundation"),
    ("simple", "Risk Has Many Faces", "A good investor names the risk before buying.", [
        "Market risk: the whole market falls.",
        "Business risk: one company disappoints.",
        "Valuation risk: a great company is bought at too high a price.",
        "Liquidity risk: it is hard to exit without moving the price.",
        "Behavior risk: panic selling, revenge trading, FOMO, or ignoring a plan.",
    ], "Foundation"),
    ("simple", "The Wealth-Building Order", "A practical sequence for a young investor.", [
        "1. Learn budgeting, saving, interest, taxes, and account types.",
        "2. Build emergency savings before taking big market risk.",
        "3. Invest steadily in diversified funds for long-term goals.",
        "4. Study individual stocks with small, controlled position sizes.",
        "5. Treat trading, options, and futures as advanced skills with strict guardrails.",
    ], "Foundation"),
    ("section", "Part 2: Long-Term Stock Investing", "How to think like a business owner instead of a price chaser.", "Long-term investing", BLUE),
    ("simple", "What Makes a Stock Attractive?", "For long-term investing, quality matters more than excitement.", [
        "A business you can understand and explain in plain English.",
        "Revenue and earnings that can grow over years, not only one quarter.",
        "Strong balance sheet: manageable debt and enough cash flexibility.",
        "Competitive advantage: brand, network effect, cost edge, switching costs, or intellectual property.",
        "Reasonable valuation compared with growth, quality, and risk.",
    ], "Long-term investing"),
    ("cards", "Long-Term Stock Selection Checklist", "Use this before buying an individual company.", [
        ("Understand", "What does the company sell, who buys it, and why does it win?", GREEN),
        ("Growth", "Are revenue, earnings, and cash flow improving over several years?", BLUE),
        ("Moat", "Can competitors easily copy it, undercut it, or replace it?", GOLD),
        ("Balance sheet", "Can the company survive recessions, rate shocks, and mistakes?", TEAL),
        ("Valuation", "Is the price sensible, or does it require perfection?", RED),
        ("Thesis", "Write the reason to own it and what would prove you wrong.", MUTED),
    ], "Long-term investing"),
    ("simple", "Fundamental Analysis: The Business Lens", "Fundamentals ask: what is this business worth?", [
        "Income statement: sales, margins, profit, and earnings per share.",
        "Balance sheet: cash, debt, assets, liabilities, and shareholder equity.",
        "Cash flow statement: whether profits convert into real cash.",
        "Management discussion: strategy, risks, competition, and capital allocation.",
        "Industry context: market size, pricing power, regulation, and disruption.",
    ], "Long-term investing"),
    ("cards", "Useful Fundamental Metrics", "No single metric tells the whole story.", [
        ("Revenue growth", "Shows demand, but growth without profit can be fragile.", GREEN),
        ("Gross margin", "Hints at pricing power and product economics.", BLUE),
        ("Operating margin", "Shows how efficiently the company runs.", TEAL),
        ("Free cash flow", "Cash left after running and reinvesting in the business.", GOLD),
        ("Debt/equity", "Helps judge financial risk and flexibility.", RED),
        ("P/E or P/S", "A valuation shortcut that needs context.", MUTED),
    ], "Long-term investing"),
    ("simple", "Building a Starter Portfolio", "Simple beats clever for most long-term goals.", [
        "A diversified index fund or ETF can be the core because it owns many companies at once.",
        "Individual stocks can be satellites: small positions chosen through research.",
        "Rebalance occasionally so one winner or one theme does not dominate the plan.",
        "Automated monthly contributions remove emotion from the decision to invest.",
        "Review the plan annually; do not redesign it every time markets get noisy.",
    ], "Long-term investing"),
    ("simple", "A One-Page Stock Thesis", "If she cannot write it, she probably does not understand it yet.", [
        "Company: what it does and how it makes money.",
        "Why now: why the business can be better in 5 to 10 years.",
        "Numbers: growth, margins, cash flow, debt, and valuation.",
        "Risks: what could damage the thesis.",
        "Decision rule: buy, watch, trim, or sell based on evidence.",
    ], "Long-term investing"),
    ("section", "Part 3: Swing Trading", "Short-term trading is a skill game with risk control at the center.", "Swing trading", GOLD),
    ("simple", "Investing vs. Swing Trading", "Different games, different scoreboards.", [
        "Investing asks whether a business will become more valuable over years.",
        "Swing trading asks whether price may move favorably over days or weeks.",
        "Trading needs entries, exits, stops, position sizing, and a journal.",
        "A profitable idea can still be a bad trade if the risk is too large.",
        "Frequent trading can increase taxes, costs, and emotional mistakes.",
    ], "Swing trading"),
    ("simple", "Technical Analysis: The Price Lens", "Technical analysis studies price, volume, trend, and market psychology.", [
        "Trend: is price making higher highs and higher lows, or the opposite?",
        "Support/resistance: where have buyers or sellers appeared before?",
        "Moving averages: simple tools to identify trend and possible changes.",
        "Volume: confirms whether a move has broad participation.",
        "Momentum: helps spot strength, weakness, and exhaustion.",
    ], "Swing trading", CHART_TECHNICAL),
    ("cards", "Swing Stock Selection Checklist", "Find stocks that can move, then control the risk.", [
        ("Liquidity", "Tight spreads and enough volume to enter and exit cleanly.", GREEN),
        ("Catalyst", "Earnings, product news, sector strength, rates, or macro events.", BLUE),
        ("Trend", "Price already showing strength or a clear reversal pattern.", GOLD),
        ("Relative strength", "Outperforming its sector or the broad market.", TEAL),
        ("Risk/reward", "Potential upside should justify the planned downside.", RED),
        ("Plan", "Entry, stop, target, invalidation, and maximum loss written first.", MUTED),
    ], "Swing trading"),
    ("simple", "Risk Management Math", "This is the part that keeps traders alive long enough to learn.", [
        "Decide the maximum account loss per trade before entering.",
        "Example: on a $1,000 practice account, risking 1% means a $10 max loss.",
        "If entry is $50 and stop is $48, risk is $2 per share, so the size is 5 shares.",
        "Never move a stop farther away just to avoid being wrong.",
        "The goal is not to be right every time. The goal is to avoid one large mistake.",
    ], "Swing trading"),
    ("simple", "A Basic Swing Trading Workflow", "Repeatable process beats random opinions.", [
        "Scan: identify liquid stocks with trend, catalyst, or relative strength.",
        "Study: mark trend, support, resistance, volume, and earnings date.",
        "Plan: define entry, stop, target, size, and reason.",
        "Execute: use limit orders where appropriate and avoid chasing.",
        "Review: journal the trade, including emotions and rule violations.",
    ], "Swing trading"),
    ("section", "Part 4: Options for Protection", "Options can manage risk, but they are complex and can create new risks.", "Options", RED),
    ("simple", "Options Basics", "An option is a contract based on an underlying asset.", [
        "Call: right, but not obligation, to buy at a strike price by expiration.",
        "Put: right, but not obligation, to sell at a strike price by expiration.",
        "Premium: the price paid or received for the option.",
        "One standard equity option contract usually represents 100 shares.",
        "Options require broker approval and the official risk disclosure document.",
    ], "Options"),
    ("simple", "Protective Put", "A protective put is like paying a premium to define downside risk.", [
        "Own the stock or ETF, then buy a put option below or near the current price.",
        "If the stock falls hard, the put can gain value and offset part of the loss.",
        "Cost: the premium reduces returns if the stock does not fall.",
        "It does not make a bad investment good. It buys time and defines part of the risk.",
        "Use sparingly; repeated hedging can become expensive.",
    ], "Options", CHART_OPTIONS),
    ("simple", "Covered Call", "A covered call can create income but limits upside.", [
        "Own at least 100 shares, then sell a call option against those shares.",
        "The premium provides income and a small cushion if price falls.",
        "If price rises above the strike, shares may be called away.",
        "Best understood as an exit plan plus income, not free money.",
        "Avoid selling calls on shares you would be upset to sell.",
    ], "Options"),
    ("cards", "Options Guardrails", "For a beginner, protection comes from limits.", [
        ("Avoid naked calls", "Loss can be theoretically unlimited.", RED),
        ("Avoid leverage first", "Small premiums can hide large exposure.", GOLD),
        ("Know the date", "Options decay and expire.", BLUE),
        ("Know assignment", "Sellers can be obligated to buy or sell.", TEAL),
        ("Paper trade", "Practice the mechanics before real money.", GREEN),
        ("Read disclosures", "Options are not approved for every investor.", MUTED),
    ], "Options"),
    ("section", "Part 5: Futures and Global Turbulence", "Futures are advanced tools for hedging and speculation in fast-moving markets.", "Futures", TEAL),
    ("simple", "What Is a Futures Contract?", "A futures contract is an agreement to buy or sell something at a future date.", [
        "Underlying markets can include stock indexes, oil, gold, currencies, interest rates, and agricultural products.",
        "Futures are standardized and trade on exchanges.",
        "They use margin, so a small amount of capital controls a larger notional value.",
        "Most contracts are closed before delivery or cash settled, but contract details matter.",
        "Leverage can create losses larger than the initial deposit.",
    ], "Futures"),
    ("simple", "Why Futures React to Geopolitics", "They connect global risk to tradable prices quickly.", [
        "Oil futures may react to supply disruptions, wars, shipping routes, and sanctions.",
        "Gold may react to inflation fears, currency stress, and safety-seeking flows.",
        "Index futures can move overnight when stock markets are closed.",
        "Currency and rate futures react to central banks, inflation, and political uncertainty.",
        "Fast reaction is useful for institutions, but dangerous for underprepared individuals.",
    ], "Futures"),
    ("cards", "Futures Risk Controls", "These belong before any trade ticket.", [
        ("Contract size", "Know the dollar value per point or tick.", GREEN),
        ("Margin", "Understand initial and maintenance margin.", BLUE),
        ("Stops", "Plan exits, but know gaps can skip stop prices.", RED),
        ("Calendar", "Know expiration, roll dates, and major reports.", GOLD),
        ("Liquidity", "Trade only active contracts with tight spreads.", TEAL),
        ("Simulation", "Use paper trading before risking real funds.", MUTED),
    ], "Futures"),
    ("simple", "Hedging vs. Speculating", "The intent changes the risk conversation.", [
        "A hedge reduces a risk you already have, such as a portfolio exposed to a market decline.",
        "A speculation creates risk in search of profit.",
        "Hedging has a cost and may reduce gains if the feared event does not happen.",
        "For families, simpler hedges such as diversification and cash reserves often come first.",
        "Futures should be introduced as advanced education, not a shortcut.",
    ], "Futures"),
    ("section", "Part 6: Practice and Discussion", "Learning sticks when she has to explain, calculate, and journal decisions.", "Practice", GREEN),
    ("simple", "Practice Exercise 1: Build a Watchlist", "Pick five companies she knows and research them.", [
        "Write what each company sells and how it earns money.",
        "Find three-year revenue trend, profit trend, debt, and free cash flow if available.",
        "Identify one competitive advantage and two major risks.",
        "Compare valuation against growth and quality.",
        "Decide: research more, avoid, or buy only as a tiny learning position.",
    ], "Practice"),
    ("simple", "Practice Exercise 2: Paper Swing Trade", "No real money. The goal is process.", [
        "Choose one liquid stock or ETF with a clear trend.",
        "Mark entry, stop, target, and position size using 1% max account risk.",
        "Take screenshots before and after the trade.",
        "Write what would invalidate the trade before entering.",
        "Review whether rules were followed, regardless of profit or loss.",
    ], "Practice"),
    ("simple", "Practice Exercise 3: Options Scenario", "Use simple payoff thinking.", [
        "Assume 100 shares of a stock at $50.",
        "Compare no hedge, buying a $45 protective put, and selling a $55 covered call.",
        "For each, discuss what happens if the stock goes to $35, $50, or $65.",
        "Name the tradeoff: cost, protection, income, capped upside, or assignment risk.",
        "Do not place the trade until the mechanics are explainable from memory.",
    ], "Practice"),
    ("simple", "Practice Exercise 4: Geopolitical Shock Map", "Connect news to markets without predicting too confidently.", [
        "Pick one event: war risk, shipping disruption, election surprise, sanctions, or central bank decision.",
        "List markets that may react: oil, gold, index futures, currency, rates, and sector ETFs.",
        "Write the bullish and bearish argument for each.",
        "Identify what could make the first reaction wrong.",
        "Discuss whether a hedge is necessary, too expensive, or too complex.",
    ], "Practice"),
    ("cards", "Family Discussion Prompts", "These help make the lesson personal.", [
        ("Goals", "What would financial independence mean at 25, 35, and 55?", GREEN),
        ("Values", "What companies would you be proud or uncomfortable owning?", BLUE),
        ("Mistakes", "What would make you panic, chase, or ignore your rules?", RED),
        ("Habits", "How much could you invest monthly without stress?", GOLD),
        ("Learning", "What topic should we study next: taxes, ETFs, earnings, or options?", TEAL),
        ("Rules", "What must be true before real money is used?", MUTED),
    ], "Practice"),
    ("simple", "A Simple Graduation Standard", "She is ready for small real-money practice only when she can explain:", [
        "The difference between saving, investing, trading, hedging, and speculating.",
        "Why diversification protects against single-company mistakes.",
        "How to read basic financial statements and valuation ratios.",
        "How to size a trade from the stop-loss, not from excitement.",
        "How options and futures can protect or harm a portfolio.",
    ], "Practice"),
    ("simple", "Recommended First Path", "A conservative path for a young learner.", [
        "Core: learn budgeting and make a long-term diversified investing plan.",
        "Research: study individual stocks with written one-page theses.",
        "Practice: paper trade swing setups for at least 20 journaled trades.",
        "Options: learn protective puts and covered calls with payoff diagrams first.",
        "Futures: study contract specs and paper trade only after options basics are solid.",
    ], "Practice"),
    ("simple", "Sources and Further Learning", "Primary education sources used for this course.", [
        "Investor.gov: compound interest calculator, stocks basics, diversification, and building wealth over time.",
        "FINRA: investing basics, risk, and options basics.",
        "CFTC: futures market basics and retail futures risk warnings.",
        "Options Industry Council/OCC: covered call education and standardized options education.",
        "Company filings: SEC EDGAR annual reports and quarterly reports for fundamental research.",
    ], "Sources"),
]


def make_pdf():
    c = canvas.Canvas(str(PDF_PATH), pagesize=landscape(letter))
    for idx, slide in enumerate(SLIDES, start=1):
        kind = slide[0]
        if kind == "title":
            title_slide(c, idx)
        elif kind == "section":
            _, title, subtitle, section, accent = slide
            section_slide(c, idx, title, subtitle, section, accent)
        elif kind == "simple":
            _, title, subtitle, items, section, *rest = slide
            simple_slide(c, idx, title, subtitle, items, section, rest[0] if rest else None)
        elif kind == "cards":
            _, title, subtitle, cards, section = slide
            cards_slide(c, idx, title, subtitle, cards, section)
        c.showPage()
    c.save()


def make_notes():
    notes = f"""# Stock Market Investing and Trading Course - Facilitator Notes

Generated deck: `{PDF_PATH.name}`

Audience: a 17-year-old beginner, taught with a parent or guardian.

Important framing:

- This course is educational and is not personal financial advice.
- A minor usually needs parent or guardian involvement for real investing accounts.
- The course intentionally puts long-term investing before trading, options, and futures.
- Options and futures are introduced as risk-management concepts first, not as shortcuts to quick money.

Suggested pacing:

- Session 1: Slides 1-8, money foundations and risk.
- Session 2: Slides 9-15, long-term stock investing and fundamental analysis.
- Session 3: Slides 16-22, swing trading and technical analysis.
- Session 4: Slides 23-27, options basics, protective puts, and covered calls.
- Session 5: Slides 28-32, futures and global market turbulence.
- Session 6: Slides 33-40, exercises, discussion, readiness standards, and sources.

Primary sources used:

- Investor.gov Compound Interest Calculator: https://www.investor.gov/tools/calculators/compound-interest-calculator
- Investor.gov Stocks FAQs: https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks
- Investor.gov Asset Allocation and Diversification: https://www.investor.gov/introduction-investing/getting-started/assessing-your-risk-tolerance
- Investor.gov Build Wealth Over Time: https://www.investor.gov/introduction-investing/investing-basics/building-wealth-over-time
- FINRA Risk: https://www.finra.org/investors/investing/investing-basics/risk
- FINRA Options Basics: https://www.finra.org/investors/insights/options-z-basics-greeks
- CFTC Futures Market Basics: https://www.cftc.gov/LearnAndProtect/EducationCenter/FuturesMarketBasics/index2.htm
- OCC Covered Calls: https://www.theocc.com/newsroom/insights/2018/08-15-get-the-facts-about-covered-calls
- SEC EDGAR for company filings: https://www.sec.gov/edgar/search/

Parent teaching tip:

Ask her to teach back each idea in her own words. If she can explain the risk, the tradeoff, and what would make her wrong, she is learning the right skill.
"""
    NOTES_PATH.write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    make_pdf()
    make_notes()
    print(f"Wrote {PDF_PATH}")
    print(f"Wrote {NOTES_PATH}")

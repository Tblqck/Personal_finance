

# finance_reports.py
import os
import json
import random
from datetime import timedelta, datetime
import requests
from get_display_name import get_display_name  # ✅ your helper
from exchange_rates import get_cached_exchange_rates
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Optional visualization helper
try:
    import seaborn as sns
except Exception:
    sns = None

# ============= Load Exchange Rates =============
# Make sure you have exchange_rates.py with get_cached_exchange_rates()
# This will fallback to NGN-only if the module is missing or returns falsy.
# ============= Load Exchange Rates =============
# Load live rates from exchange_rates.py or fallback to NGN-only.
try:
    from exchange_rates import get_cached_exchange_rates  # user-provided module
    RATES = get_cached_exchange_rates()
    if not RATES or not isinstance(RATES, dict):
        RATES = {"NGN": 1.0}
except Exception as e:
    print("⚠️ Using fallback exchange rates (NGN only). Error:", e)
    RATES = {"NGN": 1.0}


# ============= Convert to Naira =============
def convert_to_naira(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely converts all currency amounts to Naira (NGN) using live exchange rates.
    - Pulls rates from exchange_rates.json (via get_cached_exchange_rates()).
    - Handles symbols (₦, $, €, £, etc.).
    - Ensures numeric consistency (float64).
    """

    import numpy as np

    # --- Ensure valid columns ---
    if "currency" not in df.columns or "amount" not in df.columns:
        raise ValueError("DataFrame must contain 'currency' and 'amount' columns.")

    # --- Normalize currency symbols ---
    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace({"₦": "NGN", "$": "USD", "€": "EUR", "£": "GBP"})
    )

    # --- Replace unknown currencies with NGN ---
    df.loc[~df["currency"].isin(RATES.keys()), "currency"] = "NGN"

    # --- Convert to float ---
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").astype(float)

    # --- Apply conversion using dynamic rates ---
    df["amount"] = df.apply(
        lambda x: x["amount"] * RATES.get(x["currency"], 1.0), axis=1
    )

    # --- Standardize output ---
    df["currency"] = "NGN"
    df["amount"] = df["amount"].astype(np.float64)

    return df



# ============= Utility =============
def ensure_timestamps(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    """Ensure timestamp column is datetime and drop invalid timestamps."""
    if ts_col not in df.columns:
        raise ValueError(f"DataFrame must contain a '{ts_col}' column.")
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[ts_col]):
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce", utc=False)
    if df[ts_col].isna().any():
        df = df.dropna(subset=[ts_col])
    return df

def filter_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Filter dataframe by supported timeframes."""
    if df.empty:
        return df
    df = ensure_timestamps(df, "timestamp")
    now = df["timestamp"].max()

    if period == "last_hour":
        start = now - timedelta(hours=1)
        end = now
    elif period == "last_2_hours":
        start = now - timedelta(hours=2)
        end = now
    elif period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "yesterday":
        start = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1))
        end = start + timedelta(days=1)
    elif period == "last_2_days":
        start = now - timedelta(days=2)
        end = now
    elif period == "last_week":
        start = now - timedelta(days=7)
        end = now
    elif period == "last_month":
        start = now - timedelta(days=30)
        end = now
    elif period == "last_3_months":
        start = now - timedelta(days=90)
        end = now
    elif period == "last_5_months":
        start = now - timedelta(days=150)
        end = now
    elif period == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:
        # "all" or unknown returns the whole df
        return df
    return df[df["timestamp"].between(start, end)]

# ============= Praise Phrases =============
PRAISES = [
    "Nice one! Tracking this will help you save more 🎯",
    "Great job keeping track of your finances 👏",
    "You’re doing amazing staying on top of your budget 💪",
    "Excellent! Every bit of awareness counts 🌟",
    "That’s smart — financial clarity builds discipline 💰",
]

# ============= Plot Styling Helper =============
def setup_plot_style():
    try:
        if sns:
            plt.style.use("seaborn-v0_8-darkgrid")
        else:
            plt.style.use("ggplot")
    except Exception:
        plt.style.use("default")
    plt.rcParams.update(
        {
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.autolayout": True,
        }
    )

# ============= Core Analyses =============

# ✅ CATEGORY EXPENSE FUNCTION (as provided, slightly hardened)
def category_expense_summary(df: pd.DataFrame, user_id, category=None, period="all"):
    """
    Generates a category expense summary report.
    If 'category' is None or 'all', analyzes all expense categories combined.
    """
    required_cols = {"user_id", "type", "amount", "timestamp", "category"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise ValueError(f"DataFrame missing columns: {missing}")

    # --- Filter for user and expense type ---
    user_df = df[(df["user_id"] == str(user_id)) & (df["type"].str.lower() == "expense")].copy()
    if period != "all":
        user_df = filter_period(user_df, period)

    user_df["category"] = user_df["category"].fillna("").astype(str)

    # --- Handle category logic ---
    if not category or str(category).strip().lower() in ["", "all", "none"]:
        cat_df = user_df.copy()
        category_label = "All Categories"
    else:
        cat_df = user_df[user_df["category"].str.lower() == str(category).lower()].copy()
        category_label = str(category).capitalize()

    if cat_df.empty:
        return {"summary": f"No expenses found for {category_label} ({period}).", "pdf": None}

    cat_df = ensure_timestamps(cat_df, "timestamp").sort_values("timestamp")
    cat_df["weekday"] = cat_df["timestamp"].dt.day_name()

    daily = cat_df.groupby(cat_df["timestamp"].dt.date)["amount"].sum()
    by_weekday = cat_df.groupby("weekday")["amount"].sum().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).fillna(0)

    total_expense = float(daily.sum())
    pdf_path = f"user_{user_id}_{category_label.replace(' ', '_').lower()}_expense.pdf"

    setup_plot_style()
    with PdfPages(pdf_path) as pdf:
        # Page 1: Explanation
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.axis("off")
        text = (
            f" {category_label.upper()} EXPENSE ANALYSIS — {period.upper()}\n\n"
            f"This report summarizes how much you spent on {category_label.lower()} "
            f"during the selected period, and explains the insights from the following charts.\n\n"
            
            f"1. Daily Spending Pattern (Top-Left)\n"
            f"Each bar represents how much you spent per day. Taller bars show days of heavy spending.\n"
            f"If you see sharp spikes, it means your expenses were concentrated on specific days "
            f"(for example, rent or large purchases).\n\n"
            
            f"2. Spending Trend Over Time (Top-Right)\n"
            f"This line chart connects your daily expenses to show how your spending evolved. "
            f"A smooth upward slope indicates consistent spending, while peaks suggest bursts of activity.\n\n"
            
            f"3. Cumulative Spending Growth (Bottom-Left)\n"
            f"This area chart shows how your spending adds up over time. The steeper the curve, "
            f"the faster you’re spending money. A flatter section means slower spending or savings.\n\n"
            
            f"4. Weekday Spending Habits (Bottom-Right)\n"
            f"This chart compares how much you typically spend on each day of the week. "
            f"It helps identify patterns — for instance, if weekends cost you more, "
            f"you might want to plan for that in advance.\n\n"
            
            f"Total Spent: ₦{total_expense:,.2f}\n"
            f"Category: {category_label}\n"
            f"Period: {period.capitalize()}\n\n"
            
            f"Overall, this report helps you see not just how much you spent, "
            f"""but 'when' and 'how consistently'  turning your transactions into actionable insight."""
        )
        ax.text(0.02, 0.98, text, va="top", ha="left", fontsize=11, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: Dashboard 2x2
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.suptitle(f"User {user_id} - {category_label} Expense Dashboard ({period})", fontsize=15, fontweight="bold")

        axes[0, 0].bar(daily.index, daily.values)
        axes[0, 0].set_title("Bar Chart — Daily Spending")
        axes[0, 0].set_ylabel("Amount (₦)")

        axes[0, 1].plot(daily.index, daily.values, marker="o", lw=2)
        axes[0, 1].set_title("Line Chart — Spending Trend")
        axes[0, 1].set_ylabel("Amount (₦)")

        axes[1, 0].fill_between(daily.index, daily.values.cumsum(), alpha=0.7)
        axes[1, 0].set_title("Area Chart — Cumulative Spending")
        axes[1, 0].set_ylabel("Cumulative (₦)")

        if sns:
            sns.barplot(x=by_weekday.index, y=by_weekday.values, ax=axes[1, 1])
        else:
            axes[1, 1].bar(by_weekday.index, by_weekday.values)
        axes[1, 1].set_title("Bar Chart — Weekday Spending Pattern")
        axes[1, 1].set_ylabel("Amount (₦)")
        axes[1, 1].tick_params(axis="x", rotation=30)

        for ax in axes.flat:
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.tick_params(axis="x", rotation=45)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        pdf.savefig(fig)
        plt.close(fig)

        # Page 3: Daily Bar
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(daily.index, daily.values)
        ax.set_title("Daily Spending — Detailed Breakdown")
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 4: Line Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(daily.index, daily.values, marker="o", lw=2)
        ax.set_title("Spending Trend — Visualizing Change Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 5: Area Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.fill_between(daily.index, daily.values.cumsum(), alpha=0.6)
        ax.set_title("Cumulative Spending Growth — Long-Term Progress")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 6: Weekday Spending
        fig, ax = plt.subplots(figsize=(10, 6))
        if sns:
            sns.barplot(x=by_weekday.index, y=by_weekday.values, ax=ax)
        else:
            ax.bar(by_weekday.index, by_weekday.values)
        ax.set_title("Weekday Spending Pattern — When You Spend Most")
        ax.set_xlabel("Day of the Week")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

    return {
        "summary": f"User {user_id} spent ₦{total_expense:,.2f} on {category_label} ({period}).",
        "pdf": pdf_path
    }

# ============= Income Summaries =============
def income_trend_summary(df: pd.DataFrame, user_id, period="all", category=None):
    """
    Generate a comprehensive income report that mirrors the visual depth and structure
    of the category_expense_summary() function — including multi-page charts.
    """
    required_cols = {"user_id", "type", "amount", "timestamp"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise ValueError(f"DataFrame missing columns: {missing}")

    # --- Filter user & income records ---
    user_df = df[(df["user_id"] == str(user_id)) & (df["type"].str.lower() == "income")].copy()
    if user_df.empty:
        return {"summary": f"No income data found for user {user_id}.", "pdf": None}

    # --- Apply category filtering ---
    if "category" in user_df.columns and category and category.lower() != "all":
        user_df = user_df[user_df["category"].str.lower() == category.lower()]
        category_label = str(category).capitalize()
    else:
        category_label = "All Categories"

    # --- Apply time filtering ---
    if period != "all":
        user_df = filter_period(user_df, period)

    if user_df.empty:
        return {"summary": f"No income records found for {category_label} ({period}).", "pdf": None}

    # --- Prepare data ---
    user_df = ensure_timestamps(user_df, "timestamp").sort_values("timestamp")
    user_df["weekday"] = user_df["timestamp"].dt.day_name()

    daily = user_df.groupby(user_df["timestamp"].dt.date)["amount"].sum()
    by_weekday = user_df.groupby("weekday")["amount"].sum().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).fillna(0)

    total_income = float(daily.sum())
    pdf_path = f"user_{user_id}_{category_label.replace(' ', '_').lower()}_income.pdf"

    setup_plot_style()

    with PdfPages(pdf_path) as pdf:
        # === Page 1: Summary Overview ===
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.axis("off")
        
        text = (
            f"{category_label.upper()} INCOME REPORT ({period.upper()})\n\n"
            f"This document gives an easy-to-understand view of how your income behaved over time.\n"
            f"It uses visual charts to highlight both short-term earnings and long-term growth patterns.\n\n"
            f"TOTAL EARNED: ₦{total_income:,.2f}\n\n"
            "Here’s what each section of this report means:\n\n"
            "Page 2 – Income Dashboard (4-Chart Summary):\n"
            " • Top-Left: A bar chart of how much you earned on each day.\n"
            " • Top-Right: A line chart showing the direction of your income — when it rises or drops.\n"
            " • Bottom-Left: An area chart adding up all daily earnings, so you can see how your total grows over time.\n"
            " • Bottom-Right: A weekday pattern chart showing which days you earn the most or least.\n\n"
            "Page 3 – Daily Earnings Breakdown:\n"
            " This shows the exact daily values as bars, helping you spot days with unusually high or low income.\n\n"
            "Page 4 – Trend Analysis:\n"
            " This line chart connects your income over time, making it easy to see if earnings are increasing or slowing down.\n\n"
            "Page 5 – Cumulative Growth:\n"
            " This page adds each day’s income to the next — showing your financial progress building up like savings in a bank.\n\n"
            "Page 6 – Weekday Pattern:\n"
            " This compares your average income across days of the week. For example, if Fridays consistently pay higher, "
            "you’ll see taller bars on that day.\n\n"
            "The goal of this report is to help you and anyone reviewing it — even without financial training — "
            "see not just 'how much you earned', but 'how and when' you earn it."
        )

        ax.text(0.02, 0.98, text, va="top", ha="left", fontsize=11, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 2: 2x2 Dashboard ===
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.suptitle(
            f"User {user_id} - {category_label} Income Dashboard ({period})",
            fontsize=15,
            fontweight="bold",
        )

        axes[0, 0].bar(daily.index, daily.values, color="green")
        axes[0, 0].set_title("Bar Chart — Daily Earnings")
        axes[0, 0].set_ylabel("Amount (₦)")

        axes[0, 1].plot(daily.index, daily.values, marker="o", lw=2, color="blue")
        axes[0, 1].set_title("Line Chart — Income Trend")
        axes[0, 1].set_ylabel("Amount (₦)")

        axes[1, 0].fill_between(daily.index, daily.values.cumsum(), alpha=0.6, color="orange")
        axes[1, 0].set_title("Area Chart — Cumulative Income Growth")
        axes[1, 0].set_ylabel("Cumulative (₦)")

        if sns:
            sns.barplot(x=by_weekday.index, y=by_weekday.values, ax=axes[1, 1], color="purple")
        else:
            axes[1, 1].bar(by_weekday.index, by_weekday.values, color="purple")
        axes[1, 1].set_title("Bar Chart — Weekday Income Pattern")
        axes[1, 1].tick_params(axis="x", rotation=30)

        for ax in axes.flat:
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.tick_params(axis="x", rotation=45)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 3: Daily Income Bar ===
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(daily.index, daily.values, color="green")
        ax.set_title("Daily Earnings — Detailed Breakdown")
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 4: Income Trend ===
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(daily.index, daily.values, marker="o", lw=2, color="blue")
        ax.set_title("Income Trend — Visualizing Change Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 5: Cumulative Growth ===
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.fill_between(daily.index, daily.values.cumsum(), alpha=0.6, color="orange")
        ax.set_title("Cumulative Income Growth — Long-Term Progress")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Amount (₦)")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 6: Weekday Pattern ===
        fig, ax = plt.subplots(figsize=(10, 6))
        if sns:
            sns.barplot(x=by_weekday.index, y=by_weekday.values, ax=ax, color="purple")
        else:
            ax.bar(by_weekday.index, by_weekday.values, color="purple")
        ax.set_title("Weekday Income Pattern — When You Earn Most")
        ax.set_xlabel("Day of the Week")
        ax.set_ylabel("Amount (₦)")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        pdf.savefig(fig)
        plt.close(fig)

    return {
        "summary": f"User {user_id} earned ₦{total_income:,.2f} from {category_label} ({period}).",
        "pdf": pdf_path,
    }

# ============= OVERALL SUMMARY =============
def income_expense_correlation_summary(df: pd.DataFrame, user_id, period="all", income_category=None, expense_category=None):
    """
    Generate a comparative report showing how much remains when expenses are removed from income,
    optionally comparing specific income and expense categories.
    """
    required_cols = {"user_id", "type", "amount", "timestamp"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise ValueError(f"DataFrame missing columns: {missing}")

    # --- Filter user data ---
    user_df = df[df["user_id"] == str(user_id)].copy()
    user_df = ensure_timestamps(user_df, "timestamp")

    # --- Period filtering ---
    if period != "all":
        user_df = filter_period(user_df, period)

    if user_df.empty:
        return {"summary": f"No records found for {period}.", "pdf": None}

    # --- Separate income and expense ---
    income_df = user_df[user_df["type"].str.lower() == "income"]
    expense_df = user_df[user_df["type"].str.lower() == "expense"]

    # --- Optional category filters ---
    if "category" in user_df.columns:
        if income_category and income_category.lower() != "all":
            income_df = income_df[income_df["category"].str.lower() == income_category.lower()]
        if expense_category and expense_category.lower() != "all":
            expense_df = expense_df[expense_df["category"].str.lower() == expense_category.lower()]
    else:
        income_category = income_category or "all"
        expense_category = expense_category or "all"

    # --- Calculate totals ---
    total_income = income_df["amount"].sum()
    total_expense = expense_df["amount"].sum()
    remaining = total_income - total_expense

    if total_income == 0 and total_expense == 0:
        return {"summary": "No valid income or expense data found.", "pdf": None}

    # --- Daily trend comparison ---
    income_trend = income_df.groupby(income_df["timestamp"].dt.date)["amount"].sum()
    expense_trend = expense_df.groupby(expense_df["timestamp"].dt.date)["amount"].sum()

    # Align for plotting
    trend_df = pd.DataFrame({
        "Income": income_trend,
        "Expense": expense_trend
    }).fillna(0)
    trend_df["Balance"] = trend_df["Income"].cumsum() - trend_df["Expense"].cumsum()

    # --- Category-level comparison (if available) ---
    if "category" in user_df.columns:
        income_by_cat = income_df.groupby("category")["amount"].sum()
        expense_by_cat = expense_df.groupby("category")["amount"].sum()
        combined_cats = pd.concat([income_by_cat, expense_by_cat], axis=1, keys=["Income", "Expense"]).fillna(0)
    else:
        combined_cats = pd.DataFrame(columns=["Income", "Expense"])

    # --- Generate PDF ---
    pdf_path = f"user_{user_id}_income_expense_correlation.pdf"
    with PdfPages(pdf_path) as pdf:
        # === Page 1: Summary ===
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.axis("off")
        text = (
            f"INCOME AND EXPENSE CORRELATION REPORT — USER {user_id}\n\n"
            f"PERIOD ANALYZED: {period.upper()}\n"
            f"INCOME CATEGORY: {income_category or 'ALL'}\n"
            f"EXPENSE CATEGORY: {expense_category or 'ALL'}\n\n"
            f"KEY FIGURES:\n"
            f"Total Income: ₦{total_income:,.2f}\n"
            f"Total Expense: ₦{total_expense:,.2f}\n"
            f"Net Balance: ₦{remaining:,.2f}\n\n"
            f"HOW TO READ THIS REPORT:\n"
            f"1. The first chart compares total income and total expenses side by side. "
            f"If the income bar is higher than the expense bar, it means the user operated at a surplus during this period.\n\n"
            f"2. The second chart tracks income and expenses day by day. "
            f"Peaks show days of major inflow or spending. The blue shaded line in that chart represents "
            f"the running balance — when it rises, income exceeded spending; when it falls, expenses dominated.\n\n"
            f"3. The third chart (if available) breaks both income and expenses into categories such as rent, food, and salary. "
            f"This helps reveal which areas drive most income or spending. Large red bars signal costly categories to watch.\n\n"
            f"4. The last chart shows how the overall balance evolved over time. "
            f"A steady upward line indicates consistent savings, while frequent drops point to irregular or high spending patterns.\n\n"
            f"This report is designed to make financial performance easy to interpret even for readers without accounting or data training. "
            f"It explains whether spending habits align with income levels and highlights when financial pressure increased or decreased."
        )

        ax.text(0.02, 0.98, text, va="top", ha="left", fontsize=11, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 2: Income vs Expense Bar ===
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(["Income", "Expense"], [total_income, total_expense], color=["green", "red"])
        ax.set_title("Total Income vs Expense")
        for i, val in enumerate([total_income, total_expense]):
            ax.text(i, val, f"₦{val:,.0f}", ha="center", va="bottom", fontweight="bold")
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 3: Trend Comparison ===
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(trend_df.index, trend_df["Income"], marker="o", label="Income", color="green")
        ax.plot(trend_df.index, trend_df["Expense"], marker="o", label="Expense", color="red")
        ax.fill_between(trend_df.index, trend_df["Balance"], alpha=0.3, label="Balance", color="blue")
        ax.set_title("Daily Income vs Expense Trend")
        ax.set_xlabel("Date")
        ax.set_ylabel("₦")
        ax.tick_params(axis="x", rotation=45)
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        pdf.savefig(fig)
        plt.close(fig)

        # === Page 4: Category Comparison ===
        if not combined_cats.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            combined_cats.plot(kind="bar", ax=ax)
            ax.set_title("Income vs Expense by Category")
            ax.set_ylabel("₦")
            ax.tick_params(axis="x", rotation=45)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No category data available", ha="center", va="center", fontsize=12)
            ax.axis("off")
            pdf.savefig(fig)
            plt.close(fig)

        # === Page 5: Balance Progression ===
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(trend_df.index, trend_df["Balance"], color="blue", linewidth=2)
        ax.fill_between(trend_df.index, trend_df["Balance"], alpha=0.3)
        ax.set_title("Cumulative Balance Progression (Income - Expense)")
        ax.set_xlabel("Date")
        ax.set_ylabel("₦ Balance")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.5)
        pdf.savefig(fig)
        plt.close(fig)

    # === Summary text ===
    sign = "profit" if remaining > 0 else "loss"
    return {
        "summary": f"User {user_id} had a total income of ₦{total_income:,.2f}, "
                   f"spent ₦{total_expense:,.2f}, leaving ₦{remaining:,.2f} ({sign}) "
                   f"during {period}.",
        "pdf": pdf_path,
    }



# ============= AI Layer =============


def ai_interface(user_message: str, user_id):
    """
    AI interface that interprets user messages and calls the right financial analysis function.
    Now includes smarter correlation detection (e.g., 'compare my salary and rent this year' or
    'how much I made and spent last 2 months').
    """

    # === STEP 1: Load and prepare data ===
    try:
        with open("budget.json", "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data.get("transactions", []))
    except Exception as e:
        return f"⚠️ Failed to load budget.json — {e}"

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    msg = user_message.lower().strip()
    praise = random.choice(PRAISES)
    display_name = get_display_name(str(user_id))

    # === STEP 2: Normalize and convert to Naira ===
    df = convert_to_naira(df)
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0).astype(float)

    # === STEP 3: Detect time period from message ===
    period_keywords = {
        "last hour": "last_hour", "past hour": "last_hour", "previous hour": "last_hour",
        "last 2 hours": "last_2_hours", "past 2 hours": "last_2_hours", "two hours": "last_2_hours",
        "today": "today", "yesterday": "yesterday",
        "this week": "this_week", "last week": "last_week",
        "this month": "this_month", "last month": "last_month",
        "this year": "this_year", "last year": "last_year",
        "last 2 months": "last_2_months", "last three months": "last_3_months",
        "half year": "last_6_months", "six months": "last_6_months",
        "last 2 years": "last_2_years"
    }

    period = "all"
    found_period = False
    for key, val in period_keywords.items():
        if key in msg:
            period = val
            found_period = True
            break

    # === STEP 4: Category mapping (expense & income) ===
    expense_map = {
        "food": ["food", "dining", "meal", "restaurant"],
        "transport": ["transport", "bus", "taxi", "uber", "bike"],
        "rent": ["rent", "housing", "apartment", "flat"],
        "entertainment": ["entertainment", "movie", "netflix", "game"],
        "shopping": ["shopping", "clothes", "groceries", "market"],
        "gas": ["gas", "fuel", "petrol"],
        "electricity": ["electricity", "light", "power", "nepa"],
        "bills": ["bills", "subscriptions", "fees"],
    }

    income_map = {
        "salary": ["salary", "pay", "wages", "income"],
        "bonus": ["bonus", "reward"],
        "freelance": ["freelance", "gig"],
        "investment": ["investment", "dividend", "interest"],
        "sales": ["sales", "earning", "revenue"],
    }

    # === STEP 5: Full message scan ===
    found_income_cat = None
    found_expense_cat = None
    has_income_word = any(
        w in msg for w in ["income", "salary", "bonus", "reward", "freelance", "made", "investment", "earn", "earned"]
    )
    has_expense_word = any(
        w in msg for w in ["spent", "spend", "expense", "expenditure", "cost", "paid", "used", "loss"]
    )

    # detect specific categories
    for inc, words in income_map.items():
        if any(w in msg for w in words):
            found_income_cat = inc
            break
    for exp, words in expense_map.items():
        if any(w in msg for w in words):
            found_expense_cat = exp
            break

    # === STEP 6: Detect correlation/comparison phrases ===
    comparison_triggers = ["compare", "difference", "vs", "versus", "both", "and", "between", "against", "left after"]

    has_comparison = any(word in msg for word in comparison_triggers)

    # === STEP 7: Intent Routing ===
    # 💠 CORRELATIVE INTENT: if both income + expense words exist OR comparison word present
    if (has_income_word and has_expense_word) or has_comparison:
        print(f"[AI] Correlative intent detected: income={found_income_cat}, expense={found_expense_cat}, period={period}")
        result = income_expense_correlation_summary(
            df, user_id, period=period,
            income_category=found_income_cat,
            expense_category=found_expense_cat
        )

    # 💰 Pure INCOME analysis
    elif has_income_word:
        print(f"[AI] Income intent: {found_income_cat or 'general'}, period={period}")
        result = income_trend_summary(df, user_id, period=period)

    # 💸 EXPENSE analysis
    elif has_expense_word:
        found_cat = found_expense_cat or "all"
        print(f"[AI] Expense intent: {found_cat}, period={period}")
        result = category_expense_summary(df, user_id, found_cat, period)

    # 🧾 Balance or profit/loss type query
    elif any(k in msg for k in ["balance after", "how much left", "income minus expense", "profit", "loss"]):
        print(f"[AI] Balance check intent, period={period}")
        result = income_expense_correlation_summary(df, user_id, period=period)

    # ❓ Unclear request
    else:
        result = {"summary": "❓ Sorry, I didn’t understand your request.", "pdf": None}

    # === STEP 8: Timeframe clarification ===
    if not found_period and any(word in msg for word in ["last", "yesterday", "today", "month", "week", "day", "hour", "year"]):
        result["summary"] = (
            "⏳ I couldn’t recognize that exact timeframe. Try something like: "
            "'last 2 months', 'yesterday', or 'this year'.\n"
            + result.get("summary", "")
        )

    # === STEP 9: Personalize output ===
    if isinstance(result.get("summary"), str):
        result["summary"] = result["summary"].replace(f"User {user_id}", display_name)

    # === STEP 10: Add praise ===
    result["summary"] = f"{result['summary']}\n\n{praise}"

    return result

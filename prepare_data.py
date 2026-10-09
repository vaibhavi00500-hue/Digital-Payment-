"""
prepare_data.py  -  Step 2 of the project: Data Cleaning & Preparation
Run once:  python prepare_data.py
Reads  : data/RBI_Digital_Payments_Capstone_Cleaned.xlsx
Writes : data/clean/*.csv  +  data/clean/cleaning_log.csv
"""
import numpy as np
import pandas as pd

RAW = "data/RBI_Digital_Payments_Capstone_Cleaned.xlsx"
OUT = "data/clean/"
log = []  # (sheet, issue found, action taken, rows affected)


def note(sheet, issue, action, n):
    log.append({"Sheet": sheet, "Issue found": issue, "Action taken": action, "Rows/months affected": int(n)})


def fix_swapped_month(df, sheet):
    """Some 'month' values are stored as YYYY-DD-MM (e.g. 2022-01-03 really = 1 March 2022).
    Real values are always the 1st of a month, so any date whose day != 1 is swapped back."""
    d = pd.to_datetime(df["month"])
    swapped = d.dt.day != 1
    fixed = pd.to_datetime(dict(year=d.dt.year, month=d.dt.day, day=1))
    df["month"] = d.where(~swapped, fixed)
    note(sheet, "Month stored with day/month swapped (day != 1)", "Swapped back to 1st-of-month date", swapped.sum())
    return df


def drop_dupes(df, keys, sheet):
    before = len(df)
    df = df.drop_duplicates(keys, keep="first")
    note(sheet, f"Same {keys} appears more than once (mostly the swapped-date copies)",
         "Kept first row, dropped the rest", before - len(df))
    return df


# 1) Daily payments --------------------------------------------------------
daily = pd.read_excel(RAW, "01_Daily_Payments")
daily["date"] = pd.to_datetime(daily["date"])
daily = daily.sort_values("date").drop(columns="id")
gaps = (daily["date"].diff().dt.days > 1).sum()
note("01_Daily_Payments", "Missing calendar days in the series", "Left as is (not interpolated); charts skip them", gaps)
note("01_Daily_Payments", "Blank RTGS/NACH/CTS on weekends & bank holidays (these systems are closed)",
     "Kept as NaN, NOT filled with 0 - blank means 'system closed', not 'zero payments'", daily["rtgs_vol"].isna().sum())
daily.to_csv(OUT + "daily_payments.csv", index=False)

# 2) Mobile banking --------------------------------------------------------
mob = pd.read_excel(RAW, "02_Mobile_Banking")
mob["month"] = pd.to_datetime(mob["month"])
mob = drop_dupes(mob, ["month", "bank_name"], "02_Mobile_Banking").drop(columns="id")
mob = mob.rename(columns={"no_of_active_costumers": "active_customers"})
# amounts jump x100 in a few months (unit change in the source). Detect walk-forward and rescale.
g = mob.groupby("month")[["no_of_transactions", "amt_of_transactions"]].sum()
ticket = (g["amt_of_transactions"] / g["no_of_transactions"]).replace(0, np.nan)
hist, bad = [], []
for m, v in ticket.items():
    if len(hist) >= 3 and v > 10 * np.median(hist[-6:]):
        bad.append(m)
        v = v / 100
    hist.append(v)
mob["amt_unit_fixed"] = mob["month"].isin(bad)
mob.loc[mob["amt_unit_fixed"], "amt_of_transactions"] /= 100
note("02_Mobile_Banking", "Amount per transaction jumps ~100x in some months (unit change): "
     + ", ".join(x.strftime("%b-%Y") for x in bad), "Divided those months' amounts by 100", len(bad))
mob.to_csv(OUT + "mobile_banking.csv", index=False)

# 3) Internet banking ------------------------------------------------------
ib = pd.read_excel(RAW, "03_Internet_Banking")
ib = fix_swapped_month(ib, "03_Internet_Banking")
ib = drop_dupes(ib, ["month", "bank_name"], "03_Internet_Banking").drop(columns="id")
ib.to_csv(OUT + "internet_banking.csv", index=False)

# 4) NEFT ------------------------------------------------------------------
neft = pd.read_excel(RAW, "04_NEFT")
neft = fix_swapped_month(neft, "04_NEFT")
neft = drop_dupes(neft, ["month", "bank_name"], "04_NEFT").drop(columns="id")
allm = pd.date_range(neft["month"].min(), neft["month"].max(), freq="MS")
miss = allm.difference(neft["month"].unique())
note("04_NEFT", "Months with no data at all: " + ", ".join(x.strftime("%b-%Y") for x in miss), "Left as gaps", len(miss))
neft.to_csv(OUT + "neft.csv", index=False)

# 5) Bank-wise ATM / POS / cards ------------------------------------------
atm = pd.read_excel(RAW, "05_Bankwise_ATM_POS_Card")
atm["date"] = pd.to_datetime(atm["date"])
atm = drop_dupes(atm, ["date", "bank_name"], "05_Bankwise_ATM_POS_Card").drop(columns="id")
atm.to_csv(OUT + "bankwise_cards.csv", index=False)

pd.DataFrame(log).to_csv(OUT + "cleaning_log.csv", index=False)
print(pd.DataFrame(log).to_string())
for n, d in [("daily", daily), ("mobile", mob), ("internet", ib), ("neft", neft), ("cards", atm)]:
    print(n, d.shape)

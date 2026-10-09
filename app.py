"""
FinTech Digital Payment Transaction Analytics  -  Streamlit dashboard
Data: RBI digital-payment statistics via India Data Portal (cleaned by prepare_data.py)
Run : streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Digital Payments Analytics", page_icon="💳", layout="wide")

# ----------------------------------------------------------------------------
# 1. LOAD DATA (cached so the app stays fast)
# ----------------------------------------------------------------------------
CLEAN = ""

# name shown on screen -> column prefix in the daily sheet
METHODS = {
    "UPI": "upi", "IMPS": "imps", "NEFT": "neft", "RTGS": "rtgs",
    "NACH Credit": "nach_credit", "NACH Debit": "nach_debit", "BBPS (bill pay)": "bbps",
    "NETC (FASTag)": "netc", "AePS": "aeps", "Cheque (CTS)": "cts", "ATM (NFS)": "nfs_through_atms",
}


@st.cache_data
def load():
    daily = pd.read_csv(CLEAN + "daily_payments.csv", parse_dates=["date"])
    mob = pd.read_csv(CLEAN + "mobile_banking.csv", parse_dates=["month"])
    ib = pd.read_csv(CLEAN + "internet_banking.csv", parse_dates=["month"])
    neft = pd.read_csv(CLEAN + "neft.csv", parse_dates=["month"])
    cards = pd.read_csv(CLEAN + "bankwise_cards.csv", parse_dates=["date"])
    log = pd.read_csv(CLEAN + "cleaning_log.csv")
    return daily, mob, ib, neft, cards, log


daily, mob, ib, neft, cards, clean_log = load()

# long format for the daily sheet: one row per date x method
rows = []
for name, c in METHODS.items():
    t = daily[["date", f"{c}_vol", f"{c}_val"]].dropna().copy()
    t.columns = ["date", "vol", "val"]          # vol = lakh transactions, val = Rs crore
    t["method"] = name
    rows.append(t)
long = pd.concat(rows)
# Rs per transaction: (crore / lakh) = 100 rupees
long["ticket"] = long["val"] / long["vol"] * 100
long["month"] = long["date"].dt.to_period("M").dt.to_timestamp()
long["weekday"] = long["date"].dt.day_name()

# ----------------------------------------------------------------------------
# 2. HEADER + SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.title("FinTech Digital Payment Transaction Analytics")
st.caption("Source: RBI payment statistics via India Data Portal  |  Volumes in lakh transactions, values in ₹ crore "
           "(daily sheet)  |  Aggregated system data, not individual customer records")

st.sidebar.header("Filters")
dmin, dmax = daily["date"].min().date(), daily["date"].max().date()
start, end = st.sidebar.date_input("Date range (daily data)", (dmin, dmax), min_value=dmin, max_value=dmax)
chosen = st.sidebar.multiselect("Payment methods", list(METHODS), default=["UPI", "IMPS", "NEFT", "RTGS"])
if not chosen:
    st.warning("Pick at least one payment method in the sidebar.")
    st.stop()

f = long[(long["date"].dt.date >= start) & (long["date"].dt.date <= end)]
fc = f[f["method"].isin(chosen)]
if f.empty:
    st.warning("No data in that date range.")
    st.stop()

# ----------------------------------------------------------------------------
# 3. KPIs (always visible at the top)
# ----------------------------------------------------------------------------
all_vol = f.groupby("method")["vol"].mean()   # average daily volume per method in the selected range
all_val = f.groupby("method")["val"].mean()
upi = f[f["method"] == "UPI"]
last_m = upi["month"].max()
upi_last = upi[upi["month"] == last_m]
yr_ago = upi[upi["month"] == last_m - pd.DateOffset(years=1)]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Avg daily UPI volume", f"{all_vol.get('UPI', np.nan)/100:,.1f} cr txns",
          help="Average per day over the selected range (1 crore = 100 lakh)")
k2.metric("UPI share of txn volume", f"{all_vol.get('UPI', 0)/all_vol.sum()*100:.0f}%")
k3.metric("UPI share of txn value", f"{all_val.get('UPI', 0)/all_val.sum()*100:.0f}%")
k4.metric("UPI avg ticket size", f"₹{upi['val'].sum()/upi['vol'].sum()*100:,.0f}")
if len(yr_ago):
    g = upi_last["vol"].mean() / yr_ago["vol"].mean() - 1
    k5.metric(f"UPI volume growth YoY ({last_m:%b-%y})", f"{g*100:+.0f}%")
else:
    k5.metric("UPI volume growth YoY", "n/a (range too short)")

tabs = st.tabs(["Overview", "Methods & Ticket Size", "Timing & Stress Signals",
                "Bank-wise View", "Insights & Actions", "Data Quality"])

# ----------------------------------------------------------------------------
# TAB 1  OVERVIEW  - "What is happening in the business?"
# ----------------------------------------------------------------------------
with tabs[0]:
    st.subheader("What is happening? Volume vs value are two different stories")
    c1, c2 = st.columns(2)
    mix = pd.DataFrame({"Share of volume (%)": all_vol / all_vol.sum() * 100,
                        "Share of value (%)": all_val / all_val.sum() * 100}).reset_index()
    mix = mix.melt("method", var_name="Measure", value_name="Share %")
    fig = px.bar(mix, x="method", y="Share %", color="Measure", barmode="group",
                 title="Share of total volume vs total value by method (selected range)",
                 labels={"method": "Payment method"})
    c1.plotly_chart(fig, width="stretch")
    c1.caption("UPI dominates the number of payments but carries a small share of the money; RTGS/NEFT are the "
               "opposite. Customer-service effort follows volume, risk exposure follows value.")

    monthly = fc.groupby(["month", "method"])["vol"].mean().reset_index()
    fig = px.area(monthly, x="month", y="vol", color="method",
                  title="Average daily volume by month (lakh txns)",
                  labels={"month": "Month", "vol": "Lakh transactions / day"})
    c2.plotly_chart(fig, width="stretch")
    c2.caption("Stacked, so the total height is combined volume of the methods chosen in the sidebar.")

# ----------------------------------------------------------------------------
# TAB 2  METHODS & TICKET SIZE
# ----------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Which methods are growing, and what are people paying with them?")
    c1, c2 = st.columns(2)
    scale = c1.radio("Volume axis", ["Linear", "Log"], horizontal=True)
    m2 = fc.groupby(["month", "method"])["vol"].mean().reset_index()
    fig = px.line(m2, x="month", y="vol", color="method", log_y=(scale == "Log"),
                  title="Monthly average daily volume (lakh txns)", labels={"month": "Month", "vol": "Lakh txns / day"})
    c1.plotly_chart(fig, width="stretch")

    t2 = fc.groupby(["month", "method"]).apply(lambda x: x["val"].sum() / x["vol"].sum() * 100,
                                               include_groups=False).reset_index(name="ticket")
    fig = px.line(t2, x="month", y="ticket", color="method", log_y=True,
                  title="Average ticket size (₹ per transaction, log scale)",
                  labels={"month": "Month", "ticket": "₹ per transaction"})
    c2.plotly_chart(fig, width="stretch")
    c2.caption("Log scale is used because ticket sizes range from a few hundred rupees to millions.")

    st.markdown("**Summary table for the selected range**")
    s = fc.groupby("method").agg(avg_daily_volume_lakh=("vol", "mean"), avg_daily_value_cr=("val", "mean"),
                                 total_vol=("vol", "sum"), total_val=("val", "sum")).reset_index()
    s["avg_ticket_Rs"] = s["total_val"] / s["total_vol"] * 100
    st.dataframe(s.drop(columns=["total_vol", "total_val"]).round(1).sort_values("avg_daily_volume_lakh", ascending=False),
                 hide_index=True, width="stretch")

    # card payments (only reported for part of the period)
    with st.expander("Card spending at POS vs e-commerce (reported only from the later part of the data)"):
        card_cols = {"Credit card POS": "credit_card_at_pos", "Credit card e-commerce": "credit_card_at_e_commerce",
                     "Debit card POS": "debit_card_at_pos", "Debit card e-commerce": "debit_card_at_e_commerce"}
        cr = []
        for n, c in card_cols.items():
            t = daily[["date", f"{c}_vol"]].dropna().rename(columns={f"{c}_vol": "vol"})
            t["month"] = t["date"].dt.to_period("M").dt.to_timestamp()
            t = t.groupby("month")["vol"].mean().reset_index()
            t["type"] = n
            cr.append(t)
        cr = pd.concat(cr)
        if cr.empty:
            st.info("No card data in this file.")
        else:
            st.plotly_chart(px.line(cr, x="month", y="vol", color="type",
                                    title="Card payments - average daily volume (lakh txns)",
                                    labels={"month": "Month", "vol": "Lakh txns / day"}), width="stretch")

# ----------------------------------------------------------------------------
# TAB 3  TIMING & STRESS SIGNALS
# ----------------------------------------------------------------------------
with tabs[2]:
    st.subheader("When do payments peak or dip? (capacity & customer-service planning)")
    st.info("This dataset has no 'failed transaction' field. Unusual dips and weekday gaps are used as **proxy "
            "operational signals** to investigate, not as proof of failures.")
    recent = st.checkbox("Use only the most recent 12 months for weekday pattern", value=True)
    w = fc[fc["date"] >= fc["date"].max() - pd.DateOffset(months=12)] if recent else fc
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    # Index: weekday average divided by the method's overall average (1.0 = normal day)
    wd = w.groupby(["method", "weekday"])["vol"].mean().unstack()[order]
    wd = wd.div(w.groupby("method")["vol"].mean(), axis=0)
    fig = px.imshow(wd.round(2), text_auto=True, aspect="auto", color_continuous_scale="RdYlGn",
                    title="Weekday volume index by method (1.00 = that method's average day)",
                    labels={"color": "Index"})
    st.plotly_chart(fig, width="stretch")
    st.caption("UPI is flat across the week (24x7). RTGS and NEFT collapse on weekends because the rails are closed "
               "on holidays/Sundays, so weekend payment activity is almost entirely UPI.")

    c1, c2 = st.columns(2)
    u = daily.dropna(subset=["upi_vol"]).copy()
    u["dom"] = u["date"].dt.day
    dm = u[u["date"] >= u["date"].max() - pd.DateOffset(years=2)].groupby("dom")["upi_vol"].mean()
    dm = (dm / dm.mean()).reset_index(name="index")
    c1.plotly_chart(px.bar(dm, x="dom", y="index", title="UPI volume index by day of month (last 2 years)",
                           labels={"dom": "Day of month", "index": "Index (1 = average)"}), width="stretch")
    c1.caption("Shows whether volume lifts at particular points in the month (the effect is mild).")

    z = c2.slider("Flag days where UPI volume changes by more than (%) vs previous day", 10, 40, 20)
    u = u.sort_values("date")
    u["chg"] = u["upi_vol"].pct_change() * 100
    u.loc[u["date"].diff().dt.days != 1, "chg"] = np.nan   # ignore changes across missing days
    flag = u[u["chg"].abs() > z]
    fig = px.line(u, x="date", y="chg", title="UPI day-on-day volume change (%)",
                  labels={"date": "Date", "chg": "% change vs previous day"})
    fig.add_scatter(x=flag["date"], y=flag["chg"], mode="markers", name="Flagged", marker=dict(color="red", size=7))
    c2.plotly_chart(fig, width="stretch")
    st.markdown(f"**{len(flag)} flagged day(s)** - check these against holidays / known outages:")
    fl = flag.assign(weekday=flag["date"].dt.day_name())[["date", "weekday", "upi_vol", "chg"]]
    fl.columns = ["Date", "Weekday", "UPI volume (lakh)", "% change"]
    fl["UPI volume (lakh)"] = fl["UPI volume (lakh)"].round(1)
    fl["% change"] = fl["% change"].round(1)
    st.dataframe(fl.sort_values("% change"), hide_index=True, width="stretch")

# ----------------------------------------------------------------------------
# TAB 4  BANK-WISE VIEW  (the closest thing to "location" in this data)
# ----------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Which banks carry the volume? Where is engagement weak?")
    st.info("The data has no city/state field. **Bank / bank-category** is used as the 'where' dimension.")
    channel = st.selectbox("Channel", ["Mobile banking", "Internet banking", "NEFT - debit side", "NEFT - credit side"])
    if channel == "Mobile banking":
        df, ncol, acol, ucol = mob, "no_of_transactions", "amt_of_transactions", "active_customers"
    elif channel == "Internet banking":
        df, ncol, acol, ucol = ib, "no_of_transactions", "amt_of_transactions", "active_users"
    elif channel == "NEFT - debit side":
        df, ncol, acol, ucol = neft, "no_of_debit_transactions", "amt_of_debit_transactions", None
    else:
        df, ncol, acol, ucol = neft, "no_of_credit_transactions", "amt_of_credit_transactions", None

    months = sorted(df["month"].unique())
    pick = st.select_slider("Month", options=months, value=months[-1], format_func=lambda x: pd.Timestamp(x).strftime("%b %Y"))
    topn = st.slider("Show top N banks", 5, 25, 10)
    cur = df[df["month"] == pick].sort_values(ncol, ascending=False)
    tot = cur[ncol].sum()

    a, b, c = st.columns(3)
    a.metric("Banks reporting", f"{len(cur):,}")
    b.metric("Top-5 share of transactions", f"{cur[ncol].head(5).sum()/tot*100:.0f}%")
    c.metric("Top-10 share of transactions", f"{cur[ncol].head(10).sum()/tot*100:.0f}%")

    c1, c2 = st.columns(2)
    top = cur.head(topn).iloc[::-1]
    c1.plotly_chart(px.bar(top, x=ncol, y="bank_name", orientation="h",
                           title=f"Top {topn} banks by transactions - {channel}",
                           labels={ncol: "Number of transactions", "bank_name": ""}), width="stretch")
    tr = df[df["bank_name"].isin(cur["bank_name"].head(5))].groupby(["month", "bank_name"])[ncol].sum().reset_index()
    c2.plotly_chart(px.line(tr, x="month", y=ncol, color="bank_name", title="Trend of the current top-5 banks",
                            labels={"month": "Month", ncol: "Transactions", "bank_name": "Bank"}), width="stretch")
    c2.caption("Long history is shown so you can see when each channel took off.")

    if ucol:
        st.markdown("#### Engagement: transactions per active user (customer-service opportunity)")
        e = cur[cur[ucol] > 0].copy()
        e["txn_per_user"] = e[ncol] / e[ucol]
        minu = st.slider("Only banks with at least this many active users", 0, 1_000_000, 100_000, step=50_000)
        e = e[e[ucol] >= minu]
        if len(e) > 1:
            fig = px.scatter(e, x=ucol, y=ncol, hover_name="bank_name", log_x=True, log_y=True,
                             color="txn_per_user", color_continuous_scale="Viridis",
                             title="Active users vs transactions (log-log). Below the cloud = users who rarely transact",
                             labels={ucol: "Active users", ncol: "Transactions", "txn_per_user": "Txns / user"})
            st.plotly_chart(fig, width="stretch")
            lo = e.nsmallest(5, "txn_per_user")[["bank_name", ucol, ncol, "txn_per_user"]]
            lo.columns = ["Bank", "Active users", "Transactions", "Txns per user"]
            st.markdown("**Lowest engagement (users who barely transact - candidates for activation campaigns):**")
            st.dataframe(lo.round(2), hide_index=True, width="stretch")
            st.caption("Caution: a few banks show very high ratios, probably because 'active user' is defined "
                       "differently by each bank. Compare banks with care and verify before acting.")
        else:
            st.write("No banks match this filter.")

    st.markdown("#### Cards & infrastructure by bank category (ATM / POS / UPI-QR file)")
    cdate = st.select_slider("Card data month", options=sorted(cards["date"].unique()),
                             value=cards["date"].max(), format_func=lambda x: pd.Timestamp(x).strftime("%b %Y"))
    cc = cards[cards["date"] == cdate].copy()
    cc["debit_card_digital_vol"] = cc["dc_pay_trns_at_pos_vol"] + cc["dc_pay_trns_online_vol"] + cc["dc_pay_trns_other_vol"]
    cc["atms"] = cc["atms_crms_onsite"].fillna(0) + cc["atms_crms_offsite"].fillna(0)
    cat = cc.groupby("bank_category").agg(debit_cards=("debit_cards", "sum"), credit_cards=("credit_cards", "sum"),
                                          pos_terminals=("pos", "sum"), upi_qr=("upi_qr", "sum"), atms=("atms", "sum"),
                                          dc_digital_vol=("debit_card_digital_vol", "sum"),
                                          dc_atm_cash_vol=("dc_cash_withdraw_atm_vol", "sum")).reset_index()
    cat["Digital share of debit-card txns %"] = cat["dc_digital_vol"] / (cat["dc_digital_vol"] + cat["dc_atm_cash_vol"]) * 100
    d1, d2 = st.columns(2)
    d1.plotly_chart(px.bar(cat, x="bank_category", y="Digital share of debit-card txns %",
                           title="Debit-card transactions that are digital (not ATM cash), by category",
                           labels={"bank_category": "Bank category"}), width="stretch")
    cm = cat.melt("bank_category", ["pos_terminals", "upi_qr", "atms"], var_name="Asset", value_name="Count")
    d2.plotly_chart(px.bar(cm, x="bank_category", y="Count", color="Asset", barmode="group", log_y=True,
                           title="Acceptance infrastructure by category (log scale)",
                           labels={"bank_category": "Bank category"}), width="stretch")
    st.caption("Public-sector banks hold the most debit cards and rely most on ATMs; private banks lead on POS and QR "
               "acceptance. Note that card counts and QR counts are reported differently by banks.")

# ----------------------------------------------------------------------------
# TAB 5  INSIGHTS & ACTIONS  (numbers are computed live from the data)
# ----------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Business insights (computed from the full dataset, not the sidebar filters)")
    first_m, last_m2 = long["month"].min(), long["month"].max()
    base = long[long["month"] == first_m].groupby("method")["vol"].mean()
    now = long[long["month"] == last_m2].groupby("method")["vol"].mean()
    basev = long[long["month"] == last_m2].groupby("method")["val"].mean()
    ups_then, ups_now = base["UPI"] / base.sum() * 100, now["UPI"] / now.sum() * 100
    tk = long[long["method"] == "UPI"].groupby("month").apply(lambda x: x["val"].sum() / x["vol"].sum() * 100, include_groups=False)
    yoy_cut = last_m2 - pd.DateOffset(years=1)
    imps = long[long["method"] == "IMPS"].groupby("month")["vol"].mean()
    upiv = long[long["method"] == "UPI"].groupby("month")["vol"].mean()
    wk = long[(long["date"] >= long["date"].max() - pd.DateOffset(months=12))]
    wkx = wk.groupby(["method", "weekday"])["vol"].mean().unstack()
    sun_neft = wkx.loc["NEFT", "Sunday"] / wkx.loc["NEFT"].mean()
    sun_upi = wkx.loc["UPI", "Sunday"] / wkx.loc["UPI"].mean()
    l_mob = mob[mob["month"] == mob["month"].max()].sort_values("no_of_transactions", ascending=False)
    top5 = l_mob["no_of_transactions"].head(5).sum() / l_mob["no_of_transactions"].sum() * 100
    m_tot = mob.groupby("month")["no_of_transactions"].sum()
    i_tot = ib.groupby("month")["no_of_transactions"].sum()

    st.markdown(f"""
1. **UPI is now the default rail.** Its share of payment volume rose from **{ups_then:.0f}%** ({first_m:%b %Y}) to **{ups_now:.0f}%** ({last_m2:%b %Y}), but it moves only **{basev['UPI']/basev.sum()*100:.0f}%** of the value (RTGS alone carries most of the rupees).
   *Why it matters:* support, fraud and uptime effort should be sized to UPI's volume, while treasury/risk controls should watch RTGS/NEFT values.
2. **UPI tickets keep shrinking.** Average UPI ticket fell from **₹{tk.iloc[0]:,.0f}** to **₹{tk.iloc[-1]:,.0f}**, i.e. growth is coming from many small everyday payments.
   *Why it matters:* if the money earned per payment is shrinking, handling and support cost per payment has to shrink too.
3. **UPI is cannibalising IMPS.** Year-on-year (latest month vs same month last year) UPI volume grew **{(upiv[last_m2]/upiv[yoy_cut]-1)*100:+.0f}%** while IMPS moved **{(imps[last_m2]/imps[yoy_cut]-1)*100:+.0f}%**.
   *Why it matters:* a product that only duplicates UPI is losing relevance; IMPS needs a clear niche (higher ticket, 24x7 account-to-account).
4. **Weekend gap in bank rails.** On Sundays NEFT runs at only **{sun_neft:.2f}x** of its average day while UPI stays at **{sun_upi:.2f}x**.
   *Why it matters:* weekend support demand is almost entirely UPI; staffing and monitoring should reflect that.
5. **Mobile banking is concentrated and still growing; internet banking is shrinking.** The top-5 banks handle **{top5:.0f}%** of mobile-banking transactions ({mob['month'].max():%b %Y}). Mobile volume is **{m_tot.iloc[-1]/m_tot.iloc[-13]*100-100:+.0f}%** YoY, internet banking is **{i_tot.iloc[-1]/i_tot.iloc[-13]*100-100:+.0f}%**.
   *Why it matters:* concentration means an outage at a few banks hits a large share of customers; the shift to mobile means the web channel needs less investment than the app.
6. **Very uneven engagement per active user** across banks (see Bank-wise tab). Banks with many registered users but few transactions per user are activation opportunities.
""")
    st.subheader("Recommendations")
    st.markdown("""
| # | Recommendation | Evidence it is based on |
|---|---|---|
| 1 | Size customer-support and monitoring teams to **UPI volume and weekend demand**, not to bank-rail volume | UPI is the large majority of payments (see Insight 1) and is flat across the week; NEFT/RTGS fall sharply on weekends |
| 2 | Add **automated, self-serve dispute and status tracking** for small-ticket UPI payments | Falling UPI ticket size means manual handling per payment becomes uneconomic |
| 3 | Reposition or bundle **IMPS-type products** around higher-value or non-UPI-friendly use cases | IMPS volume shrinking while UPI grows |
| 4 | Build **redundancy / failover** for the top banks and rails | Top-5 banks carry over half of mobile banking transactions |
| 5 | Run **activation campaigns** for banks/segments with many registered users but few transactions per user | Engagement scatter and low-engagement table |
| 6 | **Investigate flagged volume-dip days** against outage logs and holidays and set automatic alerts on large day-on-day drops | Day-on-day change chart |
| 7 | Capture **failure code, city/state and device** in the company's own transaction logs | The public data cannot show failures or locations, which limits operational conclusions |
""")

# ----------------------------------------------------------------------------
# TAB 6  DATA QUALITY
# ----------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Data cleaning log")
    st.dataframe(clean_log, hide_index=True, width="stretch")
    st.markdown("""
**Limitations to keep in mind**
- The data is aggregated, system-level RBI statistics, not individual customer transactions.
- There is **no failed/declined-transaction field and no geographic field**. Failure patterns are approached through proxy signals (unusual dips, weekday gaps) and location through bank / bank category.
- Daily sheet: volumes are in lakh, values in ₹ crore. Bank-wise sheets use the source's own units; they are used for shares, ratios and trends, not for absolute rupee claims.
- Daily payments has some missing calendar days; NEFT has three months with no data (2009).
""")

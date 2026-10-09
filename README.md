# 💳 FinTech Digital Payment Transaction Analytics

CA4 Capstone – Business Analytics (IBA, 5th Sem) · Python + Pandas + Plotly + Streamlit

**Live app:** _paste your Streamlit link here_

## Business problem
A digital-payment company wants to understand transaction volumes, payment methods, transaction values,
locations and failure patterns, in order to find operational and customer-service opportunities.

## Dataset (real, public domain)
RBI payment statistics published through the **India Data Portal** (Reserve Bank of India data):
1. Daily Digital Payments (RTGS, NEFT, UPI, IMPS, NACH, NETC, BBPS, AePS, CTS, cards, ATM) – Jun 2020 to Jul 2026
2. Mobile Banking Statistics (bank-wise, monthly) – 2011 to 2025
3. Internet Banking Statistics (bank-wise, monthly) – 2022 to 2025
4. NEFT Transaction Metrics (bank-wise, monthly) – 2008 to 2025
5. Bank-wise ATM / POS / Card statistics – 2022 to 2025

Source link: _paste the exact India Data Portal page links you used for each sheet here._
Raw file: `data/RBI_Digital_Payments_Capstone_Cleaned.xlsx`

**Limitations (stated openly):** the data is aggregated system data, not individual transactions. It has
**no failed-transaction field and no city/state field**, so failure patterns are studied through proxy signals
(unusual day-on-day drops, weekday gaps) and "location" is studied through bank and bank category.

## Data cleaning (`prepare_data.py`)
- Found `month` stored with day and month swapped in two sheets (Internet Banking, NEFT) and fixed it.
- After the fix, thousands of rows were exact duplicate copies of other rows; kept one copy.
- Mobile Banking amounts jump ~100x in five months (a unit change in the source); detected and rescaled.
- Blank RTGS/NACH/CTS values on weekends/holidays were kept as blank (system closed), not filled with 0.
- Full log is saved in `data/clean/cleaning_log.csv` and shown in the dashboard's *Data Quality* tab.

## Dashboard tabs
| Tab | Business question |
|---|---|
| Overview | What is happening? Volume vs value share by method |
| Methods & Ticket Size | Which methods grow, and what is the average payment size? |
| Timing & Stress Signals | When do payments peak or dip? Which days look unusual? |
| Bank-wise View | Which banks carry the volume? Where is engagement weak? |
| Insights & Actions | Findings and recommendations |
| Data Quality | What was cleaned, and what are the limits? |

## Run locally
```bash
pip install -r requirements.txt
python prepare_data.py      # builds data/clean/*.csv (already included in the repo)
streamlit run app.py
```

## Tech
Python, Pandas, NumPy, Plotly, Streamlit, GitHub.

## Author
_Your name(s), roll number(s)_

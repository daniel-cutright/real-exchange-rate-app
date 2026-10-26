# Real Exchange Rate (RER) Analysis App

An interactive macroeconomic web application built with Streamlit and Plotly that computes and visualizes bilateral nominal and real exchange rates using live monthly data from the International Monetary Fund (IMF) SDMX 3.0 API.

## Features
- **IMF SDMX 3.0 Data Ingestion:** Fetches monthly Consumer Price Index (CPI) and exchange rate (local currency per USD) series dating back to January 1976.
- **Bilateral Currency Conversion:** Converts USD-based exchange rates into units of Country 2 currency per 1 unit of Country 1 currency:
  $$S(t) = \frac{E_2(t)}{E_1(t)}$$
- **Real Exchange Rate & Re-indexing:**
  $$RER(t) = S(t) \times \frac{P_1(t)}{P_2(t)}$$
  Dynamically computes the sample mean $RER^*$ and normalizes the Real Index to average 100:
  $$\text{Real Index}(t) = 100 \times \frac{RER(t)}{RER^*}$$
- **Interactive Dual-Axis Visualization:** View Real, Nominal, or Both simultaneously with synchronized tooltips.
- **Data Export:** Download the full monthly dataset with calculations for the active sample window.

## Local Installation
```bash
git clone [https://github.com/](https://github.com/)<your-username>/real-exchange-rate-app.git
cd real-exchange-rate-app
pip install -r requirements.txt
streamlit run app.py

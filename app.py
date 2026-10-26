---

#### 3. `app.py`
```python
import io
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Real Exchange Rate (RER) Explorer",
    page_icon="🌐",
    layout="wide"
)

# Supported countries & IMF codes (ISO3 / IMF Area Code)
COUNTRY_MAP = {
    "United Kingdom (GBP)": {"code": "GBR", "currency": "GBP"},
    "United States (USD)": {"code": "USA", "currency": "USD"},
    "Euro Area (EUR)": {"code": "G163", "currency": "EUR"},
    "Japan (JPY)": {"code": "JPN", "currency": "JPY"},
    "Canada (CAD)": {"code": "CAN", "currency": "CAD"},
    "Australia (AUD)": {"code": "AUS", "currency": "AUD"},
    "Switzerland (CHF)": {"code": "CHE", "currency": "CHF"},
    "Sweden (SEK)": {"code": "SWE", "currency": "SEK"},
    "Norway (NOK)": {"code": "NOR", "currency": "NOK"},
    "Denmark (DNK)": {"code": "DNK", "currency": "DKK"},
    "New Zealand (NZD)": {"code": "NZL", "currency": "NZD"},
    "South Korea (KRW)": {"code": "KOR", "currency": "KRW"},
    "Singapore (SGD)": {"code": "SGP", "currency": "SGD"},
    "Mexico (MXN)": {"code": "MEX", "currency": "MXN"},
    "Brazil (BRL)": {"code": "BRA", "currency": "BRL"},
    "South Africa (ZAR)": {"code": "ZAF", "currency": "ZAR"},
    "India (INR)": {"code": "IND", "currency": "INR"}
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_imf_series(series_type: str, iso_code: str) -> pd.Series:
    """
    Fetch monthly IMF data using SDMX 3.0 REST endpoints.
    series_type: 'CPI' or 'FX'
    """
    # Base URL for IMF SDMX 3.0
    headers = {"Accept": "text/csv, application/json, text/plain"}
    
    if series_type == "CPI":
        # CPI key: {ISO3}.CPI._T.IX.M
        url_candidates = [
            f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/~/{iso_code}.CPI._T.IX.M?c[TIME_PERIOD]=ge:1976-01",
            f"https://api.imf.org/external/sdmx/3.0/data/CPI/{iso_code}.CPI._T.IX.M",
            f"https://api.imf.org/external/sdmx/2.1/data/CPI/M.{iso_code}.CPI._T.IX?startPeriod=1976-01"
        ]
    else:
        # For the US itself, exchange rate is identically 1.0 USD per USD
        if iso_code == "USA":
            dates = pd.date_range(start="1976-01-01", end="2026-12-01", freq="MS")
            return pd.Series(1.0, index=dates, name="FX")
        
        # FX key: {ISO3}.XDC_USD.PA_RT.M (Period average, national currency per USD)
        url_candidates = [
            f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/ER/~/{iso_code}.XDC_USD.PA_RT.M?c[TIME_PERIOD]=ge:1976-01",
            f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IFS/~/{iso_code}.XDC_USD.PA_RT.M?c[TIME_PERIOD]=ge:1976-01",
            f"https://api.imf.org/external/sdmx/2.1/data/IMF.STA,ER/{iso_code}.XDC_USD.PA_RT.M?startPeriod=1976-01"
        ]

    for url in url_candidates:
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200 and len(resp.text.strip()) > 0:
                # If CSV returned
                if "TIME_PERIOD" in resp.text:
                    df = pd.read_csv(io.StringIO(resp.text))
                    date_col = next((c for c in df.columns if "TIME_PERIOD" in c.upper() or "TIME" in c.upper()), None)
                    val_col = next((c for c in df.columns if "OBS_VALUE" in c.upper() or "VALUE" in c.upper()), None)
                    if date_col and val_col:
                        df = df[[date_col, val_col]].dropna()
                        df[date_col] = df[date_col].astype(str).str.replace("-M", "-")
                        df["Date"] = pd.to_datetime(df[date_col], format="%Y-%m", errors="coerce")
                        df["Value"] = pd.to_numeric(df[val_col], errors="coerce")
                        df = df.dropna().drop_duplicates(subset=["Date"]).sort_values("Date")
                        return pd.Series(df["Value"].values, index=df["Date"], name=series_type)
                
                # If JSON returned
                elif resp.headers.get("Content-Type", "").startswith("application/json") or resp.text.startswith("{"):
                    data = resp.json()
                    # Parse standard SDMX-JSON structures
                    obs_list = []
                    # Try SDMX 3.0 / 2.1 data structure extraction
                    if "data" in data and "dataSets" in data["data"]:
                        dataset = data["data"]["dataSets"][0]
                        structure = data["data"]["structures"][0]
                        time_dim = next(d for d in structure["dimensions"]["observation"] if "TIME" in d["id"].upper())
                        time_periods = [p["id"] for p in time_dim["values"]]
                        series_dict = dataset.get("series", {}) or dataset.get("observations", {})
                        
                        for k, v in series_dict.items():
                            obs = v.get("observations", {})
                            for t_idx, val_arr in obs.items():
                                time_str = time_periods[int(t_idx)].replace("-M", "-")
                                obs_list.append({"Date": time_str, "Value": val_arr[0]})
                    
                    if obs_list:
                        df = pd.DataFrame(obs_list)
                        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m", errors="coerce")
                        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
                        df = df.dropna().drop_duplicates(subset=["Date"]).sort_values("Date")
                        return pd.Series(df["Value"].values, index=df["Date"], name=series_type)
        except Exception:
            continue

    return pd.Series(dtype=float, name=series_type)

# App UI Layout
st.title("🌐 Real Exchange Rate (RER) & Relative PPP Explorer")
st.markdown("""
This application downloads official monthly **Consumer Price Index (CPI)** and **Exchange Rate** series from the 
**IMF SDMX 3.0 API** to calculate bilateral Real Exchange Rates (RER) and normalized Real Exchange Rate Indices.
""")

col1, col2 = st.columns(2)
with col1:
    c1_name = st.selectbox("Select Country 1 (Base Currency):", list(COUNTRY_MAP.keys()), index=0)
with col2:
    c2_name = st.selectbox("Select Country 2 (Quote Currency):", list(COUNTRY_MAP.keys()), index=1)

c1_info = COUNTRY_MAP[c1_name]
c2_info = COUNTRY_MAP[c2_name]

if c1_info["code"] == c2_info["code"]:
    st.warning("Please select two distinct countries to compute bilateral exchange rates.")
    st.stop()

# Retrieve data
with st.spinner(f"Retrieving IMF macroeconomic series for {c1_name} and {c2_name}..."):
    p1 = fetch_imf_series("CPI", c1_info["code"])
    p2 = fetch_imf_series("CPI", c2_info["code"])
    e1 = fetch_imf_series("FX", c1_info["code"])
    e2 = fetch_imf_series("FX", c2_info["code"])

# Validation & merging
if p1.empty or p2.empty:
    st.error("CPI data for one or both selected countries could not be retrieved from the IMF API.")
    st.stop()
if e1.empty or e2.empty:
    st.error("Exchange rate data for one or both selected countries could not be retrieved from the IMF API.")
    st.stop()

# Combine series
df = pd.DataFrame({"P1": p1, "P2": p2, "E1": e1, "E2": e2}).dropna()

if df.empty:
    st.error("No overlapping monthly dates found between the retrieved series.")
    st.stop()

# Exchange rate conversion:
# E1 is local currency 1 per USD (e.g. GBP per USD). E2 is local currency 2 per USD (e.g. USD per USD = 1.0).
# Nominal exchange rate S(t) = units of Country 2 currency per 1 unit of Country 1 currency.
# S(t) = E2(t) / E1(t). (For UK -> US: 1.0 / (GBP per USD) = USD per GBP).
df["S"] = df["E2"] / df["E1"]

# Real Exchange Rate: RER(t) = S(t) * P1(t) / P2(t)
df["RER"] = df["S"] * df["P1"] / df["P2"]

# UI Date Range Controls
min_date = df.index.min().date()
max_date = df.index.max().date()

st.sidebar.header("Configuration & Filters")
start_date, end_date = st.sidebar.date_input(
    "Select Sample Date Range:",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

if start_date > end_date:
    st.sidebar.error("Start date must precede end date.")
    st.stop()

# Filter active sample
sample_mask = (df.index.date >= start_date) & (df.index.date <= end_date)
df_sample = df.loc[sample_mask].copy()

if df_sample.empty:
    st.warning("No data points available in the selected sample window.")
    st.stop()

# Recalculate RER* over selected valid months
rer_star = df_sample["RER"].mean()
df_sample["Real_Index"] = 100.0 * (df_sample["RER"] / rer_star)

# Format Date column for reporting
df_sample["Month"] = df_sample.index.strftime("%Y-%m")

# Display Metrics
st.markdown("### Summary Statistics for Selected Period")
mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric("Sample Start", df_sample["Month"].iloc[0])
mcol2.metric("Sample End", df_sample["Month"].iloc[-1])
mcol3.metric("Benchmark RER* (Mean)", f"{rer_star:.4f}")
mcol4.metric("Real Index Mean", f"{df_sample['Real_Index'].mean():.2f}")

# Chart Options
chart_mode = st.radio("Select Series to Display:", ["Both", "Real", "Nominal"], horizontal=True)

# Build Interactive Plotly Charts
c1_curr = c1_info["currency"]
c2_curr = c2_info["currency"]

if chart_mode == "Both":
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(
            x=df_sample.index, 
            y=df_sample["Real_Index"],
            name="Real Index (Mean = 100)",
            line=dict(color="#1f77b4", width=2)
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_sample.index, 
            y=df_sample["S"],
            name=f"Nominal S(t) ({c2_curr} per {c1_curr})",
            line=dict(color="#ff7f0e", width=2, dash="dot")
        ),
        secondary_y=True
    )
    
    fig.add_hline(y=100, line_dash="dash", line_color="gray", secondary_y=False, annotation_text="Benchmark = 100")
    fig.update_yaxes(title_text="Real Index (100 = Sample Average)", secondary_y=False)
    fig.update_yaxes(title_text=f"Nominal S(t) [{c2_curr} per {c1_curr}]", secondary_y=True)

elif chart_mode == "Real":
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sample.index, 
            y=df_sample["Real_Index"],
            name="Real Index",
            line=dict(color="#1f77b4", width=2)
        )
    )
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Benchmark = 100")
    fig.update_layout(yaxis_title="Real Index (100 = Sample Average)")

else:  # Nominal
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sample.index, 
            y=df_sample["S"],
            name=f"Nominal Spot Rate S(t)",
            line=dict(color="#ff7f0e", width=2)
        )
    )
    fig.update_layout(yaxis_title=f"Nominal Spot Rate S(t) [{c2_curr} per {c1_curr}]")

fig.update_layout(
    title=f"{c1_name} vs. {c2_name}: Exchange Rate Trajectory ({df_sample['Month'].iloc[0]} to {df_sample['Month'].iloc[-1]})",
    xaxis_title="Date",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# Data Table & CSV Download Button
st.markdown("### Export Sample Data")
export_cols = ["Month", "P1", "P2", "E1", "E2", "S", "RER", "Real_Index"]
rename_dict = {
    "P1": f"CPI_{c1_curr}",
    "P2": f"CPI_{c2_curr}",
    "E1": f"FX_{c1_curr}_per_USD",
    "E2": f"FX_{c2_curr}_per_USD",
    "S": f"Nominal_S_{c2_curr}_per_{c1_curr}",
    "RER": "Real_Exchange_Rate",
    "Real_Index": "Real_Index_Base_100"
}
export_df = df_sample[export_cols].rename(columns=rename_dict).reset_index(drop=True)

csv_data = export_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Sample Observations and Calculations as CSV",
    data=csv_data,
    file_name=f"RER_{c1_info['code']}_{c2_info['code']}_{df_sample['Month'].iloc[0]}_{df_sample['Month'].iloc[-1]}.csv",
    mime="text/csv"
)

with st.expander("Preview Exported Table"):
    st.dataframe(export_df.head(15), use_container_width=True)

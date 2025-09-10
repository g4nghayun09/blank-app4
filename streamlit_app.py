# streamlit_app.py
"""
주제: 대기 중 이산화탄소(CO₂) 농도와 산소(O₂) 농도 변화 (2000~2025)
출처:
- CO₂: NOAA Mauna Loa Observatory (https://gml.noaa.gov/ccgg/trends/data.html)
- O₂: NOAA ESRL Atmospheric Oxygen (https://gml.noaa.gov/obop/mlo/programs/esrl/oxygen.html)

규칙:
- date / value / group 표준화
- 미래 데이터 제거
- API 실패 시 예시 데이터 대체
- UI 한국어
"""

import io
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date
from zoneinfo import ZoneInfo
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="CO₂ & O₂ 농도 변화 대시보드", layout="wide")

LOCAL_TZ = ZoneInfo("Asia/Seoul")
TODAY_LOCAL = datetime.now(LOCAL_TZ).date()

# ---------- 데이터 로더 ----------
@st.cache_data(ttl=3600)
def load_co2():
    url = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"
    try:
        txt = requests.get(url, timeout=15).text
        df = pd.read_csv(io.StringIO(txt), comment="#", header=None,
                         names=["year","month","decimal_date","average","interpolated","trend","days"])
        df["date"] = pd.to_datetime(df[["year","month"]].assign(DAY=15))
        df = df[["date","trend"]].rename(columns={"trend":"value"})
        df["group"] = "CO₂ (ppm)"
        df = df[df["date"].dt.date <= TODAY_LOCAL]
        df = df[df["date"].dt.year >= 2000]
        return df, url
    except Exception:
        years = pd.date_range("2000-01-01","2025-01-01",freq="M")
        vals = np.linspace(370,420,len(years)) + np.random.normal(0,0.5,len(years))
        df = pd.DataFrame({"date":years,"value":vals,"group":"CO₂ (ppm)"})
        return df, "예시 데이터 (CO₂ 로드 실패)"

@st.cache_data(ttl=3600)
def load_o2():
    url = "https://gml.noaa.gov/webdata/ccgg/trends/o2/o2_alt_surface-flask_allvalid.txt"
    try:
        txt = requests.get(url, timeout=15).text
        df = pd.read_csv(io.StringIO(txt), comment="#", delim_whitespace=True,
                         names=["year","month","decimal_date","o2_conc","stdev","n"])
        df["date"] = pd.to_datetime(df[["year","month"]].assign(DAY=15))
        df = df[["date","o2_conc"]].rename(columns={"o2_conc":"value"})
        df["group"] = "O₂ 변화 (per meg)"
        df = df[df["date"].dt.date <= TODAY_LOCAL]
        df = df[df["date"].dt.year >= 2000]
        return df, url
    except Exception:
        years = pd.date_range("2000-01-01","2025-01-01",freq="M")
        vals = -np.linspace(0,300,len(years)) + np.random.normal(0,10,len(years))
        df = pd.DataFrame({"date":years,"value":vals,"group":"O₂ 변화 (per meg)"})
        return df, "예시 데이터 (O₂ 로드 실패)"

# ---------- 데이터 로드 ----------
st.title("🌍 대기 중 CO₂ & O₂ 농도 변화 (2000~2025)")
co2_df, co2_src = load_co2()
o2_df, o2_src = load_o2()
data = pd.concat([co2_df,o2_df]).reset_index(drop=True)

# ---------- 옵션 ----------
with st.sidebar:
    st.header("옵션")
    start = st.date_input("시작일", value=pd.to_datetime("2000-01-01").date())
    end = st.date_input("종료일", value=min(TODAY_LOCAL, pd.to_datetime("2025-12-31").date()))
    smooth = st.slider("이동 평균 (개월)", 0, 24, 6)

# ---------- 시각화 ----------
mask = (data["date"].dt.date >= start) & (data["date"].dt.date <= end)
sel = data[mask].copy()

if smooth > 0:
    sel = sel.sort_values("date")
    sel["value"] = sel.groupby("group")["value"].transform(lambda s: s.rolling(smooth,1).mean())

fig = px.line(sel, x="date", y="value", color="group",
              title="대기 중 이산화탄소 & 산소 변화 (2000~2025)",
              labels={"date":"날짜","value":"값","group":"지표"})
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ---------- 데이터 다운로드 ----------
def to_csv_bytes(df): return df.to_csv(index=False).encode("utf-8")

st.download_button("📥 데이터 다운로드 (CSV)", data=to_csv_bytes(sel),
                   file_name="co2_o2_2000_2025.csv", mime="text/csv")

st.markdown("---")
st.caption(f"CO₂ 출처: {co2_src}\n\nO₂ 출처: {o2_src}")

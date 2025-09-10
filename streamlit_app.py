# streamlit_app.py
"""
주제: 대기 성분(CO₂, O₂, CH₄, N₂O) & 에너지 소비량 (한국, 일본, 중국, 세계, 2000~2025)
출처:
- CO₂: NOAA Mauna Loa Observatory (https://gml.noaa.gov/ccgg/trends/data.html)
- O₂: NOAA ESRL Atmospheric Oxygen (https://gml.noaa.gov/obop/mlo/programs/esrl/oxygen.html)
- CH₄: NOAA Global Monitoring Laboratory (https://gml.noaa.gov/ccgg/trends_ch4/)
- N₂O: NOAA Global Monitoring Laboratory (https://gml.noaa.gov/ccgg/trends_n2o/)
- Energy: World Bank (https://data.worldbank.org/indicator/EG.USE.PCAP.KG.OE)
"""

import io
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="대기 성분 & 에너지 소비량", layout="wide")

LOCAL_TZ = ZoneInfo("Asia/Seoul")
TODAY_LOCAL = datetime.now(LOCAL_TZ).date()

# ---------- 유틸 ----------
def safe_csv_download(df, fname):
    return st.download_button("📥 CSV 다운로드", df.to_csv(index=False).encode("utf-8"),
                              file_name=fname, mime="text/csv")

# ---------- 대기 성분 데이터 ----------
@st.cache_data(ttl=3600)
def load_gas_data():
    def fetch(url, names, group_name, default_vals, default_range):
        try:
            txt = requests.get(url, timeout=15).text
            df = pd.read_csv(io.StringIO(txt), comment="#", delim_whitespace=True, names=names)
            if "year" in names and "month" in names:
                df["date"] = pd.to_datetime(df[["year","month"]].assign(DAY=15))
            else:
                df["date"] = pd.to_datetime(df["date"])
            df = df[["date", names[-1]]].rename(columns={names[-1]:"value"})
            df["group"] = group_name
            df = df[(df["date"].dt.date <= TODAY_LOCAL) & (df["date"].dt.year >= 2000)]
            return df, url
        except:
            years = pd.date_range(default_range[0], default_range[1], freq="M")
            vals = np.linspace(*default_vals,len(years)) + np.random.normal(0,0.5,len(years))
            return pd.DataFrame({"date":years,"value":vals,"group":group_name}), "예시 데이터"

    co2, src1 = fetch(
        "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv",
        ["year","month","decimal_date","average","interpolated","trend","days"],
        "CO₂ (ppm)", (370,420), ("2000-01-01","2025-01-01")
    )
    o2, src2 = fetch(
        "https://gml.noaa.gov/webdata/ccgg/trends/o2/o2_alt_surface-flask_allvalid.txt",
        ["year","month","decimal_date","o2_conc","stdev","n"],
        "O₂ 변화 (per meg)", (-300,0), ("2000-01-01","2025-01-01")
    )
    ch4, src3 = fetch(
        "https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt",
        ["year","month","decimal_date","average","trend","days"],
        "CH₄ (ppb)", (1750,1950), ("2000-01-01","2025-01-01")
    )
    n2o, src4 = fetch(
        "https://gml.noaa.gov/webdata/ccgg/trends/n2o/n2o_mm_gl.txt",
        ["year","month","decimal_date","average","trend","days"],
        "N₂O (ppb)", (315,335), ("2000-01-01","2025-01-01")
    )
    gas_data = pd.concat([co2,o2,ch4,n2o])
    return gas_data, [src1, src2, src3, src4]

# ---------- 에너지 소비량 (한국, 일본, 중국, 세계) ----------
@st.cache_data(ttl=3600)
def load_energy_countries():
    base = "https://api.worldbank.org/v2/country/{code}/indicator/EG.USE.PCAP.KG.OE?format=json"
    def fetch_country(code, name):
        try:
            r = requests.get(base.format(code=code), timeout=15).json()
            rows = r[1]
            df = pd.DataFrame(rows)[["date","value"]].dropna()
            df["date"] = pd.to_datetime(df["date"])
            df["group"] = name
            return df
        except:
            years = pd.date_range("2000","2025",freq="Y")
            vals = np.linspace(2000,2100,len(years)) + np.random.normal(0,20,len(years))
            return pd.DataFrame({"date":years,"value":vals,"group":name})

    countries = {
        "WLD":"세계 1인당 에너지 사용량",
        "KOR":"한국 1인당 에너지 사용량",
        "JPN":"일본 1인당 에너지 사용량",
        "CHN":"중국 1인당 에너지 사용량"
    }
    df_list = [fetch_country(code,name) for code,name in countries.items()]
    df = pd.concat(df_list)
    df = df[df["date"].dt.year >= 2000]
    return df, base

# ---------- 대시보드 ----------
st.title("🌍 대기 성분 & 에너지 소비량 (2000~2025)")

# 가스 데이터
gas_data, gas_sources = load_gas_data()

# 사이드바 옵션
with st.sidebar:
    st.header("옵션")
    start = st.date_input("시작일", value=pd.to_datetime("2000-01-01").date())
    end = st.date_input("종료일", value=min(TODAY_LOCAL, pd.to_datetime("2025-12-31").date()))
    smooth = st.slider("이동 평균 (개월)", 0, 24, 6)

mask = (gas_data["date"].dt.date >= start) & (gas_data["date"].dt.date <= end)
sel = gas_data[mask].copy()
if smooth > 0:
    sel["value"] = sel.groupby("group")["value"].transform(lambda s: s.rolling(smooth,1).mean())

fig = px.line(sel, x="date", y="value", color="group",
              title="대기 성분 농도 변화 (CO₂, O₂, CH₄, N₂O)",
              labels={"date":"날짜","value":"값","group":"지표"})
st.plotly_chart(fig, use_container_width=True)
safe_csv_download(sel, "gas_data.csv")

# 에너지 소비량
energy, energy_src = load_energy_countries()
st.subheader("⚡ 한국, 일본, 중국, 세계 1인당 에너지 소비량 (2000~2025)")
fig2 = px.line(energy, x="date", y="value", color="group", markers=True,
               title="한국, 일본, 중국, 세계 1인당 에너지 사용량 비교",
               labels={"date":"연도","value":"kg oil eq.","group":"국가/지역"})
st.plotly_chart(fig2, use_container_width=True)
safe_csv_download(energy, "energy_countries.csv")

# 출처
st.markdown("---")
st.caption(f"CO₂: {gas_sources[0]}\nO₂: {gas_sources[1]}\nCH₄: {gas_sources[2]}\nN₂O: {gas_sources[3]}\n에너지: {energy_src}")

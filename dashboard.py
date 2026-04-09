import streamlit as st
import pandas as pd
import plotly.express as px
import os
import pyupbit
import json
from datetime import datetime

st.set_page_config(page_title="Minchacco Trading Bot", layout="wide")

# 가시성 개선 CSS
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #adbac7; }
    .stMetric { 
        background-color: #1c2128; border: 2px solid #FFD700; 
        border-radius: 12px; padding: 20px;
    }
    [data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 28px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Minchacco Bitcoin Intelligence")

# 🔐 키 연결 상태 확인 (디버깅)
def get_upbit():
    access, secret = None, None
    
    # 1. 웹 환경(Secrets) 확인
    if "upbit_access_key" in st.secrets:
        access = st.secrets["upbit_access_key"]
        secret = st.secrets["upbit_secret_key"]
        # st.sidebar.success("✅ 웹 서버에서 키 인식 성공")
    
    # 2. 로컬 환경 확인
    elif os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        access = cfg['upbit_access_key']
        secret = cfg['upbit_secret_key']
        # st.sidebar.info("🏠 로컬 컴퓨터 키 사용 중")

    if access and secret:
        return pyupbit.Upbit(access, secret)
    return None

upbit = get_upbit()

# 💰 실시간 자산 섹션
st.subheader("💰 실시간 자산 현황 (LIVE)")
c1, c2, c3, c4 = st.columns(4)

if upbit:
    try:
        krw = upbit.get_balance("KRW")
        btc = upbit.get_balance("KRW-BTC")
        price = pyupbit.get_current_price("KRW-BTC")
        avg = upbit.get_avg_buy_price("KRW-BTC")
        
        # 키가 맞는데 0원인 경우 방지 (API 호출 결과 확인)
        if krw is None:
            st.error("🚨 업비트 서버에서 데이터를 가져올 수 없습니다. 키 권한(자산조회)을 확인하세요.")
            krw, btc, price, avg = 0, 0, 0, 0
        
        total = krw + (btc * price)
        c1.metric("총 자산", f"{total:,.0f} KRW")
        c2.metric("현금 잔고", f"{krw:,.0f} KRW")
        c3.metric("BTC 평가금", f"{(btc * price):,.0f} KRW")
        
        if btc > 0:
            yield_p = ((price - avg) / avg) * 100
            c4.metric("수익률", f"{yield_p:+.2f}%")
        else:
            c4.metric("포지션", "관망 중")
    except Exception as e:
        st.error(f"⚠️ 연결 오류 발생: {e}")
else:
    st.error("🚨 웹사이트가 API 키를 찾지 못했습니다. Secrets 설정을 다시 확인해주세요.")

st.markdown("---")

# 🤖 상태창 (GitHub에 Push된 최신 상태)
st.subheader("🤖 로봇 상태 (최근 업로드 시점)")
if os.path.exists("status.json"):
    with open("status.json", "r") as f:
        status = json.load(f)
    st.info(f"마지막 업데이트: {status.get('update_time')} | 지표: {status['indicator']} | 목표: {status['target']}")
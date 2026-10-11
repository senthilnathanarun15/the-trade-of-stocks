from email.policy import default

import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit import session_state
import google.generativeai as gen_ai
gen_ai.configure(api_key=st.secrets["gemini_api_key"])
model = gen_ai.GenerativeModel("gemini-3.8-flash")

st.subheader("📈the stock analyser")
st.sidebar.subheader("stocks")
stock_select = st.sidebar.selectbox(
  "select the stock" ,("GOLD","AAPL","BTC-USD")
)
default_stocks = "GOLD,AAPL,BTC-USD"
multi_stock_input = st.sidebar.text_input("enter preferd stock")
multi_stock_select = [t.strip().upper() for t in multi_stock_input.strip(",") if t.strip()]
show_raw_data =st.sidebar.checkbox("show raw tabular data")
stock = yf.Ticker(stock_select)
time_format = st.sidebar.selectbox("select time in",("Months","Years"))
if time_format == "Months":
    time = st.sidebar.slider("select your time in months",
                             min_value=1,
                             max_value=12,
                             value=3)
    df = stock.history(period = f"{time}mo")
if time_format == "Years" :
    time = st.sidebar.slider("select your time in years",
                             min_value=1,
                             max_value=10,
                             value=1)
    df = stock.history(period = f"{time}y")
start_price = df["Close"].iloc[0]
current_price = df["Close"].iloc[-1]
price_dif = current_price - start_price
per_dif = (current_price/start_price) * 100
multi_stock = st.sidebar.checkbox("multi stock analysis")
data = yf.download(multi_stock_select,period=time)
st.write(f"{stock_select} history for {time} in {time_format}")
st.line_chart(df["Close"])
st.line_chart(data["Close"])
c1,c2,c3,c4 = st.columns(4)
c1.metric(label= "current price:",value=f"${current_price:.2f}")
c2.metric(label= "price difference:",value=f"${price_dif:.2f} ",delta=f"{per_dif:.2f}")
c3.metric(label= "highest value:",value=f"${df["High"].max():.2f} ")
df["Daily Return"] = df["Close"].pct_change()
daily_volitity = df["Daily Return"].std() *100
c4.metric(label="daily return %" , value=f"{daily_volitity :.2f}")
#if mu
if show_raw_data :
    st.subheader("tabular stock format")
    st.dataframe(df)
if st.button("analyse"):
    info = stock.info
    context = f"stock name : {info.get('longName')} , stock sector : {info.get('sector')},current_price : {info.get('currentPrice')}"
    response = model.generate_content(F"analyse this stock for me {context}")
    st.write(response.text)
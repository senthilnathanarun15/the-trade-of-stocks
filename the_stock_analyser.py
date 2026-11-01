from calendar import month

import streamlit as st
import pandas as pd
import yfinance as yf
from google.genai import Client
from streamlit import session_state
import google.genai as genai
from streamlit.elements.widgets import checkbox

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error("the api has failed")
    client = None
st.subheader("📈the stock analyser")
st.sidebar.subheader("stocks")
stock_select = st.sidebar.selectbox(
  "select the stock" ,("GOLD","AAPL","BTC-USD")
)
#default_stocks = "GOLD,AAPL,BTC-USD"
normalize_stocks = False
multi_stock_input = st.sidebar.text_input("enter prefered tickers (seperated with ,) ")
multi_stock_select = [str(t).strip().upper() for t in multi_stock_input.split(",") if str(t).strip()]
show_raw_data =st.sidebar.checkbox("show raw tabular data")
stock = yf.Ticker(stock_select)
time_format = st.sidebar.selectbox("select time in",("Months","Years"))
end_date = pd.Timestamp.today()
sma_check = False
rsi_check = False
if time_format == "Months":
    time = st.sidebar.slider("select your time in months",
                             min_value=1,
                             max_value=12,
                             value=3)

    start_date = end_date - pd.DateOffset(months = time)
    df = stock.history(start= start_date.strftime('%Y-%m-%d'),
                                                      end= end_date.strftime('%Y-%m-%d'))
if time_format == "Years" :
    time = st.sidebar.slider("select your time in years",
                             min_value=1,
                             max_value=10,
                             value=1)
    start_date = end_date - pd.DateOffset(years = time)
    df = stock.history(start= start_date.strftime('%Y-%m-%d'),
                                                      end= end_date.strftime('%Y-%m-%d'))

tab1,tab2 = st.tabs(["single stock analysis"," multi-stock analysis"])
with tab1:
   if st.checkbox("sma"):
       sma_check = True
   if st.checkbox("rsi"):
       rsi_check = True
   if df.empty:
        st.error("you have not entered a valid stock")
   else:
        close_col = None
        for col in df.columns:
            col_str = str(col[0]) if isinstance(col,tuple) else str(col)
            if col_str.lower() == "close":
                close_col = col
                break
        if close_col is None and "Close" in df.columns:
            close_col = "Close"
        if close_col is not None:
            close_prices = df[close_col].squeeze()
            if rsi_check:
                delta = close_prices.diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                gain_avg = gain.rolling(window=14).mean()
                loss_avg = loss.rolling(window=14).mean()
                rs = gain_avg / loss_avg
                rsi = 100 - (100 / (1 + rs))
                chart_data = pd.DataFrame({
                    "Close": close_prices,
                })
                st.subheader(f"{stock_select} rsi for {time} in {time_format}")
                st.line_chart(rsi)
            if sma_check:
                sma_window = st.slider("select the days for the sma average" , min_value=5,max_value=200,value=20)
                sma_series= close_prices.rolling(window=sma_window).mean()
                chart_data = pd.DataFrame({
                    "Close" : close_prices,
                    "SMA" : sma_series
                })
                st.subheader(f"{stock_select} history and sma window for {time} in {time_format}")
            else:
                chart_data = pd.DataFrame({
                    "Close": close_prices,
                })
                st.subheader(f"{stock_select} history for {time} in {time_format}")
            st.line_chart(chart_data)
        start_price = df["Close"].iloc[0]
        current_price = df["Close"].iloc[-1]
        price_dif = current_price - start_price
        per_dif = (current_price / start_price) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(label="current price:", value=f"${current_price:.2f}")
        c2.metric(label="price difference:", value=f"${price_dif:.2f} ", delta=f"{per_dif:.2f}")
        c3.metric(label= "highest value:",value=f"${df["High"].max():.2f} ")
        df["Daily Return"] = df["Close"].pct_change()
        daily_volitity = df["Daily Return"].std() *100
        c4.metric(label="daily return %" , value=f"{daily_volitity :.2f}")
   if st.button("analyse"):
       # info = yf.Ticker(multi_stock_select).info
       context = chart_data,stock,df
       response = client.models.generate_content(model="gemini-3.5-flash",
                                                 contents=F"analyse these stock for me {context} and explain the pros and cons of each")
       st.markdown(response.text)
with tab2:
    if st.checkbox("do you want to normalize prices (works best with large gaps between assets or stocks )"):
        normalize_stocks = True
    if st.sidebar.checkbox("multi stock analysis") :
            if not multi_stock_select:
                st.error("you have not selected any stock")
            else:
                try:
                    close_prices = pd.DataFrame()
                    stock_prices_list = []
                    analyse_list = []
                    for ticker in multi_stock_select:
                        multi_stock = yf.Ticker(ticker)
                        history = multi_stock.history(start= start_date.strftime('%Y-%m-%d'),
                                                      end= end_date.strftime('%Y-%m-%d')
                                                      )
                        if not history.empty:
                            close_col = None
                            for col in history.columns:
                                col_str = str(col[0]) if isinstance(col,tuple) else str(col)
                                if col_str.lower() == "close":
                                    close_col = col
                                    break

                            if close_col is None and "Close" in history.columns:
                                    close_col = "Close"
                            if close_col is not None:
                                s = history[close_col].squeeze()
                                s.name = ticker
                                stock_prices_list.append(s)
                        if stock_prices_list :
                            close_prices = pd.concat(stock_prices_list,axis=1).ffill().bfill()
                            close_prices.index =  pd.to_datetime(close_prices.index).normalize()
                            close_prices = close_prices.groupby(close_prices.index).last().ffill().bfill()
                        else :
                            close_prices = pd.DataFrame()
                    if close_prices.empty:
                        st.error("no valid stock names were there in your input plz check and try later")
                    else:
                        st.success("data has been loaded successfully")
                        pd.DataFrame(close_prices.tail())
                        if normalize_stocks:
                            normalized_prices = close_prices/close_prices.iloc[0] *100
                            normalized_prices = normalized_prices.ffill().bfill()
                            st.line_chart(normalized_prices)
                            analyse_list.append(close_prices.iloc[0])
                            analyse_list.append(close_prices.iloc[-1])
                        else :
                            st.line_chart(close_prices)
                        print(close_prices)
                        st.subheader("the stock performence")
                        col = st.columns(len(multi_stock_select))
                        for i ,ticker in enumerate(multi_stock_select):
                            if normalize_stocks:
                                normalized_prices = normalized_prices.ffill().bfill()
                                pct_normalized_prices = normalized_prices[ticker].iloc[-1] - 100
                                col[i].metric(label=f"{ticker}: price return",
                                              value= f"{pct_normalized_prices:.2f} %",
                                              delta=f"{pct_normalized_prices:.2f} %"
                                              )
                                analyse_list.append(pct_normalized_prices)
                            else:
                                close_prices = close_prices.ffill()
                                pct_close_prices = ((close_prices[ticker].iloc[-1] - close_prices[ticker].iloc[0])/close_prices[ticker].iloc[0]) *100
                                col[i].metric(label=f"{ticker}: price return",
                                              value=f"{pct_close_prices:.2f} %",
                                              delta=f"{pct_close_prices:.2f} %" )
                                analyse_list.append(pct_close_prices)
                        print(multi_stock_select)
                        if st.button("analyse"):
                            #info = yf.Ticker(multi_stock_select).info
                            context = analyse_list,multi_stock_select, #f"stock name : {info.get('longName')} , stock sector : {info.get('sector')},current_price : {info.get('currentPrice')}"
                            response = client.models.generate_content(model="gemini-3.5-flash",contents=F"analyse these stock for me {context} and explain the pros and cons of each")
                            st.markdown(response.text)
                        if normalize_stocks:
                            csv_data = normalized_prices.to_csv().encode('utf-8')
                        else :
                            csv_data = close_prices.to_csv().encode("utf-8")
                        st.download_button("download the csv file",
                                                data=csv_data,
                                                file_name="stock_data",
                                                mime = "text/csv",
                                                )
                        if show_raw_data :
                            st.subheader("tabular stock format")
                            st.dataframe(multi_stock)
                except Exception as er:
                    st.error(f"your selection of the multi-stock analysis has not been done try later {er}")



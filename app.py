import streamlit as st
import tpqoa
import pandas as pd
import numpy as np
import plotly.graph_objects as pg
from io import StringIO 
api = tpqoa.tpqoa("oanda.cfg")
from forex_python.converter import CurrencyRates
import pyfolio as pf
import matplotlib.pyplot as plt
import yfinance as yf



st.set_page_config(layout="wide")

st.image("Blue.png", width=300)
st.title("QuantConnect Trade Analyzer")


uploaded_file = st.sidebar.file_uploader("Choose a TXT file", accept_multiple_files=False, type="txt")
uploaded_table = st.sidebar.file_uploader("Choose a CSV file", accept_multiple_files=False, type="csv")

granularity = st.sidebar.radio(
    "Enter Interval",
    ['M15', 'M5']
)
symbols = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY", "EURAUD", "EURGBP", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADNZD"]
keywords = st.sidebar.selectbox(
    "Enter Filter",
    ['None', 'Win', 'Loss']+symbols,
)

equity = st.sidebar.number_input("Starting Equity", value=100000)

orders = pd.DataFrame()
SL = 0
TP1 = 0
TP2 = 0
TSL = 0
PnL = 0
c = CurrencyRates()
if uploaded_file is None or uploaded_table is None:
    st.warning("Upload TXT and CSV files to begin")

elif uploaded_file is not None and uploaded_table is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Charts", "Orders", "Performance"])
    trades = pd.read_csv(uploaded_table, index_col="Time")
    trades = trades[trades.Status != "Canceled"]
    currencies = [pair[3:] for pair in symbols]
    currencies = list(set(currencies))

    for i in range(0, len(trades)):
        if trades.iloc[i].Quantity > 0:
            time = trades.index[i]
            symbol = trades.iloc[i].Symbol
            price = trades.iloc[i].Price
            quantity = trades.iloc[i].Quantity
            index1 = 0
            index2 = 0
            for k in range(i+1, len(trades)):
                if trades.iloc[k].Symbol == symbol:
                    index1 = k
                    break
            for k in range(index1+1, len(trades)):
                if trades.iloc[k].Symbol == symbol:
                    index2 = k
                    break
            if trades.iloc[i].Quantity == -trades.iloc[index1].Quantity:
                PnL = (trades.iloc[index1].Price - trades.iloc[i].Price)*trades.iloc[i].Quantity
                SL = trades.iloc[index1].Price
                TP1 = np.nan
                TP2 = np.nan
                TSL = np.nan
            elif trades.iloc[index1].Quantity == -trades.iloc[i].Quantity/2:
                PnL = (trades.iloc[index1].Price - trades.iloc[i].Price)*trades.iloc[i].Quantity/2 + (trades.iloc[index2].Price - trades.iloc[i].Price)*trades.iloc[i].Quantity/2
                SL = np.nan
                if trades.iloc[index1]["Tag "] == "Trailing Stop Loss ":
                    TSL = trades.iloc[index1].Price
                    TP1 = trades.iloc[index2].Price
                    TP2 = np.nan
                elif trades.iloc[index2]["Tag "] == "Trailing Stop Loss ":
                    TSL = trades.iloc[index2].Price
                    TP1 = trades.iloc[index1].Price
                    TP2 = np.nan
                else:
                    TP2 = max(trades.iloc[index1].Price, trades.iloc[index2].Price)
                    TP1 = max(trades.iloc[index1].Price, trades.iloc[index2].Price)
                    TSL = np.nan
            currency = symbol[3:]
            if PnL == 0:
                PnLUSD = 0
            elif currency != "USD":
                PnLUSD = PnL * yf.download(currency+"USD=X", start=pd.to_datetime(trades.index[i]), end=pd.to_datetime(trades.index[i])+ pd.Timedelta("1 day")).iloc[0].Close
            else:
                PnLUSD = PnL
            #PnLUSD = c.convert(currency, 'USD', PnL, pd.to_datetime(time))
            orders = orders.append({"Time": time, "Symbol":symbol, "Price":price, "Quantity":quantity, "SL": SL, "TSL": TSL, "TP1": TP1, "TP2": TP2, "P/L": PnL, "Currency": currency, "P/L (USD)": PnLUSD}, ignore_index=True)
    trades.index = pd.to_datetime(trades.index).tz_convert(None)
    name = uploaded_file.name
    #st.write(trades)
    with tab1:
        orders.set_index('Time', inplace=True)
        orders["Equity"] = orders["P/L (USD)"].cumsum()
        orders["Equity"] += equity
        orders.index = pd.to_datetime(orders.index).tz_convert(None)
        orders["Returns"] = orders.Equity.pct_change()
        orders.at[orders.index[0], "Returns"] = orders.iloc[0]["P/L (USD)"] / equity
        orders.Returns = orders.Returns#.map('{:.2%}'.format)
        #orders = orders.iloc[:-1 , :]
        
        backtest_stats = pf.timeseries.perf_stats(orders.Returns)
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        col1.metric("Equity", "$"+str(round(orders.iloc[-1].Equity)), str(round(orders.iloc[-1].Equity-equity,2)))
        col2.metric("Return", str(round(backtest_stats.iloc[1]*100, 2))+"%")
        col3.metric("CAGR", str(round(backtest_stats.iloc[0]*100, 2))+"%")
        col4.metric("Sharpe Ratio", str(round(backtest_stats.iloc[3], 2)))
        col5.metric("Max Drawdown", str(round(backtest_stats.iloc[6]*100, 2))+"%")
        col6.metric("Daily VaR", str(round(backtest_stats.iloc[-1]*100, 2))+"%")
        col7.metric("P/L Ratio", round(-(orders[orders.Returns > 0]['Returns'].mean()/orders[orders.Returns < 0]['Returns'].mean()), 2))
        col8.metric("Win Ratio", str(round((len(orders[orders.Returns > 0]['Returns'])/len(orders[orders.Returns != 0]['Returns']))*100))+"%")
        
        chart1, chart2 = st.columns(2)

        fig1, ax1 = plt.subplots()
        fig2, ax2 = plt.subplots()
        bins = round(len(orders)/1.5)
        ax1.hist(orders.Returns, bins=bins)
        ax2.plot(orders.Equity)
        chart1.subheader("Returns Distribution")
        chart1.pyplot(fig1)
        chart2.subheader("Equity")
        chart2.pyplot(fig2)

        orders["Cum Returns"] = np.exp(np.log1p(orders['Returns']).cumsum())
        orders["HighVal"] = orders['Cum Returns'].cummax()
        orders['Drawdown'] = orders['Cum Returns'] - orders['HighVal']

        chart3, chart4 = st.columns(2)
        fig3, ax3 = plt.subplots()
        fig4, ax4 = plt.subplots()
        ax3.plot(orders.Drawdown)
        chart3.subheader("Drawdown")
        chart3.pyplot(fig3)
        
        

        num_simulations = 1000  # Number of simulations
        num_periods = 252  # Number of trading days in a year (for daily simulation)
        initial_price = equity  # Initial price of the asset
        mu = backtest_stats.iloc[0]  # Average annual return (mean)
        volatility = backtest_stats.iloc[2]  # Annual volatility (standard deviation)

        # Perform Monte Carlo simulation
        simulated_prices = np.zeros((num_periods, num_simulations))
        simulated_prices[0, :] = initial_price

        for t in range(1, num_periods):
            # Generate random returns from a normal distribution
            daily_returns = np.random.normal(mu / num_periods, volatility / np.sqrt(num_periods), num_simulations)
            simulated_prices[t, :] = simulated_prices[t - 1, :] * (1 + daily_returns)

        # Plot simulation results
        ax4.plot(simulated_prices)

        chart4.subheader("Monte Carlo Simulation")
        chart4.pyplot(fig4)

    with tab3:
        st.write(orders)
        st.download_button('Download Orders', orders.to_csv(index=True).encode('utf-8'), "file.csv", "text/csv", key='download-csv')
    with tab4:
        st.table(pd.DataFrame(backtest_stats).T)


    with tab2:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        raw = stringio.readlines()
        lines = [line.rstrip() for line in raw]

        win = 0
        loss = 0
        for line in lines:
            index = lines.index(line)
            if index > len(lines) - 4:
                    break
            if line[28:39] == "Date Found:":
                if lines[index+3][28:42] == "Stop Loss Hit:":
                    loss += 1 
                else:
                    win += 1
                
        for line in lines:
            if line[26] == ":":
                instrument = line[20:26]
                index = lines.index(line)
                if index > len(lines) - 4:
                    break
                if "None" in keywords or instrument in keywords or ("Win" in keywords and lines[index+3][28:42] != "Stop Loss Hit:") or ("Loss" in keywords and lines[index+3][28:42] == "Stop Loss Hit:"):
                    if line[28:39] == "Date Found:":
                        dateStart = pd.to_datetime(line[40:59]) + pd.Timedelta(pd.to_timedelta("2 hours"))
                        dateEnd = pd.to_datetime(line[0:19]) + pd.Timedelta(pd.to_timedelta("8 hours"))
                        instrument = line[20:23]+"_"+line[23:26]
                        distal = lines[index+1][36:]
                        proximal = lines[index+2][38:]

                        session = orders[(orders.index >= pd.to_datetime(line[40:59])+ pd.Timedelta(pd.to_timedelta("3 hours"))) & (orders.index <= pd.to_datetime(line[40:59])+ pd.Timedelta(pd.to_timedelta("7 hours"))) & (orders.Symbol == line[20:26])]

                        data = api.get_history(instrument = instrument, start = dateStart, end = dateEnd,
                            granularity = granularity, price = "M", localize = False)

                        st.header(line[20:26])
                        #st.subheader("P/L: $"+str(round((0-session.Value.sum())/session.Value.iloc[0] *100))+"%")
                        st.subheader(pd.to_datetime(line[40:59]) + pd.Timedelta(pd.to_timedelta("4 hours")))
                        fig = pg.Figure()
                        fig.add_trace(pg.Candlestick(x=data.index, open=data["o"], high=data["h"], low=data["l"], close=data["c"]))
                        fig.add_hline(y=float(proximal), annotation_text="Proximal")#, annotation="Proximal")
                        fig.add_hline(y=float(distal), annotation_text="Distal")#, annotation="Distal")
                        #fig.add_hline(y=float(exit), annotation_text=type)
                        for index, row in session.iterrows():
                            st.write(pd.DataFrame(row).T)
                            if row.SL > 0:
                                fig.add_hline(y=row.SL, annotation_text="Stop Loss")
                            if row.TSL > 0:
                                fig.add_hline(y=row.TSL, annotation_text="Trailing Stop Loss")
                            if row.TP1 > 0:
                                fig.add_hline(y=row.TP1, annotation_text="Take Profit: Prev Breakout")
                            if row.TP2 > 0:
                                fig.add_hline(y=row.TP2, annotation_text="Take Profit")
                            fig.add_hline(y=row.Price, annotation_text="Buy")
                            
                        fig.update_layout(
                            margin=dict(l=20, r=20, t=20, b=20),
                            width=1200,
                            height = 800
                        )
                        st.plotly_chart(fig)
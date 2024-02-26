import streamlit as st
import tpqoa
import pandas as pd
import plotly.graph_objects as pg
from io import StringIO 
api = tpqoa.tpqoa("oanda.cfg")
from streamlit_tags import st_tags, st_tags_sidebar
st.set_page_config(layout="wide")

st.image("Blue.png", width=300)
st.title("QuantConnect Trade Analyzer")


uploaded_file = st.sidebar.file_uploader("Choose a TXT file", accept_multiple_files=False, type="txt")
uploaded_table = st.sidebar.file_uploader("Choose a CSV file", accept_multiple_files=False, type="csv")

#trades.index += pd.Timedelta(pd.to_timedelta("4 hours"))
granularity = st.sidebar.radio(
    "Enter Interval",
    ['M15', 'M5']
)

keywords = st.sidebar.selectbox(
    "Enter Filter",
    ['None', 'Win', 'Loss', "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY", "EURAUD", "EURGBP", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADNZD"],
)

if uploaded_file is not None and uploaded_table is not None:
    trades = pd.read_csv(uploaded_table, index_col="Time")
    trades.index = pd.to_datetime(trades.index).tz_convert(None)
    name = uploaded_file.name
    st.write(trades)

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
    
    st.header("Win Ratio: " + str(round(win/(win+loss)*100))+ "%")
    
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
                    #print(pd.to_datetime(line[40:59]), pd.to_datetime(line[0:19]))
                    
                    
                    
                    session = trades[(trades.index >= pd.to_datetime(line[40:59])+ pd.Timedelta(pd.to_timedelta("4 hours"))) & (trades.index <= pd.to_datetime(line[0:19])+ pd.Timedelta(pd.to_timedelta("4 hours"))) & (trades.Symbol == line[20:26])]
                    print(session)

                    if lines[index+3][28:42] == "Stop Loss Hit:":
                        exit = lines[index+3][43:]
                        type = "Stop Loss Hit"
                    else:
                        exit = lines[index+3][45:]
                        type = "Take Profit Hit"
                    
                    data = api.get_history(instrument = instrument, start = dateStart, end = dateEnd,
                        granularity = granularity[0], price = "M", localize = False)

                    st.header(line[20:26])
                    st.subheader("P/L: $"+str(round(0-session.Value.sum())))
                    #st.subheader("P/L: $"+str(round((0-session.Value.sum())/session.Value.iloc[0] *100))+"%")
                    st.subheader(pd.to_datetime(line[40:59]) + pd.Timedelta(pd.to_timedelta("4 hours")))
                    fig = pg.Figure()
                    fig.add_trace(pg.Candlestick(x=data.index, open=data["o"], high=data["h"], low=data["l"], close=data["c"]))
                    fig.add_hline(y=float(proximal), annotation_text="Proximal")#, annotation="Proximal")
                    fig.add_hline(y=float(distal), annotation_text="Distal")#, annotation="Distal")
                    #fig.add_hline(y=float(exit), annotation_text=type)
                    for index, row in session.iterrows():
                        if row.Quantity > 0 and row.Price != 0:
                            fig.add_hline(y=row.Price, annotation_text="Buy")
                        elif row.Price != 0:
                            fig.add_hline(y=row.Price, annotation_text="Sell")
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=20, b=20),
                        width=1500,
                        height = 800
                    )
                    st.plotly_chart(fig)
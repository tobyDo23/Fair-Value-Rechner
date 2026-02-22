import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# 1. Datenbank-Setup
def init_db():
    conn = sqlite3.connect('aktien_daten.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analysen 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, peg REAL)''')
    conn.commit()
    conn.close()

init_db()

# 2. Seiteneinstellungen
st.set_page_config(page_title="Aktien-Check Live", layout="centered")
st.title("🚀 Aktien-Analyse Terminal")

# 3. Live-Daten Abfrage
ticker_input = st.text_input("Börsenkürzel (z.B. AAPL, MSFT, SAP.DE)", value="AAPL").upper()

@st.cache_data(ttl=3600)
def get_full_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "pe": info.get("trailingPE", 0.0),
            "growth_est": info.get("earningsGrowth", 0.10),
            "eps_next": info.get("forwardEps", 0.0)
        }
    except: return None

data = get_full_data(ticker_input)

if data:
    # PEG Berechnung
    peg = data['pe'] / (data['growth_est'] * 100) if data['growth_est'] > 0 else 0
    
    st.subheader(f"Marktdaten: {data['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Kurs", f"{data['price']:.2f} €")
    c2.metric("KGV (Ist)", f"{data['pe']:.1f}")
    c3.metric("PEG Ratio", f"{peg:.2f}")

    # 4. Analyse-Parameter
    with st.sidebar:
        st.header("Analyse-Basis")
        shares = st.number_input("Aktien (Mio.)", value=100.0)
        mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100
        fcf = st.number_input("Free Cashflow (Mio. €)", value=100.0)
        growth_slider = st.slider("Wachstum % (DCF)", 0, 40, int(data['growth_est']*100)) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data['pe']) if data['pe'] else 15.0)

    # 5. Berechnung
    # DCF (vereinfacht für stabilen Lauf)
    val_dcf = ((fcf * (1 + growth_slider)) / (0.09 - 0.02)) / shares 
    val_kgv = data['eps_next'] * pe_target
    fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
    buy_limit = fair_value * (1 - mos)

    # 6. Grafik
    fig = go.Figure(go.Bar(
        x=['Marktpreis', 'Fairer Wert', 'Kauf-Limit'],
        y=[data['price'], fair_value, buy_limit],
        marker_color=['#636EFA', '#00CC96', '#EF553B']
    ))
    st.plotly_chart(fig, use_container_width=True)

    # 7. Speichern
    if st.button("💾 Analyse dauerhaft speichern"):
        conn = sqlite3.connect('aktien_daten.db')
        conn.cursor().execute("INSERT INTO analysen VALUES (?, ?, ?, ?, ?)", 
                             (ticker_input, data['name'], round(fair_value, 2), round(buy_limit, 2), round(peg, 2)))
        conn.commit()
        st.success("Gespeichert!")

# Historie zeigen
st.divider()
if st.checkbox("Historie anzeigen"):
    conn = sqlite3.connect('aktien_daten.db')
    df = pd.read_sql_query("SELECT * FROM analysen", conn)
    st.dataframe(df)

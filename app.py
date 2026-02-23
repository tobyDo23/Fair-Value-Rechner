import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# Datenbank Initialisierung
def init_db():
    conn = sqlite3.connect('safe_stocks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Aktien-Check Safe", layout="wide")
st.title("🛡️ Aktien-Analyse (Robust)")

# Eingabe
ticker_symbol = st.text_input("Aktien-Kürzel eingeben (z.B. AAPL)", "AAPL").upper()

@st.cache_data(ttl=600)
def load_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Wir versuchen nur die nötigsten Daten zu holen
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None
        
        # Finanzdaten
        income = stock.financials
        cf = stock.cashflow
        
        return {
            "name": info.get("longName", ticker),
            "price": info.get("currentPrice", 0.0),
            "pe": info.get("trailingPE", 15.0),
            "eps_growth": info.get("earningsGrowth", 0.1),
            "eps_next": info.get("forwardEps", 5.0),
            "shares": info.get("sharesOutstanding", 1000000) / 1_000_000,
            "income_data": income,
            "cf_data": cf
        }
    except Exception as e:
        st.error(f"Fehler beim Laden von {ticker}: {e}")
        return None

data = load_data(ticker_symbol)

if data:
    st.success(f"Daten für {data['name']} erfolgreich geladen!")
    
    # Anzeige oben
    c1, c2, c3 = st.columns(3)
    c1.metric("Preis", f"{data['price']:.2f} €")
    c2.metric("KGV", f"{data['pe']:.1f}")
    c3.metric("Aktien (Mio.)", f"{data['shares']:.1f}")

    # --- HISTORIE ---
    st.subheader("Finanz-Historie (Mio.)")
    try:
        if not data['income_data'].empty:
            df_hist = data['income_data'].loc[['Total Revenue', 'Net Income']].head(3).T
            st.table(df_hist.style.format("{:.2f}"))
    except:
        st.info("Keine Detail-Historie verfügbar.")

    # --- RECHNER ---
    with st.sidebar:
        st.header("Analyse-Werte")
        fcf_manual = st.number_input("Free Cashflow (Mio.)", value=100.0)
        growth = st.slider("Wachstum %", 0, 40, 10) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data['pe']))
        mos = st.slider("Sicherheitsmarge %", 0, 50, 20) / 100

    # Berechnung (DCF vereinfacht für Stabilität)
    val_dcf = ((fcf_manual * (1 + growth)) / (0.09 - 0.02)) / data['shares']
    val_kgv = data['eps_next'] * pe_target
    fair_value = (val_dcf * 0.5) + (val_kgv * 0.5)
    buy_limit = fair_value * (1 - mos)

    # Grafik
    fig = go.Figure(go.Bar(
        x=['Markt', 'Fairer Wert', 'Kauf-Limit'],
        y=[data['price'], fair_value, buy_limit],
        marker_color=['blue', 'green', 'red']
    ))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("Speichern"):
        conn = sqlite3.connect('safe_stocks.db')
        conn.cursor().execute("INSERT INTO history (ticker, name, fair_value, buy_limit) VALUES (?,?,?,?)",
                             (ticker_symbol, data['name'], fair_value, buy_limit))
        conn.commit()
        st.toast("Gespeichert!")

else:
    st.warning("⚠️ Keine Daten gefunden. Versuche es mit einem anderen Kürzel (z.B. MSFT oder TSLA).")

# Historie
if st.checkbox("Analysen zeigen"):
    conn = sqlite3.connect('safe_stocks.db')
    df_h = pd.read_sql_query("SELECT * FROM history", conn)
    st.dataframe(df_h, use_container_width=True)

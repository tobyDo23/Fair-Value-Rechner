import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# Datenbank-Setup
def init_db():
    conn = sqlite3.connect('aktien_daten.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analysen 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, peg REAL)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Aktien-Check Smart", layout="centered")
st.title("🚀 Smart Stock Terminal")

# Suche
ticker_input = st.text_input("Börsenkürzel eingeben", value="AAPL").upper()

@st.cache_data(ttl=3600)
def get_smart_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Free Cashflow aus der Cashflow-Rechnung extrahieren (letzter verfügbarer Wert)
        # Formel: Operating Cashflow + Capital Expenditures (CapEx ist meist negativ bei yf)
        cf_sheet = stock.cashflow
        fcf_auto = 0.0
        if not cf_sheet.empty:
            ocf = cf_sheet.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cf_sheet.index else 0
            capex = cf_sheet.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cf_sheet.index else 0
            fcf_auto = (ocf + capex) / 1_000_000 # In Millionen umrechnen
            
        return {
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "shares": info.get("sharesOutstanding", 10.0) / 1_000_000, # In Millionen
            "fcf": fcf_auto,
            "pe": info.get("trailingPE", 0.0),
            "growth_est": info.get("earningsGrowth", 0.10),
            "eps_next": info.get("forwardEps", 0.0),
            "history": stock.financials.T.head(3) if not stock.financials.empty else None
        }
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return None

data = get_smart_data(ticker_input)

if data:
    # --- METRIKEN KOPFZEILE ---
    st.subheader(f"{data['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Kurs", f"{data['price']:.2f} €")
    c2.metric("FCF (Auto)", f"{data['fcf']:.1f} Mio.")
    c3.metric("Aktien (Auto)", f"{data['shares']:.1f} Mio.")

    # --- SIDEBAR: AUTOMATIK ODER MANUELL ---
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        manual_mode = st.checkbox("Manuelle Korrektur aktivieren")
        
        if manual_mode:
            st.info("Automatik deaktiviert. Gib eigene Werte ein:")
            shares_final = st.number_input("Aktien (Mio.)", value=float(data['shares']))
            fcf_final = st.number_input("Free Cashflow (Mio. €)", value=float(data['fcf']))
        else:
            shares_final = data['shares']
            fcf_final = data['fcf']
            
        st.divider()
        mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100
        growth_slider = st.slider("Wachstum % (DCF)", 0, 40, int(data['growth_est']*100)) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data['pe']) if data['pe'] else 15.0)

    # --- BERECHNUNG ---
    # DCF Logik (Terminal Value mit 9% Abzinsung und 2% ewiges Wachstum)
    val_dcf = ((fcf_final * (1 + growth_slider)) / (0.09 - 0.02)) / shares_final 
    val_kgv = data['eps_next'] * pe_target
    fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
    buy_limit = fair_value * (1 - mos)

    # Grafik
    fig = go.Figure(go.Bar(
        x=['Marktpreis', 'Fairer Wert', 'Kauf-Limit'],
        y=[data['price'], fair_value, buy_limit],
        marker_color=['#636EFA', '#00CC96', '#EF553B']
    ))
    st.plotly_chart(fig, use_container_width=True)

    # Speichern Button
    if st.button("💾 In Datenbank speichern"):
        conn = sqlite3.connect('aktien_daten.db')
        conn.cursor().execute("INSERT INTO analysen (ticker, name, fair_value, buy_limit) VALUES (?, ?, ?, ?)", 
                             (ticker_input, data['name'], round(fair_value, 2), round(buy_limit, 2)))
        conn.commit()
        st.success("Gespeichert!")

# Historie
if st.checkbox("Gespeicherte Analysen zeigen"):
    conn = sqlite3.connect('aktien_daten.db')
    df = pd.read_sql_query("SELECT * FROM analysen", conn)
    st.dataframe(df, use_container_width=True)
    conn = sqlite3.connect('aktien_daten.db')
    df = pd.read_sql_query("SELECT * FROM analysen", conn)
    st.dataframe(df)


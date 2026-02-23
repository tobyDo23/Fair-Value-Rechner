import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# 1. Datenbank-Initialisierung
def init_db():
    conn = sqlite3.connect('aktien_daten_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Aktien-Check Pro", layout="wide")
st.title("🛡️ Aktien-Analyse Terminal (V3)")

# Eingabe-Bereich
ticker_symbol = st.text_input("Börsenkürzel (z.B. AAPL, MSFT, SAP.DE)", "AAPL").upper()

@st.cache_data(ttl=600)
def load_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None
        
        # Basis-Daten mit Sicherheits-Defaults
        return {
            "name": info.get("longName", ticker),
            "price": info.get("currentPrice", 0.0),
            "pe": info.get("trailingPE", 15.0),
            "eps_growth": info.get("earningsGrowth", 0.1),
            "eps_next": info.get("forwardEps", 5.0),
            "shares": info.get("sharesOutstanding", 100000000) / 1_000_000,
            "ebitda_margin": info.get("ebitdaMargins", 0) * 100,
            "financials": stock.financials,
            "cashflow": stock.cashflow
        }
    except:
        return None

data = load_data(ticker_symbol)

if data:
    # --- KOPFZEILE ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preis", f"{data['price']:.2f} €")
    c2.metric("KGV", f"{data['pe']:.1f}")
    c3.metric("EBITDA Marge", f"{data['ebitda_margin']:.1f}%")
    c4.metric("Aktien", f"{data['shares']:.1f} Mio.")

    # --- HISTORIE & PROGNOSEN ---
    st.divider()
    t1, t2 = st.tabs(["📜 Historie (Mio.)", "⚙️ Rechner & Grafik"])

    with t1:
        if not data['financials'].empty:
            try:
                hist_view = data['financials'].loc[['Total Revenue', 'Net Income']].head(3).T
                st.dataframe(hist_view.style.format("{:.2f}"), use_container_width=True)
            except:
                st.info("Detaillierte Historie für diesen Ticker nicht verfügbar.")
        else:
            st.warning("Keine Finanzdaten gefunden.")

    with t2:
        col_calc, col_graph = st.columns([1, 2])
        
        with col_calc:
            st.markdown("### Parameter")
            fcf_in = st.number_input("Free Cashflow (Mio.)", value=100.0)
            growth_in = st.slider("Wachstum %", 0, 40, 10) / 100
            pe_target = st.number_input("Ziel-KGV", value=float(data['pe']) if data['pe'] else 15.0)
            mos = st.slider("Sicherheitsmarge %", 0, 50, 20) / 100

        # Kalkulation (Kombination DCF & KGV)
        val_dcf = ((fcf_in * (1 + growth_in)) / (0.09 - 0.02)) / data['shares']
        val_kgv = data['eps_next'] * pe_target
        fair_value = (val_dcf * 0.5) + (val_kgv * 0.5)
        buy_limit = fair_value * (1 - mos)

        with col_graph:
            fig = go.Figure(go.Bar(
                x=['Marktpreis', 'Fairer Wert', 'Kauf-Limit'],
                y=[data['price'], fair_value, buy_limit],
                marker_color=['#636EFA', '#00CC96', '#EF553B'],
                text=[f"{data['price']:.2f}", f"{fair_value:.2f}", f"{buy_limit:.2f}"],
                textposition='auto'
            ))
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # --- SPEICHERN ---
    if st.button("💾 Analyse speichern"):
        conn = sqlite3.connect('aktien_daten_v3.db')
        conn.cursor().execute("INSERT INTO history (ticker, name, fair_value, buy_limit) VALUES (?,?,?,?)",
                             (ticker_symbol, data['name'], round(fair_value, 2), round(buy_limit, 2)))
        conn.commit()
        st.toast("In Datenbank gesichert!")

else:
    st.error("❌ Ticker nicht gefunden oder Yahoo Finance blockiert die Anfrage. Versuche ein gängiges Kürzel wie AAPL oder MSFT.")

# --- HISTORIE ANZEIGEN ---
st.divider()
if st.checkbox("Zeige gespeicherte Analysen"):
    try:
        conn = sqlite3.connect('aktien_daten_v3.db')
        df_h = pd.read_sql_query("SELECT * FROM history ORDER BY timestamp DESC", conn)
        st.dataframe(df_h, use_container_width=True)
    except:
        st.info("Noch keine Daten gespeichert.")
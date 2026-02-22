import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# 1. Datenbank-Setup (Bleibt gleich)
def init_db():
    conn = sqlite3.connect('aktien_daten.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analysen 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, peg REAL)''')
    conn.commit()
    conn.close()

init_db()

# Seiteneinstellungen
st.set_page_config(page_title="Aktien-Check Ultimate", layout="centered")
st.title("🚀 Aktien-Analyse Terminal")

# 2. Suche und Datenabfrage
ticker_input = st.text_input("Börsenkürzel (z.B. AAPL, MSFT, SAP.DE)", value="AAPL").upper()

@st.cache_data(ttl=3600)
def get_all_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Finanzdaten extrahieren
        return {
            "info": info,
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "pe": info.get("trailingPE", 0.0),
            "growth_est": info.get("earningsGrowth", 0.10),
            "eps_next": info.get("forwardEps", 0.0),
            "history": stock.financials.T.head(3) if not stock.financials.empty else None,
            "recommendations": stock.recommendations.tail(5) if stock.recommendations is not None else None,
            "calendar": stock.calendar
        }
    except:
        return None

data_package = get_all_stock_data(ticker_input)

if data_package:
    # Berechnungen für die Kopfzeile
    peg = data_package['pe'] / (data_package['growth_est'] * 100) if data_package['growth_est'] > 0 else 0
    
    # --- KOPFZEILE ---
    st.subheader(f"Marktdaten: {data_package['name']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Kurs", f"{data_package['price']:.2f} €")
    c2.metric("KGV (Ist)", f"{data_package['pe']:.1f}")
    c3.metric("PEG Ratio", f"{peg:.2f}")

    # --- NEU: ANALYSTEN & HISTORIE BEREICH ---
    st.divider()
    tab1, tab2, tab3 = st.tabs(["🔮 Prognosen", "📜 Historie", "📊 Analysten-Rating"])

    with tab1:
        st.write("**Schätzungen für die Zukunft**")
        # Kalenderdaten zeigen oft das nächste Earnings-Datum und Schätzungen
        if data_package['calendar'] is not None:
            st.dataframe(data_package['calendar'], use_container_width=True)
        else:
            st.info("Keine spezifischen Termindaten verfügbar.")
        
        st.write(f"Erwartetes EPS Wachstum: **{data_package['growth_est']*100:.1f}%**")

    with tab2:
        st.write("**Vergangene 3 Jahre (GuV in Mio.)**")
        if data_package['history'] is not None:
            # Nur wichtige Spalten anzeigen, falls vorhanden
            cols_to_show = ['Total Revenue', 'Net Income', 'Operating Cash Flow']
            existing_cols = [c for c in cols_to_show if c in data_package['history'].columns]
            st.dataframe(data_package['history'][existing_cols], use_container_width=True)
        else:
            st.info("Keine historischen Daten gefunden.")

    with tab3:
        st.write("**Aktuelle Banken-Empfehlungen**")
        if data_package['recommendations'] is not None:
            st.dataframe(data_package['recommendations'], use_container_width=True)
        else:
            st.info("Keine aktuellen Analysten-Ratings verfügbar.")

    # --- ANALYSE-PARAMETER (Sidebar) ---
    with st.sidebar:
        st.header("Analyse-Basis")
        shares = st.number_input("Aktien (Mio.)", value=100.0)
        mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100
        fcf = st.number_input("Free Cashflow (Mio. €)", value=100.0)
        # Automatischer Vorschlag basierend auf Analysten-Wachstum
        growth_slider = st.slider("Wachstum % (DCF)", 0, 40, int(data_package['growth_est']*100)) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data_package['pe']) if data_package['pe'] else 15.0)

    # --- BERECHNUNG & GRAFIK ---
    val_dcf = ((fcf * (1 + growth_slider)) / (0.09 - 0.02)) / shares 
    val_kgv = data_package['eps_next'] * pe_target
    fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
    buy_limit = fair_value * (1 - mos)

    fig = go.Figure(go.Bar(
        x=['Marktpreis', 'Fairer Wert', 'Kauf-Limit'],
        y=[data_package['price'], fair_value, buy_limit],
        marker_color=['#636EFA', '#00CC96', '#EF553B']
    ))
    st.plotly_chart(fig, use_container_width=True)

    # Speichern Button
    if st.button("💾 Analyse dauerhaft speichern"):
        conn = sqlite3.connect('aktien_daten.db')
        conn.cursor().execute("INSERT INTO analysen VALUES (?, ?, ?, ?, ?)", 
                             (ticker_input, data_package['name'], round(fair_value, 2), round(buy_limit, 2), round(peg, 2)))
        conn.commit()
        st.success("Gespeichert!")

# Historie (Checkliste)
st.divider()
if st.checkbox("Historie deiner Analysen anzeigen"):
    conn = sqlite3.connect('aktien_daten.db')
    df = pd.read_sql_query("SELECT * FROM analysen", conn)
    st.dataframe(df)

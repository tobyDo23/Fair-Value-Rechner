import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# 1. Stabile Datenbank-Initialisierung
def init_db():
    conn = sqlite3.connect('aktien_daten.db', check_same_thread=False)
    c = conn.cursor()
    # Wir erstellen die Tabelle mit allen benötigten Spalten von Anfang an
    c.execute('''CREATE TABLE IF NOT EXISTS analysen 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, peg REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Aktien-Check Ultimate", layout="wide")

# Titel und Eingabe
st.title("🚀 Aktien-Analyse Terminal")
ticker_input = st.text_input("Börsenkürzel eingeben (z.B. AAPL, MSFT, SAP.DE)", value="AAPL").upper()

@st.cache_data(ttl=3600)
def get_full_analysis_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Historie & Cashflow
        income = stock.financials
        cashflow = stock.cashflow
        hist_df = pd.DataFrame()
        
        if not income.empty and not cashflow.empty:
            try:
                hist_df['Umsatz'] = income.loc['Total Revenue'] / 1_000_000
                hist_df['Gewinn'] = income.loc['Net Income'] / 1_000_000
                if 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
                    hist_df['FCF'] = (cashflow.loc['Operating Cash Flow'] + cashflow.loc['Capital Expenditure']) / 1_000_000
                hist_df = hist_df.head(3).T
            except: pass

        return {
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "shares": info.get("sharesOutstanding", 1.0) / 1_000_000,
            "pe": info.get("trailingPE", 15.0),
            "eps_next": info.get("forwardEps", 0.0),
            "growth_est": info.get("earningsGrowth", 0.10),
            "hist_table": hist_df,
            "rev_est": stock.revenue_estimate if hasattr(stock, 'revenue_estimate') else None,
            "eps_est": stock.earnings_estimate if hasattr(stock, 'earnings_estimate') else None,
            "margin": info.get("ebitdaMargins", 0) * 100
        }
    except Exception as e:
        st.error(f"Daten für {symbol} konnten nicht geladen werden.")
        return None

data = get_full_analysis_data(ticker_input)

if data:
    # Berechnungen
    growth_val = data['growth_est'] * 100
    peg_ratio = data['pe'] / growth_val if growth_val > 0 else 0

    # Anzeige Metriken
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kurs", f"{data['price']:.2f} €")
    m2.metric("KGV", f"{data['pe']:.1f}")
    m3.metric("PEG Ratio", f"{peg_ratio:.2f}")
    m4.metric("EBITDA Marge", f"{data['margin']:.1f}%")

    # Tabellen Bereich
    st.divider()
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📜 Historie (Mio.)")
        if not data['hist_table'].empty:
            st.dataframe(data['hist_table'], use_container_width=True)
    with col_right:
        st.subheader("🔮 Prognosen")
        if data['rev_est'] is not None:
            st.write("Umsatz Schätzungen")
            st.dataframe(data['rev_est'][['avg', 'low', 'high']].head(2), use_container_width=True)

    # Sidebar & Kalkulation
    with st.sidebar:
        st.header("⚙️ Rechner")
        fcf_in = st.number_input("Free Cashflow (Mio.)", value=float(data['hist_table'].loc['FCF'].iloc[0]) if 'FCF' in data['hist_table'].index else 100.0)
        shares_in = st.number_input("Aktien (Mio.)", value=float(data['shares']))
        growth_in = st.slider("Wachstum %", 0, 40, int(data['growth_est']*100)) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data['pe']))
        mos = st.slider("Sicherheitsmarge %", 0, 50, 20) / 100

    # Fair Value
    val_dcf = ((fcf_in * (1 + growth_in)) / (0.09 - 0.02)) / shares_in 
    val_kgv = data['eps_next'] * pe_target
    fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
    buy_limit = fair_value * (1 - mos)

    # Grafik
    fig = go.Figure(go.Bar(x=['Markt', 'Fair', 'Limit'], y=[data['price'], fair_value, buy_limit], marker_color=['blue', 'green', 'red']))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("💾 Speichern"):
        conn = sqlite3.connect('aktien_daten.db')
        conn.cursor().execute("INSERT INTO analysen (ticker, name, fair_value, buy_limit, peg) VALUES (?, ?, ?, ?, ?)", 
                             (ticker_input, data['name'], round(fair_value, 2), round(buy_limit, 2), round(peg_ratio, 2)))
        conn.commit()
        st.success("Gespeichert!")

# Historie zeigen
st.divider()
if st.checkbox("Analysen-Historie"):
    try:
        conn = sqlite3.connect('aktien_daten.db')
        df_h = pd.read_sql_query("SELECT * FROM analysen ORDER BY timestamp DESC", conn)
        st.dataframe(df_h, use_container_width=True)
    except:
        st.warning("Historie wird nach dem ersten Speichern erstellt.")





import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import sqlite3
import pandas as pd

# 1. Datenbank-Setup (inkl. PEG Spalte)
def init_db():
    conn = sqlite3.connect('aktien_daten.db')
    c = conn.cursor()
    # Wir fügen die PEG Spalte hinzu, falls sie noch nicht existiert
    c.execute('''CREATE TABLE IF NOT EXISTS analysen 
                 (ticker TEXT, name TEXT, fair_value REAL, buy_limit REAL, peg REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Aktien-Check Ultimate", layout="wide")
st.title("📈 Aktien-Analyse Deep-Dive Terminal")

# Suche
ticker_input = st.text_input("Börsenkürzel eingeben (z.B. AAPL, MSFT, SAP.DE)", value="AAPL").upper()

@st.cache_data(ttl=3600)
def get_extended_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # --- HISTORISCHE DATEN (Letzte 3 Jahre) ---
        income = stock.financials
        cashflow = stock.cashflow
        
        hist_df = pd.DataFrame()
        if not income.empty and not cashflow.empty:
            # Daten in Millionen konvertieren
            hist_df['Umsatz'] = income.loc['Total Revenue'] / 1_000_000
            hist_df['Gewinn (Net)'] = income.loc['Net Income'] / 1_000_000
            if 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
                hist_df['Free Cashflow'] = (cashflow.loc['Operating Cash Flow'] + cashflow.loc['Capital Expenditure']) / 1_000_000
            
            # Margen
            hist_df['Gewinnmarge %'] = (hist_df['Gewinn (Net)'] / hist_df['Umsatz']) * 100
            hist_df = hist_df.head(3).T

        # --- PROGNOSEN ---
        rev_est = stock.revenue_estimate if stock.revenue_estimate is not None else pd.DataFrame()
        eps_est = stock.earnings_estimate if stock.earnings_estimate is not None else pd.DataFrame()

        return {
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "shares": info.get("sharesOutstanding", 10.0) / 1_000_000,
            "fcf_auto": hist_df.loc['Free Cashflow'].iloc[0] if 'Free Cashflow' in hist_df.index else 0.0,
            "pe": info.get("trailingPE", 0.0),
            "eps_next": info.get("forwardEps", 0.0),
            "growth_est": info.get("earningsGrowth", 0.10),
            "hist_table": hist_df,
            "rev_est": rev_est,
            "eps_est": eps_est,
            "ebitda_margin": info.get("ebitdaMargins", 0) * 100,
            "div_yield": info.get("dividendYield", 0) * 100
        }
    except Exception as e:
        return None

data = get_extended_stock_data(ticker_input)

if data:
    # PEG Berechnung (KGV / (Wachstum * 100))
    # Wir nutzen das erwartete Gewinnwachstum der Analysten
    growth_val = data['growth_est'] * 100
    peg_ratio = data['pe'] / growth_val if growth_val > 0 else 0

    # --- DASHBOARD KOPFZEILE ---
    st.subheader(f"Analyse: {data['name']}")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Kurs", f"{data['price']:.2f} €")
    m2.metric("KGV", f"{data['pe']:.1f}")
    m3.metric("PEG Ratio", f"{peg_ratio:.2f}", 
              delta="Günstig" if 0 < peg_ratio < 1 else "Teuer", delta_color="inverse")
    m4.metric("EBITDA Marge", f"{data['ebitda_margin']:.1f}%")
    m5.metric("Dividende", f"{data['div_yield']:.2f}%")

    # --- TABELLEN ---
    st.divider()
    col_tables_1, col_tables_2 = st.columns(2)
    
    with col_tables_1:
        st.markdown("### 📜 Historie (Letzte 3 Jahre in Mio.)")
        if not data['hist_table'].empty:
            st.table(data['hist_table'].style.format("{:.2f}"))
        else:
            st.info("Historische Daten nicht verfügbar.")

    with col_tables_2:
        st.markdown("### 🔮 Prognosen")
        if not data['rev_est'].empty:
            st.write("**Umsatz-Schätzungen (Mio.)**")
            st.dataframe(data['rev_est'][['avg', 'low', 'high']], use_container_width=True)
        if not data['eps_est'].empty:
            st.write("**EPS Schätzungen**")
            st.dataframe(data['eps_est'][['avg', 'low', 'high']], use_container_width=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        manual_mode = st.checkbox("Manuelle Korrektur")
        if manual_mode:
            shares_final = st.number_input("Aktien (Mio.)", value=float(data['shares']))
            fcf_final = st.number_input("Free Cashflow (Mio. €)", value=float(data['fcf_auto']))
        else:
            shares_final = data['shares']
            fcf_final = data['fcf_auto']

        st.divider()
        growth = st.slider("Wachstumsrate % (DCF)", 0, 40, int(data['growth_est']*100)) / 100
        wacc = st.slider("Abzinsung %", 5, 15, 9) / 100
        pe_target = st.number_input("Ziel-KGV", value=float(data['pe']) if data['pe'] else 15.0)
        mos = st.slider("Sicherheitsmarge %", 0, 50, 20) / 100

    # --- BERECHNUNG ---
    val_dcf = ((fcf_final * (1 + growth)) / (wacc - 0.02)) / shares_final 
    val_kgv = data['eps_next'] * pe_target
    fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
    buy_limit = fair_value * (1 - mos)

    # GRAFIK
    st.divider()
    fig = go.Figure(go.Bar(
        x=['Marktpreis', 'Fairer Wert', 'Kauf-Limit'],
        y=[data['price'], fair_value, buy_limit],
        marker_color=['#636EFA', '#00CC96', '#EF553B'],
        text=[f"{data['price']:.2f}", f"{fair_value:.2f}", f"{buy_limit:.2f}"],
        textposition='auto'
    ))
    fig.update_layout(title="Bewertungsvergleich (€)", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Speichern
    if st.button("💾 Analyse dauerhaft speichern"):
        conn = sqlite3.connect('aktien_daten.db')
        conn.cursor().execute("INSERT INTO analysen (ticker, name, fair_value, buy_limit, peg) VALUES (?, ?, ?, ?, ?)", 
                             (ticker_input, data['name'], round(fair_value, 2), round(buy_limit, 2), round(peg_ratio, 2)))
        conn.commit()
        st.toast("Gespeichert!")

# Verlauf
if st.checkbox("Zeige gespeicherte Analysen"):
    conn = sqlite3.connect('aktien_daten.db')
    df_hist = pd.read_sql_query("SELECT * FROM analysen ORDER BY timestamp DESC", conn)
    st.dataframe(df_hist, use_container_width=True)




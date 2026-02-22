import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Aktien-Check Pro", layout="centered")

# --- TITEL & SUCHE ---
st.title("🚀 Aktien-Analyse Live")

ticker_input = st.text_input("Gib ein Börsenkürzel ein (z.B. AAPL, MSFT, SAP.DE)", value="AAPL").upper()

# --- LIVE-DATEN LADEN ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0.0),
            "currency": info.get("currency", "EUR")
        }
    except:
        return None

data = get_stock_data(ticker_input)

if data:
    st.success(f"Daten geladen: **{data['name']}**")
    current_price = data['price']
else:
    st.error("Ticker nicht gefunden. Bitte prüfe das Kürzel.")
    current_price = 100.0

# --- EINGABE-SEKTION ---
with st.sidebar:
    st.header("📊 Stammdaten")
    price = st.number_input("Aktueller Kurs", value=float(current_price), key="p")
    shares = st.number_input("Aktien im Umlauf (Mio.)", value=10.0)
    mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100

col1, col2 = st.columns(2)
with col1:
    st.subheader("DCF")
    fcf = st.number_input("Free Cashflow (Mio.)", value=50.0)
    growth = st.slider("Wachstum %", 0, 40, 10) / 100
    wacc = st.slider("Abzinsung %", 5, 15, 9) / 100
with col2:
    st.subheader("Multiples")
    eps = st.number_input("Erwartetes EPS", value=5.0)
    pe_target = st.number_input("Ziel-KGV", value=15.0)

# --- BERECHNUNG ---
total_pv = sum([(fcf * (1 + growth)**t) / (1 + wacc)**t for t in range(1, 6)])
terminal_v = ((fcf * (1 + growth)**5) * 1.02) / (wacc - 0.02)
total_pv += terminal_v / ((1 + wacc) ** 5)
val_dcf = total_pv / shares
val_kgv = eps * pe_target
fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
buy_limit = fair_value * (1 - mos)

# --- GRAFIK ---
fig = go.Figure()
fig.add_trace(go.Bar(
    x=['Aktueller Kurs', 'Fairer Wert', 'Kauf-Limit'],
    y=[price, fair_value, buy_limit],
    marker_color=['#636EFA', '#00CC96', '#EF553B']
))
fig.update_layout(title_text=f"Bewertungsvergleich für {ticker_input}", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)



# --- SPEICHERFUNKTION ---
if 'history' not in st.session_state:
    st.session_state.history = []

if st.button("Analyse speichern"):
    entry = {"Name": ticker_input, "Fair Value": round(fair_value, 2), "Limit": round(buy_limit, 2)}
    st.session_state.history.append(entry)
    st.toast("Gespeichert!")

if st.session_state.history:
    st.divider()
    st.subheader("Deine gespeicherten Analysen")
    st.table(st.session_state.history)

# Grundkonfiguration
st.set_page_config(page_title="Aktien-Check Pro", layout="centered")

st.title("🚀 Aktien Fair Value Rechner")
st.markdown("Kombinierte Analyse aus innerem Wert und Marktbewertung.")

# --- SIDEBAR: Stammdaten ---
with st.sidebar:
    st.header("📊 Stammdaten")
    # Wir geben jedem Widget einen eindeutigen "key", um den Fehler zu vermeiden
    name = st.text_input("Name der Aktie", value="Meine Aktie", key="input_name")
    price = st.number_input("Aktueller Kurs (€)", value=100.0, key="input_price")
    shares = st.number_input("Aktien im Umlauf (Mio.)", value=10.0, key="input_shares")
    
    st.divider()
    st.header("🛡️ Risiko-Puffer")
    mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20, key="input_mos") / 100

# --- HAUPTBEREICH: Parameter ---
st.subheader("Analyse-Parameter")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**DCF (Cashflow)**")
    fcf = st.number_input("Free Cashflow (Mio. €)", value=50.0, key="input_fcf")
    growth = st.slider("Wachstum p.a. (5J) %", 0, 40, 10, key="input_growth") / 100
    wacc = st.slider("Abzinsung %", 5, 15, 9, key="input_wacc") / 100

with col2:
    st.markdown("**KGV (Multiples)**")
    eps = st.number_input("Erwartetes EPS (€)", value=5.0, key="input_eps")
    pe_target = st.number_input("Ziel-KGV", value=15.0, key="input_pe")

# --- BERECHNUNG ---
# 1. DCF Berechnung
total_pv = 0
fcf_temp = fcf
for t in range(1, 6):
    fcf_temp *= (1 + growth)
    total_pv += fcf_temp / ((1 + wacc) ** t)

# Endwert (Terminal Value) - 2% ewiges Wachstum angenommen
terminal_v = (fcf_temp * 1.02) / (wacc - 0.02)
total_pv += terminal_v / ((1 + wacc) ** 5)
val_dcf = total_pv / shares

# 2. KGV Berechnung
val_kgv = eps * pe_target

# 3. Mischwert (60% DCF / 40% KGV)
fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
buy_limit = fair_value * (1 - mos)

# --- AUSGABE ---
st.divider()
c1, c2 = st.columns(2)
c1.metric("Fairer Wert (Mix)", f"{fair_value:.2f} €")
c2.metric("Kauf-Limit (inkl. MoS)", f"{buy_limit:.2f} €")

potential = ((fair_value / price) - 1) * 100

if price < buy_limit:
    st.success(f"✅ UNTERBEWERTET: {name} hat +{potential:.1f}% Potenzial!")
elif price < fair_value:
    st.warning(f"⚠️ FAIR BEWERTET: Kurs liegt nah am fairen Wert.")
else:
    st.error(f"❌ ÜBERBEWERTET: Kurs liegt {abs(potential):.1f}% über dem fairen Wert.")



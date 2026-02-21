import streamlit as st

# Seiteneinstellungen
st.set_page_config(page_title="Aktien-Check Pro", layout="centered")

st.title("🚀 Aktien Fair Value Rechner")
st.info("Kombinierte Analyse: DCF (Zukunft) + KGV (Marktvergleich)")

# --- Eingabe-Sektion ---
with st.sidebar:
    st.header("📊 Stammdaten")
    name = st.text_input("Name der Aktie", "Meine Aktie")
    price = st.number_input("Aktueller Kurs (€)", value=100.0)
    shares = st.number_input("Aktien im Umlauf (Mio.)", value=10.0)
    
    st.divider()
    st.header("🛡️ Risiko-Puffer")
    mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100

st.subheader("Analyse-Parameter")
# ... hier geht es normal weiter mit col1, col2 = st.columns(2)


st.info("Kombinierte Analyse: DCF (Zukunft) + KGV (Marktvergleich)")

# --- Eingabe-Sektion ---
with st.sidebar:
    st.header("📊 Stammdaten")
    name = st.text_input("Name der Aktie", "Meine Aktie")
    price = st.number_input("Aktueller Kurs (€)", value=100.0)
    shares = st.number_input("Aktien im Umlauf (Mio.)", value=10.0)
    
    st.divider()
    st.header("🛡️ Risiko-Puffer")
    mos = st.slider("Sicherheitsmarge (%)", 0, 50, 20) / 100

st.subheader("Analyse-Parameter")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**DCF (Cashflow)**")
    fcf = st.number_input("Free Cashflow (Mio. €)", value=50.0)
    growth = st.slider("Wachstum p.a. (5J) %", 0, 40, 10) / 100
    wacc = st.slider("Abzinsung %", 5, 15, 9) / 100

with col2:
    st.markdown("**KGV (Multiples)**")
    eps = st.number_input("Erwartetes EPS (€)", value=5.0)
    pe_target = st.number_input("Ziel-KGV", value=15.0)

# --- Berechnung ---
# DCF Part
total_pv = 0
fcf_temp = fcf
for t in range(1, 6):
    fcf_temp *= (1 + growth)
    total_pv += fcf_temp / ((1 + wacc) ** t)

terminal_v = (fcf_temp * 1.02) / (wacc - 0.02)
total_pv += terminal_v / ((1 + wacc) ** 5)
val_dcf = total_pv / shares

# KGV Part
val_kgv = eps * pe_target

# Mix (60% DCF / 40% KGV)
fair_value = (val_dcf * 0.6) + (val_kgv * 0.4)
buy_limit = fair_value * (1 - mos)

# --- Ergebnis-Display ---
st.divider()
c1, c2 = st.columns(2)
c1.metric("Fairer Wert (Mix)", f"{fair_value:.2f} €")
c2.metric("Kauf-Limit (inkl. MoS)", f"{buy_limit:.2f} €")

if price < buy_limit:
    st.success(f"✅ UNTERBEWERTET: {name} ist aktuell ein Schnäppchen!")
    st.balloons()
elif price < fair_value:
    st.warning("⚠️ FAIR BEWERTET: Kein großer Puffer vorhanden.")
else:
    st.error("❌ ÜBERBEWERTET: Der Preis ist zu hoch.")

# Visualisierung
potential = ((fair_value / price) - 1) * 100

st.write(f"Das theoretische Potenzial zum fairen Wert beträgt **{potential:.1f}%**.")


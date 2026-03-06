import streamlit as st
import requests
from datetime import datetime

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background-color: #0f0f14;
    color: #f0ede8;
}

.hero {
    background: linear-gradient(135deg, #f7c948 0%, #f4a623 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem 2rem 2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "🚕";
    font-size: 9rem;
    position: absolute;
    right: -10px;
    top: -10px;
    opacity: 0.18;
    line-height: 1;
}
.hero h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.6rem;
    color: #0f0f14;
    margin: 0 0 0.4rem 0;
    line-height: 1.1;
}
.hero p {
    color: #3a2e00;
    font-size: 1rem;
    margin: 0;
}

.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #f7c948;
    margin-bottom: 0.5rem;
    margin-top: 1.8rem;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background-color: #1a1a24 !important;
    border: 1px solid #2a2a38 !important;
    border-radius: 10px !important;
    color: #f0ede8 !important;
}

/* Slider */
div[data-testid="stSlider"] div[role="slider"] {
    background: #f7c948 !important;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #f7c948, #f4a623);
    color: #0f0f14;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    border: none;
    border-radius: 12px;
    padding: 0.75rem 2.5rem;
    width: 100%;
    letter-spacing: 0.04em;
    margin-top: 1rem;
}
.stButton > button:hover {
    opacity: 0.85;
}

.result-box {
    background: linear-gradient(135deg, #1e2a1a, #162213);
    border: 1px solid #3a5c30;
    border-radius: 16px;
    padding: 1.8rem;
    text-align: center;
    margin-top: 1.2rem;
}
.result-box .amount {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    color: #7ed957;
    line-height: 1;
}
.result-box .sublabel {
    color: #5a8a50;
    font-size: 0.85rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 0.4rem;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>NYC Taxi Fare<br>Estimator</h1>
    <p>Instant fare prediction powered by machine learning</p>
</div>
""", unsafe_allow_html=True)

# ── Date & Time ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">⏰ Date & Time</div>', unsafe_allow_html=True)
pickup_datetime = st.text_input(
    "Pickup date and time (YYYY-MM-DD HH:MM:SS)",
    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

# ── Locations ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">📍 Pickup Location</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2, gap="medium")
with col1:
    pickup_latitude  = st.number_input("Pickup Latitude",  value=40.748817,  format="%.6f", key="plat")
with col2:
    pickup_longitude = st.number_input("Pickup Longitude", value=-73.985428, format="%.6f", key="plon")

st.markdown('<div class="section-label">🏁 Dropoff Location</div>', unsafe_allow_html=True)
col3, col4 = st.columns(2, gap="medium")
with col3:
    dropoff_latitude  = st.number_input("Dropoff Latitude",  value=40.763015,  format="%.6f", key="dlat")
with col4:
    dropoff_longitude = st.number_input("Dropoff Longitude", value=-73.979570, format="%.6f", key="dlon")

# ── Passengers ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">👥 Passengers</div>', unsafe_allow_html=True)
passenger_count = st.slider("Number of passengers", min_value=1, max_value=8, value=1)

# ── Prediction ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">🔮 Prediction</div>', unsafe_allow_html=True)

url = 'https://taxifare.lewagon.ai/predict'

if url == 'https://taxifare.lewagon.ai/predict':
    st.info("💡 You can swap the URL above to use your own trained model API.")

if st.button("Predict Fare →"):
    params = {
        "pickup_datetime":   pickup_datetime,
        "pickup_longitude":  pickup_longitude,
        "pickup_latitude":   pickup_latitude,
        "dropoff_longitude": dropoff_longitude,
        "dropoff_latitude":  dropoff_latitude,
        "passenger_count":   passenger_count,
    }

    with st.spinner("Calling the API..."):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            prediction = data.get("fare", data.get("fare_amount", None))

            if prediction is not None:
                st.markdown(f"""
                <div class="result-box">
                    <div class="amount">${prediction:.2f}</div>
                    <div class="sublabel">Estimated fare</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Unexpected API response format.")
                st.json(data)

        except requests.exceptions.RequestException as e:
            st.error(f"API call failed: {e}")

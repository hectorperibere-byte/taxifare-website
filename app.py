import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NYC Taxi Fare", page_icon="🚕", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background-color: #f8f9fb; }

section[data-testid="stSidebar"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* All inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #fff !important;
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 10px !important;
    color: #111 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 0.8rem !important;
    transition: border 0.2s;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: #f7c948 !important;
    box-shadow: 0 0 0 3px rgba(247,201,72,0.15) !important;
}

/* Labels */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: #666 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Slider */
div[data-testid="stSlider"] > div > div > div > div {
    background: #f7c948 !important;
}

/* Button */
.stButton > button {
    background: #111 !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
    transition: background 0.2s !important;
}
.stButton > button:hover {
    background: #333 !important;
}

hr { border: none; border-top: 1.5px solid #ececec; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🚕 NYC Taxi Fare Estimator")
st.markdown("<p style='color:#888; margin-top:-0.5rem; margin-bottom:1.5rem;'>Enter your ride details to get an instant fare estimate.</p>", unsafe_allow_html=True)

# ── Date & Time ───────────────────────────────────────────────────────────────
pickup_datetime = st.text_input(
    "Pickup date & time",
    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    placeholder="YYYY-MM-DD HH:MM:SS"
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Pickup ────────────────────────────────────────────────────────────────────
st.markdown("<p style='font-weight:600; color:#111; margin-bottom:0.5rem;'>📍 Pickup</p>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    pickup_latitude  = st.number_input("Latitude",  value=40.748817,  format="%.6f", key="plat")
with c2:
    pickup_longitude = st.number_input("Longitude", value=-73.985428, format="%.6f", key="plon")

st.markdown("<br>", unsafe_allow_html=True)

# ── Dropoff ───────────────────────────────────────────────────────────────────
st.markdown("<p style='font-weight:600; color:#111; margin-bottom:0.5rem;'>🏁 Dropoff</p>", unsafe_allow_html=True)
c3, c4 = st.columns(2)
with c3:
    dropoff_latitude  = st.number_input("Latitude",  value=40.763015,  format="%.6f", key="dlat")
with c4:
    dropoff_longitude = st.number_input("Longitude", value=-73.979570, format="%.6f", key="dlon")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────────────
st.markdown("<p style='font-weight:600; color:#111; margin-bottom:0.8rem;'>🗺️ Route preview</p>", unsafe_allow_html=True)

midpoint_lat = (pickup_latitude + dropoff_latitude) / 2
midpoint_lon = (pickup_longitude + dropoff_longitude) / 2

# Line layer (route)
line_layer = pdk.Layer(
    "LineLayer",
    data=pd.DataFrame([{
        "start_lon": pickup_longitude,
        "start_lat": pickup_latitude,
        "end_lon":   dropoff_longitude,
        "end_lat":   dropoff_latitude,
    }]),
    get_source_position=["start_lon", "start_lat"],
    get_target_position=["end_lon",   "end_lat"],
    get_color=[247, 201, 72, 220],
    get_width=4,
)

# Scatter layer (pickup = green, dropoff = red)
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([
        {"lon": pickup_longitude,  "lat": pickup_latitude,  "color": [34, 197, 94],  "label": "Pickup"},
        {"lon": dropoff_longitude, "lat": dropoff_latitude, "color": [239, 68, 68],  "label": "Dropoff"},
    ]),
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius=80,
    pickable=True,
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v10",
    initial_view_state=pdk.ViewState(
        latitude=midpoint_lat,
        longitude=midpoint_lon,
        zoom=12,
        pitch=0,
    ),
    layers=[line_layer, scatter_layer],
    tooltip={"text": "{label}"},
), use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Passengers ────────────────────────────────────────────────────────────────
passenger_count = st.slider("👥 Passengers", min_value=1, max_value=8, value=1)

st.markdown("<br>", unsafe_allow_html=True)

# ── Predict ───────────────────────────────────────────────────────────────────
url = 'https://taxifare-294990428867.europe-west9.run.app'

if st.button("Get Fare Estimate →"):
    params = {
        "pickup_datetime":   pickup_datetime,
        "pickup_latitude":   pickup_latitude,
        "pickup_longitude":  pickup_longitude,
        "dropoff_latitude":  dropoff_latitude,
        "dropoff_longitude": dropoff_longitude,
        "passenger_count":   passenger_count,
    }

    with st.spinner("Fetching prediction..."):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            prediction = data.get("fare", data.get("fare_amount", None))

            if prediction is not None:
                st.markdown(f"""
                <div style="
                    background:#fff;
                    border:1.5px solid #e0e0e0;
                    border-radius:16px;
                    padding:2rem;
                    text-align:center;
                    margin-top:1rem;
                ">
                    <div style="font-size:0.75rem; font-weight:600; letter-spacing:0.12em; text-transform:uppercase; color:#888; margin-bottom:0.5rem;">Estimated Fare</div>
                    <div style="font-size:3rem; font-weight:700; color:#111;">${prediction:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Unexpected API response.")
                st.json(data)

        except requests.exceptions.RequestException as e:
            st.error(f"API error: {e}")

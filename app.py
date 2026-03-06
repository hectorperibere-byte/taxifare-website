import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NYC Taxi Fare", page_icon="🚕", layout="centered")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background-color: #f5f5f7; }
#MainMenu, footer, header { visibility: hidden; }

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #ffffff !important;
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 10px !important;
    color: #111 !important;
    font-size: 0.95rem !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: #f7c948 !important;
    box-shadow: 0 0 0 3px rgba(247,201,72,0.2) !important;
}

/* Labels */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #888 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Slider track */
div[data-testid="stSlider"] > div > div > div > div {
    background: #f7c948 !important;
}

/* Button */
.stButton > button {
    background: #111 !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.8rem 1.5rem !important;
    width: 100% !important;
    letter-spacing: 0.02em;
    transition: background 0.2s !important;
}
.stButton > button:hover { background: #333 !important; }

hr { border: none; border-top: 1.5px solid #e8e8e8; margin: 1.4rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 2rem 0 0.5rem 0;">
  <div style="font-size:2rem; font-weight:700; color:#111; line-height:1.2;">🚕 NYC Taxi Fare</div>
  <div style="color:#999; font-size:0.95rem; margin-top:0.3rem;">Instant fare estimate based on your route</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Date & Time ───────────────────────────────────────────────────────────────
pickup_datetime = st.text_input(
    "Pickup date & time",
    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    placeholder="YYYY-MM-DD HH:MM:SS"
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Pickup coordinates ────────────────────────────────────────────────────────
st.markdown("<p style='font-size:0.78rem; font-weight:600; color:#888; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.5rem;'>📍 Pickup</p>", unsafe_allow_html=True)
col1, col2 = st.columns(2, gap="medium")
with col1:
    pickup_latitude  = st.number_input("Latitude",  value=40.748817,  format="%.6f", key="plat")
with col2:
    pickup_longitude = st.number_input("Longitude", value=-73.985428, format="%.6f", key="plon")

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

# ── Dropoff coordinates ───────────────────────────────────────────────────────
st.markdown("<p style='font-size:0.78rem; font-weight:600; color:#888; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.5rem;'>🏁 Dropoff</p>", unsafe_allow_html=True)
col3, col4 = st.columns(2, gap="medium")
with col3:
    dropoff_latitude  = st.number_input("Latitude",  value=40.763015,  format="%.6f", key="dlat")
with col4:
    dropoff_longitude = st.number_input("Longitude", value=-73.979570, format="%.6f", key="dlon")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────────────
st.markdown("<p style='font-size:0.78rem; font-weight:600; color:#888; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.8rem;'>🗺️ Route preview</p>", unsafe_allow_html=True)

mid_lat = (pickup_latitude + dropoff_latitude) / 2
mid_lon = (pickup_longitude + dropoff_longitude) / 2

route_layer = pdk.Layer(
    "LineLayer",
    data=pd.DataFrame([{
        "sx": pickup_longitude, "sy": pickup_latitude,
        "ex": dropoff_longitude, "ey": dropoff_latitude,
    }]),
    get_source_position=["sx", "sy"],
    get_target_position=["ex", "ey"],
    get_color=[247, 201, 72, 255],
    get_width=5,
    width_min_pixels=3,
)

dots_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pd.DataFrame([
        {"lon": pickup_longitude,  "lat": pickup_latitude,  "color": [34, 197, 94, 255],  "name": "Pickup"},
        {"lon": dropoff_longitude, "lat": dropoff_latitude, "color": [239, 68, 68, 255],   "name": "Dropoff"},
    ]),
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius=120,
    pickable=True,
)

st.pydeck_chart(
    pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",
        initial_view_state=pdk.ViewState(
            latitude=mid_lat,
            longitude=mid_lon,
            zoom=12.5,
            pitch=0,
        ),
        layers=[route_layer, dots_layer],
        tooltip={"text": "{name}"},
    ),
    use_container_width=True,
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Passengers ────────────────────────────────────────────────────────────────
passenger_count = st.slider("👥 Number of passengers", min_value=1, max_value=8, value=1)

st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)

# ── Predict ───────────────────────────────────────────────────────────────────
url = "https://taxifare.lewagon.ai/predict"

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
            prediction = data.get("fare", data.get("fare_amount"))

            if prediction is not None:
                st.markdown(f"""
                <div style="
                    background: #fff;
                    border: 1.5px solid #e0e0e0;
                    border-radius: 16px;
                    padding: 2.2rem 1.5rem;
                    text-align: center;
                    margin-top: 1rem;
                ">
                    <div style="font-size:0.72rem; font-weight:600; letter-spacing:0.14em;
                                text-transform:uppercase; color:#aaa; margin-bottom:0.6rem;">
                        Estimated Fare
                    </div>
                    <div style="font-size:3.4rem; font-weight:700; color:#111; line-height:1;">
                        ${prediction:.2f}
                    </div>
                    <div style="font-size:0.82rem; color:#bbb; margin-top:0.6rem;">
                        {passenger_count} passenger{"s" if passenger_count > 1 else ""} &nbsp;·&nbsp; NYC Taxi
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Unexpected API response format.")
                st.json(data)

        except requests.exceptions.RequestException as e:
            st.error(f"API error: {e}")

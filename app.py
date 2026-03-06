import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NYC Taxi Fare", page_icon="🚕", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0c0c0e;
    color: #f2f0eb;
}
.stApp { background-color: #0c0c0e; }
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 2.5rem 3rem 3rem 3rem !important;
    max-width: 1300px !important;
}
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3rem;
    color: #f2f0eb;
    line-height: 1.1;
    margin-bottom: 0.4rem;
}
.hero-sub { font-size: 1rem; color: #555; font-weight: 300; }
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #e8b84b;
    margin-bottom: 0.6rem;
    margin-top: 1.4rem;
}
.divider { border: none; border-top: 1px solid #1e1e28; margin: 1.2rem 0; }

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #17171c !important;
    border: 1px solid #2a2a35 !important;
    border-radius: 10px !important;
    color: #f2f0eb !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: #e8b84b !important;
    box-shadow: 0 0 0 3px rgba(232,184,75,0.12) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #555 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
div[data-testid="stButton"] > button {
    background: #e8b84b !important;
    color: #0c0c0e !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.8rem 2rem !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover { opacity: 0.85 !important; }

.result-card {
    background: #17171c;
    border: 1px solid #2a2a35;
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    margin-top: 1.2rem;
}
.result-fare {
    font-family: 'DM Serif Display', serif;
    font-size: 4rem;
    color: #e8b84b;
    line-height: 1;
}
.result-meta { font-size: 0.82rem; color: #444; margin-top: 0.6rem; }
</style>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.6], gap="large")

with left:
    st.markdown("""
    <div style="padding-bottom:0.8rem">
        <div class="hero-title">NYC Taxi<br>Fare Estimator</div>
        <div class="hero-sub">Predict your fare before you ride</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">⏰ Date & Time</div>', unsafe_allow_html=True)
    pickup_datetime = st.text_input(
        "datetime", label_visibility="collapsed",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        placeholder="YYYY-MM-DD HH:MM:SS"
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">📍 Pickup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        pickup_lat = st.number_input("Lat", value=40.748817, format="%.6f", key="plat")
    with c2:
        pickup_lon = st.number_input("Lon", value=-73.985428, format="%.6f", key="plon")

    st.markdown('<div class="section-label">🏁 Dropoff</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        dropoff_lat = st.number_input("Lat", value=40.763015, format="%.6f", key="dlat")
    with c4:
        dropoff_lon = st.number_input("Lon", value=-73.979570, format="%.6f", key="dlon")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.slider("", min_value=1, max_value=8, value=1, label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)

    url = "https://taxifare.lewagon.ai/predict"
    predict = st.button("Estimate Fare →")

    if predict:
        params = {
            "pickup_datetime":   pickup_datetime,
            "pickup_latitude":   pickup_lat,
            "pickup_longitude":  pickup_lon,
            "dropoff_latitude":  dropoff_lat,
            "dropoff_longitude": dropoff_lon,
            "passenger_count":   passenger_count,
        }
        with st.spinner(""):
            try:
                r = requests.get(url, params=params)
                r.raise_for_status()
                data = r.json()
                pred = data.get("fare", data.get("fare_amount"))
                if pred is not None:
                    pax = f"{passenger_count} passenger{'s' if passenger_count > 1 else ''}"
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.16em;
                                    text-transform:uppercase;color:#444;margin-bottom:0.5rem;">
                            Estimated Fare
                        </div>
                        <div class="result-fare">${pred:.2f}</div>
                        <div class="result-meta">{pax} &nbsp;·&nbsp; New York City</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Unexpected response.")
                    st.json(data)
            except requests.exceptions.RequestException as e:
                st.error(f"API error: {e}")

# ── Map ───────────────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="section-label" style="margin-top:0">🗺️ Route</div>', unsafe_allow_html=True)

    mid_lat = (pickup_lat + dropoff_lat) / 2
    mid_lon = (pickup_lon + dropoff_lon) / 2

    # Route line — flat 2D
    line_layer = pdk.Layer(
        "PathLayer",
        data=pd.DataFrame([{
            "path": [
                [pickup_lon, pickup_lat],
                [dropoff_lon, dropoff_lat],
            ]
        }]),
        get_path="path",
        get_color=[232, 184, 75, 255],
        get_width=6,
        width_min_pixels=4,
        pickable=False,
    )

    # Pickup dot
    pickup_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lon": pickup_lon, "lat": pickup_lat, "label": "Pickup"}]),
        get_position=["lon", "lat"],
        get_fill_color=[34, 197, 94, 255],
        get_line_color=[255, 255, 255, 200],
        get_radius=100,
        stroked=True,
        line_width_min_pixels=3,
        pickable=True,
    )

    # Dropoff dot
    dropoff_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lon": dropoff_lon, "lat": dropoff_lat, "label": "Dropoff"}]),
        get_position=["lon", "lat"],
        get_fill_color=[239, 68, 68, 255],
        get_line_color=[255, 255, 255, 200],
        get_radius=100,
        stroked=True,
        line_width_min_pixels=3,
        pickable=True,
    )

    deck = pdk.Deck(
        layers=[line_layer, pickup_layer, dropoff_layer],
        initial_view_state=pdk.ViewState(
            latitude=mid_lat,
            longitude=mid_lon,
            zoom=12,
            pitch=0,      # ← flat 2D, no tilt
            bearing=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "{label}"},
    )

    st.pydeck_chart(deck, use_container_width=True, height=580)

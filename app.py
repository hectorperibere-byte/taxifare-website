import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(page_title="NYC Taxi Fare", page_icon="🚕", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0c0c0e;
    color: #f2f0eb;
}

.stApp { background-color: #0c0c0e; }
#MainMenu, footer, header { visibility: hidden; }

/* Page layout */
.block-container {
    padding: 2.5rem 3rem 3rem 3rem !important;
    max-width: 1200px !important;
}

/* Hero */
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    color: #f2f0eb;
    line-height: 1.1;
    margin-bottom: 0.4rem;
}
.hero-sub {
    font-size: 1rem;
    color: #666;
    font-weight: 300;
    letter-spacing: 0.02em;
}

/* Section label */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #e8b84b;
    margin-bottom: 0.7rem;
    margin-top: 1.6rem;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #17171c !important;
    border: 1px solid #2a2a35 !important;
    border-radius: 10px !important;
    color: #f2f0eb !important;
    font-size: 0.92rem !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: #e8b84b !important;
    box-shadow: 0 0 0 3px rgba(232,184,75,0.12) !important;
}

/* Input labels */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #555 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

/* Number input buttons */
div[data-testid="stNumberInput"] button {
    background: #1e1e28 !important;
    border-color: #2a2a35 !important;
    color: #888 !important;
}

/* Slider */
div[data-testid="stSlider"] > div > div > div > div {
    background: #e8b84b !important;
}
div[data-testid="stSlider"] .st-emotion-cache-1dp5vir {
    background: #e8b84b !important;
}

/* Button */
div[data-testid="stButton"] > button {
    background: #e8b84b !important;
    color: #0c0c0e !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.8rem 2rem !important;
    width: 100% !important;
    letter-spacing: 0.03em;
    transition: opacity 0.2s, transform 0.1s !important;
}
div[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid #1e1e28;
    margin: 1.4rem 0;
}

/* Result card */
.result-card {
    background: linear-gradient(145deg, #17171c, #1a1a22);
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
.result-meta {
    font-size: 0.82rem;
    color: #444;
    margin-top: 0.7rem;
    letter-spacing: 0.04em;
}

/* Info box */
div[data-testid="stInfo"] {
    background: #17171c !important;
    border: 1px solid #2a2a35 !important;
    border-radius: 10px !important;
    color: #666 !important;
    font-size: 0.82rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Layout: 2 columns (form left, map right) ──────────────────────────────────
left, right = st.columns([1, 1.4], gap="large")

with left:
    # Hero
    st.markdown("""
    <div style="padding-bottom: 1rem;">
        <div class="hero-title">NYC Taxi<br>Fare Estimator</div>
        <div class="hero-sub">Predict your fare before you ride</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Date & time
    st.markdown('<div class="section-label">⏰ Date & Time</div>', unsafe_allow_html=True)
    pickup_datetime = st.text_input(
        "Pickup datetime",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        label_visibility="collapsed",
        placeholder="YYYY-MM-DD HH:MM:SS"
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Pickup
    st.markdown('<div class="section-label">📍 Pickup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        pickup_lat = st.number_input("Lat", value=40.748817, format="%.6f", key="plat", label_visibility="visible")
    with c2:
        pickup_lon = st.number_input("Lon", value=-73.985428, format="%.6f", key="plon", label_visibility="visible")

    # Dropoff
    st.markdown('<div class="section-label">🏁 Dropoff</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        dropoff_lat = st.number_input("Lat", value=40.763015, format="%.6f", key="dlat", label_visibility="visible")
    with c4:
        dropoff_lon = st.number_input("Lon", value=-73.979570, format="%.6f", key="dlon", label_visibility="visible")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Passengers
    st.markdown('<div class="section-label">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.slider("", min_value=1, max_value=8, value=1, label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)

    # Predict button
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
                    pax_label = f"{passenger_count} passenger{'s' if passenger_count > 1 else ''}"
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="font-size:0.68rem; font-weight:600; letter-spacing:0.16em;
                                    text-transform:uppercase; color:#444; margin-bottom:0.6rem;">
                            Estimated Fare
                        </div>
                        <div class="result-fare">${pred:.2f}</div>
                        <div class="result-meta">{pax_label} &nbsp;·&nbsp; New York City</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Unexpected response from API.")
                    st.json(data)
            except requests.exceptions.RequestException as e:
                st.error(f"API error: {e}")

# ── Map (right column) ────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="section-label" style="margin-top:0">🗺️ Route Map</div>', unsafe_allow_html=True)

    mid_lat = (pickup_lat + dropoff_lat) / 2
    mid_lon = (pickup_lon + dropoff_lon) / 2

    m = folium.Map(
        location=[mid_lat, mid_lon],
        zoom_start=13,
        tiles="CartoDB dark_matter",
    )

    # Route line
    folium.PolyLine(
        locations=[
            [pickup_lat, pickup_lon],
            [dropoff_lat, dropoff_lon],
        ],
        color="#e8b84b",
        weight=4,
        opacity=0.9,
        dash_array=None,
    ).add_to(m)

    # Pickup marker (green)
    folium.CircleMarker(
        location=[pickup_lat, pickup_lon],
        radius=10,
        color="#22c55e",
        fill=True,
        fill_color="#22c55e",
        fill_opacity=1,
        tooltip="📍 Pickup",
    ).add_to(m)

    # Dropoff marker (red)
    folium.CircleMarker(
        location=[dropoff_lat, dropoff_lon],
        radius=10,
        color="#ef4444",
        fill=True,
        fill_color="#ef4444",
        fill_opacity=1,
        tooltip="🏁 Dropoff",
    ).add_to(m)

    st_folium(m, width=None, height=560, returned_objects=[])

import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime
import time
from geopy.geocoders import Nominatim

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

/* Date picker */
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #17171c !important;
    border: 1px solid #2a2a35 !important;
    border-radius: 10px !important;
    color: #f2f0eb !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTimeInput"] input:focus,
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
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.8rem 2rem !important;
    width: 100% !important;
    letter-spacing: 0.03em;
}
div[data-testid="stButton"] > button:hover { opacity: 0.85 !important; }

/* F1 animation overlay */
.f1-overlay {
    position: fixed;
    inset: 0;
    background: #0c0c0e;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'DM Sans', sans-serif;
}

.f1-track {
    position: relative;
    width: 340px;
    height: 220px;
    margin-bottom: 2rem;
}

.f1-track svg {
    width: 100%;
    height: 100%;
}

.f1-car {
    position: absolute;
    font-size: 1.6rem;
    animation: drive 1.8s linear infinite;
    offset-path: path('M 60 110 C 60 50, 140 20, 200 40 C 260 60, 300 80, 300 110 C 300 145, 260 170, 200 175 C 140 180, 60 170, 60 110');
    offset-rotate: auto;
}

@keyframes drive {
    0%   { offset-distance: 0%; }
    100% { offset-distance: 100%; }
}

.f1-label {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: #e8b84b;
    margin-bottom: 0.5rem;
    animation: pulse 0.8s ease-in-out infinite alternate;
}
@keyframes pulse {
    from { opacity: 0.6; }
    to   { opacity: 1; }
}

.f1-sub {
    font-size: 0.85rem;
    color: #444;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

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

# ── Geocoding helper ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def geocode(address: str):
    """Return (lat, lon) for a given address string, biased to NYC."""
    geolocator = Nominatim(user_agent="nyc_taxi_fare_app")
    location = geolocator.geocode(f"{address}, New York City, NY", timeout=10)
    if location:
        return location.latitude, location.longitude
    return None, None

# ── Session state ─────────────────────────────────────────────────────────────
if "show_f1" not in st.session_state:
    st.session_state.show_f1 = False
if "fare_result" not in st.session_state:
    st.session_state.fare_result = None

# ── F1 Animation (full screen overlay) ───────────────────────────────────────
if st.session_state.show_f1:
    st.markdown("""
    <div class="f1-overlay" id="f1overlay">
        <div class="f1-label">Calculating your fare...</div>
        <div class="f1-track">
            <svg viewBox="0 0 360 220" fill="none" xmlns="http://www.w3.org/2000/svg">
                <!-- Track background -->
                <ellipse cx="180" cy="110" rx="140" ry="75" stroke="#2a2a35" stroke-width="28" fill="none"/>
                <!-- Track surface -->
                <ellipse cx="180" cy="110" rx="140" ry="75" stroke="#1e1e28" stroke-width="24" fill="none"/>
                <!-- Track lines -->
                <ellipse cx="180" cy="110" rx="140" ry="75" stroke="#2d2d3a" stroke-width="1" fill="none" stroke-dasharray="8 6"/>
                <!-- Start/finish line -->
                <line x1="40" y1="100" x2="40" y2="120" stroke="#e8b84b" stroke-width="3"/>
                <!-- Sector marks -->
                <line x1="290" y1="75" x2="305" y2="65" stroke="#555" stroke-width="2"/>
                <line x1="290" y1="145" x2="305" y2="155" stroke="#555" stroke-width="2"/>
            </svg>
            <div class="f1-car">🏎️</div>
        </div>
        <div class="f1-sub">NYC Grand Prix</div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(4)
    st.session_state.show_f1 = False
    st.rerun()

# ── Main UI ───────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.6], gap="large")

with left:
    st.markdown("""
    <div style="padding-bottom:0.8rem">
        <div class="hero-title">NYC Taxi<br>Fare Estimator</div>
        <div class="hero-sub">Predict your fare before you ride</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Date & time with calendar
    st.markdown('<div class="section-label">⏰ Date & Time</div>', unsafe_allow_html=True)
    col_d, col_t = st.columns(2)
    with col_d:
        pickup_date = st.date_input("Date", value=datetime.now().date(), label_visibility="collapsed")
    with col_t:
        pickup_time = st.time_input("Time", value=datetime.now().time(), label_visibility="collapsed", step=60)

    pickup_datetime = f"{pickup_date} {pickup_time}"

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Pickup address
    st.markdown('<div class="section-label">📍 Pickup Address</div>', unsafe_allow_html=True)
    pickup_address = st.text_input("pickup", label_visibility="collapsed",
                                   placeholder="e.g. Empire State Building, Manhattan")

    # Dropoff address
    st.markdown('<div class="section-label">🏁 Dropoff Address</div>', unsafe_allow_html=True)
    dropoff_address = st.text_input("dropoff", label_visibility="collapsed",
                                    placeholder="e.g. JFK Airport, Queens")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Passengers — number input
    st.markdown('<div class="section-label">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.number_input("Passengers", min_value=1, max_value=8, value=1,
                                      label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)

    predict = st.button("Estimate Fare →")

    if predict:
        if not pickup_address or not dropoff_address:
            st.error("Please enter both pickup and dropoff addresses.")
        else:
            with st.spinner("Geocoding addresses..."):
                pickup_lat, pickup_lon   = geocode(pickup_address)
                dropoff_lat, dropoff_lon = geocode(dropoff_address)

            if pickup_lat is None:
                st.error(f"Could not find: **{pickup_address}**. Try a more specific address.")
            elif dropoff_lat is None:
                st.error(f"Could not find: **{dropoff_address}**. Try a more specific address.")
            else:
                params = {
                    "pickup_datetime":   pickup_datetime,
                    "pickup_latitude":   pickup_lat,
                    "pickup_longitude":  pickup_lon,
                    "dropoff_latitude":  dropoff_lat,
                    "dropoff_longitude": dropoff_lon,
                    "passenger_count":   int(passenger_count),
                }
                try:
                    r = requests.get("https://taxifare.lewagon.ai/predict", params=params)
                    r.raise_for_status()
                    data = r.json()
                    pred = data.get("fare", data.get("fare_amount"))
                    if pred is not None:
                        st.session_state.fare_result = {
                            "pred": pred,
                            "pax": int(passenger_count),
                            "pickup_lat": pickup_lat,
                            "pickup_lon": pickup_lon,
                            "dropoff_lat": dropoff_lat,
                            "dropoff_lon": dropoff_lon,
                            "pickup_address": pickup_address,
                            "dropoff_address": dropoff_address,
                        }
                        st.session_state.show_f1 = True
                        st.rerun()
                    else:
                        st.error("Unexpected response.")
                        st.json(data)
                except requests.exceptions.RequestException as e:
                    st.error(f"API error: {e}")

    # Show result
    if st.session_state.fare_result and not st.session_state.show_f1:
        res = st.session_state.fare_result
        pax = f"{res['pax']} passenger{'s' if res['pax'] > 1 else ''}"
        st.markdown(f"""
        <div class="result-card">
            <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.16em;
                        text-transform:uppercase;color:#444;margin-bottom:0.5rem;">
                Estimated Fare
            </div>
            <div class="result-fare">${res['pred']:.2f}</div>
            <div class="result-meta">{pax} &nbsp;·&nbsp; New York City</div>
        </div>
        """, unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="section-label" style="margin-top:0">🗺️ Route</div>', unsafe_allow_html=True)

    # Defaults when no result yet
    if st.session_state.fare_result:
        r = st.session_state.fare_result
        plat, plon = r["pickup_lat"], r["pickup_lon"]
        dlat, dlon = r["dropoff_lat"], r["dropoff_lon"]
    else:
        plat, plon = 40.748817, -73.985428
        dlat, dlon = 40.763015, -73.979570

    mid_lat = (plat + dlat) / 2
    mid_lon = (plon + dlon) / 2

    line_layer = pdk.Layer(
        "PathLayer",
        data=pd.DataFrame([{"path": [[plon, plat], [dlon, dlat]]}]),
        get_path="path",
        get_color=[232, 184, 75, 255],
        get_width=6,
        width_min_pixels=4,
    )
    pickup_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lon": plon, "lat": plat, "label": "📍 Pickup"}]),
        get_position=["lon", "lat"],
        get_fill_color=[34, 197, 94, 255],
        get_line_color=[255, 255, 255, 200],
        get_radius=100,
        stroked=True,
        line_width_min_pixels=3,
        pickable=True,
    )
    dropoff_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lon": dlon, "lat": dlat, "label": "🏁 Dropoff"}]),
        get_position=["lon", "lat"],
        get_fill_color=[239, 68, 68, 255],
        get_line_color=[255, 255, 255, 200],
        get_radius=100,
        stroked=True,
        line_width_min_pixels=3,
        pickable=True,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[line_layer, pickup_layer, dropoff_layer],
        initial_view_state=pdk.ViewState(
            latitude=mid_lat, longitude=mid_lon,
            zoom=12, pitch=0, bearing=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "{label}"},
    ), use_container_width=True, height=580)

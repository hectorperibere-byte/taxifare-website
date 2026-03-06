import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

st.set_page_config(page_title="NYC TAXI FARE", page_icon="🏎️", layout="wide")

# ── FULL CSS + ANIMATIONS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #08080a;
    color: #f0ede8;
}
.stApp { background-color: #08080a; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1300px !important; }

/* ── F1 OVERLAY ─────────────────────────────────── */
#f1-overlay {
    position: fixed;
    inset: 0;
    background: #08080a;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

/* Scanlines texture */
#f1-overlay::before {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.08) 2px,
        rgba(0,0,0,0.08) 4px
    );
    pointer-events: none;
    z-index: 1;
}

.f1-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 5rem;
    color: #e8b84b;
    letter-spacing: 0.12em;
    text-shadow: 0 0 40px rgba(232,184,75,0.6), 0 0 80px rgba(232,184,75,0.2);
    animation: flicker 0.15s infinite alternate;
    z-index: 2;
    margin-bottom: 0.2rem;
}
@keyframes flicker {
    0%   { opacity: 1; text-shadow: 0 0 40px rgba(232,184,75,0.8); }
    100% { opacity: 0.94; text-shadow: 0 0 20px rgba(232,184,75,0.4); }
}

.f1-subtitle {
    font-size: 0.75rem;
    letter-spacing: 0.4em;
    text-transform: uppercase;
    color: #555;
    z-index: 2;
    margin-bottom: 3rem;
}

/* ── TRACK SVG WRAPPER ── */
.track-wrapper {
    position: relative;
    width: 520px;
    height: 320px;
    z-index: 2;
}
.track-wrapper svg {
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 0 12px rgba(232,184,75,0.15));
}

/* ── CAR on SVG path ── */
.f1-car-svg {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
}

/* animated car element */
.racing-car {
    position: absolute;
    font-size: 2.2rem;
    line-height: 1;
    animation: raceCar 2s linear infinite;
    offset-path: path('M 100 160 C 100 80 180 40 260 55 C 330 68 400 95 420 140 C 440 185 410 235 355 250 C 295 267 215 260 160 245 C 105 230 100 240 100 160');
    offset-rotate: auto;
    z-index: 3;
    filter: drop-shadow(0 0 8px rgba(232,184,75,0.9));
}
@keyframes raceCar {
    0%   { offset-distance: 0%; }
    100% { offset-distance: 100%; }
}

/* Speed lines */
.speed-line {
    position: absolute;
    height: 2px;
    background: linear-gradient(to right, transparent, rgba(232,184,75,0.4), transparent);
    animation: speedLine 0.6s linear infinite;
    z-index: 2;
}
@keyframes speedLine {
    0%   { transform: translateX(-100%); opacity: 0; }
    50%  { opacity: 1; }
    100% { transform: translateX(100vw); opacity: 0; }
}

/* Countdown lights */
.lights-row {
    display: flex;
    gap: 12px;
    margin-bottom: 2rem;
    z-index: 2;
}
.light {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #1a1a1a;
    border: 2px solid #2a2a2a;
    transition: all 0.3s;
}
.light.on {
    background: #e8b84b;
    border-color: #e8b84b;
    box-shadow: 0 0 16px rgba(232,184,75,0.9), 0 0 32px rgba(232,184,75,0.4);
    animation: lightPulse 0.5s ease-in-out infinite alternate;
}
@keyframes lightPulse {
    from { box-shadow: 0 0 10px rgba(232,184,75,0.6); }
    to   { box-shadow: 0 0 24px rgba(232,184,75,1), 0 0 48px rgba(232,184,75,0.5); }
}

/* ── FARE REVEAL ── */
#fare-reveal {
    position: fixed;
    inset: 0;
    background: #08080a;
    z-index: 99998;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: fareIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
@keyframes fareIn {
    0%   { opacity: 0; transform: scale(0.85); }
    100% { opacity: 1; transform: scale(1); }
}
.fare-amount {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 9rem;
    color: #e8b84b;
    letter-spacing: 0.06em;
    line-height: 1;
    text-shadow: 0 0 60px rgba(232,184,75,0.5);
    animation: countUp 1.2s ease-out forwards;
}
@keyframes countUp {
    0%   { transform: translateY(40px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
}
.fare-label {
    font-size: 0.7rem;
    letter-spacing: 0.4em;
    text-transform: uppercase;
    color: #444;
    margin-bottom: 1rem;
    animation: fadeUp 1s 0.3s ease-out both;
}
.fare-meta {
    font-size: 0.85rem;
    color: #333;
    letter-spacing: 0.1em;
    animation: fadeUp 1s 0.6s ease-out both;
}
@keyframes fadeUp {
    0%   { transform: translateY(20px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
}
.fare-close {
    margin-top: 3rem;
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #333;
    cursor: pointer;
    animation: fadeUp 1s 1s ease-out both;
    padding: 0.6rem 1.4rem;
    border: 1px solid #222;
    border-radius: 8px;
    transition: color 0.2s, border-color 0.2s;
}
.fare-close:hover { color: #e8b84b; border-color: #e8b84b; }

/* ── MAIN UI ── */
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4rem;
    color: #f0ede8;
    letter-spacing: 0.08em;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.hero-sub { font-size: 0.9rem; color: #444; font-weight: 300; letter-spacing: 0.04em; }

.section-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #e8b84b;
    margin-bottom: 0.5rem;
    margin-top: 1.4rem;
}
.divider { border: none; border-top: 1px solid #161620; margin: 1rem 0; }

div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #111116 !important;
    border: 1px solid #222230 !important;
    border-radius: 10px !important;
    color: #f0ede8 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.92rem !important;
}
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTimeInput"] input:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: #e8b84b !important;
    box-shadow: 0 0 0 3px rgba(232,184,75,0.1) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: #444 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
div[data-testid="stNumberInput"] button {
    background: #111116 !important;
    border-color: #222230 !important;
    color: #666 !important;
    border-radius: 8px !important;
}

div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #e8b84b, #d4a030) !important;
    color: #08080a !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.3rem !important;
    letter-spacing: 0.12em !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.9rem 2rem !important;
    width: 100% !important;
    transition: opacity 0.2s, transform 0.1s !important;
}
div[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-2px) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Snoop Dogg background music (YouTube embed, autoplay) ─────────────────────
st.markdown("""
<iframe id="yt-audio"
    src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&controls=0&mute=0"
    style="position:fixed; bottom:-100px; left:-100px; width:1px; height:1px; opacity:0; pointer-events:none;"
    allow="autoplay"
    frameborder="0">
</iframe>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("show_f1", False), ("show_fare", False), ("fare_data", None), ("geo_cache", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── F1 ANIMATION SCREEN ───────────────────────────────────────────────────────
if st.session_state.show_f1:
    st.markdown("""
    <div id="f1-overlay">
        <!-- Speed lines -->
        <div class="speed-line" style="top:20%; width:60%; left:0; animation-delay:0s;"></div>
        <div class="speed-line" style="top:35%; width:40%; left:0; animation-delay:0.2s;"></div>
        <div class="speed-line" style="top:65%; width:70%; left:0; animation-delay:0.1s;"></div>
        <div class="speed-line" style="top:80%; width:50%; left:0; animation-delay:0.3s;"></div>

        <div class="f1-title">NYC GRAND PRIX</div>
        <div class="f1-subtitle">Computing optimal fare trajectory</div>

        <!-- Countdown lights -->
        <div class="lights-row">
            <div class="light on"></div>
            <div class="light on"></div>
            <div class="light on"></div>
            <div class="light on"></div>
            <div class="light on"></div>
        </div>

        <!-- Track -->
        <div class="track-wrapper">
            <svg viewBox="0 0 520 320" fill="none" xmlns="http://www.w3.org/2000/svg">
                <!-- Outer track -->
                <path d="M 100 160 C 100 80 180 40 260 55 C 330 68 400 95 420 140 C 440 185 410 235 355 250 C 295 267 215 260 160 245 C 105 230 100 240 100 160"
                    stroke="#1e1e28" stroke-width="38" fill="none" stroke-linecap="round"/>
                <!-- Track surface -->
                <path d="M 100 160 C 100 80 180 40 260 55 C 330 68 400 95 420 140 C 440 185 410 235 355 250 C 295 267 215 260 160 245 C 105 230 100 240 100 160"
                    stroke="#17171f" stroke-width="32" fill="none" stroke-linecap="round"/>
                <!-- Center line -->
                <path d="M 100 160 C 100 80 180 40 260 55 C 330 68 400 95 420 140 C 440 185 410 235 355 250 C 295 267 215 260 160 245 C 105 230 100 240 100 160"
                    stroke="#252535" stroke-width="1" fill="none" stroke-dasharray="10 8" stroke-linecap="round"/>
                <!-- Kerbs -->
                <path d="M 100 160 C 100 80 180 40 260 55 C 330 68 400 95 420 140 C 440 185 410 235 355 250 C 295 267 215 260 160 245 C 105 230 100 240 100 160"
                    stroke="#e8b84b" stroke-width="36" fill="none" stroke-linecap="round"
                    stroke-dasharray="12 300" opacity="0.15"/>
                <!-- Start/Finish line -->
                <rect x="88" y="145" width="6" height="30" fill="#e8b84b" opacity="0.9" rx="1"/>
                <!-- Checkered pattern on S/F -->
                <rect x="88" y="145" width="3" height="8" fill="white" opacity="0.6"/>
                <rect x="91" y="153" width="3" height="8" fill="white" opacity="0.6"/>
                <rect x="88" y="161" width="3" height="8" fill="white" opacity="0.6"/>
                <!-- Sector dots -->
                <circle cx="340" cy="62" r="4" fill="#e8b84b" opacity="0.4"/>
                <circle cx="425" cy="185" r="4" fill="#e8b84b" opacity="0.4"/>
                <circle cx="200" cy="256" r="4" fill="#e8b84b" opacity="0.4"/>
            </svg>
            <!-- The racing car -->
            <div class="racing-car">🏎️</div>
        </div>
    </div>

    <script>
        setTimeout(function() {
            var overlay = document.getElementById('f1-overlay');
            if (overlay) overlay.style.display = 'none';
        }, 5000);
    </script>
    """, unsafe_allow_html=True)

    import time
    time.sleep(5)
    st.session_state.show_f1 = False
    st.session_state.show_fare = True
    st.rerun()

# ── FARE REVEAL SCREEN ────────────────────────────────────────────────────────
if st.session_state.show_fare and st.session_state.fare_data:
    d = st.session_state.fare_data
    pax = f"{d['pax']} passenger{'s' if d['pax'] > 1 else ''}"
    st.markdown(f"""
    <div id="fare-reveal">
        <div class="fare-label">Estimated Fare</div>
        <div class="fare-amount">${d['pred']:.2f}</div>
        <div class="fare-meta">{pax} &nbsp;·&nbsp; New York City &nbsp;·&nbsp; {d['datetime']}</div>
        <div class="fare-close" onclick="document.getElementById('fare-reveal').style.display='none'">
            → View Route Map
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── MAIN UI ───────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def geocode(address):
    geolocator = Nominatim(user_agent="nyc_taxi_fare_v2")
    loc = geolocator.geocode(f"{address}, New York City, NY", timeout=10)
    if loc:
        return loc.latitude, loc.longitude
    return None, None

left, right = st.columns([1, 1.6], gap="large")

with left:
    st.markdown("""
    <div style="padding-bottom:1rem">
        <div class="hero-title">NYC TAXI<br>FARE</div>
        <div class="hero-sub">Formula 1 precision · NYC speed</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">⏰ Date & Time</div>', unsafe_allow_html=True)
    cd, ct = st.columns(2)
    with cd:
        pickup_date = st.date_input("Date", value=datetime.now().date(), label_visibility="collapsed")
    with ct:
        pickup_time = st.time_input("Time", value=datetime.now().time(), label_visibility="collapsed", step=60)
    pickup_datetime = f"{pickup_date} {pickup_time}"

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">📍 Pickup Address</div>', unsafe_allow_html=True)
    pickup_address = st.text_input("pickup", label_visibility="collapsed",
                                   placeholder="e.g. Empire State Building")

    st.markdown('<div class="section-label">🏁 Dropoff Address</div>', unsafe_allow_html=True)
    dropoff_address = st.text_input("dropoff", label_visibility="collapsed",
                                    placeholder="e.g. JFK Airport")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.number_input("pass", min_value=1, max_value=8, value=1,
                                      label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)

    if st.button("🏎️  RACE TO FARE"):
        if not pickup_address or not dropoff_address:
            st.error("Enter both pickup and dropoff addresses.")
        else:
            with st.spinner("Geocoding..."):
                plat, plon = geocode(pickup_address)
                dlat, dlon = geocode(dropoff_address)

            if plat is None:
                st.error(f"Address not found: {pickup_address}")
            elif dlat is None:
                st.error(f"Address not found: {dropoff_address}")
            else:
                params = {
                    "pickup_datetime":   pickup_datetime,
                    "pickup_latitude":   plat,
                    "pickup_longitude":  plon,
                    "dropoff_latitude":  dlat,
                    "dropoff_longitude": dlon,
                    "passenger_count":   int(passenger_count),
                }
                try:
                    r = requests.get("https://taxifare.lewagon.ai/predict", params=params, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    pred = data.get("fare", data.get("fare_amount"))
                    if pred is not None:
                        st.session_state.fare_data = {
                            "pred": pred,
                            "pax": int(passenger_count),
                            "datetime": str(pickup_datetime),
                            "plat": plat, "plon": plon,
                            "dlat": dlat, "dlon": dlon,
                        }
                        st.session_state.show_f1 = True
                        st.session_state.show_fare = False
                        st.rerun()
                    else:
                        st.error("Unexpected API response.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Show compact result under button after animation
    if st.session_state.fare_data and st.session_state.show_fare:
        d = st.session_state.fare_data
        st.markdown(f"""
        <div style="background:#111116;border:1px solid #1e1e28;border-radius:14px;
                    padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;
                        color:#333;margin-bottom:0.4rem;">Estimated Fare</div>
            <div style="font-family:'Bebas Neue',serif;font-size:3.4rem;
                        color:#e8b84b;line-height:1;">${d['pred']:.2f}</div>
            <div style="font-size:0.78rem;color:#333;margin-top:0.4rem;">
                {d['pax']} pax · NYC
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── MAP ───────────────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="section-label" style="margin-top:0">🗺️ Route</div>', unsafe_allow_html=True)

    d = st.session_state.fare_data
    plat = d["plat"] if d else 40.748817
    plon = d["plon"] if d else -73.985428
    dlat = d["dlat"] if d else 40.763015
    dlon = d["dlon"] if d else -73.979570

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
    dots = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([
            {"lon": plon, "lat": plat, "color": [34, 197, 94, 255],  "label": "📍 Pickup"},
            {"lon": dlon, "lat": dlat, "color": [239, 68, 68, 255],  "label": "🏁 Dropoff"},
        ]),
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_line_color=[255, 255, 255, 180],
        get_radius=110,
        stroked=True,
        line_width_min_pixels=3,
        pickable=True,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[line_layer, dots],
        initial_view_state=pdk.ViewState(
            latitude=mid_lat, longitude=mid_lon,
            zoom=12, pitch=0, bearing=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "{label}"},
    ), use_container_width=True, height=600)

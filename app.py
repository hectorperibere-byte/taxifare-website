import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="NYC TAXI FARE", page_icon="🏎️", layout="wide")

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [("stage", "form"), ("fare_data", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── GEOCODE — zero external packages, uses requests only ──────────────────────
@st.cache_data(show_spinner=False)
def geocode(address: str):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{address}, New York, USA", "format": "json", "limit": 1},
            headers={"User-Agent": "nyc-taxi-fare/1.0"},
            timeout=10,
        )
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None, None

# ── FARE API ──────────────────────────────────────────────────────────────────
def get_fare(pickup_dt, plat, plon, dlat, dlon, pax):
    try:
        r = requests.get(
            "https://taxifare.lewagon.ai/predict",
            params={
                "pickup_datetime":   pickup_dt,
                "pickup_latitude":   plat,
                "pickup_longitude":  plon,
                "dropoff_latitude":  dlat,
                "dropoff_longitude": dlon,
                "passenger_count":   pax,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        for key in ("fare", "fare_amount", "prediction", "predicted_fare"):
            if key in data:
                return float(data[key]), None
        for v in data.values():
            try:
                return float(v), None
            except (TypeError, ValueError):
                pass
        return None, f"Unexpected response: {data}"
    except Exception as e:
        return None, str(e)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #08080a; color: #f0ede8; }
.stApp { background: #08080a; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1300px !important; }

.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: 4rem; color: #f0ede8; letter-spacing: 0.08em; line-height: 1; }
.hero-sub { font-size: 0.9rem; color: #444; font-weight: 300; }
.sec { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: #e8b84b; margin: 1.2rem 0 0.4rem 0; }
.divider { border: none; border-top: 1px solid #161620; margin: 1rem 0; }

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input {
    background: #111116 !important; border: 1px solid #222230 !important;
    border-radius: 10px !important; color: #f0ede8 !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTimeInput"] input:focus {
    border-color: #e8b84b !important;
    box-shadow: 0 0 0 3px rgba(232,184,75,0.1) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 0.7rem !important; font-weight: 600 !important;
    color: #444 !important; text-transform: uppercase; letter-spacing: 0.08em;
}
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #e8b84b, #d4a030) !important;
    color: #08080a !important; font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.3rem !important; letter-spacing: 0.12em !important;
    border: none !important; border-radius: 12px !important;
    padding: 0.9rem 2rem !important; width: 100% !important;
}
div[data-testid="stButton"] > button:hover { opacity: 0.88 !important; }

/* F1 overlay */
#f1-overlay {
    position: fixed; inset: 0; background: #08080a; z-index: 99999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    overflow: hidden;
}
#f1-overlay::before {
    content: ''; position: absolute; inset: 0;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px);
    pointer-events: none; z-index: 1;
}
.f1-title {
    font-family: 'Bebas Neue', sans-serif; font-size: 5rem; color: #e8b84b;
    letter-spacing: 0.12em; z-index: 2; margin-bottom: 0.2rem;
    animation: flicker 0.2s infinite alternate;
    text-shadow: 0 0 40px rgba(232,184,75,0.6);
}
@keyframes flicker {
    0%   { opacity: 1; }
    100% { opacity: 0.92; }
}
.f1-sub { font-size: 0.72rem; letter-spacing: 0.4em; text-transform: uppercase; color: #444; z-index: 2; margin-bottom: 2.5rem; }
.lights-row { display: flex; gap: 14px; margin-bottom: 2rem; z-index: 2; }
.light { width: 24px; height: 24px; border-radius: 50%; background: #1a1a1a; border: 2px solid #2a2a2a; }
.light.on { background: #e8b84b; border-color: #e8b84b; box-shadow: 0 0 18px rgba(232,184,75,1), 0 0 40px rgba(232,184,75,0.4); animation: lp 0.5s ease-in-out infinite alternate; }
@keyframes lp { from { box-shadow: 0 0 10px rgba(232,184,75,0.6); } to { box-shadow: 0 0 28px rgba(232,184,75,1), 0 0 56px rgba(232,184,75,0.5); } }
.track-wrap { position: relative; width: 520px; height: 300px; z-index: 2; }
.track-wrap svg { width: 100%; height: 100%; }
.rcar {
    position: absolute; font-size: 2rem; top: 0; left: 0;
    animation: drive 1.8s linear infinite;
    offset-path: path('M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150');
    offset-rotate: auto;
    filter: drop-shadow(0 0 10px rgba(232,184,75,1));
    z-index: 3;
}
@keyframes drive { 0% { offset-distance: 0%; } 100% { offset-distance: 100%; } }
.speed-line {
    position: absolute; height: 1px;
    background: linear-gradient(to right, transparent, rgba(232,184,75,0.35), transparent);
    animation: sl 0.7s linear infinite; z-index: 2;
}
@keyframes sl { 0% { transform: translateX(-120%); opacity:0; } 50% { opacity:1; } 100% { transform: translateX(110vw); opacity:0; } }

/* Fare reveal */
#fare-reveal {
    position: fixed; inset: 0; background: #08080a; z-index: 99998;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    animation: fi 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
}
@keyframes fi { 0% { opacity:0; transform:scale(0.9); } 100% { opacity:1; transform:scale(1); } }
.fare-amt {
    font-family: 'Bebas Neue', sans-serif; font-size: 10rem; color: #e8b84b; line-height: 1;
    text-shadow: 0 0 80px rgba(232,184,75,0.4);
    animation: cu 1s ease-out forwards;
}
@keyframes cu { 0% { transform: translateY(50px); opacity:0; } 100% { transform: translateY(0); opacity:1; } }
.fare-lbl { font-size: 0.68rem; letter-spacing: 0.4em; text-transform: uppercase; color: #333; margin-bottom: 1rem; animation: fu 1s 0.2s ease-out both; }
.fare-meta { font-size: 0.85rem; color: #2a2a2a; letter-spacing: 0.08em; animation: fu 1s 0.5s ease-out both; }
.fare-btn {
    margin-top: 3rem; font-size: 0.72rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: #2a2a2a; cursor: pointer; padding: 0.6rem 1.6rem;
    border: 1px solid #1e1e1e; border-radius: 8px;
    animation: fu 1s 0.9s ease-out both;
    transition: color 0.2s, border-color 0.2s;
}
.fare-btn:hover { color: #e8b84b; border-color: #e8b84b; }
@keyframes fu { 0% { transform: translateY(20px); opacity:0; } 100% { transform: translateY(0); opacity:1; } }
</style>
""", unsafe_allow_html=True)

# ── F1 ANIMATION STAGE ────────────────────────────────────────────────────────
if st.session_state.stage == "f1":
    st.markdown("""
    <div id="f1-overlay">
        <div class="speed-line" style="top:18%;width:55%;animation-delay:0s;"></div>
        <div class="speed-line" style="top:32%;width:38%;animation-delay:0.25s;"></div>
        <div class="speed-line" style="top:68%;width:65%;animation-delay:0.1s;"></div>
        <div class="speed-line" style="top:82%;width:45%;animation-delay:0.4s;"></div>
        <div class="f1-title">NYC GRAND PRIX</div>
        <div class="f1-sub">Computing optimal fare trajectory</div>
        <div class="lights-row">
            <div class="light on"></div><div class="light on"></div>
            <div class="light on"></div><div class="light on"></div>
            <div class="light on"></div>
        </div>
        <div class="track-wrap">
            <svg viewBox="0 0 520 300" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150"
                    stroke="#1e1e28" stroke-width="36" fill="none" stroke-linecap="round"/>
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150"
                    stroke="#17171f" stroke-width="30" fill="none" stroke-linecap="round"/>
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150"
                    stroke="#252535" stroke-width="1" fill="none" stroke-dasharray="10 8"/>
                <rect x="87" y="136" width="5" height="28" fill="#e8b84b" rx="1" opacity="0.9"/>
                <rect x="87" y="136" width="2.5" height="7" fill="white" opacity="0.5"/>
                <rect x="89.5" y="143" width="2.5" height="7" fill="white" opacity="0.5"/>
                <rect x="87" y="150" width="2.5" height="7" fill="white" opacity="0.5"/>
                <circle cx="342" cy="58" r="4" fill="#e8b84b" opacity="0.3"/>
                <circle cx="428" cy="180" r="4" fill="#e8b84b" opacity="0.3"/>
                <circle cx="195" cy="252" r="4" fill="#e8b84b" opacity="0.3"/>
            </svg>
            <div class="rcar">🏎️</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(5)
    st.session_state.stage = "result"
    st.rerun()

# ── FARE REVEAL STAGE ─────────────────────────────────────────────────────────
elif st.session_state.stage == "result" and st.session_state.fare_data:
    d = st.session_state.fare_data
    pax_label = f"{d['pax']} passenger{'s' if d['pax'] > 1 else ''}"
    st.markdown(f"""
    <div id="fare-reveal">
        <div class="fare-lbl">Estimated Fare</div>
        <div class="fare-amt">${d['pred']:.2f}</div>
        <div class="fare-meta">{pax_label} &nbsp;·&nbsp; New York City</div>
        <div class="fare-btn" onclick="document.getElementById('fare-reveal').style.display='none'">
            → View Route Map
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── MAIN FORM ─────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.6], gap="large")

with left:
    st.markdown('<div class="hero-title">NYC TAXI<br>FARE</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Formula 1 precision · NYC speed</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">⏰ Date & Time</div>', unsafe_allow_html=True)
    cd, ct = st.columns(2)
    with cd:
        pickup_date = st.date_input("Date", value=datetime.now().date(), label_visibility="collapsed")
    with ct:
        pickup_time = st.time_input("Time", value=datetime.now().time(), label_visibility="collapsed", step=60)
    pickup_dt = f"{pickup_date} {pickup_time}"

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">📍 Pickup Address</div>', unsafe_allow_html=True)
    pickup_address = st.text_input("p", label_visibility="collapsed", placeholder="e.g. Empire State Building")

    st.markdown('<div class="sec">🏁 Dropoff Address</div>', unsafe_allow_html=True)
    dropoff_address = st.text_input("d", label_visibility="collapsed", placeholder="e.g. JFK Airport")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.number_input("n", min_value=1, max_value=8, value=1, label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)

    if st.button("🏎️  RACE TO FARE"):
        if not pickup_address.strip() or not dropoff_address.strip():
            st.error("Please enter both addresses.")
        else:
            with st.spinner("Finding addresses..."):
                plat, plon = geocode(pickup_address.strip())
                dlat, dlon = geocode(dropoff_address.strip())

            if plat is None:
                st.error(f"Could not find: **{pickup_address}** — try a more specific address.")
            elif dlat is None:
                st.error(f"Could not find: **{dropoff_address}** — try a more specific address.")
            else:
                with st.spinner("Calculating fare..."):
                    pred, err = get_fare(pickup_dt, plat, plon, dlat, dlon, int(passenger_count))

                if err:
                    st.error(f"API error: {err}")
                else:
                    st.session_state.fare_data = {
                        "pred": pred, "pax": int(passenger_count),
                        "plat": plat, "plon": plon,
                        "dlat": dlat, "dlon": dlon,
                    }
                    st.session_state.stage = "f1"
                    st.rerun()

    # Compact result card (shown after animation)
    if st.session_state.fare_data and st.session_state.stage == "result":
        d = st.session_state.fare_data
        st.markdown(f"""
        <div style="background:#111116;border:1px solid #1e1e28;border-radius:14px;
                    padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#333;margin-bottom:0.4rem;">Estimated Fare</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3.4rem;color:#e8b84b;line-height:1;">${d['pred']:.2f}</div>
            <div style="font-size:0.78rem;color:#333;margin-top:0.4rem;">{d['pax']} pax · NYC</div>
        </div>
        """, unsafe_allow_html=True)

# ── MAP ───────────────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="sec" style="margin-top:0">🗺️ Route</div>', unsafe_allow_html=True)

    d = st.session_state.fare_data
    plat = d["plat"] if d else 40.748817
    plon = d["plon"] if d else -73.985428
    dlat = d["dlat"] if d else 40.763015
    dlon = d["dlon"] if d else -73.979570

    st.pydeck_chart(pdk.Deck(
        layers=[
            pdk.Layer("PathLayer",
                data=pd.DataFrame([{"path": [[plon, plat], [dlon, dlat]]}]),
                get_path="path", get_color=[232, 184, 75, 255],
                get_width=6, width_min_pixels=4),
            pdk.Layer("ScatterplotLayer",
                data=pd.DataFrame([
                    {"lon": plon, "lat": plat, "color": [34, 197, 94, 255],  "label": "📍 Pickup"},
                    {"lon": dlon, "lat": dlat, "color": [239, 68, 68, 255],  "label": "🏁 Dropoff"},
                ]),
                get_position=["lon", "lat"], get_fill_color="color",
                get_line_color=[255, 255, 255, 180], get_radius=110,
                stroked=True, line_width_min_pixels=3, pickable=True),
        ],
        initial_view_state=pdk.ViewState(
            latitude=(plat + dlat) / 2, longitude=(plon + dlon) / 2,
            zoom=12, pitch=0, bearing=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "{label}"},
    ), width="stretch", height=600)

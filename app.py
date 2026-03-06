import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
from datetime import datetime
import time
import json

st.set_page_config(page_title="NYC TAXI FARE", page_icon="🏎️", layout="wide")

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [("stage", "form"), ("fare_data", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── HELPERS ───────────────────────────────────────────────────────────────────
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

@st.cache_data(show_spinner=False)
def get_route(plat, plon, dlat, dlon):
    try:
        r = requests.get(
            f"http://router.project-osrm.org/route/v1/driving/{plon},{plat};{dlon},{dlat}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=8,
        )
        data = r.json()
        if data.get("code") == "Ok":
            return data["routes"][0]["geometry"]["coordinates"]
    except Exception:
        pass
    return [[plon, plat], [dlon, dlat]]

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
        return None, f"Unexpected API response: {data}"
    except Exception as e:
        return None, str(e)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #08080a; color: #f0ede8; }
.stApp { background: #08080a; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1400px !important; }

.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: 4rem; color: #f0ede8; letter-spacing: 0.08em; line-height: 1; }
.hero-sub { font-size: 0.9rem; color: #444; font-weight: 300; margin-top: 0.3rem; }
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
div[data-testid="stNumberInput"] input:focus {
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

/* ── F1 RACE OVERLAY ── */
#f1-overlay {
    position: fixed; inset: 0; background: #08080a; z-index: 99999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
#f1-overlay::before {
    content: ''; position: absolute; inset: 0;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px);
    pointer-events: none;
}
.f1-title { font-family:'Bebas Neue',sans-serif; font-size:5rem; color:#e8b84b; letter-spacing:0.12em; text-shadow:0 0 40px rgba(232,184,75,0.6); animation:flicker 0.2s infinite alternate; }
@keyframes flicker { 0%{opacity:1;} 100%{opacity:0.9;} }
.f1-sub { font-size:0.72rem; letter-spacing:0.4em; text-transform:uppercase; color:#444; margin:0.3rem 0 2rem 0; }
.lights-row { display:flex; gap:14px; margin-bottom:2rem; }
.light { width:24px; height:24px; border-radius:50%; background:#1a1a1a; border:2px solid #2a2a2a; }
.light.on { background:#e8b84b; border-color:#e8b84b; animation:lp 0.5s ease-in-out infinite alternate; box-shadow:0 0 18px rgba(232,184,75,1); }
@keyframes lp { from{box-shadow:0 0 10px rgba(232,184,75,0.6);} to{box-shadow:0 0 30px rgba(232,184,75,1),0 0 60px rgba(232,184,75,0.4);} }
.track-wrap { position:relative; width:520px; height:300px; }
.track-wrap svg { width:100%; height:100%; }
.rcar { position:absolute; font-size:2rem; top:0; left:0; animation:drive 1.8s linear infinite; offset-path:path('M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150'); offset-rotate:auto; filter:drop-shadow(0 0 10px rgba(232,184,75,1)); }
@keyframes drive { 0%{offset-distance:0%;} 100%{offset-distance:100%;} }
.speed-line { position:absolute; height:1px; background:linear-gradient(to right,transparent,rgba(232,184,75,0.35),transparent); animation:sl 0.7s linear infinite; }
@keyframes sl { 0%{transform:translateX(-120%);opacity:0;} 50%{opacity:1;} 100%{transform:translateX(110vw);opacity:0;} }

/* ── FARE REVEAL ── */
#fare-reveal {
    position:fixed; inset:0; background:#08080a; z-index:99998;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    animation:fi 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
}
@keyframes fi { 0%{opacity:0;transform:scale(0.9);} 100%{opacity:1;transform:scale(1);} }
.fare-amt { font-family:'Bebas Neue',sans-serif; font-size:10rem; color:#e8b84b; line-height:1; text-shadow:0 0 80px rgba(232,184,75,0.4); animation:cu 1s ease-out forwards; }
@keyframes cu { 0%{transform:translateY(50px);opacity:0;} 100%{transform:translateY(0);opacity:1;} }
.fare-lbl { font-size:0.68rem; letter-spacing:0.4em; text-transform:uppercase; color:#333; margin-bottom:1rem; }
.fare-meta { font-size:0.85rem; color:#2a2a2a; letter-spacing:0.08em; }
.fare-btn { margin-top:2.5rem; font-size:0.72rem; letter-spacing:0.2em; text-transform:uppercase; color:#555; cursor:pointer; padding:0.7rem 2rem; border:1px solid #222; border-radius:8px; transition:all 0.2s; background:transparent; font-family:'DM Sans',sans-serif; }
.fare-btn:hover { color:#e8b84b; border-color:#e8b84b; background:rgba(232,184,75,0.05); }

/* ── ROUTE MAP OVERLAY ── */
#route-overlay {
    position:fixed; inset:0; background:#08080a; z-index:99997;
    display:flex; flex-direction:column; align-items:stretch;
    animation:fi 0.5s ease forwards;
}
.route-header {
    display:flex; align-items:center; justify-content:space-between;
    padding:1.2rem 2rem; border-bottom:1px solid #161620;
    flex-shrink:0;
}
.route-title { font-family:'Bebas Neue',sans-serif; font-size:2rem; color:#e8b84b; letter-spacing:0.1em; }
.route-close { font-size:0.7rem; letter-spacing:0.2em; text-transform:uppercase; color:#444; cursor:pointer; padding:0.5rem 1.2rem; border:1px solid #222; border-radius:8px; transition:all 0.2s; background:transparent; font-family:'DM Sans',sans-serif; }
.route-close:hover { color:#e8b84b; border-color:#e8b84b; }
.route-map-wrap { flex:1; position:relative; overflow:hidden; }
.route-stats { display:flex; gap:0; border-top:1px solid #161620; flex-shrink:0; }
.route-stat { flex:1; padding:1rem 2rem; border-right:1px solid #161620; }
.route-stat:last-child { border-right:none; }
.route-stat-label { font-size:0.6rem; letter-spacing:0.18em; text-transform:uppercase; color:#333; margin-bottom:0.3rem; }
.route-stat-value { font-family:'Bebas Neue',sans-serif; font-size:1.8rem; color:#e8b84b; line-height:1; }
</style>
""", unsafe_allow_html=True)

# ── SNOOP DOGG ────────────────────────────────────────────────────────────────
st.markdown("""
<iframe src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&mute=0&controls=0"
    style="position:fixed;bottom:-200px;left:-200px;width:1px;height:1px;opacity:0.01;pointer-events:none;"
    allow="autoplay; encrypted-media" frameborder="0"></iframe>
""", unsafe_allow_html=True)

# ── STAGE: F1 ANIMATION ───────────────────────────────────────────────────────
if st.session_state.stage == "f1":
    st.markdown("""
    <div id="f1-overlay">
        <div class="speed-line" style="top:18%;width:55%;animation-delay:0s;"></div>
        <div class="speed-line" style="top:35%;width:38%;animation-delay:0.25s;"></div>
        <div class="speed-line" style="top:68%;width:65%;animation-delay:0.1s;"></div>
        <div class="speed-line" style="top:82%;width:44%;animation-delay:0.4s;"></div>
        <div class="f1-title">NYC GRAND PRIX</div>
        <div class="f1-sub">Computing optimal fare trajectory</div>
        <div class="lights-row">
            <div class="light on"></div><div class="light on"></div>
            <div class="light on"></div><div class="light on"></div>
            <div class="light on"></div>
        </div>
        <div class="track-wrap">
            <svg viewBox="0 0 520 300" fill="none">
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150" stroke="#1e1e28" stroke-width="36" fill="none" stroke-linecap="round"/>
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150" stroke="#17171f" stroke-width="30" fill="none" stroke-linecap="round"/>
                <path d="M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150" stroke="#252535" stroke-width="1" fill="none" stroke-dasharray="10 8"/>
                <rect x="87" y="136" width="5" height="28" fill="#e8b84b" rx="1" opacity="0.9"/>
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

# ── STAGE: FARE REVEAL ────────────────────────────────────────────────────────
elif st.session_state.stage == "result" and st.session_state.fare_data:
    d = st.session_state.fare_data
    pax_label = f"{d['pax']} passenger{'s' if d['pax'] > 1 else ''}"
    st.markdown(f"""
    <div id="fare-reveal">
        <div class="fare-lbl">Estimated Fare</div>
        <div class="fare-amt">${d['pred']:.2f}</div>
        <div class="fare-meta">{pax_label} &nbsp;·&nbsp; New York City</div>
        <button class="fare-btn" onclick="
            document.getElementById('fare-reveal').style.display='none';
        ">→ View Route Map</button>
    </div>
    """, unsafe_allow_html=True)

# ── MAIN LAYOUT ───────────────────────────────────────────────────────────────
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
    pickup_address = st.text_input("pickup_addr", label_visibility="collapsed", placeholder="e.g. Empire State Building")

    st.markdown('<div class="sec">🏁 Dropoff Address</div>', unsafe_allow_html=True)
    dropoff_address = st.text_input("dropoff_addr", label_visibility="collapsed", placeholder="e.g. JFK Airport")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">👥 Passengers</div>', unsafe_allow_html=True)
    passenger_count = st.number_input("pax_count", min_value=1, max_value=8, value=1, label_visibility="collapsed")

    st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)

    if st.button("🏎️  RACE TO FARE"):
        if not pickup_address.strip() or not dropoff_address.strip():
            st.error("Please enter both pickup and dropoff addresses.")
        else:
            with st.spinner("Finding addresses..."):
                plat, plon = geocode(pickup_address.strip())
                dlat, dlon = geocode(dropoff_address.strip())
            if plat is None:
                st.error(f"Could not find: **{pickup_address}**")
            elif dlat is None:
                st.error(f"Could not find: **{dropoff_address}**")
            else:
                with st.spinner("Calculating fare..."):
                    pred, err = get_fare(pickup_dt, plat, plon, dlat, dlon, int(passenger_count))
                if err:
                    st.error(f"API error: {err}")
                else:
                    with st.spinner("Loading route..."):
                        route = get_route(plat, plon, dlat, dlon)
                    st.session_state.fare_data = {
                        "pred": pred, "pax": int(passenger_count),
                        "plat": plat, "plon": plon,
                        "dlat": dlat, "dlon": dlon,
                        "route": route,
                        "pickup_address": pickup_address.strip(),
                        "dropoff_address": dropoff_address.strip(),
                    }
                    st.session_state.stage = "f1"
                    st.rerun()

    if st.session_state.fare_data and st.session_state.stage == "result":
        d = st.session_state.fare_data
        st.markdown(f"""
        <div style="background:#111116;border:1px solid #1e1e28;border-radius:14px;padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#333;margin-bottom:0.4rem;">Estimated Fare</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3.4rem;color:#e8b84b;line-height:1;">${d['pred']:.2f}</div>
            <div style="font-size:0.78rem;color:#333;margin-top:0.4rem;">{d['pax']} pax · NYC</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 New Ride"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()

# ── MAP with animated F1 on real route ────────────────────────────────────────
with right:
    st.markdown('<div class="sec" style="margin-top:0">🗺️ Route</div>', unsafe_allow_html=True)

    d = st.session_state.fare_data
    plat = d["plat"] if d else 40.748817
    plon = d["plon"] if d else -73.985428
    dlat = d["dlat"] if d else 40.763015
    dlon = d["dlon"] if d else -73.979570
    route = d["route"] if d else [[plon, plat], [dlon, dlat]]
    pickup_addr  = d.get("pickup_address", "Pickup")  if d else "Pickup"
    dropoff_addr = d.get("dropoff_address", "Dropoff") if d else "Dropoff"

    mid_lat = (plat + dlat) / 2
    mid_lon = (plon + dlon) / 2

    # Build animated map with Deck.GL + vanilla JS TripsLayer-style animation
    route_json = json.dumps(route)

    # We inject a custom HTML component for the animated F1 on route
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ margin:0; background:#08080a; font-family:'DM Sans',sans-serif; }}
        #map {{ width:100%; height:580px; position:relative; overflow:hidden; border-radius:12px; }}
        canvas {{ border-radius:12px; }}
        #hud {{
            position:absolute; top:16px; left:16px; z-index:10;
            background:rgba(8,8,10,0.85); border:1px solid #1e1e28;
            border-radius:10px; padding:12px 16px; backdrop-filter:blur(8px);
        }}
        #hud .addr {{ font-size:0.7rem; color:#555; text-transform:uppercase; letter-spacing:0.1em; }}
        #hud .name {{ font-size:0.88rem; color:#f0ede8; margin-bottom:8px; }}
        #hud .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
        #progress-bar {{
            position:absolute; bottom:0; left:0; height:3px;
            background:linear-gradient(to right, #e8b84b, #f0c060);
            width:0%; transition:width 0.1s linear; border-radius:0 0 12px 12px;
            z-index:10;
        }}
        #car-emoji {{
            position:absolute; font-size:1.6rem; z-index:10;
            filter:drop-shadow(0 0 12px rgba(232,184,75,0.9));
            transition:left 0.08s linear, top 0.08s linear;
            transform:translate(-50%,-50%);
            pointer-events:none;
        }}
        #speed-glow {{
            position:absolute; width:60px; height:60px;
            background:radial-gradient(circle, rgba(232,184,75,0.4) 0%, transparent 70%);
            border-radius:50%; z-index:9;
            transform:translate(-50%,-50%);
            pointer-events:none;
        }}
    </style>
    <script src="https://unpkg.com/deck.gl@latest/dist.min.js"></script>
    <script src="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.js"></script>
    </head>
    <body>
    <div id="map">
        <div id="hud">
            <div class="addr">📍 Pickup</div>
            <div class="name">{pickup_addr}</div>
            <div class="addr">🏁 Dropoff</div>
            <div class="name" style="margin-bottom:0">{dropoff_addr}</div>
        </div>
        <div id="progress-bar"></div>
        <div id="speed-glow"></div>
        <div id="car-emoji">🏎️</div>
    </div>

    <script>
    const ROUTE = {route_json};
    const MID_LAT = {mid_lat};
    const MID_LON = {mid_lon};

    // Compute zoom from route extent
    const lons = ROUTE.map(p=>p[0]), lats = ROUTE.map(p=>p[1]);
    const dLon = Math.max(...lons)-Math.min(...lons);
    const dLat = Math.max(...lats)-Math.min(...lats);
    const span = Math.max(dLon, dLat);
    const zoom = span < 0.01 ? 15 : span < 0.03 ? 14 : span < 0.08 ? 13 : span < 0.2 ? 12 : 11;

    const deckgl = new deck.DeckGL({{
        container: 'map',
        mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        initialViewState: {{ longitude: MID_LON, latitude: MID_LAT, zoom: zoom, pitch: 0, bearing: 0 }},
        controller: true,
        layers: [
            new deck.PathLayer({{
                id: 'route-bg',
                data: [{{ path: ROUTE }}],
                getPath: d => d.path,
                getColor: [40, 40, 55, 200],
                getWidth: 12,
                widthMinPixels: 8,
            }}),
            new deck.PathLayer({{
                id: 'route',
                data: [{{ path: ROUTE }}],
                getPath: d => d.path,
                getColor: [232, 184, 75, 255],
                getWidth: 5,
                widthMinPixels: 4,
            }}),
            new deck.ScatterplotLayer({{
                id: 'pickup',
                data: [{{ position: [ROUTE[0][0], ROUTE[0][1]] }}],
                getPosition: d => d.position,
                getFillColor: [34, 197, 94, 255],
                getLineColor: [255,255,255,180],
                getRadius: 18,
                stroked: true,
                lineWidthMinPixels: 2,
            }}),
            new deck.ScatterplotLayer({{
                id: 'dropoff',
                data: [{{ position: [ROUTE[ROUTE.length-1][0], ROUTE[ROUTE.length-1][1]] }}],
                getPosition: d => d.position,
                getFillColor: [239, 68, 68, 255],
                getLineColor: [255,255,255,180],
                getRadius: 18,
                stroked: true,
                lineWidthMinPixels: 2,
            }}),
        ]
    }});

    // Animate F1 car along route on the HTML overlay
    let step = 0;
    const SPEED = 0.8; // points per frame
    const progressBar = document.getElementById('progress-bar');
    const carEl = document.getElementById('car-emoji');
    const glowEl = document.getElementById('speed-glow');

    function lerpCoord(idx) {{
        const i = Math.floor(idx) % ROUTE.length;
        const next = (i+1) % ROUTE.length;
        const t = idx - Math.floor(idx);
        return [
            ROUTE[i][0] + (ROUTE[next][0]-ROUTE[i][0])*t,
            ROUTE[i][1] + (ROUTE[next][1]-ROUTE[i][1])*t,
        ];
    }}

    function lonLatToPixel(lon, lat) {{
        const vp = deckgl.getViewports()[0];
        if (!vp) return [0,0];
        return vp.project([lon, lat]);
    }}

    function animate() {{
        step = (step + SPEED) % ROUTE.length;
        const pct = (step / ROUTE.length) * 100;
        progressBar.style.width = pct + '%';

        const [lon, lat] = lerpCoord(step);
        const [px, py] = lonLatToPixel(lon, lat);

        // Rotation: angle to next point
        const [lon2, lat2] = lerpCoord(step + 1);
        const [px2, py2] = lonLatToPixel(lon2, lat2);
        const angle = Math.atan2(py2-py, px2-px) * 180/Math.PI;

        carEl.style.left = px + 'px';
        carEl.style.top = py + 'px';
        carEl.style.transform = `translate(-50%,-50%) rotate(${{angle}}deg)`;

        glowEl.style.left = px + 'px';
        glowEl.style.top = py + 'px';

        requestAnimationFrame(animate);
    }}

    // Start animation after map loads
    setTimeout(animate, 1200);
    </script>
    </body>
    </html>
    """

    st.components.v1.html(map_html, height=580)

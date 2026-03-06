import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import time

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

html, body, [class*="css"] { font-family:'DM Sans',sans-serif; background:#08080a; color:#f0ede8; }
.stApp { background:#08080a; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding:2rem 2.5rem !important; max-width:1400px !important; }

.hero-title { font-family:'Bebas Neue',sans-serif; font-size:4rem; color:#f0ede8; letter-spacing:0.08em; line-height:1; }
.hero-sub { font-size:0.9rem; color:#444; font-weight:300; margin-top:0.3rem; }
.sec { font-size:0.65rem; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:#e8b84b; margin:1.2rem 0 0.4rem 0; }
.divider { border:none; border-top:1px solid #161620; margin:1rem 0; }

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input {
    background:#111116 !important; border:1px solid #222230 !important;
    border-radius:10px !important; color:#f0ede8 !important;
    font-family:'DM Sans',sans-serif !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color:#e8b84b !important;
    box-shadow:0 0 0 3px rgba(232,184,75,0.1) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size:0.7rem !important; font-weight:600 !important;
    color:#444 !important; text-transform:uppercase; letter-spacing:0.08em;
}
div[data-testid="stButton"] > button {
    background:linear-gradient(135deg,#e8b84b,#d4a030) !important;
    color:#08080a !important; font-family:'Bebas Neue',sans-serif !important;
    font-size:1.3rem !important; letter-spacing:0.12em !important;
    border:none !important; border-radius:12px !important;
    padding:0.9rem 2rem !important; width:100% !important;
}
div[data-testid="stButton"] > button:hover { opacity:0.88 !important; }

/* F1 overlay */
#f1-overlay {
    position:fixed; inset:0; background:#08080a; z-index:99999;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
}
#f1-overlay::before {
    content:''; position:absolute; inset:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.06) 2px,rgba(0,0,0,0.06) 4px);
    pointer-events:none;
}
.f1-title { font-family:'Bebas Neue',sans-serif; font-size:5rem; color:#e8b84b; letter-spacing:0.12em; text-shadow:0 0 40px rgba(232,184,75,0.6); animation:flicker 0.2s infinite alternate; }
@keyframes flicker { 0%{opacity:1;} 100%{opacity:0.9;} }
.f1-sub { font-size:0.72rem; letter-spacing:0.4em; text-transform:uppercase; color:#444; margin:0.3rem 0 2rem 0; }
.lights-row { display:flex; gap:14px; margin-bottom:2rem; }
.light { width:24px; height:24px; border-radius:50%; background:#1a1a1a; border:2px solid #2a2a2a; }
.light.on { background:#e8b84b; border-color:#e8b84b; animation:lp 0.5s ease-in-out infinite alternate; }
@keyframes lp { from{box-shadow:0 0 10px rgba(232,184,75,0.6);} to{box-shadow:0 0 30px rgba(232,184,75,1),0 0 60px rgba(232,184,75,0.4);} }
.track-wrap { position:relative; width:520px; height:300px; }
.track-wrap svg { width:100%; height:100%; }
.rcar { position:absolute; font-size:2rem; top:0; left:0; animation:drive 1.8s linear infinite; offset-path:path('M 100 150 C 100 75 185 38 265 52 C 335 64 405 92 422 138 C 440 184 410 232 352 248 C 292 265 210 258 155 243 C 100 228 100 225 100 150'); offset-rotate:auto; filter:drop-shadow(0 0 10px rgba(232,184,75,1)); }
@keyframes drive { 0%{offset-distance:0%;} 100%{offset-distance:100%;} }
.speed-line { position:absolute; height:1px; background:linear-gradient(to right,transparent,rgba(232,184,75,0.35),transparent); animation:sl 0.7s linear infinite; }
@keyframes sl { 0%{transform:translateX(-120%);opacity:0;} 50%{opacity:1;} 100%{transform:translateX(110vw);opacity:0;} }

/* Fare reveal */
.fare-screen { text-align:center; padding:3rem; }
.fare-amt { font-family:'Bebas Neue',sans-serif; font-size:10rem; color:#e8b84b; line-height:1; text-shadow:0 0 80px rgba(232,184,75,0.3); }
.fare-lbl { font-size:0.68rem; letter-spacing:0.4em; text-transform:uppercase; color:#333; margin-bottom:0.5rem; }
.fare-meta { font-size:0.85rem; color:#2a2a2a; letter-spacing:0.08em; margin-top:0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── SNOOP DOGG ────────────────────────────────────────────────────────────────
st.markdown("""
<iframe src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&mute=0&controls=0"
    style="position:fixed;bottom:-200px;left:-200px;width:1px;height:1px;opacity:0.01;pointer-events:none;"
    allow="autoplay; encrypted-media" frameborder="0"></iframe>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STAGE: F1 ANIMATION (5 sec)
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# STAGE: FARE RESULT + VIEW ROUTE BUTTON
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "result" and st.session_state.fare_data:
    d = st.session_state.fare_data
    pax_label = f"{d['pax']} passenger{'s' if d['pax'] > 1 else ''}"

    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;">
        <div style="font-size:0.68rem;letter-spacing:0.4em;text-transform:uppercase;color:#333;margin-bottom:0.5rem;">Estimated Fare</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:10rem;color:#e8b84b;line-height:1;text-shadow:0 0 80px rgba(232,184,75,0.3);">${d['pred']:.2f}</div>
        <div style="font-size:0.85rem;color:#2a2a2a;letter-spacing:0.08em;margin-top:0.5rem;">{pax_label} &nbsp;·&nbsp; New York City</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🗺️  VIEW THE ROUTE"):
            st.session_state.stage = "map"
            st.rerun()
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("🔄  NEW RIDE"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STAGE: ANIMATED MAP — F1 drives the real route over 10 seconds
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "map" and st.session_state.fare_data:
    d = st.session_state.fare_data
    route = d.get("route", [[d["plon"], d["plat"]], [d["dlon"], d["dlat"]]])
    mid_lat = (d["plat"] + d["dlat"]) / 2
    mid_lon = (d["plon"] + d["dlon"]) / 2
    route_json = json.dumps(route)
    pickup_addr  = d.get("pickup_address", "Pickup")
    dropoff_addr = d.get("dropoff_address", "Dropoff")
    fare = d["pred"]
    pax  = d["pax"]

    lons = [p[0] for p in route]
    lats = [p[1] for p in route]
    span = max(max(lons)-min(lons), max(lats)-min(lats))
    zoom = 15 if span < 0.01 else 14 if span < 0.03 else 13 if span < 0.08 else 12 if span < 0.2 else 11

    map_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#08080a; font-family:'DM Sans',sans-serif; overflow:hidden; }}
  #wrap {{ width:100vw; height:100vh; position:relative; }}

  /* Top bar */
  #topbar {{
    position:absolute; top:0; left:0; right:0; z-index:20;
    background:rgba(8,8,10,0.9); border-bottom:1px solid #1a1a28;
    display:flex; align-items:center; justify-content:space-between;
    padding:12px 20px; backdrop-filter:blur(10px);
  }}
  #topbar .title {{ font-family:'Bebas Neue',cursive; font-size:1.4rem; color:#e8b84b; letter-spacing:0.1em; }}
  #topbar .fare-chip {{
    font-family:'Bebas Neue',cursive; font-size:1.8rem; color:#e8b84b;
    text-shadow:0 0 20px rgba(232,184,75,0.5);
  }}
  #topbar .addrs {{ font-size:0.75rem; color:#444; line-height:1.5; }}
  #topbar .addrs span {{ color:#888; }}

  /* Map */
  #map {{ width:100%; height:100%; }}

  /* Progress bar */
  #progress-wrap {{
    position:absolute; bottom:0; left:0; right:0; z-index:20;
    height:4px; background:#111116;
  }}
  #progress-bar {{
    height:100%; width:0%;
    background:linear-gradient(to right, #e8b84b, #fff5cc);
    transition:width 0.05s linear;
    box-shadow:0 0 8px rgba(232,184,75,0.8);
  }}

  /* Speed lines */
  .sline {{
    position:absolute; height:1px; pointer-events:none; z-index:15;
    background:linear-gradient(to right,transparent,rgba(232,184,75,0.2),transparent);
    animation:sl 0.8s linear infinite;
  }}
  @keyframes sl {{ 0%{{transform:translateX(-100%);opacity:0;}} 50%{{opacity:1;}} 100%{{transform:translateX(100vw);opacity:0;}} }}

  /* Car */
  #car {{
    position:absolute; z-index:25; font-size:1.8rem;
    pointer-events:none;
    filter:drop-shadow(0 0 14px rgba(232,184,75,1)) drop-shadow(0 0 4px #fff);
    transform:translate(-50%,-50%);
    transition:left 0.05s linear, top 0.05s linear;
  }}
  #glow {{
    position:absolute; z-index:24; width:70px; height:70px; border-radius:50%;
    background:radial-gradient(circle,rgba(232,184,75,0.35) 0%,transparent 70%);
    transform:translate(-50%,-50%); pointer-events:none;
  }}
  #trail-canvas {{ position:absolute; top:0; left:0; z-index:16; pointer-events:none; }}

  /* Arrival splash */
  #arrival {{
    display:none; position:absolute; inset:0; z-index:30;
    background:rgba(8,8,10,0.92); backdrop-filter:blur(8px);
    flex-direction:column; align-items:center; justify-content:center;
    animation:popIn 0.6s cubic-bezier(0.16,1,0.3,1) forwards;
  }}
  @keyframes popIn {{ 0%{{opacity:0;transform:scale(0.85);}} 100%{{opacity:1;transform:scale(1);}} }}
  #arrival .big {{ font-family:'Bebas Neue',cursive; font-size:6rem; color:#e8b84b; line-height:1; text-shadow:0 0 60px rgba(232,184,75,0.5); }}
  #arrival .sub {{ font-size:0.8rem; letter-spacing:0.3em; text-transform:uppercase; color:#333; margin-top:0.5rem; }}
  #arrival .checkered {{ font-size:3rem; margin-bottom:1rem; animation:wave 1s ease-in-out infinite alternate; }}
  @keyframes wave {{ from{{transform:rotate(-10deg);}} to{{transform:rotate(10deg);}} }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.css" rel="stylesheet">
</head>
<body>
<div id="wrap">
  <div id="topbar">
    <div>
      <div class="title">🏎️ NYC GRAND PRIX ROUTE</div>
      <div class="addrs">
        <span>📍</span> {pickup_addr}<br>
        <span>🏁</span> {dropoff_addr}
      </div>
    </div>
    <div class="fare-chip">${fare:.2f}</div>
  </div>

  <div class="sline" style="top:30%;width:40%;animation-delay:0.1s;"></div>
  <div class="sline" style="top:55%;width:30%;animation-delay:0.4s;"></div>
  <div class="sline" style="top:75%;width:50%;animation-delay:0.2s;"></div>

  <div id="map"></div>
  <canvas id="trail-canvas"></canvas>
  <div id="glow"></div>
  <div id="car">🏎️</div>
  <div id="arrival">
    <div class="checkered">🏁</div>
    <div class="big">ARRIVED!</div>
    <div class="sub">{pax} pax · ${fare:.2f} · New York City</div>
  </div>
  <div id="progress-wrap"><div id="progress-bar"></div></div>
</div>

<script>
const ROUTE = {route_json};
const MID_LAT = {mid_lat};
const MID_LON = {mid_lon};
const ZOOM = {zoom};
const DURATION_MS = 10000; // 10 seconds for full route

// Init MapLibre
const map = new maplibregl.Map({{
  container: 'map',
  style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  center: [MID_LON, MID_LAT],
  zoom: ZOOM,
  interactive: true,
}});

map.on('load', () => {{
  // Route shadow
  map.addSource('route-shadow', {{ type:'geojson', data:{{ type:'Feature', geometry:{{ type:'LineString', coordinates:ROUTE }} }} }});
  map.addLayer({{ id:'route-shadow', type:'line', source:'route-shadow', layout:{{'line-join':'round','line-cap':'round'}}, paint:{{'line-color':'#000','line-width':14,'line-opacity':0.6 }} }});

  // Route gold
  map.addSource('route', {{ type:'geojson', data:{{ type:'Feature', geometry:{{ type:'LineString', coordinates:ROUTE }} }} }});
  map.addLayer({{ id:'route', type:'line', source:'route', layout:{{'line-join':'round','line-cap':'round'}}, paint:{{'line-color':'#e8b84b','line-width':5,'line-opacity':1 }} }});

  // Pickup dot
  map.addSource('pickup', {{ type:'geojson', data:{{ type:'Feature', geometry:{{ type:'Point', coordinates:ROUTE[0] }} }} }});
  map.addLayer({{ id:'pickup', type:'circle', source:'pickup', paint:{{'circle-radius':10,'circle-color':'#22c55e','circle-stroke-color':'#fff','circle-stroke-width':2 }} }});

  // Dropoff dot
  map.addSource('dropoff', {{ type:'geojson', data:{{ type:'Feature', geometry:{{ type:'Point', coordinates:ROUTE[ROUTE.length-1] }} }} }});
  map.addLayer({{ id:'dropoff', type:'circle', source:'dropoff', paint:{{'circle-radius':10,'circle-color':'#ef4444','circle-stroke-color':'#fff','circle-stroke-width':2 }} }});

  startAnimation();
}});

// Trail canvas
const canvas = document.getElementById('trail-canvas');
const ctx = canvas.getContext('2d');
function resizeCanvas() {{
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

const carEl  = document.getElementById('car');
const glowEl = document.getElementById('glow');
const progEl = document.getElementById('progress-bar');
const arrivalEl = document.getElementById('arrival');
let trailPoints = [];

function lerp(a, b, t) {{ return a + (b-a)*t; }}

function getPositionAtProgress(t) {{
  const totalIdx = t * (ROUTE.length - 1);
  const i = Math.floor(totalIdx);
  const f = totalIdx - i;
  const next = Math.min(i+1, ROUTE.length-1);
  return [
    lerp(ROUTE[i][0], ROUTE[next][0], f),
    lerp(ROUTE[i][1], ROUTE[next][1], f),
  ];
}}

function lonLatToScreen(lon, lat) {{
  const pt = map.project([lon, lat]);
  return [pt.x, pt.y];
}}

function startAnimation() {{
  const startTime = performance.now();
  let done = false;

  function frame(now) {{
    const elapsed = now - startTime;
    const t = Math.min(elapsed / DURATION_MS, 1);
    progEl.style.width = (t * 100) + '%';

    const [lon, lat] = getPositionAtProgress(t);
    const [px, py] = lonLatToScreen(lon, lat);

    // Direction angle
    const t2 = Math.min(t + 0.005, 1);
    const [lon2, lat2] = getPositionAtProgress(t2);
    const [px2, py2] = lonLatToScreen(lon2, lat2);
    const angle = Math.atan2(py2-py, px2-px) * 180 / Math.PI;

    carEl.style.left  = px + 'px';
    carEl.style.top   = py + 'px';
    carEl.style.transform = `translate(-50%,-50%) rotate(${{angle}}deg)`;

    glowEl.style.left = px + 'px';
    glowEl.style.top  = py + 'px';

    // Trail
    trailPoints.push([px, py]);
    if (trailPoints.length > 40) trailPoints.shift();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (trailPoints.length > 1) {{
      for (let i=1; i<trailPoints.length; i++) {{
        const alpha = (i / trailPoints.length) * 0.6;
        const width = (i / trailPoints.length) * 6;
        ctx.beginPath();
        ctx.moveTo(trailPoints[i-1][0], trailPoints[i-1][1]);
        ctx.lineTo(trailPoints[i][0], trailPoints[i][1]);
        ctx.strokeStyle = `rgba(232,184,75,${{alpha}})`;
        ctx.lineWidth = width;
        ctx.lineCap = 'round';
        ctx.stroke();
      }}
    }}

    if (t < 1) {{
      requestAnimationFrame(frame);
    }} else if (!done) {{
      done = true;
      carEl.style.display = 'none';
      glowEl.style.display = 'none';
      arrivalEl.style.display = 'flex';
    }}
  }}

  requestAnimationFrame(frame);
}}
</script>
</body>
</html>"""

    st.components.v1.html(map_html, height=700, scrolling=False)

    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔄  NEW RIDE"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STAGE: FORM
# ══════════════════════════════════════════════════════════════════════════════
else:
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.markdown('<div class="hero-title">NYC TAXI<br>FARE</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-sub">Formula 1 precision · NYC speed</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sec">⏰ Date & Time</div>', unsafe_allow_html=True)
        cd, ct = st.columns(2)
        with cd:
            pickup_date = st.date_input("Date", value=datetime.now().date(), label_visibility="collapsed")
        with ct:
            hours = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
            default_hour = datetime.now().strftime("%H")
            default_min  = "00" if int(datetime.now().strftime("%M")) < 30 else "30"
            default_time = f"{default_hour}:{default_min}"
            default_idx  = hours.index(default_time) if default_time in hours else 0
            pickup_time  = st.selectbox("Time", hours, index=default_idx, label_visibility="collapsed")
        pickup_dt = f"{pickup_date} {pickup_time}:00"

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

    with right:
        # Default NYC map preview
        import pydeck as pdk
        st.markdown('<div class="sec" style="margin-top:0">🗺️ NYC Preview</div>', unsafe_allow_html=True)
        st.pydeck_chart(pdk.Deck(
            layers=[],
            initial_view_state=pdk.ViewState(latitude=40.7549, longitude=-73.9840, zoom=12, pitch=0),
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        ), width="stretch", height=580)

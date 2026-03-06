import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import json
from datetime import datetime
import time

st.set_page_config(page_title="NYC TAXI FARE", page_icon="🚂", layout="wide")

for k, v in [("stage", "form"), ("fare_data", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:#08080a;color:#f0ede8;}
.stApp{background:#08080a;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:2rem 2.5rem !important;max-width:1400px !important;}
.hero-title{font-family:'Bebas Neue',sans-serif;font-size:4rem;color:#f0ede8;letter-spacing:0.08em;line-height:1;}
.hero-sub{font-size:0.9rem;color:#444;font-weight:300;margin-top:0.3rem;}
.sec{font-size:0.65rem;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#e8b84b;margin:1.2rem 0 0.4rem 0;}
.divider{border:none;border-top:1px solid #161620;margin:1rem 0;}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background:#111116 !important;border:1px solid #222230 !important;
    border-radius:10px !important;color:#f0ede8 !important;}
div[data-testid="stTextInput"] input:focus,div[data-testid="stNumberInput"] input:focus{
    border-color:#e8b84b !important;box-shadow:0 0 0 3px rgba(232,184,75,0.1) !important;}
label[data-testid="stWidgetLabel"] p{font-size:0.7rem !important;font-weight:600 !important;color:#444 !important;text-transform:uppercase;letter-spacing:0.08em;}
div[data-testid="stButton"]>button{
    background:linear-gradient(135deg,#e8b84b,#d4a030) !important;
    color:#08080a !important;font-family:'Bebas Neue',sans-serif !important;
    font-size:1.3rem !important;letter-spacing:0.12em !important;
    border:none !important;border-radius:12px !important;
    padding:0.9rem 2rem !important;width:100% !important;}
div[data-testid="stButton"]>button:hover{opacity:0.88 !important;}

/* TRAIN OVERLAY */
#train-overlay{position:fixed;inset:0;background:#08080a;z-index:99999;
    display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden;}
#train-overlay::before{content:'';position:absolute;inset:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.06) 2px,rgba(0,0,0,0.06) 4px);
    pointer-events:none;}
.train-title{font-family:'Bebas Neue',sans-serif;font-size:5rem;color:#e8b84b;
    letter-spacing:0.12em;text-shadow:0 0 40px rgba(232,184,75,0.6);animation:flicker 0.2s infinite alternate;}
@keyframes flicker{0%{opacity:1;}100%{opacity:0.9;}}
.train-sub{font-size:0.72rem;letter-spacing:0.4em;text-transform:uppercase;color:#444;margin:0.3rem 0 2.5rem 0;}
.rail-wrap{position:relative;width:600px;height:120px;}
.rail{position:absolute;bottom:20px;left:0;right:0;height:4px;background:linear-gradient(to right,#1a1a28,#2a2a3a,#1a1a28);border-radius:2px;}
.rail::before,.rail::after{content:'';position:absolute;top:-8px;left:0;right:0;height:2px;background:repeating-linear-gradient(90deg,#1e1e2e 0px,#1e1e2e 18px,transparent 18px,transparent 30px);}
.rail::after{top:12px;}
/* Sleepers */
.sleeper{position:absolute;bottom:14px;width:6px;height:18px;background:#1e1e2e;border-radius:1px;}
.train-car{position:absolute;bottom:24px;font-size:2.8rem;animation:trainMove 3s linear infinite;filter:drop-shadow(0 0 8px rgba(232,184,75,0.6));}
@keyframes trainMove{0%{left:-80px;}100%{left:640px;}}
/* Smoke particles */
.smoke{position:absolute;border-radius:50%;background:rgba(180,180,200,0.15);
    animation:smokeRise var(--dur) ease-out infinite;
    animation-delay:var(--delay);}
@keyframes smokeRise{
    0%{transform:translate(var(--sx),var(--sy)) scale(0.3);opacity:0.7;}
    100%{transform:translate(calc(var(--sx) - 40px),calc(var(--sy) - 80px)) scale(2.5);opacity:0;}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<iframe src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&mute=0&controls=0"
    style="position:fixed;bottom:-200px;left:-200px;width:1px;height:1px;opacity:0.01;pointer-events:none;"
    allow="autoplay; encrypted-media" frameborder="0"></iframe>
""", unsafe_allow_html=True)

# ══════════ STAGE: TRAIN ANIMATION ══════════
if st.session_state.stage == "f1":
    st.markdown("""
    <div id="train-overlay">
        <div class="train-title">NYC EXPRESS</div>
        <div class="train-sub">Computing optimal fare trajectory</div>
        <div class="rail-wrap">
            <div class="rail"></div>
            <!-- sleepers -->
            <div class="sleeper" style="left:40px"></div><div class="sleeper" style="left:80px"></div>
            <div class="sleeper" style="left:120px"></div><div class="sleeper" style="left:160px"></div>
            <div class="sleeper" style="left:200px"></div><div class="sleeper" style="left:240px"></div>
            <div class="sleeper" style="left:280px"></div><div class="sleeper" style="left:320px"></div>
            <div class="sleeper" style="left:360px"></div><div class="sleeper" style="left:400px"></div>
            <div class="sleeper" style="left:440px"></div><div class="sleeper" style="left:480px"></div>
            <div class="sleeper" style="left:520px"></div><div class="sleeper" style="left:560px"></div>
            <!-- train -->
            <div class="train-car">🚂💨</div>
            <!-- smoke particles -->
            <div class="smoke" style="width:20px;height:20px;--sx:20px;--sy:-20px;--dur:1.2s;--delay:0s;left:30%;top:10px;"></div>
            <div class="smoke" style="width:14px;height:14px;--sx:10px;--sy:-15px;--dur:1.5s;--delay:0.3s;left:32%;top:15px;"></div>
            <div class="smoke" style="width:24px;height:24px;--sx:25px;--sy:-25px;--dur:1.0s;--delay:0.6s;left:28%;top:5px;"></div>
            <div class="smoke" style="width:18px;height:18px;--sx:15px;--sy:-20px;--dur:1.8s;--delay:0.1s;left:34%;top:12px;"></div>
            <div class="smoke" style="width:30px;height:30px;--sx:30px;--sy:-30px;--dur:2.0s;--delay:0.9s;left:26%;top:0px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(5)
    st.session_state.stage = "result"
    st.rerun()

# ══════════ STAGE: FARE RESULT ══════════
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

# ══════════ STAGE: ANIMATED MAP — train with smoke on real route ══════════
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
    lons = [p[0] for p in route]; lats = [p[1] for p in route]
    span = max(max(lons)-min(lons), max(lats)-min(lats))
    zoom = 15 if span<0.01 else 14 if span<0.03 else 13 if span<0.08 else 12 if span<0.2 else 11

    map_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#08080a;overflow:hidden;font-family:'DM Sans',sans-serif;}}
#wrap{{width:100vw;height:100vh;position:relative;}}
#map{{width:100%;height:100%;}}
#topbar{{position:absolute;top:0;left:0;right:0;z-index:20;
    background:rgba(8,8,10,0.88);border-bottom:1px solid #1a1a28;
    display:flex;align-items:center;justify-content:space-between;
    padding:12px 20px;backdrop-filter:blur(10px);}}
#topbar .title{{font-family:'Bebas Neue',cursive;font-size:1.4rem;color:#e8b84b;letter-spacing:0.1em;}}
#topbar .fare-chip{{font-family:'Bebas Neue',cursive;font-size:1.8rem;color:#e8b84b;text-shadow:0 0 20px rgba(232,184,75,0.5);}}
#topbar .addrs{{font-size:0.75rem;color:#444;line-height:1.6;}}
#topbar .addrs span{{color:#888;}}
#progress-wrap{{position:absolute;bottom:0;left:0;right:0;z-index:20;height:4px;background:#111116;}}
#progress-bar{{height:100%;width:0%;background:linear-gradient(to right,#e8b84b,#fff5cc);box-shadow:0 0 8px rgba(232,184,75,0.8);}}
#train-el{{position:absolute;z-index:25;font-size:2.2rem;pointer-events:none;
    transform:translate(-50%,-50%);
    filter:drop-shadow(0 0 10px rgba(232,184,75,0.8));}}
canvas#smoke-canvas{{position:absolute;top:0;left:0;z-index:24;pointer-events:none;}}
#arrival{{display:none;position:absolute;inset:0;z-index:30;
    background:rgba(8,8,10,0.92);backdrop-filter:blur(8px);
    flex-direction:column;align-items:center;justify-content:center;}}
#arrival .big{{font-family:'Bebas Neue',cursive;font-size:6rem;color:#e8b84b;line-height:1;text-shadow:0 0 60px rgba(232,184,75,0.5);}}
#arrival .sub{{font-size:0.8rem;letter-spacing:0.3em;text-transform:uppercase;color:#333;margin-top:0.8rem;}}
#arrival .ico{{font-size:3.5rem;margin-bottom:1rem;animation:sway 1.2s ease-in-out infinite alternate;}}
@keyframes sway{{from{{transform:rotate(-8deg);}}to{{transform:rotate(8deg);}}}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.css" rel="stylesheet">
</head>
<body>
<div id="wrap">
  <div id="topbar">
    <div>
      <div class="title">🚂 NYC EXPRESS ROUTE</div>
      <div class="addrs"><span>📍</span> {pickup_addr}<br><span>🏁</span> {dropoff_addr}</div>
    </div>
    <div class="fare-chip">${fare:.2f}</div>
  </div>
  <div id="map"></div>
  <canvas id="smoke-canvas"></canvas>
  <div id="train-el">🚂</div>
  <div id="arrival">
    <div class="ico">🚉</div>
    <div class="big">ARRIVED!</div>
    <div class="sub">{pax} pax · ${fare:.2f} · New York City</div>
  </div>
  <div id="progress-wrap"><div id="progress-bar"></div></div>
</div>
<script>
const ROUTE = {route_json};
const MID_LAT = {mid_lat}, MID_LON = {mid_lon}, ZOOM = {zoom};
const DURATION_MS = 10000;

const map = new maplibregl.Map({{
  container:'map',
  style:'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  center:[MID_LON,MID_LAT], zoom:ZOOM, interactive:true,
}});

map.on('load',()=>{{
  map.addSource('rs',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'LineString',coordinates:ROUTE}}}}}});
  map.addLayer({{id:'rshadow',type:'line',source:'rs',layout:{{'line-join':'round','line-cap':'round'}},paint:{{'line-color':'#000','line-width':14,'line-opacity':0.5}}}});
  map.addLayer({{id:'rline',type:'line',source:'rs',layout:{{'line-join':'round','line-cap':'round'}},paint:{{'line-color':'#e8b84b','line-width':4,'line-opacity':1}}}});
  map.addSource('pu',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'Point',coordinates:ROUTE[0]}}}}}});
  map.addLayer({{id:'pudot',type:'circle',source:'pu',paint:{{'circle-radius':10,'circle-color':'#22c55e','circle-stroke-color':'#fff','circle-stroke-width':2}}}});
  map.addSource('do',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'Point',coordinates:ROUTE[ROUTE.length-1]}}}}}});
  map.addLayer({{id:'dodot',type:'circle',source:'do',paint:{{'circle-radius':10,'circle-color':'#ef4444','circle-stroke-color':'#fff','circle-stroke-width':2}}}});
  startAnim();
}});

const canvas = document.getElementById('smoke-canvas');
const ctx = canvas.getContext('2d');
function resize(){{ canvas.width=window.innerWidth; canvas.height=window.innerHeight; }}
resize(); window.addEventListener('resize',resize);

const trainEl   = document.getElementById('train-el');
const progEl    = document.getElementById('progress-bar');
const arrivalEl = document.getElementById('arrival');

// Smoke particle system
let particles = [];
function spawnSmoke(px, py){{
  for(let i=0;i<3;i++){{
    particles.push({{
      x: px + (Math.random()-0.5)*8,
      y: py - 10,
      vx: (Math.random()-0.5)*0.8 - 0.5,
      vy: -(Math.random()*1.2 + 0.4),
      r:  Math.random()*8 + 5,
      alpha: Math.random()*0.4 + 0.3,
      life: 1.0,
      decay: Math.random()*0.012 + 0.008,
    }});
  }}
}}

function updateSmoke(){{
  ctx.clearRect(0,0,canvas.width,canvas.height);
  particles = particles.filter(p=>p.life>0);
  for(const p of particles){{
    p.x += p.vx; p.y += p.vy;
    p.r  += 0.3;
    p.life -= p.decay;
    p.alpha = p.life * 0.45;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
    ctx.fillStyle = `rgba(190,190,210,${{p.alpha}})`;
    ctx.fill();
  }}
}}

function lerp(a,b,t){{ return a+(b-a)*t; }}
function posAt(t){{
  const idx = t*(ROUTE.length-1);
  const i = Math.floor(idx), f = idx-i;
  const n = Math.min(i+1,ROUTE.length-1);
  return [lerp(ROUTE[i][0],ROUTE[n][0],f), lerp(ROUTE[i][1],ROUTE[n][1],f)];
}}
function toScreen(lon,lat){{
  const pt = map.project([lon,lat]);
  return [pt.x, pt.y];
}}

function startAnim(){{
  const t0 = performance.now();
  let done = false;
  function frame(now){{
    const t = Math.min((now-t0)/DURATION_MS, 1);
    progEl.style.width = (t*100)+'%';

    const [lon,lat] = posAt(t);
    const [px,py]   = toScreen(lon,lat);

    // angle
    const t2 = Math.min(t+0.004,1);
    const [l2,a2] = posAt(t2);
    const [px2,py2] = toScreen(l2,a2);
    const angle = Math.atan2(py2-py,px2-px)*180/Math.PI;

    trainEl.style.left = px+'px';
    trainEl.style.top  = py+'px';
    trainEl.style.transform = `translate(-50%,-50%) rotate(${{angle}}deg)`;

    // spawn smoke every 3 frames
    if(Math.round(t*1000)%3===0) spawnSmoke(px,py);
    updateSmoke();

    if(t<1){{ requestAnimationFrame(frame); }}
    else if(!done){{
      done=true;
      trainEl.style.display='none';
      arrivalEl.style.display='flex';
    }}
  }}
  requestAnimationFrame(frame);
}}
</script>
</body></html>"""

    st.components.v1.html(map_html, height=700, scrolling=False)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔄  NEW RIDE"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()

# ══════════ STAGE: FORM ══════════
else:
    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.markdown('<div class="hero-title">NYC TAXI<br>FARE</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-sub">All aboard · NYC speed</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sec">⏰ Date & Time</div>', unsafe_allow_html=True)
        cd, ct = st.columns(2)
        with cd:
            pickup_date = st.date_input("Date", value=datetime.now().date(), label_visibility="collapsed")
        with ct:
            hours = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
            default_time = f"{datetime.now().strftime('%H')}:{'00' if int(datetime.now().strftime('%M'))<30 else '30'}"
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

        if st.button("🚂  ALL ABOARD"):
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
        st.markdown('<div class="sec" style="margin-top:0">🗺️ NYC Preview</div>', unsafe_allow_html=True)
        st.pydeck_chart(pdk.Deck(
            layers=[],
            initial_view_state=pdk.ViewState(latitude=40.7549, longitude=-73.9840, zoom=12, pitch=0),
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        ), width="stretch", height=580)

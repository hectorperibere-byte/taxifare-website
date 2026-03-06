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

/* TRAIN OVERLAY — full canvas 3D scene */
#train-overlay{position:fixed;inset:0;background:#08080a;z-index:99999;overflow:hidden;}
#train-canvas{position:absolute;inset:0;width:100%;height:100%;}
#train-ui{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding-top:10vh;pointer-events:none;}
.train-title{font-family:'Bebas Neue',sans-serif;font-size:5.5rem;color:#e8b84b;letter-spacing:0.14em;
    text-shadow:0 0 60px rgba(232,184,75,0.7),0 0 120px rgba(232,184,75,0.3);
    animation:titlePulse 2s ease-in-out infinite alternate;}
@keyframes titlePulse{0%{text-shadow:0 0 40px rgba(232,184,75,0.5);}100%{text-shadow:0 0 80px rgba(232,184,75,0.9),0 0 140px rgba(232,184,75,0.4);}}
.train-sub{font-size:0.75rem;letter-spacing:0.5em;text-transform:uppercase;color:#555;margin:0.6rem 0 0 0;}
#fare-loading{position:absolute;bottom:12vh;left:50%;transform:translateX(-50%);
    font-family:'Bebas Neue',sans-serif;font-size:1.1rem;color:#333;letter-spacing:0.25em;
    animation:blink 1s step-end infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0;}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<iframe src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&mute=0&controls=0"
    style="position:fixed;bottom:-200px;left:-200px;width:1px;height:1px;opacity:0.01;pointer-events:none;"
    allow="autoplay; encrypted-media" frameborder="0"></iframe>
""", unsafe_allow_html=True)

# ══════════ STAGE: TRAIN ANIMATION ══════════
if st.session_state.stage == "f1":
    st.components.v1.html("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#08080a; overflow:hidden; }
#c { display:block; width:100vw; height:100vh; }
#ui {
  position:fixed; top:0; left:0; right:0;
  display:flex; flex-direction:column; align-items:center; padding-top:8vh;
  pointer-events:none;
}
.title {
  font-family:'Bebas Neue',cursive; font-size:5rem; color:#e8b84b;
  letter-spacing:0.14em;
  text-shadow:0 0 60px rgba(232,184,75,0.8), 0 0 120px rgba(232,184,75,0.3);
  animation:glow 2s ease-in-out infinite alternate;
}
@keyframes glow {
  from { text-shadow:0 0 40px rgba(232,184,75,0.5); }
  to   { text-shadow:0 0 100px rgba(232,184,75,1), 0 0 200px rgba(232,184,75,0.4); }
}
.sub { font-size:0.7rem; letter-spacing:0.5em; text-transform:uppercase; color:#444; margin-top:0.5rem; }
#dot { position:fixed; bottom:12vh; left:50%; transform:translateX(-50%);
  font-family:'Bebas Neue',cursive; font-size:1rem; color:#2a2a2a; letter-spacing:0.3em;
  animation:blink 1.2s step-end infinite; }
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0;} }
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet">
</head>
<body>
<canvas id="c"></canvas>
<div id="ui">
  <div class="title">NYC EXPRESS</div>
  <div class="sub">Computing optimal fare trajectory</div>
</div>
<div id="dot">LOADING FARE ···</div>

<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
resize();
window.addEventListener('resize', resize);

// ── TRAIN HORN (Web Audio API) ─────────────────────────────────────────────
function playHorn() {
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    function tone(freq, start, dur, vol) {
      const osc  = ac.createOscillator();
      const gain = ac.createGain();
      osc.connect(gain); gain.connect(ac.destination);
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, ac.currentTime + start);
      gain.gain.setValueAtTime(0, ac.currentTime + start);
      gain.gain.linearRampToValueAtTime(vol, ac.currentTime + start + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + start + dur);
      osc.start(ac.currentTime + start);
      osc.stop(ac.currentTime + start + dur + 0.1);
    }
    // Classic train horn chord: F, Ab, C, Eb (minor 7th)
    tone(174, 0.0, 0.8, 0.25);
    tone(207, 0.0, 0.8, 0.20);
    tone(261, 0.0, 0.8, 0.18);
    tone(311, 0.0, 0.8, 0.15);
    tone(174, 1.1, 1.4, 0.30);
    tone(207, 1.1, 1.4, 0.22);
    tone(261, 1.1, 1.4, 0.20);
    tone(311, 1.1, 1.4, 0.18);
  } catch(e) {}
}

// ── SCENE SETUP ────────────────────────────────────────────────────────────
// 3D perspective
const VP = { x: 0.5, y: 0.55 }; // vanishing point (relative)
const RAIL_SPREAD = 0.18;        // half-width at bottom (relative)
const HORIZON_Y   = 0.40;        // horizon at 40% height

// Smoke particles
let smokes = [];
function spawnSmoke(x, y, big) {
  for (let i = 0; i < (big ? 6 : 2); i++) {
    smokes.push({
      x: x + (Math.random()-0.5)*30,
      y: y + (Math.random()-0.5)*10,
      vx: (Math.random()-0.5)*0.6 - 0.2,
      vy: -(Math.random()*1.5 + 0.5),
      r:  Math.random()*18 + 12,
      alpha: Math.random()*0.5 + 0.3,
      life: 1.0,
      decay: Math.random()*0.008 + 0.004,
      gray: Math.floor(Math.random()*40 + 160),
    });
  }
}

// Speed lines (background atmosphere)
let speedLines = [];
for (let i = 0; i < 30; i++) {
  speedLines.push({
    x: Math.random(), y: Math.random(),
    len: Math.random()*0.12 + 0.04,
    speed: Math.random()*0.003 + 0.001,
    alpha: Math.random()*0.15 + 0.03,
  });
}

// Stars
let stars = [];
for (let i = 0; i < 120; i++) {
  stars.push({
    x: Math.random(), y: Math.random() * HORIZON_Y,
    r: Math.random()*1.2 + 0.3,
    twinkle: Math.random()*Math.PI*2,
    speed: Math.random()*0.03 + 0.01,
  });
}

// Ground tiles (perspective grid)
function drawGround() {
  const W = canvas.width, H = canvas.height;
  const vx = VP.x * W, vy = HORIZON_Y * H;
  const spread = RAIL_SPREAD * W;

  // Sky gradient
  const sky = ctx.createLinearGradient(0,0,0,vy);
  sky.addColorStop(0,  '#010108');
  sky.addColorStop(1,  '#0c0c18');
  ctx.fillStyle = sky; ctx.fillRect(0,0,W,vy);

  // Ground
  const gnd = ctx.createLinearGradient(0,vy,0,H);
  gnd.addColorStop(0,  '#0d0d12');
  gnd.addColorStop(1,  '#080810');
  ctx.fillStyle = gnd; ctx.fillRect(0,vy,W,H-vy);

  // Perspective rail ties
  const tieCount = 22;
  for (let i = 0; i < tieCount; i++) {
    const t = i / tieCount;
    const tEased = Math.pow(t, 1.8); // perspective squish
    const yy = vy + tEased * (H - vy);
    const halfW = spread * tEased + 4;
    ctx.fillStyle = `rgba(25,25,40,${0.4 + t*0.5})`;
    ctx.fillRect(vx - halfW - 4, yy - 3, (halfW+4)*2, 6);

    // Tie highlight
    ctx.fillStyle = `rgba(40,40,60,${0.3 + t*0.4})`;
    ctx.fillRect(vx - halfW - 4, yy - 1.5, (halfW+4)*2, 2);
  }

  // Rails
  function rail(side) {
    ctx.beginPath();
    ctx.moveTo(vx, vy);
    ctx.lineTo(vx + side * (spread + 4), H);
    const rg = ctx.createLinearGradient(0, vy, 0, H);
    rg.addColorStop(0, 'rgba(232,184,75,0.1)');
    rg.addColorStop(0.5, 'rgba(180,150,60,0.6)');
    rg.addColorStop(1, 'rgba(232,184,75,0.9)');
    ctx.strokeStyle = rg;
    ctx.lineWidth = 4;
    ctx.stroke();
  }
  rail(-1); rail(1);
}

// 3D train drawing
let trainX = -0.3; // -0.3 = far left (off screen), 1.3 = far right
const TRAIN_SPEED = 0.018; // slower
let hornFired = false;
let hornFired2 = false;

function drawTrain(tx) {
  const W = canvas.width, H = canvas.height;
  const vx = VP.x * W, vy = HORIZON_Y * H;
  const spread = RAIL_SPREAD * W;

  // tx in [0,1] → horizontal position from left to right
  // Compute perspective: train moves from horizon toward bottom-left or bottom-right
  // We simulate train coming from distant left and passing across
  const perspT = Math.max(0, Math.min(tx, 1));

  // As train moves right (0→1), it gets bigger and lower
  const scale  = 0.18 + perspT * 0.55; // size multiplier
  const trainY = vy + perspT * (H - vy) * 0.7;
  const xPos   = vx - spread*0.6 + tx * (W * 0.9);

  // Train body dimensions
  const bodyW  = (260 + perspT * 180) * scale;
  const bodyH  = (55 + perspT * 35) * scale;

  const bx = xPos - bodyW * 0.3; // offset so front leads
  const by = trainY - bodyH;

  // Shadow
  ctx.save();
  ctx.globalAlpha = 0.3 * perspT;
  ctx.fillStyle = '#000';
  ctx.beginPath();
  ctx.ellipse(bx + bodyW*0.5, trainY + 6*scale, bodyW*0.5, 10*scale, 0, 0, Math.PI*2);
  ctx.fill();
  ctx.restore();

  // Wheels (4 pairs)
  const wheelR = 11 * scale;
  const wheelY = trainY + 2*scale;
  const wheelPositions = [0.08, 0.25, 0.60, 0.80];
  wheelPositions.forEach(wp => {
    const wx = bx + bodyW * wp;
    // Wheel
    ctx.beginPath(); ctx.arc(wx, wheelY, wheelR, 0, Math.PI*2);
    ctx.fillStyle = '#1a1a28'; ctx.fill();
    ctx.strokeStyle = '#e8b84b'; ctx.lineWidth = 2*scale; ctx.stroke();
    // Spoke
    const spAngle = (Date.now()/200) * (0.5 + perspT);
    for (let s=0; s<4; s++) {
      const a = spAngle + s * Math.PI/2;
      ctx.beginPath();
      ctx.moveTo(wx + Math.cos(a)*wheelR*0.3, wheelY + Math.sin(a)*wheelR*0.3);
      ctx.lineTo(wx + Math.cos(a)*wheelR*0.85, wheelY + Math.sin(a)*wheelR*0.85);
      ctx.strokeStyle = 'rgba(232,184,75,0.7)'; ctx.lineWidth = 1.5*scale; ctx.stroke();
    }
  });

  // Main body
  const bodyGrad = ctx.createLinearGradient(bx, by, bx, by + bodyH);
  bodyGrad.addColorStop(0,   '#2a2a3a');
  bodyGrad.addColorStop(0.3, '#1e1e2c');
  bodyGrad.addColorStop(1,   '#111118');
  ctx.fillStyle = bodyGrad;
  ctx.beginPath();
  ctx.roundRect(bx, by, bodyW, bodyH, 8*scale);
  ctx.fill();

  // Body border
  ctx.strokeStyle = 'rgba(232,184,75,0.25)'; ctx.lineWidth = 1.5*scale; ctx.stroke();

  // Gold stripe
  const stripeY = by + bodyH*0.55;
  const stripeGrad = ctx.createLinearGradient(bx,0,bx+bodyW,0);
  stripeGrad.addColorStop(0,   'rgba(232,184,75,0)');
  stripeGrad.addColorStop(0.1, 'rgba(232,184,75,0.8)');
  stripeGrad.addColorStop(0.9, 'rgba(232,184,75,0.8)');
  stripeGrad.addColorStop(1,   'rgba(232,184,75,0)');
  ctx.fillStyle = stripeGrad;
  ctx.fillRect(bx, stripeY, bodyW, 3*scale);

  // Windows (6)
  const winW = 20*scale, winH = 14*scale;
  const winY = by + bodyH*0.18;
  for (let w=0; w<6; w++) {
    const winX = bx + bodyW*0.08 + w * (bodyW*0.14);
    const wGrad = ctx.createLinearGradient(winX, winY, winX, winY+winH);
    const lit = Math.random() > 0.4;
    wGrad.addColorStop(0, lit ? 'rgba(255,240,180,0.9)' : 'rgba(30,30,50,0.9)');
    wGrad.addColorStop(1, lit ? 'rgba(200,160,80,0.7)'  : 'rgba(15,15,30,0.8)');
    ctx.fillStyle = wGrad;
    ctx.beginPath(); ctx.roundRect(winX, winY, winW, winH, 3*scale); ctx.fill();
    ctx.strokeStyle = 'rgba(232,184,75,0.3)'; ctx.lineWidth = scale; ctx.stroke();
  }

  // Cabin / locomotive front
  const cabW = 42*scale, cabH = bodyH * 1.15;
  const cabX = bx + bodyW - cabW;
  const cabY = by - cabH * 0.15;
  const cabGrad = ctx.createLinearGradient(cabX, cabY, cabX+cabW, cabY);
  cabGrad.addColorStop(0, '#1e1e2c');
  cabGrad.addColorStop(1, '#2d2d40');
  ctx.fillStyle = cabGrad;
  ctx.beginPath(); ctx.roundRect(cabX, cabY, cabW, cabH, 6*scale); ctx.fill();
  ctx.strokeStyle = 'rgba(232,184,75,0.4)'; ctx.lineWidth = 1.5*scale; ctx.stroke();

  // Headlight beam
  const hlX = cabX + cabW - 2*scale;
  const hlY = cabY + cabH * 0.3;
  const beam = ctx.createRadialGradient(hlX, hlY, 0, hlX, hlY, 80*scale);
  beam.addColorStop(0, 'rgba(255,250,210,0.9)');
  beam.addColorStop(0.1,'rgba(232,184,75,0.4)');
  beam.addColorStop(1,  'rgba(232,184,75,0)');
  ctx.fillStyle = beam;
  ctx.beginPath(); ctx.arc(hlX, hlY, 80*scale, 0, Math.PI*2); ctx.fill();
  // Headlight dot
  ctx.beginPath(); ctx.arc(hlX, hlY, 5*scale, 0, Math.PI*2);
  ctx.fillStyle = '#fff8e0'; ctx.fill();

  // Chimney + smoke spawn point
  const chimneyX = cabX + cabW*0.3;
  const chimneyY = cabY - 14*scale;
  ctx.fillStyle = '#1a1a28';
  ctx.fillRect(chimneyX - 5*scale, chimneyY, 10*scale, 14*scale);
  ctx.strokeStyle = 'rgba(232,184,75,0.3)'; ctx.lineWidth = scale; ctx.stroke();

  // Connecting rods animation
  const rodPhase = Date.now()/180;
  ctx.beginPath();
  ctx.moveTo(bx + bodyW*0.08 + Math.cos(rodPhase)*8*scale, wheelY - wheelR*0.5);
  ctx.lineTo(bx + bodyW*0.25 + Math.cos(rodPhase+1.2)*8*scale, wheelY - wheelR*0.5);
  ctx.lineTo(bx + bodyW*0.60 + Math.cos(rodPhase+2.4)*8*scale, wheelY - wheelR*0.5);
  ctx.strokeStyle = 'rgba(232,184,75,0.5)'; ctx.lineWidth = 3*scale; ctx.stroke();

  return { smokeX: chimneyX, smokeY: chimneyY };
}

// Stars
function drawStars(dt) {
  stars.forEach(s => {
    s.twinkle += s.speed;
    const a = 0.4 + Math.sin(s.twinkle)*0.3;
    ctx.beginPath(); ctx.arc(s.x*canvas.width, s.y*canvas.height, s.r, 0, Math.PI*2);
    ctx.fillStyle = `rgba(255,255,255,${a})`; ctx.fill();
  });
}

// City skyline
function drawSkyline() {
  const W = canvas.width, H = canvas.height;
  const vy = HORIZON_Y * H;
  ctx.save();
  ctx.globalAlpha = 0.18;
  const buildings = [
    {x:0.02,w:0.04,h:0.20},{x:0.07,w:0.03,h:0.28},{x:0.11,w:0.05,h:0.15},
    {x:0.17,w:0.04,h:0.32},{x:0.22,w:0.06,h:0.22},{x:0.29,w:0.03,h:0.38},
    {x:0.34,w:0.05,h:0.25},{x:0.40,w:0.04,h:0.18},{x:0.45,w:0.07,h:0.30},
    {x:0.54,w:0.04,h:0.42},{x:0.59,w:0.05,h:0.20},{x:0.65,w:0.06,h:0.28},
    {x:0.72,w:0.04,h:0.35},{x:0.77,w:0.05,h:0.18},{x:0.83,w:0.04,h:0.24},
    {x:0.88,w:0.06,h:0.30},{x:0.95,w:0.04,h:0.16},
  ];
  buildings.forEach(b => {
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(b.x*W, vy - b.h*vy, b.w*W, b.h*vy);
    // windows
    ctx.fillStyle = 'rgba(232,184,75,0.6)';
    for (let wy=0; wy<b.h*vy-8; wy+=10) {
      for (let wx=3; wx<b.w*W-3; wx+=8) {
        if (Math.random()>0.5) ctx.fillRect(b.x*W+wx, vy-b.h*vy+wy+4, 4, 5);
      }
    }
  });
  ctx.restore();
}

// Main loop
let last = 0;
function loop(ts) {
  const dt = (ts - last) / 1000; last = ts;
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0,0,W,H);

  drawGround();
  drawStars(dt);
  drawSkyline();

  // Speed lines
  speedLines.forEach(sl => {
    sl.x -= sl.speed;
    if (sl.x < -sl.len) sl.x = 1 + sl.len;
    ctx.beginPath();
    ctx.moveTo(sl.x*W, sl.y*H);
    ctx.lineTo((sl.x+sl.len)*W, sl.y*H);
    ctx.strokeStyle = `rgba(232,184,75,${sl.alpha})`;
    ctx.lineWidth = 1; ctx.stroke();
  });

  trainX += TRAIN_SPEED * (60*dt);
  if (trainX > 1.3) trainX = -0.3;

  // Horn at t=0.1 and t=0.6
  const normT = (trainX + 0.3) / 1.6;
  if (!hornFired  && normT > 0.1) { hornFired  = true; playHorn(); }
  if (!hornFired2 && normT > 0.65){ hornFired2 = true; playHorn(); }
  if (normT < 0.05) { hornFired = false; hornFired2 = false; }

  const { smokeX, smokeY } = drawTrain(trainX);

  // Spawn smoke
  if (Math.random() < 0.4) spawnSmoke(smokeX, smokeY, false);

  // Update + draw smoke
  smokes = smokes.filter(s => s.life > 0);
  smokes.forEach(s => {
    s.x += s.vx; s.y += s.vy; s.r += 0.4;
    s.life -= s.decay;
    s.alpha = s.life * 0.5;
    const sg = ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r);
    sg.addColorStop(0, `rgba(${s.gray},${s.gray},${s.gray+10},${s.alpha})`);
    sg.addColorStop(1, `rgba(${s.gray},${s.gray},${s.gray+10},0)`);
    ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
    ctx.fillStyle = sg; ctx.fill();
  });

  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script>
</body></html>
    """, height=700, scrolling=False)
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

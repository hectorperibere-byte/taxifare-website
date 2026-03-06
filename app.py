import streamlit as st
import requests
import pydeck as pdk
import json
from datetime import datetime
import time
import streamlit.components.v1

st.set_page_config(page_title="NYC TAXI FARE", page_icon="\U0001f682", layout="wide")
for k, v in [("stage","form"),("fare_data",None)]:
    if k not in st.session_state: st.session_state[k]=v

@st.cache_data(show_spinner=False)
def geocode(address:str):
    try:
        r=requests.get("https://nominatim.openstreetmap.org/search",
            params={"q":f"{address}, New York, USA","format":"json","limit":1},
            headers={"User-Agent":"nyc-taxi-fare/1.0"},timeout=10)
        res=r.json()
        if res: return float(res[0]["lat"]),float(res[0]["lon"])
    except: pass
    return None,None

@st.cache_data(show_spinner=False)
def get_route(plat,plon,dlat,dlon):
    try:
        r=requests.get(f"http://router.project-osrm.org/route/v1/driving/{plon},{plat};{dlon},{dlat}",
            params={"overview":"full","geometries":"geojson"},timeout=8)
        data=r.json()
        if data.get("code")=="Ok": return data["routes"][0]["geometry"]["coordinates"]
    except: pass
    return [[plon,plat],[dlon,dlat]]

def get_fare(pickup_dt,plat,plon,dlat,dlon,pax):
    try:
        r=requests.get("https://taxifare.lewagon.ai/predict",
            params={"pickup_datetime":pickup_dt,"pickup_latitude":plat,"pickup_longitude":plon,
                    "dropoff_latitude":dlat,"dropoff_longitude":dlon,"passenger_count":pax},timeout=10)
        r.raise_for_status(); data=r.json()
        for key in ("fare","fare_amount","prediction","predicted_fare"):
            if key in data: return float(data[key]),None
        for v in data.values():
            try: return float(v),None
            except: pass
        return None,f"Bad response: {data}"
    except Exception as e: return None,str(e)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:#08080a;color:#f0ede8;}
.stApp{background:#08080a;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:2rem 2.5rem !important;max-width:1400px !important;}
.hero-title{font-family:'Bebas Neue',sans-serif;font-size:4rem;color:#f0ede8;letter-spacing:.08em;line-height:1;}
.hero-sub{font-size:.9rem;color:#444;font-weight:300;margin-top:.3rem;}
.sec{font-size:.65rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#e8b84b;margin:1.2rem 0 .4rem 0;}
.divider{border:none;border-top:1px solid #161620;margin:1rem 0;}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,div[data-testid="stSelectbox"] div[data-baseweb="select"]
{background:#111116 !important;border:1px solid #222230 !important;border-radius:10px !important;color:#f0ede8 !important;}
div[data-testid="stButton"]>button{background:linear-gradient(135deg,#e8b84b,#d4a030) !important;
color:#08080a !important;font-family:'Bebas Neue',sans-serif !important;font-size:1.3rem !important;
letter-spacing:.12em !important;border:none !important;border-radius:12px !important;padding:.9rem 2rem !important;width:100% !important;}
div[data-testid="stButton"]>button:hover{opacity:.88 !important;}
</style>""", unsafe_allow_html=True)

st.markdown("""<iframe src="https://www.youtube.com/embed/QFcv5Ma8u8k?autoplay=1&loop=1&playlist=QFcv5Ma8u8k&mute=0&controls=0"
style="position:fixed;bottom:-200px;left:-200px;width:1px;height:1px;opacity:.01;pointer-events:none;"
allow="autoplay; encrypted-media" frameborder="0"></iframe>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# STAGE: IMMERSIVE 3D WAITING ANIMATION
# ═══════════════════════════════════════════════
if st.session_state.stage == "f1":
    _WAIT_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#020208;overflow:hidden}
#c{display:block;width:100vw;height:100vh}
#ui{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;padding-top:7vh;pointer-events:none}
#title{font-family:'Bebas Neue',cursive;font-size:5.5rem;color:#e8b84b;letter-spacing:.16em;animation:glow 1.8s ease-in-out infinite alternate}
@keyframes glow{from{text-shadow:0 0 40px rgba(232,184,75,.5)}to{text-shadow:0 0 120px rgba(232,184,75,1),0 0 240px rgba(232,184,75,.5)}}
#sub{font-size:.72rem;letter-spacing:.5em;text-transform:uppercase;color:#444;margin-top:.7rem}
#ticker{position:fixed;bottom:8vh;left:50%;transform:translateX(-50%);font-family:'Bebas Neue',cursive;font-size:.9rem;color:#222;letter-spacing:.4em;animation:blink 1s step-end infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300&display=swap" rel="stylesheet">
</head><body>
<canvas id="c"></canvas>
<div id="ui"><div id="title">NYC EXPRESS</div><div id="sub">Computing your fare</div></div>
<div id="ticker">CALCULATING FARE ...</div>
<script>
const c=document.getElementById('c'),g=c.getContext('2d');
function resize(){c.width=innerWidth;c.height=innerHeight}
resize();window.addEventListener('resize',resize);

/* ── AUDIO ── */
function horn(delay){
  try{
    const A=new(window.AudioContext||window.webkitAudioContext)();
    [146,174,207,261,311,392].forEach((f,i)=>{
      const o=A.createOscillator(),gn=A.createGain(),w=A.createWaveShaper();
      const k=new Float32Array(256);for(let j=0;j<256;j++){const x=j*2/256-1;k[j]=x*(Math.abs(x)<.5?2:.9)}
      w.curve=k;o.connect(w);w.connect(gn);gn.connect(A.destination);
      o.type='sawtooth';o.frequency.value=f;
      const t=A.currentTime+delay+i*.04;
      gn.gain.setValueAtTime(0,t);gn.gain.linearRampToValueAtTime(.16,t+.06);
      gn.gain.setValueAtTime(.16,t+1.3);gn.gain.exponentialRampToValueAtTime(.001,t+2.2);
      o.start(t);o.stop(t+2.3);
    });
    const buf=A.createBuffer(1,A.sampleRate*.7,A.sampleRate);
    const d=buf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*.5;
    const s=A.createBufferSource(),gn=A.createGain(),fl=A.createBiquadFilter();
    fl.type='bandpass';fl.frequency.value=650;fl.Q.value=.45;
    s.buffer=buf;s.connect(fl);fl.connect(gn);gn.connect(A.destination);
    gn.gain.setValueAtTime(.12,A.currentTime+delay);gn.gain.exponentialRampToValueAtTime(.001,A.currentTime+delay+.8);
    s.start(A.currentTime+delay);s.stop(A.currentTime+delay+.9);
  }catch(e){}
}
function clack(){
  try{
    const A=new(window.AudioContext||window.webkitAudioContext)();
    const o=A.createOscillator(),gn=A.createGain();
    o.connect(gn);gn.connect(A.destination);o.type='square';o.frequency.value=85+Math.random()*55;
    gn.gain.setValueAtTime(.16,A.currentTime);gn.gain.exponentialRampToValueAtTime(.001,A.currentTime+.09);
    o.start();o.stop(A.currentTime+.1);
  }catch(e){}
}

/* ── PARTICLES ── */
let S=[],SP=[],EM=[];
function smoke(x,y){for(let i=0;i<5;i++)S.push({x:x+(Math.random()-.5)*20,y,vx:(Math.random()-.5)*.6-.3,vy:-(Math.random()*2+.7),r:Math.random()*18+10,life:1,decay:Math.random()*.007+.004,gray:130+Math.floor(Math.random()*60)})}
function spark(x,y){for(let i=0;i<5;i++){const a=Math.random()*Math.PI*2,sp=Math.random()*6+2;SP.push({x,y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp-2,life:1,decay:.025+Math.random()*.02,r:.8+Math.random()*2.5})}}
function ember(x,y){for(let i=0;i<3;i++)EM.push({x,y,vx:(Math.random()-.5)*3,vy:-(Math.random()*4+1),life:1,decay:.01+Math.random()*.015,r:.5+Math.random()*2,hue:15+Math.floor(Math.random()*30)})}

/* ── SCENE ── */
const H0=.40;
const STARS=Array.from({length:200},()=>({x:Math.random(),y:Math.random()*H0,r:.2+Math.random()*1.5,tw:Math.random()*Math.PI*2,spd:.008+Math.random()*.04}));
const BLDS=[[.00,.05,.30],[.06,.03,.45],[.10,.06,.22],[.17,.04,.55],[.22,.05,.28],[.28,.03,.65],[.32,.06,.35],[.39,.04,.20],[.44,.07,.48],[.52,.04,.70],[.57,.05,.32],[.63,.06,.44],[.70,.04,.58],[.75,.05,.26],[.81,.04,.40],[.86,.06,.50],[.93,.04,.22],[.98,.03,.35]].map(([x,w,h])=>({x,w,h,wins:Array.from({length:80},()=>Math.random()>.45)}));

function scene(){
  const W=c.width,H=c.height,vx=W*.5,vy=H*H0,sp=W*.18;
  let sky=g.createLinearGradient(0,0,0,vy);sky.addColorStop(0,'#010106');sky.addColorStop(1,'#0d0d1e');g.fillStyle=sky;g.fillRect(0,0,W,vy);
  /* nebula */let neb=g.createRadialGradient(vx,vy,0,vx,vy,W*.5);neb.addColorStop(0,'rgba(60,20,100,.15)');neb.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=neb;g.fillRect(0,0,W,vy);
  /* moon */g.beginPath();g.arc(W*.82,H*.065,H*.026,0,Math.PI*2);g.fillStyle='rgba(255,248,205,.68)';g.fill();
  /* moon halo */let mh=g.createRadialGradient(W*.82,H*.065,0,W*.82,H*.065,H*.12);mh.addColorStop(0,'rgba(255,245,190,.1)');mh.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=mh;g.fillRect(0,0,W,vy);
  /* stars */STARS.forEach(s=>{s.tw+=s.spd;g.beginPath();g.arc(s.x*W,s.y*H,s.r*(0.7+Math.sin(s.tw)*.3),0,Math.PI*2);g.fillStyle=`rgba(255,255,255,${.22+Math.sin(s.tw)*.2})`;g.fill()});
  /* buildings */BLDS.forEach((b,bi)=>{
    const bx=b.x*W,bw=b.w*W,bh=b.h*vy,by=vy-bh;
    let bg=g.createLinearGradient(bx,by,bx,vy);bg.addColorStop(0,'#0d0d1c');bg.addColorStop(1,'#060610');g.fillStyle=bg;g.fillRect(bx,by,bw,bh);
    g.strokeStyle='rgba(232,184,75,.04)';g.lineWidth=.7;g.strokeRect(bx,by,bw,bh);
    let wi=0;for(let wy=4;wy<bh-4;wy+=9)for(let wx=3;wx<bw-3;wx+=7){if(b.wins[wi%b.wins.length]){g.fillStyle=`rgba(255,235,150,${.3+Math.sin(Date.now()/3000+bi+wi)*.08})`;g.fillRect(bx+wx,by+wy,4,5)}wi++}
    if(b.h>.4){g.beginPath();g.moveTo(bx+bw/2,by);g.lineTo(bx+bw/2,by-H*.045);g.strokeStyle='rgba(70,70,100,.45)';g.lineWidth=1;g.stroke();const bl=Math.sin(Date.now()/650)>.5;g.beginPath();g.arc(bx+bw/2,by-H*.045,2.5,0,Math.PI*2);g.fillStyle=bl?'rgba(255,50,50,.9)':'rgba(60,10,10,.4)';g.fill()}
  });
  /* ground */let gnd=g.createLinearGradient(0,vy,0,H);gnd.addColorStop(0,'#0b0b14');gnd.addColorStop(1,'#040408');g.fillStyle=gnd;g.fillRect(0,vy,W,H-vy);
  /* ground glow */let gg=g.createRadialGradient(vx,vy,0,vx,vy,sp*2);gg.addColorStop(0,'rgba(232,184,75,.06)');gg.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=gg;g.fillRect(0,vy,W,H-vy);
  /* ties */for(let i=0;i<28;i++){const t=i/28,te=Math.pow(t,1.65),yy=vy+te*(H-vy),hw=sp*te+6;g.fillStyle=`rgba(16,16,28,${.3+t*.65})`;g.fillRect(vx-hw-6,yy-3.5,(hw+6)*2,7);g.fillStyle=`rgba(38,38,55,${.15+t*.3})`;g.fillRect(vx-hw-6,yy-1.5,(hw+6)*2,2)}
  /* rails */[-1,1].forEach(s=>{let rg=g.createLinearGradient(0,vy,0,H);rg.addColorStop(0,'rgba(232,184,75,.04)');rg.addColorStop(.35,'rgba(175,140,50,.45)');rg.addColorStop(1,'rgba(232,184,75,.92)');g.beginPath();g.moveTo(vx,vy);g.lineTo(vx+s*(sp+5),H);g.strokeStyle=rg;g.lineWidth=4.5;g.stroke()});
}

function train3D(tx){
  const W=c.width,H=c.height,vx=W*.5,vy=H*H0,sp=W*.18;
  const pt=Math.max(0,Math.min(tx,1)),sc=.14+pt*.70;
  const tY=vy+pt*(H-vy)*.74,xP=vx-sp*.55+tx*(W*.92);
  const bW=(340+pt*250)*sc,bH=(56+pt*42)*sc,bx=xP-bW*.28,by=tY-bH;

  /* shadow */g.save();g.globalAlpha=.42*pt;g.fillStyle='#000';g.beginPath();g.ellipse(bx+bW*.5,tY+9*sc,bW*.55,15*sc,0,0,Math.PI*2);g.fill();g.restore();

  /* 6 wheel pairs */const wR=14*sc,wY=tY+4*sc,rp=Date.now()/145;
  const wpos=[.06,.18,.34,.52,.69,.84];
  wpos.forEach(wp=>{
    const wx=bx+bW*wp;
    g.save();g.globalAlpha=.3*pt;g.fillStyle='#000';g.beginPath();g.ellipse(wx,wY+wR*.3,wR*.9,wR*.22,0,0,Math.PI*2);g.fill();g.restore();
    g.beginPath();g.arc(wx,wY,wR,0,Math.PI*2);
    let wg=g.createRadialGradient(wx-wR*.35,wY-wR*.35,0,wx,wY,wR);wg.addColorStop(0,'#2e2e4a');wg.addColorStop(1,'#0b0b16');g.fillStyle=wg;g.fill();
    g.strokeStyle='#e8b84b';g.lineWidth=2.5*sc;g.stroke();
    for(let s=0;s<6;s++){const a=rp*(1.2+pt*.5)+s*Math.PI/3;g.beginPath();g.moveTo(wx+Math.cos(a)*wR*.22,wY+Math.sin(a)*wR*.22);g.lineTo(wx+Math.cos(a)*wR*.88,wY+Math.sin(a)*wR*.88);g.strokeStyle='rgba(232,184,75,.82)';g.lineWidth=1.8*sc;g.stroke()}
    g.beginPath();g.arc(wx,wY,wR*.18,0,Math.PI*2);g.fillStyle='#e8b84b';g.fill();
  });
  /* connecting rods */g.beginPath();g.moveTo(bx+bW*wpos[0],wY-wR*.58);wpos.forEach(wp=>g.lineTo(bx+bW*wp,wY-wR*.58));g.strokeStyle='rgba(232,184,75,.65)';g.lineWidth=4*sc;g.stroke();

  /* body */let bg=g.createLinearGradient(bx,by,bx,by+bH);bg.addColorStop(0,'#34344e');bg.addColorStop(.25,'#22223a');bg.addColorStop(.65,'#131320');bg.addColorStop(1,'#07070e');g.fillStyle=bg;g.beginPath();g.roundRect(bx,by,bW,bH,10*sc);g.fill();g.strokeStyle='rgba(232,184,75,.18)';g.lineWidth=1.5*sc;g.stroke();

  /* top face 3D */const tH=10*sc;g.beginPath();g.moveTo(bx,by);g.lineTo(bx+tH*.7,by-tH);g.lineTo(bx+bW+tH*.7,by-tH);g.lineTo(bx+bW,by);g.closePath();g.fillStyle='#262640';g.fill();g.strokeStyle='rgba(232,184,75,.1)';g.lineWidth=sc;g.stroke();

  /* gold stripe */let sg=g.createLinearGradient(bx,0,bx+bW,0);sg.addColorStop(0,'rgba(232,184,75,0)');sg.addColorStop(.06,'rgba(232,184,75,.96)');sg.addColorStop(.94,'rgba(232,184,75,.96)');sg.addColorStop(1,'rgba(232,184,75,0)');g.fillStyle=sg;g.fillRect(bx,by+bH*.52,bW,4.5*sc);

  /* windows */for(let i=0;i<9;i++){const wx2=bx+bW*.05+i*(bW*.105),wy2=by+bH*.16,wW=19*sc,wH=13*sc;const lit=((Date.now()/2100+i*.38)%2)<1.75;let wG=g.createLinearGradient(wx2,wy2,wx2,wy2+wH);wG.addColorStop(0,lit?'rgba(255,245,178,.96)':'rgba(16,16,28,.96)');wG.addColorStop(1,lit?'rgba(195,150,65,.78)':'rgba(7,7,15,.88)');g.fillStyle=wG;g.beginPath();g.roundRect(wx2,wy2,wW,wH,3*sc);g.fill();if(lit){g.fillStyle='rgba(255,255,255,.22)';g.fillRect(wx2+2*sc,wy2+2*sc,wW*.36,wH*.28)}g.strokeStyle='rgba(232,184,75,.28)';g.lineWidth=sc;g.stroke()}

  /* cab */const cW=54*sc,cH=bH*1.2,cX=bx+bW-cW,cY=by-cH*.18;
  let cG=g.createLinearGradient(cX,cY,cX+cW,cY);cG.addColorStop(0,'#1d1d32');cG.addColorStop(1,'#2e2e48');g.fillStyle=cG;g.beginPath();g.roundRect(cX,cY,cW,cH,7*sc);g.fill();g.strokeStyle='rgba(232,184,75,.4)';g.lineWidth=1.5*sc;g.stroke();
  /* cab top */g.beginPath();g.moveTo(cX,cY);g.lineTo(cX+tH*.7,cY-tH);g.lineTo(cX+cW+tH*.7,cY-tH);g.lineTo(cX+cW,cY);g.closePath();g.fillStyle='#222238';g.fill();
  /* cab window */g.fillStyle='rgba(110,185,255,.22)';g.beginPath();g.roundRect(cX+4*sc,cY+5*sc,cW-8*sc,cH*.3,4*sc);g.fill();g.strokeStyle='rgba(232,184,75,.5)';g.lineWidth=sc;g.stroke();
  /* cab window reflection */g.fillStyle='rgba(255,255,255,.14)';g.fillRect(cX+5*sc,cY+6*sc,(cW-8*sc)*.4,cH*.11);

  /* headlight beam */const hlX=cX+cW,hlY=cY+cH*.37;g.save();g.globalAlpha=.6+Math.sin(Date.now()/270)*.09;g.beginPath();g.moveTo(hlX,hlY);g.lineTo(hlX+210*sc,hlY-65*sc);g.lineTo(hlX+210*sc,hlY+65*sc);g.closePath();let bG=g.createLinearGradient(hlX,hlY,hlX+210*sc,hlY);bG.addColorStop(0,'rgba(255,252,200,.38)');bG.addColorStop(1,'rgba(232,184,75,0)');g.fillStyle=bG;g.fill();g.restore();
  g.beginPath();g.arc(hlX,hlY,7*sc,0,Math.PI*2);g.fillStyle='#fffce8';g.fill();
  g.beginPath();g.arc(hlX,hlY,13*sc,0,Math.PI*2);g.fillStyle='rgba(255,248,175,.2)';g.fill();

  /* chimney */const chiX=cX+cW*.38,chiY=cY-17*sc;g.fillStyle='#1c1c2e';g.fillRect(chiX-5.5*sc,chiY,11*sc,17*sc);g.strokeStyle='rgba(232,184,75,.22)';g.lineWidth=sc;g.stroke();
  g.beginPath();g.ellipse(chiX,chiY,9*sc,4.5*sc,0,Math.PI,0);g.fillStyle='#252538';g.fill();

  /* front bumper */g.fillStyle='rgba(232,184,75,.3)';g.fillRect(hlX,cY+cH*.65,4*sc,cH*.22);

  return {chiX,chiY,sparkX:bx+bW*wpos[1],sparkY:wY};
}

/* ── MAIN LOOP ── */
let TX=-0.15,LAST=0,HD=[false,false,false],CT=0;
function loop(ts){
  const dt=Math.min((ts-LAST)/1000,.05);LAST=ts;g.clearRect(0,0,c.width,c.height);
  scene();
  /* speed lines */for(let i=0;i<22;i++){const t=((ts*.00055+i*.046)%1);const al=Math.sin(t*Math.PI)*.09;if(al>.01){g.beginPath();g.moveTo(t*c.width,(i/22)*c.height*.42);g.lineTo((t+.055)*c.width,(i/22)*c.height*.42);g.strokeStyle=`rgba(232,184,75,${al})`;g.lineWidth=1;g.stroke()}}
  TX+=.0075*(60*dt);if(TX>1.28){TX=-0.15;HD=[false,false,false]}
  const nT=(TX+.15)/1.43;
  if(!HD[0]&&nT>.06){HD[0]=true;horn(0)}
  if(!HD[1]&&nT>.55){HD[1]=true;horn(.06)}
  if(!HD[2]&&nT>.90){HD[2]=true;horn(0)}
  CT+=dt;if(CT>.19){CT=0;clack()}
  const {chiX,chiY,sparkX,sparkY}=train3D(TX);
  if(Math.random()<.55)smoke(chiX,chiY);
  if(Math.random()<.12)spark(sparkX,sparkY);
  if(Math.random()<.08)ember(chiX,chiY);
  S=S.filter(s=>s.life>0);S.forEach(s=>{s.x+=s.vx;s.y+=s.vy;s.r+=.55;s.life-=s.decay;let sg=g.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r);sg.addColorStop(0,`rgba(${s.gray},${s.gray},${s.gray+15},${s.life*.53})`);sg.addColorStop(1,`rgba(${s.gray},${s.gray},${s.gray},0)`);g.beginPath();g.arc(s.x,s.y,s.r,0,Math.PI*2);g.fillStyle=sg;g.fill()});
  SP=SP.filter(s=>s.life>0);SP.forEach(s=>{s.x+=s.vx;s.y+=s.vy;s.vy+=.13;s.life-=s.decay;g.beginPath();g.arc(s.x,s.y,s.r*s.life,0,Math.PI*2);g.fillStyle=`rgba(232,184,75,${s.life*.9})`;g.fill()});
  EM=EM.filter(e=>e.life>0);EM.forEach(e=>{e.x+=e.vx;e.y+=e.vy;e.vy+=.06;e.vx*=.98;e.life-=e.decay;g.beginPath();g.arc(e.x,e.y,e.r*e.life,0,Math.PI*2);g.fillStyle=`hsla(${e.hue},100%,65%,${e.life*.82})`;g.fill()});
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script></body></html>"""
    st.components.v1.html(_WAIT_HTML, height=700, scrolling=False)
    time.sleep(5)
    st.session_state.stage = "result"
    st.rerun()

# ═══════════════════════════════════════════════
# STAGE: FARE RESULT
# ═══════════════════════════════════════════════
elif st.session_state.stage == "result" and st.session_state.fare_data:
    d = st.session_state.fare_data
    pax_label = f"{d['pax']} passenger{'s' if d['pax']>1 else ''}"
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;">
        <div style="font-size:.68rem;letter-spacing:.4em;text-transform:uppercase;color:#333;margin-bottom:.5rem;">Estimated Fare</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:10rem;color:#e8b84b;line-height:1;text-shadow:0 0 80px rgba(232,184,75,.35);">${d['pred']:.2f}</div>
        <div style="font-size:.85rem;color:#2a2a2a;letter-spacing:.08em;margin-top:.5rem;">{pax_label} &nbsp;·&nbsp; New York City</div>
    </div>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("\U0001f5fa\ufe0f  VIEW THE ROUTE"):
            st.session_state.stage = "map"
            st.rerun()
        st.markdown("<div style='margin-top:.5rem'></div>", unsafe_allow_html=True)
        if st.button("\U0001f504  NEW RIDE"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()


# ═══════════════════════════════════════════════
# STAGE: 3D TRAIN ON REAL MAP
# ═══════════════════════════════════════════════
elif st.session_state.stage == "map" and st.session_state.fare_data:
    d = st.session_state.fare_data
    route = d.get("route", [[d["plon"],d["plat"]],[d["dlon"],d["dlat"]]])
    mid_lat = (d["plat"]+d["dlat"])/2
    mid_lon = (d["plon"]+d["dlon"])/2
    route_json = json.dumps(route)
    pa = d.get("pickup_address","Pickup")
    da = d.get("dropoff_address","Dropoff")
    fare = d["pred"]
    pax  = d["pax"]
    lons=[p[0] for p in route]; lats=[p[1] for p in route]
    span=max(max(lons)-min(lons), max(lats)-min(lats))
    zoom=15 if span<.01 else 14 if span<.03 else 13 if span<.08 else 12 if span<.2 else 11

    map_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#020208;overflow:hidden}}
#wrap{{width:100vw;height:100vh;position:relative}}
#map{{width:100%;height:100%}}
#topbar{{position:absolute;top:0;left:0;right:0;z-index:20;background:rgba(2,2,8,.92);
border-bottom:1px solid #161624;display:flex;align-items:center;justify-content:space-between;
padding:10px 20px;backdrop-filter:blur(16px)}}
.tbt{{font-family:'Bebas Neue',cursive;font-size:1.3rem;color:#e8b84b;letter-spacing:.1em}}
.tbf{{font-family:'Bebas Neue',cursive;font-size:2rem;color:#e8b84b;text-shadow:0 0 20px rgba(232,184,75,.7)}}
.tba{{font-size:.7rem;color:#333;line-height:1.6}}
.tba b{{color:#555}}
canvas#fx{{position:absolute;top:0;left:0;z-index:22;pointer-events:none}}
#prog{{position:absolute;bottom:0;left:0;right:0;z-index:20;height:5px;background:#08080e}}
#pbar{{height:100%;width:0%;background:linear-gradient(90deg,#6b3a00,#e8b84b,#fffacc,#e8b84b,#6b3a00);
background-size:300% 100%;animation:sh 1.2s linear infinite;box-shadow:0 0 14px rgba(232,184,75,.9)}}
@keyframes sh{{0%{{background-position:100% 0}}100%{{background-position:0 0}}}}
#spd{{position:absolute;bottom:22px;right:20px;z-index:21;background:rgba(2,2,8,.88);
border:1px solid #1a1a28;border-radius:10px;padding:8px 16px;backdrop-filter:blur(10px);text-align:center}}
#spdv{{font-family:'Bebas Neue',cursive;font-size:2rem;color:#e8b84b;line-height:1}}
.spdu{{font-size:.52rem;letter-spacing:.18em;text-transform:uppercase;color:#2a2a3a}}
#arr{{display:none;position:absolute;inset:0;z-index:30;background:rgba(2,2,8,.95);
backdrop-filter:blur(14px);flex-direction:column;align-items:center;justify-content:center}}
.arri{{font-size:4.5rem;margin-bottom:1.2rem;animation:bo .7s ease-in-out infinite alternate}}
@keyframes bo{{from{{transform:translateY(0) rotate(-3deg)}}to{{transform:translateY(-14px) rotate(3deg)}}}}
.arrb{{font-family:'Bebas Neue',cursive;font-size:7rem;color:#e8b84b;line-height:1;
animation:ag 1s ease-in-out infinite alternate}}
@keyframes ag{{from{{text-shadow:0 0 40px rgba(232,184,75,.4)}}to{{text-shadow:0 0 120px rgba(232,184,75,1),0 0 240px rgba(232,184,75,.4)}}}}
.arrs{{font-size:.78rem;letter-spacing:.32em;text-transform:uppercase;color:#222;margin-top:.9rem}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400&display=swap" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@3/dist/maplibre-gl.css" rel="stylesheet">
</head><body>
<div id="wrap">
  <div id="topbar">
    <div>
      <div class="tbt">&#x1F682; NYC EXPRESS &mdash; LIVE ROUTE</div>
      <div class="tba"><b>&#x1F4CD;</b> {pa} &rarr; <b>&#x1F689;</b> {da}</div>
    </div>
    <div class="tbf">${{fare:.2f}}</div>
  </div>
  <div id="map"></div>
  <canvas id="fx"></canvas>
  <div id="spd"><div id="spdv">0</div><div class="spdu">mph</div></div>
  <div id="arr">
    <div class="arri">&#x1F689;</div>
    <div class="arrb">ARRIVED!</div>
    <div class="arrs">{pax} pax &nbsp;&middot;&nbsp; ${fare:.2f} &nbsp;&middot;&nbsp; New York City</div>
  </div>
  <div id="prog"><div id="pbar"></div></div>
</div>
<script>
const ROUTE={route_json};
const ML={mid_lat},MLN={mid_lon},Z={zoom},DUR=18000;

/* ── AUDIO ── */
function horn(){{
  try{{
    const A=new(window.AudioContext||window.webkitAudioContext)();
    [146,174,207,261,311,392].forEach((f,i)=>{{
      const o=A.createOscillator(),gn=A.createGain(),w=A.createWaveShaper();
      const k=new Float32Array(256);for(let j=0;j<256;j++){{const x=j*2/256-1;k[j]=x*(Math.abs(x)<.45?2:.9)}}
      w.curve=k;o.connect(w);w.connect(gn);gn.connect(A.destination);
      o.type='sawtooth';o.frequency.value=f;
      const t=A.currentTime+i*.05;
      gn.gain.setValueAtTime(0,t);gn.gain.linearRampToValueAtTime(.22,t+.07);
      gn.gain.setValueAtTime(.22,t+1.6);gn.gain.exponentialRampToValueAtTime(.001,t+2.6);
      o.start(t);o.stop(t+2.7);
    }});
    const buf=A.createBuffer(1,A.sampleRate*.85,A.sampleRate);
    const d=buf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*.6;
    const s=A.createBufferSource(),gn=A.createGain(),fl=A.createBiquadFilter();
    fl.type='bandpass';fl.frequency.value=500;fl.Q.value=.4;
    s.buffer=buf;s.connect(fl);fl.connect(gn);gn.connect(A.destination);
    gn.gain.setValueAtTime(.15,A.currentTime);gn.gain.exponentialRampToValueAtTime(.001,A.currentTime+1.0);
    s.start();s.stop(A.currentTime+1.1);
  }}catch(e){{}}
}}
function clack(){{
  try{{
    const A=new(window.AudioContext||window.webkitAudioContext)();
    const o=A.createOscillator(),gn=A.createGain();
    o.connect(gn);gn.connect(A.destination);o.type='square';o.frequency.value=80+Math.random()*60;
    gn.gain.setValueAtTime(.2,A.currentTime);gn.gain.exponentialRampToValueAtTime(.001,A.currentTime+.1);
    o.start();o.stop(A.currentTime+.12);
  }}catch(e){{}}
}}

/* ── CANVAS FX ── */
const fx=document.getElementById('fx'),ctx=fx.getContext('2d');
function rsz(){{fx.width=innerWidth;fx.height=innerHeight}}
rsz();window.addEventListener('resize',rsz);

let S=[],SP=[],EM=[];
function smoke(x,y){{for(let i=0;i<5;i++)S.push({{x:x+(Math.random()-.5)*18,y:y+(Math.random()-.5)*8,vx:(Math.random()-.5)*.65-.35,vy:-(Math.random()*2+.7),r:Math.random()*16+10,life:1,decay:.004+Math.random()*.007,gray:130+Math.floor(Math.random()*60)}})}}
function spark(x,y){{for(let i=0;i<6;i++){{const a=Math.random()*Math.PI*2,sp=Math.random()*6+2;SP.push({{x,y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp-1,life:1,decay:.022+Math.random()*.03,r:.8+Math.random()*2.5}})}}}}
function ember(x,y){{for(let i=0;i<3;i++)EM.push({{x,y,vx:(Math.random()-.5)*3,vy:-(Math.random()*4+1),life:1,decay:.01+Math.random()*.015,r:.4+Math.random()*2,hue:15+Math.floor(Math.random()*30)}})}}

/* ── 3D TRAIN DRAW ON CANVAS ── */
function drawTrain(px,py,ang,sc){{
  ctx.save();ctx.translate(px,py);ctx.rotate(ang);
  const bW=180+sc*95,bH=34+sc*22,bx=-bW*.6,by=-bH*.5;

  /* shadow */ctx.save();ctx.globalAlpha=.32*sc;ctx.fillStyle='#000';ctx.beginPath();ctx.ellipse(0,bH*.9,bW*.55,bH*.28,0,0,Math.PI*2);ctx.fill();ctx.restore();

  /* wheels */const wR=11+sc*5.5,wY=bH*.55,rp=Date.now()/140;
  [-0.58,-0.36,.05,.32,.58].forEach(wp=>{{
    const wx=bW*wp;
    ctx.beginPath();ctx.arc(wx,wY,wR,0,Math.PI*2);
    let wg=ctx.createRadialGradient(wx-wR*.32,wY-wR*.32,0,wx,wY,wR);wg.addColorStop(0,'#2e2e4a');wg.addColorStop(1,'#0b0b16');ctx.fillStyle=wg;ctx.fill();
    ctx.strokeStyle='#e8b84b';ctx.lineWidth=2+sc*.5;ctx.stroke();
    for(let s=0;s<6;s++){{const a=rp+s*Math.PI/3;ctx.beginPath();ctx.moveTo(wx+Math.cos(a)*wR*.22,wY+Math.sin(a)*wR*.22);ctx.lineTo(wx+Math.cos(a)*wR*.88,wY+Math.sin(a)*wR*.88);ctx.strokeStyle='rgba(232,184,75,.82)';ctx.lineWidth=1.5;ctx.stroke()}}
    ctx.beginPath();ctx.arc(wx,wY,wR*.17,0,Math.PI*2);ctx.fillStyle='#e8b84b';ctx.fill();
  }});
  ctx.beginPath();ctx.moveTo(bW*-0.58,wY-wR*.55);ctx.lineTo(bW*.58,wY-wR*.55);ctx.strokeStyle='rgba(232,184,75,.6)';ctx.lineWidth=3.5;ctx.stroke();

  /* body */let bg=ctx.createLinearGradient(bx,by,bx,by+bH);bg.addColorStop(0,'#30304c');bg.addColorStop(.3,'#1e1e30');bg.addColorStop(.7,'#101020');bg.addColorStop(1,'#06060e');ctx.fillStyle=bg;ctx.beginPath();ctx.roundRect(bx,by,bW,bH,6);ctx.fill();ctx.strokeStyle='rgba(232,184,75,.18)';ctx.lineWidth=1.5;ctx.stroke();

  /* top 3D */const tH=7;ctx.beginPath();ctx.moveTo(bx,by);ctx.lineTo(bx+tH*.6,by-tH);ctx.lineTo(bx+bW+tH*.6,by-tH);ctx.lineTo(bx+bW,by);ctx.closePath();ctx.fillStyle='#222236';ctx.fill();ctx.strokeStyle='rgba(232,184,75,.1)';ctx.lineWidth=.8;ctx.stroke();

  /* gold stripe */let sg=ctx.createLinearGradient(bx,0,bx+bW,0);sg.addColorStop(0,'rgba(232,184,75,0)');sg.addColorStop(.07,'rgba(232,184,75,.95)');sg.addColorStop(.93,'rgba(232,184,75,.95)');sg.addColorStop(1,'rgba(232,184,75,0)');ctx.fillStyle=sg;ctx.fillRect(bx,by+bH*.52,bW,3.5);

  /* windows */for(let i=0;i<7;i++){{const wx2=bx+bW*.07+i*(bW*.125),wy2=by+bH*.14,wW=16,wH=10;const lit=((Date.now()/2000+i*.35)%2)<1.75;let wG=ctx.createLinearGradient(wx2,wy2,wx2,wy2+wH);wG.addColorStop(0,lit?'rgba(255,244,176,.96)':'rgba(12,12,22,.96)');wG.addColorStop(1,lit?'rgba(195,150,65,.78)':'rgba(5,5,12,.88)');ctx.fillStyle=wG;ctx.beginPath();ctx.roundRect(wx2,wy2,wW,wH,2);ctx.fill();if(lit){{ctx.fillStyle='rgba(255,255,255,.2)';ctx.fillRect(wx2+2,wy2+2,wW*.35,wH*.28)}}ctx.strokeStyle='rgba(232,184,75,.25)';ctx.lineWidth=.7;ctx.stroke()}}

  /* cab */const cW=38,cH=bH*1.16,cX=bx+bW-cW,cY=by-cH*.16;
  ctx.fillStyle='#1c1c2e';ctx.beginPath();ctx.roundRect(cX,cY,cW,cH,5);ctx.fill();ctx.strokeStyle='rgba(232,184,75,.42)';ctx.lineWidth=1.4;ctx.stroke();
  /* cab window */ctx.fillStyle='rgba(105,178,255,.2)';ctx.beginPath();ctx.roundRect(cX+3,cY+4,cW-6,cH*.28,3);ctx.fill();

  /* headlight */const hlX=cX+cW,hlY=cY+cH*.37;ctx.save();ctx.globalAlpha=.65+Math.sin(Date.now()/260)*.1;ctx.beginPath();ctx.moveTo(hlX,hlY);ctx.lineTo(hlX+155,hlY-46);ctx.lineTo(hlX+155,hlY+46);ctx.closePath();let bG=ctx.createLinearGradient(hlX,hlY,hlX+155,hlY);bG.addColorStop(0,'rgba(255,252,198,.34)');bG.addColorStop(1,'rgba(232,184,75,0)');ctx.fillStyle=bG;ctx.fill();ctx.restore();
  ctx.beginPath();ctx.arc(hlX,hlY,5,0,Math.PI*2);ctx.fillStyle='#fffce6';ctx.fill();ctx.beginPath();ctx.arc(hlX,hlY,9,0,Math.PI*2);ctx.fillStyle='rgba(255,248,178,.22)';ctx.fill();

  /* chimney */const chiX=cX+cW*.36,chiY=cY-13;ctx.fillStyle='#1a1a2c';ctx.fillRect(chiX-4,chiY,8,13);ctx.strokeStyle='rgba(232,184,75,.2)';ctx.lineWidth=.8;ctx.stroke();

  ctx.restore();
  /* smoke spawn point (world coords, above chimney rotated) */
  const smokeX=px+Math.cos(ang-Math.PI*.5)*16+Math.cos(ang)*(-bW*.24);
  const smokeY=py+Math.sin(ang-Math.PI*.5)*16+Math.sin(ang)*(-bW*.24);
  return {{smokeX,smokeY}};
}}

/* ── MAP ── */
const map=new maplibregl.Map({{container:'map',style:'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',center:[MLN,ML],zoom:Z,pitch:48,bearing:-12,interactive:true}});
map.on('load',()=>{{
  map.addSource('rs',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'LineString',coordinates:ROUTE}}}}}});
  map.addLayer({{id:'rsh',type:'line',source:'rs',layout:{{'line-join':'round','line-cap':'round'}},paint:{{'line-color':'#000','line-width':18,'line-opacity':.65}}}});
  map.addLayer({{id:'rl',type:'line',source:'rs',layout:{{'line-join':'round','line-cap':'round'}},paint:{{'line-color':'#e8b84b','line-width':5}}}});
  map.addLayer({{id:'rgl',type:'line',source:'rs',layout:{{'line-join':'round','line-cap':'round'}},paint:{{'line-color':'#fffacc','line-width':2,'line-opacity':.5,'line-blur':4}}}});
  map.addSource('pu',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'Point',coordinates:ROUTE[0]}}}}}});
  map.addLayer({{id:'pud',type:'circle',source:'pu',paint:{{'circle-radius':14,'circle-color':'#22c55e','circle-stroke-color':'#fff','circle-stroke-width':3}}}});
  map.addSource('do',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'Point',coordinates:ROUTE[ROUTE.length-1]}}}}}});
  map.addLayer({{id:'dod',type:'circle',source:'do',paint:{{'circle-radius':14,'circle-color':'#ef4444','circle-stroke-color':'#fff','circle-stroke-width':3}}}});
  startAnim();
}});

const pb=document.getElementById('pbar'),sv=document.getElementById('spdv'),arrEl=document.getElementById('arr');
function lerp(a,b,t){{return a+(b-a)*t}}
function posAt(t){{const idx=t*(ROUTE.length-1),i=Math.floor(idx),f=idx-i,n=Math.min(i+1,ROUTE.length-1);return[lerp(ROUTE[i][0],ROUTE[n][0],f),lerp(ROUTE[i][1],ROUTE[n][1],f)]}}
function toScr(lon,lat){{const p=map.project([lon,lat]);return[p.x,p.y]}}

let HD=[false,false,false,false],CT2=0,LT=0,vsc=.55;
function startAnim(){{
  const t0=performance.now();let done=false;
  function fr(now){{
    const dt=Math.min((now-LT)/1000,.05);LT=now;
    const t=Math.min((now-t0)/DUR,1);
    pb.style.width=(t*100)+'%';
    sv.textContent=Math.round(15+t*45+Math.sin(now/700)*6);
    vsc=.42+t*.60;
    const[lon,lat]=posAt(t);const[px,py]=toScr(lon,lat);
    const t2=Math.min(t+.003,1);const[l2,a2]=posAt(t2);const[px2,py2]=toScr(l2,a2);
    const ang=Math.atan2(py2-py,px2-px);
    ctx.clearRect(0,0,fx.width,fx.height);
    const{{smokeX,smokeY}}=drawTrain(px,py,ang,vsc);
    if(Math.random()<.5)smoke(smokeX,smokeY);
    if(Math.random()<.12)spark(px,py);
    if(Math.random()<.07)ember(smokeX,smokeY);
    S=S.filter(s=>s.life>0);S.forEach(s=>{{s.x+=s.vx;s.y+=s.vy;s.r+=.6;s.life-=s.decay;let sg=ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r);sg.addColorStop(0,`rgba(${{s.gray}},${{s.gray}},${{s.gray+15}},${{s.life*.55}})`);sg.addColorStop(1,`rgba(${{s.gray}},${{s.gray}},${{s.gray}},0)`);ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fillStyle=sg;ctx.fill()}});
    SP=SP.filter(s=>s.life>0);SP.forEach(s=>{{s.x+=s.vx;s.y+=s.vy;s.vy+=.14;s.life-=s.decay;ctx.beginPath();ctx.arc(s.x,s.y,s.r*s.life,0,Math.PI*2);ctx.fillStyle=`rgba(232,184,75,${{s.life*.9}})`;ctx.fill()}});
    EM=EM.filter(e=>e.life>0);EM.forEach(e=>{{e.x+=e.vx;e.y+=e.vy;e.vy+=.07;e.vx*=.97;e.life-=e.decay;ctx.beginPath();ctx.arc(e.x,e.y,e.r*e.life,0,Math.PI*2);ctx.fillStyle=`hsla(${{e.hue}},100%,65%,${{e.life*.85}})`;ctx.fill()}});
    if(!HD[0]&&t>.04){{HD[0]=true;horn()}}
    if(!HD[1]&&t>.28){{HD[1]=true;horn()}}
    if(!HD[2]&&t>.62){{HD[2]=true;horn()}}
    if(!HD[3]&&t>.91){{HD[3]=true;horn()}}
    CT2+=dt;if(CT2>.22){{CT2=0;clack()}}
    map.easeTo({{center:[lon,lat],duration:150,easing:x=>x}});
    if(t<1){{requestAnimationFrame(fr)}}
    else if(!done){{done=true;ctx.clearRect(0,0,fx.width,fx.height);arrEl.style.display='flex';horn();setTimeout(horn,700)}}
  }}
  requestAnimationFrame(fr);
}}
</script></body></html>"""
    st.components.v1.html(map_html, height=700, scrolling=False)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("\U0001f504  NEW RIDE"):
            st.session_state.stage = "form"
            st.session_state.fare_data = None
            st.rerun()


# ═══════════════════════════════════════════════
# STAGE: FORM
# ═══════════════════════════════════════════════
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
            hours = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0,30)]
            default_time = f"{datetime.now().strftime('%H')}:{'00' if int(datetime.now().strftime('%M'))<30 else '30'}"
            default_idx = hours.index(default_time) if default_time in hours else 0
            pickup_time = st.selectbox("Time", hours, index=default_idx, label_visibility="collapsed")
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
                st.error("Please enter both addresses.")
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
                            "pred":pred, "pax":int(passenger_count),
                            "plat":plat, "plon":plon, "dlat":dlat, "dlon":dlon,
                            "route":route,
                            "pickup_address":pickup_address.strip(),
                            "dropoff_address":dropoff_address.strip(),
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

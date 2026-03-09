"""
brandhub Atlas · POS Asset Location Intelligence
A Streamlit demo app showing how Bluetooth beacons + VIP fleet GPS
track POS materials from production to placement.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="brandhub Atlas · POS Asset Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Brand colors ────────────────────────────────────────────────────────────────
NAVY   = "#1D1846"
BLUE   = "#30B4E6"
ORANGE = "#FF9119"
BG     = "#090C1C"
CARD   = "#141A30"
BORDER = "rgba(255,255,255,0.07)"
MUTED  = "#8898B5"
GREEN  = "#28C840"

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Dark background */
  [data-testid="stAppViewContainer"],
  [data-testid="stHeader"],
  [data-testid="stToolbar"] {{
    background: {BG} !important;
  }}
  [data-testid="stSidebar"] {{
    background: #0E1225 !important;
  }}
  /* Remove default padding */
  .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
  }}
  /* Hide streamlit branding */
  #MainMenu, footer, header {{ visibility: hidden; }}
  /* Button styles */
  div.stButton > button {{
    background: linear-gradient(135deg, {BLUE}, {NAVY});
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
    font-weight: 700;
    font-size: 14px;
    width: 100%;
    transition: all 0.2s;
    letter-spacing: 0.3px;
  }}
  div.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(48,180,230,0.35);
    background: linear-gradient(135deg, #3dc9ff, {NAVY});
  }}
  div.stButton > button:disabled {{
    background: #1e2540;
    color: {MUTED};
    transform: none;
    box-shadow: none;
    cursor: not-allowed;
  }}
  /* Slider */
  .stSlider [data-baseweb="slider"] {{
    padding: 0;
  }}
  div[data-testid="stSlider"] label {{
    color: {MUTED} !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── Journey data ─────────────────────────────────────────────────────────────────
# A Heaven Hill floor display tracked from Bardstown, KY → Louisville retail
ASSET_ID   = "HH-DISPLAY-2024-0077"
ASSET_DESC = "Heaven Hill Elijah Craig – 48″ Illuminated Floor Display"

JOURNEY = [
    dict(
        stage=0, icon="🏭",
        label="Beacon Embedded at Production",
        detail="48″ floor display fabricated. Low-energy Bluetooth beacon embedded and registered in brandhub Atlas. Asset ID issued.",
        lat=37.8115, lng=-85.4702,
        place="Heaven Hill Distillery – Bardstown, KY",
        src=None,
        ts="Mon Mar 9  9:14 AM",
        conf=100,
    ),
    dict(
        stage=1, icon="🚛",
        label="Loaded onto VIP Truck #TX-4482",
        detail="VIP fleet GPS geofence triggered at loading dock. Asset pickup confirmed via truck telemetry. No phone opt-in required.",
        lat=37.9750, lng=-85.5900,
        place="VIP Distribution Hub – Shepherdsville, KY",
        src="vip",
        ts="Mon Mar 9 10:52 AM",
        conf=100,
    ),
    dict(
        stage=2, icon="📱",
        label="Phone Ping – En Route on I-65",
        detail="Driver's Bluetooth-enabled device detected the beacon while en route north. Location triangulated from phone GPS.",
        lat=38.1400, lng=-85.6700,
        place="I-65 North near Brooks, KY",
        src="phone",
        ts="Mon Mar 9 11:33 AM",
        conf=72,
    ),
    dict(
        stage=3, icon="🚛",
        label="VIP Truck GPS – First Drop Confirmed",
        detail="Truck #TX-4482 entered Party Mart geofence. Asset off-loaded and confirmed placed per delivery manifest.",
        lat=38.2527, lng=-85.7585,
        place="Party Mart Liquors – Louisville, KY",
        src="vip",
        ts="Mon Mar 9  1:08 PM",
        conf=100,
    ),
    dict(
        stage=4, icon="📱",
        label="Shopper Phone Ping – In-Store",
        detail="Shopper's iPhone detected beacon near checkout display. Asset confirmed active and visible on retail floor.",
        lat=38.2529, lng=-85.7583,
        place="Party Mart Liquors – Louisville, KY",
        src="phone",
        ts="Mon Mar 9  3:41 PM",
        conf=68,
    ),
    dict(
        stage=5, icon="📱",
        label="Second Shopper Ping – Next Day",
        detail="Independent Android scan confirms display still in place. Two-day dwell time logged. Compliance milestone hit.",
        lat=38.2528, lng=-85.7586,
        place="Party Mart Liquors – Louisville, KY",
        src="phone",
        ts="Tue Mar 10 11:15 AM",
        conf=71,
    ),
    dict(
        stage=6, icon="🚛",
        label="VIP Truck #TX-4487 – Pickup & Reroute",
        detail="Asset relocated by VIP truck. New destination: on-premise bar. Delivery logged automatically via fleet telemetry.",
        lat=38.2423, lng=-85.7198,
        place="The Silver Dollar Bar – Louisville, KY",
        src="vip",
        ts="Wed Mar 11  9:30 AM",
        conf=100,
    ),
    dict(
        stage=7, icon="📱",
        label="Bar Patron Ping – Evening",
        detail="Guest's phone detected beacon near the bar's back bar display. Asset confirmed placed and visible to consumers.",
        lat=38.2424, lng=-85.7196,
        place="The Silver Dollar Bar – Louisville, KY",
        src="phone",
        ts="Wed Mar 11  8:47 PM",
        conf=65,
    ),
]

MAX_STAGE = len(JOURNEY) - 1

SRC_COLOR = {None: GREEN, "vip": BLUE, "phone": ORANGE}
SRC_LABEL = {None: "🏭 Production Origin", "vip": "🚛 VIP Fleet GPS", "phone": "📱 Bluetooth Phone Ping"}

# ── Session state ────────────────────────────────────────────────────────────────
if "stage"   not in st.session_state: st.session_state.stage   = 0
if "playing" not in st.session_state: st.session_state.playing = False

# ── Map builder ──────────────────────────────────────────────────────────────────
def build_map(stage_idx: int) -> go.Figure:
    events = JOURNEY[: stage_idx + 1]
    fig    = go.Figure()

    lats = [e["lat"] for e in events]
    lngs = [e["lng"] for e in events]

    # ── Route trail ──────────────────────────────────────────────────────────────
    if len(events) > 1:
        fig.add_trace(go.Scattermapbox(
            lat=lats, lon=lngs,
            mode="lines",
            line=dict(width=2.5, color=f"rgba(48,180,230,0.30)"),
            hoverinfo="skip",
            showlegend=False,
            name="route",
        ))

    # ── Past events (faded markers) ───────────────────────────────────────────────
    for i, evt in enumerate(events[:-1]):
        c = SRC_COLOR[evt["src"]]
        # outer glow
        fig.add_trace(go.Scattermapbox(
            lat=[evt["lat"]], lon=[evt["lng"]],
            mode="markers",
            marker=dict(size=20, color=c, opacity=0.07),
            hoverinfo="skip",
            showlegend=False,
            name="",
        ))
        # solid dot
        fig.add_trace(go.Scattermapbox(
            lat=[evt["lat"]], lon=[evt["lng"]],
            mode="markers",
            marker=dict(size=9, color=c, opacity=0.45),
            hovertemplate=f"<b>{evt['icon']} {evt['label']}</b><br>"
                          f"📍 {evt['place']}<br>"
                          f"🕐 {evt['ts']}<br>"
                          f"Source: {SRC_LABEL[evt['src']]}<extra></extra>",
            showlegend=False,
            name="",
        ))

    # ── Current position – pulse rings ────────────────────────────────────────────
    cur   = events[-1]
    color = SRC_COLOR[cur["src"]]

    for size, opacity in [(64, 0.04), (46, 0.08), (32, 0.14)]:
        fig.add_trace(go.Scattermapbox(
            lat=[cur["lat"]], lon=[cur["lng"]],
            mode="markers",
            marker=dict(size=size, color=color, opacity=opacity),
            hoverinfo="skip",
            showlegend=False,
            name="",
        ))

    # bright dot + label
    fig.add_trace(go.Scattermapbox(
        lat=[cur["lat"]], lon=[cur["lng"]],
        mode="markers+text",
        marker=dict(size=18, color=color, opacity=0.95),
        text=[f" {cur['place']}"],
        textposition="middle right",
        textfont=dict(color="white", size=12, family="sans-serif"),
        hovertemplate=f"<b>{cur['icon']} {cur['label']}</b><br>"
                      f"📍 {cur['place']}<br>"
                      f"🕐 {cur['ts']}<br>"
                      f"Source: {SRC_LABEL[cur['src']]}<br>"
                      f"Confidence: {cur['conf']}%<extra></extra>",
        showlegend=False,
        name="Current",
    ))

    # ── Origin marker ─────────────────────────────────────────────────────────────
    origin = JOURNEY[0]
    fig.add_trace(go.Scattermapbox(
        lat=[origin["lat"]], lon=[origin["lng"]],
        mode="markers",
        marker=dict(size=11, color=GREEN, opacity=0.85, symbol="circle"),
        hovertemplate=f"<b>🏭 Origin: {origin['place']}</b><extra></extra>",
        showlegend=False,
        name="Origin",
    ))

    # ── Map layout ────────────────────────────────────────────────────────────────
    lat_c = np.mean(lats)
    lng_c = np.mean(lngs)
    spread = max(abs(max(lats) - min(lats)), abs(max(lngs) - min(lngs)))
    zoom   = 9.5 if spread < 0.05 else (8.5 if spread < 0.5 else 7.5)

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=lat_c, lon=lng_c),
            zoom=zoom,
        ),
        margin=dict(r=0, t=0, l=0, b=0),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        showlegend=False,
        height=500,
    )
    return fig

# ════════════════════════════════════════════════════════════════════════════════
# ── UI ───────────────────────────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,{NAVY} 0%,{BG} 100%);
            padding:32px 48px 28px;border-bottom:2px solid rgba(48,180,230,0.18);
            margin-bottom:0">
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px">
    <span style="font-size:36px">📡</span>
    <div>
      <div style="font-size:30px;font-weight:900;color:white;letter-spacing:-0.8px;line-height:1">
        brandhub <span style="color:{BLUE}">Atlas</span>
      </div>
      <div style="font-size:11px;color:{MUTED};font-weight:700;letter-spacing:2.5px;
                  text-transform:uppercase;margin-top:3px">
        POS Asset Location Intelligence
      </div>
    </div>
  </div>
  <div style="color:{MUTED};font-size:14px;max-width:680px;line-height:1.65">
    Real-time visibility into where your POS materials are — from production to consumer placement
    — powered by <b style="color:white">Bluetooth beacons</b> embedded at the point of manufacture
    and the <b style="color:{BLUE}">VIP Distributors fleet network</b> already servicing thousands
    of accounts nationwide.
  </div>
</div>
""", unsafe_allow_html=True)

# ── How It Works ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:24px 48px 4px">
  <div style="font-size:11px;color:{MUTED};font-weight:700;letter-spacing:2px;
              text-transform:uppercase;margin-bottom:14px">How It Works</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="background:{CARD};border:1px solid rgba(255,145,25,0.22);
                border-radius:16px;padding:22px 26px">
      <div style="font-size:18px;font-weight:800;color:{ORANGE};margin-bottom:10px">
        📱 Bluetooth Beacon Pings
      </div>
      <div style="color:{MUTED};font-size:13px;line-height:1.75">
        A low-energy Bluetooth beacon is embedded in each POS asset <em>at the point of production</em>.
        Any nearby smartphone — a shopper, staff member, or delivery driver — can detect it and report its location.
        <br><br>
        <b style="color:rgba(255,255,255,0.5)">⚠ Challenge:</b>
        iOS and Android now prompt users to opt in to Bluetooth tracking, making
        coverage inconsistent and unpredictable.
      </div>
    </div>
    <div style="background:{CARD};border:1px solid rgba(48,180,230,0.28);
                border-radius:16px;padding:22px 26px">
      <div style="font-size:18px;font-weight:800;color:{BLUE};margin-bottom:10px">
        🚛 VIP Fleet GPS Network — The Differentiator
      </div>
      <div style="color:{MUTED};font-size:13px;line-height:1.75">
        brandhub partners with <b style="color:white">VIP Distributors</b>, whose trucks
        <em>already</em> service thousands of liquor stores, bars, and restaurants across the country
        and run integrated fleet-management software.
        <br><br>
        <b style="color:{BLUE}">✓ Result:</b> Every VIP pickup and delivery automatically
        logs your asset's location — no consumer opt-in needed, no gaps in coverage.
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Asset card + stats ────────────────────────────────────────────────────────────
current      = JOURNEY[st.session_state.stage]
events_shown = JOURNEY[: st.session_state.stage + 1]
vip_count    = sum(1 for e in events_shown if e["src"] == "vip")
phone_count  = sum(1 for e in events_shown if e["src"] == "phone")
total_events = len(events_shown)
conf_color   = GREEN if current["conf"] >= 95 else ORANGE

st.markdown(f"""
<div style="margin:20px 48px 0;background:{CARD};border:1px solid {BORDER};
            border-radius:16px;padding:20px 28px;
            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">
  <div>
    <div style="font-size:10px;color:{MUTED};font-weight:700;letter-spacing:1.8px;
                text-transform:uppercase;margin-bottom:5px">Tracking Asset</div>
    <div style="font-size:20px;font-weight:900;color:white;font-family:monospace;
                letter-spacing:0.5px">{ASSET_ID}</div>
    <div style="font-size:12px;color:{MUTED};margin-top:2px">{ASSET_DESC}</div>
  </div>
  <div style="display:flex;gap:28px;align-items:center;flex-wrap:wrap">
    <div style="text-align:center">
      <div style="font-size:28px;font-weight:900;color:{BLUE};line-height:1">{vip_count}</div>
      <div style="font-size:10px;color:{MUTED};font-weight:600;letter-spacing:1px;
                  text-transform:uppercase;margin-top:2px">VIP Pings</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:28px;font-weight:900;color:{ORANGE};line-height:1">{phone_count}</div>
      <div style="font-size:10px;color:{MUTED};font-weight:600;letter-spacing:1px;
                  text-transform:uppercase;margin-top:2px">Phone Pings</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:28px;font-weight:900;color:white;line-height:1">{total_events}</div>
      <div style="font-size:10px;color:{MUTED};font-weight:600;letter-spacing:1px;
                  text-transform:uppercase;margin-top:2px">Total Events</div>
    </div>
    <div style="border-left:1px solid {BORDER};padding-left:24px">
      <div style="font-size:10px;color:{MUTED};font-weight:600;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:3px">Last Confirmed</div>
      <div style="font-size:13px;font-weight:700;color:white">{current['ts']}</div>
      <div style="font-size:12px;color:{SRC_COLOR[current['src']]};font-weight:600;
                  margin-top:2px">{SRC_LABEL[current['src']]}</div>
    </div>
    <div style="border-left:1px solid {BORDER};padding-left:24px">
      <div style="font-size:10px;color:{MUTED};font-weight:600;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:3px">Confidence</div>
      <div style="font-size:28px;font-weight:900;color:{conf_color};line-height:1">
        {current['conf']}%
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Map ──────────────────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div style="margin:16px 48px 0">', unsafe_allow_html=True)
    map_placeholder = st.empty()
    map_placeholder.plotly_chart(
        build_map(st.session_state.stage),
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": True},
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ── Current event detail ──────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin:8px 48px 0;background:{CARD};
            border-left:4px solid {SRC_COLOR[current['src']]};
            border-radius:0 14px 14px 0;padding:18px 24px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              flex-wrap:wrap;gap:12px">
    <div style="flex:1">
      <div style="font-size:10px;color:{MUTED};font-weight:700;letter-spacing:1.5px;
                  text-transform:uppercase;margin-bottom:6px">
        Stage {st.session_state.stage + 1} of {MAX_STAGE + 1}
      </div>
      <div style="font-size:20px;font-weight:900;color:white;margin-bottom:6px;
                  letter-spacing:-0.3px">
        {current['icon']} {current['label']}
      </div>
      <div style="font-size:13px;color:{MUTED};line-height:1.65;max-width:580px">
        {current['detail']}
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div style="font-size:12px;color:{MUTED};margin-bottom:2px">📍 Location</div>
      <div style="font-size:13px;font-weight:700;color:white">{current['place']}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Playback controls ─────────────────────────────────────────────────────────────
st.markdown('<div style="margin:14px 48px 0">', unsafe_allow_html=True)
ctrl_cols = st.columns([1, 1, 1, 3])

with ctrl_cols[0]:
    if st.button("⟵ Prev", disabled=(st.session_state.stage == 0)):
        st.session_state.stage   -= 1
        st.session_state.playing  = False
        st.rerun()

with ctrl_cols[1]:
    play_label = "⏸ Pause" if st.session_state.playing else "▶ Play Demo"
    if st.button(play_label):
        st.session_state.playing = not st.session_state.playing
        st.rerun()

with ctrl_cols[2]:
    if st.button("Next ⟶", disabled=(st.session_state.stage == MAX_STAGE)):
        st.session_state.stage   += 1
        st.session_state.playing  = False
        st.rerun()

with ctrl_cols[3]:
    st.markdown(f"""
    <div style="display:flex;gap:20px;align-items:center;padding:6px 0">
      <div style="display:flex;gap:8px;align-items:center">
        <div style="width:10px;height:10px;background:{BLUE};border-radius:50%"></div>
        <span style="color:{MUTED};font-size:12px;font-weight:600">VIP Fleet GPS</span>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <div style="width:10px;height:10px;background:{ORANGE};border-radius:50%"></div>
        <span style="color:{MUTED};font-size:12px;font-weight:600">Phone Bluetooth</span>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <div style="width:10px;height:10px;background:{GREEN};border-radius:50%"></div>
        <span style="color:{MUTED};font-size:12px;font-weight:600">Production Origin</span>
      </div>
      <span style="color:{MUTED};font-size:11px;margin-left:8px">
        Scroll to zoom · Click markers for detail
      </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Auto-play logic ───────────────────────────────────────────────────────────────
if st.session_state.playing:
    if st.session_state.stage < MAX_STAGE:
        time.sleep(2.8)
        st.session_state.stage += 1
        st.rerun()
    else:
        st.session_state.playing = False
        st.rerun()

# ── Event log ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin:28px 48px 0 48px">
  <div style="font-size:15px;font-weight:800;color:white;margin-bottom:12px;
              letter-spacing:-0.3px">📋 Asset Event Log</div>
""", unsafe_allow_html=True)

for evt in reversed(JOURNEY[: st.session_state.stage + 1]):
    is_current = (evt["stage"] == st.session_state.stage)
    bar_color  = SRC_COLOR[evt["src"]]
    text_color = "white" if is_current else MUTED
    bg_extra   = f"background:rgba(48,180,230,0.06);" if is_current else ""
    latest_badge = (
        f'<span style="font-size:10px;font-weight:700;color:{BLUE};'
        f'background:rgba(48,180,230,0.15);padding:2px 8px;border-radius:20px;'
        f'margin-left:8px;vertical-align:middle">LATEST</span>'
        if is_current else ""
    )
    st.markdown(f"""
    <div style="{bg_extra}border-left:3px solid {bar_color};border-radius:0 12px 12px 0;
                padding:14px 20px;margin-bottom:8px;transition:all 0.2s">
      <div style="display:flex;justify-content:space-between;align-items:center;
                  flex-wrap:wrap;gap:8px">
        <div>
          <span style="font-size:14px;font-weight:700;color:{text_color}">
            {evt['icon']} {evt['label']}
          </span>
          {latest_badge}
          <div style="font-size:12px;color:{MUTED};margin-top:3px">
            📍 {evt['place']}
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:11px;font-weight:700;color:{bar_color}">
            {SRC_LABEL[evt['src']]}
          </div>
          <div style="font-size:11px;color:{MUTED};margin-top:2px">{evt['ts']}</div>
          <div style="font-size:11px;color:{'#28C840' if evt['conf']>=95 else ORANGE};
                      margin-top:1px;font-weight:600">
            {evt['conf']}% confidence
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Why VIP callout ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin:28px 48px 8px;background:linear-gradient(135deg,{NAVY}CC,{CARD});
            border:1px solid rgba(48,180,230,0.25);border-radius:18px;padding:28px 36px">
  <div style="font-size:20px;font-weight:900;color:white;margin-bottom:10px;
              letter-spacing:-0.4px">
    🚛 Why VIP Makes the Difference
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:16px">
    <div>
      <div style="font-size:26px;font-weight:900;color:{BLUE};line-height:1">10,000+</div>
      <div style="font-size:12px;color:{MUTED};margin-top:3px;line-height:1.5">
        Liquor stores, bars & restaurants already on VIP's route network
      </div>
    </div>
    <div>
      <div style="font-size:26px;font-weight:900;color:{BLUE};line-height:1">100%</div>
      <div style="font-size:12px;color:{MUTED};margin-top:3px;line-height:1.5">
        Opt-in rate — VIP trucks always carry GPS, no consumer permissions needed
      </div>
    </div>
    <div>
      <div style="font-size:26px;font-weight:900;color:{BLUE};line-height:1">Real-time</div>
      <div style="font-size:12px;color:{MUTED};margin-top:3px;line-height:1.5">
        Fleet telemetry automatically syncs to brandhub Atlas on every pickup &amp; drop
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:28px 0 20px;
            color:{MUTED};font-size:12px;
            border-top:1px solid rgba(255,255,255,0.05);
            margin:28px 0 0">
  brandhub Atlas &nbsp;·&nbsp; POS Asset Location Intelligence
  &nbsp;·&nbsp; Powered by Bluetooth Beacons + VIP Fleet Network
</div>
""", unsafe_allow_html=True)

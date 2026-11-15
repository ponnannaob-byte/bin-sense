"""
BinSense - Smart Waste Monitoring and Collection Route Planner
Pure Python: Streamlit (UI) + Plotly (charts) + Pandas (data).
Run:  streamlit run app.py
"""
import json
import math
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------
# CONFIG  (edit these)
# --------------------------------------------------------------------------
DATA_FILE = Path(__file__).parent / "binsense_data.json"
BASE_LAT, BASE_LNG = 12.9716, 77.5946   # real-world position of grid point (0, 0)
KM_PER_UNIT = 0.5                        # 1 grid unit = 0.5 km
TRUCK_KM_PER_LITRE = 3.0                 # truck mileage
DIESEL_PRICE = 95.0                      # price per litre (change to your currency)
TIME_FMT = "%Y-%m-%d %H:%M:%S"
INTERVALS = {"Every 2 minutes": 120, "Every 30 seconds (demo)": 30, "Every 10 seconds (demo)": 10}

# Palette
INK, EMERALD, LIME = "#0E1F2F", "#00B37E", "#C6F432"
AMBER, ORANGE, CORAL = "#FFB020", "#FF7A1A", "#FF4B3E"
STATUS_COLORS = {"Normal": EMERALD, "Filling": AMBER, "Due": ORANGE, "Overflow": CORAL}

st.set_page_config(page_title="BinSense", page_icon="♻️", layout="wide")

# --------------------------------------------------------------------------
# STYLING
# --------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; color: {INK}; }}
h1, h2, h3, h4 {{ font-family: 'Sora', sans-serif !important; color: {INK}; letter-spacing: -0.02em; }}
#MainMenu, footer {{ visibility: hidden; height: 0; }}
.block-container {{ padding-top: 1.4rem; max-width: 1250px; }}

[data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {{ background: #FFFFFF !important; }}
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {{ background: #FFFFFF !important; border-right: 1.5px solid #E3ECE8; }}
header[data-testid="stHeader"], header[data-testid="stHeader"] [data-testid="stToolbar"] {{
    background: #FFFFFF !important; color: {INK} !important; box-shadow: none !important;
}}
header[data-testid="stHeader"] button, header[data-testid="stHeader"] a {{
    color: {INK} !important;
}}
.brand {{ font-family:'Sora'; font-weight:800; font-size:1.7rem; letter-spacing:-0.03em; color:{INK} !important; }}
.brand span {{ background:{LIME}; color:{INK} !important; padding:0 .35rem; border-radius:.4rem; }}
.brand-sub {{ font-size:.8rem; color:#53636F !important; opacity:1; margin-bottom:1rem; }}

.hero {{ position:relative; overflow:hidden; background:#fff;
        border-radius:22px; padding:1.8rem 2rem; margin-bottom:1.3rem; }}
.hero-frame {{ position:absolute; inset:0; border:1.5px solid {INK}; border-radius:inherit;
        pointer-events:none; z-index:3; }}
.hero:before {{ content:""; position:absolute; right:-70px; top:-70px; width:260px; height:260px;
        background:{LIME}; border-radius:50%; }}
.hero:after {{ content:""; position:absolute; right:90px; bottom:-90px; width:170px; height:170px;
        background:{EMERALD}; border-radius:50%; opacity:.9; }}
.hero h1 {{ margin:0; font-size:2.2rem; font-weight:800; position:relative; z-index:2; }}
.hero p {{ margin:.35rem 0 0; font-size:1.02rem; max-width:560px; opacity:.8; position:relative; z-index:2; }}

.kpi {{ background:#fff; border:1.5px solid #E3ECE8; border-radius:18px; padding:1rem 1.2rem;
        border-left:7px solid var(--c); }}
.kpi .v {{ font-family:'Sora'; font-size:2rem; font-weight:800; line-height:1.1; }}
.kpi .l {{ font-size:.85rem; font-weight:700; opacity:.7; }}
.kpi .s {{ font-size:.78rem; opacity:.55; }}

.alert {{ border-radius:16px; padding:.9rem 1.1rem; margin-bottom:.7rem; border:1.5px solid var(--c);
        background:color-mix(in srgb, var(--c) 8%, white); }}
.alert b {{ font-family:'Sora'; }}
.history-empty {{ border:1.5px solid #D5E3DC; border-left:5px solid {EMERALD}; border-radius:14px;
        background:#F6FBF8; color:{INK}; padding:1rem 1.2rem; }}
.banner {{ background:{CORAL}; color:#fff; border-radius:16px; padding:.85rem 1.2rem; font-weight:700;
        margin-bottom:1rem; }}
.pill {{ display:inline-block; padding:.15rem .7rem; border-radius:99px; font-size:.78rem; font-weight:700;
        background:{LIME}; color:{INK}; }}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    background:{INK}; color:#fff; border:none; border-radius:12px; font-weight:700; padding:.55rem 1.3rem; }}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ background:{EMERALD}; color:#fff; }}
a[data-testid="stBaseLinkButton-secondary"], a[kind="secondary"] {{ border-radius:12px !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap:.4rem; }}
.stTabs [data-baseweb="tab"] {{ background:#FFFFFF; border:1.5px solid #E3ECE8; border-radius:12px; padding:.45rem 1rem; font-weight:700; }}
.stTabs [aria-selected="true"] {{ background:{LIME} !important; color:{INK} !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
div[data-testid="stPlotlyChart"] {{ border:1.5px solid #E3ECE8; border-radius:18px; padding:.4rem; background:#fff; }}
</style>
""",
    unsafe_allow_html=True,
)


# Force a light look even if the browser/OS is in dark mode or config.toml was not picked up
st.markdown(
    f"""
<style>
:root {{ color-scheme: light; }}
.stApp {{ background:#FFFFFF !important; color:{INK} !important; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label, .stApp li,
.stApp [data-testid="stMarkdownContainer"] :is(p, li, strong, b, span, h1, h2, h3, h4),
.stApp [data-testid="stWidgetLabel"] *, .stApp [data-testid="stCaptionContainer"] *,
.stApp [data-testid="stRadio"] *, .stApp [data-testid="stToggle"] *, .stApp [data-testid="stCheckbox"] *,
.stApp [data-testid="stSlider"] *, .stApp .stTabs [data-baseweb="tab"] p {{ color:{INK} !important; }}
.stApp .kpi, .stApp .kpi *, .stApp .alert, .stApp .alert *, .stApp .hero, .stApp .hero * {{ color:{INK} !important; }}
.stApp .banner, .stApp .banner * {{ color:#FFFFFF !important; }}
.stApp .stButton button *, .stApp .stFormSubmitButton button *, .stApp .stDownloadButton button *,
.stApp a[data-testid^="stBaseLinkButton"] * {{ color:#FFFFFF !important; }}

.stApp [data-baseweb="select"] > div {{ background:#FFFFFF !important; border:1.5px solid #D5E3DC !important; border-radius:12px !important; }}
.stApp [data-baseweb="select"] * {{ color:{INK} !important; }}
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {{ background:#FFFFFF !important; color:{INK} !important; }}
[data-baseweb="popover"] li:hover {{ background:#F1FBF6 !important; }}
.stApp input, .stApp textarea {{ background:#FFFFFF !important; color:{INK} !important; -webkit-text-fill-color:{INK} !important; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="textarea"] {{ background:#FFFFFF !important; border-color:#D5E3DC !important; }}
.stApp [data-testid="stNumberInput"] button {{ background:#FFFFFF !important; }}
.stApp [data-testid="stNumberInput"] button * {{ color:{INK} !important; }}

.stApp label[data-baseweb="radio"] > div:first-child {{ background:#FFFFFF !important; border:2px solid #9FB3AB !important; }}
.stApp label[data-baseweb="radio"]:has(input:checked) > div:first-child {{ background:{EMERALD} !important; border-color:{EMERALD} !important; }}
.stApp label[data-baseweb="checkbox"] > div:first-child {{ background:#C9D3CF !important; }}
.stApp label[data-baseweb="checkbox"]:has(input:checked) > div:first-child {{ background:{EMERALD} !important; }}
.stApp [data-baseweb="slider"] div[role="slider"] {{ background:{EMERALD} !important; }}

.stApp [data-testid="stAlert"] {{ background:#F6FBF8 !important; border:1.5px solid #D5E3DC; border-radius:14px; }}
.stApp [data-testid="stAlert"] * {{ color:{INK} !important; }}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# DATA LAYER  (JSON file acts as the "array" storage)
# --------------------------------------------------------------------------
def now_str():
    return datetime.now().strftime(TIME_FMT)


def load_db():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return {"depot": {"x": 0.0, "y": 0.0}, "bins": [], "history": []}


def save_db():
    DATA_FILE.write_text(json.dumps(st.session_state.db, indent=2))


def demo_data():
    random.seed(7)
    spec = [("B1", 2, 3, 90), ("B2", 5, 7, 40), ("B3", 1, 8, 85), ("B4", 9, 2, 30),
            ("B5", 4, 4, 100), ("B6", 7, 6, 78), ("B7", 3, 9, 55), ("B8", 8, 8, 92),
            ("B9", 6, 1, 20), ("B10", 10, 5, 68)]
    now = datetime.now()
    bins = []
    for bid, x, y, f in spec:
        rate = round(random.uniform(1, 4), 1)          # % added per live update
        readings = [[(now - timedelta(minutes=2 * (5 - i))).strftime(TIME_FMT),
                     round(max(0, f - rate * (5 - i)), 1)] for i in range(6)]
        bins.append({"id": bid, "x": x, "y": y, "fill": f, "rate": rate, "readings": readings})
    return {"depot": {"x": 0.0, "y": 0.0}, "bins": bins, "history": []}


def ensure_live(d, keep=None):
    d["live"] = keep or d.get("live") or {"enabled": True, "interval": 120}
    d["live"]["last_tick"] = time.time()
    return d


def bump(n=1):
    """Add n live updates: every bin below 100% fills by its own rate (with a little randomness)."""
    d = st.session_state.db
    ts = now_str()
    for b in d["bins"]:
        if b["fill"] < 100:
            b["fill"] = round(min(100, b["fill"] + b.get("rate", 2.0) * n * random.uniform(0.7, 1.3)), 1)
            b.setdefault("readings", []).append([ts, b["fill"]])
            b["readings"] = b["readings"][-200:]
    save_db()


def apply_ticks():
    """Run any live updates that are due. Returns how many ran."""
    d = st.session_state.db
    lv = d["live"]
    if not lv["enabled"]:
        return 0
    now = time.time()
    n = int((now - lv["last_tick"]) // lv["interval"])
    if n <= 0:
        return 0
    n = min(n, 30)
    lv["last_tick"] = lv["last_tick"] + n * lv["interval"] if n < 30 else now
    bump(n)
    return n


def _live_toggle():
    lv = st.session_state.db["live"]
    lv["enabled"] = st.session_state.live_toggle
    lv["last_tick"] = time.time()


@st.fragment(run_every=5)
def live_status():
    d = st.session_state.db
    lv = d["live"]
    if not lv["enabled"]:
        st.caption("Auto-fill is paused.")
        return
    if apply_ticks():
        st.rerun(scope="app")
    left = max(0, int(lv["interval"] - (time.time() - lv["last_tick"])))
    st.markdown(f'<span class="pill">● LIVE</span> next update in <b>{left // 60}:{left % 60:02d}</b>',
                unsafe_allow_html=True)


if "db" not in st.session_state:
    st.session_state.db = ensure_live(load_db())
db = st.session_state.db
apply_ticks()


# --------------------------------------------------------------------------
# CORE LOGIC
# --------------------------------------------------------------------------
THRESHOLD = 75  # overwritten from the sidebar slider


def status_of(fill):
    if fill >= 100:
        return "Overflow"
    if fill >= THRESHOLD:
        return "Due"
    if fill >= 50:
        return "Filling"
    return "Normal"


def dist(a, b):
    """Euclidean distance between two (x, y) grid points, in km."""
    return math.hypot(a[0] - b[0], a[1] - b[1]) * KM_PER_UNIT


def bins_df():
    rows = []
    d = (db["depot"]["x"], db["depot"]["y"])
    for b in db["bins"]:
        rows.append({"Bin ID": b["id"], "X": b["x"], "Y": b["y"], "Fill %": b["fill"],
                     "Status": status_of(b["fill"]), "Distance from depot (km)": round(dist(d, (b["x"], b["y"])), 2),
                     "Rate % per update": b.get("rate", 2.0)})
    return pd.DataFrame(rows, columns=["Bin ID", "X", "Y", "Fill %", "Status", "Distance from depot (km)", "Rate % per update"])


def nearest_neighbour(depot, bins, return_home=True):
    """Nearest Neighbour Algorithm. Returns (ordered bins, legs, total km)."""
    current, remaining, order, legs, total = depot, list(bins), [], [], 0.0
    while remaining:
        nxt = min(remaining, key=lambda b: dist(current, (b["x"], b["y"])))
        d = dist(current, (nxt["x"], nxt["y"]))
        order.append(nxt)
        legs.append(d)
        total += d
        current = (nxt["x"], nxt["y"])
        remaining.remove(nxt)
    if return_home and order:
        total += dist(current, depot)
    return order, legs, total


def due_bins():
    return [b for b in db["bins"] if b["fill"] >= THRESHOLD]


def fuel_savings(return_home=True):
    depot = (db["depot"]["x"], db["depot"]["y"])
    _, _, all_km = nearest_neighbour(depot, db["bins"], return_home)
    _, _, due_km = nearest_neighbour(depot, due_bins(), return_home)
    saved = all_km - due_km
    litres = saved / TRUCK_KM_PER_LITRE
    return {"all_km": all_km, "due_km": due_km, "saved_km": saved,
            "pct": (saved / all_km * 100) if all_km else 0,
            "litres": litres, "money": litres * DIESEL_PRICE}


def predict(b):
    """Fill rate (%/hour) from the latest rising readings, and hours until 100%."""
    r = b.get("readings", [])
    if len(r) < 2:
        return None, None
    seg = [r[-1]]
    for prev in reversed(r[:-1]):
        if prev[1] <= seg[0][1]:
            seg.insert(0, prev)
        else:
            break
    if len(seg) < 2:
        return None, None
    hrs = (datetime.strptime(seg[-1][0], TIME_FMT) - datetime.strptime(seg[0][0], TIME_FMT)).total_seconds() / 3600
    if hrs <= 0 or seg[-1][1] <= seg[0][1]:
        return None, None
    rate = (seg[-1][1] - seg[0][1]) / hrs
    left = max(0.0, (100 - b["fill"]) / rate)
    return round(rate, 2), round(left, 1)


def to_latlng(x, y):
    lat = BASE_LAT + (y * KM_PER_UNIT) / 111.0
    lng = BASE_LNG + (x * KM_PER_UNIT) / (111.0 * math.cos(math.radians(BASE_LAT)))
    return lat, lng


def google_maps_links(depot, order, return_home=True):
    """Google Maps directions links/embeds that need NO API key."""
    pts = [depot] + [(b["x"], b["y"]) for b in order] + ([depot] if return_home else [])
    ll = [to_latlng(*p) for p in pts]
    coords = [f"{a:.6f},{b:.6f}" for a, b in ll]
    open_url = "https://www.google.com/maps/dir/" + "/".join(coords) + "/?travelmode=driving"
    embed_url = ("https://maps.google.com/maps?saddr=" + coords[0] + "&daddr=" + "+to:".join(coords[1:])
                 + "&output=embed")
    return open_url, embed_url


# --------------------------------------------------------------------------
# UI HELPERS
# --------------------------------------------------------------------------
def style(fig, h=380, legend=True):
    fig.update_layout(
        template="plotly_white",
        height=h,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="DM Sans", color=INK),
        showlegend=legend,
        title_font=dict(family="Sora", size=16, color=INK),
        legend=dict(title_font=dict(color=INK), font=dict(color=INK, size=12)),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title_font=dict(color=INK), tickfont=dict(color=INK), gridcolor="#D9E0E5",
                   zerolinecolor="#7A8A94", linecolor="#7A8A94"),
        yaxis=dict(title_font=dict(color=INK), tickfont=dict(color=INK), gridcolor="#D9E0E5",
                   zerolinecolor="#7A8A94", linecolor="#7A8A94"),
    )
    return fig


def kpi(col, label, value, sub, color):
    col.markdown(f'<div class="kpi" style="--c:{color}"><div class="l">{label}</div>'
                 f'<div class="v">{value}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)


def hero(title, text):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{text}</p>'
                '<span class="hero-frame" aria-hidden="true"></span></div>', unsafe_allow_html=True)


def empty_state():
    st.info("No bins yet. Add a bin on the **Manage Bins** page, or click **Load demo data** in the sidebar.")


# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="brand">Bin<span>Sense</span></div>'
                '<div class="brand-sub">Smart waste monitoring & route planner</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", ["📊  Dashboard", "🗑️  Manage Bins", "🚨  Alerts", "🚚  Route Planner",
                                 "📈  Analytics", "🕘  Collection History"], label_visibility="collapsed")
    st.divider()
    THRESHOLD = st.slider("Collection threshold (%)", 50, 95, 75, 5)
    st.markdown("**Live filling**")
    _lv = st.session_state.db["live"]
    st.toggle("Auto-fill bins", value=_lv["enabled"], key="live_toggle", on_change=_live_toggle)
    _names = list(INTERVALS)
    _pick = st.selectbox("Update speed", _names, index=[INTERVALS[n] for n in _names].index(_lv["interval"])
                         if _lv["interval"] in INTERVALS.values() else 0)
    _lv["interval"] = INTERVALS[_pick]
    live_status()
    if st.button("Add one update now", use_container_width=True):
        bump(1)
        st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("Load demo data", use_container_width=True):
        st.session_state.db = ensure_live(demo_data(), st.session_state.db["live"])
        db = st.session_state.db
        save_db()
        st.rerun()
    if c2.button("Reset all", use_container_width=True):
        st.session_state.db = ensure_live({"depot": {"x": 0.0, "y": 0.0}, "bins": [], "history": []}, st.session_state.db["live"])
        db = st.session_state.db
        save_db()
        st.rerun()

df = bins_df()
overflow = [b for b in db["bins"] if b["fill"] >= 100]

# --------------------------------------------------------------------------
# PAGE: DASHBOARD
# --------------------------------------------------------------------------
if page.endswith("Dashboard"):
    hero("City waste at a glance", "Only collect what is full. BinSense shows which bins need a pickup and the shortest way to reach them.")
    if df.empty:
        empty_state()
    else:
        if overflow:
            st.markdown(f'<div class="banner">⚠ Overflow alert: {", ".join(b["id"] for b in overflow)} '
                        f'{"is" if len(overflow) == 1 else "are"} at 100%. Collect now.</div>', unsafe_allow_html=True)
        k = st.columns(4)
        kpi(k[0], "Total bins", len(df), "registered in the city", INK)
        kpi(k[1], f"Need collection (≥{THRESHOLD}%)", int((df["Fill %"] >= THRESHOLD).sum()), "included in today's route", ORANGE)
        kpi(k[2], "Overflowing", len(overflow), "bins at 100%", CORAL)
        kpi(k[3], "Average fill", f"{df['Fill %'].mean():.0f}%", "across all bins", EMERALD)
        st.write("")

        a, b = st.columns([2, 1])
        d = df.sort_values("Fill %", ascending=False)
        fig = px.bar(d, x="Bin ID", y="Fill %", color="Status", color_discrete_map=STATUS_COLORS,
                     text="Fill %", title="Fill level by bin")
        fig.add_hline(y=THRESHOLD, line_dash="dash", line_color=INK, annotation_text=f"{THRESHOLD}% threshold")
        fig.update_traces(textposition="outside")
        fig.update_yaxes(range=[0, 115])
        a.plotly_chart(style(fig), use_container_width=True)

        counts = df["Status"].value_counts().reset_index()
        counts.columns = ["Status", "Count"]
        fig = px.pie(counts, names="Status", values="Count", hole=.62, color="Status",
                     color_discrete_map=STATUS_COLORS, title="Bin status mix")
        b.plotly_chart(style(fig), use_container_width=True)

        a, b = st.columns([2, 1])
        fig = px.scatter(df, x="X", y="Y", size="Fill %", color="Status", text="Bin ID",
                         color_discrete_map=STATUS_COLORS, size_max=38, title="Bin locations (bubble size = fill)")
        fig.add_trace(go.Scatter(x=[db["depot"]["x"]], y=[db["depot"]["y"]], mode="markers+text", text=["DEPOT"],
                                 textposition="bottom center", name="Depot",
                                 marker=dict(symbol="star", size=20, color=INK)))
        fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        a.plotly_chart(style(fig, 420), use_container_width=True)

        fig = go.Figure(go.Indicator(mode="gauge+number", value=df["Fill %"].mean(),
                                     number={"suffix": "%"}, title={"text": "City average fill"},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": INK},
                                            "steps": [{"range": [0, 50], "color": "#D9F7EA"},
                                                      {"range": [50, THRESHOLD], "color": "#FFF0CC"},
                                                      {"range": [THRESHOLD, 100], "color": "#FFD9C2"}]}))
        b.plotly_chart(style(fig, 420, False), use_container_width=True)

# --------------------------------------------------------------------------
# PAGE: MANAGE BINS  (Features 1 & 2)
# --------------------------------------------------------------------------
elif page.endswith("Manage Bins"):
    hero("Manage bins", "Register dustbins, update fill levels as new readings arrive, or remove a bin.")
    t1, t2, t3, t4 = st.tabs(["Add bin", "Update fill level", "All bins", "Remove bin"])

    with t1:
        with st.form("add_bin", clear_on_submit=True):
            c = st.columns(5)
            bid = c[0].text_input("Bin ID", placeholder="B11").strip().upper()
            x = c[1].number_input("X coordinate", value=0.0, step=1.0)
            y = c[2].number_input("Y coordinate", value=0.0, step=1.0)
            fill = c[3].number_input("Fill %", 0, 100, 0)
            rate = c[4].number_input("Fill rate (% per update)", 0.0, 20.0, 2.0, 0.5)
            if st.form_submit_button("Add bin"):
                if not bid:
                    st.error("Enter a Bin ID.")
                elif any(b["id"] == bid for b in db["bins"]):
                    st.error(f"{bid} already exists. Use a different ID.")
                else:
                    db["bins"].append({"id": bid, "x": x, "y": y, "fill": fill, "rate": rate, "readings": [[now_str(), fill]]})
                    save_db()
                    st.success(f"Added {bid} at ({x:g}, {y:g}) with {fill}% fill.")
                    st.rerun()

    with t2:
        if not db["bins"]:
            empty_state()
        else:
            with st.form("upd"):
                c = st.columns(2)
                sel = c[0].selectbox("Bin", [b["id"] for b in db["bins"]])
                cur = next(b for b in db["bins"] if b["id"] == sel)["fill"]
                new = c[1].slider("New fill %", 0, 100, int(cur))
                if st.form_submit_button("Update level"):
                    b = next(b for b in db["bins"] if b["id"] == sel)
                    old, b["fill"] = b["fill"], new
                    b.setdefault("readings", []).append([now_str(), new])
                    save_db()
                    st.success(f"{sel}: {old}% → {new}%")
                    if new >= 100:
                        st.error(f"Overflow warning: {sel} is full. Collect it now.")
                    elif new >= THRESHOLD:
                        st.warning(f"{sel} is above {THRESHOLD}% and will be on the next route.")

    with t3:
        if df.empty:
            empty_state()
        else:
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Fill %": st.column_config.ProgressColumn("Fill %", min_value=0, max_value=100, format="%.0f%%")})

    with t4:
        if db["bins"]:
            sel = st.selectbox("Bin to remove", [b["id"] for b in db["bins"]], key="del")
            if st.button("Remove bin"):
                db["bins"] = [b for b in db["bins"] if b["id"] != sel]
                save_db()
                st.rerun()
        else:
            empty_state()

# --------------------------------------------------------------------------
# PAGE: ALERTS  (Features 3 & 5)
# --------------------------------------------------------------------------
elif page.endswith("Alerts"):
    hero("Alerts", f"Bins above {THRESHOLD}% are ready for pickup. Bins at 100% are overflowing.")
    if df.empty:
        empty_state()
    else:
        a, b = st.columns(2)
        a.subheader(f"Bins above {THRESHOLD}%")
        due = sorted(due_bins(), key=lambda x: -x["fill"])
        if not due:
            a.success("No bin needs collection right now.")
        for x in due:
            col = CORAL if x["fill"] >= 100 else ORANGE
            a.markdown(f'<div class="alert" style="--c:{col}"><b>{x["id"]}</b> &nbsp;·&nbsp; {x["fill"]}% full'
                       f'<br><small>Location ({x["x"]:g}, {x["y"]:g})</small></div>', unsafe_allow_html=True)
        b.subheader("Overflow warnings")
        if not overflow:
            b.success("No overflowing bins.")
        for x in overflow:
            b.markdown(f'<div class="alert" style="--c:{CORAL}"><b>⚠ OVERFLOW: {x["id"]}</b><br>'
                       f'<small>Bin is at 100% at ({x["x"]:g}, {x["y"]:g}). Send a truck immediately.</small></div>',
                       unsafe_allow_html=True)
        soon = [(x, predict(x)[1]) for x in db["bins"] if x["fill"] < 100 and predict(x)[1] is not None]
        soon = sorted([s for s in soon if s[1] <= 6], key=lambda s: s[1])
        if soon:
            b.subheader("Will overflow within 6 hours")
            for x, h in soon:
                b.markdown(f'<div class="alert" style="--c:{AMBER}"><b>{x["id"]}</b> &nbsp;·&nbsp; full in about {h:g} h</div>',
                           unsafe_allow_html=True)

# --------------------------------------------------------------------------
# PAGE: ROUTE PLANNER  (Feature 4 + Google Maps)
# --------------------------------------------------------------------------
elif page.endswith("Route Planner"):
    hero("Route planner", "Nearest Neighbour route through every bin above the threshold, starting at the depot.")
    if df.empty:
        empty_state()
    else:
        c = st.columns([1, 1, 2])
        db["depot"]["x"] = c[0].number_input("Truck start X", value=float(db["depot"]["x"]), step=1.0)
        db["depot"]["y"] = c[1].number_input("Truck start Y", value=float(db["depot"]["y"]), step=1.0)
        return_home = c[2].checkbox("Return to depot after last bin", value=True)
        depot = (db["depot"]["x"], db["depot"]["y"])
        order, legs, total = nearest_neighbour(depot, due_bins(), return_home)

        if not order:
            st.success(f"No bin is above {THRESHOLD}%. No trip needed today.")
        else:
            fs = fuel_savings(return_home)
            k = st.columns(4)
            kpi(k[0], "Stops", len(order), "bins to collect", ORANGE)
            kpi(k[1], "Route distance", f"{total:.1f} km", "nearest neighbour", INK)
            kpi(k[2], "Distance saved", f"{fs['saved_km']:.1f} km", f"{fs['pct']:.0f}% vs visiting all bins", EMERALD)
            kpi(k[3], "Fuel saved", f"{fs['litres']:.1f} L", f"≈ {fs['money']:.0f} money units", LIME)
            st.write("")

            # route chart
            fig = go.Figure()
            others = [b for b in db["bins"] if b["fill"] < THRESHOLD]
            fig.add_trace(go.Scatter(x=[b["x"] for b in others], y=[b["y"] for b in others], mode="markers+text",
                                     text=[b["id"] for b in others], textposition="top center", name="Skipped",
                                     marker=dict(size=11, color="#C9D3CF")))
            path = [depot] + [(b["x"], b["y"]) for b in order] + ([depot] if return_home else [])
            for i in range(len(path) - 1):
                fig.add_annotation(x=path[i + 1][0], y=path[i + 1][1], ax=path[i][0], ay=path[i][1],
                                   xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                                   arrowhead=3, arrowsize=1.3, arrowwidth=2.6, arrowcolor=EMERALD)
            fig.add_trace(go.Scatter(x=[b["x"] for b in order], y=[b["y"] for b in order], mode="markers+text",
                                     text=[f"{i + 1}" for i in range(len(order))], textfont=dict(color="white", size=13),
                                     name="Stops", marker=dict(size=30, color=[CORAL if b["fill"] >= 100 else ORANGE for b in order])))
            fig.add_trace(go.Scatter(x=[depot[0]], y=[depot[1]], mode="markers+text", text=["DEPOT"],
                                     textposition="bottom center", name="Depot",
                                     marker=dict(symbol="star", size=24, color=INK)))
            fig.update_layout(title="Collection route (numbers show visiting order)")
            st.plotly_chart(style(fig, 460), use_container_width=True)

            # table
            rows, cum, prev = [], 0.0, "Depot"
            for i, (b, d) in enumerate(zip(order, legs), 1):
                cum += d
                rows.append({"Stop": i, "From": prev, "To": b["id"], "Fill %": b["fill"],
                             "Leg (km)": round(d, 2), "Cumulative (km)": round(cum, 2)})
                prev = b["id"]
            if return_home:
                last = dist((order[-1]["x"], order[-1]["y"]), depot)
                rows.append({"Stop": "-", "From": prev, "To": "Depot", "Fill %": None,
                             "Leg (km)": round(last, 2), "Cumulative (km)": round(total, 2)})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("Order: Depot → " + " → ".join(b["id"] for b in order) + (" → Depot" if return_home else ""))

            # Google Maps - no API key needed
            st.subheader("Route on Google Maps")
            open_url, embed_url = google_maps_links(depot, order, return_home)
            st.link_button("Open full route in Google Maps", open_url, type="primary")
            components.iframe(embed_url, height=500)
            st.caption("No API key needed. The map uses real coordinates built from BASE_LAT, BASE_LNG and KM_PER_UNIT in app.py. "
                       "If the embedded map is blank, use the button above.")

            st.divider()
            if st.button("Mark route as collected"):
                run_no = max([h["route_no"] for h in db["history"]], default=0) + 1
                for b in order:
                    db["history"].append({"route_no": run_no, "bin_id": b["id"], "time": now_str(), "prev_fill": b["fill"]})
                    b["fill"] = 0
                    b["readings"] = [[now_str(), 0]]
                save_db()
                st.success(f"Route {run_no} recorded. {len(order)} bins emptied.")
                st.rerun()

# --------------------------------------------------------------------------
# PAGE: ANALYTICS
# --------------------------------------------------------------------------
elif page.endswith("Analytics"):
    hero("Analytics", "Fill trends, overflow predictions and fuel savings.")
    if df.empty:
        empty_state()
    else:
        t1, t2, t3, t4 = st.tabs(["Fill trends", "Predictions", "Fuel savings", "Spatial insights"])

        with t1:
            rows = [{"Bin": b["id"], "Time": r[0], "Fill %": r[1]} for b in db["bins"] for r in b.get("readings", [])]
            if rows:
                rd = pd.DataFrame(rows)
                rd["Time"] = pd.to_datetime(rd["Time"])
                fig = px.line(rd, x="Time", y="Fill %", color="Bin", markers=True, title="Fill level over time",
                              color_discrete_sequence=px.colors.qualitative.Bold)
                fig.add_hline(y=THRESHOLD, line_dash="dash", line_color=INK)
                st.plotly_chart(style(fig, 440), use_container_width=True)
            fig = px.histogram(df, x="Fill %", nbins=10, title="Distribution of fill levels", color_discrete_sequence=[EMERALD])
            st.plotly_chart(style(fig, 320, False), use_container_width=True)

        with t2:
            pr = []
            for b in db["bins"]:
                rate, left = predict(b)
                pr.append({"Bin ID": b["id"], "Fill %": b["fill"], "Rate (% per hour)": rate,
                           "Hours to full": left if b["fill"] < 100 else 0,
                           "Expected full at": (datetime.now() + timedelta(hours=left)).strftime("%d %b, %H:%M") if left is not None and b["fill"] < 100
                           else ("Now" if b["fill"] >= 100 else "n/a")})
            pdf = pd.DataFrame(pr)
            valid = pdf.dropna(subset=["Hours to full"]).sort_values("Hours to full")
            if not valid.empty:
                fig = px.bar(valid, x="Hours to full", y="Bin ID", orientation="h", color="Hours to full",
                             color_continuous_scale=[CORAL, AMBER, EMERALD], title="Hours until each bin overflows")
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(style(fig, 420, False), use_container_width=True)
            st.dataframe(pdf, use_container_width=True, hide_index=True)
            st.caption("Rate is the average % increase per hour over the latest rising readings. Update fill levels regularly for better predictions.")

        with t3:
            rh = st.checkbox("Include return to depot", value=True, key="rh2")
            fs = fuel_savings(rh)
            k = st.columns(4)
            kpi(k[0], "Visit all bins", f"{fs['all_km']:.1f} km", "daily full round", INK)
            kpi(k[1], "Visit only due bins", f"{fs['due_km']:.1f} km", f"bins ≥ {THRESHOLD}%", ORANGE)
            kpi(k[2], "Saved", f"{fs['saved_km']:.1f} km", f"{fs['pct']:.0f}% shorter", EMERALD)
            kpi(k[3], "Fuel & cost saved", f"{fs['litres']:.1f} L", f"≈ {fs['money']:.0f} money units", LIME)
            st.write("")
            cmp = pd.DataFrame({"Plan": ["Visit all bins", f"Only bins ≥ {THRESHOLD}%"], "Distance (km)": [fs["all_km"], fs["due_km"]]})
            fig = px.bar(cmp, x="Plan", y="Distance (km)", color="Plan", text_auto=".1f",
                         color_discrete_sequence=["#C9D3CF", EMERALD], title="Distance travelled per trip")
            a, b = st.columns(2)
            a.plotly_chart(style(fig, 380, False), use_container_width=True)
            monthly = fs["saved_km"] * 30
            fig = px.bar(x=["Per day", "Per month (30 days)"], y=[fs["litres"], fs["litres"] * 30],
                         labels={"x": "", "y": "Litres saved"}, text_auto=".1f", title="Fuel saved",
                         color_discrete_sequence=[LIME])
            b.plotly_chart(style(fig, 380, False), use_container_width=True)
            st.info(f"Skipping bins that are not full saves about {monthly:.0f} km of driving per month.")

        with t4:
            fig = px.scatter(df, x="Distance from depot (km)", y="Fill %", color="Status", size="Fill %", text="Bin ID",
                             color_discrete_map=STATUS_COLORS, title="Distance from depot vs fill level")
            fig.update_traces(textposition="top center")
            st.plotly_chart(style(fig, 420), use_container_width=True)
            fig = px.density_heatmap(df, x="X", y="Y", z="Fill %", histfunc="avg", nbinsx=8, nbinsy=8,
                                     color_continuous_scale=["#FFFFFF", LIME, EMERALD, ORANGE, CORAL],
                                     title="Waste heat map (average fill by area)")
            st.plotly_chart(style(fig, 420, False), use_container_width=True)

# --------------------------------------------------------------------------
# PAGE: COLLECTION HISTORY  (Feature 5)
# --------------------------------------------------------------------------
else:
    hero("Collection history", "Every collected bin with its ID, date and time, and the fill level before pickup.")
    if not db["history"]:
        st.markdown(
            '<div class="history-empty">Nothing collected yet. Generate a route and press '
            '<strong>Mark route as collected</strong>.</div>',
            unsafe_allow_html=True,
        )
    else:
        h = pd.DataFrame(db["history"]).rename(columns={"route_no": "Route", "bin_id": "Bin ID", "time": "Collected at",
                                                         "prev_fill": "Fill before pickup %"})
        h = h[["Route", "Bin ID", "Collected at", "Fill before pickup %"]].iloc[::-1]
        k = st.columns(3)
        kpi(k[0], "Routes completed", h["Route"].nunique(), "so far", INK)
        kpi(k[1], "Bins collected", len(h), "total pickups", EMERALD)
        kpi(k[2], "Avg fill at pickup", f"{h['Fill before pickup %'].mean():.0f}%", "higher is more efficient", ORANGE)
        st.write("")
        st.dataframe(h, use_container_width=True, hide_index=True,
                     column_config={"Fill before pickup %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%")})
        a, b = st.columns(2)
        cnt = h["Bin ID"].value_counts().reset_index()
        cnt.columns = ["Bin ID", "Pickups"]
        a.plotly_chart(style(px.bar(cnt, x="Bin ID", y="Pickups", title="Pickups per bin", color_discrete_sequence=[EMERALD]), 360, False),
                       use_container_width=True)
        per_route = h.groupby("Route").size().reset_index(name="Bins collected")
        b.plotly_chart(style(px.bar(per_route, x="Route", y="Bins collected", title="Bins collected per route",
                                    color_discrete_sequence=[ORANGE]), 360, False), use_container_width=True)
        st.download_button("Download history (CSV)", h.to_csv(index=False), "binsense_history.csv", "text/csv")

import base64
import html
import inspect
import requests
from pathlib import Path

import streamlit as st

from compliance import run_compliance_checks
from parser import parse_product

API_BASE_URL = "http://localhost:8000"

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FMCG Label Compliance Auditor",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "rules.json"


# ============================================================
# DESIGN TOKENS
# ============================================================

PRIMARY = "#5B2DB5"
DARK_PURPLE = "#24134F"
DEEP_NAVY = "#17152F"
LAVENDER = "#F2ECFF"
LAVENDER_LIGHT = "#F8F5FF"
MUTED = "#626174"
BORDER = "#E6E1F0"


# ============================================================
# ICONS (inline Lucide-style line icons)
# ============================================================

def icon(paths, size=20, color=PRIMARY, stroke=1.8, cls="ico"):
        markup = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'{paths.replace("currentColor", color)}</svg>'
    )
        encoded = base64.b64encode(markup.encode("utf-8")).decode("ascii")
        return (
        f'<img class="{cls}" src="data:image/svg+xml;base64,{encoded}" '
        f'alt="" aria-hidden="true" '
        f'style="width:{size}px;height:{size}px;display:block;flex:0 0 auto;" />'
    )


IC_TAG = (
    '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 '
    '1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 '
    '0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>'
)

IC_MANDATORY = (
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h6"/><path d="M8 17h4"/>'
)

IC_FLASK = (
    '<path d="M10 2v7.31"/><path d="M14 9.3V1.99"/><path d="M8.5 2h7"/>'
    '<path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><path d="M5.52 16h12.96"/>'
)

IC_CHART = (
    '<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/>'
    '<line x1="6" x2="6" y1="20" y2="14"/>'
)

IC_ALERT = (
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 '
    '1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>'
)

IC_UPLOAD_CLOUD = (
    '<path d="M12 13v8"/><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 '
    '2.5 8.242"/><path d="m8 17 4-4 4 4"/>'
)

IC_SCAN = (
    '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
    '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/>'
    '<path d="M7 12h10"/>'
)

IC_SCALE = (
    '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1"/>'
    '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1"/>'
    '<path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'
)

IC_BARS = (
    '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M7 16v-4"/><path d="M12 16V8"/>'
    '<path d="M17 16v-6"/>'
)

IC_BRAIN = (
    '<circle cx="12" cy="12" r="9"/><path d="M12 3c-2 3-2 15 0 18"/>'
    '<path d="M3 12h18"/>'
)

IC_CLIPBOARD = (
    '<rect width="8" height="4" x="8" y="2" rx="1"/>'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
    '<path d="M9 12h6"/><path d="M9 16h4"/>'
)

IC_IMAGE = (
    '<rect width="18" height="18" x="3" y="3" rx="2"/>'
    '<circle cx="9" cy="9" r="2"/><path d="m21 15-4.586-4.586a2 2 0 0 0-2.828 0L3 21"/>'
)

IC_MONITOR = (
    '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/>'
    '<path d="M12 17v4"/><path d="m10 7 5 3-5 3z"/>'
)

IC_INFO = (
    '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
)

IC_ARROW = '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>'

# ============================================================
# HTML / CSS RENDERER
# ============================================================
# Some Streamlit builds sanitize `<style>` tags out of render_html(), which strips
# every style rule and leaves the page unstyled. st.markdown with
# unsafe_allow_html=True keeps them, so all markup goes through this helper.
# Lines are collapsed first: markdown turns 4-space-indented lines into code
# blocks, which would otherwise mangle the indented HTML below.


def render_html(markup: str) -> None:
    compact = " ".join(
        line.strip() for line in markup.strip().splitlines() if line.strip()
    )
    st.markdown(compact, unsafe_allow_html=True)

# ============================================================
# CUSTOM CSS
# ============================================================

render_html(
    f"""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, .stApp, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}

    html {{ scroll-behavior: smooth; }}
    .section-anchor {{ scroll-margin-top: 2rem; }}

    /* ========================================================
       PAGE SHELL
       ======================================================== */

    /* The reference design is a light UI. These rules keep it light even when
       Streamlit is running with its dark theme active. */

    :root {{ color-scheme: light; }}

    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background: #FFFFFF !important;
        color: {DEEP_NAVY} !important;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: {DEEP_NAVY} !important;
    }}

    .stApp p, .stApp li, .stApp label, .stApp .stMarkdown {{
        color: {MUTED} ;
    }}

    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        padding-left: 1.6rem;
        padding-right: 1.6rem;
        max-width: 1400px;
    }}

    #MainMenu, footer {{ visibility: hidden; }}

    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {{
        width: 280px !important;
        min-width: 280px !important;
        background: #FFFFFF;
        border-right: 1px solid {BORDER};
    }}

    section[data-testid="stSidebar"] > div {{
        padding-top: 1.6rem;
    }}

    .sb-brand {{
        display: flex;
        gap: 0.7rem;
        align-items: flex-start;
    }}

    .sb-logo {{
        flex: 0 0 auto;
        margin-top: 2px;
    }}

    .sb-title {{
        font-size: 1.22rem;
        font-weight: 700;
        line-height: 1.25;
        color: {DEEP_NAVY};
        letter-spacing: -0.01em;
    }}

    .sb-subtitle {{
        font-size: 0.82rem;
        color: {MUTED};
        line-height: 1.45;
        margin-top: 0.55rem;
    }}

    .sb-divider {{
        height: 1px;
        background: {BORDER};
        margin: 1.35rem 0 1.1rem 0;
    }}

    .sb-section {{
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #7C7A96;
        margin-bottom: 0.6rem;
    }}

    .sb-nav {{
        display: flex;
        flex-direction: column;
        gap: 2px;
    }}

    .sb-item {{
        display: flex;
        align-items: center;
        gap: 0.85rem;
        height: 50px;
        padding: 0 0.85rem;
        border-radius: 12px;
        font-size: 0.97rem;
        font-weight: 500;
        color: {DEEP_NAVY};
        transition: background 160ms ease;
    }}

    .sb-item:hover {{
        background: {LAVENDER_LIGHT};
    }}

    .sb-item.active {{
        background: {LAVENDER};
        font-weight: 600;
    }}

    /* Sidebar highlight follows the selected page anchor. */
    body:has(#mandatory-section:target) .sb-item[data-section="mandatory-section"],
    body:has(#ingredients-section:target) .sb-item[data-section="ingredients-section"],
    body:has(#nutrition-section:target) .sb-item[data-section="nutrition-section"],
    body:has(#claims-section:target) .sb-item[data-section="claims-section"],
    body:has(#regulatory-section:target) .sb-item[data-section="regulatory-section"] {{
        background: {LAVENDER};
        font-weight: 600;
    }}

    .sb-item svg {{ flex: 0 0 auto; }}

    .sb-footer {{
        margin-top: 1.6rem;
        padding-top: 1.1rem;
        border-top: 1px solid {BORDER};
        color: #8B8AA0;
        font-size: 0.79rem;
        line-height: 1.7;
    }}

    /* sidebar controls */
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stSelectbox label {{
        color: {MUTED};
        font-size: 0.82rem;
    }}

    /* ========================================================
       HERO
       ======================================================== */

    .hero {{
        position: relative;
        overflow: hidden;
        min-height: 300px;
        border: 1px solid {BORDER};
        border-radius: 20px;
        padding: 44px 46px;
        margin-bottom: 2rem;
        background:
            radial-gradient(120% 140% at 100% 0%, #EFE4FB 0%, rgba(248,245,255,0) 60%),
            linear-gradient(115deg, #FBF9FF 0%, #F6F1FD 55%, #F0E7FA 100%);
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.06);
    }}

    .hero-blob {{
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
    }}

    .blob-a {{
        width: 460px; height: 460px;
        right: -120px; top: -180px;
        background: radial-gradient(circle at 40% 40%, rgba(140,88,214,0.16), rgba(140,88,214,0) 70%);
    }}

    .blob-b {{
        width: 520px; height: 520px;
        right: -60px; bottom: -300px;
        background: radial-gradient(circle at 50% 40%, rgba(102,51,181,0.13), rgba(102,51,181,0) 70%);
    }}

    .blob-c {{
        width: 300px; height: 300px;
        right: 190px; top: 40px;
        background: radial-gradient(circle at 50% 50%, rgba(168,132,224,0.12), rgba(168,132,224,0) 72%);
    }}

    .hero-inner {{ position: relative; z-index: 2; max-width: 780px; }}

    .hero-eyebrow {{
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {PRIMARY};
        margin-bottom: 1.1rem;
    }}

    .hero-title {{
        font-size: 3.35rem;
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: -0.03em;
        color: {DARK_PURPLE};
        margin: 0 0 1rem 0;
    }}

    .hero-sub {{
        font-size: 1.24rem;
        line-height: 1.55;
        color: #4C4A63;
        margin-bottom: 1.7rem;
        max-width: 660px;
    }}

    .hero-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.85rem;
    }}

    .badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.6rem;
        height: 46px;
        padding: 0 1.25rem;
        border-radius: 999px;
        background: #FFFFFF;
        border: 1px solid {BORDER};
        box-shadow: 0 4px 14px rgba(40, 20, 80, 0.05);
        font-size: 1rem;
        font-weight: 500;
        color: {DARK_PURPLE};
    }}

    /* ========================================================
       SECTION HEADINGS
       ======================================================== */

    .sec-title {{
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: {DARK_PURPLE};
        margin-bottom: 0.25rem;
    }}

    .sec-sub {{
        font-size: 1rem;
        color: {MUTED};
        margin-bottom: 1.4rem;
    }}

    /* ========================================================
       WORKFLOW
       ======================================================== */

    .flow {{
        display: flex;
        align-items: stretch;
        gap: 0;
        margin-bottom: 2rem;
    }}

    .flow-card {{
        flex: 1 1 0;
        background: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 17px;
        padding: 20px 22px 26px 22px;
        min-height: 236px;
        position: relative;
        text-align: center;
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.05);
        transition: transform 180ms ease, box-shadow 180ms ease;
    }}

    .flow-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 26px rgba(40, 20, 80, 0.09);
    }}

    .flow-step {{
        position: absolute;
        top: 18px; left: 18px;
        width: 26px; height: 26px;
        border-radius: 50%;
        background: {LAVENDER};
        color: {PRIMARY};
        font-size: 0.78rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .flow-icon {{
        width: 74px; height: 74px;
        margin: 20px auto 16px auto;
        border-radius: 50%;
        background: {PRIMARY};
        display: flex;
        align-items: center;
        justify-content: center;
         overflow: visible;
    }}

    /* Icons are <img> data-URI SVGs (see the icon() helper): colour and stroke
       live inside the encoded document, so only sizing is needed here. */
    .flow-icon img {{
        width: 34px !important;
        height: 34px !important;
        display: block;
        flex: 0 0 auto;
    }}

    .flow-arrow img {{
        width: 22px !important;
        height: 22px !important;
        display: block;
    }}

    .flow-title {{
        font-size: 1.13rem;
        font-weight: 700;
        color: {DARK_PURPLE};
        margin-bottom: 0.5rem;
    }}

    .flow-text {{
        font-size: 0.94rem;
        line-height: 1.5;
        color: {MUTED};
    }}

    .flow-arrow {{
        flex: 0 0 54px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    /* ========================================================
       PANEL + METHOD CARDS
       ======================================================== */

    .panel {{
        background: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 18px;
        padding: 26px 28px 8px 28px;
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.06);
        margin-bottom: 0.4rem;
    }}

    .panel-title {{
        font-size: 1.4rem;
        font-weight: 700;
        color: {DARK_PURPLE};
        letter-spacing: -0.01em;
    }}

    .method {{
        display: flex;
        align-items: center;
        gap: 1.4rem;
        background: {LAVENDER_LIGHT};
        border: 1.6px dashed #C9B4EE;
        border-radius: 18px;
        padding: 26px 28px;
        min-height: 170px;
        transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
    }}

    .method:hover {{
        background: {LAVENDER};
        border-color: {PRIMARY};
        transform: translateY(-2px);
    }}

    .method-icon {{
        flex: 0 0 auto;
        width: 84px; height: 84px;
        border-radius: 50%;
        background: #E8DCFB;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .method-title {{
        font-size: 1.28rem;
        font-weight: 700;
        color: {PRIMARY};
        margin-bottom: 0.45rem;
    }}

    .method-text {{
        font-size: 1rem;
        line-height: 1.5;
        color: #4C4A63;
    }}

    /* ---- whole-card click target (overlay button) ---- */

    .st-key-method_upload,
    .st-key-method_demo {{
        position: relative;
        margin-bottom: 1rem;
    }}


    .st-key-method_upload:hover .method,
    .st-key-method_demo:hover .method {{
        background: {LAVENDER};
        border-color: {PRIMARY};
        transform: translateY(-2px);
        box-shadow: 0 8px 26px rgba(40, 20, 80, 0.10);
    }}

    .st-key-method_upload:hover .method-icon,
    .st-key-method_demo:hover .method-icon {{
        background: #DCCBF9;
    }}

    .st-key-method_upload:focus-within .method,
    .st-key-method_demo:focus-within .method {{
        border-style: solid;
        border-color: {PRIMARY};
        box-shadow: 0 0 0 3px rgba(91, 45, 181, 0.18);
    }}

    .helper {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.55rem;
        color: {MUTED};
        font-size: 0.98rem;
        padding: 1.1rem 0 1.4rem 0;
    }}

    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {{
        width: 100%;
        border-radius: 12px;
        border: 1px solid {BORDER};
        background: #FFFFFF;
        color: {PRIMARY};
        font-weight: 600;
        padding: 0.6rem 1rem;
        transition: all 160ms ease;
    }}

    .stButton > button:hover {{
        border-color: {PRIMARY};
        background: {LAVENDER_LIGHT};
        color: {DARK_PURPLE};
    }}

    /* ========================================================
       INPUTS
       ======================================================== */

    section[data-testid="stFileUploaderDropzone"] {{
        background: {LAVENDER_LIGHT};
        border: 1.6px dashed #C9B4EE;
        border-radius: 14px;
    }}

    /* Streamlit's uploader button is not inside .stButton, so style it
       explicitly to preserve the light purple visual system. */
    section[data-testid="stFileUploaderDropzone"] button {{
        background: #FFFFFF !important;
        border: 1px solid #BDA2E8 !important;
        border-radius: 10px !important;
        color: {PRIMARY} !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }}

    section[data-testid="stFileUploaderDropzone"] button:hover {{
        background: {LAVENDER} !important;
        border-color: {PRIMARY} !important;
        color: {DARK_PURPLE} !important;
    }}

    section[data-testid="stFileUploaderDropzone"] small,
    section[data-testid="stFileUploaderDropzone"] span,
    section[data-testid="stFileUploaderDropzone"] p {{
        color: {MUTED} !important;
    }}

    div[data-baseweb="select"] > div {{
        border-radius: 12px;
        border-color: {BORDER};
    }}

    /* ========================================================
       CARDS / METRICS / RESULTS
       ======================================================== */

    .info-card {{
        background: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 0.9rem;
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.05);
    }}

    .kicker {{
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #7C7A96;
    }}

    .value-lg {{
        font-size: 1.2rem;
        font-weight: 700;
        color: {DARK_PURPLE};
        margin-top: 0.15rem;
    }}

    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 15px;
        padding: 0.85rem 1rem;
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.05);
    }}

    div[data-testid="stMetricLabel"] {{ color: {MUTED}; }}
    div[data-testid="stMetricValue"] {{ color: {DARK_PURPLE}; }}

    .claim-pill {{
        display: inline-block;
        background: {LAVENDER};
        border: 1px solid #DCCFF5;
        color: {PRIMARY};
        border-radius: 999px;
        padding: 0.38rem 0.8rem;
        margin: 0 0.35rem 0.4rem 0;
        font-size: 0.85rem;
        font-weight: 600;
    }}

    .result {{
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 0.9rem;
        border: 1px solid {BORDER};
        background: #FFFFFF;
        box-shadow: 0 4px 20px rgba(40, 20, 80, 0.05);
    }}

    .result.pass {{ border-left: 4px solid #3F9E6A; }}
    .result.review {{ border-left: 4px solid #C9922B; }}
    .result.flagged {{ border-left: 4px solid #C2455B; }}

    .result-head {{
        font-size: 1.02rem;
        font-weight: 700;
        color: {DARK_PURPLE};
        margin-bottom: 0.6rem;
    }}

    .result-row {{
        font-size: 0.88rem;
        color: #4C4A63;
        margin-bottom: 0.32rem;
    }}

    .result-ref {{
        font-size: 0.82rem;
        color: {MUTED};
        margin-top: 0.6rem;
    }}

    .app-footer {{
        text-align: center;
        color: #8B8AA0;
        font-size: 0.8rem;
        margin-top: 2.2rem;
        padding-top: 1.1rem;
        border-top: 1px solid {BORDER};
    }}

    /* ========================================================
       RESPONSIVE
       ======================================================== */

    @media (max-width: 1100px) {{
        .hero {{ padding: 34px 30px; }}
        .hero-title {{ font-size: 2.5rem; }}
        .hero-sub {{ font-size: 1.08rem; }}
        .flow-arrow {{ flex: 0 0 34px; }}
        .flow-card {{ padding: 18px 14px 22px 14px; }}
    }}

    @media (max-width: 760px) {{
        .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
        .hero {{ padding: 26px 22px; min-height: 0; }}
        .hero-title {{ font-size: 2rem; }}
        .hero-sub {{ font-size: 1rem; }}
        .badge {{ height: 40px; font-size: 0.9rem; padding: 0 0.9rem; }}
        .flow {{ flex-direction: column; }}
        .flow-card {{ min-height: 0; }}
        .flow-arrow {{ flex: 0 0 42px; transform: rotate(90deg); }}
        .method {{ flex-direction: column; text-align: center; }}
        .panel {{ padding: 20px 18px 8px 18px; }}
    }}

    </style>
    """
)


# ============================================================
# PRESET SAMPLES
# IMPORTANT:
# These keys match the nutrition keys expected by rules.json.
# ============================================================

PRESET_SAMPLES = {

    "Sample 1: Deceptive Choco Biscuits": {

        "product_name": "Delight Choco Biscuits 150g",

        "category": "Biscuits / Bakery",

        "claims": [
            "Zero Sugar"
        ],

        "ingredients": [
            "Refined Wheat Flour",
            "Palm Oil",
            "Cocoa Solids",
            "Maltodextrin",
            "Leavening Agents"
        ],

        "nutrition": {
            "total_sugars_g": 18.0,
            "sodium_mg": 210.0,
            "calories": 460.0
        },

        "declared_basis": "100g",
        "serving_size_g": 150.0,

        "front_uploaded": True,
        "back_uploaded": True
    },


    "Sample 2: Hidden Sweetener Energy Bar": {

        "product_name": "Vitality Crunch Bar 40g",

        "category": "Cereal Snacks",

        "claims": [
            "No Added Sugar"
        ],

        "ingredients": [
            "Rolled Oats",
            "Almonds",
            "Maltodextrin",
            "Honey",
            "Chia Seeds"
        ],

        "nutrition": {
            "total_sugars_g": 3.2,
            "sodium_mg": 85.0,
            "calories": 180.0
        },

        "declared_basis": "100g",
        "serving_size_g": 40.0,

        "front_uploaded": True,
        "back_uploaded": True
    },


    "Sample 3: Fully Compliant Organic Green Tea": {

        "product_name": "Pure Himalaya Green Tea 50g",

        "category": "Beverages",

        "claims": [
            "Zero Sugar",
            "Low Sodium"
        ],

        "ingredients": [
            "Organic Green Tea Leaves"
        ],

        "nutrition": {
            "total_sugars_g": 0.0,
            "sodium_mg": 5.0,
            "calories": 2.0
        },

        "declared_basis": "100g",
        "serving_size_g": 50.0,

        "front_uploaded": True,
        "back_uploaded": True
    }
}


UPLOAD_MODE = "Upload Packaging Images"
DEMO_MODE = "Select Preset Sample (Demo Mode)"


if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = None


# ============================================================
# SIDEBAR
# ============================================================

NAV_ITEMS = [
    ("Mandatory", IC_MANDATORY, True),
    ("Ingredients", IC_FLASK, False),
    ("Nutrition", IC_CHART, False),
    ("Claims", IC_TAG, False),
    ("Regulatory", IC_ALERT, False),
]


with st.sidebar:

    nav_html = ""

    for label, glyph, _ in NAV_ITEMS:

        nav_html += (
            f'<a class="sb-item" href="#{label.lower()}-section" '
            f'data-section="{label.lower()}-section">'
            f'{icon(glyph, size=21)}'
            f'<span>{label}</span>'
            f'</a>'
        )

    render_html(
        f"""
        <div class="sb-brand">
            <div class="sb-logo">
                {icon(IC_TAG, size=30, color="#F5C542", stroke=1.9)}
            </div>
            <div class="sb-title">FMCG Label<br>Compliance</div>
        </div>

        <div class="sb-subtitle">
            Automated food-label<br>regulatory audit
        </div>

        <div class="sb-divider"></div>

        <div class="sb-section">Compliance Areas</div>

        <div class="sb-nav">{nav_html}</div>
        """
    )

    if st.session_state.analysis_mode is not None:

        render_html('<div class="sb-divider"></div>')

        if st.button("Change analysis method", key="reset_mode"):

            st.session_state.analysis_mode = None
            st.rerun()

    render_html(
        """
        <div class="sb-footer">
            Smart India Hackathon<br>Prototype
            <br><br>
            Version 1.0.0
        </div>
        """
    )


# ============================================================
# HERO
# ============================================================

render_html(
    f"""
    <div class="hero">

        <div class="hero-blob blob-a"></div>
        <div class="hero-blob blob-b"></div>
        <div class="hero-blob blob-c"></div>

        <div class="hero-inner">

            <div class="hero-eyebrow">
                Regulatory Technology &nbsp;•&nbsp; FSSAI Standards
            </div>

            <h1 class="hero-title">FMCG Label Compliance</h1>

            <div class="hero-sub">
                Automated food-label compliance analysis powered by OCR,
                rule engine, and FSSAI regulatory standards
            </div>

            <div class="hero-badges">

                <span class="badge">
                    {icon(IC_BRAIN, size=19)} AI + OCR
                </span>

                <span class="badge">
                    {icon(IC_CLIPBOARD, size=19)} Rule-Based
                </span>

                <span class="badge">
                    <span style="font-size:1.05rem;line-height:1;">🇮🇳</span> FSSAI
                </span>

            </div>

        </div>

    </div>
    """
)


# ============================================================
# OVERVIEW + WORKFLOW
# ============================================================

render_html(
    """
    <div class="sec-title">Overview</div>
    <div class="sec-sub">How the Audit Works</div>
    """
)


WORKFLOW = [
    (
        "1",
        IC_UPLOAD_CLOUD,
        "Upload",
        "Upload front and back images of the product packaging",
    ),
    (
        "2",
        IC_SCAN,
        "Extract",
        "OCR extracts text from images and identifies key label information",
    ),
    (
        "3",
        IC_SCALE,
        "Validate",
        "Extracted information is validated against FSSAI rules and standards",
    ),
    (
        "4",
        IC_BARS,
        "Report",
        "Comprehensive compliance report with findings and recommendations",
    ),
]


flow_html = '<div class="flow">'

for index, item in enumerate(WORKFLOW):

    step, glyph, title, text = item

    flow_html += (
        f'<div class="flow-card">'
        f'<div class="flow-step">{step}</div>'
        f'<div class="flow-icon">'
        f'{icon(glyph, size=34, color="#FFFFFF", stroke=1.9, cls="ico ico-flow")}'
        f'</div>'
        f'<div class="flow-title">{title}</div>'
        f'<div class="flow-text">{text}</div>'
        f'</div>'
    )

    if index < len(WORKFLOW) - 1:

        flow_html += (
            f'<div class="flow-arrow">'
            f'{icon(IC_ARROW, size=22, color="#4B4A5F", stroke=1.7)}'
            f'</div>'
        )

flow_html += '</div>'

render_html(flow_html)


# ============================================================
# STEP 1 — CHOOSE AN ANALYSIS METHOD
# ============================================================

if st.session_state.analysis_mode is None:

    render_html(
        """
        <div class="panel" style="padding-bottom:26px;">
            <div class="panel-title">Step 1 — Choose an Analysis Method</div>
        </div>
        """
    )

    # Streamlit >= 1.39 supports keyed containers, which lets the whole card
    # act as a single click target (an invisible button overlaid on the card).
    # On older versions we fall back to a visible button under the card.
    CONTAINER_KEYS = "key" in inspect.signature(st.container).parameters


    def method_card(container_key, card_icon, title, text, aria_label):
        """Render a clickable analysis-method card. Returns True when clicked."""

        card_html = f"""
            <div class="method">
                <div class="method-icon">
                    {icon(card_icon, size=36, stroke=1.7)}
                </div>
                <div>
                    <div class="method-title">{title}</div>
                    <div class="method-text">{text}</div>
                </div>
            </div>
        """

        if CONTAINER_KEYS:

            with st.container(key=container_key):

                render_html(card_html)

                return st.button(
                    aria_label,
                    key=f"choose_{container_key}",
                    use_container_width=True,
                )

        render_html(card_html)

        return st.button(
            aria_label,
            key=f"choose_{container_key}",
            use_container_width=True,
        )


    method_left, method_right = st.columns(2, gap="large")


    with method_left:

        if method_card(
            "method_upload",
            IC_IMAGE,
            "Upload Packaging Images",
            "Upload clear images of the product front and back "
            "packaging for comprehensive OCR analysis",
            "Upload packaging images",
        ):

            st.session_state.analysis_mode = UPLOAD_MODE
            st.rerun()


    with method_right:

        if method_card(
            "method_demo",
            IC_MONITOR,
            "Demo Mode",
            "Run analysis on sample data to see how the "
            "compliance check works",
            "Run demo mode",
        ):

            st.session_state.analysis_mode = DEMO_MODE
            st.rerun()


    render_html(
        f"""
        <div class="helper">
            {icon(IC_INFO, size=18, color="#8B8AA0", stroke=1.7)}
            Choose an option above to get started with the compliance analysis
        </div>
        """
    )

    st.stop()


mode = st.session_state.analysis_mode


# ============================================================
# UPLOAD MODE
# ============================================================

if mode == UPLOAD_MODE:

    render_html(
        """
        <div class="sec-title">Step 2 — Upload Packaging Images</div>
        <div class="sec-sub">
            Provide the front and back of the product packaging.
        </div>
        """
    )

    front_col, back_col = st.columns(2, gap="large")


    # --------------------------------------------------------
    # FRONT IMAGE
    # --------------------------------------------------------

    with front_col:

        render_html(
            f"""
            <div class="info-card">
                <div style="display:flex;align-items:center;gap:0.7rem;">
                    {icon(IC_IMAGE, size=22)}
                    <div>
                        <div class="value-lg" style="font-size:1.05rem;margin:0;">
                            Front of Package
                        </div>
                        <div style="color:{MUTED};font-size:0.86rem;">
                            Product name and front-of-pack claims
                        </div>
                    </div>
                </div>
            </div>
            """
        )

        front_file = st.file_uploader(
            "Upload FRONT image",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            key="front_image"
        )


    # --------------------------------------------------------
    # BACK IMAGE
    # --------------------------------------------------------

    with back_col:

        render_html(
            f"""
            <div class="info-card">
                <div style="display:flex;align-items:center;gap:0.7rem;">
                    {icon(IC_MANDATORY, size=22)}
                    <div>
                        <div class="value-lg" style="font-size:1.05rem;margin:0;">
                            Back of Package
                        </div>
                        <div style="color:{MUTED};font-size:0.86rem;">
                            Ingredients and nutritional information
                        </div>
                    </div>
                </div>
            </div>
            """
        )

        back_file = st.file_uploader(
            "Upload BACK image",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            key="back_image"
        )


    # --------------------------------------------------------
    # REQUIRE AT LEAST ONE IMAGE
    # --------------------------------------------------------

    if (
        front_file is None
        and back_file is None
    ):

        render_html(
            """
            <div class="info-card">
                <div style="display:flex;align-items:center;gap:0.7rem;">
                    {icon(IC_INFO, size=22)}
                    <div>
                        <div class="value-lg" style="font-size:1.05rem;margin:0;">
                            Please upload an image
                        </div>
                        <div style="color:{MUTED};font-size:0.86rem;">
                            Upload a front image, back image, or both to begin the audit.
                        </div>
                    </div>
                </div>
            </div>
            """
        )

        st.stop()


    # --------------------------------------------------------
    # LAZY OCR IMPORT
    # --------------------------------------------------------

    try:

        from ocr_engine import extract_text

    except Exception as error:

        st.error(
            "OCR engine could not be loaded."
        )

        st.code(
            str(error)
        )

        st.stop()


    # --------------------------------------------------------
    # FRONT OCR
    # --------------------------------------------------------

    front_data = ""

    if front_file is not None:

        with st.spinner(
            "Processing front package image..."
        ):

            try:

                front_data, _ = extract_text(
                    front_file.getvalue()
                )

            except Exception as error:

                st.error(
                    f"Front image processing failed: {error}"
                )

                st.stop()


    # --------------------------------------------------------
    # BACK OCR
    # --------------------------------------------------------

    back_data = ""

    if back_file is not None:

        with st.spinner(
            "Processing back package image..."
        ):

            try:

                back_data, _ = extract_text(
                    back_file.getvalue()
                )

            except Exception as error:

                st.error(
                    f"Back image processing failed: {error}"
                )

                st.stop()


    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    with st.spinner(
        "Parsing extracted label information..."
    ):

        try:

            front_product = parse_product(
                front_data
            )

            back_product = parse_product(
                back_data
            )

        except Exception as error:

            st.error(
                f"Label parsing failed: {error}"
            )

            st.stop()


    # --------------------------------------------------------
    # CLAIMS
    # --------------------------------------------------------

    front_claims = (
        front_product.get(
            "claims",
            []
        )
        or []
    )

    back_claims = (
        back_product.get(
            "claims",
            []
        )
        or []
    )

    combined_claims = list(
        dict.fromkeys(
            front_claims
            + back_claims
        )
    )


    # --------------------------------------------------------
    # INGREDIENTS
    # --------------------------------------------------------

    front_ingredients = (
        front_product.get(
            "ingredients",
            []
        )
        or []
    )

    back_ingredients = (
        back_product.get(
            "ingredients",
            []
        )
        or []
    )

    combined_ingredients = list(
        dict.fromkeys(
            front_ingredients
            + back_ingredients
        )
    )


    # --------------------------------------------------------
    # NUTRITION
    #
    # Keep the exact names expected by rules.json.
    # --------------------------------------------------------

    front_nutrition = (
        front_product.get(
            "nutrition",
            {}
        )
        or {}
    )

    back_nutrition = (
        back_product.get(
            "nutrition",
            {}
        )
        or {}
    )


    def get_first_value(key):

        back_value = back_nutrition.get(
            key
        )

        if back_value is not None:

            return back_value

        return front_nutrition.get(
            key
        )


    combined_nutrition = {}


    nutrition_keys = [

        "calories",

        "total_sugars_g",

        "added_sugars_g",

        "sodium_mg",

        "protein_g",

        "total_fat_g",

        "trans_fat_g",

        "saturated_fat_g",

        "dietary_fiber_g",

        "gi"
    ]


    for key in nutrition_keys:

        value = get_first_value(
            key
        )

        if value is not None:

            combined_nutrition[
                key
            ] = value


    # --------------------------------------------------------
    # DECLARED BASIS
    # --------------------------------------------------------

    declared_basis = (

        back_product.get(
            "declared_basis"
        )

        if back_product.get(
            "declared_basis"
        ) is not None

        else front_product.get(
            "declared_basis"
        )
    )


    # --------------------------------------------------------
    # SERVING SIZE
    # --------------------------------------------------------

    serving_size_g = (

        back_product.get(
            "serving_size_g"
        )

        if back_product.get(
            "serving_size_g"
        ) is not None

        else front_product.get(
            "serving_size_g"
        )
    )


    # --------------------------------------------------------
    # PRODUCT DATA
    # --------------------------------------------------------

    product_data = {

        "product_name":
            "Live Scanned Product",

        "category":
            "Uncategorized",

        "claims":
            combined_claims,

        "ingredients":
            combined_ingredients,

        "nutrition":
            combined_nutrition,

        "declared_basis":
            declared_basis,

        "serving_size_g":
            serving_size_g,

        "front_uploaded":
            front_file is not None,

        "back_uploaded":
            back_file is not None,

        "front_ocr_text":
            front_data,

        "back_ocr_text":
            back_data
    }


    st.success(
        "OCR extraction and parsing completed."
    )


# ============================================================
# DEMO MODE
# ============================================================

else:

    render_html(
        """
        <div class="sec-title">Step 2 — Select a Demo Product</div>
        <div class="sec-sub">
            Run the audit against a prepared demonstration case.
        </div>
        """
    )

    selected_key = st.selectbox(

        "Choose Product Case:",

        list(
            PRESET_SAMPLES.keys()
        )
    )


    product_data = dict(
        PRESET_SAMPLES[
            selected_key
        ]
    )


# ============================================================
# IMAGE COVERAGE
# ============================================================

render_html(
    """
    <div id="mandatory-section" class="section-anchor sec-title" style="margin-top:1.6rem;">Image Coverage</div>
    <div class="sec-sub">Which sides of the packaging were supplied.</div>
    """
)


coverage1, coverage2 = st.columns(2)


with coverage1:

    if product_data.get(
        "front_uploaded",
        False
    ):

        st.success(
            "Front Image: Supplied"
        )

    else:

        st.warning(
            "Front Image: Not supplied"
        )


with coverage2:

    if product_data.get(
        "back_uploaded",
        False
    ):

        st.success(
            "Back Image: Supplied"
        )

    else:

        st.warning(
            "Back Image: Not supplied"
        )


st.divider()


# ============================================================
# MAIN DASHBOARD
# ============================================================

left_col, right_col = st.columns(
    [1, 1],
    gap="large"
)


# ============================================================
# EXTRACTED INFORMATION
# ============================================================

with left_col:

    render_html(
        """
        <div class="sec-title">Extracted Label Information</div>
        <div class="sec-sub">
            Fields recovered from the packaging.
        </div>
        """
    )


    product_name = html.escape(
        str(
            product_data.get(
                "product_name",
                "Unknown Product"
            )
        )
    )


    render_html(
        f"""
        <div class="info-card">
            <div class="kicker">Product</div>
            <div class="value-lg">{product_name}</div>
        </div>
        """
    )


    # --------------------------------------------------------
    # CLAIMS
    # --------------------------------------------------------

    render_html(
        '<div id="claims-section" class="section-anchor sec-title" style="font-size:1.05rem;margin-top:0.6rem;">'
        'Declared Front-of-Pack Claims</div>'
    )


    claims = (
        product_data.get(
            "claims",
            []
        )
        or []
    )


    if claims:

        claim_html = ""


        for claim in claims:

            safe_claim = html.escape(
                str(claim)
            )

            claim_html += (
                '<span class="claim-pill">'
                f'{safe_claim}'
                '</span>'
            )


        render_html(
            claim_html
        )

    else:

        st.info(
            "No auditable claims were detected."
        )


    # --------------------------------------------------------
    # INGREDIENTS
    # --------------------------------------------------------

    render_html(
        '<div id="ingredients-section" class="section-anchor sec-title" style="font-size:1.05rem;margin-top:1rem;">'
        'Ingredient Extraction</div>'
    )


    ingredients = (
        product_data.get(
            "ingredients",
            []
        )
        or []
    )


    if ingredients:

        st.success(
            "Ingredient section detected — "
            f"{len(ingredients)} extracted entries."
        )


        with st.expander(
            "View ingredients"
        ):

            for ingredient in ingredients:

                st.write(
                    f"• {ingredient}"
                )

    else:

        st.warning(
            "No ingredients could be extracted."
        )


    # --------------------------------------------------------
    # NUTRITION
    # --------------------------------------------------------

    render_html(
        '<div id="nutrition-section" class="section-anchor sec-title" style="font-size:1.05rem;margin-top:1rem;">'
        'Declared Nutritional Values</div>'
    )


    nutrition = (
        product_data.get(
            "nutrition",
            {}
        )
        or {}
    )


    if nutrition:

        st.json(
            nutrition
        )

    else:

        st.info(
            "No nutritional values were extracted."
        )


# ============================================================
# COMPLIANCE RESULTS
# ============================================================

with right_col:

    render_html(
        """
        <div id="regulatory-section" class="section-anchor sec-title">Regulatory Screening</div>
        <div class="sec-sub">
            Rule-engine findings with evidence and legal references.
        </div>
        """
    )


    try:

        results = run_compliance_checks(

            product_data,

            rules_path=str(
                RULES_PATH
            )
        )

    except Exception as error:

        st.error(
            f"Compliance screening failed: {error}"
        )

        st.stop()


    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    passed_count = sum(

        1

        for result in results

        if result.get(
            "status"
        ) == "PASS"
    )


    flagged_count = sum(

        1

        for result in results

        if result.get(
            "status"
        ) == "FLAGGED"
    )


    review_count = sum(

        1

        for result in results

        if result.get(
            "status"
        ) == "REVIEW"
    )


    # --------------------------------------------------------
    # OVERALL RESULT
    # --------------------------------------------------------

    if flagged_count > 0:

        st.error(
            "OVERALL RESULT: POTENTIAL VIOLATION"
        )

    elif review_count > 0:

        st.warning(
            "OVERALL RESULT: REQUIRES REVIEW"
        )

    else:

        st.success(
            "OVERALL RESULT: PASSED CURRENT AUDITS"
        )


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    metric1, metric2, metric3 = st.columns(
        3
    )


    with metric1:

        st.metric(
            "Passed",
            passed_count
        )


    with metric2:

        st.metric(
            "Flagged",
            flagged_count
        )


    with metric3:

        st.metric(
            "Review",
            review_count
        )


    st.divider()


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    if not results:

        st.info(
            "No compliance rules were returned."
        )


    for result in results:

        status = result.get(
            "status",
            "REVIEW"
        )


        claim = html.escape(
            str(
                result.get(
                    "claim",
                    "Unnamed Rule"
                )
            )
        )


        rule_id = html.escape(
            str(
                result.get(
                    "rule_id",
                    "N/A"
                )
            )
        )


        evidence = html.escape(
            str(
                result.get(
                    "evidence",
                    "No evidence provided."
                )
            )
        )


        message = html.escape(
            str(
                result.get(
                    "message",
                    "No finding provided."
                )
            )
        )


        regulation = html.escape(
            str(
                result.get(
                    "regulation",
                    "No regulatory reference provided."
                )
            )
        )


        # ----------------------------------------------------
        # STATUS DESIGN
        # ----------------------------------------------------

        if status == "FLAGGED":

            css_class = "flagged"

            label = "POTENTIAL NON-COMPLIANCE"


        elif status == "REVIEW":

            css_class = "review"

            label = "REQUIRES REVIEW"


        else:

            css_class = "pass"

            label = "COMPLIANT"


        # ----------------------------------------------------
        # RESULT CARD
        # ----------------------------------------------------

        render_html(
            f"""
            <div class="result {css_class}">

                <div class="result-head">
                    {label}: {claim}
                </div>

                <div class="result-row">
                    <b>Rule ID:</b> <code>{rule_id}</code>
                </div>

                <div class="result-row">
                    <b>Evidence:</b> {evidence}
                </div>

                <div class="result-row">
                    <b>Finding:</b> {message}
                </div>

                <div class="result-ref">
                    <b>Legal Reference:</b> {regulation}
                </div>

            </div>
            """
        )


# ============================================================
# REGULATORY LEGAL SYNTHESIS (RAG)
# ============================================================

st.divider()

render_html(
    """
    <div class="sec-title">Regulatory Legal Synthesis (RAG)</div>
    <div class="sec-sub">
        Generates source-grounded legal justifications for all audits using ChromaDB + local LLM.
    </div>
    """
)

if results:
    for result in results:
        status = result.get("status", "REVIEW")
        claim_name = result.get('claim', 'General Compliance').upper()
        
        status_prefix = "🔴 VIOLATION" if status == "FLAGGED" else ("🟡 REVIEW ADVISORY" if status == "REVIEW" else "🟢 COMPLIANCE AFFIRMATION")
        
        with st.expander(f"{status_prefix}: {claim_name}", expanded=(status == "FLAGGED")):
            with st.spinner(f"Querying FSSAI database and synthesizing report for {result.get('rule_id', 'Unknown')}..."):
                try:
                    # Make a request to the FastAPI endpoint
                    resp = requests.post(
                        f"{API_BASE_URL}/api/v1/rag/justify",
                        json=result,
                        timeout=30
                    )
                    resp.raise_for_status()
                    rag_data = resp.json()
                    
                    justification = rag_data.get("justification", "No justification generated.")
                    retrieved_docs = rag_data.get("retrieved_docs", [])
                    
                    st.markdown(f"**Auditor Analysis:**\n\n{justification}")
                    
                    if retrieved_docs:
                        st.divider()
                        st.caption("📚 **Retrieved Legal Context (ChromaDB):**")
                        for doc in retrieved_docs:
                            st.caption(f"- {doc['clause']}: {doc['text']}")
                            
                except Exception as e:
                    st.error(f"Failed to connect to Legal Synthesis Engine: {e}")
                    st.info("Make sure the FastAPI backend is running on port 8000.")
else:
    st.info("No auditable items evaluated.")


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="app-footer">

        FMCG Label Compliance ·
        FSSAI Regulatory Audit Prototype ·
        Smart India Hackathon · Version 1.0.0

    </div>
    """
)

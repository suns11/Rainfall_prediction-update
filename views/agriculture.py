import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from datetime import date


# ============================================================
# AUTO RAINFALL PREDICTION SERVICES
# Reuse the exact prediction engine from the Rain Prediction page.
# ============================================================

from services.data_loader import get_station_table

from services.weather_api import build_on_demand_history

from views.prediction import (
    load_weather_values,
    create_prediction_features,
    condition,
    estimate_rain_probability
)


# ============================================================
# VOICE SERVICE
# ============================================================

from services.voice import (
    play_welcome,
    selection_voice as voice_selection,
    section_voice,
    speak_sequence,
    clean_voice_text,
    agriculture_result_voice,
    agriculture_recommendation_voice,
    growth_stage_auto_voice,
    render_voice_player,
    process_voice_queue,
    reset_voice_hash,
    is_voice_enabled,
    set_voice_enabled
)


# ============================================================
# VOICE INPUT (STT)
# ============================================================

from services.voice_input import (
    prepare_voice_input,
    voice_input_widget
)


# ============================================================
# AGRICULTURE SERVICES
# ============================================================

from services.agriculture import (
    SOIL_TYPES,
    WATER_DEPTH_OPTIONS,
    STAGE_LABELS,
    STAGE_FROM_LABEL,
    get_crop_options,
    get_season_options,
    get_crop_reference,
    determine_growth_stage,
    get_kc,
    convert_area_to_m2,
    convert_water_depth_to_mm,
    calculate_existing_water_volume,
    calculate_irrigation
)


# ============================================================
# WELCOME VOICE
# ============================================================

AGRICULTURE_WELCOME_TEXT = (
    "আসসালামু আলাইকুম। "
    "স্মার্ট কৃষি পরামর্শ সিস্টেমে স্বাগতম। "
    "ফসলের তথ্য দিন। "
    "প্রয়োজনীয় সেচ ও কৃষি পরামর্শ পান।"
)


def start_agriculture_welcome():
    """
    Agriculture page open হলে:
    1. প্রথমে Welcome voice
    2. Welcome শেষ হলে "স্থান ও তারিখ নির্বাচন করুন"

    অন্য কোনো input-এর voice page load-এর সময় বাজবে না।
    """

    if st.session_state.get(
        "agriculture_voice_started",
        False
    ):
        return

    st.session_state[
        "agriculture_voice_started"
    ] = True

    # IMPORTANT:
    # Welcome এবং first instruction একই sequence-এর মধ্যে থাকবে।
    # তাই প্রথমে Welcome শেষ হবে, তারপর instruction বাজবে।
    #
    # NOTE: page-এর প্রথম section এখন "স্থান ও তারিখ", তাই welcome-এর
    # পরের instruction ও সেটাই বলে।

    speak_sequence(
        [
            AGRICULTURE_WELCOME_TEXT,
            "স্থান ও তারিখ নির্বাচন করুন"
        ],
        delay=0.10
    )


# ============================================================
# VOICE ON / OFF TOGGLE (PAGE TOP)
# ============================================================

def agriculture_voice_toggle():
    """
    Page-এর একদম উপরে একটি single ON/OFF বাটন।

    ON:  page-এর সব voice (welcome, section, input confirmation,
         result, recommendation) স্বাভাবিকভাবে বাজবে।
    OFF: কোনো voice generate বা play হবে না।

    NOTE:
    slider/toggle-এ key থাকলে Streamlit widget-এর নিজস্ব session
    value ব্যবহার করে এবং value= সম্পূর্ণ উপেক্ষা করে (এই ফাইলে
    irrigation efficiency slider-এও একই সমস্যা আগে হয়েছিল)। তাই
    widget তৈরি হওয়ার আগেই session_state-এ default বসানো হচ্ছে,
    value= প্যারামিটার ব্যবহার করা হচ্ছে না।
    """

    if "agriculture_voice_toggle" not in st.session_state:

        st.session_state[
            "agriculture_voice_toggle"
        ] = is_voice_enabled()

    vcol1, vcol2 = st.columns([5, 2])

    with vcol2:

        voice_on = st.toggle(
            "🔊 ভয়েস (Voice)",
            key="agriculture_voice_toggle"
        )

    set_voice_enabled(voice_on)


# ============================================================
# PAGE STYLES  (BOX / CARD UI)
# ============================================================
#
# IMPORTANT:
# Streamlit প্রতিটি rerun-এ পুরো script আবার চালায় এবং
# আগের DOM মুছে ফেলে। তাই এই CSS প্রতিবার inject করতে হবে।
# session_state দিয়ে "একবার only" guard দিলে প্রথম run-এর পর
# box style হারিয়ে যাবে।
# ============================================================

def inject_agriculture_styles():

    st.markdown(
        """
        <style>

        /* ============================================================
           IMPORTANT SCOPING NOTE

           সব radio rule শুধুমাত্র main content area-তে প্রয়োগ হবে
           ( section[data-testid="stMain"] )।

           আগে scope ছাড়া লেখা ছিল বলে sidebar navigation-এর radio-ও
           সাদা box হয়ে যেত এবং সাদা লেখা সাদা background-এ মিশে
           অদৃশ্য হয়ে যেত।
           ============================================================ */


        /* ---------- RADIO OPTION → BOX (MAIN AREA ONLY) ---------- */

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 6px;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label {
            border: 2px solid #d5dee7;
            border-radius: 12px;
            padding: 14px 16px;
            background: #ffffff;
            width: 100%;
            cursor: pointer;
            transition: border-color .15s ease,
                        background-color .15s ease;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            border-color: #0e9f6e;
            background: #f4fbf8;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            border-color: #0e9f6e;
            background: #e8f9f1;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:focus-within {
            outline: 2px solid #0e9f6e;
            outline-offset: 2px;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #102a43 !important;
            margin: 0 !important;
        }

        section[data-testid="stMain"]
        div[data-testid="stRadio"] > label p {
            font-size: 17px !important;
            font-weight: 700 !important;
        }


        /* ============================================================
           SIDEBAR NAVIGATION
           ============================================================ */

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1b2a 0%, #102a43 100%);
            border-right: 1px solid rgba(255,255,255,.06);
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            color: #e6edf3 !important;
        }

        section[data-testid="stSidebar"] h1 {
            font-size: 20px !important;
            font-weight: 700 !important;
            letter-spacing: .2px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255,255,255,.08);
        }

        /* Nav list */
        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        /* Nav item → pill */
        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label {
            background: transparent;
            border: 1px solid transparent;
            border-left: 3px solid transparent;
            border-radius: 8px;
            padding: 10px 12px;
            width: 100%;
            cursor: pointer;
            transition: background-color .15s ease,
                        border-color .15s ease;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            background: rgba(255,255,255,.06);
        }

        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            background: rgba(14,159,110,.16);
            border-left-color: #0e9f6e;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            color: #cdd9e5 !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* Nav-এ radio dot লুকানো — pill navigation-এ dot দরকার নেই */
        section[data-testid="stSidebar"]
        div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,.08);
        }


        /* ============================================================
           MAIN AREA WIDGETS
           ============================================================ */

        section[data-testid="stMain"] div[data-testid="stNumberInput"] label p,
        section[data-testid="stMain"] div[data-testid="stSelectbox"] label p,
        section[data-testid="stMain"] div[data-testid="stDateInput"] label p,
        section[data-testid="stMain"] div[data-testid="stTextInput"] label p,
        section[data-testid="stMain"] div[data-testid="stSlider"] label p {
            font-size: 15px !important;
            font-weight: 600 !important;
        }

        /* Placeholder text একটু নরম রঙে */
        section[data-testid="stMain"] input::placeholder {
            color: #8a9aa8 !important;
            opacity: 1 !important;
        }

        /* ---------- FIELD CARD (st.container(border=True)) ---------- */

        section[data-testid="stMain"]
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px !important;
            background: #ffffff;
        }

        /* ---------- SECTION TITLE ---------- */

        .section-title {
            font-size: 20px;
            font-weight: 700;
            border-left: 5px solid #0e9f6e;
            padding-left: 12px;
            margin: 22px 0 12px 0;
        }

        /* ---------- RESULT CARD ---------- */

        .result-card {
            border-radius: 16px;
            padding: 20px 22px;
            background: linear-gradient(135deg, #0e9f6e 0%, #0b7f59 100%);
            color: #ffffff;
            margin: 6px 0 14px 0;
        }

        .result-card h2 {
            color: #ffffff;
            margin: 0 0 4px 0;
            font-size: 26px;
        }

        .result-card h3 {
            color: rgba(255,255,255,.85);
            margin: 0;
            font-size: 16px;
            font-weight: 500;
        }

        /* ---------- HEADER CARD ---------- */

        .agri-card {
            border-radius: 14px;
            padding: 16px 18px;
            background: #eef6f2;
            border: 1px solid #cfe6db;
            margin-bottom: 8px;
        }

        .agri-card h3 {
            margin: 0 0 6px 0;
            font-size: 18px;
        }

        .agri-card p {
            margin: 0;
            font-size: 15px;
            line-height: 1.7;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# BANGLA NUMBER
# ============================================================

def bn_num(
    value,
    decimals=2,
    comma=False
):

    if value is None:

        return "N/A"

    try:

        if comma:

            text = f"{float(value):,.{decimals}f}"

        else:

            text = f"{float(value):.{decimals}f}"

        return text.translate(
            str.maketrans(
                "0123456789",
                "০১২৩৪৫৬৭৮৯"
            )
        )

    except Exception:

        return "N/A"


# ============================================================
# DATE TEXT
# ============================================================

BANGLA_MONTHS = {
    1: "জানুয়ারি",
    2: "ফেব্রুয়ারি",
    3: "মার্চ",
    4: "এপ্রিল",
    5: "মে",
    6: "জুন",
    7: "জুলাই",
    8: "আগস্ট",
    9: "সেপ্টেম্বর",
    10: "অক্টোবর",
    11: "নভেম্বর",
    12: "ডিসেম্বর",
}


def date_text(value):

    if value is None:

        return "N/A"

    try:
        return f"{value.day} {BANGLA_MONTHS[value.month]} {value.year}"

    except Exception:

        return str(value)


def voice_date_text(value):
    """Return a date in Bangla so clean_voice_text() does not remove the month."""
    if value is None:
        return ""

    try:
        day = bn_num(value.day, 0)
        year = bn_num(value.year, 0)
        month = BANGLA_MONTHS.get(value.month, "")
        return f"{day} {month} {year}"

    except Exception:

        return str(value)


# ============================================================
# SECTION TITLE
# ============================================================

def _voice_input_field(
    key,
    prompt,
    value_type="text",
    options=None,
    minimum=None,
    maximum=None
):
    applied = voice_input_widget(
        key=key,
        prompt=prompt,
        value_type=value_type,
        options=options,
        minimum=minimum,
        maximum=maximum
    )

    # A voice-entered value follows the exact same existing
    # confirmation -> next-instruction flow as a normal widget change.
    if applied:
        input_voice_callback(
            key,
            prompt,
            None
        )

    return applied


def section_title(
    bangla,
    english
):

    st.markdown(
        f"""
        <div class='section-title'>
            {bangla}
            ({english})
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# SECTION VOICE STATE
# ============================================================
#
# This controls section-level voice.
#
# Example:
#
# Crop section:
# "ফসল নির্বাচন করুন"
#
# Season section:
# "মৌসুম নির্বাচন করুন"
#
# A section voice is spoken only once for the current
# Agriculture page state.
# ============================================================

def agriculture_section_voice(
    key,
    text
):

    state_key = (
        f"agriculture_section_voice_{key}"
    )

    # --------------------------------------------------------
    # Already spoken
    # --------------------------------------------------------

    if st.session_state.get(
        state_key,
        False
    ):

        return


    # --------------------------------------------------------
    # Mark BEFORE starting voice
    #
    # This is important because Streamlit can rerun quickly.
    # --------------------------------------------------------

    st.session_state[
        state_key
    ] = True


    section_voice(
        text,
        key=key,
        delay=0.10
    )


# ============================================================
# VOICE STATE HELPER
# ============================================================

def selection_voice(
    key,
    value,
    text
):

    state_key = (
        f"agriculture_voice_{key}"
    )

    old_value = st.session_state.get(
        state_key
    )


    # --------------------------------------------------------
    # First render
    #
    # Do NOT speak default value.
    # --------------------------------------------------------

    if old_value is None:

        st.session_state[
            state_key
        ] = value

        return


    # --------------------------------------------------------
    # Same value
    # --------------------------------------------------------

    if old_value == value:

        return


    # --------------------------------------------------------
    # Value changed
    # --------------------------------------------------------

    st.session_state[
        state_key
    ] = value


    voice_selection(
        text,
        key=key,
        delay=0.12
    )


# ============================================================
# INTERACTION VOICE CALLBACK
# ============================================================
#
# Native Streamlit widgets do not expose a server-side "opened"
# event. They do expose an on_change event. We therefore make
# every input widget voice-aware at the moment the user actually
# changes/selects its value.
#
# First real selection:
#   instruction -> selected value
#
# Later changes:
#   selected value only
#
# This keeps the voice tied to the widget interaction instead of
# the page rerun.
# ============================================================

def _voice_value_text(key, value):
    """Return a short Bangla confirmation for one widget value."""

    if value is None:
        return ""

    if key in {
        "agriculture_land_area",
        "agriculture_prediction_fallback_rain",
        "agriculture_prediction_fallback_et0",
        "agriculture_manual_rain",
        "agriculture_manual_et0",
        "agriculture_custom_water_depth",
        "agriculture_manual_crop_water_need",
        "agriculture_irrigation_efficiency",
    }:

        try:

            number = float(value)

            if number.is_integer():

                number_text = bn_num(
                    number,
                    0
                )

            else:

                number_text = bn_num(
                    number,
                    2
                )

        except Exception:

            number_text = str(value)


        if key == "agriculture_land_area":

            return (
                f"জমির পরিমাণ "
                f"{number_text} দেওয়া হয়েছে"
            )

        if "rain" in key:

            return (
                f"বৃষ্টির পরিমাণ "
                f"{number_text} দেওয়া হয়েছে"
            )

        if "et0" in key:

            return (
                f"রেফারেন্স বাষ্পীভবনের পরিমাণ "
                f"{number_text} দেওয়া হয়েছে"
            )

        if key == "agriculture_custom_water_depth":

            return (
                f"পানির গভীরতা "
                f"{number_text} সেন্টিমিটার দেওয়া হয়েছে"
            )

        if key == "agriculture_manual_crop_water_need":

            return (
                f"ফসলের পানির চাহিদা "
                f"{number_text} দেওয়া হয়েছে"
            )

        if key == "agriculture_irrigation_efficiency":

            return (
                f"সেচ দক্ষতা "
                f"{number_text} শতাংশ নির্বাচন করা হয়েছে"
            )


    if key in {
        "agriculture_calculation_date",
        "agriculture_actual_planting_date",
        "agriculture_prediction_date",
    }:

        value_text = voice_date_text(value)

        if key == "agriculture_calculation_date":

            return (
                f"হিসাবের তারিখ "
                f"{value_text} নির্বাচন করা হয়েছে"
            )

        if key == "agriculture_prediction_date":

            return (
                f"পূর্বাভাসের তারিখ "
                f"{value_text} নির্বাচন করা হয়েছে"
            )

        return (
            f"রোপণ বা বপনের তারিখ "
            f"{value_text} নির্বাচন করা হয়েছে"
        )


    # ----------------------------------------------------------
    # STATION / LOCATION
    # ----------------------------------------------------------
    #
    # dropdown-এর value পুরো display_label
    # ("Station, District (Division)  —  স্টেশন, জেলা (বিভাগ)")।
    # আগে পুরো Bangla অংশ (স্টেশন, জেলা, বিভাগ) বলা হতো — Dhaka-র
    # মতো ক্ষেত্রে Station = District = Division same হওয়ায় একই
    # নাম তিনবার শোনা যেত (যেমন "ঢাকা ঢাকা ঢাকা")। এখন শুধু
    # প্রথম অংশ (Station-এর Bangla নাম) বলা হবে।

    if key == "agriculture_station":

        raw_value = str(value)

        bn_part = raw_value

        if "—" in raw_value:

            bn_part = raw_value.split(
                "—"
            )[-1]

        station_bn = bn_part.split(
            ","
        )[0].strip()

        station_text = clean_voice_text(
            station_bn
        )

        if not station_text:

            return ""

        return (
            f"{station_text} নির্বাচন করা হয়েছে"
        )


    text = clean_voice_text(
        str(value)
    )

    if not text:

        return ""


    if key == "agriculture_weather_source":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_area_unit":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_crop_select":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_season_select":

        return (
            f"{text} মৌসুম নির্বাচন করা হয়েছে"
        )

    if key.startswith(
        "agriculture_growth_stage"
    ):

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_soil_type":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_water_measurement":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_water_requirement_method":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_irrigation_method":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_reference_period":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    if key == "agriculture_out_of_season_stage":

        return (
            f"{text} নির্বাচন করা হয়েছে"
        )

    return (
        f"{text} নির্বাচন করা হয়েছে"
    )


# The page is intentionally treated as a small voice state machine.
# After one input is changed, only that input's confirmation and the
# NEXT relevant instruction are spoken.
VOICE_NEXT_INSTRUCTION = {

    # --------------------------------------------------------
    # WEATHER FLOW
    # --------------------------------------------------------

    # Weather source select করার পর সরাসরি Land Area নয়।
    # Manual rainfall হলে আগে rainfall -> ET0 complete হবে.
    "agriculture_weather_source": "",

    # Manual rainfall input-এর পরে ET0
    "agriculture_manual_rain":
        "রেফারেন্স বাষ্পীভবনের পরিমাণ দিন",

    # Prediction fallback rainfall-এর পরে ET0
    "agriculture_prediction_fallback_rain":
        "রেফারেন্স বাষ্পীভবনের পরিমাণ দিন",

    # ET0 শেষ হলে Land Area
    "agriculture_manual_et0":
        "জমির পরিমাণ দিন",

    "agriculture_prediction_fallback_et0":
        "জমির পরিমাণ দিন",


    # --------------------------------------------------------
    # LAND FLOW
    # --------------------------------------------------------

    "agriculture_land_area":
        "জমির একক নির্বাচন করুন",

    "agriculture_area_unit":
        "ফসল নির্বাচন করুন",


    # --------------------------------------------------------
    # CROP FLOW
    # --------------------------------------------------------

    "agriculture_crop_select":
        "মৌসুম নির্বাচন করুন",

    "agriculture_season_select":
        "হিসাবের তারিখ নির্বাচন করুন",


    # --------------------------------------------------------
    # DATE / GROWTH FLOW
    # --------------------------------------------------------

    "agriculture_calculation_date":
        "রোপণ বা বপনের তারিখ নির্বাচন করুন",

    # Planting date-এর পরে automatic growth stage নিজেই
    # voice announce করবে। তাই এখানে আর কোনো next instruction নেই।
    "agriculture_actual_planting_date":
        "",

    # Growth stage নির্বাচনের পর পরবর্তী ধাপ মাটির ধরন।
    # Automatic announcement-ও শেষে এই একই instruction বলে,
    # তাই কৃষক stage না বদলালেও flow থেমে থাকে না।
    "agriculture_growth_stage":
        "মাটির ধরন নির্বাচন করুন",

    "agriculture_growth_stage_fallback":
        "মাটির ধরন নির্বাচন করুন",

    "agriculture_out_of_season_stage":
        "",

    "agriculture_reference_period":
        "",


    # --------------------------------------------------------
    # SOIL / WATER FLOW
    # --------------------------------------------------------

    "agriculture_soil_type":
        "জমিতে থাকা পানির গভীরতা নির্বাচন করুন",

    "agriculture_water_measurement":
        "ফসলের পানির চাহিদা নির্ধারণের পদ্ধতি নির্বাচন করুন",

    "agriculture_custom_water_depth":
        "ফসলের পানির চাহিদা নির্ধারণের পদ্ধতি নির্বাচন করুন",

    "agriculture_water_requirement_method":
        "সেচ পদ্ধতি নির্বাচন করুন",

    "agriculture_manual_crop_water_need":
        "সেচ পদ্ধতি নির্বাচন করুন",


    # --------------------------------------------------------
    # IRRIGATION FLOW
    # --------------------------------------------------------

    # Irrigation efficiency-এর কোনো voice নেই।
    # Irrigation method select করার পর সরাসরি calculation instruction।
    "agriculture_irrigation_method":
        "স্মার্ট সেচ হিসাব করতে বোতামে চাপ দিন",

    # IMPORTANT:
    # Efficiency selection voice completely disabled.
    "agriculture_irrigation_efficiency":
        "",
}


def input_voice_callback(
    key,
    instruction=None,
    selected_text=None
):
    """
    Streamlit on_change callback.

    Voice flow:
        confirmation -> next relevant instruction

    Special handling:
    1. Weather source:
       শুধু selection confirmation বলবে।
       সরাসরি Land Area বলবে না।

    2. Manual rainfall:
       Rainfall confirmation -> ET0 instruction

    3. ET0:
       ET0 confirmation -> Land Area instruction

    4. Planting date:
       Date confirmation বলবে।
       Automatic Growth Stage আলাদা stage logic থেকে handle হবে।

    5. Growth stage:
       Duplicate next instruction বলবে না।

    6. Irrigation efficiency:
       কোনো voice হবে না।

    7. Crop select:
       কোনো voice এখান থেকে হবে না — পুরো crop confirmation +
       rice/non-rice অনুযায়ী পরবর্তী ধাপ crop_information_section()-এ
       একটি single speak_sequence() call-এ হ্যান্ডেল করা হয়।
    """

    value = st.session_state.get(key)

    if value is None:

        return


    # --------------------------------------------------------
    # IRRIGATION EFFICIENCY
    # --------------------------------------------------------
    # Efficiency-এর কোনো voice একদমই হবে না.
    if key == "agriculture_irrigation_efficiency":

        return


    # --------------------------------------------------------
    # CROP SELECT
    # --------------------------------------------------------
    # ফসল নির্বাচনের voice এখন crop_information_section()-এ একটি
    # combined speak_sequence() হিসেবে হ্যান্ডেল করা হয় (crop
    # confirmation + rice/non-rice অনুযায়ী পরবর্তী ধাপ)। একই
    # rerun-এ দুটো আলাদা speak_sequence() call এসে একে অপরকে
    # overwrite করে ফেলত, তাই generic voice এখানে skip করা হলো।
    if key == "agriculture_crop_select":

        return


    # --------------------------------------------------------
    # STATE KEY
    # --------------------------------------------------------

    state_key = (
        f"agriculture_interaction_voice_{key}"
    )

    previous = st.session_state.get(
        state_key
    )


    # Same value হলে আবার voice নয়
    if previous == value:

        return


    # নতুন value save
    st.session_state[
        state_key
    ] = value


    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    confirmation = (
        selected_text
        or _voice_value_text(
            key,
            value
        )
    )


    # --------------------------------------------------------
    # NEXT INSTRUCTION
    # --------------------------------------------------------

    next_instruction = (
        VOICE_NEXT_INSTRUCTION.get(
            key,
            ""
        )
    )


    sequence = []


    if confirmation:

        sequence.append(
            confirmation
        )


    if next_instruction:

        sequence.append(
            next_instruction
        )


    # --------------------------------------------------------
    # PLAY
    # --------------------------------------------------------

    if sequence:

        speak_sequence(
            sequence,
            delay=0.05
        )


# ============================================================
# AGRICULTURE AUTO RAINFALL PREDICTION
# ============================================================

def auto_predict_agriculture_rainfall(
    df,
    model,
    feature_columns,
    train_medians,
    history_days,
    selected_label,
    target_date
):
    """
    Automatically predict rainfall for the selected Agriculture station/date.

    The prediction engine is the same one used by views.prediction, so
    Agriculture and Rain Prediction use identical feature preparation and
    model logic. The result is stored in st.session_state.rain_prediction,
    which the existing Agriculture calculations already consume.

    NOTE: `selected_label` here is always the plain English
    "Station, District (Division)" key (see agriculture_location_date_section
    below), even though the dropdown the farmer sees also shows a Bangla
    translation next to it.
    """

    meta = get_station_table(df).copy()

    if meta.empty:
        st.error("❌ কোনো station পাওয়া যায়নি।")
        return None

    if selected_label is None or target_date is None:
        return None

    station = meta.loc[
        meta.apply(
            lambda x: (
                f"{x['Station']}, "
                f"{x['District']} "
                f"({x['Division']})"
            ),
            axis=1
        ) == selected_label
    ]

    if station.empty:
        st.error("❌ নির্বাচিত station পাওয়া যায়নি।")
        return None

    station = station.iloc[0]
    target = pd.Timestamp(target_date).normalize()

    weather_key = (
        f"{station['Station_ID']}_"
        f"{target.strftime('%Y%m%d')}"
    )

    # Already predicted for this exact station/date -> reuse it.
    if (
        st.session_state.get("agriculture_prediction_key") == weather_key
        and "rain_prediction" in st.session_state
    ):
        return station

    # Remove the previous Agriculture prediction before calculating the new one.
    st.session_state.pop("rain_prediction", None)

    try:
        with st.spinner("🌦️ Station weather data load হচ্ছে..."):
            weather_values, weather_error = load_weather_values(
                station=station,
                target=target
            )

        station_df = df[
            df["Station_ID"] == station["Station_ID"]
        ].copy()

        base = station_df.median(
            numeric_only=True
        ).to_dict()

        if weather_values is None:
            values = base
            values["Latitude"] = float(station["Latitude"])
            values["Longitude"] = float(station["Longitude"])
            weather_note = (
                "Weather API পাওয়া যায়নি; station-এর CSV median values ব্যবহার করা হয়েছে।"
            )
        else:
            values = dict(weather_values)
            weather_note = (
                "নির্বাচিত তারিখের station weather data ব্যবহার করে automatic prediction করা হয়েছে।"
            )

        numeric_weather_fields = [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_mean",
            "sunshine_duration",
            "daylight_duration",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
            "shortwave_radiation_sum",
            "weather_code",
            "et0_fao_evapotranspiration"
        ]

        for col in numeric_weather_fields:
            value = values.get(col)
            try:
                value = float(value)
            except Exception:
                value = np.nan

            if pd.isna(value):
                value = base.get(col, np.nan)

            try:
                value = float(value)
            except Exception:
                value = 0.0

            values[col] = value

        values["Latitude"] = float(
            values.get("Latitude", station["Latitude"])
        )
        values["Longitude"] = float(
            values.get("Longitude", station["Longitude"])
        )

        with st.spinner("📚 Historical rainfall features তৈরি হচ্ছে..."):
            pred_hist, bridge_note = build_on_demand_history(
                df=df,
                station=station,
                target_date=target,
                history_days=history_days
            )

        with st.spinner("🤖 Rainfall prediction চলছে..."):
            X = create_prediction_features(
                historical_df=pred_hist,
                station_id=station["Station_ID"],
                target_date=target,
                weather_values=values,
                feature_columns=feature_columns,
                train_medians=train_medians
            )

            if X.empty:
                raise ValueError("Prediction features are empty.")

            if len(X.columns) != len(feature_columns):
                raise ValueError(
                    "Feature column count does not match model."
                )

            X = X.replace([np.inf, -np.inf], np.nan)
            nan_count = int(X.isna().sum().sum())

            if nan_count > 0:
                raise ValueError(
                    f"Prediction features contain {nan_count} NaN values."
                )

            prediction_array = np.asarray(
                model.predict(X)
            ).reshape(-1)

            if len(prediction_array) == 0:
                raise ValueError("Model returned no prediction.")

            pred = max(
                float(prediction_array[0]),
                0.0
            )

        weather_code = int(
            round(float(values.get("weather_code", 0)))
        )

        weather_name, message = condition(
            code=weather_code,
            pred=pred
        )

        rain_probability = estimate_rain_probability(pred)

        try:
            et0 = float(
                values.get(
                    "et0_fao_evapotranspiration",
                    4.0
                )
            )
        except Exception:
            et0 = 4.0

        if not np.isfinite(et0):
            et0 = 4.0

        st.session_state.rain_prediction = {
            "prediction": pred,
            "rain_probability": rain_probability,
            "station": station,
            "date": target,
            "weather_values": values,
            "condition": weather_name,
            "message": message,
            "et0": et0,
            "history_note": bridge_note,
            "is_future": target.date() > date.today(),
            "agriculture_auto": True,
            "weather_note": weather_note,
            "weather_error": weather_error
        }

        st.session_state.agriculture_prediction_key = weather_key

        return station

    except Exception as exc:
        st.session_state.pop("rain_prediction", None)
        st.session_state.pop("agriculture_prediction_key", None)

        st.error(
            "❌ Agriculture-এর জন্য automatic rainfall prediction করা যায়নি।"
        )
        st.exception(exc)
        return station


# ============================================================
# LOCATION NAME → BANGLA TRANSLATION
# ============================================================
#
# The station/district/division names in the dataset are in
# English. The dropdown must show the Bangla name next to it too.
# These lookup tables cover the divisions, districts and common
# BMD weather-station names used in Bangladesh.
#
# If a name is not found in the table (e.g. an unusual spelling),
# the ORIGINAL English text is shown instead of crashing — this
# keeps the page fully safe even for unmapped names.
# ============================================================

BN_DIVISIONS = {
    "Dhaka": "ঢাকা",
    "Chattogram": "চট্টগ্রাম",
    "Chittagong": "চট্টগ্রাম",
    "Rajshahi": "রাজশাহী",
    "Khulna": "খুলনা",
    "Barisal": "বরিশাল",
    "Barishal": "বরিশাল",
    "Sylhet": "সিলেট",
    "Rangpur": "রংপুর",
    "Mymensingh": "ময়মনসিংহ",
}

BN_DISTRICTS = {
    "Dhaka": "ঢাকা", "Faridpur": "ফরিদপুর", "Gazipur": "গাজীপুর",
    "Gopalganj": "গোপালগঞ্জ", "Kishoreganj": "কিশোরগঞ্জ",
    "Madaripur": "মাদারীপুর", "Manikganj": "মানিকগঞ্জ",
    "Munshiganj": "মুন্সিগঞ্জ", "Narayanganj": "নারায়ণগঞ্জ",
    "Narsingdi": "নরসিংদী", "Rajbari": "রাজবাড়ী",
    "Shariatpur": "শরীয়তপুর", "Tangail": "টাঙ্গাইল",
    "Bogra": "বগুড়া", "Bogura": "বগুড়া", "Joypurhat": "জয়পুরহাট",
    "Naogaon": "নওগাঁ", "Natore": "নাটোর",
    "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Nawabganj": "চাঁপাইনবাবগঞ্জ",
    "Pabna": "পাবনা", "Rajshahi": "রাজশাহী", "Sirajganj": "সিরাজগঞ্জ",
    "Dinajpur": "দিনাজপুর", "Gaibandha": "গাইবান্ধা",
    "Kurigram": "কুড়িগ্রাম", "Lalmonirhat": "লালমনিরহাট",
    "Nilphamari": "নীলফামারী", "Panchagarh": "পঞ্চগড়",
    "Rangpur": "রংপুর", "Thakurgaon": "ঠাকুরগাঁও",
    "Bagerhat": "বাগেরহাট", "Chuadanga": "চুয়াডাঙ্গা",
    "Jashore": "যশোর", "Jessore": "যশোর", "Jhenaidah": "ঝিনাইদহ",
    "Khulna": "খুলনা", "Kushtia": "কুষ্টিয়া", "Magura": "মাগুরা",
    "Meherpur": "মেহেরপুর", "Narail": "নড়াইল", "Satkhira": "সাতক্ষীরা",
    "Barguna": "বরগুনা", "Barisal": "বরিশাল", "Barishal": "বরিশাল",
    "Bhola": "ভোলা", "Jhalokati": "ঝালকাঠি",
    "Patuakhali": "পটুয়াখালী", "Pirojpur": "পিরোজপুর",
    "Habiganj": "হবিগঞ্জ", "Moulvibazar": "মৌলভীবাজার",
    "Sunamganj": "সুনামগঞ্জ", "Sylhet": "সিলেট",
    "Bandarban": "বান্দরবান", "Brahmanbaria": "ব্রাহ্মণবাড়িয়া",
    "Chandpur": "চাঁদপুর", "Chattogram": "চট্টগ্রাম",
    "Chittagong": "চট্টগ্রাম", "Cumilla": "কুমিল্লা", "Comilla": "কুমিল্লা",
    "Cox's Bazar": "কক্সবাজার", "Coxs Bazar": "কক্সবাজার",
    "Coxsbazar": "কক্সবাজার", "Feni": "ফেনী",
    "Khagrachhari": "খাগড়াছড়ি", "Lakshmipur": "লক্ষ্মীপুর",
    "Noakhali": "নোয়াখালী", "Rangamati": "রাঙ্গামাটি",
    "Jamalpur": "জামালপুর", "Mymensingh": "ময়মনসিংহ",
    "Netrokona": "নেত্রকোণা", "Sherpur": "শেরপুর",
}

BN_STATIONS = {
    "Dhaka": "ঢাকা", "Faridpur": "ফরিদপুর", "Tangail": "টাঙ্গাইল",
    "Mymensingh": "ময়মনসিংহ", "Bogra": "বগুড়া", "Rangpur": "রংপুর",
    "Dinajpur": "দিনাজপুর", "Sylhet": "সিলেট", "Srimangal": "শ্রীমঙ্গল",
    "Rajshahi": "রাজশাহী", "Ishurdi": "ঈশ্বরদী", "Bagerhat": "বাগেরহাট",
    "Chuadanga": "চুয়াডাঙ্গা", "Jessore": "যশোর", "Jashore": "যশোর",
    "Khulna": "খুলনা", "Mongla": "মোংলা", "Satkhira": "সাতক্ষীরা",
    "Barisal": "বরিশাল", "Barishal": "বরিশাল", "Bhola": "ভোলা",
    "Patuakhali": "পটুয়াখালী", "Khepupara": "খেপুপাড়া",
    "Chittagong": "চট্টগ্রাম", "Chattogram": "চট্টগ্রাম",
    "Comilla": "কুমিল্লা", "Cumilla": "কুমিল্লা",
    "Cox's Bazar": "কক্সবাজার", "Coxsbazar": "কক্সবাজার",
    "Feni": "ফেনী", "Hatiya": "হাতিয়া", "Kutubdia": "কুতুবদিয়া",
    "Maijdee Court": "মাইজদী কোর্ট", "Rangamati": "রাঙ্গামাটি",
    "Sandwip": "সন্দ্বীপ", "Sitakunda": "সীতাকুণ্ড", "Teknaf": "টেকনাফ",
    "Chandpur": "চাঁদপুর", "Jamalpur": "জামালপুর",
    "Madaripur": "মাদারীপুর", "Narail": "নড়াইল",
    "Netrokona": "নেত্রকোণা", "Sirajganj": "সিরাজগঞ্জ",
    "Tetulia": "তেঁতুলিয়া", "Panchagarh": "পঞ্চগড়",
    "Gopalganj": "গোপালগঞ্জ",
}


def _bn_lookup(name, table):
    """Look up a Bangla translation; fall back to the original text."""

    if name is None:
        return ""

    key = str(name).strip()

    if key in table:
        return table[key]

    lowered = key.lower()

    for eng, bn in table.items():
        if eng.lower() == lowered:
            return bn

    # No mapping found -> show the original text instead of crashing.
    return key


def build_bn_location_label(station, district, division):
    """Return a Bangla translation of 'Station, District (Division)'."""

    station_bn = _bn_lookup(station, BN_STATIONS)
    district_bn = _bn_lookup(district, BN_DISTRICTS)
    division_bn = _bn_lookup(division, BN_DIVISIONS)

    return f"{station_bn}, {district_bn} ({division_bn})"


# ============================================================
# LOCATION & DATE SECTION
# ============================================================

def agriculture_location_date_section(
    df,
    model,
    feature_columns,
    train_medians,
    history_days
):
    """Select Agriculture location/date and create the rainfall prediction."""

    section_title(
        "স্থান ও তারিখ",
        "Location & Date"
    )

    meta = get_station_table(df).copy()

    if meta.empty:
        st.error("❌ কোনো station পাওয়া যায়নি।")
        return None, None

    meta["label"] = meta.apply(
        lambda x: (
            f"{x['Station']}, "
            f"{x['District']} "
            f"({x['Division']})"
        ),
        axis=1
    )

    # Bangla translation shown alongside the English label, so the
    # farmer sees the location name in Bangla too. The English
    # "label" stays exactly as before internally, so the matching
    # logic in auto_predict_agriculture_rainfall() is unaffected.
    meta["label_bn"] = meta.apply(
        lambda x: build_bn_location_label(
            x["Station"],
            x["District"],
            x["Division"]
        ),
        axis=1
    )

    meta["display_label"] = (
        meta["label"] + "  —  " + meta["label_bn"]
    )

    display_to_label = dict(
        zip(meta["display_label"], meta["label"])
    )

    display_labels = sorted(
        meta["display_label"].tolist()
    )

    with st.container(border=True):
        c1, c2 = st.columns(2)

        with c1:

            prepare_voice_input("agriculture_station")

            selected_display_label = st.selectbox(
                "📍 Location / Station নির্বাচন করুন",
                display_labels,
                index=None,
                key="agriculture_station",
                on_change=input_voice_callback,
                args=(
                    "agriculture_station",
                    "Location / Station নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_station",
                "স্টেশন বা এলাকার নাম বলুন",
                "option",
                display_labels
            )

        with c2:

            prepare_voice_input("agriculture_prediction_date")

            target_date = st.date_input(
                "তারিখ নির্বাচন করুন (Prediction Date)",
                value=None,
                format="YYYY/MM/DD",
                key="agriculture_prediction_date",
                on_change=input_voice_callback,
                args=(
                    "agriculture_prediction_date",
                    "পূর্বাভাসের তারিখ নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_prediction_date",
                "তারিখ বলুন, যেমন ১৫ সেপ্টেম্বর ২০২৬",
                "date"
            )

    selected_label = (
        display_to_label.get(selected_display_label)
        if selected_display_label is not None
        else None
    )

    if selected_label is None or target_date is None:
        st.info(
            "Rainfall prediction-এর জন্য আগে Location এবং Date নির্বাচন করুন।"
        )
        st.session_state.pop("rain_prediction", None)
        st.session_state.pop("agriculture_prediction_key", None)
        return selected_label, target_date

    selected_station = auto_predict_agriculture_rainfall(
        df=df,
        model=model,
        feature_columns=feature_columns,
        train_medians=train_medians,
        history_days=history_days,
        selected_label=selected_label,
        target_date=target_date
    )

    rain_data = st.session_state.get(
        "rain_prediction",
        {}
    )

    if selected_station is not None and rain_data:
        with st.container(border=True):
            st.success(
                f"বৃষ্টির পূর্বাভাস: {bn_num(float(rain_data.get('prediction', 0.0)), 2)} mm"
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Location",
                selected_display_label
            )

            c2.metric(
                "Date",
                date_text(target_date)
            )

            c3.metric(
                "ET0",
                f"{bn_num(float(rain_data.get('et0', 0.0)), 2)} mm/day"
            )

    return selected_label, target_date


# ============================================================
# WEATHER SECTION
# ============================================================

def weather_information_section():

    section_title(
        "আবহাওয়া ও বৃষ্টির তথ্য",
        "Weather & Rainfall Information"
    )

    st.session_state.pop("agriculture_weather_source", None)


    # --------------------------------------------------------
    # RAINFALL SOURCE
    # Auto prediction is default. Manual rainfall is optional.
    # --------------------------------------------------------

    with st.container(border=True):

        manual_selected = st.checkbox(
            "☐ নিজে বৃষ্টির পরিমাণ দিতে চাই",
            key="agriculture_manual_rain_choice"
        )


    if manual_selected:
        weather_source = "MANUAL"
    else:
        weather_source = "AUTO"


    predicted_rain = 0.0
    et0_value = 0.0


    # ========================================================
    # PREDICTION
    # ========================================================

    if weather_source == "AUTO":

        if "rain_prediction" in st.session_state:

            rain_data = (
                st.session_state.rain_prediction
            )


            try:

                predicted_rain = float(
                    rain_data.get(
                        "prediction",
                        0.0
                    )
                )

            except Exception:

                predicted_rain = 0.0


            try:

                et0_value = float(
                    rain_data.get(
                        "et0",
                        4.0
                    )
                )

            except Exception:

                et0_value = 4.0


            with st.container(border=True):

                st.success(
                    f"""
                    বৃষ্টির পূর্বাভাস:
                    {bn_num(predicted_rain, 2)} mm

                    ET0:
                    {bn_num(et0_value, 2)} mm/day
                    """
                )


            # =================================================
            # PREDICTION WEATHER VOICE
            # =================================================
            #
            # Prediction থেকে Rainfall এবং ET0 পাওয়া গেলে
            # কোনো manual input নেওয়া হবে না।
            #
            # Voice flow:
            #
            # Source confirmation
            #       ↓
            # Predicted Rainfall
            #       ↓
            # Predicted ET0
            #       ↓
            # Land Area
            #
            # Signature ব্যবহার করা হয়েছে যাতে Streamlit rerun-এর
            # কারণে একই prediction voice বারবার না বাজে।
            # =================================================

            prediction_voice_signature = (
                round(
                    float(predicted_rain),
                    2
                ),
                round(
                    float(et0_value),
                    2
                )
            )


            if (
                st.session_state.get(
                    "agriculture_prediction_weather_voice_signature"
                )
                != prediction_voice_signature
            ):

                st.session_state[
                    "agriculture_prediction_weather_voice_signature"
                ] = prediction_voice_signature


                # ---------------------------------------------
                # NOTE:
                #
                # "বৃষ্টির পূর্বাভাস ব্যবহার করুন" এখন ডিফল্টভাবে
                # আগে থেকেই নির্বাচিত থাকে (radio index=0), তাই এই
                # sequence কৃষকের কোনো ক্লিক ছাড়াই বেজে যায়।
                #
                # কৃষক চাইলে এর মাঝেই "নিজে বৃষ্টির পরিমাণ দিন"-এ
                # switch করতে পারেন — সেটা করলে radio-র on_change
                # সাথে সাথেই fire হয়ে rerun হবে এবং নতুন confirmation
                # audio (Manual path-এর) পুরনো <audio> element-কে
                # replace করে দেবে, ফলে এই "জমির পরিমাণ দিন" অংশ
                # ব্রাউজারে বাজলেও থেমে/replace হয়ে যাবে। তাই আলাদা
                # server-side wait/re-check লজিক দরকার নেই — শুধু
                # "আপনি চাইলে নিজে পরিমাপ দিতে পারেন" বলার পর কয়েকটি
                # PAUSE_TOKEN ("।") দিয়ে ছোট বিরতির অনুভূতি তৈরি করা
                # হচ্ছে, তারপর পরবর্তী instruction।
                # ---------------------------------------------

                PAUSE_TOKEN = "।"

                speak_sequence(
                    [
                        (
                            f"আজকে আনুমানিক "
                            f"{bn_num(predicted_rain, 2)} "
                            f"মিলিমিটার বৃষ্টি হতে পারে।"
                        ),

                        (
                            f"রেফারেন্স বাষ্পীভবনের পরিমাণ "
                            f"আনুমানিক "
                            f"{bn_num(et0_value, 2)} "
                            f"মিলিমিটার হতে পারে।"
                        ),

                        "আপনি চাইলে নিজে পরিমাপ দিতে পারেন   অথবা পরবর্তী তথ্য",

                        PAUSE_TOKEN,
                        PAUSE_TOKEN,
                        PAUSE_TOKEN,

                        "জমির পরিমাণ দিন"
                    ],
                    delay=0.05
                )


        else:

            with st.container(border=True):

                st.warning(
                    "আগে Rain Prediction করুন অথবা "
                    "নিজে বৃষ্টির পরিমাণ দিন নির্বাচন করুন।"
                )


                c1, c2 = st.columns(2)


                with c1:

                    prepare_voice_input("agriculture_prediction_fallback_rain")

                    predicted_rain = st.number_input(
                        "আজকের বৃষ্টির পরিমাণ "
                        "(Today's Rainfall) mm",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                        key="agriculture_prediction_fallback_rain",
                        on_change=input_voice_callback,
                        args=(
                            "agriculture_prediction_fallback_rain",
                            "আজকের বৃষ্টির পরিমাণ দিন",
                            None
                        )
                    )

                    _voice_input_field(
                        "agriculture_prediction_fallback_rain",
                        "আজকের বৃষ্টির পরিমাণ বলুন",
                        "number",
                        minimum=0.0
                    )


                with c2:

                    prepare_voice_input("agriculture_prediction_fallback_et0")

                    et0_value = st.number_input(
                        "রেফারেন্স বাষ্পীভবন "
                        "(ET0 / Reference Evapotranspiration) mm/day",
                        min_value=0.0,
                        value=4.0,
                        step=0.1,
                        key="agriculture_prediction_fallback_et0",
                        on_change=input_voice_callback,
                        args=(
                            "agriculture_prediction_fallback_et0",
                            "রেফারেন্স বাষ্পীভবনের পরিমাণ দিন",
                            None
                        )
                    )

                    _voice_input_field(
                        "agriculture_prediction_fallback_et0",
                        "রেফারেন্স বাষ্পীভবনের পরিমাণ বলুন",
                        "number",
                        minimum=0.0
                    )


    # ========================================================
    # MANUAL
    # ========================================================

    else:

        with st.container(border=True):

            c1, c2 = st.columns(2)


            with c1:

                prepare_voice_input("agriculture_manual_rain")

                predicted_rain = st.number_input(
                    "আজকের বৃষ্টির পরিমাণ "
                    "(Today's Rainfall) mm",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    key="agriculture_manual_rain",
                    on_change=input_voice_callback,
                    args=(
                        "agriculture_manual_rain",
                        "আজকের বৃষ্টির পরিমাণ দিন",
                        None
                    )
                )

                _voice_input_field(
                    "agriculture_manual_rain",
                    "আজকের বৃষ্টির পরিমাণ বলুন",
                    "number",
                    minimum=0.0
                )


            with c2:

                prepare_voice_input("agriculture_manual_et0")

                et0_value = st.number_input(
                    "রেফারেন্স বাষ্পীভবন "
                    "(ET0 / Reference Evapotranspiration) mm/day",
                    min_value=0.0,
                    value=4.0,
                    step=0.1,
                    key="agriculture_manual_et0",
                    on_change=input_voice_callback,
                    args=(
                        "agriculture_manual_et0",
                        "রেফারেন্স বাষ্পীভবনের পরিমাণ দিন",
                        None
                    )
                )

                _voice_input_field(
                    "agriculture_manual_et0",
                    "রেফারেন্স বাষ্পীভবনের পরিমাণ বলুন",
                    "number",
                    minimum=0.0
                )


    return (
        weather_source,
        predicted_rain,
        et0_value
    )


# ============================================================
# LAND INFORMATION SECTION
# ============================================================

def land_information_section():

    section_title(
        "জমির তথ্য",
        "Land Information"
    )


    with st.container(border=True):

        c1, c2 = st.columns(2)


        # ----------------------------------------------------
        # LAND AREA
        # ----------------------------------------------------
        # value=None দিলে box খালি থাকে এবং ভিতরে placeholder
        # লেখা দেখায় — ঠিক "ফসল নির্বাচন করুন" এর মতো।
        # কৃষক সংখ্যা দিলে তখনই value বসে।

        with c1:

            prepare_voice_input("agriculture_land_area")

            land_area = st.number_input(
                "জমির পরিমাণ (Land Area)",
                min_value=0.01,
                value=None,
                step=0.01,
                placeholder="জমির পরিমাণ লিখুন",
                key="agriculture_land_area",
                on_change=input_voice_callback,
                args=(
                    "agriculture_land_area",
                    "জমির পরিমাণ দিন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_land_area",
                "জমির পরিমাণ বলুন",
                "number",
                minimum=0.01
            )


        # ----------------------------------------------------
        # AREA UNIT
        # ----------------------------------------------------

        with c2:

            prepare_voice_input("agriculture_area_unit")

            area_unit = st.selectbox(
                "জমির একক (Area Unit)",
                [
                    "শতক (Decimal)",
                    "একর (Acre)",
                    "হেক্টর (Hectare)",
                    "বর্গমিটার (Square Meter)"
                ],
                index=None,
                placeholder="জমির একক নির্বাচন করুন",
                key="agriculture_area_unit",
                on_change=input_voice_callback,
                args=(
                    "agriculture_area_unit",
                    "জমির একক নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_area_unit",
                "জমির একক বলুন",
                "option",
                [
                    "শতক (Decimal)",
                    "একর (Acre)",
                    "হেক্টর (Hectare)",
                    "বর্গমিটার (Square Meter)"
                ]
            )


        if land_area is None or area_unit is None:

            st.info(
                "জমির পরিমাণ লিখুন এবং একক নির্বাচন করুন।"
            )


    return (
        land_area,
        area_unit
    )


# ============================================================
# CROP INFORMATION SECTION
# ============================================================

def crop_information_section():

    section_title(
        "ফসলের তথ্য",
        "Crop Information"
    )

    crop_options = get_crop_options()

    if not crop_options:

        st.error(
            "Crop reference dataset পাওয়া যায়নি।"
        )

        return (
            None,
            None,
            None,
            None,
            True
        )


    # --------------------------------------------------------
    # CROP + SEASON  (BOX)
    # --------------------------------------------------------

    with st.container(border=True):

        c1, c2 = st.columns(2)


        # ====================================================
        # CROP
        # ====================================================

        with c1:

            prepare_voice_input("agriculture_crop_select")

            crop_label = st.selectbox(
                "ফসল নির্বাচন করুন (Select Crop)",
                list(crop_options.keys()),
                index=None,
                placeholder="ফসল নির্বাচন করুন",
                key="agriculture_crop_select",
                on_change=input_voice_callback,
                args=(
                    "agriculture_crop_select",
                    "ফসল নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_crop_select",
                "ফসলের নাম বলুন",
                "option",
                list(crop_options.keys())
            )


        # Nothing else is rendered until a crop is actually selected.
        if crop_label is None:

            st.info(
                "উপরের বক্সে একটি ফসল নির্বাচন করুন।"
            )

            return (
                None,
                None,
                None,
                None,
                True
            )


        previous_crop = st.session_state.get(
            "agriculture_previous_crop"
        )


        crop_changed = (
            previous_crop is not None
            and previous_crop != crop_label
        )


        # A crop change makes the old season invalid.
        if crop_changed:

            st.session_state.pop(
                "agriculture_season_select",
                None
            )

            st.session_state.pop(
                "agriculture_interaction_voice_agriculture_season_select",
                None
            )

            st.session_state.pop(
                "agriculture_crop_voice_signature",
                None
            )


        st.session_state[
            "agriculture_previous_crop"
        ] = crop_label


        crop_name = crop_options[
            crop_label
        ]


        # ====================================================
        # SEASON
        # ====================================================

        season_options = get_season_options(
            crop_name
        )


        if not season_options:

            st.error(
                "এই ফসলের Season data পাওয়া যায়নি।"
            )

            return (
                crop_label,
                crop_name,
                None,
                None,
                True
            )


        # ----------------------------------------------------
        # ধান (Rice) → কৃষক নিজে মৌসুম নির্বাচন করবেন।
        # অন্য সব ফসল → একটি মাত্র মৌসুম নিজে থেকেই নির্বাচিত হবে।
        # ----------------------------------------------------

        is_rice = crop_label.startswith("ধান")


        # ----------------------------------------------------
        # CROP SELECTION VOICE (COMBINED, SINGLE CALL)
        # ----------------------------------------------------
        #
        # আগে crop select-এর voice দুই জায়গা থেকে আলাদাভাবে
        # generate হতো — (১) on_change callback থেকে generic
        # confirmation, (২) non-rice ফসলের জন্য আলাদা auto-season
        # speak_sequence()। voice player-এ একবারে একটাই audio
        # slot থাকায় দ্বিতীয় call প্রথমটাকে overwrite করে ফেলত,
        # ফলে "{ফসল} নির্বাচন করা হয়েছে" কখনো শোনা যেত না এবং
        # non-rice-এর ক্ষেত্রে পরের instruction ("হিসাবের তারিখ
        # নির্বাচন করুন")-ও কখনো বলা হতো না।
        #
        # এখন পুরো chain (crop confirmation + rice হলে "মৌসুম
        # নির্বাচন করুন" / non-rice হলে auto-season announce +
        # "হিসাবের তারিখ নির্বাচন করুন") একটি মাত্র speak_sequence()
        # call-এ পাঠানো হচ্ছে, crop_label পরিবর্তন হলে ঠিক একবার।

        crop_voice_signature = crop_label

        crop_voice_already_spoken = (
            st.session_state.get(
                "agriculture_crop_voice_signature"
            )
            == crop_voice_signature
        )


        if is_rice:

            if not crop_voice_already_spoken:

                st.session_state[
                    "agriculture_crop_voice_signature"
                ] = crop_voice_signature

                speak_sequence(
                    [
                        f"{clean_voice_text(crop_label)} নির্বাচন করা হয়েছে",
                        "মৌসুম নির্বাচন করুন"
                    ],
                    delay=0.10
                )

            with c2:

                prepare_voice_input("agriculture_season_select")

                season_label = st.selectbox(
                    "মৌসুম নির্বাচন করুন (Select Season)",
                    list(season_options.keys()),
                    index=None,
                    placeholder="মৌসুম নির্বাচন করুন",
                    key="agriculture_season_select",
                    on_change=input_voice_callback,
                    args=(
                        "agriculture_season_select",
                        "মৌসুম নির্বাচন করুন",
                        None
                    )
                )

                _voice_input_field(
                    "agriculture_season_select",
                    "মৌসুমের নাম বলুন",
                    "option",
                    list(season_options.keys())
                )


            if season_label is None:

                st.info(
                    "মৌসুম নির্বাচন করুন।"
                )

                return (
                    crop_label,
                    crop_name,
                    None,
                    None,
                    True
                )


            season_name = season_options[season_label]


        else:

            # শুধুমাত্র একটি মৌসুম উপলব্ধ থাকায় সেটিই
            # নিজে নিজে নির্বাচিত হয় — কৃষককে আলাদা করে
            # কিছু নির্বাচন করতে হয় না।

            season_label = list(season_options.keys())[0]
            season_name = season_options[season_label]

            if not crop_voice_already_spoken:

                st.session_state[
                    "agriculture_crop_voice_signature"
                ] = crop_voice_signature

                speak_sequence(
                    [
                        f"{clean_voice_text(crop_label)} নির্বাচন করা হয়েছে",
                        f"{clean_voice_text(season_label)} "
                        f"মৌসুম স্বয়ংক্রিয়ভাবে নির্বাচন করা হয়েছে।",
                        "হিসাবের তারিখ নির্বাচন করুন"
                    ],
                    delay=0.10
                )

            with c2:

                st.info(
                    f"মৌসুম (Season): {season_label}"
                )


    return (
        crop_label,
        crop_name,
        season_label,
        season_name,
        False
    )


# ============================================================
# PLANTING / GROWTH SECTION
# ============================================================

def planting_growth_section(
    crop_name,
    season_name
):

    section_title(
        "রোপণ/বপন ও বৃদ্ধির পর্যায়",
        "Planting & Growth Stage"
    )


    with st.container(border=True):

        d1, d2 = st.columns(2)


        with d1:

            prepare_voice_input("agriculture_calculation_date")

            calculation_date = st.date_input(
                "হিসাবের তারিখ (Calculation Date)",
                value=None,
                format="YYYY/MM/DD",
                key="agriculture_calculation_date",
                on_change=input_voice_callback,
                args=(
                    "agriculture_calculation_date",
                    "হিসাবের তারিখ নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_calculation_date",
                "হিসাবের তারিখ বলুন, যেমন ১৫ সেপ্টেম্বর ২০২৬",
                "date"
            )


        with d2:

            prepare_voice_input("agriculture_actual_planting_date")

            actual_planting_date = st.date_input(
                "রোপণ/বপনের তারিখ "
                "(Planting / Sowing Date)",
                value=None,
                format="YYYY/MM/DD",
                key="agriculture_actual_planting_date",
                on_change=input_voice_callback,
                args=(
                    "agriculture_actual_planting_date",
                    "রোপণ বা বপনের তারিখ নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_actual_planting_date",
                "রোপণ বা বপনের তারিখ বলুন, যেমন ১০ জুলাই ২০২৬",
                "date"
            )


        if (
            calculation_date is None
            or actual_planting_date is None
        ):

            st.info(
                "হিসাবের তারিখ এবং রোপণ/বপনের তারিখ নির্বাচন করুন। "
                "ক্যালেন্ডার থেকে নির্বাচন করতে পারেন অথবা তারিখ লিখতে পারেন।"
            )


    use_actual_planting = True


    if (
        calculation_date is None
        or actual_planting_date is None
    ):

        return (
            calculation_date,
            actual_planting_date,
            use_actual_planting,
            {
                "available": False,
                "status": "INCOMPLETE"
            },
            None,
            False
        )


    st.caption(
        "ফসলের বয়স ও বৃদ্ধি পর্যায় "
        "রোপণ/বপনের তারিখ থেকে স্বয়ংক্রিয়ভাবে হিসাব করা হবে।"
    )


    stage_info = determine_growth_stage(
        crop_name,
        season_name,
        calculation_date,
        planting_date=actual_planting_date,
        use_actual_planting_date=use_actual_planting
    )


    calculation_allowed = True
    crop_stage = None


    # ========================================================
    # STAGE AVAILABLE
    # ========================================================

    if stage_info.get("available"):

        automatic_stage = (
            stage_info["stage"]
        )


        # Auto-detected stage is announced first. The farmer can
        # then change the stage from the selector if needed.
        stage_voice_state_key = (
            "agriculture_auto_stage_voice_signature"
        )

        stage_voice_signature = (
            crop_name,
            season_name,
            str(calculation_date),
            str(actual_planting_date),
            automatic_stage
        )

        if (
            st.session_state.get(
                stage_voice_state_key
            )
            != stage_voice_signature
        ):

            st.session_state[
                stage_voice_state_key
            ] = (
                stage_voice_signature
            )

            growth_stage_auto_voice(
                stage_info.get(
                    "stage_label",
                    automatic_stage
                )
            )


        with st.container(border=True):

            st.markdown(
                f"""
                <div style="font-size:16px; font-weight:600; margin:0 0 10px 0;">
                    স্বয়ংক্রিয়ভাবে নির্ধারিত পর্যায়:
                    {stage_info.get('stage_label', automatic_stage)}
                </div>
                """,
                unsafe_allow_html=True
            )


            c1, c2 = st.columns(2)


            with c1:

                prepare_voice_input("agriculture_growth_stage")

                manual_stage_label = st.selectbox(
                    "বর্তমান বৃদ্ধি পর্যায় "
                    "(Growth Stage)",
                    [
                        "স্বয়ংক্রিয় (Automatic)",
                        "চারা/প্রাথমিক পর্যায় (Initial Stage)",
                        "বৃদ্ধি পর্যায় (Development Stage)",
                        "মধ্য পর্যায় (Mid Stage)",
                        "পরিপক্বতা পর্যায় (Late Stage)"
                    ],
                    key="agriculture_growth_stage",
                    on_change=input_voice_callback,
                    args=(
                        "agriculture_growth_stage",
                        "বর্তমান বৃদ্ধি পর্যায় নির্বাচন করুন",
                        None
                    )
                )

                _voice_input_field(
                    "agriculture_growth_stage",
                    "বৃদ্ধি পর্যায় বলুন",
                    "option",
                    [
                        "স্বয়ংক্রিয় (Automatic)",
                        "চারা/প্রাথমিক পর্যায় (Initial Stage)",
                        "বৃদ্ধি পর্যায় (Development Stage)",
                        "মধ্য পর্যায় (Mid Stage)",
                        "পরিপক্বতা পর্যায় (Late Stage)"
                    ]
                )


            stage_map = {

                "স্বয়ংক্রিয় (Automatic)":
                    automatic_stage,

                "চারা/প্রাথমিক পর্যায় (Initial Stage)":
                    "Initial",

                "বৃদ্ধি পর্যায় (Development Stage)":
                    "Development",

                "মধ্য পর্যায় (Mid Stage)":
                    "Mid",

                "পরিপক্বতা পর্যায় (Late Stage)":
                    "Late"
            }


            crop_stage = stage_map[
                manual_stage_label
            ]


            c2.info(
                f"""
                ফসলের বয়স

                {bn_num(
                    stage_info.get('day_of_crop'),
                    0
                )}
                দিন /

                {bn_num(
                    stage_info.get('duration_days'),
                    0
                )}
                দিন
                """
            )


            st.caption(
                "আপনি চাইলে উপরের বৃদ্ধি পর্যায় থেকে "
                "অন্য পর্যায় নির্বাচন করতে পারেন।"
            )


            if stage_info.get("message"):

                st.success(
                    stage_info["message"]
                )


            if stage_info.get("warning"):

                st.warning(
                    stage_info["warning"]
                )


    # ========================================================
    # OUT OF SEASON
    # ========================================================

    elif stage_info.get("status") == "OUT_OF_SEASON":

        calculation_allowed = False


        with st.container(border=True):

            c1, c2 = st.columns(2)


            c1.text_input(
                "ফসলের বৃদ্ধি পর্যায় "
                "(Crop Growth Stage)",
                value="মৌসুমের বাইরে (Out of Season)",
                disabled=True,
                key="agriculture_out_of_season_stage"
            )


            reference_period = (
                f"{date_text(stage_info.get('reference_start_date'))}"
                f" → "
                f"{date_text(stage_info.get('reference_end_date'))}"
            )


            c2.text_input(
                "রেফারেন্স ফসলের সময়কাল "
                "(Reference Crop Period)",
                value=reference_period,
                disabled=True,
                key="agriculture_reference_period"
            )


            st.error(
                "নির্বাচিত হিসাবের তারিখটি এই ফসলের "
                "reference growing season-এর বাইরে। "
                "মৌসুমের মধ্যে একটি তারিখ নির্বাচন করুন "
                "অথবা কৃষকের প্রকৃত রোপণ/বপনের তারিখ ব্যবহার করুন।"
            )


    # ========================================================
    # INVALID / FUTURE / COMPLETE
    # ========================================================

    elif stage_info.get("status") in [
        "FUTURE_PLANTING_DATE",
        "CROP_CYCLE_COMPLETE",
        "INVALID_PLANTING_DATE"
    ]:

        calculation_allowed = False


        st.error(
            stage_info.get(
                "message",
                "রোপণ/বপনের তারিখ সঠিক নয়। আবার নির্বাচন করুন।"
            )
        )


    # ========================================================
    # CALENDAR INCOMPLETE
    # ========================================================

    else:

        with st.container(border=True):

            st.warning(
                stage_info.get(
                    "message",
                    "Calendar data অসম্পূর্ণ।"
                )
            )


            prepare_voice_input("agriculture_growth_stage_fallback")

            manual_stage_label = st.selectbox(
                "বর্তমান বৃদ্ধি পর্যায় "
                "(Growth Stage)",
                [
                    "চারা/প্রাথমিক পর্যায় (Initial Stage)",
                    "বৃদ্ধি পর্যায় (Development Stage)",
                    "মধ্য পর্যায় (Mid Stage)",
                    "পরিপক্বতা পর্যায় (Late Stage)"
                ],
                index=None,
                placeholder="বৃদ্ধি পর্যায় নির্বাচন করুন",
                key="agriculture_growth_stage_fallback",
                on_change=input_voice_callback,
                args=(
                    "agriculture_growth_stage_fallback",
                    "বর্তমান বৃদ্ধি পর্যায় নির্বাচন করুন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_growth_stage_fallback",
                "বৃদ্ধি পর্যায় বলুন",
                "option",
                [
                    "চারা/প্রাথমিক পর্যায় (Initial Stage)",
                    "বৃদ্ধি পর্যায় (Development Stage)",
                    "মধ্য পর্যায় (Mid Stage)",
                    "পরিপক্বতা পর্যায় (Late Stage)"
                ]
            )


            stage_map = {

                "চারা/প্রাথমিক পর্যায় (Initial Stage)":
                    "Initial",

                "বৃদ্ধি পর্যায় (Development Stage)":
                    "Development",

                "মধ্য পর্যায় (Mid Stage)":
                    "Mid",

                "পরিপক্বতা পর্যায় (Late Stage)":
                    "Late"
            }


            # Calendar data না থাকায় "স্বয়ংক্রিয়" option রাখা হয়নি।
            # আগে Automatic নিলে crop_stage None হয়ে যেত এবং
            # get_kc() / calculate_irrigation() fail করত।

            crop_stage = stage_map.get(
                manual_stage_label
            )


            if crop_stage is None:

                calculation_allowed = False

                st.info(
                    "Calendar data অসম্পূর্ণ। "
                    "হিসাব করার আগে বৃদ্ধি পর্যায় নির্বাচন করুন।"
                )


            st.caption(
                "Calendar data অসম্পূর্ণ হওয়ায় "
                "Growth Stage manualভাবে নির্বাচন করা হচ্ছে।"
            )


    return (
        calculation_date,
        actual_planting_date,
        use_actual_planting,
        stage_info,
        crop_stage,
        calculation_allowed
    )


# ============================================================
# CROP REFERENCE SECTION
# ============================================================

def crop_reference_section(
    crop_label,
    season_label,
    crop_reference
):
    """
    ফসলের রেফারেন্স তথ্য।

    আগে এটি একটি expander (ক্লিক করে খোলা) হিসেবে ছিল, যা দেখতে
    dropdown/option-এর মতো লাগছিল। এখন এটি সরাসরি একটি auto-visible
    card হিসেবে দেখানো হয় — বাকি "love card" (.agri-card) গুলোর
    মতোই — ক্লিক করার দরকার নেই।
    """

    if not crop_reference:

        return


    cultivar = crop_reference.get("cultivar") or "N/A"


    duration_row = ""

    if crop_reference.get("duration_days") is not None:

        duration_row = (
            f"<p>রেফারেন্স সময়কাল (Reference Duration): "
            f"{bn_num(crop_reference['duration_days'], 0)} দিন</p>"
        )


    cwr_row = ""

    if crop_reference.get("cwr_mm") is not None:

        cwr_row = (
            f"<p>মৌসুমি ফসলের পানির চাহিদা (Seasonal CWR Reference): "
            f"{bn_num(crop_reference['cwr_mm'], 0)} mm/season</p>"
        )


    iwr_row = ""

    if crop_reference.get("iwr_mm") is not None:

        iwr_row = (
            f"<p>মৌসুমি সেচের রেফারেন্স (Seasonal IWR Reference): "
            f"{bn_num(crop_reference['iwr_mm'], 0)} mm/season</p>"
        )


    st.markdown(
        f"""
        <div class='agri-card'>
            <h3>ফসলের রেফারেন্স তথ্য (Crop Reference Information)</h3>
            <p>ফসল (Crop): {crop_label}</p>
            <p>মৌসুম (Season): {season_label}</p>
            <p>জাত (Cultivar): {cultivar}</p>
            {duration_row}
            {cwr_row}
            {iwr_row}
            <p style="font-size:13px; opacity:.75; margin-top:8px;">
                নোট: CWR/IWR এখানে seasonal reference। এগুলো আজকের
                daily irrigation requirement নয়।
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# SOIL SECTION
# ============================================================

def soil_information_section():

    section_title(
        "মাটির তথ্য",
        "Soil Information"
    )


    with st.container(border=True):

        prepare_voice_input("agriculture_soil_type")

        soil_type = st.selectbox(
            "মাটির ধরন (Soil Type)",
            list(SOIL_TYPES.keys()),
            key="agriculture_soil_type",
            on_change=input_voice_callback,
            args=(
                "agriculture_soil_type",
                "মাটির ধরন নির্বাচন করুন",
                None
            )
        )

        _voice_input_field(
            "agriculture_soil_type",
            "মাটির ধরন বলুন",
            "option",
            list(SOIL_TYPES.keys())
        )


        st.caption(
            SOIL_TYPES[soil_type]["description"]
        )


        st.caption(
            "নোট: মাটির ধরন তথ্য ও পরামর্শের জন্য ব্যবহার করা হচ্ছে। "
            "সেচের পরিমাণে কোনো arbitrary soil multiplier প্রয়োগ করা হচ্ছে না।"
        )


    return soil_type


# ============================================================
# EXISTING WATER SECTION
# ============================================================

def existing_water_section(
    land_area,
    area_unit
):

    section_title(
        "জমিতে আগে থেকে থাকা পানি",
        "Existing Water"
    )


    st.info(
        """
        জমিতে কত মিলিমিটার পানি আছে তা সরাসরি জানা কঠিন।
        তাই আপনি আঙুল দিয়ে পানির গভীরতা মাপতে পারেন।
        সিস্টেম সেই পরিমাপকে আনুমানিক মিলিমিটারে পরিবর্তন করবে।
        এটি একটি আনুমানিক হিসাব।
        """
    )


    with st.container(border=True):

        prepare_voice_input("agriculture_water_measurement")

        water_measurement = st.selectbox(
            "পানির গভীরতা নির্বাচন করুন "
            "(Select Water Depth)",
            list(WATER_DEPTH_OPTIONS.keys())
            +
            [
                "নিজে পরিমাপ দিন "
                "(Custom Measurement)"
            ],
            key="agriculture_water_measurement",
            on_change=input_voice_callback,
            args=(
                "agriculture_water_measurement",
                "পানির গভীরতা নির্বাচন করুন",
                None
            )
        )

        _voice_input_field(
            "agriculture_water_measurement",
            "পানির গভীরতার ধরন বলুন",
            "option",
            list(WATER_DEPTH_OPTIONS.keys()) + [
                "নিজে পরিমাপ দিন (Custom Measurement)"
            ]
        )


        custom_depth_cm = 0.0


        if water_measurement == (
            "নিজে পরিমাপ দিন "
            "(Custom Measurement)"
        ):

            prepare_voice_input("agriculture_custom_water_depth")

            custom_depth_cm = st.number_input(
                "পানির গভীরতা সেন্টিমিটারে দিন "
                "(Water Depth in cm)",
                min_value=0.0,
                value=0.0,
                step=0.5,
                key="agriculture_custom_water_depth",
                on_change=input_voice_callback,
                args=(
                    "agriculture_custom_water_depth",
                    "পানির গভীরতা সেন্টিমিটারে দিন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_custom_water_depth",
                "পানির গভীরতা সেন্টিমিটারে বলুন",
                "number",
                minimum=0.0
            )


    existing_water_mm = (
        convert_water_depth_to_mm(
            water_measurement,
            custom_depth_cm
        )
    )


    area_m2_preview = convert_area_to_m2(
        land_area,
        area_unit
    )


    existing_water_volume = (
        calculate_existing_water_volume(
            area_m2_preview,
            existing_water_mm
        )
    )


    section_title(
        "আনুমানিক পানির হিসাব",
        "Estimated Water Calculation"
    )


    with st.container(border=True):

        a, b, c = st.columns(3)


        a.metric(
            "আনুমানিক পানির গভীরতা "
            "(Estimated Water Depth)",
            f"{bn_num(existing_water_mm, 1)} mm"
        )


        b.metric(
            "আনুমানিক মোট পানি "
            "(Estimated Total Water)",
            f"{bn_num(existing_water_volume['water_liters'], 0, True)} L"
        )


        c.metric(
            "আনুমানিক পানির পরিমাণ "
            "(Estimated Water Volume)",
            f"{bn_num(existing_water_volume['water_m3'], 2)} m³"
        )


        st.caption(
            "নোট: আঙুল দিয়ে মাপার কারণে এটি আনুমানিক হিসাব। "
            "বিশেষ করে ধানের ক্ষেত্রে দৃশ্যমান standing water "
            "এবং root-zone available water এক জিনিস নয়।"
        )


    return (
        water_measurement,
        existing_water_mm,
        existing_water_volume
    )


# ============================================================
# CROP WATER REQUIREMENT SECTION
# ============================================================

def crop_water_requirement_section(
    crop_name,
    crop_stage,
    et0_value,
    predicted_rain
):

    section_title(
        "ফসলের পানির চাহিদা",
        "Crop Water Requirement"
    )


    kc_preview = None
    automatic_etc_preview = None


    if crop_stage is not None:

        try:

            kc_preview = get_kc(
                crop_name,
                crop_stage
            )

        except Exception:

            kc_preview = None


        if kc_preview is not None:

            automatic_etc_preview = (
                float(et0_value)
                *
                float(kc_preview["kc"])
            )


    # ========================================================
    # AUTOMATIC ETC
    # ========================================================

    if automatic_etc_preview is not None:

        with st.container(border=True):

            a, b, c = st.columns(3)


            a.metric(
                "ET0 "
                "(Reference Evapotranspiration)",
                f"{bn_num(et0_value, 2)} mm/day"
            )


            b.metric(
                "ফসল সহগ "
                "(Crop Coefficient / Kc)",
                f"{bn_num(kc_preview['kc'], 2)}"
            )


            c.metric(
                "দৈনিক ফসলের পানির চাহিদা "
                "(Daily Crop Water Need / ETc)",
                f"{bn_num(automatic_etc_preview, 2)} mm/day"
            )


            if predicted_rain <= 0:

                st.warning(
                    f"""
                    আজ বৃষ্টি না হলেও এই ফসলের বর্তমান stage অনুযায়ী
                    আনুমানিক {bn_num(automatic_etc_preview, 2)} mm/day
                    পানি প্রয়োজন। জমিতে পর্যাপ্ত পানি না থাকলে
                    সেচ প্রয়োজন হতে পারে।
                    """
                )


    # ========================================================
    # METHOD  (BOX)
    # ========================================================

    with st.container(border=True):

        prepare_voice_input("agriculture_water_requirement_method")

        water_requirement_method = st.radio(
            "পানির চাহিদা নির্ধারণের পদ্ধতি "
            "(Water Requirement Method)",
            [
                "স্বয়ংক্রিয়ভাবে পানির চাহিদা নির্ধারণ করুন "
                "(Automatic — Recommended)",

                "নিজে দৈনিক পানির চাহিদা দিন "
                "(Manual Override)"
            ],
            index=None,
            key="agriculture_water_requirement_method",
            on_change=input_voice_callback,
            args=(
                "agriculture_water_requirement_method",
                "পানির চাহিদা নির্ধারণের পদ্ধতি নির্বাচন করুন",
                None
            )
        )

        _voice_input_field(
            "agriculture_water_requirement_method",
            "পানির চাহিদা নির্ধারণের পদ্ধতি বলুন",
            "option",
            [
                "স্বয়ংক্রিয়ভাবে পানির চাহিদা নির্ধারণ করুন (Automatic — Recommended)",
                "নিজে দৈনিক পানির চাহিদা দিন (Manual Override)"
            ]
        )


        if water_requirement_method is None:

            st.info(
                "উপরের যেকোনো একটি বক্স নির্বাচন করুন।"
            )


    if water_requirement_method is None:

        return (
            kc_preview,
            automatic_etc_preview,
            None,
            None
        )


    manual_crop_water_need_mm = None


    if water_requirement_method.startswith(
        "নিজে"
    ):

        default_manual_need = (
            float(automatic_etc_preview)
            if automatic_etc_preview is not None
            else 0.0
        )


        with st.container(border=True):

            # NOTE:
            # key already in session state হলে Streamlit value=
            # উপেক্ষা করে। তাই প্রথমবার default বসানো হচ্ছে।

            if (
                "agriculture_manual_crop_water_need"
                not in st.session_state
            ):

                st.session_state[
                    "agriculture_manual_crop_water_need"
                ] = default_manual_need


            prepare_voice_input("agriculture_manual_crop_water_need")

            manual_crop_water_need_mm = st.number_input(
                "দৈনিক ফসলের পানির চাহিদা "
                "(Daily Crop Water Requirement) mm/day",
                min_value=0.0,
                step=0.1,
                key="agriculture_manual_crop_water_need",
                on_change=input_voice_callback,
                args=(
                    "agriculture_manual_crop_water_need",
                    "দৈনিক ফসলের পানির চাহিদা দিন",
                    None
                )
            )

            _voice_input_field(
                "agriculture_manual_crop_water_need",
                "দৈনিক ফসলের পানির চাহিদা বলুন",
                "number",
                minimum=0.0
            )


            st.warning(
                "Manual Override ব্যবহার করলে irrigation calculation "
                "আপনার দেওয়া daily crop water requirement অনুযায়ী হবে। "
                "Automatic ET0 × Kc value reference হিসেবে উপরে দেখানো থাকবে।"
            )


    return (
        kc_preview,
        automatic_etc_preview,
        water_requirement_method,
        manual_crop_water_need_mm
    )


# ============================================================
# IRRIGATION SECTION
# ============================================================

def irrigation_system_section():

    section_title(
        "সেচ ব্যবস্থা",
        "Irrigation System"
    )


    with st.container(border=True):

        prepare_voice_input("agriculture_irrigation_method")

        irrigation_method = st.selectbox(
            "সেচ পদ্ধতি নির্বাচন করুন "
            "(Select Irrigation Method)",
            [
                "সাধারণ সেচ (Traditional Irrigation)",
                "স্প্রিংকলার (Sprinkler)",
                "ড্রিপ সেচ (Drip Irrigation)"
            ],
            key="agriculture_irrigation_method",
            on_change=input_voice_callback,
            args=(
                "agriculture_irrigation_method",
                "সেচ পদ্ধতি নির্বাচন করুন",
                None
            )
        )

        _voice_input_field(
            "agriculture_irrigation_method",
            "সেচ পদ্ধতির নাম বলুন",
            "option",
            [
                "সাধারণ সেচ (Traditional Irrigation)",
                "স্প্রিংকলার (Sprinkler)",
                "ড্রিপ সেচ (Drip Irrigation)"
            ]
        )


        if irrigation_method.startswith(
            "সাধারণ"
        ):

            default_efficiency = 60

        elif irrigation_method.startswith(
            "স্প্রিংকলার"
        ):

            default_efficiency = 75

        else:

            default_efficiency = 90


        # ----------------------------------------------------
        # EFFICIENCY AUTO UPDATE
        # ----------------------------------------------------
        # slider-এ key থাকলে Streamlit session value ব্যবহার করে
        # এবং value= সম্পূর্ণ উপেক্ষা করে। তাই সেচ পদ্ধতি বদলালেও
        # আগের percentage আটকে থাকত (৬০ → ড্রিপ নিলেও ৬০)।
        #
        # সমাধান: slider তৈরি হওয়ার আগেই session value বসানো।
        # widget instantiate হওয়ার আগে session state লেখা বৈধ।

        method_signature_key = (
            "agriculture_efficiency_method_signature"
        )

        if (
            st.session_state.get(method_signature_key)
            != irrigation_method
        ):

            st.session_state[
                method_signature_key
            ] = irrigation_method

            st.session_state[
                "agriculture_irrigation_efficiency"
            ] = default_efficiency


        irrigation_efficiency = st.slider(
            "সেচ দক্ষতা (Irrigation Efficiency %)",
            min_value=30,
            max_value=100,
            key="agriculture_irrigation_efficiency",
            on_change=input_voice_callback,
            args=(
                "agriculture_irrigation_efficiency",
                "সেচ দক্ষতা নির্বাচন করুন",
                None
            )
        )


        st.caption(
            "নোট: Default efficiency values planning assumption হিসেবে "
            "ব্যবহৃত হচ্ছে। প্রয়োজন হলে field condition অনুযায়ী "
            "slider পরিবর্তন করুন।"
        )


    return (
        irrigation_method,
        irrigation_efficiency
    )


# ============================================================
# MAIN INPUT PANEL
# ============================================================


def _agriculture_input_panel():

    # ========================================================
    # WEATHER
    # ========================================================

    (
        weather_source,
        predicted_rain,
        et0_value
    ) = weather_information_section()


    if weather_source is None:

        return


    # ========================================================
    # LAND
    # ========================================================

    (
        land_area,
        area_unit
    ) = land_information_section()


    # জমির পরিমাণ/একক ছাড়া convert_area_to_m2() কাজ করবে না।
    if land_area is None or area_unit is None:

        return


    # ========================================================
    # CROP
    # ========================================================

    (
        crop_label,
        crop_name,
        season_label,
        season_name,
        crop_error
    ) = crop_information_section()


    if crop_error:

        return


    # ========================================================
    # CROP REFERENCE
    # ========================================================

    crop_reference = get_crop_reference(
        crop_name,
        season_name
    )


    # ========================================================
    # PLANTING / GROWTH
    # ========================================================

    (
        calculation_date,
        actual_planting_date,
        use_actual_planting,
        stage_info,
        crop_stage,
        calculation_allowed
    ) = planting_growth_section(
        crop_name,
        season_name
    )


    # ========================================================
    # REFERENCE
    # ========================================================

    crop_reference_section(
        crop_label,
        season_label,
        crop_reference
    )


    # ========================================================
    # SOIL
    # ========================================================

    soil_type = (
        soil_information_section()
    )


    # ========================================================
    # EXISTING WATER
    # ========================================================

    (
        water_measurement,
        existing_water_mm,
        existing_water_volume
    ) = existing_water_section(
        land_area,
        area_unit
    )


    # ========================================================
    # CROP WATER
    # ========================================================

    (
        kc_preview,
        automatic_etc_preview,
        water_requirement_method,
        manual_crop_water_need_mm
    ) = crop_water_requirement_section(
        crop_name,
        crop_stage,
        et0_value,
        predicted_rain
    )


    # ========================================================
    # IRRIGATION
    # ========================================================

    (
        irrigation_method,
        irrigation_efficiency
    ) = irrigation_system_section()


    # ========================================================
    # CALCULATION GUARDS
    # ========================================================
    #
    # পদ্ধতি বা বৃদ্ধি পর্যায় নির্বাচন না করলে calculate করা
    # যাবে না। আগে এই guard না থাকায় crop_stage=None নিয়ে
    # calculate_irrigation() exception দিত।

    missing_inputs = []


    if water_requirement_method is None:

        missing_inputs.append(
            "পানির চাহিদা নির্ধারণের পদ্ধতি"
        )

        calculation_allowed = False


    if crop_stage is None:

        missing_inputs.append(
            "ফসলের বৃদ্ধি পর্যায়"
        )

        calculation_allowed = False


    # ========================================================
    # INPUT SIGNATURE
    # ========================================================

    current_signature = (

        crop_name,

        season_name,

        str(calculation_date),

        str(actual_planting_date),

        use_actual_planting,

        crop_stage,

        float(predicted_rain),

        float(et0_value),

        float(existing_water_mm),

        float(land_area),

        area_unit,

        soil_type,

        irrigation_method,

        int(irrigation_efficiency),

        water_requirement_method,

        (
            None
            if manual_crop_water_need_mm is None
            else float(
                manual_crop_water_need_mm
            )
        )
    )


    # ========================================================
    # CALCULATE
    # ========================================================

    calculate_clicked = st.button(
        "স্মার্ট সেচ হিসাব করুন "
        "(Calculate Smart Irrigation)",
        type="primary",
        use_container_width=True,
        disabled=not calculation_allowed,
        key="agriculture_calculate_button"
    )


    if not calculation_allowed:

        if missing_inputs:

            st.caption(
                "হিসাব করার আগে নির্বাচন করুন: "
                + ", ".join(missing_inputs)
                + "।"
            )

        else:

            st.caption(
                "সঠিক Season / Planting Date নির্বাচন না করা পর্যন্ত "
                "calculation চালানো যাবে না।"
            )


    # ========================================================
    # CALCULATION
    # ========================================================

    if calculate_clicked:

        try:

            result = calculate_irrigation(

                land_area=land_area,

                area_unit=area_unit,

                crop_name=crop_name,

                crop_stage=crop_stage,

                soil_type=soil_type,

                existing_water_mm=existing_water_mm,

                predicted_rain_mm=predicted_rain,

                et0_value=et0_value,

                irrigation_efficiency=irrigation_efficiency,

                manual_crop_water_need_mm=(
                    manual_crop_water_need_mm
                )
            )


            # ------------------------------------------------
            # NO RAIN SCENARIO
            # ------------------------------------------------
            # যদি আজ কোনো বৃষ্টি না হয় — এই হিসাব result card-এ
            # লিখিতভাবেও দেখানো হবে (voice-এর সাথে হুবহু এক)।

            no_rain_net_mm = max(
                float(result["crop_water_need"])
                -
                float(result["available_water"]),
                0.0
            )

            efficiency_ratio = (
                float(irrigation_efficiency)
                /
                100.0
            )

            no_rain_gross_mm = (
                no_rain_net_mm
                /
                efficiency_ratio
                if efficiency_ratio > 0
                else 0.0
            )

            no_rain_water_liters = (
                no_rain_gross_mm
                *
                float(result["area_m2"])
            )


            if no_rain_net_mm > 0:

                no_rain_message = (
                    f"যদি আজ কোনো বৃষ্টি না হয়, তাহলে জমিতে থাকা পানি বাদ দেওয়ার পর "
                    f"প্রায় {no_rain_gross_mm:.1f} মিলিমিটার অথবা "
                    f"{no_rain_water_liters:.0f} লিটার পানি সেচ দিতে হবে।"
                )

            else:

                no_rain_message = (
                    "যদি আজ কোনো বৃষ্টি না হয়, তবুও জমিতে থাকা পানি "
                    "ফসলের বর্তমান দৈনিক পানির চাহিদা পূরণ করতে যথেষ্ট। "
                    "অতিরিক্ত সেচের প্রয়োজন হবে না।"
                )


            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            st.session_state.agri_result = {

                "input_signature":
                    current_signature,

                "result":
                    result,

                "crop_label":
                    crop_label,

                "crop_name":
                    crop_name,

                "season_label":
                    season_label,

                "season_name":
                    season_name,

                "crop_stage":
                    crop_stage,

                "crop_stage_label":
                    STAGE_LABELS.get(
                        crop_stage,
                        crop_stage
                    ),

                "stage_info":
                    stage_info,

                "actual_planting_date":
                    actual_planting_date,

                "calculation_date":
                    calculation_date,

                "soil_type":
                    soil_type,

                "predicted_rain":
                    predicted_rain,

                "existing_water":
                    existing_water_mm,

                "existing_water_liters":
                    existing_water_volume[
                        "water_liters"
                    ],

                "existing_water_m3":
                    existing_water_volume[
                        "water_m3"
                    ],

                "water_measurement":
                    water_measurement,

                "et0":
                    et0_value,

                "land_area":
                    land_area,

                "area_unit":
                    area_unit,

                "irrigation_method":
                    irrigation_method,

                "efficiency":
                    irrigation_efficiency,

                "water_requirement_method":
                    water_requirement_method,

                "manual_crop_water_need_mm":
                    manual_crop_water_need_mm,

                "crop_reference":
                    crop_reference,

                "no_rain_net_mm":
                    no_rain_net_mm,

                "no_rain_gross_mm":
                    no_rain_gross_mm,

                "no_rain_water_liters":
                    no_rain_water_liters,

                "no_rain_message":
                    no_rain_message,
            }


            # ------------------------------------------------
            # RESULT VOICE
            # ------------------------------------------------
            # Speak the main result immediately after calculation.
            # Smart recommendations remain separate and are only
            # spoken when the recommendation button is clicked.

            try:

                # New result must always be allowed to play.
                reset_voice_hash()

                agriculture_result_voice(
                    irrigation_needed=(
                        result.get("status")
                        !=
                        "NO_IRRIGATION"
                    ),

                    water_liters=float(
                        result.get(
                            "water_liters",
                            0.0
                        )
                    ),

                    gross_irrigation=float(
                        result.get(
                            "gross_water_mm",
                            0.0
                        )
                    ),

                    available_water=float(
                        result.get(
                            "available_water",
                            0.0
                        )
                    ),

                    effective_rain=float(
                        result.get(
                            "effective_rain",
                            0.0
                        )
                    ),

                    net_irrigation=float(
                        result.get(
                            "net_water_needed",
                            0.0
                        )
                    ),

                    no_rain_message=
                        no_rain_message,
                )


            except Exception as exc:

                st.warning(
                    f"ফলাফল ভয়েস তৈরি করা যায়নি "
                    f"(Result voice failed): {exc}"
                )


            st.session_state[
                "agriculture_show_recommendations"
            ] = False

            st.rerun()


        except Exception as exc:

            st.error(
                f"সেচ হিসাব করা যায়নি "
                f"(Irrigation calculation failed): {exc}"
            )


# ============================================================
# RESULT SECTION
# ============================================================

def show_agriculture_result():

    if "agri_result" not in st.session_state:

        return


    data = st.session_state.agri_result

    result = data["result"]

    stage_info = data.get(
        "stage_info"
    ) or {}


    st.divider()


    st.subheader(
        "স্মার্ট সেচের ফলাফল "
        "(Smart Irrigation Result)"
    )


    # ========================================================
    # STATUS
    # ========================================================

    st.markdown(
        f"""
        <div class='result-card'>
            <h2>{result['status_bn']}</h2>
            <h3>{result['status_en']}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # NOTE
    # ========================================================
    # ফসল / মৌসুম / বৃদ্ধি পর্যায় / ফসলের বয়স — এই তথ্যগুলো
    # কৃষক উপরেই দিয়েছে। Result card-এ আবার দেখালে সিদ্ধান্তের
    # উপর থেকে নজর সরে যায়। তাই এগুলো "হিসাবের বিস্তারিত"
    # expander-এ সরানো হয়েছে।


    # ========================================================
    # CROP WATER CALCULATION
    # ========================================================

    section_title(
        "ফসলের পানির হিসাব",
        "Crop Water Calculation"
    )


    with st.container(border=True):

        a, b, c = st.columns(3)


        a.metric(
            "ET0 "
            "(Reference Evapotranspiration)",
            f"{bn_num(result['et0_mm'], 2)} mm/day"
        )


        b.metric(
            "ফসল সহগ "
            "(Crop Coefficient / Kc)",
            f"{bn_num(result['kc'], 2)}"
        )


        c.metric(
            "স্বয়ংক্রিয় ETc "
            "(Automatic Crop Water Need)",
            f"{bn_num(result['automatic_etc_mm'], 2)} mm/day"
        )


        # ----------------------------------------------------
        # APPLIED WATER NEED
        # ----------------------------------------------------

        if result.get(
            "water_requirement_method"
        ) == "MANUAL":

            st.info(
                f"""
                ব্যবহৃত দৈনিক ফসলের পানির চাহিদা
                (Applied Daily Crop Water Requirement):

                {bn_num(
                    result['crop_water_need'],
                    2
                )}
                mm/day

                Manual Override
                """
            )


        else:

            st.info(
                f"""
                ব্যবহৃত দৈনিক ফসলের পানির চাহিদা
                (Applied Daily Crop Water Requirement):

                {bn_num(
                    result['crop_water_need'],
                    2
                )}
                mm/day

                ET0 × Kc
                """
            )


    # ========================================================
    # WATER BALANCE
    # ========================================================

    section_title(
        "পানির ভারসাম্য",
        "Water Balance"
    )


    with st.container(border=True):

        a, b, c, d = st.columns(4)


        a.metric(
            "কার্যকর বৃষ্টির পানি "
            "(Effective Rain)",
            f"{bn_num(result['effective_rain'], 2)} mm"
        )


        b.metric(
            "জমিতে থাকা পানি "
            "(Available Water)",
            f"{bn_num(result['available_water'], 2)} mm"
        )


        c.metric(
            "নিট সেচের প্রয়োজন "
            "(Net Irrigation)",
            f"{bn_num(result['net_water_needed'], 2)} mm"
        )


        d.metric(
            "মোট সেচের প্রয়োজন "
            "(Gross Irrigation)",
            f"{bn_num(result['gross_water_mm'], 2)} mm"
        )


    # ========================================================
    # RAINFALL MESSAGE
    # ========================================================

    if result["predicted_rain"] <= 0:

        st.warning(
            f"""
            আজ বৃষ্টির পরিমাণ ০ mm।

            ফসলের দৈনিক পানির চাহিদা:
            {bn_num(result['crop_water_need'], 2)} mm/day

            জমিতে থাকা পানি বাদ দেওয়ার পর
            নিট সেচের প্রয়োজন:
            {bn_num(result['net_water_needed'], 2)} mm।
            """
        )


    else:

        st.info(
            f"""
            ফসলের দৈনিক পানির চাহিদা:
            {bn_num(result['crop_water_need'], 2)} mm/day

            কার্যকর বৃষ্টি:
            {bn_num(result['effective_rain'], 2)} mm

            জমিতে থাকা পানি:
            {bn_num(result['available_water'], 2)} mm

            নিট সেচের প্রয়োজন:
            {bn_num(result['net_water_needed'], 2)} mm।
            """
        )


    # ========================================================
    # HOW MUCH WATER
    # ========================================================

    section_title(
        "কতটুকু পানি প্রয়োজন",
        "How Much Water"
    )


    with st.container(border=True):

        a, b, c = st.columns(3)


        a.metric(
            "লিটার (Liters)",
            f"{bn_num(result['water_liters'], 0, True)} L"
        )


        b.metric(
            "ঘনমিটার (Cubic Meter)",
            f"{bn_num(result['water_m3'], 2, True)} m³"
        )


        c.metric(
            "জমির আয়তন (Land Area)",
            f"{bn_num(result['area_m2'], 0, True)} m²"
        )


    # ========================================================
    # IF THERE IS NO RAIN TODAY
    # ========================================================
    #
    # Voice-এ এই কথাটা বলা হতো কিন্তু screen-এ লেখা ছিল না।
    # এখন voice এবং লেখা একই message ব্যবহার করছে।

    section_title(
        "আজ বৃষ্টি না হলে করণীয়",
        "If There Is No Rain Today"
    )


    no_rain_net_mm = data.get(
        "no_rain_net_mm"
    )


    if no_rain_net_mm is None:

        # পুরোনো session-এর result হলে এখানেই হিসাব করা হবে।

        no_rain_net_mm = max(
            float(result["crop_water_need"])
            -
            float(result["available_water"]),
            0.0
        )

        efficiency_ratio = (
            float(data.get("efficiency", 100))
            /
            100.0
        )

        no_rain_gross_mm = (
            no_rain_net_mm
            /
            efficiency_ratio
            if efficiency_ratio > 0
            else 0.0
        )

        no_rain_water_liters = (
            no_rain_gross_mm
            *
            float(result["area_m2"])
        )

    else:

        no_rain_gross_mm = float(
            data.get(
                "no_rain_gross_mm",
                0.0
            )
        )

        no_rain_water_liters = float(
            data.get(
                "no_rain_water_liters",
                0.0
            )
        )


    with st.container(border=True):

        a, b, c = st.columns(3)


        a.metric(
            "বৃষ্টি ছাড়া নিট চাহিদা "
            "(Net Need without Rain)",
            f"{bn_num(no_rain_net_mm, 2)} mm"
        )


        b.metric(
            "বৃষ্টি ছাড়া মোট সেচ "
            "(Gross Irrigation without Rain)",
            f"{bn_num(no_rain_gross_mm, 2)} mm"
        )


        c.metric(
            "প্রয়োজনীয় পানি "
            "(Water Required)",
            f"{bn_num(no_rain_water_liters, 0, True)} L"
        )


        no_rain_message = data.get(
            "no_rain_message"
        )


        if no_rain_net_mm > 0:

            st.warning(
                no_rain_message
                or (
                    f"যদি আজ কোনো বৃষ্টি না হয়, তাহলে জমিতে থাকা পানি "
                    f"বাদ দেওয়ার পর প্রায় "
                    f"{bn_num(no_rain_gross_mm, 1)} মিলিমিটার অথবা "
                    f"{bn_num(no_rain_water_liters, 0, True)} লিটার "
                    f"পানি সেচ দিতে হবে।"
                )
            )


            st.caption(
                "এই হিসাবে আজকের বৃষ্টির পূর্বাভাস ধরা হয়নি। "
                "শুধু জমিতে থাকা পানি বাদ দেওয়া হয়েছে।"
            )


        else:

            st.success(
                no_rain_message
                or (
                    "যদি আজ কোনো বৃষ্টি না হয়, তবুও জমিতে থাকা পানি "
                    "ফসলের বর্তমান দৈনিক পানির চাহিদা পূরণ করতে যথেষ্ট। "
                    "অতিরিক্ত সেচের প্রয়োজন হবে না।"
                )
            )


    # ========================================================
    # EXISTING WATER
    # ========================================================

    section_title(
        "জমিতে থাকা পানির তথ্য",
        "Existing Water Information"
    )


    with st.container(border=True):

        a, b, c = st.columns(3)


        a.metric(
            "পানির গভীরতা (Water Depth)",
            f"{bn_num(data['existing_water'], 1)} mm"
        )


        b.metric(
            "আনুমানিক মোট পানি "
            "(Estimated Total Water)",
            f"{bn_num(data['existing_water_liters'], 0, True)} L"
        )


        c.metric(
            "আনুমানিক পানির পরিমাণ "
            "(Estimated Volume)",
            f"{bn_num(data['existing_water_m3'], 2, True)} m³"
        )


        st.caption(
            f"""
            ব্যবহৃত পরিমাপ:
            {data['water_measurement']}।

            এটি একটি আনুমানিক হিসাব।
            """
        )


    # ========================================================
    # SMART RECOMMENDATION
    # ========================================================

    section_title(
        "স্মার্ট পরামর্শ",
        "Smart Recommendation"
    )


    recommendations = []


    if result["status"] == "NO_IRRIGATION":

        recommendations.append(
            "আজ অতিরিক্ত সেচ দেওয়ার প্রয়োজন নেই।"
        )

        recommendations.append(
            "জমিতে থাকা পানি এবং কার্যকর বৃষ্টির পানি "
            "ফসলের বর্তমান পানির চাহিদা পূরণের জন্য যথেষ্ট।"
        )


    elif result["status"] == "LOW":

        recommendations.append(
            "অল্প পরিমাণ সেচ দিন।"
        )


    elif result["status"] == "MEDIUM":

        recommendations.append(
            "মাঝারি পরিমাণ সেচ দেওয়া ভালো হবে।"
        )


    else:

        recommendations.append(
            "আজ ফসলের পানির চাহিদা বেশি। "
            "পর্যাপ্ত সেচ দিন।"
        )


    # Voice-এ বলা "বৃষ্টি না হলে করণীয়" পরামর্শেও রাখা হলো।
    if data.get("no_rain_message"):

        recommendations.append(
            data["no_rain_message"]
        )


    if data["predicted_rain"] >= 20:

        recommendations.append(
            "বৃষ্টির পরিমাণ বেশি হতে পারে। "
            "সেচ দেওয়ার আগে বৃষ্টির পরিস্থিতি বিবেচনা করুন।"
        )


    if (
        data["existing_water"]
        >=
        result["crop_water_need"]
    ):

        recommendations.append(
            "জমিতে আগে থেকেই পর্যাপ্ত পানি আছে। "
            "অতিরিক্ত পানি জমে থাকলে ফসলের ক্ষতি হতে পারে।"
        )


    if data["soil_type"].startswith(
        "বেলে"
    ):

        recommendations.append(
            "বেলে মাটিতে পানি দ্রুত নিচে চলে যায়। "
            "প্রয়োজন হলে একবারে বেশি পানি না দিয়ে "
            "ভাগ করে সেচ দিন।"
        )


    if data["soil_type"].startswith(
        "এঁটেল"
    ):

        recommendations.append(
            "এঁটেল মাটি পানি বেশি সময় ধরে রাখে। "
            "সেচ দেওয়ার আগে জমিতে পানি জমে আছে কিনা "
            "পরীক্ষা করুন।"
        )


    if data["irrigation_method"].startswith(
        "ড্রিপ"
    ):

        recommendations.append(
            "ড্রিপ সেচ পানি সাশ্রয়ে কার্যকর এবং "
            "নিয়ন্ত্রিতভাবে পানি সরবরাহ করতে সাহায্য করে।"
        )


    if "agriculture_show_recommendations" not in st.session_state:

        st.session_state[
            "agriculture_show_recommendations"
        ] = False


    recommendation_clicked = st.button(
        "স্মার্ট পরামর্শ দেখুন ও শুনুন "
        "(Show & Listen to Smart Recommendations)",
        use_container_width=True,
        key="agriculture_recommendation_button"
    )


    if recommendation_clicked:

        st.session_state[
            "agriculture_show_recommendations"
        ] = True

        # একই পরামর্শ আবার শুনতে চাইলেও যেন বাজে।
        reset_voice_hash()

        agriculture_recommendation_voice(
            recommendations
        )


    if st.session_state.get(
        "agriculture_show_recommendations",
        False
    ):

        with st.container(border=True):

            for rec in recommendations:

                st.write(
                    f"• {rec}"
                )


    # ========================================================
    # CALCULATION DETAILS
    # ========================================================

    with st.expander(
        "হিসাবের বিস্তারিত (Calculation Details)"
    ):

        st.write(
            f"ফসল (Crop): {data['crop_label']}"
        )


        st.write(
            f"মৌসুম (Season): {data['season_label']}"
        )


        st.write(
            f"হিসাবের তারিখ "
            f"(Calculation Date): "
            f"{data['calculation_date']}"
        )


        st.write(
            f"রোপণ/বপনের তারিখ "
            f"(Planting Date): "
            f"{data['actual_planting_date']}"
        )


        st.write(
            f"ফসলের বয়স "
            f"(Crop Age): "
            f"{bn_num(stage_info.get('day_of_crop'), 0)} / "
            f"{bn_num(stage_info.get('duration_days'), 0)} দিন"
        )


        st.write(
            f"স্বয়ংক্রিয়ভাবে নির্ধারিত পর্যায় "
            f"(Auto Stage): "
            f"{stage_info.get('stage_label', 'N/A')}"
        )


        st.write(
            f"ব্যবহৃত বৃদ্ধি পর্যায় "
            f"(Applied Growth Stage): "
            f"{data['crop_stage_label']}"
        )


        st.write(
            f"ET0: "
            f"{bn_num(result['et0_mm'], 2)} mm/day"
        )


        st.write(
            f"Kc: "
            f"{bn_num(result['kc'], 2)}"
        )


        st.write(
            f"Automatic ETc = ET0 × Kc = "
            f"{bn_num(result['automatic_etc_mm'], 2)} mm/day"
        )


        st.write(
            f"Applied Crop Water Requirement = "
            f"{bn_num(result['crop_water_need'], 2)} mm/day"
        )


        st.write(
            f"বৃষ্টির পূর্বাভাস "
            f"(Predicted Rainfall): "
            f"{bn_num(data['predicted_rain'], 2)} mm"
        )


        st.write(
            f"কার্যকর বৃষ্টি "
            f"(Effective Rainfall): "
            f"{bn_num(result['effective_rain'], 2)} mm"
        )


        st.write(
            f"জমিতে থাকা পানি "
            f"(Available Water): "
            f"{bn_num(result['available_water'], 2)} mm"
        )


        st.write(
            f"নিট সেচ "
            f"(Net Irrigation): "
            f"{bn_num(result['net_water_needed'], 2)} mm"
        )


        st.write(
            f"সেচ দক্ষতা "
            f"(Irrigation Efficiency): "
            f"{bn_num(data['efficiency'], 0)}%"
        )


        st.write(
            f"মোট সেচ "
            f"(Gross Irrigation): "
            f"{bn_num(result['gross_water_mm'], 2)} mm"
        )


        st.write(
            f"বৃষ্টি ছাড়া নিট সেচ "
            f"(Net Irrigation without Rain): "
            f"{bn_num(no_rain_net_mm, 2)} mm"
        )


        st.write(
            f"বৃষ্টি ছাড়া মোট সেচ "
            f"(Gross Irrigation without Rain): "
            f"{bn_num(no_rain_gross_mm, 2)} mm "
            f"/ "
            f"{bn_num(no_rain_water_liters, 0, True)} L"
        )


        st.write(
            f"জমির আয়তন "
            f"(Area): "
            f"{bn_num(result['area_m2'], 2, True)} m²"
        )


        st.write(
            f"মোট পানি "
            f"(Water Required): "
            f"{bn_num(result['water_liters'], 0, True)} L "
            f"/ "
            f"{bn_num(result['water_m3'], 2, True)} m³"
        )


        st.caption(
            "Formula: Automatic ETc = ET0 × Kc; "
            "Net Irrigation = max("
            "Applied Crop Water Requirement − "
            "Effective Rainfall − "
            "Available Water, 0); "
            "Gross Irrigation = "
            "Net Irrigation ÷ Efficiency; "
            "No-Rain Net = max("
            "Applied Crop Water Requirement − "
            "Available Water, 0)."
        )


    # ========================================================
    # WATER BALANCE CHART
    # ========================================================

    chart_df = pd.DataFrame({

        "বিভাগ (Category)": [

            "ফসলের পানির চাহিদা "
            "(Crop Water Need)",

            "কার্যকর বৃষ্টি "
            "(Effective Rain)",

            "জমিতে থাকা পানি "
            "(Available Water)",

            "নিট সেচ "
            "(Net Irrigation)",

            "মোট সেচ "
            "(Gross Irrigation)",

            "বৃষ্টি ছাড়া মোট সেচ "
            "(No Rain Gross)"
        ],

        "পানি (Water mm)": [

            result["crop_water_need"],

            result["effective_rain"],

            result["available_water"],

            result["net_water_needed"],

            result["gross_water_mm"],

            no_rain_gross_mm
        ]
    })


    fig = px.bar(
        chart_df,
        x="বিভাগ (Category)",
        y="পানি (Water mm)",
        title=(
            "কৃষি পানির ভারসাম্য "
            "(Agricultural Water Balance)"
        ),
        text_auto=".2f"
    )


    fig.update_layout(
        xaxis_title="",
        yaxis_title="পানির পরিমাণ (Water in mm)"
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# MAIN AGRICULTURE PAGE
# ============================================================

def show_agriculture(
    df,
    model,
    feature_columns,
    train_medians,
    history_days
):

    # ========================================================
    # STYLES
    # ========================================================
    # প্রতিটি rerun-এ inject করতে হবে।

    inject_agriculture_styles()


    # ========================================================
    # VOICE ON / OFF (page-এর একদম উপরে)
    # ========================================================

    agriculture_voice_toggle()


    # ========================================================
    # WELCOME
    # ========================================================

    start_agriculture_welcome()


    # ========================================================
    # PAGE HEADER
    # ========================================================

    st.title(
        "Smart Agriculture & Irrigation"
    )


    st.caption(
        "ফসল, মৌসুম, রোপণ/বপনের তারিখ, জমির পরিমাণ, "
        "মাটির ধরন, বৃষ্টির পূর্বাভাস এবং জমিতে থাকা পানি "
        "অনুযায়ী সেচের পানি হিসাব করুন।"
    )


    st.markdown(
        """
        <div class='agri-card'>
            <h3>Smart Irrigation Recommendation</h3>
            <p>
            ফসলের মৌসুম, প্রকৃত রোপণ/বপনের তারিখ,
            বৃদ্ধি পর্যায়, জমির পরিমাণ, বৃষ্টির পূর্বাভাস
            এবং ET0 ব্যবহার করে প্রয়োজনীয় সেচের পরিমাণ
            হিসাব করা হবে।
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # LOCATION & DATE + AUTOMATIC RAINFALL PREDICTION
    # ========================================================

    agriculture_location_date_section(
        df=df,
        model=model,
        feature_columns=feature_columns,
        train_medians=train_medians,
        history_days=history_days
    )


    # ========================================================
    # INPUT PANEL
    # ========================================================

    _agriculture_input_panel()


    # ========================================================
    # RESULT
    # ========================================================

    show_agriculture_result()


    # ========================================================
    # BROWSER VOICE PLAYER
    # ========================================================

    process_voice_queue()

    render_voice_player()
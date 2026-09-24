import io
import re
import hashlib

import streamlit as st
from gtts import gTTS


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def _init_voice_state():

    defaults = {
        "voice_audio": None,
        "voice_version": 0,
        "voice_rendered_version": -1,
        "voice_hash": None,
        "voice_enabled": True,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# GLOBAL VOICE ON / OFF SWITCH
# ============================================================

def is_voice_enabled():

    _init_voice_state()

    return bool(
        st.session_state.get(
            "voice_enabled",
            True
        )
    )


def set_voice_enabled(enabled):

    _init_voice_state()

    st.session_state["voice_enabled"] = bool(
        enabled
    )


# ============================================================
# BANGLA TEXT CLEANER
# ============================================================

def clean_voice_text(text):
    """
    TTS-এর জন্য English UI words বাদ দিয়ে
    Bangla-readable text তৈরি করে।

    Bangla text এবং Bangla/English digits রাখা হয়।
    """

    if text is None:
        return ""

    text = str(text)

    # --------------------------------------------------------
    # HTML / TAG REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # --------------------------------------------------------
    # URL REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # EMAIL REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"\S+@\S+\.\S+",
        " ",
        text
    )

    # --------------------------------------------------------
    # ENGLISH WORDS REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"[A-Za-z]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # COMMON SYMBOLS REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"[_/\\*]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # KEEP:
    #
    # Bangla Unicode
    # Bangla digits
    # English digits
    # spaces
    # common punctuation
    # --------------------------------------------------------

    text = re.sub(
        r"[^\u0980-\u09FF\u09E6-\u09EF0-9\s।,!?;:%\-–—()]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # REMOVE DASHES
    # --------------------------------------------------------

    text = re.sub(
        r"[-–—]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # REMOVE EMPTY BRACKETS
    # --------------------------------------------------------

    text = re.sub(
        r"\(\s*\)",
        " ",
        text
    )

    # --------------------------------------------------------
    # NORMALIZE SPACES
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# BANGLA NUMBER CONVERSION
# ============================================================

def _english_digits_to_bangla(text):

    table = str.maketrans(
        "0123456789",
        "০১২৩৪৫৬৭৮৯"
    )

    return text.translate(table)


# ============================================================
# PREPARE VOICE TEXT
# ============================================================

def _prepare_voice_text(text):

    text = clean_voice_text(text)

    if not text:
        return ""

    text = _english_digits_to_bangla(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# GENERATE MP3
# ============================================================

def _generate_audio(text):

    clean_text = _prepare_voice_text(
        text
    )

    if not clean_text:
        return None

    try:

        audio_buffer = io.BytesIO()

        tts = gTTS(
            text=clean_text,
            lang="bn",
            slow=False
        )

        tts.write_to_fp(
            audio_buffer
        )

        audio_buffer.seek(0)

        return audio_buffer.getvalue()

    except Exception:

        # gTTS / Internet failure হলে
        # Streamlit app crash করবে না।
        return None


# ============================================================
# SPEAK SEQUENCE
# ============================================================

def speak_sequence(
    messages,
    delay=0.0
):
    """
    একাধিক voice message একসাথে একটি Bangla audio-তে
    convert করে।

    একই text হলে duplicate audio generate করবে না।
    """

    _init_voice_state()

    # --------------------------------------------------------
    # GLOBAL VOICE SWITCH
    # --------------------------------------------------------

    if not is_voice_enabled():
        return

    if not messages:
        return

    # --------------------------------------------------------
    # PREPARE ALL MESSAGES
    # --------------------------------------------------------

    prepared_messages = []

    for message in messages:

        cleaned = _prepare_voice_text(
            message
        )

        if cleaned:
            prepared_messages.append(
                cleaned
            )

    if not prepared_messages:
        return

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    final_text = " । ".join(
        prepared_messages
    )

    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------

    voice_hash = hashlib.md5(
        final_text.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------------

    if (
        st.session_state.get(
            "voice_hash"
        )
        ==
        voice_hash
    ):
        return

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    audio = _generate_audio(
        final_text
    )

    if audio is None:
        return

    # --------------------------------------------------------
    # SAVE AUDIO
    # --------------------------------------------------------

    st.session_state[
        "voice_audio"
    ] = audio

    st.session_state[
        "voice_hash"
    ] = voice_hash

    st.session_state[
        "voice_version"
    ] = (
        st.session_state.get(
            "voice_version",
            0
        )
        + 1
    )


# ============================================================
# RESET VOICE HASH
# ============================================================

def reset_voice_hash():

    _init_voice_state()

    st.session_state[
        "voice_hash"
    ] = None


# ============================================================
# GROWTH STAGE VOICE
# ============================================================

def growth_stage_auto_voice(
    stage_label,
    next_instruction="মাটির ধরন নির্বাচন করুন"
):

    if not stage_label:
        return

    PAUSE_TOKEN = "।"

    messages = [

        (
            "স্বয়ংক্রিয়ভাবে আপনার ফসলের "
            f"পর্যায় নির্ধারণ করা হয়েছে {stage_label}।"
        ),

        (
            "আপনি চাইলে উপরের বৃদ্ধি পর্যায় "
            "থেকে অন্য পর্যায় নির্বাচন করতে পারেন।"
        )
    ]

    if next_instruction:

        messages.extend([
            PAUSE_TOKEN,
            PAUSE_TOKEN,
            PAUSE_TOKEN,
            next_instruction
        ])

    speak_sequence(
        messages,
        delay=0.10
    )


# ============================================================
# AGRICULTURE RESULT VOICE
# ============================================================

def agriculture_result_voice(

    irrigation_needed,

    water_liters=0,

    gross_irrigation=0,

    available_water=0,

    effective_rain=0,

    net_irrigation=0,

    no_rain_message="",

    irrigation_time_hours=None,

):

    """
    Agriculture Result Card-এর জন্য farmer-friendly voice।

    Technical ET0, Kc বা formula voice-এ বলা হবে না।
    """

    messages = []

    # ========================================================
    # 1. MAIN DECISION
    # ========================================================

    if irrigation_needed:

        messages.append(

            f"আজ আপনার জমিতে সেচ প্রয়োজন। "
            f"প্রায় {water_liters:.0f} লিটার পানি "
            f"অথবা {gross_irrigation:.1f} মিলিমিটার "
            f"সেচ দিতে হবে।"

        )

    else:

        messages.append(

            "আজ আপনার জমিতে অতিরিক্ত সেচ দেওয়ার "
            "প্রয়োজন নেই। জমিতে থাকা পানি এবং "
            "বৃষ্টির পানি বর্তমান প্রয়োজন মেটাতে যথেষ্ট।"

        )

    # ========================================================
    # 2. WATER BALANCE
    # ========================================================

    if irrigation_needed:

        messages.append(

            f"জমিতে থাকা পানি {available_water:.1f} মিলিমিটার "
            f"এবং কার্যকর বৃষ্টির পানি "
            f"{effective_rain:.1f} মিলিমিটার। "
            f"সব বাদ দেওয়ার পর পানির ঘাটতি "
            f"{net_irrigation:.1f} মিলিমিটার।"

        )

    # ========================================================
    # 3. NO RAIN DECISION
    # ========================================================

    if no_rain_message:

        messages.append(
            no_rain_message
        )

    # ========================================================
    # 4. IRRIGATION TIME
    # ========================================================

    if (
        irrigation_needed
        and irrigation_time_hours is not None
    ):

        try:

            irrigation_time_hours = float(
                irrigation_time_hours
            )

            if irrigation_time_hours > 0:

                messages.append(

                    "আপনার নির্বাচিত সেচ পদ্ধতি অনুযায়ী "
                    f"প্রায় {irrigation_time_hours:.1f} "
                    "ঘণ্টা সেচ দিতে হবে।"

                )

        except (
            TypeError,
            ValueError
        ):

            pass

    # ========================================================
    # FINAL VOICE
    # ========================================================

    speak_sequence(
        messages
    )


# ============================================================
# SMART RECOMMENDATION VOICE
# ============================================================

def agriculture_recommendation_voice(
    recommendations
):

    if not recommendations:
        return

    if isinstance(
        recommendations,
        str
    ):

        messages = [
            recommendations
        ]

    else:

        messages = list(
            recommendations
        )

    speak_sequence(
        messages
    )


# ============================================================
# SIMPLE SINGLE VOICE
# ============================================================

def speak(
    text,
    delay=0.0
):

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# PLAY VOICE
# ============================================================

def play_voice(
    text,
    delay=0.0
):

    speak(
        text,
        delay=delay
    )


# ============================================================
# WELCOME VOICE
# ============================================================

def play_welcome(text):

    speak_sequence(
        [text],
        delay=0.10
    )


# ============================================================
# SELECTION VOICE
# ============================================================

def selection_voice(

    text,

    value=None,

    key=None,

    delay=0.12

):

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# SECTION VOICE
# ============================================================

def section_voice(

    text,

    key=None,

    delay=0.10

):

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# PROCESS VOICE QUEUE
# ============================================================

def process_voice_queue():

    """
    Compatibility function.
    বর্তমানে আলাদা queue/thread দরকার নেই।
    """

    _init_voice_state()


# ============================================================
# BROWSER VOICE PLAYER
# ============================================================

def render_voice_player():

    """
    Browser-এর ভিতরে Bangla audio play করবে।

    Streamlit Cloud compatible.
    Server-side playsound ব্যবহার করা হচ্ছে না।
    """

    _init_voice_state()

    # --------------------------------------------------------
    # GLOBAL SWITCH
    # --------------------------------------------------------

    if not is_voice_enabled():
        return

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    audio = st.session_state.get(
        "voice_audio"
    )

    version = st.session_state.get(
        "voice_version",
        0
    )

    rendered_version = st.session_state.get(
        "voice_rendered_version",
        -1
    )

    if not audio:
        return

    # --------------------------------------------------------
    # SAME AUDIO SHOULD NOT PLAY AGAIN
    # --------------------------------------------------------

    if version == rendered_version:
        return

    # --------------------------------------------------------
    # MARK AS RENDERED
    # --------------------------------------------------------

    st.session_state[
        "voice_rendered_version"
    ] = version

    # --------------------------------------------------------
    # BROWSER AUDIO
    # --------------------------------------------------------

    st.audio(
        audio,
        format="audio/mp3",
        autoplay=True
    )


# ============================================================
# CANCEL CURRENT VOICE
# ============================================================

def cancel_pending_voice():

    _init_voice_state()

    st.session_state[
        "voice_audio"
    ] = None

    st.session_state[
        "voice_hash"
    ] = None

    st.session_state[
        "voice_version"
    ] = (
        st.session_state.get(
            "voice_version",
            0
        )
        + 1
    )


# ============================================================
# RESET VOICE STATE
# ============================================================

def reset_voice_state():

    _init_voice_state()

    st.session_state[
        "voice_audio"
    ] = None

    st.session_state[
        "voice_hash"
    ] = None

    st.session_state[
        "voice_version"
    ] = 0

    st.session_state[
        "voice_rendered_version"
    ] = -1
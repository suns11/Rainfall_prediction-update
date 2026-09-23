
"""Optional speech-to-text input helper for the Agriculture page.

This module is intentionally separate from services.voice.py.

It does not change the existing TTS / confirmation voice flow.
"""

import io
import re
from datetime import date
from difflib import SequenceMatcher

import streamlit as st
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr


BN_DIGITS = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789"
)

BN_MONTHS = {
    "জানুয়ারি": 1,
    "জানুয়ারি": 1,
    "ফেব্রুয়ারি": 2,
    "ফেব্রুয়ারি": 2,
    "মার্চ": 3,
    "এপ্রিল": 4,
    "মে": 5,
    "জুন": 6,
    "জুলাই": 7,
    "আগস্ট": 8,
    "সেপ্টেম্বর": 9,
    "অক্টোবর": 10,
    "নভেম্বর": 11,
    "ডিসেম্বর": 12,
}

NUMBER_WORDS = {
    "শূন্য": 0,
    "এক": 1,
    "দুই": 2,
    "দুইটা": 2,
    "দুটি": 2,
    "তিন": 3,
    "চার": 4,
    "পাঁচ": 5,
    "ছয়": 6,
    "ছয়": 6,
    "সাত": 7,
    "আট": 8,
    "নয়": 9,
    "নয়": 9,
    "দশ": 10,
    "এগারো": 11,
    "বারো": 12,
    "তেরো": 13,
    "চৌদ্দ": 14,
    "পনেরো": 15,
    "ষোল": 16,
    "সতেরো": 17,
    "আঠারো": 18,
    "উনিশ": 19,
    "বিশ": 20,
    "ত্রিশ": 30,
    "চল্লিশ": 40,
    "পঞ্চাশ": 50,
    "ষাট": 60,
    "সত্তর": 70,
    "আশি": 80,
    "নব্বই": 90,
    "একশ": 100,
    "একশো": 100,
}

EN_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


def _norm(text):
    text = str(text or "").strip().lower()
    text = text.translate(BN_DIGITS)
    text = re.sub(
        r"[।,;:!?]+",
        " ",
        text
    )
    text = re.sub(
        r"\s+",
        " ",
        text
    )
    return text


def _number_from_words(text):
    t = _norm(text)

    # Direct Arabic / Bangla digits, including decimals.
    m = re.search(
        r"\d+(?:\.\d+)?",
        t
    )

    if m:
        return float(m.group(0))

    words = t.split()
    values = []

    for word in words:
        if word in NUMBER_WORDS:
            values.append(NUMBER_WORDS[word])

        elif word in EN_NUMBER_WORDS:
            values.append(EN_NUMBER_WORDS[word])

    if not values:
        return None

    # Common speech forms:
    # "দুই দশমিক পাঁচ", "two point five".

    if "দশমিক" in words or "point" in words:

        marker = (
            "দশমিক"
            if "দশমিক" in words
            else "point"
        )

        i = words.index(marker)

        left = values[:i]
        right_words = words[i + 1:]
        right = []

        for w in right_words:
            if w in NUMBER_WORDS:
                right.append(
                    str(NUMBER_WORDS[w])
                )

            elif w in EN_NUMBER_WORDS:
                right.append(
                    str(EN_NUMBER_WORDS[w])
                )

            elif w.isdigit():
                right.append(w)

        if left and right:
            return float(
                f"{sum(left)}.{''.join(right)}"
            )

    if 100 in values and len(values) > 1:
        total = 0
        current = 0

        for v in values:
            if v == 100:
                current = max(1, current) * 100
                total += current
                current = 0
            else:
                current += v

        return float(total + current)

    # "দুই দশ" is uncommon but this keeps
    # simple compound forms useful.
    return float(sum(values))


def parse_number(
    text,
    minimum=None,
    maximum=None
):
    value = _number_from_words(text)

    if value is None:
        raise ValueError(
            "সংখ্যাটি বোঝা যায়নি। আবার বলুন।"
        )

    if minimum is not None and value < minimum:
        raise ValueError(
            f"মানটি {minimum} এর চেয়ে কম হতে পারবে না।"
        )

    if maximum is not None and value > maximum:
        raise ValueError(
            f"মানটি {maximum} এর চেয়ে বেশি হতে পারবে না।"
        )

    return value


OPTION_SUGGESTION_LABELS = {
    "agriculture_weather_source": "বৃষ্টির তথ্যের উৎস",
    "agriculture_area_unit": "জমির একক",
    "agriculture_crop_select": "ফসল",
    "agriculture_season_select": "মৌসুম",
    "agriculture_growth_stage": "বৃদ্ধি পর্যায়",
    "agriculture_growth_stage_fallback": "বৃদ্ধি পর্যায়",
    "agriculture_out_of_season_stage": "বৃদ্ধি পর্যায়",
    "agriculture_soil_type": "মাটির ধরন",
    "agriculture_water_measurement": "পানির গভীরতার ধরন",
    "agriculture_water_requirement_method":
        "পানির চাহিদা নির্ধারণের পদ্ধতি",
    "agriculture_irrigation_method": "সেচ পদ্ধতি",
    "agriculture_reference_period": "সময়কাল",
}


def _clean_option_for_voice(option):
    """
    Keep the Bangla label and remove English text
    in parentheses.
    """

    text = str(option or "")

    text = re.sub(
        r"\([^)]*\)",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip(" -–—")

    return text


def _speak_option_suggestion(
    key,
    transcript,
    options
):
    """
    Speak valid options only when an option voice
    input does not match.
    """

    if not options:
        return

    try:
        # Imported lazily so services.voice_input stays
        # separate from the existing TTS module at import time.

        from services.voice import speak_sequence

        label = OPTION_SUGGESTION_LABELS.get(
            key,
            "এই অংশে"
        )

        spoken_options = [
            _clean_option_for_voice(option)
            for option in options
            if _clean_option_for_voice(option)
        ]

        if not spoken_options:
            return

        transcript_text = _clean_option_for_voice(
            transcript
        )

        message = (
            f"আপনি বলেছেন {transcript_text}। "
            f"{label} রয়েছে: "
            + ", ".join(spoken_options)
            + "। অনুগ্রহ করে তালিকা থেকে একটি নির্বাচন করুন।"
        )

        speak_sequence(
            [message],
            delay=0.05
        )

    except Exception:
        # Suggestion voice must never break
        # the Agriculture page.
        pass


def parse_option(text, options):
    if not options:
        raise ValueError(
            "এই field-এর option পাওয়া যায়নি।"
        )

    query = _norm(text)

    best = None
    best_score = 0.0

    for option in options:

        candidate = _norm(option)

        score = SequenceMatcher(
            None,
            query,
            candidate
        ).ratio()

        # Matching words is more reliable for
        # Bangla + English labels.

        q_words = set(query.split())
        c_words = set(candidate.split())

        if q_words and c_words:
            score = max(
                score,
                len(q_words & c_words)
                / len(q_words | c_words)
            )

        if query and query in candidate:
            score = max(score, 0.90)

        if score > best_score:
            best_score = score
            best = option

    if best is None or best_score < 0.34:
        raise ValueError(
            "কথাটি কোনো option-এর সাথে মেলানো যায়নি।"
        )

    return best


def parse_date(text):
    t = _norm(text)

    # YYYY-MM-DD / DD-MM-YYYY / DD/MM/YYYY

    nums = [
        int(x)
        for x in re.findall(
            r"\d+",
            t
        )
    ]

    if len(nums) >= 3:

        if nums[0] >= 1900:
            return date(
                nums[0],
                nums[1],
                nums[2]
            )

        if nums[2] >= 1900:
            return date(
                nums[2],
                nums[1],
                nums[0]
            )

    month = None

    for name, number in BN_MONTHS.items():
        if name in t:
            month = number
            break

    if month is None:

        english_months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        for name, number in english_months.items():
            if name in t:
                month = number
                break

    if month is None:
        raise ValueError(
            "মাস বোঝা যায়নি। যেমন: ১৫ সেপ্টেম্বর ২০২৬ বলুন।"
        )

    years = [
        n for n in nums
        if n >= 1900
    ]

    year = years[0] if years else None

    day_candidates = [
        n for n in nums
        if n != year and 1 <= n <= 31
    ]

    if year is None or not day_candidates:
        raise ValueError(
            "তারিখটি সম্পূর্ণ বোঝা যায়নি। "
            "দিন, মাস ও বছর বলুন।"
        )

    return date(
        year,
        month,
        day_candidates[0]
    )


def _parse(
    text,
    value_type,
    options=None,
    minimum=None,
    maximum=None
):
    if value_type == "number":
        return parse_number(
            text,
            minimum,
            maximum
        )

    if value_type == "option":
        return parse_option(
            text,
            options or []
        )

    if value_type == "date":
        return parse_date(text)

    return str(text).strip()


def prepare_voice_input(key):
    """
    Apply a value captured on the previous rerun
    before the widget is built.
    """

    pending_key = (
        f"voice_input_pending_{key}"
    )

    applied_key = (
        f"voice_input_applied_{key}"
    )

    if pending_key not in st.session_state:
        return False

    value, transcript = st.session_state.pop(
        pending_key
    )

    st.session_state[key] = value

    st.session_state[
        f"voice_input_transcript_{key}"
    ] = transcript

    st.session_state[applied_key] = True

    return True


def voice_input_widget(
    key,
    prompt,
    value_type="text",
    options=None,
    minimum=None,
    maximum=None,
):
    """
    Render one microphone control and capture
    the transcript/value.

    The target Streamlit widget value is applied
    on the next rerun, before the target widget
    is instantiated.

    This avoids Streamlit widget-state mutation
    errors and keeps normal typing/selection untouched.
    """

    result = mic_recorder(
        start_prompt="🎤 ভয়েসে বলুন",
        stop_prompt="⏹️ রেকর্ডিং বন্ধ করুন",
        just_once=True,
        use_container_width=False,
        format="wav",
        key=f"voice_input_mic_{key}",
    )

    if result and result.get("bytes"):

        try:
            recognizer = sr.Recognizer()

            with sr.AudioFile(
                io.BytesIO(result["bytes"])
            ) as source:

                audio = recognizer.record(source)

            transcript = recognizer.recognize_google(
                audio,
                language="bn-BD"
            )

            # Always keep the exact recognized speech visible,
            # even when it does not match an available option.

            st.session_state[
                f"voice_input_transcript_{key}"
            ] = transcript

            try:

                value = _parse(
                    transcript,
                    value_type,
                    options=options,
                    minimum=minimum,
                    maximum=maximum
                )

            except ValueError as exc:

                if value_type == "option":

                    _speak_option_suggestion(
                        key,
                        transcript,
                        options or []
                    )

                    st.warning(
                        f"{exc} "
                        "অনুগ্রহ করে উপরের তালিকা থেকে "
                        "একটি option বলুন।"
                    )

                else:
                    st.warning(str(exc))

                value = None

            if value is not None:

                st.session_state[
                    f"voice_input_pending_{key}"
                ] = (
                    value,
                    transcript
                )

                st.rerun()

        except sr.UnknownValueError:

            st.warning(
                "কথাটি পরিষ্কারভাবে বোঝা যায়নি। "
                "আবার ভয়েস দিন।"
            )

        except sr.RequestError:

            st.error(
                "ভয়েসকে লেখায় রূপান্তর করার সেবা "
                "এই মুহূর্তে পাওয়া যাচ্ছে না।"
            )

        except Exception as exc:

            st.warning(
                f"ভয়েস ইনপুট নেওয়া যায়নি: {exc}"
            )

    transcript = st.session_state.get(
        f"voice_input_transcript_{key}"
    )

    if transcript:
        st.caption(
            f"ভয়েসে যা বলা হয়েছে: {transcript}"
        )

    return st.session_state.pop(
        f"voice_input_applied_{key}",
        False
    )

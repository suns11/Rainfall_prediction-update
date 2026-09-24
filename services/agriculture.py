from pathlib import Path
from datetime import date, datetime
import pandas as pd
from services.voice import speak


# ============================================================
# DATA PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

CROP_REFERENCE_FILE = DATA_DIR / "01_bangladesh_crop_water_reference.csv"
KC_REFERENCE_FILE = DATA_DIR / "02_crop_kc_reference.csv"
CROP_CALENDAR_FILE = DATA_DIR / "03_bangladesh_crop_calendar.csv"
LOCATION_IWR_FILE = DATA_DIR / "04_bangladesh_location_iwr_reference.csv"


# ============================================================
# BANGLA / ENGLISH DISPLAY MAPS
# ============================================================

STAGE_LABELS = {
    "Initial": "প্রাথমিক পর্যায় (Initial)",
    "Development": "বৃদ্ধি পর্যায় (Development)",
    "Mid": "মধ্য পর্যায় (Mid)",
    "Late": "শেষ পর্যায় (Late)"
}

STAGE_FROM_LABEL = {
    value: key for key, value in STAGE_LABELS.items()
}


# ============================================================
# SOIL TYPES
# ============================================================

# Soil is used for information/advisory only.
# No arbitrary soil multiplier is applied in the irrigation calculation.

SOIL_TYPES = {

    "বেলে মাটি (Sandy Soil)": {
        "description": (
            "বেলে মাটিতে পানি দ্রুত নিচে চলে যেতে পারে। "
            "প্রয়োজন হলে একবারে বেশি পানি না দিয়ে ভাগ করে সেচ দেওয়া যেতে পারে।"
        )
    },

    "দোআঁশ মাটি (Loamy Soil)": {
        "description": (
            "দোআঁশ মাটির পানি ধারণক্ষমতা সাধারণত মাঝারি "
            "এবং ফসলের জন্য উপযোগী।"
        )
    },

    "এঁটেল মাটি (Clay Soil)": {
        "description": (
            "এঁটেল মাটি পানি তুলনামূলক বেশি সময় ধরে রাখতে পারে। "
            "সেচের আগে জমিতে পানি জমে আছে কিনা দেখা প্রয়োজন।"
        )
    }

}


# ============================================================
# WATER DEPTH CONVERSION
# ============================================================

WATER_DEPTH_OPTIONS = {

    "পানি নেই (No Water)": 0,

    "আধা আঙুল (Half Finger)": 8,

    "১ আঙুল (One Finger)": 15,

    "২ আঙুল (Two Fingers)": 30,

    "৩ আঙুল (Three Fingers)": 45,

    "৪ আঙুল (Four Fingers)": 60

}


# ============================================================
# BASIC HELPERS
# ============================================================

def _read_csv(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required agriculture data file not found: {path}"
        )

    return pd.read_csv(path)


def _safe_float(value):

    if value is None or pd.isna(value):
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def _parse_mm_dd(mm_dd, year):

    if mm_dd is None or pd.isna(mm_dd):
        return None

    text = str(mm_dd).strip()

    if not text:
        return None

    try:
        month, day = map(int, text.split("-"))
        return date(year, month, day)

    except (TypeError, ValueError):
        return None


def _stage_from_progress(progress):

    if progress <= 0.20:
        return "Initial"

    elif progress <= 0.45:
        return "Development"

    elif progress <= 0.80:
        return "Mid"

    return "Late"


# ============================================================
# CSV LOADING
# ============================================================

def load_crop_reference():
    return _read_csv(CROP_REFERENCE_FILE)


def load_kc_reference():
    return _read_csv(KC_REFERENCE_FILE)


def load_crop_calendar():
    return _read_csv(CROP_CALENDAR_FILE)


def load_location_iwr_reference():

    if not LOCATION_IWR_FILE.exists():

        return pd.DataFrame(
            columns=[
                "Crop_or_Season",
                "Location",
                "Net_Irrigation_Reference_mm",
                "Source_Type",
                "Source"
            ]
        )

    return pd.read_csv(LOCATION_IWR_FILE)


# ============================================================
# CROP / SEASON LOOKUP
# ============================================================

def get_crop_options():

    df = load_crop_reference()

    options = {}

    for _, row in df.drop_duplicates(subset=["Crop"]).iterrows():

        crop_en = str(row["Crop"]).strip()

        crop_bn = (
            str(row["Crop_Bangla"]).strip()
            if pd.notna(row.get("Crop_Bangla"))
            else crop_en
        )

        label = f"{crop_bn} ({crop_en})"

        options[label] = crop_en

    return options


def get_season_options(crop):

    df = load_crop_reference()

    rows = df[
        df["Crop"].astype(str).str.strip().str.lower()
        ==
        str(crop).strip().lower()
    ].copy()

    options = {}

    for _, row in rows.iterrows():

        season_en = str(row["Season"]).strip()

        season_bn = (
            str(row["Season_Bangla"]).strip()
            if pd.notna(row.get("Season_Bangla"))
            else season_en
        )

        label = f"{season_bn} ({season_en})"

        options[label] = season_en

    return options


def get_crop_reference(crop, season):

    df = load_crop_reference()

    rows = df[
        (
            df["Crop"].astype(str).str.strip().str.lower()
            ==
            str(crop).strip().lower()
        )
        &
        (
            df["Season"].astype(str).str.strip().str.lower()
            ==
            str(season).strip().lower()
        )
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    return {
        "crop": row.get("Crop"),
        "crop_bangla": row.get("Crop_Bangla"),
        "season": row.get("Season"),
        "season_bangla": row.get("Season_Bangla"),
        "crop_group": row.get("Crop_Group"),
        "growing_period": row.get("Growing_Period"),
        "cultivar": row.get("Cultivar"),
        "start_mm_dd": row.get("Start_MM_DD"),
        "end_mm_dd": row.get("End_MM_DD"),
        "duration_days": _safe_float(
            row.get("Reference_Duration_Days")
        ),
        "cwr_mm": _safe_float(
            row.get("Bangladesh_Study_CWR_mm")
        ),
        "iwr_mm": _safe_float(
            row.get("Bangladesh_Study_IWR_mm")
        ),
        "source_type": row.get("Source_Type"),
        "source": row.get("Source"),
        "database_status": row.get("Database_Status")
    }


# ============================================================
# CROP CALENDAR
# ============================================================

def get_crop_calendar_record(crop, season):

    df = load_crop_calendar()

    rows = df[
        (
            df["Crop"].astype(str).str.strip().str.lower()
            ==
            str(crop).strip().lower()
        )
        &
        (
            df["Season"].astype(str).str.strip().str.lower()
            ==
            str(season).strip().lower()
        )
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    return {
        "crop": row.get("Crop"),
        "season": row.get("Season"),
        "cultivar": row.get("Cultivar"),
        "start_mm_dd": row.get("Start_MM_DD"),
        "end_mm_dd": row.get("End_MM_DD"),
        "duration_days": _safe_float(
            row.get("Reference_Duration_Days")
        ),
        "source_type": row.get("Source_Type"),
        "source": row.get("Source")
    }


def _make_reference_interval(
    start_mm_dd,
    end_mm_dd,
    start_year
):

    start_date = _parse_mm_dd(
        start_mm_dd,
        start_year
    )

    if start_date is None:
        return None, None

    end_same_year = _parse_mm_dd(
        end_mm_dd,
        start_year
    )

    if end_same_year is None:
        return start_date, None

    # If end month/day comes before start month/day,
    # the crop season crosses into the next calendar year.
    if end_same_year < start_date:

        end_date = _parse_mm_dd(
            end_mm_dd,
            start_year + 1
        )

    else:

        end_date = end_same_year

    return start_date, end_date


def resolve_reference_season(
    crop,
    season,
    calculation_date
):

    calendar = get_crop_calendar_record(
        crop,
        season
    )

    if not calendar:

        return {
            "available": False,
            "in_season": None,
            "start_date": None,
            "end_date": None,
            "calendar": None
        }

    start_raw = calendar.get("start_mm_dd")
    end_raw = calendar.get("end_mm_dd")

    if (
        start_raw is None
        or pd.isna(start_raw)
        or end_raw is None
        or pd.isna(end_raw)
    ):

        return {
            "available": False,
            "in_season": None,
            "start_date": None,
            "end_date": None,
            "calendar": calendar
        }

    if isinstance(calculation_date, datetime):
        calculation_date = calculation_date.date()

    candidate_intervals = []

    for start_year in [
        calculation_date.year - 1,
        calculation_date.year,
        calculation_date.year + 1
    ]:

        start_date, end_date = _make_reference_interval(
            start_raw,
            end_raw,
            start_year
        )

        if start_date and end_date:

            candidate_intervals.append(
                (start_date, end_date)
            )

            if start_date <= calculation_date <= end_date:

                return {
                    "available": True,
                    "in_season": True,
                    "start_date": start_date,
                    "end_date": end_date,
                    "calendar": calendar
                }

    # If date is outside the reference season, return the closest interval
    # so the UI can show the correct reference period.
    if candidate_intervals:

        closest = min(
            candidate_intervals,
            key=lambda item: min(
                abs((calculation_date - item[0]).days),
                abs((calculation_date - item[1]).days)
            )
        )

        return {
            "available": True,
            "in_season": False,
            "start_date": closest[0],
            "end_date": closest[1],
            "calendar": calendar
        }

    return {
        "available": False,
        "in_season": None,
        "start_date": None,
        "end_date": None,
        "calendar": calendar
    }


# ============================================================
# GROWTH STAGE
# ============================================================

def determine_growth_stage(
    crop,
    season,
    calculation_date,
    planting_date=None,
    use_actual_planting_date=False
):

    calendar = get_crop_calendar_record(
        crop,
        season
    )

    if not calendar:

        return {
            "status": "NO_CALENDAR",
            "available": False,
            "stage": None,
            "stage_label": None,
            "day_of_crop": None,
            "duration_days": None,
            "progress": None,
            "reference_start_date": None,
            "reference_end_date": None,
            "message": "এই ফসলের জন্য crop calendar data পাওয়া যায়নি।"
        }

    duration_days = calendar.get(
        "duration_days"
    )

    if not duration_days or duration_days <= 0:

        return {
            "status": "NO_DURATION",
            "available": False,
            "stage": None,
            "stage_label": None,
            "day_of_crop": None,
            "duration_days": duration_days,
            "progress": None,
            "reference_start_date": None,
            "reference_end_date": None,
            "message": "এই ফসলের জন্য reference duration পাওয়া যায়নি।"
        }

    if isinstance(calculation_date, datetime):
        calculation_date = calculation_date.date()

    # ========================================================
    # ACTUAL FARMER PLANTING / TRANSPLANTING DATE
    # ========================================================

    if use_actual_planting_date:

        if planting_date is None:

            return {
                "status": "INVALID_PLANTING_DATE",
                "available": False,
                "stage": None,
                "stage_label": None,
                "day_of_crop": None,
                "duration_days": duration_days,
                "progress": None,
                "reference_start_date": None,
                "reference_end_date": None,
                "message": "প্রকৃত রোপণ/বপনের তারিখ নির্বাচন করুন।"
            }

        if isinstance(planting_date, datetime):
            planting_date = planting_date.date()

        if planting_date > calculation_date:

            return {
                "status": "FUTURE_PLANTING_DATE",
                "available": False,
                "stage": None,
                "stage_label": None,
                "day_of_crop": None,
                "duration_days": duration_days,
                "progress": None,
                "reference_start_date": None,
                "reference_end_date": None,
                "message": "রোপণ/বপনের তারিখ হিসাবের তারিখের পরে হতে পারে না।"
            }

        day_of_crop = (
            calculation_date - planting_date
        ).days + 1

        if day_of_crop > int(round(duration_days)):

            return {
                "status": "CROP_CYCLE_COMPLETE",
                "available": False,
                "stage": None,
                "stage_label": None,
                "day_of_crop": day_of_crop,
                "duration_days": duration_days,
                "progress": (
                    day_of_crop / float(duration_days)
                ),
                "reference_start_date": None,
                "reference_end_date": None,
                "message": (
                    "প্রকৃত রোপণ/বপনের তারিখ অনুযায়ী reference crop "
                    "duration শেষ হয়ে গেছে। তারিখগুলো আবার যাচাই করুন।"
                )
            }

        progress = (
            day_of_crop / float(duration_days)
        )

        stage = _stage_from_progress(
            progress
        )

        reference = resolve_reference_season(
            crop,
            season,
            calculation_date
        )

        planting_reference = resolve_reference_season(
            crop,
            season,
            planting_date
        )

        warning = None

        if (
            planting_reference.get("available")
            and
            planting_reference.get("in_season") is False
        ):

            warning = (
                "প্রকৃত রোপণ/বপনের তারিখ reference crop calendar-এর বাইরে। "
                "তবুও farmer-provided date অনুযায়ী stage হিসাব করা হয়েছে।"
            )

        return {
            "status": "IN_SEASON_ACTUAL_DATE",
            "available": True,
            "stage": stage,
            "stage_label": STAGE_LABELS[stage],
            "day_of_crop": day_of_crop,
            "duration_days": duration_days,
            "progress": progress,
            "reference_start_date": reference.get("start_date"),
            "reference_end_date": reference.get("end_date"),
            "message": (
                "কৃষকের দেওয়া প্রকৃত রোপণ/বপনের তারিখ অনুযায়ী "
                "Growth Stage নির্ধারণ করা হয়েছে।"
            ),
            "warning": warning,
            "planting_date": planting_date
        }

    # ========================================================
    # REFERENCE CROP CALENDAR DATE
    # ========================================================

    reference = resolve_reference_season(
        crop,
        season,
        calculation_date
    )

    if not reference.get("available"):

        return {
            "status": "NO_CALENDAR_DATES",
            "available": False,
            "stage": None,
            "stage_label": None,
            "day_of_crop": None,
            "duration_days": duration_days,
            "progress": None,
            "reference_start_date": None,
            "reference_end_date": None,
            "message": (
                "এই ফসলের জন্য automatic Growth Stage নির্ধারণের মতো "
                "reference start/end date পাওয়া যায়নি।"
            )
        }

    if not reference.get("in_season"):

        return {
            "status": "OUT_OF_SEASON",
            "available": False,
            "stage": None,
            "stage_label": None,
            "day_of_crop": None,
            "duration_days": duration_days,
            "progress": None,
            "reference_start_date": reference.get("start_date"),
            "reference_end_date": reference.get("end_date"),
            "message": (
                "নির্বাচিত তারিখটি এই ফসলের reference growing "
                "season-এর বাইরে।"
            )
        }

    start_date = reference["start_date"]

    day_of_crop = (
        calculation_date - start_date
    ).days + 1

    # Calendar end date and reference duration can differ slightly.
    # Stage is calculated using the reference duration.
    progress = min(
        day_of_crop / float(duration_days),
        1.0
    )

    stage = _stage_from_progress(
        progress
    )

    return {
        "status": "IN_SEASON_REFERENCE",
        "available": True,
        "stage": stage,
        "stage_label": STAGE_LABELS[stage],
        "day_of_crop": day_of_crop,
        "duration_days": duration_days,
        "progress": progress,
        "reference_start_date": reference.get("start_date"),
        "reference_end_date": reference.get("end_date"),
        "message": (
            "Reference crop calendar অনুযায়ী Growth Stage "
            "স্বয়ংক্রিয়ভাবে নির্ধারণ করা হয়েছে।"
        ),
        "warning": None,
        "planting_date": start_date
    }


# ============================================================
# Kc LOOKUP
# ============================================================

def get_kc(crop, growth_stage):

    df = load_kc_reference()

    rows = df[
        (
            df["Crop"].astype(str).str.strip().str.lower()
            ==
            str(crop).strip().lower()
        )
        &
        (
            df["Growth_Stage"].astype(str).str.strip().str.lower()
            ==
            str(growth_stage).strip().lower()
        )
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    return {
        "kc": float(row["Kc"]),
        "source_type": row.get("Kc_Source_Type"),
        "source": row.get("Kc_Source")
    }


# ============================================================
# LOCATION-WISE SEASONAL IWR REFERENCE
# ============================================================

def _location_reference_key(crop, season):

    if str(crop).strip().lower() == "rice":
        return str(season).strip()

    return str(crop).strip()


def get_location_options(crop, season):

    df = load_location_iwr_reference()

    if df.empty:
        return []

    key = _location_reference_key(
        crop,
        season
    )

    rows = df[
        df["Crop_or_Season"].astype(str).str.strip().str.lower()
        ==
        key.lower()
    ]

    return sorted(
        rows["Location"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def get_location_iwr_reference(
    crop,
    season,
    location
):

    df = load_location_iwr_reference()

    if df.empty or not location:
        return None

    key = _location_reference_key(
        crop,
        season
    )

    rows = df[
        (
            df["Crop_or_Season"].astype(str).str.strip().str.lower()
            ==
            key.lower()
        )
        &
        (
            df["Location"].astype(str).str.strip().str.lower()
            ==
            str(location).strip().lower()
        )
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    return {
        "crop_or_season": row.get("Crop_or_Season"),
        "location": row.get("Location"),
        "net_iwr_reference_mm": _safe_float(
            row.get("Net_Irrigation_Reference_mm")
        ),
        "source_type": row.get("Source_Type"),
        "source": row.get("Source")
    }


# ============================================================
# AREA CONVERSION
# ============================================================

def convert_area_to_m2(
    land_area,
    area_unit
):

    if area_unit == "শতক (Decimal)":
        return land_area * 40.4686

    elif area_unit == "একর (Acre)":
        return land_area * 4046.8564

    elif area_unit == "হেক্টর (Hectare)":
        return land_area * 10000

    else:
        return land_area


# ============================================================
# WATER DEPTH TO MM
# ============================================================

def convert_water_depth_to_mm(
    water_measurement,
    custom_depth_cm=0.0
):

    if water_measurement == "নিজে পরিমাপ দিন (Custom Measurement)":
        return custom_depth_cm * 10

    return WATER_DEPTH_OPTIONS.get(
        water_measurement,
        0
    )


# ============================================================
# CALCULATE EXISTING WATER VOLUME
# ============================================================

def calculate_existing_water_volume(
    area_m2,
    water_depth_mm
):

    # 1 mm water over 1 square meter = 1 liter

    water_liters = (
        area_m2 * water_depth_mm
    )

    water_m3 = (
        water_liters / 1000
    )

    return {
        "water_liters": water_liters,
        "water_m3": water_m3
    }


# ============================================================
# EFFECTIVE RAINFALL
# ============================================================

def calculate_effective_rainfall(
    predicted_rain_mm
):

    predicted_rain_mm = max(
        float(predicted_rain_mm),
        0.0
    )

    # Simplified planning assumption.
    # This is not claimed as a universal physical law.

    if predicted_rain_mm <= 5:

        return predicted_rain_mm * 0.90

    elif predicted_rain_mm <= 20:

        return predicted_rain_mm * 0.80

    else:

        return predicted_rain_mm * 0.65


# ============================================================
# CALCULATE IRRIGATION
# ============================================================

def calculate_irrigation(

    land_area,

    area_unit,

    crop_name,

    crop_stage,

    soil_type,

    existing_water_mm,

    predicted_rain_mm,

    et0_value,

    irrigation_efficiency,

    manual_crop_water_need_mm=None

):

    # ========================================================
    # AREA
    # ========================================================

    area_m2 = convert_area_to_m2(
        land_area,
        area_unit
    )

    # ========================================================
    # Kc
    # ========================================================

    kc_record = get_kc(
        crop_name,
        crop_stage
    )

    if kc_record is None:

        raise ValueError(
            f"Kc value পাওয়া যায়নি: Crop={crop_name}, "
            f"Stage={crop_stage}"
        )

    kc = kc_record["kc"]

    # ========================================================
    # AUTOMATIC CROP WATER REQUIREMENT
    # ETc = ET0 × Kc
    # ========================================================

    et0_mm = max(
        float(et0_value),
        0.0
    )

    automatic_etc_mm = (
        et0_mm * kc
    )

    # ========================================================
    # WATER REQUIREMENT METHOD
    # ========================================================

    if manual_crop_water_need_mm is not None:

        crop_water_need = max(
            float(manual_crop_water_need_mm),
            0.0
        )

        water_requirement_method = "MANUAL"

    else:

        crop_water_need = automatic_etc_mm

        water_requirement_method = "AUTOMATIC_ETC"

    # ========================================================
    # EFFECTIVE RAINFALL
    # ========================================================

    effective_rain = calculate_effective_rainfall(
        predicted_rain_mm
    )

    # ========================================================
    # AVAILABLE WATER
    # ========================================================

    available_water = max(
        float(existing_water_mm),
        0.0
    )

    # ========================================================
    # NET IRRIGATION REQUIREMENT
    # ========================================================

    net_water_needed = max(
        crop_water_need
        -
        effective_rain
        -
        available_water,
        0
    )

    # ========================================================
    # IRRIGATION EFFICIENCY
    # ========================================================

    efficiency = max(
        min(
            float(irrigation_efficiency) / 100,
            1.0
        ),
        0.10
    )

    # ========================================================
    # GROSS IRRIGATION REQUIREMENT
    # ========================================================

    gross_water_mm = (
        net_water_needed / efficiency
    )

    # ========================================================
    # WATER VOLUME
    # ========================================================

    # 1 mm water over 1 m² = 1 liter

    water_liters = (
        gross_water_mm * area_m2
    )

    water_m3 = (
        water_liters / 1000
    )

    # ========================================================
    # STATUS
    # ========================================================

    if net_water_needed <= 0:

        status = "NO_IRRIGATION"

        status_bn = "আজ সেচ প্রয়োজন নেই"

        status_en = "No irrigation needed today"

    elif net_water_needed <= 3:

        status = "LOW"

        status_bn = "অল্প পরিমাণ সেচ দিন"

        status_en = "Light irrigation recommended"

    elif net_water_needed <= 7:

        status = "MEDIUM"

        status_bn = "মাঝারি পরিমাণ সেচ দিন"

        status_en = "Moderate irrigation recommended"

    else:

        status = "HIGH"

        status_bn = "বেশি পরিমাণ সেচ প্রয়োজন"

        status_en = "High irrigation requirement"

    return {

        "area_m2": area_m2,

        "et0_mm": et0_mm,

        "kc": kc,

        "automatic_etc_mm": automatic_etc_mm,

        "etc_mm": automatic_etc_mm,

        "crop_water_need": crop_water_need,

        "water_requirement_method": water_requirement_method,

        "predicted_rain": max(
            float(predicted_rain_mm),
            0.0
        ),

        "effective_rain": effective_rain,

        "existing_water": available_water,

        "available_water": available_water,

        "net_water_needed": net_water_needed,

        "gross_water_mm": gross_water_mm,

        "irrigation_efficiency": efficiency * 100,

        "water_liters": water_liters,

        "water_m3": water_m3,

        "kc_source_type": kc_record.get("source_type"),

        "kc_source": kc_record.get("source"),

        "soil_type": soil_type,

        "status": status,

        "status_bn": status_bn,

        "status_en": status_en

    }


# ============================================================
# IRRIGATION METHOD WATER FLOW
# ============================================================
#
# NOTE:
# এগুলো representative/default planning values।
# নির্দিষ্ট pump, dripper বা sprinkler-এর guaranteed discharge নয়।
# Actual field discharge ভিন্ন হতে পারে।
#
# এই section calculate_irrigation()-এর calculation logic পরিবর্তন করে না।
# calculate_irrigation() থেকে পাওয়া final water_liters ব্যবহার করে
# irrigation method অনুযায়ী আনুমানিক সময় হিসাব করা হয়.
# ============================================================

IRRIGATION_METHODS = {

    "শ্যালো পাম্প দিয়ে সেচ (Shallow Pump)": {
        "type": "FIXED_FLOW",
        "default_flow_lph": 60000.0,
        "default_efficiency": 60
    },

    "ডিপ টিউবওয়েল দিয়ে সেচ (Deep Tubewell)": {
        "type": "FIXED_FLOW",
        "default_flow_lph": 180000.0,
        "default_efficiency": 60
    },

    "ড্রিপ/ফোঁটা ফোঁটা সেচ (Drip Irrigation)": {
        "type": "PER_DRIPPER",
        "default_flow_per_unit_lph": 3.4,
        "default_efficiency": 90
    },

    "স্প্রিংকলার সেচ (Sprinkler Irrigation)": {
        "type": "PER_SPRINKLER",
        "default_flow_per_unit_lph": None,
        "default_efficiency": 75
    }

}


def get_irrigation_method_options():
    return list(IRRIGATION_METHODS.keys())


def get_irrigation_method_config(method_label):
    return IRRIGATION_METHODS.get(method_label)


def calculate_irrigation_time(
    water_liters,
    irrigation_needed,
    method_label,
    num_drippers=None,
    num_sprinklers=None,
    flow_per_sprinkler_lph=None
):
    """
    calculate_irrigation()-এর final water_liters ব্যবহার করে
    selected irrigation method অনুযায়ী আনুমানিক irrigation time
    হিসাব করে।

    এখানে ET0, Kc, rainfall, existing water বা মূল irrigation
    calculation পরিবর্তন করা হয় না।
    """

    result = {
        "available": False,
        "total_flow_lph": None,
        "hours": None,
        "needs_flow_input": False,
        "method_type": None,
        "num_units": None,
        "flow_per_unit_lph": None
    }

    # সেচ প্রয়োজন না হলে সময়ও প্রয়োজন নেই।
    if not irrigation_needed:
        return result

    # Water amount valid কি না।
    try:
        water_liters = float(water_liters)
    except (TypeError, ValueError):
        return result

    if water_liters <= 0:
        return result

    config = IRRIGATION_METHODS.get(method_label)

    if config is None:
        return result

    method_type = config.get("type")

    result["method_type"] = method_type

    # ========================================================
    # SHALLOW PUMP / DEEP TUBEWELL
    # ========================================================

    if method_type == "FIXED_FLOW":

        total_flow_lph = _safe_float(
            config.get("default_flow_lph")
        )

        if total_flow_lph is None or total_flow_lph <= 0:
            return result

    # ========================================================
    # DRIP
    # ========================================================

    elif method_type == "PER_DRIPPER":

        try:
            num_drippers = float(num_drippers)
        except (TypeError, ValueError):
            num_drippers = 0

        if num_drippers <= 0:

            result["needs_flow_input"] = True

            return result

        flow_per_unit = _safe_float(
            config.get("default_flow_per_unit_lph")
        )

        if flow_per_unit is None or flow_per_unit <= 0:
            return result

        total_flow_lph = (
            num_drippers * flow_per_unit
        )

        result["num_units"] = num_drippers
        result["flow_per_unit_lph"] = flow_per_unit

    # ========================================================
    # SPRINKLER
    # ========================================================

    elif method_type == "PER_SPRINKLER":

        try:
            num_sprinklers = float(num_sprinklers)
        except (TypeError, ValueError):
            num_sprinklers = 0

        try:
            flow_per_sprinkler_lph = float(
                flow_per_sprinkler_lph
            )
        except (TypeError, ValueError):
            flow_per_sprinkler_lph = 0

        if (
            num_sprinklers <= 0
            or flow_per_sprinkler_lph <= 0
        ):

            result["needs_flow_input"] = True

            return result

        total_flow_lph = (
            num_sprinklers
            *
            flow_per_sprinkler_lph
        )

        result["num_units"] = num_sprinklers
        result["flow_per_unit_lph"] = (
            flow_per_sprinkler_lph
        )

    else:

        return result

    # ========================================================
    # FINAL TIME
    # ========================================================

    if total_flow_lph <= 0:
        return result

    irrigation_hours = (
        water_liters
        /
        total_flow_lph
    )

    result["available"] = True
    result["total_flow_lph"] = total_flow_lph
    result["hours"] = irrigation_hours

    return result
import os
import pandas as pd
import requests


from config.settings import (
    OPEN_METEO_ARCHIVE_URL,
    TIMEZONE
)


CSV_PATH = "data/bangladesh_weather_stations_FINAL.csv"


CSV_COLUMNS = [
    "Date",
    "Station_ID",
    "Division",
    "Station",
    "District",
    "Latitude",
    "Longitude",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
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


API_VARIABLES = [
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
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


def fetch_archive_weather(
    lat,
    lon,
    start_date,
    end_date
):

    params = {

        "latitude": float(lat),

        "longitude": float(lon),

        "daily": ",".join(
            API_VARIABLES
        ),

        "timezone": TIMEZONE,

        "start_date": str(start_date),

        "end_date": str(end_date)

    }


    response = requests.get(
        OPEN_METEO_ARCHIVE_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    data = response.json()


    daily = data["daily"]


    df = pd.DataFrame(
        daily
    )


    df.rename(
        columns={
            "time": "Date"
        },
        inplace=True
    )


    df["Date"] = pd.to_datetime(
        df["Date"]
    ).dt.normalize()


    return df



def update_station_csv(
    csv_path,
    station,
    target_date
):


    df = pd.read_csv(
        csv_path
    )


    df["Date"] = pd.to_datetime(
        df["Date"]
    ).dt.normalize()



    target_date = pd.Timestamp(
        target_date
    ).normalize()



    station_id = station["Station_ID"]



    station_df = df[
        df["Station_ID"] == station_id
    ]



    last_date = (
        station_df["Date"]
        .max()
    )



    if last_date >= target_date:

        return df



    start_date = (
        last_date
        +
        pd.Timedelta(days=1)
    )



    end_date = (
        target_date
        -
        pd.Timedelta(days=1)
    )



    if start_date > end_date:

        return df



    api_df = fetch_archive_weather(

        lat=station["Latitude"],

        lon=station["Longitude"],

        start_date=start_date.date(),

        end_date=end_date.date()

    )



    if api_df.empty:

        return df



    # Add station information

    api_df["Station_ID"] = (
        station["Station_ID"]
    )


    api_df["Division"] = (
        station["Division"]
    )


    api_df["Station"] = (
        station["Station"]
    )


    api_df["District"] = (
        station["District"]
    )


    api_df["Latitude"] = (
        float(
            station["Latitude"]
        )
    )


    api_df["Longitude"] = (
        float(
            station["Longitude"]
        )
    )



    # Match column order


    for col in CSV_COLUMNS:

        if col not in api_df.columns:

            api_df[col] = None



    api_df = api_df[
        CSV_COLUMNS
    ]



    # Merge


    updated = pd.concat(
        [
            df,
            api_df
        ],
        ignore_index=True
    )



    updated = updated.drop_duplicates(

        subset=[
            "Station_ID",
            "Date"
        ],

        keep="first"

    )



    updated = updated.sort_values(

        [
            "Station_ID",
            "Date"
        ]

    )



    updated["Date"] = (
        updated["Date"]
        .dt.strftime("%Y-%m-%d")
    )



    updated.to_csv(

        csv_path,

        index=False

    )


    return updated
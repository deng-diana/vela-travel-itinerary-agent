from __future__ import annotations

import httpx

from src.tools.mock_data import get_weather as get_mock_weather
from src.tools.schemas import WeatherInput, WeatherSummary


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(input_data: WeatherInput) -> WeatherSummary:
    try:
        location = _geocode(input_data.destination)
        forecast = _forecast(location["latitude"], location["longitude"], location["timezone"])
        return _to_summary(location["name"], input_data.month, forecast)
    except Exception:
        return get_mock_weather(input_data)


def _geocode(destination: str) -> dict:
    response = httpx.get(
        GEOCODING_URL,
        params={"name": destination, "count": 1, "language": "en", "format": "json"},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise ValueError(f"Could not geocode {destination}")

    top = results[0]
    return {
        "name": top["name"],
        "latitude": top["latitude"],
        "longitude": top["longitude"],
        "timezone": top.get("timezone") or "auto",
    }


def _forecast(latitude: float, longitude: float, timezone: str) -> dict:
    response = httpx.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": timezone,
            "forecast_days": 7,
        },
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()


def _to_summary(destination: str, month: str, forecast: dict) -> WeatherSummary:
    current = forecast.get("current", {})
    daily = forecast.get("daily", {})

    current_temp = current.get("temperature_2m")
    current_precip = current.get("precipitation", 0) or 0
    highs = [v for v in daily.get("temperature_2m_max", []) if v is not None]
    lows = [v for v in daily.get("temperature_2m_min", []) if v is not None]
    rain = [0 if v is None else v for v in daily.get("precipitation_sum", [])]

    avg_temp_c = round(current_temp) if current_temp is not None else None
    rainfall_mm = round(sum(rain)) if rain else None

    return WeatherSummary(
        destination=destination,
        month=month.title(),
        avg_temp_c=avg_temp_c,
        rainfall_mm=rainfall_mm,
        conditions_summary=_conditions(current_temp, current_precip, highs, lows),
        packing_notes=_packing(current_temp, rain),
    )


def _conditions(current_temp: float | None, current_precip: float, highs: list[float], lows: list[float]) -> str:
    if current_temp is None:
        return "Live weather snapshot available with mixed short-term conditions."

    avg_high = round(sum(highs) / len(highs)) if highs else round(current_temp)
    avg_low = round(sum(lows) / len(lows)) if lows else round(current_temp)

    if current_temp >= 28:
        base = f"Currently hot at around {round(current_temp)}C."
    elif current_temp >= 18:
        base = f"Currently mild to warm at around {round(current_temp)}C."
    else:
        base = f"Currently cool at around {round(current_temp)}C."

    if current_precip > 0:
        return f"{base} Some precipitation is active now. Expect highs near {avg_high}C and lows near {avg_low}C this week."
    return f"{base} Expect highs near {avg_high}C and lows near {avg_low}C over the next few days."


def _packing(current_temp: float | None, rain: list[float]) -> list[str]:
    notes = []

    if current_temp is not None and current_temp >= 25:
        notes.append("Pack breathable layers for warmer daytime conditions.")
    elif current_temp is not None and current_temp >= 15:
        notes.append("Bring light layers for mixed daytime and evening temperatures.")
    else:
        notes.append("Bring a light outer layer for cooler conditions.")

    if sum(rain) >= 10:
        notes.append("Carry a compact umbrella or light rain jacket.")
    else:
        notes.append("Rain gear is less important than comfortable walking layers.")

    notes.append("Wear comfortable shoes for long neighborhood-based days.")
    return notes

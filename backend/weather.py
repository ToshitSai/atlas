"""Small, keyless Open-Meteo weather tool with bounded network calls."""
from __future__ import annotations
import json, re, urllib.parse, urllib.request
from datetime import datetime

_TIMEOUT = 5

def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Atlas/1.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))

def is_weather_query(text: str) -> bool:
    return bool(re.search(r"\b(weather|temperature|forecast|rain|humidity|wind)\b", text or "", re.I))

def city_from_question(text: str) -> str | None:
    m = re.search(r"\b(?:in|at|for)\s+([A-Za-z][A-Za-z .'-]{1,50}?)(?:\?|$|\s+today|\s+tomorrow)", text or "", re.I)
    return m.group(1).strip(" .") if m else None

def forecast(city: str) -> dict:
    geo = _get("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"}))
    hit = (geo.get("results") or [None])[0]
    if not hit:
        return {"status": "not_found", "city": city}
    params = {"latitude": hit["latitude"], "longitude": hit["longitude"], "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max", "timezone": "auto", "forecast_days": 2}
    data = _get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params))
    current = data.get("current") or {}; daily = data.get("daily") or {}
    return {"status": "ok", "city": hit.get("name", city), "country": hit.get("country"), "timezone": data.get("timezone"), "current": current, "daily": daily, "source": "Open-Meteo", "retrievedAt": datetime.utcnow().isoformat() + "Z"}

def format_answer(result: dict) -> str:
    if result.get("status") != "ok": return f"I couldn't find weather data for {result.get('city', 'that location')}. Which city should I check?"
    c, d = result["current"], result["daily"]
    return (f"**{result['city']} weather**\n\n"
            f"Temperature: {c.get('temperature_2m')}°C (feels like {c.get('apparent_temperature')}°C)\n"
            f"Humidity: {c.get('relative_humidity_2m')}% · Wind: {c.get('wind_speed_10m')} km/h\n"
            f"Rain chance today: {(d.get('precipitation_probability_max') or [None])[0]}%\n"
            f"Today's high/low: {(d.get('temperature_2m_max') or [None])[0]}°C / {(d.get('temperature_2m_min') or [None])[0]}°C\n\n"
            f"Source: Open-Meteo, updated {c.get('time', '')}.")

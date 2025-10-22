from __future__ import annotations

from typing import Optional

import httpx

from .models import WeatherSnapshot


async def load_weather_snapshot(
    lat: float,
    lon: float,
    intensity: str,
    highlight: Optional[str] = None,
) -> Optional[WeatherSnapshot]:
    url = f"https://wttr.in/{lat},{lon}"
    params = {"format": "j1"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
    except Exception:
        return None

    try:
        payload = response.json()
        current_block = (payload.get("current_condition") or [None])[0] or {}
        description = (
            (current_block.get("weatherDesc") or [{}])[0].get("value", "")
        ).strip()
        temp_raw = current_block.get("temp_C") or current_block.get("tempC")
        precip_raw = current_block.get("precipMM") or current_block.get("precip_mm")
        wind_raw = current_block.get("windspeedKmph") or current_block.get("windspeed_kmph")
    except Exception:
        return None

    def _safe_float(value) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    temp_value = _safe_float(temp_raw)
    precip_value = _safe_float(precip_raw) or 0.0
    wind_value = _safe_float(wind_raw) or 0.0

    fragments = []

    if precip_value >= 1.0:
        fragments.append("Сегодня дождливо — возьмите зонт")
    elif precip_value > 0.1:
        fragments.append("Возможен лёгкий дождь, захватите ветровку")
    elif wind_value >= 25:
        fragments.append("На улице ветрено, планируйте уютные остановки")
    elif description:
        fragments.append(description.lower().capitalize())
    else:
        fragments.append("Погода располагает к прогулке")

    clothing = []

    if temp_value is not None:
        temp_label = int(round(temp_value))
        fragments.append(f"температура около {temp_label}°C")
        if temp_label <= -10:
            clothing.append("очень тёплую куртку и термоперчатки")
        elif temp_label <= 0:
            clothing.append("слоистую одежду и шапку")
        elif temp_label <= 10:
            clothing.append("ветровку или лёгкое пальто")
        elif temp_label >= 24:
            clothing.append("дышащую одежду и головной убор")

    if precip_value >= 0.3:
        clothing.append("непромокаемую обувь")

    if intensity in {"intense", "high"}:
        clothing.append("удобные кроссовки и лёгкий рюкзак для воды")
    elif intensity in {"medium", "relaxed", "low"}:
        clothing.append("комфортную обувь для долгой прогулки")

    advice = None
    if fragments:
        advice = ", ".join(fragments)
        if clothing:
            advice = advice + ". " + "Рекомендовано: " + ", ".join(clothing)

    condition = current_block.get("weatherDesc") or [{}]
    condition_key = (
        (current_block.get("weatherCode") or "")
        or (condition[0].get("value") if condition else "")
    )

    return WeatherSnapshot(
        description=description or None,
        condition_key=str(condition_key).lower() if condition_key else description,
        temperature_c=temp_value,
        precipitation_mm=float(precip_value or 0.0),
        wind_kmph=wind_value,
        advice=advice,
    )

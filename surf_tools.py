from datetime import datetime
import requests
import os

from rating_system import (
    calculate_rating,
    get_rating_label,
    get_rating_explanation,
    find_good_wave_windows,
)

# 🌊 Beach coordinates
BEACH_COORDS = {
    "tel aviv": (32.0853, 34.7818),
    "herzliya": (32.1624, 34.8445),
    "haifa": (32.7940, 34.9896),
    "ashdod": (31.8044, 34.6502),
    "netanya": (32.3328, 34.8600),
    "habonim": (32.6390, 34.9210)
}

STORMGLASS_API_KEY = os.getenv("STORMGLASS_API_KEY")

HEBREW_DAYS = {
    "Monday": "שני",
    "Tuesday": "שלישי",
    "Wednesday": "רביעי",
    "Thursday": "חמישי",
    "Friday": "שישי",
    "Saturday": "שבת",
    "Sunday": "ראשון"
}


def get_surf_forecast(beach="tel aviv", days=1, lang="en"):
    """
    Fetch a surf forecast from the Stormglass API.

    Returns a tuple of:
        report  – formatted text summary (str)
        hours   – list of hourly dicts with keys:
                    time (datetime), height, period, wind, rating
        windows – list of good-wave window dicts (may be empty)
    """
    try:
        lat, lng = BEACH_COORDS.get(beach.lower(), BEACH_COORDS["tel aviv"])

        url = "https://api.stormglass.io/v2/weather/point"
        params = {
            "lat": lat,
            "lng": lng,
            "params": "waveHeight,windSpeed,wavePeriod",
            "hours": 24 * days
        }
        headers = {"Authorization": STORMGLASS_API_KEY}

        res = requests.get(url, params=params, headers=headers, timeout=15)
        data = res.json()

        # 🛟 SAFETY: API failed or limit reached
        if "hours" not in data:
            return "⚠️ Stormglass API limit reached / unavailable", [], []

        raw_hours = data["hours"]

        # ⭐ CONVERT to graph-friendly structure and attach ratings
        hours = []
        for hour in raw_hours:
            try:
                dt = datetime.fromisoformat(hour["time"].replace("Z", ""))

                height = hour["waveHeight"]["noaa"]
                wind = hour["windSpeed"]["noaa"]
                period = hour["wavePeriod"]["noaa"]
                rating = calculate_rating(height, period, wind)

                hours.append({
                    "time": dt,
                    "height": height,
                    "period": period,
                    "wind": wind,
                    "rating": rating,
                })
            except:
                continue

        # If no valid hours → stop
        if not hours:
            return "⚠️ No surf data available", [], []

        # Detect good-wave windows (rating >= 7, at least 2 consecutive hours)
        windows = find_good_wave_windows(hours, min_rating=7.0, min_consecutive=2)

        # 📄 TEXT REPORT
        start_date = hours[0]["time"]
        end_date = hours[-1]["time"]

        if lang == "he":
            report = f"🌊 תחזית גלישה – {beach}\n"
            report += f"📅 תקופה: {start_date:%d/%m} → {end_date:%d/%m}\n\n"
        else:
            report = f"🌊 Surf forecast – {beach}\n"
            report += f"📅 Period: {start_date:%d %b} → {end_date:%d %b}\n\n"

        # Show every 6 hours (nice Telegram summary)
        for h in hours[::6]:
            day = HEBREW_DAYS[h["time"].strftime("%A")] if lang == "he" else h["time"].strftime("%A")
            label = get_rating_label(h["rating"])

            if lang == "he":
                report += f"{day} {h['time']:%d/%m %H:%M}\n"
                report += f"🌊 גל: {h['height']:.1f}מ | ⏱️ פרק גל: {h['period']:.1f}ש\n"
                report += f"💨 רוח: {h['wind']:.1f} מ/ש | ⭐ דירוג: {h['rating']}/10 {label}\n\n"
            else:
                report += f"{day} {h['time']:%d %b %H:%M}\n"
                report += f"🌊 Wave: {h['height']:.1f}m | Period: {h['period']:.1f}s\n"
                report += f"💨 Wind: {h['wind']:.1f} m/s | ⭐ Rating: {h['rating']}/10 {label}\n\n"

        return report, hours, windows

    except Exception as e:
        print("Stormglass error:", e)
        return "⚠️ Surf API error", [], []

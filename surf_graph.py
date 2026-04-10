import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import make_interp_spline

# 🟢🟡🔴 Surf scoring per hour
def surf_score(wave, wind):
    if 0.7 <= wave <= 1.8 and wind < 6:
        return "good"
    elif wave >= 0.5 and wind < 9:
        return "ok"
    else:
        return "bad"

COLORS = {
    "good": "#66ff99",
    "ok": "#ffd966",
    "bad": "#ff6666"
}

def create_wave_graph(hours, beach):

    rows = []
    for h in hours:
        dt = datetime.fromisoformat(h["time"].replace("Z",""))
        rows.append({
            "time": dt,
            "wave": h["waveHeight"]["noaa"],
            "wind": h["windSpeed"]["noaa"],
            "period": h["wavePeriod"]["noaa"]
        })

    df = pd.DataFrame(rows)

    # reduce density → every 6 hours
    df = df.iloc[::6].reset_index(drop=True)

    df["score"] = df.apply(lambda r: surf_score(r.wave, r.wind), axis=1)

    labels = [t.strftime("%d/%m %Hh") for t in df["time"]]

    avg_period = df["period"].mean()

    # Smooth wave curve
    x = np.arange(len(df))
    y = df["wave"].values
    spline = make_interp_spline(x, y, k=3)
    x_smooth = np.linspace(x.min(), x.max(), 300)
    y_smooth = spline(x_smooth)

    plt.figure(figsize=(14,7))
    ax1 = plt.gca()

    # 🌈 Colored fill per segment
    for i in range(len(df)-1):
        color = COLORS[df["score"][i]]
        ax1.fill_between(
            [x[i], x[i+1]],
            [df["wave"][i], df["wave"][i+1]],
            color=color,
            alpha=0.45
        )

    # 🌊 Smooth wave line
    ax1.plot(x_smooth, y_smooth, linewidth=4, label="Wave height (m)")

    # 💨 Wind overlay (bold black dashed)
    ax2 = ax1.twinx()
    ax2.plot(x, df["wind"], linestyle="--", linewidth=3, label="Wind (m/s)")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=35, ha="right", fontsize=10)

    ax1.set_ylabel("Wave height (m)", fontsize=14)
    ax2.set_ylabel("Wind speed (m/s)", fontsize=14)

    plt.title(
        f"{beach.title()} Surf Forecast  |  Avg Wave Period: {avg_period:.1f}s",
        fontsize=18,
        pad=20
    )

    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    plt.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax1.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()

    filename = f"{beach}_surf.png"
    plt.savefig(filename, dpi=150)
    plt.close()

    return filename

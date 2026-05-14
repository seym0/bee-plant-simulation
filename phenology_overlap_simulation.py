"""
Симуляция рассинхронизации цветения растений и активности пчёл на фоне потепления (1950–2050).

Среднегодовая температурная аномалия T: **0** в 1950–1980 (контрольный период), затем
линейный рост **(год − 1980) × D_T** только после 1980 г. Старты фенофаз — линейный отклик на T;
перекрытие фиксированных окон активности задаёт динамику популяций относительно **базового**
перекрытия в 1980 г. (аномалия T = 0): множитель `overlap / base_overlap` (рост при синхронизации,
спад при рассинхроне, без верхнего лимита численности).

Условные экологические фазы по мере роста T и сдвига стартов:
(1) пчёлы раньше растений, частичное перекрытие; (2) сближение окон; (3) пик overlap;
(4) растения «уходят» раньше, overlap падает; (5) коллапс популяций при нулевом перекрытии.

Запуск: python3 phenology_overlap_simulation.py
"""

from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


# --- Параметры климата и горизонта симуляции ---
START_YEAR = 1950
END_YEAR = 2050
N_YEARS = END_YEAR - START_YEAR + 1
D_T = 0.064  # шаг аномалии на каждый календарный год после WARMING_START_YEAR (коэффициент не меняем)
WARMING_START_YEAR = 1980  # до этого года включительно аномалия = 0 (контрольный период)

# --- Линейные фенофазы: day = day_base + slope * T (slope < 0 — раньше при потеплении) ---
DAY_BEES_BASE = 100
DAY_PLANTS_BASE = 110
SLOPE_BEES = -2.6    # день/градус T
SLOPE_PLANTS = -7.2
DURATION = 20  # длина окна активности, дней

# Единая палитра визуализации: пчёлы — оранжевый, растения — зелёный
COLOR_BEES = "#ff7f0e"
COLOR_PLANTS = "#2ca02c"

# --- Популяции: отношение перекрытия к базовому (1980, T=0) ---
POP_BEES_INITIAL = 1000
POP_PLANTS_INITIAL = 10000
POP_RELAXATION_TAU_BEES = 0.55  # сглаженное стремление к целевой численности за год
POP_RELAXATION_TAU_PLANTS = 0.45


def warming_anomaly_for_year(calendar_year: int) -> float:
    """
    Температурная аномалия (условные °C): 0 в 1950–1980, линейный рост только после 1980.
    Формула: (год − 1980) * D_T при год > 1980; иначе 0.0.
    """
    if calendar_year <= WARMING_START_YEAR:
        return 0.0
    return float(calendar_year - WARMING_START_YEAR) * D_T


def temperature_for_year_index(year_index: int) -> float:
    """Оставлено для совместимости: аномалия по индексу года симуляции (0 = START_YEAR)."""
    y = START_YEAR + year_index
    return warming_anomaly_for_year(y)


def phenology_start_day(day_base: float, slope: float, t: float) -> float:
    return day_base + slope * t


def overlap_days(start_a: float, start_b: float, duration: float) -> float:
    """Длина пересечения [start_a, start_a+duration] и [start_b, start_b+duration]."""
    end_a = start_a + duration
    end_b = start_b + duration
    lo = max(start_a, start_b)
    hi = min(end_a, end_b)
    return max(0.0, hi - lo)


def success_rate_from_overlap(overlap: float, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return max(0.0, min(1.0, overlap / duration))


def overlap_for_calendar_year(calendar_year: int) -> float:
    """Дни перекрытия окон для заданного календарного года."""
    t = warming_anomaly_for_year(calendar_year)
    db = phenology_start_day(DAY_BEES_BASE, SLOPE_BEES, t)
    dp = phenology_start_day(DAY_PLANTS_BASE, SLOPE_PLANTS, t)
    return overlap_days(db, dp, DURATION)


# Базовое перекрытие при T = 0 в 1980 г. (контрольный период 1950–1980 — то же перекрытие)
base_overlap: float = max(overlap_for_calendar_year(WARMING_START_YEAR), 1e-9)


def reproduction_factor(current_overlap: float) -> float:
    """Отношение текущего перекрытия к базовому; на историческом участке = 1.0."""
    return max(0.0, current_overlap) / base_overlap


def relax_toward(current: float, target: float, tau: float) -> float:
    t = min(1.0, max(0.0, tau))
    return max(0.0, current + t * (target - current))


def target_bee_population(current_overlap: float) -> float:
    """Целевая численность пчёл: baseline × (overlap/base)."""
    return POP_BEES_INITIAL * reproduction_factor(current_overlap)


def target_plant_population(current_overlap: float, bees_alive: float) -> float:
    """Целевая численность растений: тот же множитель по перекрытию; без пчёл — 0."""
    if bees_alive <= 0:
        return 0.0
    return POP_PLANTS_INITIAL * reproduction_factor(current_overlap)


def update_bee_population(pop_bees: float, current_overlap: float) -> float:
    tgt = target_bee_population(current_overlap)
    return relax_toward(pop_bees, tgt, POP_RELAXATION_TAU_BEES)


def update_plant_population(pop_plants: float, current_overlap: float, pop_bees: float) -> float:
    tgt = target_plant_population(current_overlap, pop_bees)
    return relax_toward(pop_plants, tgt, POP_RELAXATION_TAU_PLANTS)


def run_simulation() -> pd.DataFrame:
    rows = []
    pop_bees = float(POP_BEES_INITIAL)
    pop_plants = float(POP_PLANTS_INITIAL)

    for i in range(N_YEARS):
        year = START_YEAR + i
        t = warming_anomaly_for_year(year)
        day_bees = phenology_start_day(DAY_BEES_BASE, SLOPE_BEES, t)
        day_plants = phenology_start_day(DAY_PLANTS_BASE, SLOPE_PLANTS, t)
        ov = overlap_days(day_bees, day_plants, DURATION)

        bees_before = pop_bees
        pop_bees = update_bee_population(pop_bees, ov)
        pop_plants = update_plant_population(pop_plants, ov, bees_before)

        rows.append(
            {
                "Год": year,
                "Температура": t,
                "Старт_Пчел": day_bees,
                "Старт_Растений": day_plants,
                "Перекрытие_Дней": ov,
                "Популяция_Пчел": pop_bees,
                "Популяция_Растений": pop_plants,
            }
        )

    return pd.DataFrame(rows)


def plot_simulation_results(df: pd.DataFrame, output_file: str = "phenology_overlap_results.png") -> None:
    """Два блока: сходимость/расходимость стартов фенофаз; динамика популяций до коллапса."""
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, (ax_pheno, ax_pop) = plt.subplots(
        2, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.0]}
    )

    ax_pheno.plot(
        df["Год"],
        df["Старт_Пчел"],
        color=COLOR_BEES,
        linewidth=2.2,
        label="Старт активности пчёл",
    )
    ax_pheno.plot(
        df["Год"],
        df["Старт_Растений"],
        color=COLOR_PLANTS,
        linewidth=2.2,
        label="Старт цветения растений",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Пчел"],
        df["Старт_Пчел"] + DURATION,
        color=COLOR_BEES,
        alpha=0.12,
        label=f"Окно пчёл (+{DURATION} дн.)",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Растений"],
        df["Старт_Растений"] + DURATION,
        color=COLOR_PLANTS,
        alpha=0.12,
        label=f"Окно растений (+{DURATION} дн.)",
    )
    ax_pheno.set_ylabel("День года")
    ax_pheno.set_title("Фенология: сближение окон при потеплении и последующее расхождение")
    ax_pheno.legend(loc="upper right", fontsize=9)
    ax_pheno.grid(True, alpha=0.3)
    ax_pheno.invert_yaxis()
    ax_pheno.axvline(
        WARMING_START_YEAR,
        color="gray",
        linestyle="--",
        linewidth=1.5,
        alpha=0.85,
        zorder=1,
    )

    bee_color = COLOR_BEES
    plant_color = COLOR_PLANTS
    ax_pop.plot(df["Год"], df["Популяция_Пчел"], color=bee_color, linewidth=2.0, label="Пчёлы")
    ax_pop.set_ylabel("Пчёлы (усл. ед.)", color=bee_color, fontweight="bold")
    ax_pop.tick_params(axis="y", labelcolor=bee_color)
    ax_pop.set_xlabel("Год")
    ax_pop.set_title(
        "Популяции"
    )
    ax_pop.grid(True, alpha=0.3)
    ax_pop.set_ylim(bottom=0)
    ax_pop.xaxis.set_major_locator(MultipleLocator(10))
    ax_pop.axvline(
        WARMING_START_YEAR,
        color="gray",
        linestyle="--",
        linewidth=1.5,
        alpha=0.85,
        zorder=0,
    )

    ax_plants = ax_pop.twinx()
    ax_plants.plot(
        df["Год"], df["Популяция_Растений"], color=plant_color, linewidth=2.0, label="Растения"
    )
    ax_plants.set_ylabel("Растения (усл. ед.)", color=plant_color, fontweight="bold")
    ax_plants.tick_params(axis="y", labelcolor=plant_color)
    ax_plants.set_ylim(bottom=0)

    h1, l1 = ax_pop.get_legend_handles_labels()
    h2, l2 = ax_plants.get_legend_handles_labels()
    ax_pop.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)

    fig.suptitle(
        "Рассинхронизация пчёл и растений при линейном потеплении (модель перекрытия фенофаз)",
        fontsize=13,
        y=0.98,
    )
    fig.tight_layout()
    plt.savefig(output_file, dpi=200, bbox_inches="tight")
    print(f"\nГрафик сохранён: {output_file}")
    plt.close(fig)


def print_summary_statistics(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("ИТОГ СИМУЛЯЦИИ")
    print("=" * 60)
    print(f"Годы: {df['Год'].iloc[0]} — {df['Год'].iloc[-1]} ({len(df)} лет)")
    print(f"T: {df['Температура'].iloc[0]:.2f} → {df['Температура'].iloc[-1]:.2f}")
    max_ov_idx = df["Перекрытие_Дней"].idxmax()
    sr_max = success_rate_from_overlap(df.loc[max_ov_idx, "Перекрытие_Дней"], DURATION)
    print(
        f"Макс. перекрытие: {df.loc[max_ov_idx, 'Перекрытие_Дней']:.1f} дн. "
        f"({df.loc[max_ov_idx, 'Год']:.0f}, success_rate={sr_max:.2f})"
    )
    bees_extinct = df[df["Популяция_Пчел"] <= 0]
    if not bees_extinct.empty:
        y0 = bees_extinct["Год"].iloc[0]
        print(f"Пчёлы → 0: с года {y0:.0f}")
    else:
        print("Пчёлы: популяция > 0 на всём горизонте")
    plants_extinct = df[df["Популяция_Растений"] <= 0]
    if not plants_extinct.empty:
        print(f"Растения → 0: с года {plants_extinct['Год'].iloc[0]:.0f}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    results = run_simulation()
    pd.set_option("display.width", 120)
    pd.set_option("display.max_rows", 14)
    print(results.head(7).to_string(index=False))
    print("...")
    print(results.tail(7).to_string(index=False))
    print_summary_statistics(results)
    plot_simulation_results(results, output_file="phenology_overlap_results.png")

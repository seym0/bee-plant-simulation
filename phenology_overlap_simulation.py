"""
Симуляция рассинхронизации цветения растений и активности пчёл на фоне потепления (1950–2050).

Среднегодовая температура T растёт линейно от 0. Старты фенофаз — линейный отклик на T;
перекрытие фиксированных окон активности задаёт success_rate и демографию популяций.

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
D_T = 0.1  # прирост среднегодовой T за год (условные единицы)

# --- Линейные фенофазы: day = day_base + slope * T (slope < 0 — раньше при потеплении) ---
DAY_BEES_BASE = 100
DAY_PLANTS_BASE = 110
SLOPE_BEES = -2.6    # день/градус T
SLOPE_PLANTS = -7.2
DURATION = 20  # длина окна активности, дней

# --- Демография пчёл: pop(t+1) = pop(t) * max(0, base_reproduction_bees * success_rate - mortality_rate) ---
POP_BEES_INITIAL = 1000
BASE_REPRODUCTION_BEES = 3.0
MORTALITY_RATE_BEES = 0.55

# --- Демография растений: многолетники; семена при успешном опылении; без пчёл — быстрая деградация ---
POP_PLANTS_INITIAL = 10000
PLANT_SURVIVAL = 0.92
PLANT_FECUNDITY = 0.18
PLANT_DECAY_WITHOUT_BEES = 0.62
PLANT_STRESS_NO_OVERLAP = 0.88
PLANT_EXTINCTION_THRESHOLD = 30.0


def temperature_for_year_index(year_index: int) -> float:
    """Среднегодовая T: 0 в первый год, +dT каждый следующий."""
    return year_index * D_T


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


def update_bee_population(pop_bees: float, success: float) -> float:
    growth = BASE_REPRODUCTION_BEES * success - MORTALITY_RATE_BEES
    return max(0.0, pop_bees * max(0.0, growth))


def update_plant_population(pop_plants: float, success: float, pop_bees: float) -> float:
    if pop_bees <= 0:
        multiplier = PLANT_DECAY_WITHOUT_BEES
    elif success <= 0:
        multiplier = PLANT_STRESS_NO_OVERLAP
    else:
        multiplier = PLANT_SURVIVAL + PLANT_FECUNDITY * success
    next_pop = max(0.0, pop_plants * multiplier)
    if next_pop < PLANT_EXTINCTION_THRESHOLD:
        return 0.0
    return next_pop


def run_simulation() -> pd.DataFrame:
    rows = []
    pop_bees = float(POP_BEES_INITIAL)
    pop_plants = float(POP_PLANTS_INITIAL)

    for i in range(N_YEARS):
        year = START_YEAR + i
        t = temperature_for_year_index(i)
        day_bees = phenology_start_day(DAY_BEES_BASE, SLOPE_BEES, t)
        day_plants = phenology_start_day(DAY_PLANTS_BASE, SLOPE_PLANTS, t)
        ov = overlap_days(day_bees, day_plants, DURATION)
        success = success_rate_from_overlap(ov, DURATION)

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

        bees_this_season = pop_bees
        pop_bees = update_bee_population(pop_bees, success)
        pop_plants = update_plant_population(pop_plants, success, bees_this_season)

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
        color="#1f77b4",
        linewidth=2.2,
        label="Старт активности пчёл",
    )
    ax_pheno.plot(
        df["Год"],
        df["Старт_Растений"],
        color="#2ca02c",
        linewidth=2.2,
        label="Старт цветения растений",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Пчел"],
        df["Старт_Пчел"] + DURATION,
        color="#1f77b4",
        alpha=0.12,
        label=f"Окно пчёл (+{DURATION} дн.)",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Растений"],
        df["Старт_Растений"] + DURATION,
        color="#2ca02c",
        alpha=0.12,
        label=f"Окно растений (+{DURATION} дн.)",
    )
    ax_pheno.set_ylabel("День года")
    ax_pheno.set_title("Фенология: сближение окон при потеплении и последующее расхождение")
    ax_pheno.legend(loc="upper right", fontsize=9)
    ax_pheno.grid(True, alpha=0.3)
    ax_pheno.invert_yaxis()

    bee_color = "#ff7f0e"
    plant_color = "#9467bd"
    ax_pop.plot(df["Год"], df["Популяция_Пчел"], color=bee_color, linewidth=2.0, label="Пчёлы")
    ax_pop.set_ylabel("Пчёлы (усл. ед.)", color=bee_color, fontweight="bold")
    ax_pop.tick_params(axis="y", labelcolor=bee_color)
    ax_pop.set_xlabel("Год")
    ax_pop.set_title("Популяции: падение при низком перекрытии и вымирании опылителей")
    ax_pop.grid(True, alpha=0.3)
    ax_pop.set_ylim(bottom=0)
    ax_pop.xaxis.set_major_locator(MultipleLocator(10))

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

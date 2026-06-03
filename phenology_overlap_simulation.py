"""
Симуляция рассинхронизации цветения растений и активности пчёл на фоне потепления.

Горизонт задаётся константами **START_YEAR** … **END_YEAR** (по умолчанию 1950–2100), шаг — один
календарный год; результат — `pandas.DataFrame` и опционально график `phenology_overlap_results.png`.

**Температурная аномалия T** (условные °C), кусочно-линейно по календарному году `y`:
- при `y <= WARMING_START_YEAR` (1980): **T = 0**;
- при `1980 < y < ACCELERATION_YEAR` (2010): **T = (y − 1980) × SLOW_WARMING_RATE**, где
  `SLOW_WARMING_RATE = 0.015` °C/год;
- с **2010**: **T = (2010 − 1980) × SLOW_WARMING_RATE + (y − 2010) × D_T**, т.е. на стыке 2010 г.
  величина **0.45** °C и далее рост со скоростью **D_T** (в коде **0.04** °C/год).

**Фенофазы:** день старта `day_base + slope × T` (отрицательный `slope` — сдвиг раньше при росте T);
для пчёл и растений — свои `DAY_*_BASE` и `SLOPE_*`. **Перекрытие** — длина пересечения отрезков
`[старт, старт + DURATION]` (прямоугольные окна активности, **DURATION = 20** дней).

**Популяции:** базовое перекрытие **base_overlap** берётся при **T = 0** в 1980 г. (как в контрольном
периоде 1950–1980). Множитель численности **gm = overlap / base_overlap** (с нулём снизу при
нулевом overlap): при **gm < 1** используется **gm²** (усиленная депрессия при рассинхроне), при
**gm ≥ 1** — линейный **gm** (рост при синхронизации, без искусственного потолка). Целевые
численности — начальные популяции × этот множитель; цель растений **0**, если пчёл не осталось.
Ежегодное обновление — сглаживание `relax_toward` с коэффициентами **POP_RELAXATION_TAU_***;
сначала обновляются пчёлы, затем растения (растения зависят от численности пчёл до шага).

Типичная интерпретация ряда по overlap и сдвигу стартов: (1) пчёлы раньше растений; (2) сближение
окон; (3) пик перекрытия; (4) растения уходят раньше, overlap падает; (5) вымирание при обнулении
перекрытия или популяций.

Запуск: `python3 phenology_overlap_simulation.py` — печать фрагментов таблицы, сводка в консоль,
сохранение PNG через `plot_simulation_results`.
"""

from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


# --- Параметры климата и горизонта симуляции ---
START_YEAR = 1950
END_YEAR = 2100
N_YEARS = END_YEAR - START_YEAR + 1
D_T = 0.04  # быстрый шаг аномалии после ACCELERATION_YEAR (°C/год; коэффициент не меняем)
WARMING_START_YEAR = 1980  # до этого года включительно аномалия = 0 (контрольный период)
ACCELERATION_YEAR = 2010  # переход к стремительному потеплению (стык с умеренной фазой)
SLOW_WARMING_RATE = 0.015  # °C/год в интервале (1980, 2010)

# --- Линейные фенофазы: day = day_base + slope * T (slope < 0 — раньше при потеплении) ---
DAY_BEES_BASE = 100.0
DAY_PLANTS_BASE = 105.0   # при T=0 → gap=5 дн., base_overlap=15; синхронизация пик ~2020
SLOPE_BEES = -2.0    # день/градус T
SLOPE_PLANTS = -5.2
DURATION = 20.0  # длина окна активности, дней

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
    Температурная аномалия (условные °C): кусочно-линейный тренд.
    До 1980 включительно — 0; 1981–2009 — (год − 1980) * SLOW_WARMING_RATE;
    с 2010 — 0.45 + (год − 2010) * D_T (на стыке 2010 обе ветки дают 0.45 °C).
    """
    if calendar_year <= WARMING_START_YEAR:
        return 0.0
    if calendar_year < ACCELERATION_YEAR:
        return float(calendar_year - WARMING_START_YEAR) * SLOW_WARMING_RATE
    anomaly_at_accel = float(ACCELERATION_YEAR - WARMING_START_YEAR) * SLOW_WARMING_RATE
    return anomaly_at_accel + float(calendar_year - ACCELERATION_YEAR) * D_T


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
    """
    Множитель численности: current_overlap / base_overlap.
    При значении < 1.0 применяется квадратичная депрессия (gm²), усиливая
    чувствительность к потере синхронизации; при ≥ 1.0 — линейный рост.
    """
    gm = max(0.0, current_overlap) / base_overlap
    return gm ** 2 if gm < 1.0 else gm


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
    for ax in (ax_pheno,):
        ax.axvline(WARMING_START_YEAR, color="gray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=1)
        ax.axvline(ACCELERATION_YEAR, color="slategray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=1)

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
    ax_pop.axvline(WARMING_START_YEAR, color="gray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=0)
    ax_pop.axvline(ACCELERATION_YEAR, color="slategray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=0)
    _xax_tr = ax_pop.get_xaxis_transform()  # x: данные, y: 0–1 (оси)
    ax_pop.text(WARMING_START_YEAR + 0.8, 0.04, "1980", fontsize=8, color="gray",
                va="bottom", transform=_xax_tr)
    ax_pop.text(ACCELERATION_YEAR + 0.8, 0.04, "2010", fontsize=8, color="slategray",
                va="bottom", transform=_xax_tr)

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
        "Рассинхронизация пчёл и растений при многофазном потеплении (модель перекрытия фенофаз)",
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

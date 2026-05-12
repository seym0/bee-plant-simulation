import argparse
import sys

try:
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "matplotlib is required to run this script. Install it with:\n  pip install matplotlib"
    ) from exc

from main import Nature, Plant, BeePopulation


def simulate(years=20, base_temp=10, amplitude=15, warming_rate=0.5):
    nature = Nature(base_temp=base_temp, amplitude=amplitude, warming_rate=warming_rate)
    plant = Plant(base_bloom_threshold=12)
    bees = BeePopulation(initial_population=100, base_activation_temp=13)

    history = []
    year_daily_states = {}

    for year in range(1, years + 1):
        sync_days = 0
        warming = year * warming_rate

        plant.adapt_to_climate(warming)
        bees.adapt_to_climate(warming)
        plant.reset_for_next_year()
        bees.reset_for_next_year()

        bloom_start = None
        bloom_end = None
        bee_start = None
        bee_end = None
        daily_bloom = []
        daily_bee = []
        daily_overlap = []

        for day in range(1, 366):
            temp = nature.get_current_temp()
            plant.check_status(temp)
            bees.check_status(temp)

            is_blooming = plant.is_blooming
            is_bee_active = bees.is_active

            if is_blooming and bloom_start is None:
                bloom_start = day
            if is_blooming:
                bloom_end = day
            if is_bee_active and bee_start is None:
                bee_start = day
            if is_bee_active:
                bee_end = day

            if is_bee_active:
                if is_blooming:
                    nectar = plant.harvest_nectar(bees.population)
                    if nectar > 0:
                        sync_days += 1
                        bees.eat(nectar)
                        plant.pollinate()
                    else:
                        bees.apply_flight_cost()
                else:
                    bees.apply_flight_cost()

            daily_bloom.append(is_blooming)
            daily_bee.append(is_bee_active)
            daily_overlap.append(is_blooming and is_bee_active)

            nature.update()

        bees.complete_year(sync_days)

        bloom_duration = 0 if bloom_start is None else bloom_end - bloom_start + 1
        bee_duration = 0 if bee_start is None else bee_end - bee_start + 1
        overlap_days = sum(daily_overlap)
        food_quality = (
            0.0
            if bees.population <= 0
            else min(1.0, bees.nectar_collected / (bees.population * 60.0))
        )
        mismatch = None
        if bee_start is not None and bloom_start is not None:
            mismatch = bee_start - bloom_start

        history.append(
            {
                "year": year,
                "bloom_start": bloom_start,
                "bloom_end": bloom_end,
                "bloom_duration": bloom_duration,
                "bee_start": bee_start,
                "bee_end": bee_end,
                "bee_duration": bee_duration,
                "overlap_days": overlap_days,
                "sync_days": sync_days,
                "mismatch": mismatch,
                "nectar_collected": bees.nectar_collected,
                "energy_reserves": bees.energy_reserves,
                "population": bees.population,
                "food_quality": food_quality,
            }
        )

        year_daily_states[year] = {
            "bloom": daily_bloom,
            "bee": daily_bee,
            "overlap": daily_overlap,
        }

    return history, year_daily_states


def plot_yearly_mismatch(history, output_prefix="mismatch"):
    years = [row["year"] for row in history]
    bloom_start = [row["bloom_start"] or 365 for row in history]
    bee_start = [row["bee_start"] or 365 for row in history]
    bloom_duration = [row["bloom_duration"] for row in history]
    bee_duration = [row["bee_duration"] for row in history]
    overlap_days = [row["overlap_days"] for row in history]
    mismatch = [row["mismatch"] if row["mismatch"] is not None else 0 for row in history]
    populations = [row["population"] for row in history]
    food_quality = [row["food_quality"] for row in history]

    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    axes[0].plot(years, bloom_start, marker="o", label="Начало цветения")
    axes[0].plot(years, bee_start, marker="o", label="Начало активности роя")
    axes[0].set_ylabel("День года")
    axes[0].set_title("Начало цветения и активности роя по годам")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(years, bloom_duration, marker="s", label="Длительность цветения")
    axes[1].plot(years, bee_duration, marker="s", label="Длительность активности роя")
    axes[1].plot(years, overlap_days, marker="^", label="Перекрытие")
    axes[1].set_ylabel("Дни")
    axes[1].set_title("Длительности цветения, активности и перекрытия")
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(years, mismatch, marker="d", label="Смещение начала (пчелы — цветы)")
    axes[2].plot(years, populations, marker="x", label="Популяция")
    axes[2].plot(years, food_quality, marker="o", label="Качество питания")
    axes[2].set_ylabel("Значение")
    axes[2].set_title("Показатели mismatch и выживания")
    axes[2].legend()
    axes[2].grid(True)

    axes[-1].set_xlabel("Год")

    fig.tight_layout()
    fig.savefig(f"{output_prefix}_years.png")
    print(f"Saved yearly mismatch summary to {output_prefix}_years.png")


def plot_window_bars(history, output_prefix="mismatch"):
    years = [row["year"] for row in history]
    bloom_start = [row["bloom_start"] or 365 for row in history]
    bloom_duration = [row["bloom_duration"] for row in history]
    bee_start = [row["bee_start"] or 365 for row in history]
    bee_duration = [row["bee_duration"] for row in history]

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(years, bloom_duration, left=bloom_start, height=0.35, label="Цветение", color="#1f77b4")
    ax.barh([y + 0.35 for y in years], bee_duration, left=bee_start, height=0.35, label="Активность роя", color="#ff7f0e")
    ax.set_xlabel("День года")
    ax.set_ylabel("Год")
    ax.set_title("Окна цветения и активности роя по годам")
    ax.legend()
    ax.grid(True, axis="x", linestyle="--", alpha=0.5)

    fig.tight_layout()
    fig.savefig(f"{output_prefix}_windows.png")
    print(f"Saved yearly window chart to {output_prefix}_windows.png")


def plot_daily_timeline(year_daily_states, year, output_prefix="mismatch"):
    daily = year_daily_states[year]
    days = list(range(1, len(daily["bloom"]) + 1))
    bloom = [1 if state else 0 for state in daily["bloom"]]
    bee = [1 if state else 0 for state in daily["bee"]]
    overlap = [1 if state else 0 for state in daily["overlap"]]

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(days, bloom, step="pre", alpha=0.3, label="Цветение")
    ax.fill_between(days, bee, step="pre", alpha=0.3, label="Активность роя")
    ax.fill_between(days, overlap, step="pre", alpha=0.6, label="Перекрытие")
    ax.set_xlim(1, len(days))
    ax.set_ylim(0, 1.2)
    ax.set_xlabel("День года")
    ax.set_title(f"Схема цветения и активности роя за год {year}")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Нет", "Да"])
    ax.legend(loc="upper right")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(f"{output_prefix}_day_{year}.png")
    print(f"Saved daily timeline for year {year} to {output_prefix}_day_{year}.png")


def main():
    parser = argparse.ArgumentParser(
        description="Generate mismatch plots for bee and plant activity windows."
    )
    parser.add_argument("--years", type=int, default=20, help="Number of years to simulate")
    parser.add_argument(
        "--sample-year",
        type=int,
        default=1,
        help="Year number to plot daily timeline for",
    )
    parser.add_argument(
        "--output-prefix",
        default="mismatch",
        help="Prefix for saved plot files",
    )
    args = parser.parse_args()

    history, year_daily_states = simulate(years=args.years)
    plot_yearly_mismatch(history, output_prefix=args.output_prefix)
    plot_window_bars(history, output_prefix=args.output_prefix)

    sample_year = min(max(1, args.sample_year), args.years)
    plot_daily_timeline(year_daily_states, sample_year, output_prefix=args.output_prefix)

    print("Simulation completed.")
    print("Available files:")
    print(f"  {args.output_prefix}_years.png")
    print(f"  {args.output_prefix}_windows.png")
    print(f"  {args.output_prefix}_day_{sample_year}.png")


if __name__ == "__main__":
    main()

"""
Интерактивный график как в phenology_overlap_simulation.plot_simulation_results,
с ползунком скорости потепления D_T (°C/год после 2010 г.) и экспортом GIF по смене D_T.

Файл phenology_overlap_simulation.py не изменяется: перед run_simulation()
временно подставляется sim.D_T.

Запуск: streamlit run phenology_overlap_dt.py
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

import phenology_overlap_simulation as sim

DT_MIN = 0.04
DT_MAX = 0.10
DT_DEFAULT = 0.04


def next_available_gif_path(path: str | Path) -> Path:
    """
    Путь для записи GIF: как задано, если файла ещё нет; иначе stem_1, stem_2, … перед суффиксом.
    Относительные имена разрешаются относительно текущего каталога (как при запуске Streamlit).
    """
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path.name
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    for n in range(1, 100_000):
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise OSError("Не удалось подобрать свободное имя для GIF")


@st.cache_data(show_spinner=False)
def run_simulation_for_dt(d_t: float) -> pd.DataFrame:
    """Симуляция при заданном D_T; модуль sim восстанавливается после вызова."""
    d_t = float(d_t)
    prev = sim.D_T
    try:
        sim.D_T = d_t
        return sim.run_simulation().copy()
    finally:
        sim.D_T = prev


def _collapse_year(df: pd.DataFrame, col: str, threshold: float = 1.0) -> int | None:
    sub = df[df[col] <= threshold]
    if sub.empty:
        return None
    return int(sub["Год"].iloc[0])


@st.cache_data(show_spinner=False)
def fixed_phenology_ylim() -> tuple[float, float]:
    """
    Общие пределы оси «день года» на верхней панели для всего диапазона D_T.

    Для каждого календарного года T монотонна по D_T после 2010 г., старт фенофазы
    линейна по T — достаточно крайних D_T, чтобы охватить все промежуточные кривые.
    """
    lo = float("inf")
    hi = float("-inf")
    for d_t in (DT_MIN, DT_MAX):
        df = run_simulation_for_dt(d_t)
        for series in (
            df["Старт_Пчел"],
            df["Старт_Пчел"] + sim.DURATION,
            df["Старт_Растений"],
            df["Старт_Растений"] + sim.DURATION,
        ):
            lo = min(lo, float(series.min()))
            hi = max(hi, float(series.max()))
    span = hi - lo
    pad = max(3.0, 0.02 * span) if span > 0 else 5.0
    return lo - pad, hi + pad


def figure_overlap_results(df: pd.DataFrame, d_t: float) -> plt.Figure:
    """
    Два блока как в plot_simulation_results: фенофазы и популяции.
    """
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, (ax_pheno, ax_pop) = plt.subplots(
        2, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.0]}
    )

    ax_pheno.plot(
        df["Год"],
        df["Старт_Пчел"],
        color=sim.COLOR_BEES,
        linewidth=2.2,
        label="Старт активности пчёл",
    )
    ax_pheno.plot(
        df["Год"],
        df["Старт_Растений"],
        color=sim.COLOR_PLANTS,
        linewidth=2.2,
        label="Старт цветения растений",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Пчел"],
        df["Старт_Пчел"] + sim.DURATION,
        color=sim.COLOR_BEES,
        alpha=0.12,
        label=f"Окно пчёл (+{sim.DURATION} дн.)",
    )
    ax_pheno.fill_between(
        df["Год"],
        df["Старт_Растений"],
        df["Старт_Растений"] + sim.DURATION,
        color=sim.COLOR_PLANTS,
        alpha=0.12,
        label=f"Окно растений (+{sim.DURATION} дн.)",
    )
    ax_pheno.set_ylabel("День года")
    ax_pheno.set_title("Фенология: сближение окон при потеплении и последующее расхождение")
    ax_pheno.legend(loc="upper right", fontsize=9)
    ax_pheno.grid(True, alpha=0.3)
    y_lo, y_hi = fixed_phenology_ylim()
    ax_pheno.set_ylim(y_lo, y_hi)
    ax_pheno.invert_yaxis()
    ax_pheno.axvline(sim.WARMING_START_YEAR, color="gray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=1)
    ax_pheno.axvline(sim.ACCELERATION_YEAR, color="slategray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=1)

    bee_color = sim.COLOR_BEES
    plant_color = sim.COLOR_PLANTS
    ax_pop.plot(df["Год"], df["Популяция_Пчел"], color=bee_color, linewidth=2.0, label="Пчёлы")
    ax_pop.set_ylabel("Пчёлы (усл. ед.)", color=bee_color, fontweight="bold")
    ax_pop.tick_params(axis="y", labelcolor=bee_color)
    ax_pop.set_xlabel("Год")
    ax_pop.set_title("Популяции")
    ax_pop.grid(True, alpha=0.3)
    ax_pop.set_ylim(bottom=0)
    ax_pop.xaxis.set_major_locator(MultipleLocator(10))
    ax_pop.axvline(sim.WARMING_START_YEAR, color="gray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=0)
    ax_pop.axvline(sim.ACCELERATION_YEAR, color="slategray", linestyle="--", linewidth=1.4, alpha=0.8, zorder=0)
    _xax_tr = ax_pop.get_xaxis_transform()
    ax_pop.text(
        sim.WARMING_START_YEAR + 0.8,
        0.04,
        "1980",
        fontsize=8,
        color="gray",
        va="bottom",
        transform=_xax_tr,
    )
    ax_pop.text(
        sim.ACCELERATION_YEAR + 0.8,
        0.04,
        "2010",
        fontsize=8,
        color="slategray",
        va="bottom",
        transform=_xax_tr,
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
        "Рассинхронизация пчёл и растений при многофазном потеплении (модель перекрытия фенофаз)\n"
        f"D_T = {d_t:.3f} °C/год (скорость роста аномалии после {sim.ACCELERATION_YEAR} г.)",
        fontsize=13,
        y=0.98,
    )
    fig.tight_layout()
    return fig


def export_dt_sweep_gif(
    path: str | Path,
    d_t_values: np.ndarray | None = None,
    dpi: int = 110,
    frame_ms: int = 450,
) -> Path:
    """
    GIF: кадры — полный двухпанельный график при последовательном росте D_T.
    """
    path = next_available_gif_path(path)
    if d_t_values is None:
        d_t_values = np.linspace(DT_MIN, DT_MAX, 25)

    frames: list[Image.Image] = []
    for d_t in d_t_values:
        df = run_simulation_for_dt(float(d_t))
        fig = figure_overlap_results(df, float(d_t))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        im = Image.open(buf).convert("RGB")
        frames.append(im.copy())
        im.close()

    if not frames:
        raise ValueError("Нет кадров для GIF")

    duration_ms = int(frame_ms)
    frames[0].save(
        str(path),
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    for im in frames:
        im.close()
    return path


def main() -> None:
    st.set_page_config(
        page_title="Фенология: D_T",
        page_icon="🌡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Скорость потепления D_T и рассинхронизация фенофаз")
    st.caption(
        "Тот же вид графика, что и при `python phenology_overlap_simulation.py` "
        "(две панели: дни старта и популяции). Параметр **D_T** — рост температурной аномалии "
        f"после {sim.ACCELERATION_YEAR} г., °C/год. Исходный модуль не меняется."
    )

    with st.sidebar:
        st.header("Параметры")
        d_t = st.slider(
            "D_T (°C/год после 2010)",
            min_value=float(DT_MIN),
            max_value=float(DT_MAX),
            value=float(DT_DEFAULT),
            step=0.005,
            format="%.3f",
            help="Чем выше D_T, тем быстрее растёт T после 2010 г. и тем раньше обычно наступает рассинхрон и коллапс.",
        )

        st.divider()
        st.subheader("Экспорт GIF по D_T")
        n_frames = st.number_input(
            "Число кадров (значений D_T)",
            min_value=5,
            max_value=60,
            value=25,
            step=1,
            help="От 0.04 до 0.1 равномерно по числу кадров.",
        )
        frame_ms = st.slider("Длительность кадра (мс)", 200, 1200, 450, 50)
        out_name = st.text_input("Имя файла", value="phenology_overlap_dt.gif")

        if st.button("Собрать GIF (смена D_T)", type="primary"):
            dts = np.linspace(DT_MIN, DT_MAX, int(n_frames))
            target = Path(out_name).name
            with st.spinner("Счёт симуляций и рендер кадров…"):
                out_path = export_dt_sweep_gif(
                    target,
                    d_t_values=dts,
                    frame_ms=int(frame_ms),
                )
            st.success(f"Сохранено: `{out_path.resolve()}`")
            if out_path.exists():
                st.download_button(
                    label=f"Скачать {out_path.name}",
                    data=out_path.read_bytes(),
                    file_name=out_path.name,
                    mime="image/gif",
                    key="dl_dt_gif",
                )

    df = run_simulation_for_dt(d_t)
    fig = figure_overlap_results(df, d_t)
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    y_bees = _collapse_year(df, "Популяция_Пчел")
    y_plants = _collapse_year(df, "Популяция_Растений")
    c1, c2, c3 = st.columns(3)
    c1.metric("D_T", f"{d_t:.3f} °C/год")
    c2.metric(
        "Первый год: пчёлы ≤ 1",
        "—" if y_bees is None else str(y_bees),
        help="Условный порог вымирания пчёл на горизонте симуляции.",
    )
    c3.metric(
        "Первый год: растения ≤ 1",
        "—" if y_plants is None else str(y_plants),
        help="Условный порог для растений.",
    )

    with st.expander("Как устроено технически"):
        st.markdown(
            f"""
- Данные: `phenology_overlap_simulation.run_simulation()` после присвоения `sim.D_T` выбранному значению (в `finally` значение восстанавливается).
- Диапазон ползунка: **{DT_MIN}** … **{DT_MAX}** °C/год.
- GIF: для каждого кадра заново считается ряд и рисуется та же фигура matplotlib, кадры склеиваются через Pillow. Если файл с выбранным именем уже есть, к имени добавляется **`_1`**, **`_2`**, …
- Верхняя ось «день года» фиксируется по размаху данных при **D_T = 0.04** и **D_T = 0.10**, чтобы масштаб не прыгал между кадрами.
"""
        )


if __name__ == "__main__":
    main()

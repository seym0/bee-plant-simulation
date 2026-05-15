"""
Интерактивный дашборд Streamlit + Plotly для модели перекрытия фенофаз (phenology_overlap_simulation).

Запуск: streamlit run phenology_mismatch.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import phenology_overlap_simulation as sim

COLOR_BEES = sim.COLOR_BEES
COLOR_PLANTS = sim.COLOR_PLANTS
# Заливка пересечения — нейтральный «между» оранжевым и зелёным (не путается с линиями)
COLOR_OVERLAP_FILL = "rgba(218, 165, 32, 0.38)"
COLOR_OVERLAP_FILL_MPL = (218 / 255, 165 / 255, 32 / 255, 0.38)


# ~95% массы нормального распределения в интервале ~20 дней вокруг пика
PHENO_SIGMA_DAYS = 20.0 / (2.0 * 1.96)
SPRING_DAY_MIN = 60
SPRING_DAY_MAX = 160
SPRING_RESOLUTION = 400

DEFAULT_MISMATCH_GIF = "phenology_mismatch.gif"


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
def load_simulation() -> pd.DataFrame:
    return sim.run_simulation()


def gaussian_activity_normalized(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    """Гладкая колоколообразная кривая активности 0..1, пик в mu."""
    if sigma <= 0:
        sigma = PHENO_SIGMA_DAYS
    z = np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    m = float(np.max(z))
    if m <= 0:
        return np.zeros_like(x)
    return z / m


def overlap_fill_y(y_bees: np.ndarray, y_plants: np.ndarray) -> np.ndarray:
    """Нормализованная «общая» интенсивность перекрытия: min двух кривых (визуализация пересечения)."""
    return np.minimum(y_bees, y_plants)


def ecological_stage(row: pd.Series, df: pd.DataFrame, year_idx: int) -> tuple[int, str, str]:
    """
    Возвращает (номер 1..5, короткий заголовок, пояснение).
    Учитывает год симуляции, сдвиг пиков и перекрытие прямоугольных окон (как в модели).
    """
    db = float(row["Старт_Пчел"])
    dp = float(row["Старт_Растений"])
    ov = float(row["Перекрытие_Дней"])
    pb = float(row["Популяция_Пчел"])
    pp = float(row["Популяция_Растений"])
    gap = dp - db

    max_ov = float(df["Перекрытие_Дней"].max())
    idx_max = int(df["Перекрытие_Дней"].idxmax())
    cur_idx = int(year_idx)

    collapse_bees = pb < 1.0
    collapse_plants = pp < 1.0
    if collapse_bees and collapse_plants:
        return (
            5,
            "Экологический коллапс",
            "Обе популяции вымерли или на грани вымирания.",
        )
    if collapse_bees or collapse_plants:
        return (
            5,
            "Экологический коллапс",
            "Одна из популяций уничтожена; система неустойчива.",
        )

    # При T≈0 перекрытие ~15 дн., max_ov≈20 — порог 0.75*max отсекает все ранние годы.
    if gap >= 5.0 and cur_idx <= max(0, idx_max - 3) and ov < 0.80 * max_ov:
        return (
            1,
            "Историческое опережение пчёл",
            "Пики разнесены: пчёлы активны раньше основного цветения.",
        )

    if cur_idx < idx_max and 1.0 <= gap < 7.0 and ov >= 0.72 * max_ov:
        return (
            2,
            "Сближение",
            "Окна активности сходятся; перекрытие растёт к максимуму.",
        )

    if ov >= 0.88 * max_ov and abs(gap) < 3.5:
        return (
            3,
            "Идеальная синхронизация",
            "Высокое перекрытие: опыление и ресурс совпадают по времени.",
        )

    if gap < -1.5:
        return (
            4,
            "Инверсия и нарастающий рассинхрон",
            "Центр активности растений сместился раньше пиковки пчёл.",
        )

    if cur_idx > idx_max and ov < 0.5 * max_ov:
        return (
            4,
            "Инверсия и нарастающий рассинхрон",
            "Пик синхронизации пройден; перекрытие окон снижается.",
        )

    if ov < 6.0:
        return (
            4,
            "Инверсия и нарастающий рассинхрон",
            "Критически мало дней совместной активности.",
        )

    if cur_idx < idx_max and gap > 0.5:
        return (
            2,
            "Сближение",
            "Климат сдвигает фенофазы; окна активности сходятся.",
        )

    return (
        2,
        "Сближение",
        "Переходная фаза между режимами перекрытия.",
    )


def figure_overlap_year(
    row: pd.Series,
    x: np.ndarray,
    sigma: float = PHENO_SIGMA_DAYS,
) -> go.Figure:
    mu_b, mu_p = float(row["Старт_Пчел"]), float(row["Старт_Растений"])
    y_b = gaussian_activity_normalized(x, mu_b, sigma)
    y_p = gaussian_activity_normalized(x, mu_p, sigma)
    y_ov = overlap_fill_y(y_b, y_p)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y_ov,
            fill="tozeroy",
            mode="lines",
            line=dict(width=0),
            fillcolor=COLOR_OVERLAP_FILL,
            name="Перекрытие (min интенсивностей)",
            hovertemplate="День %{x:.0f}<br>min(I)=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y_b,
            mode="lines",
            line=dict(color=COLOR_BEES, width=2.8),
            name="Пчёлы",
            hovertemplate="День %{x:.0f}<br>I пчёл=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y_p,
            mode="lines",
            line=dict(color=COLOR_PLANTS, width=2.8),
            name="Растения",
            hovertemplate="День %{x:.0f}<br>I растений=%{y:.3f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"Весенние фенофазы — {int(row['Год'])} г.",
            font=dict(size=14),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="День года (весенний сегмент)",
        yaxis_title="Интенсивность (0–1)",
        yaxis=dict(range=[0, 1.05]),
        xaxis=dict(range=[SPRING_DAY_MIN, SPRING_DAY_MAX]),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.28,
            xanchor="center",
            x=0.5,
        ),
        template="plotly_white",
        height=360,
        margin=dict(t=48, b=95, l=50, r=25),
    )
    return fig


def figure_population_timeseries(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["Год"],
            y=df["Популяция_Пчел"],
            name="Пчёлы",
            line=dict(color=COLOR_BEES, width=2.2),
            mode="lines",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["Год"],
            y=df["Популяция_Растений"],
            name="Растения",
            line=dict(color=COLOR_PLANTS, width=2.2),
            mode="lines",
        ),
        secondary_y=True,
    )
    fig.add_vline(
        x=sim.WARMING_START_YEAR,
        line_dash="dash",
        line_color="rgba(80,80,80,0.85)",
        line_width=2,
        annotation_text="1980 — начало учёта потепления",
        annotation_position="top",
    )
    fig.add_vline(
        x=sim.ACCELERATION_YEAR,
        line_dash="dash",
        line_color="rgba(80,80,80,0.85)",
        line_width=2,
        annotation_text="2010",
        annotation_position="bottom",
    )
    fig.update_layout(
        title="Динамика популяций за весь горизонт симуляции",
        template="plotly_white",
        height=380,
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="Год")
    fig.update_yaxes(title_text="Пчёлы (усл. ед.)", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title_text="Растения (усл. ед.)", secondary_y=True, rangemode="tozero")
    return fig


def export_animation_gif(
    df: pd.DataFrame,
    path: str | Path = DEFAULT_MISMATCH_GIF,
    sigma: float = PHENO_SIGMA_DAYS,
    fps: int = 3,
) -> Path:
    """
    Анимация главного графика перекрытия гауссовых пиков по годам (matplotlib + pillow).
    Сохраняет GIF для вставки в презентацию.
    """
    path = next_available_gif_path(path)
    x = np.linspace(SPRING_DAY_MIN, SPRING_DAY_MAX, SPRING_RESOLUTION)
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=100)
    plt.rcParams["font.family"] = "DejaVu Sans"

    def draw_frame(i: int) -> None:
        ax.clear()
        row = df.iloc[i]
        mu_b, mu_p = float(row["Старт_Пчел"]), float(row["Старт_Растений"])
        y_b = gaussian_activity_normalized(x, mu_b, sigma)
        y_p = gaussian_activity_normalized(x, mu_p, sigma)
        y_ov = overlap_fill_y(y_b, y_p)

        ax.fill_between(x, 0, y_ov, color=COLOR_OVERLAP_FILL_MPL, label="Перекрытие")
        ax.plot(x, y_b, color=COLOR_BEES, lw=2.4, label="Пчёлы")
        ax.plot(x, y_p, color=COLOR_PLANTS, lw=2.4, label="Растения")
        ax.set_xlim(SPRING_DAY_MIN, SPRING_DAY_MAX)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("День года (весна)")
        ax.set_ylabel("Интенсивность (0–1)")
        ax.set_title(f"Перекрытие фенофаз — год {int(row['Год'])}  |  T′ = {row['Температура']:.2f} °C")
        ax.grid(True, alpha=0.35)
        ax.legend(loc="upper right", fontsize=9)

    def _update(i: int):
        draw_frame(i)
        return ()

    anim = animation.FuncAnimation(
        fig,
        _update,
        frames=len(df),
        interval=max(80, int(1000 / max(1, fps))),
        blit=False,
    )
    writer = animation.PillowWriter(fps=fps)
    anim.save(str(path), writer=writer)
    plt.close(fig)
    return path


def main() -> None:
    st.set_page_config(
        page_title="Фенология: пчёлы и растения",
        page_icon="🐝",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Модель рассинхронизации фенофаз при потеплении")
    st.caption(
        "Интерактивная демонстрация для проекта (Streamlit + Plotly). "
        "Данные — из `phenology_overlap_simulation.run_simulation()`."
    )

    df = load_simulation().reset_index(drop=True)
    df.index.name = "year_idx"
    n = len(df)

    with st.sidebar:
        st.header("Параметры просмотра")
        year_idx = st.slider(
            "Год симуляции / прогресс потепления",
            min_value=0,
            max_value=n - 1,
            value=0,
            help="Индекс года от 0 до N−1: соответствует строке симуляции и накопленной аномалии T.",
        )
        row = df.iloc[year_idx]
        st.progress(min(1.0, year_idx / max(1, n - 1)), text=f"Прогресс: год {int(row['Год'])} ({year_idx + 1} / {n})")
        st.caption(f"Календарный год: **{int(row['Год'])}**  ·  ΔT от старта: **{row['Температура']:.2f}** (условные °C)")

        st.divider()
        st.subheader("Экспорт для слайдов")
        if st.button(f"Сгенерировать {DEFAULT_MISMATCH_GIF}", type="primary"):
            with st.spinner("Рендер анимации (может занять 1–2 минуты)…"):
                out = export_animation_gif(df, path=DEFAULT_MISMATCH_GIF, fps=3)
            st.success(f"Сохранено в папке проекта: `{out.resolve()}`")
            if out.exists():
                st.download_button(
                    label=f"Скачать {out.name}",
                    data=out.read_bytes(),
                    file_name=out.name,
                    mime="image/gif",
                    key="dl_phenology_gif",
                )

    x = np.linspace(SPRING_DAY_MIN, SPRING_DAY_MAX, SPRING_RESOLUTION)
    fig_main = figure_overlap_year(row, x)
    st.plotly_chart(fig_main, use_container_width=True)

    t_anom = float(row["Температура"])
    ov = float(row["Перекрытие_Дней"])
    pb = float(row["Популяция_Пчел"])
    pp = float(row["Популяция_Растений"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Температурная аномалия", f"{t_anom:.2f} °C", help="Условная среднегодовая аномалия (модельный ряд).")
    m2.metric("Дней перекрытия", f"{ov:.1f}", help="Пересечение окон активности 20 дней (как в базовой модели).")
    m3.metric("Популяция пчёл", f"{pb:.3g}", help="Условные единицы численности.")
    m4.metric("Популяция растений", f"{pp:.3g}", help="Условные единицы численности.")

    stage_num, stage_title, stage_desc = ecological_stage(row, df, year_idx)
    palette = {
        1: "#e8f4fd",
        2: "#e6f4ea",
        3: "#fff8e1",
        4: "#fce4ec",
        5: "#ffebee",
    }
    st.markdown(
        f"""
<div style="padding:14px 18px;border-radius:10px;background:{palette.get(stage_num, '#f5f5f5')};
border-left:6px solid #3949ab;margin-top:12px;">
<b>Стадия {stage_num}:</b> {stage_title}<br/>
<span style="opacity:0.9;font-size:0.95rem;">{stage_desc}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Общая динамика популяций")
    st.plotly_chart(figure_population_timeseries(df), use_container_width=True)

    with st.expander("Как читать гауссовы кривые"):
        st.markdown(
            f"""
- Центры кривых — дни старта **Старт_Пчел** и **Старт_Растений** для выбранного года.
- σ ≈ **{PHENO_SIGMA_DAYS:.2f}** дня: ширина подобрана так, чтобы основная масса активности укладывалась примерно в **~20 дней** (как длительность окна в дискретной модели).
- Заливка — **min** двух нормализованных кривых: визуальный аналог пересечения интенсивностей.
"""
        )


if __name__ == "__main__":
    main()

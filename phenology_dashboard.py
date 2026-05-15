"""
Объединённый дашборд для защиты проекта:
  1) интерактивное перекрытие фенофаз по году (как phenology_mismatch.gif / Plotly);
  2) двухпанельный график по D_T 0.04…0.1 °C/год (как phenology_overlap_dt.gif / matplotlib).

Запуск локально:  streamlit run phenology_dashboard.py

Деплой (Streamlit Community Cloud): репозиторий → Main file path: phenology_dashboard.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import phenology_mismatch as pm
import phenology_overlap_dt as podt


def first_year_at_or_below(df: pd.DataFrame, col: str, threshold: float = 1.0) -> int | None:
    sub = df[df[col] <= threshold]
    if sub.empty:
        return None
    return int(sub["Год"].iloc[0])


def figure_overlap_year_with_species_icons(row: pd.Series, x: np.ndarray) -> go.Figure:
    """
    График перекрытия как в phenology_mismatch, с эмодзи на пиках гауссиан пчёл и растений.
    """
    fig = pm.figure_overlap_year(row, x)
    mu_b = float(row["Старт_Пчел"])
    mu_p = float(row["Старт_Растений"])
    gap = abs(mu_p - mu_b)
    if gap < 2.5:
        bee_xshift, plant_xshift = -24, 24
    elif gap < 8:
        bee_xshift, plant_xshift = -16, 16
    else:
        bee_xshift, plant_xshift = 0, 0

    fig.add_annotation(
        x=mu_b,
        y=1.0,
        text="🐝",
        showarrow=False,
        xshift=bee_xshift,
        yshift=18,
        font=dict(size=28),
        xanchor="center",
        yanchor="bottom",
    )
    fig.add_annotation(
        x=mu_p,
        y=1.0,
        text="🌸",
        showarrow=False,
        xshift=plant_xshift,
        yshift=18,
        font=dict(size=28),
        xanchor="center",
        yanchor="bottom",
    )
    fig.update_layout(yaxis=dict(range=[0, 1.14]), margin=dict(t=72, b=50))
    return fig


def render_year_control(df_year: pd.DataFrame) -> tuple[int, pd.Series]:
    """Ползунок года в основной колонке — на телефоне боковая панель перекрывает графики."""
    n = len(df_year)
    with st.expander("Год симуляции", expanded=True):
        year_idx = st.slider(
            "Год симуляции",
            min_value=0,
            max_value=n - 1,
            value=0,
            help="Прокрутите, чтобы увидеть сдвиг фенофаз по годам (1950–2100).",
        )
        row = df_year.iloc[year_idx]
        st.progress(
            min(1.0, year_idx / max(1, n - 1)),
            text=f"Календарный год {int(row['Год'])} · шаг {year_idx + 1} из {n}",
        )
    return year_idx, row


def render_d_t_slider() -> float:
    return st.slider(
        "D_T — скорость потепления (°C/год)",
        min_value=float(podt.DT_MIN),
        max_value=float(podt.DT_MAX),
        value=float(podt.DT_DEFAULT),
        step=0.005,
        format="%.3f",
        help="Скорость роста температурной аномалии после 2010 г.",
    )


def main() -> None:
    st.set_page_config(
        page_title="Пчёлы и растения: фенология",
        page_icon="🐝",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Моделирование (рас)синхронизации активности пчел и цветения растений")
    # st.caption(
    #     "Сверху — сдвиг гауссовых кривых по годам при сценарии из `phenology_overlap_simulation` "
    #     f"(базовый D_T = {sim.D_T:.3f} °C/год после 2010). "
    #     "Ниже — полный ряд 1950–2100 при выбранном D_T."
    # )

    df_year = pm.load_simulation().reset_index(drop=True)
    year_idx, row = render_year_control(df_year)

    # --- Блок 1: перекрытие по выбранному году (Plotly) ---
    st.subheader("1. Перекрытие фенофаз в выбранный год")
    x = np.linspace(pm.SPRING_DAY_MIN, pm.SPRING_DAY_MAX, pm.SPRING_RESOLUTION)
    st.plotly_chart(figure_overlap_year_with_species_icons(row, x), use_container_width=True)

    t_anom = float(row["Температура"])
    ov = float(row["Перекрытие_Дней"])
    pb = float(row["Популяция_Пчел"])
    pp = float(row["Популяция_Растений"])
    m1, m2 = st.columns(2)
    m3, m4 = st.columns(2)
    m1.metric("T′ (аномалия)", f"{t_anom:.2f} °C")
    m2.metric("Дней перекрытия", f"{ov:.1f}")
    m3.metric("Популяция пчёл", f"{pb:.3g}")
    m4.metric("Популяция растений", f"{pp:.3g}")

    stage_num, stage_title, stage_desc = pm.ecological_stage(row, df_year, year_idx)
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

    # --- Блок 2: фенофазы и популяции при D_T (Plotly) ---
    st.subheader("2. Фенология и популяции на горизонте 1950–2100 при выбранном D_T")
    d_t = render_d_t_slider()
    df_dt = podt.run_simulation_for_dt(d_t)
    st.plotly_chart(podt.figure_overlap_results_plotly(df_dt, d_t), use_container_width=True)

    y_bees = first_year_at_or_below(df_dt, "Популяция_Пчел")
    y_plants = first_year_at_or_below(df_dt, "Популяция_Растений")
    st.metric(
        "Год, в котором популяция пчёл станет меньше 1",
        "—" if y_bees is None else str(y_bees),
        help="Первый год, когда численность пчёл в модели не выше 1 усл. ед.",
    )
    st.metric(
        "Год, в котором популяция растений станет меньше 1",
        "—" if y_plants is None else str(y_plants),
        help="Первый год, когда численность растений в модели не выше 1 усл. ед.",
    )

    st.divider()
    st.subheader("Динамика популяций (базовый сценарий при D_T = 0.04 °C/год)")  
    # st.caption("Ряд при фиксированном D_T из `phenology_overlap_simulation.py` (для сравнения с блоком 1).")
    st.plotly_chart(pm.figure_population_timeseries(df_year), use_container_width=True)

#     with st.expander("Как читать графики"):
#         st.markdown(
#             f"""
# - **Блок 1:** центры кривых — дни старта пчёл и растений в выбранном году; заливка — min двух нормализованных гауссиан (σ ≈ **{pm.PHENO_SIGMA_DAYS:.2f}** дня).
# - **Блок 2:** тот же расчёт, что в `phenology_overlap_simulation.plot_simulation_results`, но с подставленным **D_T**; верхняя панель — день года (ось инвертирована: вверх — раньше в сезоне).
# """
#         )


if __name__ == "__main__":
    main()

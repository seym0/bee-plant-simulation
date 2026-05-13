import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Настройка страницы Streamlit
st.set_page_config(page_title="Симуляция: Фенологический рассинхрон", layout="wide")
st.title("🐝 Фенологический рассинхрон: Растения и Пчелы (1950–2050)")

# --- БОКОВАЯ ПАНЕЛЬ: ИНТЕРАКТИВНЫЕ СЛАЙДЕРЫ ---
st.sidebar.header("Параметры симуляции")
warming_rate = st.sidebar.slider("Скорость потепления (°C/год)", min_value=0.0, max_value=0.1, value=0.02, step=0.005)
bloom_duration = st.sidebar.slider("Длительность цветения (дней)", min_value=10, max_value=90, value=60, step=5)
selected_year = st.sidebar.slider("Год для детального среза", min_value=1950, max_value=2050, value=2000, step=1)

# --- ЛОГИКА МОДЕЛИ ---
years = np.arange(1950, 2051)
days = np.arange(1, 366)

base_temp = 10.0
amplitude = 15.0
plant_base_thresh = 12.0
bee_base_thresh = 13.0
plant_k = 0.9
bee_k = 0.3

plant_starts = []
bee_starts = []

# Расчет динамики по годам
for y in years:
    total_warming = (y - 1950) * warming_rate
    # Синусоидальная модель температуры (пик летом, сдвиг на 100 дней)
    temps = base_temp + total_warming + amplitude * np.sin(2 * np.pi * (days - 100) / 365)
    
    # Адаптированные пороги
    p_thresh = plant_base_thresh - (total_warming * plant_k)
    b_thresh = bee_base_thresh - (total_warming * bee_k)
    
    # Поиск первого дня превышения порога
    p_day = np.argmax(temps >= p_thresh) + 1 if np.any(temps >= p_thresh) else 365
    b_day = np.argmax(temps >= b_thresh) + 1 if np.any(temps >= b_thresh) else 365
    
    plant_starts.append(p_day)
    bee_starts.append(b_day)

df = pd.DataFrame({
    'Year': years,
    'PlantStart': plant_starts,
    'PlantEnd': np.minimum(np.array(plant_starts) + bloom_duration, 365),
    'BeeStart': bee_starts
})

# Определение наличия рассинхрона (если цветение закончилось до вылета пчел)
df['Mismatch'] = df['PlantEnd'] < df['BeeStart']

# --- ГРАФИК 1: ЭВОЛЮЦИЯ СДВИГА (1950-2050) ---
fig1 = go.Figure()

# Линии старта
fig1.add_trace(go.Scatter(x=df['Year'], y=df['PlantStart'], mode='lines', name='Начало цветения', line=dict(color='green', width=2)))
fig1.add_trace(go.Scatter(x=df['Year'], y=df['BeeStart'], mode='lines', name='Пробуждение пчел', line=dict(color='orange', width=2)))
fig1.add_trace(go.Scatter(x=df['Year'], y=df['PlantEnd'], mode='lines', name='Конец цветения', line=dict(color='lightgreen', width=1, dash='dash')))

# Закраска области пересечения (синхронизации) и рассинхрона
for i in range(len(df) - 1):
    y_curr, y_next = df.loc[i, 'Year'], df.loc[i+1, 'Year']
    mismatch = df.loc[i, 'Mismatch']
    fill_color = 'rgba(255, 0, 0, 0.2)' if mismatch else 'rgba(0, 255, 0, 0.15)'
    
    y_upper = [df.loc[i, 'PlantEnd'], df.loc[i+1, 'PlantEnd']]
    y_lower = [df.loc[i, 'BeeStart'], df.loc[i+1, 'BeeStart']]
    
    # Отрисовка полигона заливки между линиями
    fig1.add_trace(go.Scatter(
        x=[y_curr, y_next, y_next, y_curr],
        y=[y_upper[0], y_upper[1], y_lower[1], y_lower[0]],
        fill='toself', fillcolor=fill_color, line=dict(color='rgba(255,255,255,0)'),
        showlegend=False, hoverinfo='skip'
    ))

fig1.update_layout(title="Динамика фенологических фаз и зоны риска", xaxis_title="Год", yaxis_title="День года", yaxis=dict(range=[1, 200]))

# --- ГРАФИК 2: ДЕТАЛЬНЫЙ СРЕЗ ГОДА ---
curr_idx = selected_year - 1950
curr_warming = curr_idx * warming_rate
curr_temps = base_temp + curr_warming + amplitude * np.sin(2 * np.pi * (days - 100) / 365)
p_start = df.loc[curr_idx, 'PlantStart']
p_end = df.loc[curr_idx, 'PlantEnd']
b_start = df.loc[curr_idx, 'BeeStart']

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=days, y=curr_temps, mode='lines', name='Температура (°C)', line=dict(color='royalblue', width=2)))

# Добавление зон активности
fig2.add_vrect(x0=p_start, x1=p_end, fillcolor="green", opacity=0.2, layer="below", line_width=0, annotation_text="Цветение")
fig2.add_vrect(x0=b_start, x1=365, fillcolor="orange", opacity=0.2, layer="below", line_width=0, annotation_text="Активность пчел")

# Пороги текущего года
p_thr = plant_base_thresh - (curr_warming * plant_k)
b_thr = bee_base_thresh - (curr_warming * bee_k)
fig2.add_hline(y=p_thr, line_dash="dot", line_color="green", annotation_text=f"Порог растений ({p_thr:.1f}°C)")
fig2.add_hline(y=b_thr, line_dash="dot", line_color="orange", annotation_text=f"Порог пчел ({b_thr:.1f}°C)")

fig2.update_layout(title=f"Температурный профиль и периоды активности ({selected_year} год)", xaxis_title="День года", yaxis_title="Температура (°C)", xaxis=dict(range=[1, 300]))

# --- ОТОБРАЖЕНИЕ В STREAMLIT ---
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.plotly_chart(fig2, use_container_width=True)

# Информационная плашка
if df.loc[curr_idx, 'Mismatch']:
    st.error(f"⚠️ В {selected_year} году наблюдается критический рассинхрон! Растения отцветают до пробуждения пчел. Популяция под угрозой.")
else:
    overlap = p_end - b_start
    st.success(f"✅ В {selected_year} году опыление успешно. Окно совместной активности составляет {overlap} дней.")
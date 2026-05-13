"""
Модуль визуализации для анализа многолетней динамики экосистемы.
Отображает популяции пчел и растений, а также фенологический сдвиг.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime
import math
from collections import defaultdict
import numpy as np


class SimulationLogger:
    """Класс для логирования метрик симуляции по годам."""
    
    def __init__(self):
        self.years = []
        self.bee_population = []
        self.temperature_mean = []
        self.bee_activation_day = []  # День просыпания пчел (вычисляется в конце года)
        self.plant_data = {}  # {plant_name: [seed_bank_values]}
        
        # Новые данные для фенологической синхронизации
        self.plant_bloom_periods = defaultdict(list)  # {plant_name: [(start_day, end_day) per year]}
        self.bee_activity_periods = []  # [(start_day, end_day) per year]
    
    def log_year(self, year, bees, flora, nature):
        """Логирование метрик в конце года."""
        self.years.append(year)
        self.bee_population.append(bees.population)
        
        # Температурные метрики
        yearly_mean = nature.base_temp + (year * nature.warming_rate)
        self.temperature_mean.append(yearly_mean)
        
        # День пробуждения пчел (приблизительный расчет)
        bee_wake_day = self._calculate_activation_day(bees.current_activation_temp, nature)
        self.bee_activation_day.append(bee_wake_day)
        
        # Логирование seed_bank для каждого растения
        for plant in flora:
            if plant.name not in self.plant_data:
                self.plant_data[plant.name] = []
            self.plant_data[plant.name].append(plant.seed_bank)
            
            # Логирование периодов цветения
            self.plant_bloom_periods[plant.name].append((plant.bloom_start_day, plant.bloom_end_day))
        
        # Логирование периода активности пчел
        self.bee_activity_periods.append((bees.start_day, bees.end_day))
    
    def _calculate_activation_day(self, activation_temp, nature):
        """Вычисляет день, когда температура впервые достигает порога активации."""
        for day in range(1, 366):
            yearly_mean = nature.base_temp + (nature.year * nature.warming_rate)
            season_mod = 15 * math.sin(2 * math.pi * (day - 80) / 365)
            temp = yearly_mean + season_mod
            if temp >= activation_temp:
                return day
        return 365  # Если не нашли, возвращаем конец года
    
    def _calculate_sleep_day(self, sleep_temp, nature):
        """Вычисляет день, когда температура опускается ниже порога сна."""
        for day in range(365, 0, -1):
            yearly_mean = nature.base_temp + (nature.year * nature.warming_rate)
            season_mod = 15 * math.sin(2 * math.pi * (day - 80) / 365)
            temp = yearly_mean + season_mod
            if temp < sleep_temp:
                return day
        return 1  # Если не нашли, возвращаем начало года
    
    def _calculate_bloom_start(self, plant, nature):
        """Вычисляет день старта цветения растения."""
        for day in range(1, 366):
            yearly_mean = nature.base_temp + (nature.year * nature.warming_rate)
            season_mod = 15 * math.sin(2 * math.pi * (day - 80) / 365)
            temp = yearly_mean + season_mod
            if temp >= plant.current_bloom_threshold:
                return day
        return 365


def plot_simulation_results(history_data, output_file='simulation_results.png'):
    """
    Строит дашборд из двух графиков для анализа симуляции.
    
    Args:
        history_data: объект SimulationLogger с накопленными данными
        output_file: путь для сохранения графика
    """
    
    # Настройка стиля
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (14, 10)
    plt.rcParams['font.size'] = 10
    
    # Создание фигуры с двумя подграфиками
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # ========== ВЕРХНИЙ ГРАФИК: Популяции пчел и растений ==========
    ax1.set_title('Динамика популяций: пчелы и растения', fontsize=14, fontweight='bold', pad=15)
    
    # График популяции пчел (толстая линия)
    ax1.plot(history_data.years, history_data.bee_population, 
             linewidth=2.5, marker='o', markersize=3, 
             label='Популяция пчел', color='#FF6B35', zorder=5)
    
    # Графики seed_bank для каждого вида растений
    colors = ['#004E89', '#1B6CA8', '#43AA8B', '#F18F01', '#C73E1D', '#6A994E']
    plant_names = list(history_data.plant_data.keys())
    
    for idx, plant_name in enumerate(plant_names):
        ax1.plot(history_data.years, history_data.plant_data[plant_name],
                 linewidth=1.5, marker='s', markersize=2,
                 label=plant_name, color=colors[idx % len(colors)],
                 linestyle='--', alpha=0.8)
    
    ax1.set_ylabel('Размер популяции (особи / семена)', fontsize=11, fontweight='bold')
    ax1.legend(loc='best', fontsize=9, framealpha=0.95, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)
    
    # ========== НИЖНИЙ ГРАФИК: Фенологическая синхронизация ==========
    ax2.set_title('Фенологическая синхронизация: цветение растений и активность пчел', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('День года', fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 365)
    
    # Цвета для растений
    plant_colors = ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFBA', '#BAE1FF', '#E8BAFF']
    plant_names = list(history_data.plant_bloom_periods.keys())
    
    # Вертикальные бары для цветения растений по годам
    for idx, plant_name in enumerate(plant_names):
        bloom_periods = history_data.plant_bloom_periods[plant_name]
        starts = [s if s is not None else np.nan for s, e in bloom_periods]
        ends = [e if e is not None else np.nan for s, e in bloom_periods]
        heights = [e - s if s is not None and e is not None else 0 for s, e in bloom_periods]
        ax2.bar(history_data.years, height=heights, bottom=starts, width=0.8, 
                color=plant_colors[idx % len(plant_colors)], alpha=0.7, label=plant_name)
    
    # Активность пчел (дискретные бары с штриховкой)
    bee_starts = [s if s is not None else np.nan for s, e in history_data.bee_activity_periods]
    bee_durations = [e - s if s is not None and e is not None else 0 for s, e in history_data.bee_activity_periods]
    ax2.bar(history_data.years, height=bee_durations, bottom=bee_starts, width=0.4, 
            facecolor='none', edgecolor='black', hatch='//', linewidth=1.2, 
            zorder=10, label='Bee Activity Window')
    
    ax2.legend(loc='best', fontsize=9, framealpha=0.95)
    ax2.grid(True, alpha=0.3)
    
    # Общие настройки
    fig.suptitle('Многолетняя динамика системы: Фенологический рассинхрон и коллапс',
                 fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # Сохранение графика
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ График сохранен в файл: {output_file}")
    
    # Вывод на экран
    plt.show()


def print_summary_statistics(history_data):
    """Выводит итоговую статистику симуляции."""
    print("\n" + "="*70)
    print("ИТОГОВАЯ СТАТИСТИКА СИМУЛЯЦИИ")
    print("="*70)
    
    print(f"\nОбщее количество лет: {len(history_data.years)}")
    print(f"Максимальная популяция пчел: {max(history_data.bee_population)} (год {history_data.years[history_data.bee_population.index(max(history_data.bee_population))]})")
    print(f"Год экологического коллапса (популяция пчел = 0): {history_data.years[-1] if history_data.bee_population[-1] == 0 else 'Нет'}")
    
    print("\nДинамика популяций растений (seed_bank):")
    for plant_name in history_data.plant_data.keys():
        final_value = history_data.plant_data[plant_name][-1]
        max_value = max(history_data.plant_data[plant_name])
        extinction_year = None
        for i, val in enumerate(history_data.plant_data[plant_name]):
            if val == 0 and extinction_year is None:
                extinction_year = history_data.years[i]
        
        print(f"  {plant_name}:")
        print(f"    - Финальный seed_bank: {final_value}")
        print(f"    - Максимум: {max_value}")
        if extinction_year:
            print(f"    - Вымирание на год: {extinction_year}")
        else:
            print(f"    - Статус: Выжил")
    
    print(f"\nФенологическая синхронизация:")
    print(f"  - Средний сезон активности пчел: дни {int(sum([s for s, e in history_data.bee_activity_periods if s is not None]) / len([s for s, e in history_data.bee_activity_periods if s is not None]))} - {int(sum([e for s, e in history_data.bee_activity_periods if e is not None]) / len([e for s, e in history_data.bee_activity_periods if e is not None]))}")
    print(f"  - Виды растений с цветением: {len([p for p in history_data.plant_bloom_periods.keys() if any(start is not None for start, end in history_data.plant_bloom_periods[p])])} из {len(history_data.plant_bloom_periods)}")
    
    print(f"\nТемпературные изменения:")
    print(f"  - Средняя температура год 1: {history_data.temperature_mean[0]:.2f}°C")
    print(f"  - Средняя температура год {len(history_data.years)}: {history_data.temperature_mean[-1]:.2f}°C")
    print(f"  - Изменение: {history_data.temperature_mean[-1] - history_data.temperature_mean[0]:.2f}°C")
    print("="*70 + "\n")

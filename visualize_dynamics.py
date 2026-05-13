"""
Модуль визуализации для анализа многолетней динамики экосистемы.
Отображает популяции пчел и растений, а также фенологический сдвиг.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime


class SimulationLogger:
    """Класс для логирования метрик симуляции по годам."""
    
    def __init__(self):
        self.years = []
        self.bee_population = []
        self.temperature_mean = []
        self.bee_activation_day = []  # День просыпания пчел (вычисляется в конце года)
        self.plant_data = {}  # {plant_name: [seed_bank_values]}
    
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
    
    def _calculate_activation_day(self, activation_temp, nature):
        """Вычисляет день, когда температура впервые достигает порога активации."""
        for day in range(1, 366):
            yearly_mean = nature.base_temp + (nature.year * nature.warming_rate)
            season_mod = 15 * (2 * 3.14159 * (day - 80) / 365)
            # Упрощенный расчет (используем sin)
            import math
            season_mod = 15 * math.sin(2 * math.pi * (day - 80) / 365)
            temp = yearly_mean + season_mod
            if temp >= activation_temp:
                return day
        return 365  # Если не нашли, возвращаем конец года


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
    
    # ========== НИЖНИЙ ГРАФИК: Фенологический сдвиг и температура ==========
    ax2.set_title('Климатические сдвиги и фенологический рассинхрон', fontsize=14, fontweight='bold', pad=15)
    
    # Двойная ось Y для температуры
    ax2_twin = ax2.twinx()
    
    # Температура (правая ось)
    line_temp = ax2_twin.plot(history_data.years, history_data.temperature_mean,
                              linewidth=2, marker='^', markersize=4,
                              label='Среднегодовая температура', 
                              color='#E63946', zorder=4)
    ax2_twin.set_ylabel('Температура (°C)', fontsize=11, fontweight='bold', color='#E63946')
    ax2_twin.tick_params(axis='y', labelcolor='#E63946')
    
    # День активации пчел (левая ось)
    line_bee = ax2.plot(history_data.years, history_data.bee_activation_day,
                        linewidth=2, marker='o', markersize=4,
                        label='День просыпания пчел', 
                        color='#457B9D', zorder=3)
    
    ax2.set_xlabel('Год симуляции', fontsize=11, fontweight='bold')
    ax2.set_ylabel('День года', fontsize=11, fontweight='bold', color='#457B9D')
    ax2.tick_params(axis='y', labelcolor='#457B9D')
    ax2.set_ylim(50, 150)
    ax2.grid(True, alpha=0.3)
    
    # Объединенная легенда
    lines = line_bee + line_temp
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc='upper right', fontsize=9, framealpha=0.95)
    
    # Общие настройки
    ax2.set_xlabel('Год симуляции', fontsize=11, fontweight='bold')
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
    
    print(f"\nФенологический сдвиг (день просыпания пчел):")
    print(f"  - Год 1: день {history_data.bee_activation_day[0]}")
    print(f"  - Год {len(history_data.years)}: день {history_data.bee_activation_day[-1]}")
    print(f"  - Изменение: {history_data.bee_activation_day[-1] - history_data.bee_activation_day[0]} дней")
    
    print(f"\nТемпературные изменения:")
    print(f"  - Средняя температура год 1: {history_data.temperature_mean[0]:.2f}°C")
    print(f"  - Средняя температура год {len(history_data.years)}: {history_data.temperature_mean[-1]:.2f}°C")
    print(f"  - Изменение: {history_data.temperature_mean[-1] - history_data.temperature_mean[0]:.2f}°C")
    print("="*70 + "\n")

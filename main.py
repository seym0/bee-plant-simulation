import math
from visualize_dynamics import SimulationLogger, plot_simulation_results, print_summary_statistics


class Nature:
    """Модель окружающей среды, управляющая сезонными колебаниями и трендом глобального потепления."""
    def __init__(self, base_temp=10, amplitude=15, warming_rate=0.02):
        self.day = 1
        self.year = 1
        self.base_temp = base_temp       # Базовая среднегодовая температура
        self.amplitude = amplitude       # Сезонная амплитуда (размах между зимой и летом)
        self.warming_rate = warming_rate # Ежегодный прирост температуры

    def get_current_temp(self):
        # Тренд потепления для текущего года
        yearly_mean = self.base_temp + (self.year * self.warming_rate)
        # Сезонная синусоида со сдвигом, чтобы весна (переход через базовую t) начиналась в районе 80-го дня
        season_mod = self.amplitude * math.sin(2 * math.pi * (self.day - 80) / 365)
        return yearly_mean + season_mod

    def update(self):
        self.day += 1
        if self.day > 365:
            self.day = 1
            self.year += 1  


class Plant:
    """Модель отдельного вида растений со своими биологическими порогами и зависимостью от опыления."""
    def __init__(self, name, base_bloom_threshold, bloom_duration, nectar_amount=500, seasonal_nectar_capacity=10000, adaptation_rate=0.7, seed_bank=10000, min_day=0, requires_temp_drop=False):
        self.name = name
        self.base_bloom_threshold = base_bloom_threshold
        self.current_bloom_threshold = base_bloom_threshold
        self.bloom_duration = bloom_duration
        self.daily_nectar_supply = nectar_amount
        self.seasonal_nectar_capacity = seasonal_nectar_capacity
        self.adaptation_rate = adaptation_rate
        self.min_day = min_day
        self.requires_temp_drop = requires_temp_drop
        
        # Динамические ресурсы
        self.nectar_available = seasonal_nectar_capacity
        self.daily_nectar_available = 0
        self.bloom_days_left = 0
        self.days_bloomed = 0
        
        # Флаги состояния
        self.is_blooming = False
        self.has_bloomed = False  # Гарантирует один цикл цветения за год
        self.is_pollinated = False
        self.is_alive = True      # Без опыления вид погибает

        # Новые атрибуты для динамики популяции
        self.seed_bank = seed_bank  # Объем популяции (банк семян), стартовое значение 10000
        self.visits = 0  # Количество визитов пчел за сезон
        self.weak_years = 0  # Счетчик подряд лет слабого опыления
        
        # Фенологические атрибуты
        self.bloom_start_day = None
        self.bloom_end_day = None

    def adapt_to_climate(self, warming_degrees):
        if not self.is_alive:
            return
        # Быстрая адаптация к потеплению (сдвиг порога вниз)
        self.current_bloom_threshold = self.base_bloom_threshold - (warming_degrees * self.adaptation_rate)

    def update(self, current_day, current_temp):
        if not self.is_alive:
            self.is_blooming = False
            self.daily_nectar_available = 0
            return

        if self.is_blooming:
            self.days_bloomed += 1
            self.bloom_days_left = max(0, self.bloom_days_left - 1)
            if self.days_bloomed >= self.bloom_duration or self.bloom_days_left <= 0:
                self.is_blooming = False
                if self.bloom_end_day is None:
                    self.bloom_end_day = current_day
        elif not self.has_bloomed and current_day >= self.min_day:
            if self.requires_temp_drop:
                can_bloom = current_day > 180 and current_temp <= self.base_bloom_threshold
            else:
                can_bloom = current_temp >= self.current_bloom_threshold

            if can_bloom and self.nectar_available > 0:
                self.is_blooming = True
                self.has_bloomed = True
                self.bloom_days_left = self.bloom_duration
                self.days_bloomed = 1
                if self.bloom_start_day is None:
                    self.bloom_start_day = current_day
            else:
                self.is_blooming = False

        # Выделение суточной порции нектара — зависит от seed_bank
        if self.is_blooming and self.nectar_available > 0:
            population_factor = self.seed_bank / 10000.0  # Нормализация к стартовому значению
            self.daily_nectar_available = min(self.daily_nectar_supply * population_factor, self.nectar_available)
        else:
            self.daily_nectar_available = 0

        if self.is_blooming and self.bloom_days_left == 0 and self.bloom_end_day is None:
            self.is_blooming = False
            self.bloom_end_day = current_day

    def harvest_nectar(self, demand):
        if not self.is_alive or not self.is_blooming:
            return 0
        nectar = min(self.daily_nectar_available, demand)
        self.daily_nectar_available -= nectar
        self.nectar_available -= nectar
        return nectar

    def pollinate(self):
        if self.is_alive and self.is_blooming:
            self.is_pollinated = True
            self.visits += 1  # Увеличиваем счетчик визитов пчел

    def reproduce(self):
        """Расчет размера популяции на следующий год на основе качества опыления."""
        # Если вид растений уже вымер, воскреснуть он не может
        if self.seed_bank <= 0:
            self.is_alive = False
            return

        # Параметры формулы
        # R_base = 0.5  # Базовый коэффициент роста
        # K_pollination = 0.5  # Коэффициент влияния опыления
        Visits_required = 60  # Минимальное количество визитов для полного опыления
        # Loss_natural = 0.1  # Естественная потеря (10%)

        # Расчет нового seed_bank
        # Расчет коэффициента успешности опыления (от 0.0 до 1.0)
        # Ограничиваем сверху 1.0, чтобы сверхууспешное опыление не давало бесконечный рост
        pollination_ratio = min(1.0, self.visits / Visits_required)
        
        # 2. Экологическая формула:
        # - 50% старых семян сохраняются в почве (ею не страшна зима)
        # - Новые семена дают прирост до +70% от популяции при идеальном опылении
        base_survival = 0.5
        max_reproduction = 0.65
        
        # Итоговый множитель роста
        growth_factor = base_survival + (max_reproduction * pollination_ratio)

        # new_seed_bank = int(self.seed_bank * growth_factor * (1 - Loss_natural))
        self.seed_bank = int(self.seed_bank * growth_factor)
        # 4. Естественное вырождение при критически низкой численности
        if self.seed_bank < 100:
            self.seed_bank = 0

        self.is_alive = self.seed_bank > 0
        self.visits = 0

    def reset_for_next_year(self):
        if not self.is_alive:
            return
        self.is_blooming = False
        self.has_bloomed = False
        self.is_pollinated = False
        self.nectar_available = self.seasonal_nectar_capacity
        self.daily_nectar_available = 0
        self.bloom_days_left = 0
        self.visits = 0  # Сброс визитов для нового сезона
        self.bloom_start_day = None
        self.bloom_end_day = None


class BeePopulation:
    """Модель колонии пчел-универсалов, страдающих от фенологического отставания."""
    def __init__(self, initial_population=100, base_activation_temp=13, base_sleep_temp=9, adaptation_rate=0.5):
        self.population = initial_population
        self.base_activation_temp = base_activation_temp
        self.base_sleep_temp = base_sleep_temp
        self.current_activation_temp = base_activation_temp
        self.current_sleep_temp = base_sleep_temp
        self.adaptation_rate = adaptation_rate  # Адаптируются медленнее флоры

        self.base_energy = 1000
        self.energy_reserves = self.base_energy
        self.daily_metabolism = 0.005
        self.flight_cost = 0.08

        self.is_active = False
        self.is_alive = True
        self.nectar_collected = 0
        self.active_days = 0
        self.starvation_days = 0
        self.max_starvation_days = 15
        
        self.start_day = None
        self.end_day = None

    def adapt_to_climate(self, warming_degrees):
        self.current_activation_temp = self.base_activation_temp - (warming_degrees * self.adaptation_rate)
        self.current_sleep_temp = self.base_sleep_temp - (warming_degrees * self.adaptation_rate)

    def check_status(self, current_temp, day):
        if self.population <= 0:
            self.is_alive = False
            self.is_active = False
            return

        previous_active = self.is_active
        if self.is_active:
            # Пчелы засыпают, когда температура опускается ниже порога ухода.
            self.is_active = current_temp >= self.current_sleep_temp
        else:
            # Выпадение из спячки, когда запускается сезон.
            self.is_active = current_temp >= self.current_activation_temp and self.is_alive

        # Логика фенологических дней
        if self.is_active and not previous_active and self.start_day is None:
            self.start_day = day
        elif not self.is_active and previous_active and self.start_day is not None and self.end_day is None:
            self.end_day = day

        # Расход энергии на поддержание жизни базы — только когда активны
        if self.is_active:
            self.energy_reserves -= self.population * self.daily_metabolism
            self.energy_reserves = max(0.0, self.energy_reserves)
            self.active_days += 1

        # Проверка критического истощения
        if self.energy_reserves <= 0:
            self.is_alive = False
            self.is_active = False
            self.population = 0

    def apply_flight_cost(self):
        """Штраф за вылет вхолостую (когда доступных цветов нет)."""
        if self.is_alive and self.is_active:
            self.energy_reserves -= self.population * self.flight_cost
            self.energy_reserves = max(0.0, self.energy_reserves)
            self.starvation_days += 1
            if self.energy_reserves <= 0:
                self.is_alive = False
                self.is_active = False
                self.population = 0

    def eat(self, nectar_amount):
        """Пополнение запасов при успешном нахождении цветка."""
        if self.is_alive and self.is_active and nectar_amount > 0:
            self.energy_reserves += nectar_amount
            self.nectar_collected += nectar_amount
            self.starvation_days = 0

    def complete_year(self, sync_days):
        """Расчет размера нового поколения, переживающего зиму.

        Текущее поколение живет ровно один год, затем заменяется потомством.
        """
        if self.population <= 0:
            return

        pollination_quality = min(1.0, sync_days / 60.0)
        food_quality = min(1.0, self.nectar_collected / (self.population * 60.0))
        overall_quality = min(pollination_quality, food_quality)

        # При хорошем кормлении и опылении — рост или стабильность.
        # При плохом качестве — снижение популяции.
        reproduction_rate = 0.8 + 0.4 * overall_quality
        winter_loss = 0.2 * (1.0 - overall_quality)
        # Расчет количества потомства, которое переживет зиму
        # Поколение отмирает после года, а дальше работает только потомство.
        new_population = int(self.population * reproduction_rate * (1.0 - winter_loss))
        # Полная замена старого значения популяции новым поколением
        self.population = max(0, new_population)
        if self.population == 0:
            self.is_alive = False
            return
        
        self.is_alive = True

    def reset_for_next_year(self):
        if not self.is_alive:
            return
        self.is_active = False
        self.energy_reserves = self.base_energy
        self.nectar_collected = 0
        self.active_days = 0
        self.starvation_days = 0
        self.start_day = None
        self.end_day = None


# --- ГЛАВНЫЙ УПРАВЛЯЮЩИЙ ЦИКЛ (MAIN LOOP) ---

if __name__ == "__main__":
    # 1. Инициализация климата и агентов
    nature = Nature(base_temp=10, amplitude=15, warming_rate=0.01)
    bees = BeePopulation(initial_population=100, base_activation_temp=10)
    
    # Пул флоры (сезонный конвейер из 6 видов)
    flora = [
        # 1. Зацветает при первых оттепелях, цветет недолго и освобождает нишу early
        Plant("Очень ранний вид", base_bloom_threshold=6, bloom_duration=20, nectar_amount=600, seasonal_nectar_capacity=6000, min_day=0),
        
        # 2. Массовое весеннее цветение, начинается после начала размножения опылителей
        Plant("Ранневесенний вид", base_bloom_threshold=10, bloom_duration=30, nectar_amount=700, seasonal_nectar_capacity=10000, min_day=90),
        
        # 3. Раннее лето, открывает половину сезона
        Plant("Раннелетний вид", base_bloom_threshold=14, bloom_duration=40, nectar_amount=500, seasonal_nectar_capacity=15000, min_day=110),
        
        # 4. Пик лета, требует максимального прогрева
        Plant("Летнее разнотравье", base_bloom_threshold=18, bloom_duration=50, nectar_amount=600, seasonal_nectar_capacity=20000, min_day=150),
        
        # 5. Поздне-летнее цветение, смещено к августу
        Plant("Поздне-летний вид", base_bloom_threshold=21, bloom_duration=45, nectar_amount=550, seasonal_nectar_capacity=18000, min_day=190),
        
        # 6. Осенний вид, требует охлаждения после середины года
        Plant("Осенний вид", base_bloom_threshold=18, bloom_duration=60, nectar_amount=450, seasonal_nectar_capacity=15000, min_day=210, requires_temp_drop=True)
    ]
    # flora = [
    #     Plant("Очень ранний вид", base_bloom_threshold=8, bloom_duration=50, nectar_amount=300, seasonal_nectar_capacity=8000),
    #     Plant("Ранневесенний вид", base_bloom_threshold=10, bloom_duration=80, nectar_amount=400, seasonal_nectar_capacity=10000),
    #     Plant("Летнее разнотравье", base_bloom_threshold=11, bloom_duration=100, nectar_amount=600, seasonal_nectar_capacity=20000),
    #     Plant("Поздний вид", base_bloom_threshold=13, bloom_duration=70, nectar_amount=500, seasonal_nectar_capacity=15000),
    #     Plant("Поздне-летний вид", base_bloom_threshold=14, bloom_duration=90, nectar_amount=550, seasonal_nectar_capacity=18000),
    #     Plant("Осенний вид", base_bloom_threshold=12, bloom_duration=60, nectar_amount=450, seasonal_nectar_capacity=12000)
    # ]

    years_to_simulate = 100

    print("=== СТАРТ СИМУЛЯЦИИ ===\n")
    
    # Инициализация логгера для сбора данных
    logger = SimulationLogger()

    # ВНЕШНИЙ ЦИКЛ: Годы
    for year in range(1, years_to_simulate + 1):
        sync_days = 0
        warming = year * nature.warming_rate
        
        # Климатическая адаптация перед стартом весны (изменение температуры пробуждения и цветения)
        bees.adapt_to_climate(warming)
        for plant in flora:
            plant.adapt_to_climate(warming)

        # Сброс сезонных переменных
        bees.reset_for_next_year()
        for plant in flora:
            plant.reset_for_next_year()

        # ВНУТРЕННИЙ ЦИКЛ: Дни
        for day in range(1, 366):
            temp = nature.get_current_temp()

            # Обновление внутренних статусов
            for plant in flora:
                plant.update(day, temp)
            bees.check_status(temp, day)

            # Взаимодействие (поиск пропитания) — ДО проверки на стадийность,
            # чтобы пчелы могли найти еду до того как сдохнут
            if bees.population > 0 and bees.is_active:
                fed_today = False
                
                # Пчелы кормятся с первого цветущего вида, но при этом
                # могут опылить все доступные цветы в это же активное окно.
                for plant in flora:
                    if plant.is_blooming:
                        nectar = plant.harvest_nectar(bees.population)
                        if nectar > 0:
                            bees.eat(nectar)
                            plant.pollinate()
                            fed_today = True

                            # Дополнительное опыление других цветущих видов
                            for other in flora:
                                if other is not plant and other.is_blooming:
                                    other.pollinate()
                            break

                if fed_today:
                    sync_days += 1
                else:
                    # Рассинхрон: вылетели, но ни один вид не цветет (или все пусты)
                    bees.apply_flight_cost()

            nature.update()

        # --- ПОДВЕДЕНИЕ ИТОГОВ ГОДА ---
        bees.complete_year(sync_days)
        
        # Репродукция растений на основе визитов пчел
        for plant in flora:
            plant.reproduce()
        
        # Логирование метрик за год
        logger.log_year(year, bees, flora, nature)
        
        # Логирование результатов
        status = "Жива" if bees.population > 0 else "Погибла"
        active_flora = [p.name for p in flora if p.is_alive]
        
        print(f"Год {year}: Дней синхронизации = {sync_days} | Популяция пчел: {bees.population} ({status})")
        print(f"  Живая флора в экосистеме: {', '.join(active_flora) if active_flora else 'Нет выживших видов'}\n")

        # Условия досрочного прерывания
        if bees.population <= 0 and not active_flora:
            print(f"[!!!] Полный коллапс экосистемы к {year}-му году: вымерли и опылители, и растения.")
            break
        elif bees.population <= 0:
            print(f"[!] Популяция пчел погибла к {year}-му году. Оставшиеся растения обречены на вымирание.")
            break
    
    # ========== ВИЗУАЛИЗАЦИЯ И АНАЛИЗ РЕЗУЛЬТАТОВ ==========
    print_summary_statistics(logger)
    plot_simulation_results(logger, output_file='simulation_results.png')
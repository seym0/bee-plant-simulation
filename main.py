import math


class Nature:
    def __init__(self, base_temp=10, amplitude=15, warming_rate=0.02):
        self.day = 1
        self.year = 1
        self.base_temp = base_temp       # Базовая температура
        self.amplitude = amplitude       # Размах сезонов
        self.warming_rate = warming_rate # Скорость глобального потепления

    def get_current_temp(self):
        # Рассчитываем среднюю температуру для текущего года (тренд потепления)
        yearly_mean = self.base_temp + (self.year * self.warming_rate)
        
        # Рассчитываем сезонное колебание (синусоида)
        # 80 — это примерный сдвиг, чтобы весна начиналась в марте
        season_mod = self.amplitude * math.sin(2 * math.pi * (self.day - 80) / 365)
        
        return yearly_mean + season_mod

    def update(self):
        self.day += 1
        if self.day > 365:
            self.day = 1
            self.year += 1  


class Plant:
    def __init__(self, base_bloom_threshold=12, nectar_amount=500, seasonal_nectar_capacity=10000, bloom_duration=60, adaptation_rate=0.9):
        self.base_bloom_threshold = base_bloom_threshold  # Температура, при которой растение начинает цвести
        self.current_bloom_threshold = base_bloom_threshold # Этот порог будет адаптироваться с потеплением
        self.daily_nectar_supply = nectar_amount  # Максимум нектара, который растение может дать за один день цветения
        self.seasonal_nectar_capacity = seasonal_nectar_capacity # Максимальный запас нектара за сезон (ограничивает общее количество нектара, которое растение может произвести за сезон)
        self.nectar_available = seasonal_nectar_capacity # Текущий запас нектара, который может быть собран пчелами (уменьшается при сборе)
        self.daily_nectar_available = 0 # Количество нектара, доступного в текущий день (обновляется при каждом вызове check_status)
        self.bloom_duration = bloom_duration # Количество дней, в течение которых растение будет цвести после достижения порога
        self.bloom_days_left = 0 # Счетчик оставшихся дней цветения
        self.is_blooming = False # Флаг, указывающий, цветет ли растение в текущий день
        self.has_bloomed = False # Флаг, указывающий, запускалось ли цветение в этом году (чтобы не запускать его повторно при каждом достижении порога)
        self.is_pollinated = False # Флаг, указывающий, было ли растение опылено в текущем году (может влиять на адаптацию и воспроизводство)
        self.adaptation_rate = adaptation_rate # Растения адаптируются быстрее, чем пчелы, поэтому высокий коэффициент адаптации
    
    def adapt_to_climate(self, warming_degrees):
        # Растения адаптируются быстрее и начинают цвести раньше при потеплении
        self.current_bloom_threshold = self.base_bloom_threshold - (warming_degrees * self.adaptation_rate)
    
    def check_status(self, current_temp):
        if self.bloom_days_left > 0:
            self.is_blooming = True
        # Запускаем цветение только если в этом году оно еще не запускалось:
        elif current_temp >= self.current_bloom_threshold and self.nectar_available > 0 and not self.has_bloomed:
            self.is_blooming = True
            self.has_bloomed = True  # Запоминаем, что процесс пошел
            self.bloom_days_left = self.bloom_duration
        else:
            self.is_blooming = False

        if self.is_blooming and self.nectar_available > 0:
            self.daily_nectar_available = min(self.daily_nectar_supply, self.nectar_available)
        else:
            self.daily_nectar_available = 0

        if self.bloom_days_left > 0:
            self.bloom_days_left -= 1
            if self.bloom_days_left == 0:
                self.is_blooming = False

    def harvest_nectar(self, demand):
        nectar = min(self.daily_nectar_available, demand)
        self.daily_nectar_available -= nectar
        self.nectar_available -= nectar
        return nectar

    def pollinate(self):
        self.is_pollinated = True

    def reset_for_next_year(self):
        # Сброс флагов и восстановление запасов нектара перед новым сезоном
        self.is_blooming = False
        self.is_pollinated = False
        self.has_bloomed = False
        self.nectar_available = self.seasonal_nectar_capacity
        self.daily_nectar_available = 0
        self.bloom_days_left = 0


class BeePopulation:
    # не все пчелы просыпаются одновременно
    def __init__(self, initial_population=100, base_activation_temp=13, adaptation_rate=0.3):
        self.population = initial_population
        self.base_activation_temp = base_activation_temp
        self.current_activation_temp = base_activation_temp

        self.energy_reserves = 250
        self.base_energy = 250
        self.daily_metabolism = 0.18
        self.flight_cost = 0.12

        self.is_active = False # Изначально пчелы не активны, так как температура может быть ниже порога
        self.is_alive = True # Изначально пчелы живы, но могут погибнуть от голода или холода
        self.nectar_collected = 0
        self.active_days = 0
        self.starvation_days = 0
        self.max_starvation_days = 12

        # Пчелы адаптируются медленнее растений
        self.adaptation_rate = adaptation_rate

    def adapt_to_climate(self, warming_degrees):
        self.current_activation_temp = self.base_activation_temp - (warming_degrees * self.adaptation_rate)

    def check_status(self, current_temp):
        if self.population <= 0:
            self.is_alive = False
            self.is_active = False
            return

        self.energy_reserves -= self.population * self.daily_metabolism
        self.energy_reserves = max(0.0, self.energy_reserves)

        self.is_active = current_temp >= self.current_activation_temp and self.is_alive
        if self.is_active:
            self.active_days += 1

        if self.energy_reserves <= 0 or self.starvation_days > self.max_starvation_days:
            self.is_alive = False
            self.is_active = False

    def apply_flight_cost(self):
        if self.is_alive and self.is_active:
            self.energy_reserves -= self.population * self.flight_cost
            self.energy_reserves = max(0.0, self.energy_reserves)
            self.starvation_days += 1
            if self.energy_reserves <= 0 or self.starvation_days > self.max_starvation_days:
                self.is_alive = False
                self.is_active = False

    def eat(self, nectar_amount):
        if self.is_alive and self.is_active and nectar_amount > 0:
            self.energy_reserves += nectar_amount
            self.nectar_collected += nectar_amount
            self.starvation_days = 0

    def reset_for_next_year(self):
        self.is_active = False
        self.is_alive = True
        self.energy_reserves = self.base_energy
        self.nectar_collected = 0
        self.active_days = 0
        self.starvation_days = 0

    def complete_year(self, sync_days):
        if self.population <= 0:
            return

        pollination_quality = min(1.0, sync_days / 60.0)
        food_quality = min(1.0, self.nectar_collected / (self.population * 60.0))

        reproduction_rate = 0.6 + 0.4 * min(pollination_quality, food_quality)
        winter_loss = 0.2 + (1.0 - pollination_quality) * 0.35 + (1.0 - food_quality) * 0.2

        new_population = int(self.population * reproduction_rate * (1.0 - winter_loss))
        self.population = max(0, new_population)


# --- ГЛАВНЫЙ УПРАВЛЯЮЩИЙ ЦИКЛ (MAIN LOOP) ---

if __name__ == "__main__":
    # 1. Инициализация мира
    nature = Nature(base_temp=10, amplitude=15, warming_rate=0.02)
    # plant = Plant(base_bloom_threshold=12)
    # Инициализируем флору с разными порогами активации
    flora = [
        # Ранневесенние (просыпаются уже при 10°C, цветут 40 дней)
        Plant(base_bloom_threshold=10, bloom_duration=40, nectar_amount=300, seasonal_nectar_capacity=6000),
    
        # Летнее разнотравье (базовый порог 12°C, цветут 60 дней)
        Plant(base_bloom_threshold=12, bloom_duration=60, nectar_amount=500, seasonal_nectar_capacity=10000),
    
        # Позднецветущие (требуют стабильного тепла 15°C, цветут 45 дней)
        Plant(base_bloom_threshold=15, bloom_duration=45, nectar_amount=400, seasonal_nectar_capacity=8000)
        ]
    
    bees = BeePopulation(initial_population=100, base_activation_temp=13)

    years_to_simulate = 20
    results = []

    # ВНЕШНИЙ ЦИКЛ: Годы симуляции
    for year in range(1, years_to_simulate + 1):
        sync_days = 0
        warming = year * nature.warming_rate
        
        # Пересчет порогов (климатическая адаптация перед стартом года)
        for plant in flora:
            plant.adapt_to_climate(warming)
        bees.adapt_to_climate(warming)

        # Сброс состояний перед стартом очередного года
        bees.reset_for_next_year()
        for plant in flora:
            plant.reset_for_next_year()

        # ВНУТРЕННИЙ ЦИКЛ: Дни
        for day in range(1, 366):
            temp = nature.get_current_temp()

            # Обновление состояния растений и пчел
            for plant in flora:
                plant.check_status(temp)
            bees.check_status(temp)
            
            # 2. Логика поиска еды
            fed_today = False
            if bees.population > 0 and bees.is_active:
                # Пчелы ищут первое попавшееся цветущее растение с нектаром
                for plant in flora:
                    if plant.is_blooming:
                        nectar = plant.harvest_nectar(bees.population)
                        if nectar > 0:
                            bees.eat(nectar)
                            plant.pollinate()
                            fed_today = True
                            # Если наелись с этого вида флоры, другие сегодня не трогаем
                            break 
        
            # Успешный день синхронизации засчитывается, если нашли хоть какую-то еду
            if fed_today:
                sync_days += 1
            else:
                # Все отцвели или еще не распустились — пчелы тратят энергию впустую
                bees.apply_flight_cost()

            # Переход к следующему дню
            nature.update()

        # Естественный годичный жизненный цикл: взрослые пчелы погибают зимой,
        # а размер нового поколения зависит от успешности сезона.
        bees.complete_year(sync_days)
        results.append(sync_days)

        status = "Жива" if bees.population > 0 else "Погибла"
        print(f"Год {year}: Дней синхронизации = {sync_days} | Запас энергии = {bees.energy_reserves} | Популяция: {bees.population} ({status})")

        if bees.population <= 0:
            print(f"\n[!] Популяция пчел погибла к {year}-му году из-за климатического рассинхрона и неудачного воспроизводства.")
            break
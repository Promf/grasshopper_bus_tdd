"""Модульные тесты публичного интерфейса GrasshopperBus."""

from itertools import product

from grasshopper_bus import (
    BusError, CapacityError, DoorsClosedError, DoorsOpenError, GrasshopperBus,
    JumpTooFarError, NoEnergyError, SpringsStateError,
)
from tests.bus_state import (
    PUBLIC_FIELDS, BusTestCase, attempt, raised_by, typed_values,
)


class BusTests(BusTestCase):
    def test_TC_001_initial_state(self):
        """TC-001. Имя и стартовая энергия задают начальное состояние."""
        # Arrange
        for args, expected_energy in (
            (("Кузя",), 100), ((" Кузя ", 0), 0), (("К", 100), 100),
        ):
            with self.subTest(args=args):
                expected = {
                    "name": args[0], "energy": expected_energy, "passengers": 0,
                    "doors_open": False, "springs_charged": False,
                    "position_m": 0, "mileage_m": 0, "max_jump_m": 8,
                }
                # Act
                bus = GrasshopperBus(*args)
                # Assert
                self.assertBusState(bus, expected)

    def test_TC_002_reject_invalid_constructor_arguments(self):
        """TC-002. Недопустимое имя или энергия вызывают ValueError."""
        # Arrange
        bad_names = ("", "   ", "\t\n", None, 1)
        bad_energy = (-1, 101, True, 50.0, "50", None, float("nan"), float("inf"))
        cases = [(name, 100) for name in bad_names] + [("К", value) for value in bad_energy]
        for name, energy in cases:
            with self.subTest(name=name, energy=energy):
                # Act
                error = raised_by(GrasshopperBus, name, energy)
                # Assert
                self.assertIsInstance(error, ValueError)

    def test_TC_003_status_contract(self):
        """TC-003. Словарь и атрибуты дают восемь полей с точными типами и значениями."""
        # Arrange
        bus = GrasshopperBus("Кузя", 20)
        bus.move(-5)
        bus.charge_springs()
        bus.open_doors()
        bus.board(3)
        expected = typed_values({
            "name": "Кузя", "energy": 9, "passengers": 3, "doors_open": True,
            "springs_charged": True, "position_m": -5, "mileage_m": 5, "max_jump_m": 7,
        })
        before = typed_values({key: getattr(bus, key) for key in PUBLIC_FIELDS})
        # Act
        status = bus.get_status()
        # Assert
        self.assertIsInstance(status, dict)
        self.assertEqual(typed_values(status), expected)
        self.assertEqual(before, expected)
        self.assertEqual(typed_values({key: getattr(bus, key) for key in PUBLIC_FIELDS}), before)

    def test_TC_004_doors_take_requested_state(self):
        """TC-004. Первое и повторное открытие или закрытие сохраняют остальные поля."""
        # Arrange
        commands = (("open_doors", True), ("close_doors", False))
        for (method, target_open), repeat, charged in product(commands, (False, True), (False, True)):
            with self.subTest(method=method, repeat=repeat, charged=charged):
                bus = GrasshopperBus("Кузя")
                if charged:
                    bus.charge_springs()
                if method == "close_doors":
                    bus.open_doors()
                if repeat:
                    getattr(bus, method)()
                expected = dict(bus.get_status(), doors_open=target_open)
                # Act
                result = getattr(bus, method)()
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_005_board_updates_load_and_jump_limit(self):
        """TC-005. Посадка обновляет число пассажиров и предел прыжка при любой загрузке."""
        # Arrange
        limits = (8, 7, 7, 6, 6, 5, 5, 4)
        cases = [(0, total, limit, True) for total, limit in enumerate(limits, 1)]
        cases += [(total - 1, 1, limit, False) for total, limit in enumerate(limits, 1)]
        cases.append((1, 7, 4, False))
        for already, count, expected_limit, charged in cases:
            with self.subTest(already=already, count=count, charged=charged):
                bus = GrasshopperBus("Кузя")
                if charged:
                    bus.charge_springs()
                bus.open_doors()
                if already:
                    bus.board(already)
                expected = dict(
                    bus.get_status(), passengers=already + count, max_jump_m=expected_limit,
                )
                # Act
                result = bus.board(count)
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_006_reject_invalid_passenger_count(self):
        """TC-006. Проверка count предшествует проверке дверей при посадке и высадке."""
        # Arrange
        counts = (0, 9, -1, True, 1.0, "1", None)
        for method, count in product(("board", "alight"), counts):
            with self.subTest(method=method, count=count):
                bus = GrasshopperBus("Кузя")
                # Act
                result = attempt(bus, getattr(bus, method), count)
                # Assert
                self.assertRejected(ValueError, result)

    def test_TC_007_alight_all_passengers_success(self):
        """TC-007. Полная и частичная высадка сразу меняют загрузку и дальность."""
        # Arrange
        cases = ((8, 0, 8), (1, 7, 5))
        for (count, remaining, limit), charged in product(cases, (False, True)):
            with self.subTest(count=count, charged=charged):
                bus = GrasshopperBus("Кузя")
                if charged:
                    bus.charge_springs()
                bus.open_doors()
                bus.board(8)
                expected = dict(bus.get_status(), passengers=remaining, max_jump_m=limit)
                # Act
                result = bus.alight(count)
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_008_move_distance_and_cost(self):
        """TC-008. Знак задаёт направление, расход округляется вверх и не зависит от загрузки."""
        # Arrange
        for energy, load, prior, distance, remaining in (
            (100, 0, 0, 6, 98), (100, 0, 0, -5, 99), (1, 0, 0, 1, 0),
            (2, 0, 0, 6, 0), (2, 8, 0, 6, 0), (20, 0, 0, 100, 0), (20, 8, 0, -100, 0),
            (100, 0, 6, -5, 97), (100, 0, 100, -100, 60),
        ):
            with self.subTest(energy=energy, load=load, prior=prior, distance=distance):
                bus = GrasshopperBus("Кузя", energy)
                if prior:
                    bus.move(prior)
                if load:
                    bus.open_doors()
                    bus.board(load)
                    bus.close_doors()
                expected = dict(
                    bus.get_status(), position_m=prior + distance,
                    mileage_m=abs(prior) + abs(distance), energy=remaining,
                )
                # Act
                result = bus.move(distance)
                # Assert
                self.assertIs(type(result), int)
                self.assertEqual(result, abs(distance))
                self.assertBusState(bus, expected)

    def test_TC_009_reject_invalid_move_distance(self):
        """TC-009. Ошибка аргумента езды имеет приоритет над всеми блокировками."""
        # Arrange
        distances = (0, 101, -101, True, 1.0, "1", None, float("nan"), float("inf"))
        for distance, blocked in product(distances, (False, True)):
            with self.subTest(distance=distance, blocked=blocked):
                bus = GrasshopperBus("Кузя", 10 if blocked else 100)
                if blocked:
                    bus.charge_springs()
                    bus.open_doors()
                # Act
                result = attempt(bus, bus.move, distance)
                # Assert
                self.assertRejected(ValueError, result)

    def test_TC_010_reject_move_without_energy(self):
        """TC-010. Езда при нехватке энергии сохраняет состояние."""
        # Arrange
        for energy, distance in ((1, 6), (0, 1)):
            with self.subTest(energy=energy, distance=distance):
                bus = GrasshopperBus("Кузя", energy)
                # Act
                result = attempt(bus, bus.move, distance)
                # Assert
                self.assertRejected(NoEnergyError, result)

    def test_TC_011_move_interlock_priority(self):
        """TC-011. Открытые двери приоритетнее пружин, пружины приоритетнее нехватки энергии."""
        # Arrange
        for charged, opened, error in (
            (True, True, DoorsOpenError),
            (False, True, DoorsOpenError),
            (True, False, SpringsStateError),
        ):
            with self.subTest(charged=charged, opened=opened):
                bus = GrasshopperBus("Кузя", 10 if charged else 0)
                if charged:
                    bus.charge_springs()
                if opened:
                    bus.open_doors()
                # Act
                result = attempt(bus, bus.move, 1)
                # Assert
                self.assertRejected(error, result)

    def test_TC_012_charge_springs_costs_ten(self):
        """TC-012. Подготовка прыжка списывает ровно десять единиц."""
        # Arrange
        for energy, remaining in ((10, 0), (100, 90)):
            with self.subTest(energy=energy):
                bus = GrasshopperBus("Кузя", energy)
                expected = dict(bus.get_status(), energy=remaining, springs_charged=True)
                # Act
                result = bus.charge_springs()
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_013_release_springs_without_refund(self):
        """TC-013. Сброс доступен при открытых дверях и при уже разряженных пружинах."""
        # Arrange
        for charged, opened in ((True, True), (True, False), (False, True), (False, False)):
            with self.subTest(charged=charged, opened=opened):
                bus = GrasshopperBus("Кузя")
                if charged:
                    bus.charge_springs()
                if opened:
                    bus.open_doors()
                expected = dict(bus.get_status(), springs_charged=False)
                # Act
                result = bus.release_springs()
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_014_jump_within_current_limit(self):
        """TC-014. Пустой автобус прыгает на ±8 м, полный на ±4 м с тем же расходом."""
        # Arrange
        for load, prior, distance, energy in (
            (0, 0, 8, 90), (0, 0, -8, 90), (8, 0, 4, 90), (8, 0, -4, 90),
            (0, 8, -8, 80),
        ):
            with self.subTest(load=load, prior=prior, distance=distance):
                bus = GrasshopperBus("Кузя")
                if prior:
                    bus.charge_springs()
                    bus.jump(prior)
                bus.charge_springs()
                if load:
                    bus.open_doors()
                    bus.board(load)
                    bus.close_doors()
                expected = dict(
                    bus.get_status(), energy=energy, springs_charged=False,
                    position_m=prior + distance, mileage_m=abs(prior) + abs(distance),
                )
                # Act
                result = bus.jump(distance)
                # Assert
                self.assertIs(type(result), int)
                self.assertEqual(result, abs(distance))
                self.assertBusState(bus, expected)

    def test_TC_015_reject_invalid_jump_distance(self):
        """TC-015. Ошибка абсолютного диапазона и типа прыжка предшествует блокировкам."""
        # Arrange
        distances = (0, 9, -9, True, 1.0, "1", None, float("nan"), float("inf"))
        for distance, boarding in product(distances, (False, True)):
            with self.subTest(distance=distance, boarding=boarding):
                bus = GrasshopperBus("Кузя")
                if boarding:
                    bus.open_doors()
                    bus.board(8)
                # Act
                result = attempt(bus, bus.jump, distance)
                # Assert
                self.assertRejected(ValueError, result)

    def test_TC_016_reject_loaded_jump_beyond_limit(self):
        """TC-016. У полного автобуса отказ при прыжке на ±5 м сохраняет все поля."""
        # Arrange
        for distance in (5, -5):
            with self.subTest(distance=distance):
                bus = GrasshopperBus("Кузя")
                bus.charge_springs()
                bus.open_doors()
                bus.board(8)
                bus.close_doors()
                # Act
                result = attempt(bus, bus.jump, distance)
                # Assert
                self.assertRejected(JumpTooFarError, result)

    def test_TC_017_prepaid_jump_at_zero_energy(self):
        """TC-017. При нулевом остатке энергии можно выполнить оплаченный прыжок."""
        # Arrange
        bus = GrasshopperBus("Кузя", 10)
        bus.charge_springs()
        expected = dict(bus.get_status(), energy=0, springs_charged=False, position_m=1, mileage_m=1)
        # Act
        result = bus.jump(1)
        # Assert
        self.assertIs(type(result), int)
        self.assertEqual(result, 1)
        self.assertBusState(bus, expected)

    def test_TC_018_recharge_adds_to_energy(self):
        """TC-018. Пополнение прибавляет amount к остатку, включая случай 20 + 5 = 25."""
        # Arrange
        for initial, amount, expected_energy, during_boarding in (
            (20, 5, 25, False), (0, 1, 1, False), (30, 5, 25, True),
        ):
            with self.subTest(initial=initial, amount=amount, during_boarding=during_boarding):
                bus = GrasshopperBus("Кузя", initial)
                if during_boarding:
                    bus.charge_springs()
                    bus.open_doors()
                    bus.board(2)
                expected = dict(bus.get_status(), energy=expected_energy)
                # Act
                result = bus.recharge(amount)
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_019_domain_errors_share_base(self):
        """TC-019. BusError непосредственно наследует Exception, доменные ошибки наследуют BusError."""
        # Arrange
        cases = (
            (BusError, Exception), (DoorsOpenError, BusError), (DoorsClosedError, BusError),
            (CapacityError, BusError), (NoEnergyError, BusError),
            (SpringsStateError, BusError), (JumpTooFarError, BusError),
        )
        for error, parent in cases:
            with self.subTest(error=error.__name__):
                # Act
                bases = error.__bases__ if error is BusError else error.__mro__[1:]
                # Assert
                self.assertIn(parent, bases)

    def test_TC_020_jump_interlock_priority(self):
        """TC-020. Перед прыжком проверяются двери, заряд и дальность, в таком порядке."""
        # Arrange
        for load, opened, spring_state, distance, error in (
            (0, True, "empty", 1, DoorsOpenError),
            (0, False, "empty", 1, SpringsStateError),
            (0, False, "used", 1, SpringsStateError),
            (8, True, "empty", 5, DoorsOpenError),
            (8, True, "charged", 5, DoorsOpenError),
            (8, False, "empty", 5, SpringsStateError),
            (8, False, "empty", 1, SpringsStateError),
            (8, False, "used", 1, SpringsStateError),
            (8, False, "charged", 5, JumpTooFarError),
        ):
            with self.subTest(load=load, opened=opened, springs=spring_state, distance=distance):
                bus = GrasshopperBus("Кузя")
                if load:
                    bus.open_doors()
                    bus.board(load)
                    bus.close_doors()
                if spring_state != "empty":
                    bus.charge_springs()
                if spring_state == "used":
                    bus.jump(4)
                if opened:
                    bus.open_doors()
                # Act
                result = attempt(bus, bus.jump, distance)
                # Assert
                self.assertRejected(error, result)

    def test_TC_025_public_attributes_are_read_only(self):
        """TC-025. Присваивать полю запрещено даже его текущее значение."""
        # Arrange
        for name in PUBLIC_FIELDS:
            with self.subTest(field=name):
                bus = GrasshopperBus("Кузя")
                value = getattr(bus, name)
                # Act
                result = attempt(bus, setattr, bus, name, value)
                # Assert
                self.assertRejected(AttributeError, result)

    def test_TC_026_status_is_detached(self):
        """TC-026. Редактирование выданного словаря не меняет автобус и другой снимок."""
        # Arrange
        bus = GrasshopperBus("Кузя")
        first = bus.get_status()
        second = bus.get_status()
        expected = dict(second)
        # Act
        first["energy"] = 0
        # Assert
        self.assertIsNot(first, second)
        self.assertEqual(typed_values(second), typed_values(expected))
        self.assertBusState(bus, expected)

    def test_TC_027_reject_passenger_operations_doors_closed(self):
        """TC-027. Допустимое количество при закрытых дверях даёт DoorsClosedError."""
        # Arrange
        for method, load in (("board", 0), ("board", 8), ("alight", 0), ("alight", 1)):
            with self.subTest(method=method, load=load):
                bus = GrasshopperBus("Кузя")
                if load:
                    bus.open_doors()
                    bus.board(load)
                    bus.close_doors()
                # Act
                result = attempt(bus, getattr(bus, method), 1)
                # Assert
                self.assertRejected(DoorsClosedError, result)

    def test_TC_028_reject_alight_empty_bus(self):
        """TC-028. Нельзя высадить больше пассажиров, чем находится в автобусе."""
        # Arrange
        for load, count in ((0, 1), (1, 2)):
            with self.subTest(load=load, count=count):
                bus = GrasshopperBus("Кузя")
                bus.open_doors()
                if load:
                    bus.board(load)
                # Act
                result = attempt(bus, bus.alight, count)
                # Assert
                self.assertRejected(CapacityError, result)

    def test_TC_029_reject_boarding_above_capacity(self):
        """TC-029. Посадка сверх восьми мест запрещена при открытых дверях."""
        # Arrange
        bus = GrasshopperBus("Кузя")
        bus.open_doors()
        bus.board(8)
        # Act
        result = attempt(bus, bus.board, 1)
        # Assert
        self.assertRejected(CapacityError, result)

    def test_TC_030_spring_charge_refusal_priority(self):
        """TC-030. При зарядке проверяются по порядку двери, имеющийся заряд и энергия."""
        # Arrange
        for initial, charged, opened, error in (
            (9, False, False, NoEnergyError), (9, False, True, DoorsOpenError),
            (10, True, False, SpringsStateError), (10, True, True, DoorsOpenError),
        ):
            with self.subTest(initial=initial, charged=charged, opened=opened):
                bus = GrasshopperBus("Кузя", initial)
                if charged:
                    bus.charge_springs()
                if opened:
                    bus.open_doors()
                # Act
                result = attempt(bus, bus.charge_springs)
                # Assert
                self.assertRejected(error, result)

    def test_TC_031_recharge_stops_at_one_hundred(self):
        """TC-031. При достижении и превышении предела энергия равна 100."""
        # Arrange
        for energy, amount, boarding in (
            (95, 5, False), (1, 100, False), (100, 1, False), (100, 100, True),
        ):
            with self.subTest(energy=energy, amount=amount, boarding=boarding):
                bus = GrasshopperBus("Кузя", energy)
                if boarding:
                    bus.charge_springs()
                    bus.open_doors()
                expected = dict(bus.get_status(), energy=100)
                # Act
                result = bus.recharge(amount)
                # Assert
                self.assertIsNone(result)
                self.assertBusState(bus, expected)

    def test_TC_032_reject_invalid_recharge(self):
        """TC-032. Неверный тип или величина пополнения вызывают ValueError."""
        # Arrange
        for amount in (0, 101, -1, True, 1.0, "1", None, float("nan"), float("inf")):
            with self.subTest(amount=amount):
                bus = GrasshopperBus("Кузя", 20)
                # Act
                result = attempt(bus, bus.recharge, amount)
                # Assert
                self.assertRejected(ValueError, result)

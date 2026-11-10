"""Контрактные тесты автора Агапова А. М. Реализацию выполняет D."""
import unittest
from grasshopper_bus import (GrasshopperBus, BusError, DoorsOpenError,
    DoorsClosedError, CapacityError, NoEnergyError, SpringsStateError,
    JumpTooFarError)
from tests.pilot import Pilot

class BusTests(unittest.TestCase):
    def setUp(self):
        self.bus = GrasshopperBus("Кузя")

    def checked_status(self):
        """Полный снимок и точные типы публичного состояния по SPEC §3.3."""
        expected_types = {
            "name": str, "energy": int, "passengers": int,
            "doors_open": bool, "springs_charged": bool,
            "position_m": int, "mileage_m": int, "max_jump_m": int,
        }
        status = self.bus.get_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(set(status), set(expected_types))
        for key, expected_type in expected_types.items():
            self.assertIs(type(status[key]), expected_type, key)
            self.assertIs(type(getattr(self.bus, key)), expected_type, key)
            self.assertEqual(getattr(self.bus, key), status[key], key)
        return dict(status)

    def tearDown(self):
        self.checked_status()

    def reject(self, error, method, *args):
        before = self.checked_status()
        with self.assertRaises(error):
            method(*args)
        after = self.checked_status()
        self.assertEqual(after, before)
        for key in before:
            self.assertIs(type(after[key]), type(before[key]), key)

    def test_TC_001_initial(self):
        """TC-001. Новый GrasshopperBus("Кузя"): полный начальный снимок."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.assertEqual(self.bus.get_status(), {"name":"Кузя", "energy":100, "passengers":0, "doors_open":False, "springs_charged":False, "position_m":0, "mileage_m":0, "max_jump_m":8})

    def test_TC_002_constructor(self):
        """TC-002. Некорректные параметры конструктора; energy=0 и 100 допустимы."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        for name in ("", "   ", None, 1):
            with self.subTest(name=name), self.assertRaises(ValueError):
                GrasshopperBus(name)
        for energy in (-1, 101, True, 50.0, "50", None, float("nan"), float("inf")):
            with self.subTest(energy=energy), self.assertRaises(ValueError):
                GrasshopperBus("Кузя", energy)
        self.assertEqual(GrasshopperBus("К", 0).energy, 0)
        self.assertEqual(GrasshopperBus("К", 100).energy, 100)
        self.assertEqual(GrasshopperBus(" Кузя ").name, " Кузя ")

    def test_TC_003_public_state(self):
        """TC-003. Все атрибуты read-only, снимок независим, экземпляры независимы."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        before=self.bus.get_status()
        for key, value in before.items():
            with self.subTest(key=key), self.assertRaises(AttributeError):
                setattr(self.bus, key, value)
        copy=self.bus.get_status()
        self.assertIsNot(copy, self.bus.get_status())
        for key, value in before.items():
            self.assertEqual(getattr(self.bus, key), value)
        copy["energy"]=0
        self.assertEqual(self.bus.get_status(), before)
        other=GrasshopperBus("Другой")
        self.bus.move(5)
        self.assertEqual(other.energy,100)
        for key,value in before.items():
            if key in ("doors_open","springs_charged"):
                self.assertIs(type(value),bool)
            elif key != "name":
                self.assertIs(type(value),int)

    def test_TC_004_doors(self):
        """TC-004. Открытие и закрытие идемпотентны, возвращают None."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        # Act
        result = self.bus.open_doors()
        # Assert
        self.assertIsNone(result)
        # Act
        result = self.bus.open_doors()
        # Assert
        self.assertIsNone(result)
        self.assertTrue(self.bus.doors_open)
        # Act
        result = self.bus.close_doors()
        # Assert
        self.assertIsNone(result)
        # Act
        result = self.bus.close_doors()
        # Assert
        self.assertIsNone(result)
        self.assertFalse(self.bus.doors_open)
        self.assertEqual(self.bus.energy,100)

    def test_TC_005_boarding(self):
        """TC-005. Посадка 1+7 до вместимости; перерасход вместимости запрещён."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus.open_doors()
        # Act
        result = self.bus.board(1)
        # Assert
        self.assertIsNone(result)
        self.bus.board(7)
        self.assertEqual((self.bus.passengers,self.bus.max_jump_m), (8,4))
        self.reject(CapacityError,self.bus.board,1)

    def test_TC_006_passenger_errors(self):
        """TC-006. Типы и диапазоны количества; закрытые двери; высадка лишних."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        for method in (self.bus.board,self.bus.alight):
            for count in (0,9,-1,True,1.0,"1",None):
                self.reject(ValueError,method,count)
            self.reject(DoorsClosedError,method,1)
        self.bus.open_doors()
        self.reject(CapacityError,self.bus.alight,1)
        self.bus.board(8)
        # Act
        result = self.bus.alight(8)
        # Assert
        self.assertIsNone(result)
        self.assertEqual(self.bus.passengers,0)

    def test_TC_007_load_jump_limit(self):
        """TC-007. Дальность при числе пассажиров 0…8: 8,8,7,7,6,6,5,5,4."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus.open_doors()
        for count,limit in enumerate((8,8,7,7,6,6,5,5,4)):
            if count:
                self.bus.board(1)
            self.assertEqual(self.bus.max_jump_m,limit)
        self.bus.alight(1)
        self.assertEqual(self.bus.max_jump_m,5)

    def test_TC_008_movement(self):
        """TC-008. move(6),move(-5): возвраты 6/5, позиция 1, пробег 11, энергия 97."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        # Act
        result = self.bus.move(6)
        # Assert
        self.assertEqual(result, 6)
        # Act
        result = self.bus.move(-5)
        # Assert
        self.assertEqual(result, 5)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy),(1,11,97))

    def test_TC_009_movement_arguments(self):
        """TC-009. Ноль и неверные типы/границы запрещены; ±100 разрешены."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        for distance in (0,101,-101,True,1.0,"1",None):
            self.reject(ValueError,self.bus.move,distance)
        self.bus.move(100)
        self.bus.move(-100)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy),(0,200,60))

    def test_TC_010_movement_energy(self):
        """TC-010. Ровно 2 энергии для 6 м; при 1 отказ; ноль энергии не даёт ехать."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus=GrasshopperBus("К",2)
        self.bus.move(6)
        self.assertEqual(self.bus.energy,0)
        self.reject(NoEnergyError,self.bus.move,1)
        self.bus=GrasshopperBus("К",1)
        self.reject(NoEnergyError,self.bus.move,6)

    def test_TC_011_movement_interlocks(self):
        """TC-011. Приоритет ValueError → DoorsOpenError → SpringsStateError → энергия."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus=GrasshopperBus("К",10)
        self.bus.charge_springs()
        self.bus.open_doors()
        self.reject(ValueError,self.bus.move,0)
        self.reject(DoorsOpenError,self.bus.move,1)
        self.bus.close_doors()
        self.reject(SpringsStateError,self.bus.move,1)
        self.bus=GrasshopperBus("К",0)
        self.bus.open_doors()
        self.reject(DoorsOpenError,self.bus.move,1)

    def test_TC_012_spring_charge(self):
        """TC-012. Зарядка стоит 10, повтор запрещён; точный запас и нехватка."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus=GrasshopperBus("К",10)
        # Act
        result = self.bus.charge_springs()
        # Assert
        self.assertIsNone(result)
        self.assertEqual((self.bus.energy,self.bus.springs_charged),(0,True))
        self.reject(SpringsStateError,self.bus.charge_springs)
        self.bus=GrasshopperBus("К",9)
        self.reject(NoEnergyError,self.bus.charge_springs)
        self.bus.open_doors()
        self.reject(DoorsOpenError,self.bus.charge_springs)

    def test_TC_013_spring_release(self):
        """TC-013. Сброс заряда не возвращает энергию; повтор разрешён, двери не мешают."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        # Act
        result = self.bus.release_springs()
        # Assert
        self.assertIsNone(result)
        self.bus.charge_springs()
        self.bus.open_doors()
        # Act
        result = self.bus.release_springs()
        # Assert
        self.assertIsNone(result)
        self.assertEqual((self.bus.energy,self.bus.springs_charged),(90,False))

    def test_TC_014_jump(self):
        """TC-014. Прыжок ±8; расход только при зарядке; позиция и пробег."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus.charge_springs()
        # Act
        result = self.bus.jump(8)
        # Assert
        self.assertEqual(result, 8)
        self.assertEqual((self.bus.energy,self.bus.position_m,self.bus.mileage_m,self.bus.springs_charged),(90,8,8,False))
        self.bus.charge_springs()
        # Act
        result = self.bus.jump(-8)
        # Assert
        self.assertEqual(result, 8)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m),(0,16))
        self.reject(SpringsStateError,self.bus.jump,1)

    def test_TC_015_jump_arguments(self):
        """TC-015. Некорректные дистанции имеют приоритет; без заряда отказ."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        for distance in (0,9,-9,True,1.0,"1",None):
            self.reject(ValueError,self.bus.jump,distance)
        self.reject(SpringsStateError,self.bus.jump,1)
        self.bus.open_doors()
        self.reject(DoorsOpenError,self.bus.jump,1)

    def test_TC_016_loaded_jump(self):
        """TC-016. Полный автобус: ±5 запрещены, ±4 разрешены; отказ атомарен."""
        for direction in (1, -1):
            with self.subTest(direction=direction):
                # Arrange: отдельный объект для каждого направления.
                self.bus = GrasshopperBus("Кузя")
                self.bus.charge_springs()
                self.bus.open_doors()
                self.bus.board(8)
                self.bus.close_doors()
                expected = {
                    "name": "Кузя", "energy": 90, "passengers": 8,
                    "doors_open": False, "springs_charged": True,
                    "position_m": 0, "mileage_m": 0, "max_jump_m": 4,
                }
                self.assertEqual(self.checked_status(), expected)
                # Act / Assert: превышение предела сохраняет весь снимок.
                self.reject(JumpTooFarError, self.bus.jump, direction * 5)
                # Act: точная граница допустима с прежним зарядом.
                result = self.bus.jump(direction * 4)
                # Assert: полный результат и состояние.
                self.assertIs(type(result), int)
                self.assertEqual(result, 4)
                expected.update(position_m=direction * 4, mileage_m=4,
                                springs_charged=False)
                self.assertEqual(self.checked_status(), expected)

    def test_TC_017_zero_energy_jump(self):
        """TC-017. Предварительно оплаченный прыжок разрешён при нулевой энергии."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus=GrasshopperBus("К",10)
        self.bus.charge_springs()
        self.bus.jump(1)
        self.assertEqual((self.bus.energy,self.bus.position_m),(0,1))

    def test_TC_018_recharge(self):
        """TC-018. Пополнение 1…100 с насыщением, неверные аргументы; открытые двери и заряд пружин допустимы."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus=GrasshopperBus("К",0)
        # Act
        result = self.bus.recharge(1)
        # Assert
        self.assertIsNone(result)
        self.assertEqual(self.bus.energy,1)
        self.bus.recharge(100)
        self.assertEqual(self.bus.energy,100)
        for amount in (0,101,-1,True,1.0,"1",None):
            self.reject(ValueError,self.bus.recharge,amount)
        self.bus.charge_springs()
        self.bus.open_doors()
        self.bus.recharge(100)
        self.assertEqual((self.bus.energy,self.bus.springs_charged),(100,True))
        before=self.bus.get_status()
        self.bus.recharge(1)
        self.assertEqual(self.bus.get_status(),before)

        # Arrange: ненулевой запас; сумма остаётся ниже ограничения 100.
        self.bus = GrasshopperBus("Кузя", energy=20)
        expected = self.checked_status()
        expected["energy"] = 25
        # Act
        result = self.bus.recharge(5)
        # Assert: amount прибавляется, остальные поля сохраняются.
        self.assertIsNone(result)
        self.assertEqual(self.checked_status(), expected)

    def test_TC_019_all_errors(self):
        """TC-019. Каждое доменное исключение наследует BusError."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        for error in (DoorsOpenError,DoorsClosedError,CapacityError,NoEnergyError,SpringsStateError,JumpTooFarError):
            self.assertTrue(issubclass(error,BusError))
        self.assertTrue(issubclass(BusError,Exception))

    def test_TC_020_jump_priority(self):
        """TC-020. Для полного автобуса: сначала двери, потом заряд, потом дальность."""
        # Arrange: исходный автобус из setUp.
        # Подслучаи ниже: подготовка → вызов → проверка.
        self.bus.open_doors()
        self.bus.board(8)
        self.reject(DoorsOpenError,self.bus.jump,5)
        self.bus.close_doors()
        self.reject(SpringsStateError,self.bus.jump,5)
        self.bus.charge_springs()
        self.reject(JumpTooFarError,self.bus.jump,5)


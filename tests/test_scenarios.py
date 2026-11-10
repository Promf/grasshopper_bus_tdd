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

    def test_TC_021_route(self):
        """TC-021. Маршрут: посадка 4, езда 10, зарядка, прыжок 6, езда -5, высадка 4. Итог position=11,mileage=21,energy=87."""
        pilot=Pilot(self.bus)
        # Given: пустой автобус с полным зарядом.
        pilot.pick_up(4)
        # When: доехать до ямы и перепрыгнуть её.
        pilot.drive(10)
        pilot.prepare_jump()
        self.assertEqual(self.bus.energy,88)
        pilot.jump(6)
        # Then: после приземления можно ехать и высаживать людей.
        pilot.drive(-5)
        pilot.drop_off(4)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy,self.bus.passengers),(11,21,87,0))

    def test_TC_022_heavy_bus(self):
        """TC-022. Восемь пассажиров; прыжок 6 отвергнут; высадка 4; тот же заряд позволяет 6 м. Итог energy=90,passengers=4."""
        pilot=Pilot(self.bus)
        # Given: полный автобус, пружины заряжены.
        pilot.pick_up(8)
        pilot.prepare_jump()
        # When: дальность слишком велика.
        self.reject(JumpTooFarError,pilot.jump,6)
        # Then: высадка части пассажиров позволяет использовать прежний заряд.
        pilot.drop_off(4)
        self.assertTrue(self.bus.springs_charged)
        pilot.jump(6)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy,self.bus.passengers),(6,6,90,4))

    def test_TC_023_last_charge(self):
        """TC-023. energy=12; езда 6, зарядка до нуля, прыжок 8; езда запрещена; пополнение 5, езда -5. Итог position=9,mileage=19,energy=4."""
        self.bus=GrasshopperBus("К",12)
        pilot=Pilot(self.bus)
        # Given: малый запас энергии.
        pilot.drive(6)
        pilot.prepare_jump()
        self.assertEqual(self.bus.energy,0)
        # When: запасённая энергия пружин обеспечивает прыжок.
        pilot.jump(8)
        self.reject(NoEnergyError,pilot.drive,1)
        # Then: после пополнения можно двигаться на колёсах.
        pilot.recharge(5)
        pilot.drive(-5)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy),(9,19,4))

    def test_TC_024_cancelled_jump(self):
        """TC-024. Открытые двери блокируют езду; заряд пружин блокирует езду; сброс и возврат. Итог position=0,mileage=10,energy=88."""
        pilot=Pilot(self.bus)
        # Given: двери открыты, пассажиры ещё садятся.
        self.bus.open_doors()
        self.reject(DoorsOpenError,pilot.drive,5)
        self.bus.board(2)
        self.bus.close_doors()
        # When: план прыжка отменён после зарядки.
        pilot.prepare_jump()
        self.reject(SpringsStateError,pilot.drive,5)
        pilot.cancel_jump()
        # Then: езда снова доступна, энергия зарядки не возвращается.
        pilot.drive(5)
        pilot.drive(-5)
        self.assertEqual((self.bus.position_m,self.bus.mileage_m,self.bus.energy,self.bus.passengers),(0,10,88,2))


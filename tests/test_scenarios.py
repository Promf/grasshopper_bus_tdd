"""Сценарии поездок из §4.2 ТЗ."""

from grasshopper_bus import (
    DoorsOpenError, GrasshopperBus, JumpTooFarError, NoEnergyError, SpringsStateError,
)
from tests.bus_state import BusTestCase, attempt, typed_values
from tests.pilot import Pilot


class RouteTests(BusTestCase):
    def test_TC_021_trip_over_a_ditch(self):
        """TC-021. Автобус перепрыгивает яму и высаживает четырёх пассажиров на обратном пути."""
        # Given
        bus = GrasshopperBus("Кузя")
        pilot = Pilot(bus)
        # When
        pilot.pick_up(4)
        pilot.drive(10)
        pilot.prepare_jump()
        # Then
        self.assertEqual((bus.energy, bus.max_jump_m), (88, 6))
        self.assertTrue(bus.springs_charged)
        # When
        pilot.jump(6)
        pilot.drive(-5)
        pilot.drop_off(4)
        # Then
        self.assertBusState(bus, {
            "name": "Кузя", "energy": 87, "passengers": 0, "doors_open": False,
            "springs_charged": False, "position_m": 11, "mileage_m": 21, "max_jump_m": 8,
        })

    def test_TC_022_unload_and_retry_jump(self):
        """TC-022. После отказа пилот высаживает четверых и повторяет прыжок без подзарядки."""
        # Given
        bus = GrasshopperBus("Кузя")
        pilot = Pilot(bus)
        pilot.pick_up(8)
        pilot.prepare_jump()
        # When
        result = attempt(bus, pilot.jump, 6)
        # Then
        self.assertRejected(JumpTooFarError, result)
        self.assertEqual((bus.energy, bus.max_jump_m), (90, 4))
        self.assertTrue(bus.springs_charged)
        # When
        pilot.drop_off(4)
        distance = pilot.jump(6)
        # Then
        self.assertIs(type(distance), int)
        self.assertEqual(distance, 6)
        self.assertBusState(bus, {
            "name": "Кузя", "energy": 90, "passengers": 4, "doors_open": False,
            "springs_charged": False, "position_m": 6, "mileage_m": 6, "max_jump_m": 6,
        })

    def test_TC_023_last_charge(self):
        """TC-023. Автобус прыгает при нулевой энергии и продолжает поездку после подзарядки."""
        # Given
        bus = GrasshopperBus("Кузя", 12)
        pilot = Pilot(bus)
        # When
        pilot.drive(6)
        pilot.prepare_jump()
        # Then
        self.assertEqual(bus.energy, 0)
        self.assertTrue(bus.springs_charged)
        # When
        distance = pilot.jump(8)
        # Then
        self.assertIs(type(distance), int)
        self.assertEqual((distance, bus.position_m, bus.mileage_m, bus.energy), (8, 14, 14, 0))
        self.assertFalse(bus.springs_charged)
        # When
        result = attempt(bus, pilot.drive, 1)
        # Then
        self.assertRejected(NoEnergyError, result)
        # When
        pilot.recharge(5)
        pilot.drive(-5)
        # Then
        self.assertBusState(bus, {
            "name": "Кузя", "energy": 4, "passengers": 0, "doors_open": False,
            "springs_charged": False, "position_m": 9, "mileage_m": 19, "max_jump_m": 8,
        })

    def test_TC_024_cancel_jump_then_drive(self):
        """TC-024. Пилот закрывает двери после посадки и отменяет прыжок для езды."""
        # Given
        bus = GrasshopperBus("Кузя")
        pilot = Pilot(bus)
        pilot.open_doors()
        # When
        result = attempt(bus, pilot.drive, 5)
        # Then
        self.assertRejected(DoorsOpenError, result)
        # When
        pilot.finish_boarding(2)
        pilot.prepare_jump()
        result = attempt(bus, pilot.drive, 5)
        # Then
        self.assertRejected(SpringsStateError, result)
        self.assertTrue(bus.springs_charged)
        self.assertEqual(bus.energy, 90)
        # When
        pilot.cancel_jump()
        pilot.drive(5)
        pilot.drive(-5)
        # Then
        self.assertBusState(bus, {
            "name": "Кузя", "energy": 88, "passengers": 2, "doors_open": False,
            "springs_charged": False, "position_m": 0, "mileage_m": 10, "max_jump_m": 7,
        })

    def test_TC_033_trip_leaves_reserve_bus_at_depot(self):
        """TC-033. Резервный автобус остаётся на стоянке, пока второй выполняет рейс."""
        # Given
        bus = GrasshopperBus("Рейсовый")
        reserve = GrasshopperBus("Резервный", 35)
        pilot = Pilot(bus)
        departure = bus.get_status()
        # When
        pilot.pick_up(2)
        pilot.drive(5)
        pilot.prepare_jump()
        pilot.jump(7)
        # Then
        self.assertBusState(bus, {
            "name": "Рейсовый", "energy": 89, "passengers": 2, "doors_open": False,
            "springs_charged": False, "position_m": 12, "mileage_m": 12, "max_jump_m": 7,
        })
        initial = {
            "name": "Рейсовый", "energy": 100, "passengers": 0, "doors_open": False,
            "springs_charged": False, "position_m": 0, "mileage_m": 0, "max_jump_m": 8,
        }
        self.assertEqual(typed_values(departure), typed_values(initial))
        self.assertBusState(reserve, {**initial, "name": "Резервный", "energy": 35})

    def test_TC_034_shorten_jump_without_unloading(self):
        """TC-034. С полной загрузкой после отказа пилот укорачивает прыжок до четырёх метров."""
        for direction in (1, -1):
            with self.subTest(direction=direction):
                # Given
                bus = GrasshopperBus("Кузя")
                pilot = Pilot(bus)
                pilot.pick_up(8)
                pilot.prepare_jump()
                # When
                result = attempt(bus, pilot.jump, direction * 5)
                # Then
                self.assertRejected(JumpTooFarError, result)
                self.assertEqual((bus.energy, bus.max_jump_m), (90, 4))
                self.assertTrue(bus.springs_charged)
                # When
                distance = pilot.jump(direction * 4)
                # Then
                self.assertIs(type(distance), int)
                self.assertEqual(distance, 4)
                self.assertBusState(bus, {
                    "name": "Кузя", "energy": 90, "passengers": 8, "doors_open": False,
                    "springs_charged": False, "position_m": direction * 4,
                    "mileage_m": 4, "max_jump_m": 4,
                })

    def test_TC_035_top_up_before_preparing_jump(self):
        """TC-035. Одной дополнительной единицы энергии хватает, чтобы зарядить пружины и прыгнуть."""
        # Given
        bus = GrasshopperBus("Кузя", 10)
        pilot = Pilot(bus)
        # When
        pilot.drive(5)
        result = attempt(bus, pilot.prepare_jump)
        # Then
        self.assertRejected(NoEnergyError, result)
        self.assertEqual(bus.energy, 9)
        self.assertFalse(bus.springs_charged)
        # When
        pilot.recharge(1)
        pilot.prepare_jump()
        distance = pilot.jump(-8)
        # Then
        self.assertIs(type(distance), int)
        self.assertEqual(distance, 8)
        self.assertBusState(bus, {
            "name": "Кузя", "energy": 0, "passengers": 0, "doors_open": False,
            "springs_charged": False, "position_m": -3, "mileage_m": 13, "max_jump_m": 8,
        })

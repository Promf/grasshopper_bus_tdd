"""Команды пилота для маршрутных сценариев."""


class Pilot:
    def __init__(self, bus):
        self.bus = bus

    def open_doors(self):
        self.bus.open_doors()

    def pick_up(self, count):
        self.open_doors()
        self.finish_boarding(count)

    def finish_boarding(self, count):
        self.bus.board(count)
        self.bus.close_doors()

    def drop_off(self, count):
        self.open_doors()
        self.bus.alight(count)
        self.bus.close_doors()

    def drive(self, distance):
        return self.bus.move(distance)

    def prepare_jump(self):
        return self.bus.charge_springs()

    def jump(self, distance):
        return self.bus.jump(distance)

    def cancel_jump(self):
        return self.bus.release_springs()

    def recharge(self, amount):
        return self.bus.recharge(amount)

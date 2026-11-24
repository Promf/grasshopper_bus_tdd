"""Снимки публичного состояния для проверок по §3.1 ТЗ."""

import unittest
from copy import deepcopy
from dataclasses import dataclass


PUBLIC_FIELDS = (
    "name", "energy", "passengers", "doors_open", "springs_charged",
    "position_m", "mileage_m", "max_jump_m",
)
_MISSING = object()


def typed_values(fields):
    return {key: (type(value), value) for key, value in fields.items()}


def snapshot(bus):
    attributes = {}
    for name in PUBLIC_FIELDS:
        value = getattr(bus, name, _MISSING)
        if value is not _MISSING:
            attributes[name] = value
    return deepcopy({"атрибут": attributes, "get_status()": bus.get_status()})


def _describe(value):
    if value is _MISSING:
        return "нет поля"
    return f"{value!r} ({type(value).__name__})"


def state_changes(before, after) -> list[str]:
    """Возвращает все расхождения, в том числе замену 100 на 100.0."""
    changes = {}
    for source, old_fields in before.items():
        new_fields = after[source]
        if not isinstance(old_fields, dict) or not isinstance(new_fields, dict):
            old_fields = {"результат": old_fields}
            new_fields = {"результат": new_fields}
        for key in dict.fromkeys([*old_fields, *new_fields]):
            old = old_fields.get(key, _MISSING)
            new = new_fields.get(key, _MISSING)
            if type(old) is type(new) and old == new:
                continue
            difference = f"{key}: {_describe(old)} → {_describe(new)}"
            changes.setdefault(difference, []).append(source)
    return [f"{line} [{', '.join(sources)}]" for line, sources in changes.items()]


def raised_by(command, *args) -> Exception | None:
    try:
        command(*args)
    except Exception as error:
        return error
    return None


@dataclass
class CommandAttempt:
    name: str
    error: Exception | None
    before: dict
    after: dict


def attempt(bus, command, *args) -> CommandAttempt:
    """Выполняет команду один раз и сохраняет наблюдения для Assert."""
    before = snapshot(bus)
    error = raised_by(command, *args)
    return CommandAttempt(command.__name__, error, before, snapshot(bus))


class BusTestCase(unittest.TestCase):
    def assertBusState(self, bus, expected):
        differences = state_changes(
            {"атрибут": expected, "get_status()": expected}, snapshot(bus)
        )
        if differences:
            self.fail("\n".join(differences))

    def assertRejected(self, expected_error: type[Exception], result: CommandAttempt) -> None:
        violations = []
        if result.error is None:
            violations.append(f"Ожидалось {expected_error.__name__}, команда завершилась без исключения")
        elif not isinstance(result.error, expected_error):
            violations.append(f"Ожидалось {expected_error.__name__}, получено {result.error!r}")
        violations.extend(state_changes(result.before, result.after))
        if violations:
            self.fail(f"{result.name} — проверка отказа\n" + "\n".join(violations))

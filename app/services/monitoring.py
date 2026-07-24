"""Printer polling orchestration and persistence."""

from app.database import (
    get_printer,
    get_settings,
    list_printers,
    record_monitoring_result,
)
from app.services.snmp_client import SnmpClient, SnmpError


async def check_printer(printer_id: int) -> bool:
    printer = get_printer(printer_id)
    if printer is None:
        return False

    try:
        result = await SnmpClient().check(printer["host"], printer["community"])
    except (SnmpError, OSError, TimeoutError) as exc:
        record_monitoring_result(
            printer_id,
            status="offline",
            supplies=None,
            message=f"SNMP-проверка не выполнена: {exc}",
        )
        return False
    except Exception as exc:
        record_monitoring_result(
            printer_id,
            status="error",
            supplies=None,
            message=f"Ошибка SNMP-проверки: {exc}",
        )
        return False

    supplies = [
        {"name": supply.name, "level_percent": supply.level_percent}
        for supply in result.supplies
    ]
    try:
        warning_threshold = int(
            get_settings().get("warning_threshold_percent", "20")
        )
    except ValueError:
        warning_threshold = 20
    low_supplies = [
        supply
        for supply in supplies
        if supply["level_percent"] is not None
        and int(supply["level_percent"]) <= warning_threshold
    ]
    status = "warning" if low_supplies else "ok"
    message = (
        "Низкий уровень расходных материалов: "
        + ", ".join(
            f"{supply['name']} ({supply['level_percent']}%)"
            for supply in low_supplies
        )
        if low_supplies
        else f"SNMP-проверка успешна: {result.description}"
    )
    record_monitoring_result(
        printer_id,
        status=status,
        supplies=supplies,
        message=message,
    )
    return True


async def check_all_printers() -> None:
    for printer in list_printers():
        if printer["enabled"]:
            await check_printer(printer["id"])

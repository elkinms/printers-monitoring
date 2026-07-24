"""Asynchronous SNMP v2c client for printer availability and supplies."""

from dataclasses import dataclass, field

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
    walk_cmd,
)

SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SUPPLY_DESCRIPTION = "1.3.6.1.2.1.43.11.1.1.6"
SUPPLY_MAX_CAPACITY = "1.3.6.1.2.1.43.11.1.1.8"
SUPPLY_LEVEL = "1.3.6.1.2.1.43.11.1.1.9"


@dataclass(slots=True, frozen=True)
class SupplyReading:
    name: str
    level_percent: int | None


@dataclass(slots=True, frozen=True)
class SnmpResult:
    description: str
    supplies: list[SupplyReading] = field(default_factory=list)


class SnmpError(RuntimeError):
    """Raised when a printer cannot be queried over SNMP."""


class SnmpClient:
    def __init__(self, timeout: float = 2, retries: int = 1) -> None:
        self.timeout = timeout
        self.retries = retries

    async def check(self, host: str, community: str) -> SnmpResult:
        engine = SnmpEngine()
        auth = CommunityData(community, mpModel=1)
        target = await UdpTransportTarget.create(
            (host, 161), timeout=self.timeout, retries=self.retries
        )
        try:
            description = await self._get_description(engine, auth, target)
            supplies = await self._get_supplies(engine, auth, target)
            return SnmpResult(description=description, supplies=supplies)
        finally:
            engine.close_dispatcher()

    async def _get_description(
        self, engine: SnmpEngine, auth: CommunityData, target: UdpTransportTarget
    ) -> str:
        error, status, index, bindings = await get_cmd(
            engine,
            auth,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(SYS_DESCR)),
        )
        self._raise_on_error(error, status, index, bindings)
        return bindings[0][1].prettyPrint()

    async def _walk(
        self,
        engine: SnmpEngine,
        auth: CommunityData,
        target: UdpTransportTarget,
        oid: str,
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        async for error, status, index, bindings in walk_cmd(
            engine,
            auth,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographic_mode=False,
        ):
            self._raise_on_error(error, status, index, bindings)
            for name, value in bindings:
                full_oid = name.prettyPrint()
                suffix = full_oid.removeprefix(f"{oid}.")
                values[suffix] = value.prettyPrint()
        return values

    async def _get_supplies(
        self, engine: SnmpEngine, auth: CommunityData, target: UdpTransportTarget
    ) -> list[SupplyReading]:
        try:
            descriptions = await self._walk(
                engine, auth, target, SUPPLY_DESCRIPTION
            )
            capacities = await self._walk(
                engine, auth, target, SUPPLY_MAX_CAPACITY
            )
            levels = await self._walk(engine, auth, target, SUPPLY_LEVEL)
        except SnmpError:
            # Availability is useful even on devices without Printer-MIB supplies.
            return []

        readings: list[SupplyReading] = []
        for suffix, name in descriptions.items():
            level_percent: int | None = None
            try:
                maximum = int(capacities.get(suffix, ""))
                current = int(levels.get(suffix, ""))
                if maximum > 0 and current >= 0:
                    level_percent = max(0, min(100, round(current * 100 / maximum)))
            except ValueError:
                pass
            readings.append(
                SupplyReading(name=name or f"Supply {suffix}", level_percent=level_percent)
            )
        return readings

    @staticmethod
    def _raise_on_error(error, status, index, bindings) -> None:
        if error:
            raise SnmpError(str(error))
        if status:
            position = int(index or 0)
            failed_oid = (
                bindings[position - 1][0].prettyPrint()
                if position and position <= len(bindings)
                else "unknown OID"
            )
            raise SnmpError(f"{status.prettyPrint()} at {failed_oid}")

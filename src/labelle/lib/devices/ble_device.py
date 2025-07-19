from __future__ import annotations

# TODO: Check sources for protocol
# https://github.com/monti-tls/Dymo-LT-Application/blob/main/dymo_lt_ble_interface.cpp
# https://github.com/brz/letra200bsharp/blob/main/letra200bsharp/LetraHelper.cs
# https://github.com/alexhorn/lt200b
import asyncio
import logging
import platform
from sys import version_info
from typing import Final, NoReturn

if version_info.micro < 12:
    from itertools import islice

    # From python docs, backport
    def batched(iterable, n, *, strict=False):
        # batched('ABCDEFG', 3) → ABC DEF G
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            if strict and len(batch) != n:
                raise ValueError("batched(): incomplete batch")
            yield batch
else:
    from itertools import batched  # type: ignore

# TODO: Check if Qt6.bluetooth would be a better option
# https://doc.qt.io/qtforpython-6/PySide6/QtBluetooth/index.html
# says, that BLE scanning is not supported
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from labelle.lib.constants import (
    SUPPORTED_BLE_MODELS,
    SUPPORTED_BLE_PRODUCTS,
)
from labelle.lib.devices.device import Device

LOG = logging.getLogger(__name__)
GITHUB_ISSUE_MAC = "<https://github.com/labelle-org/labelle/issues/5>"
GITHUB_ISSUE_UDEV = "<https://github.com/labelle-org/labelle/issues/6>"


class BleDeviceError(RuntimeError):
    pass


class BleDevice(Device):
    END_BYTES: Final[list[int]] = [0x12, 0x34]
    START_BYTES: Final[list[int]] = [0xFF, 0xF0, *END_BYTES]

    _dev: BLEDevice
    _manufacturer: str
    _serial_number: str
    _model: str = ""
    _device_name: str = ""
    _loop: asyncio.AbstractEventLoop
    _client: BleakClient
    _devices: list[BLEDevice] | None = None

    def __init__(self, dev: BLEDevice) -> None:
        self._dev = dev
        self._loop = asyncio.new_event_loop()

    @property
    def hash(self) -> str:
        return self.connection_id

    @property
    def manufacturer(self) -> str | None:
        return self._manufacturer

    @property
    def product(self) -> str | None:
        return f"{self._device_name} {self._model}"

    @property
    def serial_number(self) -> str | None:
        return self._serial_number

    @property
    def ble_id(self) -> str:
        return self._dev.address

    @property
    def connection_id(self) -> str:
        return self.ble_id

    @staticmethod
    def _is_supported_vendor(dev: BLEDevice) -> bool:
        return dev.name is not None and dev.name.split()[0] in SUPPORTED_BLE_PRODUCTS

    @property
    def is_supported(self) -> bool:
        return (
            self._is_supported_vendor(self._dev) and self._model in SUPPORTED_BLE_MODELS
        )

    @classmethod
    async def _scan(cls):
        cls._devices = await BleakScanner.discover(2.0)
        possible_devices: list[BLEDevice] = list(
            filter(cls._is_supported_vendor, cls._devices)  # type: ignore
        )
        for device in possible_devices:
            print(f"{device.name}")

    @classmethod
    def supported_devices(cls) -> set[Device]:
        devices = cls._devices
        if not devices:
            return set()
        return {
            BleDevice(dev) for dev in filter(BleDevice._is_supported_vendor, devices)
        }

    @property
    def device_info(self) -> str:
        try:
            _ = self.manufacturer
        except ValueError:
            self._instruct_on_access_denied()
        res = ""
        res += f"{self._dev!r}\n"
        res += f"  manufacturer: {self.manufacturer}\n"
        res += f"  product: {self.product}\n"
        res += f"  serial: {self.serial_number}\n"
        return res

    # TODO: rewrite
    def _instruct_on_access_denied(self) -> NoReturn:
        system = platform.system()
        if system == "Linux":
            self._instruct_on_access_denied_linux()
        elif system == "Windows":
            raise BleDeviceError(
                "Couldn't access the device. Please make sure that the "
                "device driver is set to WinUSB. This can be accomplished "
                "with Zadig <https://zadig.akeo.ie/>."
            )
        elif system == "Darwin":
            raise BleDeviceError(
                f"Could not access {self._dev}. Thanks for bravely trying this on a "
                f"Mac. You are in uncharted territory. It would be appreciated if you "
                f"share the results of your experimentation at {GITHUB_ISSUE_MAC}."
            )
        else:
            raise BleDeviceError(f"Unknown platform {system}")

    # TODO: rewrite
    def _instruct_on_access_denied_linux(self) -> NoReturn:
        raise BleDeviceError("TODO")

    def setup(self) -> None:
        try:
            self._loop.run_until_complete(self._setup())
        except Exception as e:
            raise BleDeviceError(f"Failed setup BLE device: {e}") from e

    async def _setup(self):
        self._client = BleakClient(self._dev)
        await self._client.connect()
        if self._client._backend.__class__.__name__ == "BleakClientBlueZDBus":  # type: ignore
            await self._client._backend._acquire_mtu()  # type: ignore
        data = await self._client.read_gatt_char("00002a29-0000-1000-8000-00805f9b34fb")
        self._manufacturer = "".join(map(chr, data))
        data = await self._client.read_gatt_char("00002a24-0000-1000-8000-00805f9b34fb")
        self._model = "".join(map(chr, data))
        data = await self._client.read_gatt_char("00002a25-0000-1000-8000-00805f9b34fb")
        self._serial_number = "".join(map(chr, data))
        data = await self._client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
        self._device_name = "".join(map(chr, data))

    def dispose(self) -> None:
        self._loop.run_until_complete(self._client.disconnect())

    def is_match(self, patterns: list[str] | None) -> bool:
        if patterns is None:
            return True
        match = True
        for pattern in patterns:
            pattern = pattern.lower()
            match &= (
                pattern in (self.manufacturer or "").lower()
                or pattern in (self.product or "").lower()
                or pattern in (self.serial_number or "").lower()
            )
        return match

    @staticmethod
    def checksum(data):
        return sum(data) & 0xFF

    @staticmethod
    def chunkify(body, chunk_size=498):
        chunks = [list(x) for x in batched(body, chunk_size)]
        chunks[-1].extend(BleDevice.END_BYTES)
        return chunks

    @staticmethod
    def get_header(body):
        body_size = len(body).to_bytes(4, byteorder="little")
        result = [
            *BleDevice.START_BYTES,
            *body_size,
        ]
        result.append(BleDevice.checksum(result))
        return result

    def execute_command(
        self, cmd: list[int], synwait: int | None = None, response: bool = False
    ) -> list[int] | None:
        return self._loop.run_until_complete(self._execute_command(cmd, response))

    async def _execute_command(
        self, cmd: list[int], response=False
    ) -> list[int] | None:
        if not self._client.is_connected:
            print("Connection lost, reconnecting…")
            await self._client.connect()
            if self._client._backend.__class__.__name__ == "BleakClientBlueZDBus":  # type: ignore
                self._client._backend._acquire_mtu()  # type: ignore
        print("Connceted")
        head = BleDevice.get_header(cmd)
        print("sending header:")
        chunks = BleDevice.chunkify(cmd, self._client.mtu_size - 2)
        print("sending chunkks")
        await self._client.write_gatt_char(
            "be3dd651-2b3d-42f1-99c1-f0f749dd0678", bytearray(head), response=False
        )
        for chunk in chunks:
            await self._client.write_gatt_char(
                "be3dd651-2b3d-42f1-99c1-f0f749dd0678",
                bytearray(chunk),
                response=response,
            )
        if response:
            # TODO: Not sure which UUID is correct, could also be
            # be3dd653-2b3d-42f1-99c1-f0f749dd0678
            data = await self._client.read_gatt_char(
                "be3dd652-2b3d-42f1-99c1-f0f749dd0678"
            )
            return list(data)
        return None


# TODO: Make this toggelable
asyncio.run(BleDevice._scan())

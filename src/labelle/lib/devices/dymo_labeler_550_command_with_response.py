from __future__ import annotations

import logging
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, BinaryIO

from retry.api import retry_call  # type: ignore[import-untyped]
from rich.console import Console
from rich.table import Table

from labelle.lib.constants import ESC
from labelle.lib.devices.dymo_labeler_550_commands import Command

LOG = logging.getLogger(__name__)
LOCK = 0
MAGIC_NUMBER = 0xCAB6


class DymoLabeler550PrintStatus(Enum):
    IDLE = 0
    PRINTING = 1
    ERROR = 2
    CANCEL = 3
    BUSY = 4
    UNLOCK = 5


class DymoLabeler550PrintHeadStatus(Enum):
    OK = 0
    OVERHEATED = 1
    STATUS_UNKNOWN = 2


class DymoLabeler550MainBayStatus(Enum):
    BAY_STATUS_UNKNOWN = 0
    BAY_OPEN__MEDIA_PRESENCE_UNKNOWN = 1
    NO_MEDIA_PRESENT = 2
    MEDIA_NOT_INSERTED_PROPERLY = 3
    MEDIA_PRESENT__MEDIA_STATUS_UNKNOWN = 4
    MEDIA_PRESENT__EMPTY = 5
    MEDIA_PRESENT__CRITICALLY_LOW = 6
    MEDIA_PRESENT__LOW = 7
    MEDIA_PRESENT__OK = 8
    MEDIA_PRESENT__JAMMED = 9
    MEDIA_PRESENT__COUNTERFEIT_MEDIA = 10


class DymoLabeler550EpsStatus(Enum):
    UNKNOWN = 0  # Made-up value. We get 0 although it is not in the documentation
    EPS_PRESENT = 1


class DymoLabeler550PrintHeadVoltage(Enum):
    UNKNOWN = 0
    OK = 1
    LOW = 2
    CRITICALLY_LOW = 3
    TOO_LOW_FOR_PRINTING = 4


class DymoLabeler550BrandId(Enum):
    DYMO = 0


class DymoLabeler550Region(Enum):
    GLOBAL = 0xFF


class DymoLabeler550MaterialType(Enum):
    CARD = 0x00
    CLEAR = 0x01
    DURABLE = 0x02
    PAPER = 0x03
    PERMANENT = 0x04
    PLASTIC = 0x05
    REMOVABLE = 0x06
    TIME_EXP = 0x07


class DymoLabeler550LabelType(Enum):
    CONTINUOUS = 0x00
    DIE = 0x01
    CARD = 0x02


class DymoLabeler550LabelColor(Enum):
    CLEAR = 0x00
    WHITE = 0x01
    PINK = 0x02
    YELLOW = 0x03
    GREEN = 0x04
    BLUE = 0x05


class DymoLabeler550ContentColor(Enum):
    BLACK = 0x00
    RED_OR_BLACK = 0x01


class DymoLabeler550MarkerType(Enum):
    # Marker 1 front edge indicates offset to cut location and
    # offset to start of label
    M1FE_O2CL_O2SOL = 0x00
    # Marker 1 front edge indicates offset to cut location and
    # Marker 1 rear edge indicates offset to start of label
    M1FE_O2CL_M1RE_O2SOL = 0x01
    # Marker 1 front edge indicates offset to start of label and
    # Marker 1 rear edge indicates offset to cut location
    M1FE_O2SOL_M1RE_O2CL = 0x02
    # Marker 1 front edge indicates cut location and
    # Marker 2 front edge indicates offset to start of label
    M1FE_O2CL_M2FE_O2SOL = 0x03


class DymoLabeler550CounterStrategy(Enum):
    # Counting up from 0x0000 to "amount of labels" + "counter margin"
    COUNT_UP = 0x01
    # Counting up from 0xFFFF - "amount of labels" - “Counter margin" to 0xFFFF
    COUNT_DOWN = 0x02


class DymoLabeler550FirmwareVersion(Enum):
    # Application FW Version
    FWAP = 0
    # Boot Loader FW Version
    FWBL = 1


def val_or_msg(val: int, msg: str) -> str:
    return str(val) if val else msg


@dataclass
class DymoLabeler550PrintEngineStatus:
    print_status: DymoLabeler550PrintStatus
    print_job_id: int
    label_index: int
    print_head_status: DymoLabeler550PrintHeadStatus
    print_density: int
    main_bay_status: DymoLabeler550MainBayStatus
    sku_info: str
    error_id: int
    label_count: int
    eps_status: DymoLabeler550EpsStatus
    print_head_voltage: DymoLabeler550PrintHeadVoltage

    def dump(self):
        table = Table(title="Print Engine Status", show_header=False)
        table.add_row(
            "Print Status", self.print_status.name, "The actual print engine status"
        )
        table.add_row(
            "Print Job ID",
            val_or_msg(self.print_job_id, "Printer Idle"),
            "The Job ID of the ongoing print process",
        )
        table.add_row(
            "Label Index",
            str(self.label_index),
            "The index of the label/page currently being printed",
        )
        table.add_row(
            "Print Head Status",
            str(self.print_head_status.name),
            "The actual thermal print head status",
        )
        table.add_row(
            "Print Density",
            f"{self.print_density}%",
            "The actual print density setting in %",
        )
        table.add_row(
            "Main Bay Status", self.main_bay_status.name, "The status of the main bay"
        )
        table.add_row("SKU Info", self.sku_info, "The SKU of the inserted consumable")
        table.add_row(
            "Error ID",
            val_or_msg(self.error_id, "No Error Present"),
            "The ID of the present error",
        )
        table.add_row(
            "Label Count",
            str(self.label_count),
            "Remaining count of inserted consumable",
        )
        table.add_row(
            "EPS Status",
            self.eps_status.name,
            "The status of the external power supply",
        )
        table.add_row(
            "Print Head Voltage", self.print_head_voltage.name, "Print Head Voltage"
        )
        console = Console()
        console.print(table)


class NfcNotReadyYetError(Exception):
    pass


def string_from_int(val: int) -> str:
    val_str = str(hex(val))[2:]
    return "".join(chr(int(val_str[i : i + 2], 16)) for i in range(0, len(val_str), 2))


def datetime_from_string_bytes(date_str: bytes, date_format: str) -> datetime:
    return datetime.strptime(f"{int(date_str):04}", date_format)


def length_from_tenth_mm(val: int) -> str:
    return f"{val / 10:.1f}mm"


@dataclass
class DymoLabeler550SkuInformation:
    magic_number: int
    version: int
    length: int
    crc: int
    sku_number: str
    brand_id: DymoLabeler550BrandId
    region: DymoLabeler550Region
    material_type: DymoLabeler550MaterialType
    label_type: DymoLabeler550LabelType
    label_color: DymoLabeler550LabelColor
    content_color: DymoLabeler550ContentColor
    marker_type: DymoLabeler550MarkerType
    reserved_byte_27: int
    marker_pitch: int  # 1 - 2^16 = length in mm
    marker1_width: int  # 1 - 2^16 = length in mm
    marker1_to_start_of_label: int  # 1 - 2^16 = length in mm
    marker2_width: int  # 1 - 2^16 = length in mm
    marker2_offset: int  # 1 - 2^16 = length in mm
    vertical_offset: int  # 1 - 2^16 = length in mm
    label_length: int  # 1 - 2^16 = length in mm
    label_width: int  # 1 - 2^16 = length in mm
    printable_area_horizontal_offset: int  # 1 - 2^16 = length in mm
    printable_area_vertical_offset: int  # 1 - 2^16 = length in mm
    liner_width: int  # 1 - 2^16 = length in mm
    total_label_count: int
    total_length: int  # 1 - 2^16 = length in mm
    counter_margin: int
    counter_strategy: DymoLabeler550CounterStrategy
    reserved_byte_57: int
    reserved_byte_58: int
    reserved_byte_59: int
    production_date: datetime
    production_time: datetime

    def dump(self):
        table = Table(title="SKU Information", show_header=False)
        table.add_row("Version", str(self.version))
        table.add_row("Length", str(self.length))
        table.add_row("CRC", str(self.crc))
        table.add_row("SKU Number", self.sku_number, "The SKU # of inserted")
        table.add_row("Brand ID", self.brand_id.name)
        table.add_row("Region", self.region.name)
        table.add_row(
            "Material Type", self.material_type.name, "The type of label material"
        )
        table.add_row("Label Type", self.label_type.name)
        table.add_row("Label Color", self.label_color.name)
        table.add_row("Content Color", self.content_color.name)
        table.add_row("Marker Type", self.marker_type.name)
        table.add_row("Marker Pitch", length_from_tenth_mm(self.marker_pitch))
        table.add_row("Marker 1 Width", length_from_tenth_mm(self.marker1_width))
        table.add_row(
            "Marker 1 to Start of Label",
            length_from_tenth_mm(self.marker1_to_start_of_label),
        )
        table.add_row("Marker 2 Width", length_from_tenth_mm(self.marker2_width))
        table.add_row("Marker 2 Offset", length_from_tenth_mm(self.marker2_offset))
        table.add_row("Vertical Offset", length_from_tenth_mm(self.vertical_offset))
        table.add_row("Label Length", length_from_tenth_mm(self.label_length))
        table.add_row("Label Width", length_from_tenth_mm(self.label_width))
        table.add_row(
            "Printable Area Horizontal Offset",
            length_from_tenth_mm(self.printable_area_horizontal_offset),
        )
        table.add_row(
            "Printable Area Vertical Offset",
            length_from_tenth_mm(self.printable_area_vertical_offset),
        )
        table.add_row("Liner Width", length_from_tenth_mm(self.liner_width))
        table.add_row("Total Label Count", str(self.total_label_count))
        table.add_row(
            "Total Length", length_from_tenth_mm(self.total_length), "Length of roll"
        )
        table.add_row(
            "Counter Margin",
            str(self.counter_margin),
            "Used to determine remaining labels on roll or limit usage",
        )
        table.add_row("Counter Strategy", self.counter_strategy.name)
        table.add_row("Production Date", self.production_date.strftime("%x"))
        table.add_row("Production Time", self.production_time.strftime("%X"))
        console = Console()
        console.print(table)


@dataclass
class DymoLabeler550PrintEngineVersion:
    hw_version: str
    fw_version: DymoLabeler550FirmwareVersion
    major_release_version: str
    minor_release_version: str
    release_date: datetime  # MMYY format
    product_id: str  # Two bytes of USB PID

    def dump(self):
        table = Table(title="Print Engine Version", show_header=False)
        table.add_row("HW Version", self.hw_version, "The hardware version")
        table.add_row("FW Version", self.fw_version.name, "The firmware version")
        table.add_row("Major Release Version", self.major_release_version)
        table.add_row("Minor Release Version", self.minor_release_version)
        table.add_row("Release Date", self.release_date.strftime("%m-%Y"))
        table.add_row("Product ID", self.product_id, "Two bytes of USB PID")
        console = Console()
        console.print(table)


class CommandWithResponse(ABC):
    expected_response_length: int
    retry_exceptions: tuple[type[Exception]] | None = None

    @classmethod
    def execute(cls, devin: BinaryIO, devout: BinaryIO) -> Any:
        return retry_call(
            cls._execute,
            fkwargs={"devin": devin, "devout": devout},
            exceptions=cls.retry_exceptions,
            tries=10,
            delay=0.5,
        )

    @classmethod
    def _execute(cls, devin: BinaryIO, devout: BinaryIO) -> Any:
        command = cls._request()
        devout.write(command.payload)
        response_payload = devin.read(cls.expected_response_length)
        response_payload = bytes(response_payload)  # convert from array.array to bytes
        assert len(response_payload) == cls.expected_response_length
        payload_str = " ".join([f"{x:02x}" for x in response_payload])
        LOG.debug(f"Read {len(response_payload)} bytes: {payload_str}")
        response = cls._response(response_payload)
        LOG.debug(f"Response: {response}")
        return response

    @staticmethod
    @abstractmethod
    def _request() -> Command:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _response(response: bytes) -> Any:
        raise NotImplementedError


class CommandPrintEngineStatus(CommandWithResponse):
    expected_response_length = 32

    @staticmethod
    def _request() -> Command:
        """ESC A Request Print Engine Status
        1B 41
        """  # noqa: D205, D400
        return Command(
            "Request Print Engine Status",
            struct.pack("<BBB", ESC, ord("A"), LOCK),
        )

    @staticmethod
    def _response(response: bytes) -> DymoLabeler550PrintEngineStatus:
        """ESC A Request Print Engine Status
        1B 41
        """  # noqa: D205, D400
        (
            print_status,
            print_job_id,
            label_index,
            reserved_byte_7,
            print_head_status,
            print_density,
            main_bay_status,
            sku_info,
            error_id,
            label_count,
            eps_status,
            print_head_voltage,
            reserved_byte_31,
        ) = struct.unpack("<BIHBBBB12sIHBBB", response)
        assert reserved_byte_7 == 0
        assert reserved_byte_31 == 0
        return DymoLabeler550PrintEngineStatus(
            print_status=DymoLabeler550PrintStatus(print_status),
            print_job_id=print_job_id,
            label_index=label_index,
            print_head_status=DymoLabeler550PrintHeadStatus(print_head_status),
            print_density=print_density,
            main_bay_status=DymoLabeler550MainBayStatus(main_bay_status),
            sku_info=sku_info.split(b"\x00")[0].decode(),
            error_id=error_id,
            label_count=label_count,
            eps_status=DymoLabeler550EpsStatus(eps_status),
            print_head_voltage=DymoLabeler550PrintHeadVoltage(print_head_voltage),
        )


class CommandGetSkuInformation(CommandWithResponse):
    expected_response_length = 64
    retry_exceptions = (NfcNotReadyYetError,)

    @staticmethod
    def _request() -> Command:
        """ESC U Get SKU Information
        1B 55
        Used to retrieve the inserted LW550 Consumable SKU information from NFC.
        """  # noqa: D205
        return Command(
            "Get SKU Information",
            struct.pack("<BB", ESC, ord("U")),
        )

    @staticmethod
    def _response(response: bytes) -> DymoLabeler550SkuInformation:
        """ESC U Get SKU Information
        1B 55
        Used to retrieve the inserted LW550 Consumable SKU information from NFC.
        """  # noqa: D205
        (
            magic_number,
            version,
            length,
            crc,
            sku_number,
            brand_id,
            region,
            material_type,
            label_type,
            label_color,
            content_color,
            marker_type,
            reserved_byte_27,
            marker_pitch,
            marker1_width,
            marker1_to_start_of_label,
            marker2_width,
            marker2_offset,
            vertical_offset,
            label_length,
            label_width,
            printable_area_horizontal_offset,
            printable_area_vertical_offset,
            liner_width,
            total_label_count,
            total_length,
            counter_margin,
            counter_strategy,
            reserved_byte_57,
            reserved_byte_58,
            reserved_byte_59,
            production_date,
            production_time,
        ) = struct.unpack("<HBBI12sBBBBBBBBHHHHHHHHHHHHHHBBBBHH", response)
        if magic_number == 0:
            # If printer is in sleep mode, first ESC U query could be all 0 since it
            # takes about 3s for NFC to work properly
            raise NfcNotReadyYetError("NFC not ready yet")

        assert magic_number == MAGIC_NUMBER
        assert version == 0
        try:
            material_type_enum = DymoLabeler550MaterialType(material_type)
        except ValueError as e:
            LOG.warning(f"Material_type 0x{material_type:02x} not recognized: {e}")
            material_type_enum = DymoLabeler550MaterialType.CARD  # arbitrary default
        return DymoLabeler550SkuInformation(
            magic_number=magic_number,
            version=version,
            length=length,
            crc=crc,
            sku_number=sku_number.decode(),
            brand_id=DymoLabeler550BrandId(brand_id),
            region=DymoLabeler550Region(region),
            material_type=material_type_enum,
            label_type=DymoLabeler550LabelType(label_type),
            label_color=DymoLabeler550LabelColor(label_color),
            content_color=DymoLabeler550ContentColor(content_color),
            marker_type=DymoLabeler550MarkerType(marker_type),
            reserved_byte_27=reserved_byte_27,
            marker_pitch=marker_pitch,
            marker1_width=marker1_width,
            marker1_to_start_of_label=marker1_to_start_of_label,
            marker2_width=marker2_width,
            marker2_offset=marker2_offset,
            vertical_offset=vertical_offset,
            label_length=label_length,
            label_width=label_width,
            printable_area_horizontal_offset=printable_area_horizontal_offset,
            printable_area_vertical_offset=printable_area_vertical_offset,
            liner_width=liner_width,
            total_label_count=total_label_count,
            total_length=total_length,
            counter_margin=counter_margin,
            counter_strategy=DymoLabeler550CounterStrategy(counter_strategy),
            reserved_byte_57=reserved_byte_57,
            reserved_byte_58=reserved_byte_58,
            reserved_byte_59=reserved_byte_59,
            production_date=datetime_from_string_bytes(production_date, "%j%y"),
            production_time=datetime_from_string_bytes(production_time, "%H%M"),
        )


class CommandPrintEngineVersion(CommandWithResponse):
    expected_response_length = 34

    @staticmethod
    def _request() -> Command:
        """ESC V Request Print Engine Version
        1B 56
        Used to retrieve version information of the print engine.
        """  # noqa: D205
        return Command(
            "Request Print Engine Version",
            struct.pack("<BB", ESC, ord("V")),
        )

    @staticmethod
    def _response(response: bytes) -> DymoLabeler550PrintEngineVersion:
        (
            hw_version,
            fw_version,
            major_release_version,
            minor_release_version,
            release_date,
            product_id,
        ) = struct.unpack("<16s4sII4sH", response)
        return DymoLabeler550PrintEngineVersion(
            hw_version=hw_version.decode("utf-8"),
            fw_version=DymoLabeler550FirmwareVersion[fw_version.decode()],
            major_release_version=string_from_int(major_release_version),
            minor_release_version=string_from_int(minor_release_version),
            release_date=datetime_from_string_bytes(release_date, "%m%y"),
            product_id=string_from_int(product_id),
        )

from __future__ import annotations

import logging
import platform
from typing import NoReturn

import usb

from labelle.lib.constants import (
    DEV_VENDOR,
    HID_INTERFACE_CLASS,
    PRINTER_INTERFACE_CLASS,
    SUPPORTED_PRODUCTS,
)

LOG = logging.getLogger(__name__)
GITHUB_ISSUE_MAC = "<https://github.com/labelle-org/labelle/issues/5>"
GITHUB_ISSUE_UDEV = "<https://github.com/labelle-org/labelle/issues/6>"


class UsbDeviceError(RuntimeError):
    pass


class UsbDevice:
    _dev: usb.core.Device
    _intf: usb.core.Interface | None
    _devin: usb.core.Endpoint | None
    _devout: usb.core.Endpoint | None

    def __init__(self, dev: usb.core.Device) -> None:
        self._dev = dev
        self._intf = None
        self._devin = None
        self._devout = None

    @property
    def hash(self):
        try:
            return (
                f"<{self._dev.manufacturer}|{self._dev.product}"
                f"|{self._dev.serial_number}>"
            )
        except (ValueError, usb.core.USBError):
            return None

    def _get_dev_attribute(self, attr):
        try:
            return getattr(self._dev, attr)
        except (ValueError, usb.core.USBError):
            return None

    @property
    def manufacturer(self):
        return self._get_dev_attribute("manufacturer")

    @property
    def product(self):
        return self._get_dev_attribute("product")

    @property
    def serial_number(self):
        return self._get_dev_attribute("serial_number")

    @property
    def id_vendor(self):
        return self._get_dev_attribute("idVendor")

    @property
    def id_product(self):
        return self._get_dev_attribute("idProduct")

    @property
    def vendor_product_id(self):
        vendor_id = int(self.id_vendor)
        product_id = int(self.id_product)
        return f"{vendor_id:04x}:{product_id:04x}"

    @property
    def usb_id(self):
        bus = self._get_dev_attribute("bus")
        address = self._get_dev_attribute("address")
        return f"Bus {bus:03} Device {address:03}: ID {self.vendor_product_id}"

    @staticmethod
    def _is_supported_vendor(dev: usb.core.Device):
        return dev.idVendor == DEV_VENDOR

    @property
    def is_supported(self):
        return (
            self._is_supported_vendor(self._dev)
            and self.id_product in SUPPORTED_PRODUCTS
        )

    @staticmethod
    def supported_devices() -> set[UsbDevice]:
        return {
            UsbDevice(dev)
            for dev in usb.core.find(
                find_all=True, custom_match=UsbDevice._is_supported_vendor
            )
        }

    @property
    def device_info(self) -> str:
        try:
            _ = self._dev.manufacturer
        except ValueError:
            self._instruct_on_access_denied()
        res = ""
        res += f"{self._dev!r}\n"
        res += f"  manufacturer: {self._dev.manufacturer}\n"
        res += f"  product: {self._dev.product}\n"
        res += f"  serial: {self._dev.serial_number}\n"
        configs = self._dev.configurations()
        if configs:
            res += "  configurations:\n"
            for cfg in configs:
                res += f"  - {cfg!r}\n"
                intfs = cfg.interfaces()
                if intfs:
                    res += "    interfaces:\n"
                    for intf in intfs:
                        res += f"    - {intf!r}\n"
        return res

    def _instruct_on_access_denied(self) -> NoReturn:
        system = platform.system()
        if system == "Linux":
            self._instruct_on_access_denied_linux()
        elif system == "Windows":
            raise UsbDeviceError(
                "Couldn't access the device. Please make sure that the "
                "device driver is set to WinUSB. This can be accomplished "
                "with Zadig <https://zadig.akeo.ie/>."
            )
        elif system == "Darwin":
            raise UsbDeviceError(
                f"Could not access {self._dev}. Thanks for bravely trying this on a "
                f"Mac. You are in uncharted territory. It would be appreciated if you "
                f"share the results of your experimentation at {GITHUB_ISSUE_MAC}."
            )
        else:
            raise UsbDeviceError(f"Unknown platform {system}")

    def _instruct_on_access_denied_linux(self) -> NoReturn:
        # try:
        #     os_release = platform.freedesktop_os_release()
        # except OSError:
        #     os_release = {}
        # dists_with_empties = [os_release.get("ID", "")] + os_release.get(
        #     "ID_LIKE", ""
        # ).split(" ")
        # dists = [dist for dist in dists_with_empties if dist]
        # if "arch" in dists:
        #     restart_udev_command = "sudo udevadm control --reload"
        # elif "ubuntu" in dists or "debian" in dists:
        #     restart_udev_command = "sudo systemctl restart udev.service"
        # # detect whether we are in arch linux or ubuntu linux
        # if Path("/etc/arch-release").exists():
        #     restart_udev_command = "sudo udevadm control --reload"
        # elif Path("/etc/lsb-release").exists():
        #     restart_udev_command = "sudo systemctl restart udev.service"
        # else:
        #     restart_udev_command = None

        udev_rule = ", ".join(
            [
                'ACTION=="add"',
                'SUBSYSTEMS=="usb"',
                f'ATTRS{{idVendor}}=="{self._dev.idVendor:04x}"',
                f'ATTRS{{idProduct}}=="{self._dev.idProduct:04x}"',
                'MODE="0666"',
            ]
        )

        msg = f"""
            You do not have sufficient access to the device. You probably want to add the a udev
            rule in /etc/udev/rules.d with the following command:

            echo '{udev_rule}' | sudo tee /etc/udev/rules.d/91-labelle-{self._dev.idProduct:x}.rules

            Next, refresh udev with:

            sudo udevadm control --reload-rules
            sudo udevadm trigger --attr-match=idVendor="0922"

            Finally, turn your device off and back on again to activate the new permissions.

            If this still does not resolve the problem, you might need to reboot.
            In case rebooting is necessary, please report this at {GITHUB_ISSUE_UDEV}.
            We are still trying to figure out a simple procedure which works for everyone.
            In case you still cannot connect, or if you have any information or ideas, please
            post them at that link.
        """  # noqa: E501
        LOG.error(msg)
        raise UsbDeviceError("Insufficient access to the device")

    def _set_configuration(self):
        try:
            self._dev.get_active_configuration()
            LOG.debug("Active device configuration already found.")
        except usb.core.USBError:
            try:
                self._dev.set_configuration()
                LOG.debug("Device configuration set.")
            except usb.core.USBError as e:
                if e.errno == 13:
                    raise UsbDeviceError("Access denied") from e
                if e.errno == 16:
                    LOG.debug("Device is busy, but this is okay.")
                else:
                    raise

    def setup(self):
        try:
            self._setup()
        except usb.core.USBError as e:
            raise UsbDeviceError(f"Failed setup USB device: {e}") from e

    def _setup(self):
        self._set_configuration()
        intf = usb.util.find_descriptor(
            self._dev.get_active_configuration(),
            bInterfaceClass=PRINTER_INTERFACE_CLASS,
        )
        if intf is not None:
            LOG.debug(f"Opened printer interface: {intf!r}")
        else:
            intf = usb.util.find_descriptor(
                self._dev.get_active_configuration(),
                bInterfaceClass=HID_INTERFACE_CLASS,
            )
            if intf is not None:
                LOG.debug(f"Opened HID interface: {intf!r}")
            else:
                raise UsbDeviceError("Could not open a valid interface")
        assert isinstance(intf, usb.core.Interface)

        try:
            if self._dev.is_kernel_driver_active(intf.bInterfaceNumber):
                LOG.debug(
                    f"Detaching kernel driver from interface {intf.bInterfaceNumber}"
                )
                self._dev.detach_kernel_driver(intf.bInterfaceNumber)
        except NotImplementedError:
            LOG.debug(
                f"Kernel driver detaching not necessary on " f"{platform.system()}."
            )
        devout = usb.util.find_descriptor(
            intf,
            custom_match=(
                lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_OUT
            ),
        )
        devin = usb.util.find_descriptor(
            intf,
            custom_match=(
                lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_IN
            ),
        )

        if not devout or not devin:
            self._intf = None
            self._devin = None
            self._devout = None
            raise UsbDeviceError("The device endpoints not be found")
        self._intf = intf
        self._devin = devin
        self._devout = devout

    def dispose(self):
        usb.util.dispose_resources(self._dev)

    def is_match(self, patterns: list[str] | None) -> bool:
        if patterns is None:
            return True
        match = True
        for pattern in patterns:
            pattern = pattern.lower()
            match &= (
                pattern in self.manufacturer.lower()
                or pattern in self.product.lower()
                or pattern in self.serial_number.lower()
            )
        return match

    @property
    def devin(self):
        return self._devin

    @property
    def devout(self):
        return self._devout

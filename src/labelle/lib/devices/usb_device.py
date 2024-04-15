from __future__ import annotations

import logging
import platform
from typing import NamedTuple, NoReturn

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
    dev: usb.core.Device

    def __init__(self, dev: usb.core.Device) -> None:
        self.dev = dev

    @property
    def hash(self):
        try:
            return (
                f"<{self.dev.manufacturer}|{self.dev.product}|{self.dev.serial_number}>"
            )
        except (ValueError, usb.core.USBError):
            return None

    def _get_dev_attribute(self, attr):
        try:
            return getattr(self.dev, attr)
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
    def id_product(self):
        return self._get_dev_attribute("idProduct")

    @staticmethod
    def is_supported_vendor(dev: usb.core.Device):
        return dev.idVendor == DEV_VENDOR

    @property
    def is_supported(self):
        return (
            self.is_supported_vendor(self.dev) and self.id_product in SUPPORTED_PRODUCTS
        )

    @staticmethod
    def supported_devices() -> set[UsbDevice]:
        return {
            UsbDevice(dev)
            for dev in usb.core.find(
                find_all=True, custom_match=UsbDevice.is_supported_vendor
            )
        }

    @property
    def device_info(self) -> str:
        try:
            _ = self.dev.manufacturer
        except ValueError:
            self._instruct_on_access_denied()
        res = ""
        res += f"{self.dev!r}\n"
        res += f"  manufacturer: {self.dev.manufacturer}\n"
        res += f"  product: {self.dev.product}\n"
        res += f"  serial: {self.dev.serial_number}\n"
        configs = self.dev.configurations()
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
                f"Could not access {self.dev}. Thanks for bravely trying this on a Mac."
                f" You are in uncharted territory. It would be appreciated if you share"
                f" the results of your experimentation at {GITHUB_ISSUE_MAC}."
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
                f'ATTRS{{idVendor}}=="{self.dev.idVendor:04x}"',
                f'ATTRS{{idProduct}}=="{self.dev.idProduct:04x}"',
                'MODE="0666"',
            ]
        )

        msg = f"""
            You do not have sufficient access to the device. You probably want to add the a udev
            rule in /etc/udev/rules.d with the following command:

            echo '{udev_rule}' | sudo tee /etc/udev/rules.d/91-labelle-{self.dev.idProduct:x}.rules

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


class DetectedDevice(NamedTuple):
    id: int
    """See dymoprint.constants.SUPPORTED_PRODUCTS for a list of known IDs."""
    dev: usb.core.Device
    intf: usb.core.Interface
    devout: usb.core.Endpoint
    devin: usb.core.Endpoint


def _configure_device(dev):
    try:
        dev.get_active_configuration()
        LOG.debug("Active device configuration already found.")
    except usb.core.USBError:
        try:
            dev.set_configuration()
            LOG.debug("Device configuration set.")
        except usb.core.USBError as e:
            if e.errno == 13:
                raise UsbDeviceError("Access denied") from e
            if e.errno == 16:
                LOG.debug("Device is busy, but this is okay.")
            else:
                raise


def _find_device_descriptors(
    dev,
) -> tuple[usb.core.Interface, usb.core.Endpoint, usb.core.Endpoint]:
    intf = usb.util.find_descriptor(
        dev.get_active_configuration(), bInterfaceClass=PRINTER_INTERFACE_CLASS
    )
    if intf is not None:
        LOG.debug(f"Opened printer interface: {intf!r}")
    else:
        intf = usb.util.find_descriptor(
            dev.get_active_configuration(), bInterfaceClass=HID_INTERFACE_CLASS
        )
        if intf is not None:
            LOG.debug(f"Opened HID interface: {intf!r}")
        else:
            raise UsbDeviceError("Could not open a valid interface")
    assert isinstance(intf, usb.core.Interface)

    try:
        if dev.is_kernel_driver_active(intf.bInterfaceNumber):
            LOG.debug(f"Detaching kernel driver from interface {intf.bInterfaceNumber}")
            dev.detach_kernel_driver(intf.bInterfaceNumber)
    except NotImplementedError:
        LOG.debug(f"Kernel driver detaching not necessary on " f"{platform.system()}.")
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
        raise UsbDeviceError("The device endpoints not be found")

    return intf, devout, devin


def setup_device(usb_device: UsbDevice) -> DetectedDevice:
    _configure_device(usb_device.dev)
    intf, devout, devin = _find_device_descriptors(usb_device.dev)
    return DetectedDevice(
        id=usb_device.dev.idProduct,
        dev=usb_device.dev,
        intf=intf,
        devout=devout,
        devin=devin,
    )

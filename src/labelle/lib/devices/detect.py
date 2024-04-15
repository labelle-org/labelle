import logging
import platform
from typing import NamedTuple

import usb

from labelle.lib.constants import (
    HID_INTERFACE_CLASS,
    PRINTER_INTERFACE_CLASS,
)
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)


class DymoUSBError(RuntimeError):
    pass


class DetectedDevice(NamedTuple):
    id: int
    """See labelle.constants.SUPPORTED_PRODUCTS for a list of known IDs."""
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
                raise DymoUSBError("Access denied") from e
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
            raise DymoUSBError("Could not open a valid interface")
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
        raise DymoUSBError("The device endpoints not be found")

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

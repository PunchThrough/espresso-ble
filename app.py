#!/usr/bin/env python3

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from ble import (
    Advertisement,
    Characteristic,
    Service,
    Application,
    find_adapter,
    Descriptor,
    Agent,
)


import requests
import array

MainLoop = None
try:
    from gi.repository import GLib

    MainLoop = GLib.MainLoop
except ImportError:
    import gobject as GObject

    MainLoop = GObject.MainLoop
import sys

from random import randint


mainloop = None

BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.InvalidValueLength"


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.Failed"


def register_app_cb():
    print("GATT application registered")


def register_app_error_cb(error):
    print("Failed to register application: " + str(error))
    mainloop.quit()


class VivaldiS1Service(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """

    ESPRESSO_SVC_UUID = "12634d89-d598-4874-8e86-7d042ee07ba7"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.ESPRESSO_SVC_UUID, True)
        self.add_characteristic(PowerControlCharacteristic(bus, 0, self))
        self.add_characteristic(BoilerControlCharacteristic(bus, 1, self))
        self.add_characteristic(AutoOffCharacteristic(bus, 2, self))


class PowerControlCharacteristic(Characteristic):
    uuid = "4116f8d2-9f66-4f58-a53d-fc7440e7c14e"
    description = b"Get/set machine power state"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["secure-read", "secure-write"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print("power Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("power Write: " + repr(value))
        self.value = value


class BoilerControlCharacteristic(Characteristic):
    uuid = "322e774f-c909-49c4-bd7b-48a4003a967f"
    description = b"Get/set boiler power state"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["secure-read", "secure-write"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print("boiler Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("boiler Write: " + repr(value))
        self.value = value


class AutoOffCharacteristic(Characteristic):
    uuid = "9c7dbce8-de5f-4168-89dd-74f04f4e5842"
    description = b"Get/set autoff time in minutes"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["secure-read", "secure-write"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print("auto off Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("auto off Write: " + repr(value))
        self.value = value


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.
    """

    CUD_UUID = "2901"

    def __init__(
        self, bus, index, characteristic,
    ):

        self.value = array.array("B", characteristic.description)
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index, self.CUD_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class VivaldiAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_manufacturer_data(
            0xFFFF, [0x70, 0x74],
        )
        self.add_service_uuid(VivaldiS1Service.ESPRESSO_SVC_UUID)

        self.add_local_name("Vivaldi")
        self.include_tx_power = True


def register_ad_cb():
    print("Advertisement registered")


def register_ad_error_cb(error):
    print("Failed to register advertisement: " + str(error))
    mainloop.quit()


AGENT_PATH = "/com/punchthrough/agent"


def main():
    global mainloop

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # get the system bus
    bus = dbus.SystemBus()
    # get the ble controller
    adapter = find_adapter(bus)

    if not adapter:
        print("GattManager1 interface not found")
        return

    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter)

    adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")

    # powered property on the controller to on
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    # Get manager objs
    service_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

    advertisement = VivaldiAdvertisement(bus, 0)
    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")

    agent = Agent(bus, AGENT_PATH)

    app = Application(bus)
    app.add_service(VivaldiS1Service(bus, 2))

    mainloop = MainLoop()

    agent_manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")

    ad_manager.RegisterAdvertisement(
        advertisement.get_path(),
        {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb,
    )

    print("Registering GATT application...")

    service_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb,
    )

    agent_manager.RequestDefaultAgent(AGENT_PATH)

    mainloop.run()
    # ad_manager.UnregisterAdvertisement(advertisement)
    # dbus.service.Object.remove_from_connection(advertisement)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import array

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import sys

from random import randint

mainloop = None

BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESC_IFACE = "org.bluez.GattDescriptor1"

LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"


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


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """

    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

        self.add_service(VivaldiS1Service(bus, 2))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        print("GetManagedObjects")

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """

    PATH_BASE = "/org/bluez/example/service"

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(
                    self.get_characteristic_paths(), signature="o"
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.get_descriptor_paths(), signature="o"),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print("Default StartNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print("Default StopNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/desc" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                "Characteristic": self.chrc.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise NotSupportedException()


class VivaldiS1Service(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """

    TEST_SVC_UUID = "12634d89-d598-4874-8e86-7d042ee07ba7"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        self.add_characteristic(TestEncryptCharacteristic(bus, 1, self))
        self.add_characteristic(TestSecureCharacteristic(bus, 2, self))


class TestCharacteristic(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef1"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["read", "write", "writable-auxiliaries"],
            service,
        )
        self.value = []
        self.add_descriptor(TestDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print("TestCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestCharacteristic Write: " + repr(value))
        self.value = value


class TestDescriptor(Descriptor):
    """
    Dummy test descriptor. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef2"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self, bus, index, self.TEST_DESC_UUID, ["read", "write"], characteristic
        )

    def ReadValue(self, options):
        print("sddsf")
        return array.array("B", b"This is here it s1")


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.

    """

    CUD_UUID = "2901"

    def __init__(self, bus, index, characteristic):
        self.writable = "writable-auxiliaries" in characteristic.flags
        self.value = array.array("B", b"This is a characteristic for testing")
        self.value = self.value.tolist()
        Descriptor.__init__(
            self, bus, index, self.CUD_UUID, ["read", "write"], characteristic
        )

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class TestEncryptCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring encryption.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef3"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["encrypt-read", "encrypt-write"],
            service,
        )
        self.value = []
        self.add_descriptor(TestEncryptDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print("TestEncryptCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestEncryptCharacteristic Write: " + repr(value))
        self.value = value


class TestEncryptDescriptor(Descriptor):
    """
    Dummy test descriptor requiring encryption. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef4"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self,
            bus,
            index,
            self.TEST_DESC_UUID,
            ["encrypt-read", "encrypt-write"],
            characteristic,
        )

    def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


class TestSecureCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring secure connection.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef5"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["secure-read", "secure-write"],
            service,
        )
        self.value = []
        self.add_descriptor(TestSecureDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print("TestSecureCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestSecureCharacteristic Write: " + repr(value))
        self.value = value


class TestSecureDescriptor(Descriptor):
    """
    Dummy test descriptor requiring secure connection. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef6"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self,
            bus,
            index,
            self.TEST_DESC_UUID,
            ["secure-read", "secure-write"],
            characteristic,
        )

    def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


def register_app_cb():
    print("GATT application registered")


def register_app_error_cb(error):
    print("Failed to register application: " + str(error))
    mainloop.quit()


def find_adapter(bus):
    """
    Returns the first object that the bluez service has that has a GattManager1 interface
    """
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None


class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties["Type"] = self.ad_type
        if self.service_uuids is not None:
            properties["ServiceUUIDs"] = dbus.Array(self.service_uuids, signature="s")
        if self.solicit_uuids is not None:
            properties["SolicitUUIDs"] = dbus.Array(self.solicit_uuids, signature="s")
        if self.manufacturer_data is not None:
            properties["ManufacturerData"] = dbus.Dictionary(
                self.manufacturer_data, signature="qv"
            )
        if self.service_data is not None:
            properties["ServiceData"] = dbus.Dictionary(
                self.service_data, signature="sv"
            )
        if self.local_name is not None:
            properties["LocalName"] = dbus.String(self.local_name)
        if self.include_tx_power is not None:
            properties["IncludeTxPower"] = dbus.Boolean(self.include_tx_power)

        if self.data is not None:
            properties["Data"] = dbus.Dictionary(self.data, signature="yv")
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature="qv")
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature="y")

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature="sv")
        self.service_data[uuid] = dbus.Array(data, signature="y")

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature="yv")
        self.data[ad_type] = dbus.Array(data, signature="y")

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        print("GetAll")
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print("returning props")
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("%s: Released!" % self.path)


class TestAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_manufacturer_data(0xFFFF, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data("9999", [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_local_name("Vivaldi")
        self.include_tx_power = True
        self.add_data(0x26, [0x01, 0x01, 0x00])


def register_ad_cb():
    print("Advertisement registered")


def register_ad_error_cb(error):
    print("Failed to register advertisement: " + str(error))
    mainloop.quit()

AGENT_INTERFACE = "org.bluez.Agent1"
AGENT_PATH = "/test/agent"


def ask(prompt):
    try:
        return raw_input(prompt)
    except:
        return input(prompt)


def set_trusted(path):
    props = dbus.Interface(
        bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties"
    )
    props.Set("org.bluez.Device1", "Trusted", True)


def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path), "org.bluez.Device1")
    dev.Connect()


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if authorize == "yes":
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = ask("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("CCCCConfirm passkey (yes/no): ")
        if confirm == "yes":
            set_trusted(device)
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if auth == "yes":
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


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

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE
    )

    adapter_props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter), "org.freedesktop.DBus.Properties"
    )

    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE
    )

    test_advertisement = TestAdvertisement(bus, 0)
    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")
    path = "/test/agent"
    agent = Agent(bus, path)

    app = Application(bus)

    mainloop = GObject.MainLoop()

    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(path, "NoInputNoOutput")

    ad_manager.RegisterAdvertisement(
        test_advertisement.get_path(),
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

    manager.RequestDefaultAgent(path)

    mainloop.run()
    ad_manager.UnregisterAdvertisement(test_advertisement)
    dbus.service.Object.remove_from_connection(test_advertisement)


if __name__ == "__main__":
    main()

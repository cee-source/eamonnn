"""Minimal read-only INA219 driver - just enough to read bus voltage for an
early low-power warning wired inline on the 5V rail. No calibration
register is touched since current/power readings aren't needed here.
"""

_DEFAULT_ADDRESS = 0x40
_CONFIG_REG = 0x00
_BUS_VOLTAGE_REG = 0x02
# 32V range, continuous shunt+bus conversion, 12-bit resolution (power-on default).
_CONFIG_RESET_VALUE = 0x399F


class INA219:
    def __init__(self, address: int = _DEFAULT_ADDRESS, bus_number: int = 1):
        import smbus2

        self._bus = smbus2.SMBus(bus_number)
        self._address = address
        self._write_word(_CONFIG_REG, _CONFIG_RESET_VALUE)

    def _write_word(self, register: int, value: int) -> None:
        self._bus.write_i2c_block_data(
            self._address, register, [(value >> 8) & 0xFF, value & 0xFF]
        )

    def _read_word(self, register: int) -> int:
        high, low = self._bus.read_i2c_block_data(self._address, register, 2)
        return (high << 8) | low

    def read_bus_voltage(self) -> float:
        """Volts on the load side of the shunt - i.e. what the Pi actually sees."""
        raw = self._read_word(_BUS_VOLTAGE_REG)
        return (raw >> 3) * 0.004

from .pool_boiler import BoilingPot
import asyncio
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import ModbusTcpServer, StartAsyncTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock
from pymodbus import __version__ as pymodbus_version
import logging
from rich.table import Table, Row
from rich.live import Live
from rich.text import Text
from rich import box
from rich.console import Console
from rich.style import Style

from typing import Optional

_logger = logging.getLogger(__name__)


# logging.basicConfig(level=logging.DEBUG)


class Engine:
    """

    """

    server_task: Optional[asyncio.Task]

    def __init__(self, ui_table: "PotUI", time_mult=1.0, time_step=0.05, max_heater_power=20000, pump_flow_rate=0.0005):
        self.max_heater_power = max_heater_power
        self.pump_flow_rate = pump_flow_rate
        self.boiling_pot = BoilingPot()
        self.time_mult = time_mult
        self.time_step = time_step

        self.closing = False

        self.max_heater_power = 5000
        self.in_pump = 0.001  # 60 l/min
        self.out_pump = 0.001  # 60 l/min

        self._in_pump = False
        self._out_pump = False
        self._heater_reg = 0

        self._boiling_alert = False
        self._full_alert = False
        self._burnout_alert = False

        self._pot_temperature = 0.0
        self._water_level = 0.0

        self.server_task = None

        self.ui_table = ui_table

        self.time = 0

        self.modbus_identification = ModbusDeviceIdentification(
            info_name={
                "VendorName": "Boiling pots ltd.",
                "ProductCode": "PM",
                "VendorUrl": "https://github.com/FabioCorradini/mqtt_opc_ua_box_conveyor",
                "ProductName": "Boiling pot master pro",
                "ModelName": "Model0001",
                "MajorMinorRevision": pymodbus_version
            }
        )

        self.discrete_input_memory = ModbusSequentialDataBlock(1001, [False, False, False])
        # 0: boiling
        # 1: full
        # 2: burnout

        self.coils_memory = ModbusSequentialDataBlock(1, [False, False])
        # 1: in_pump
        # 2: out_pump

        self.holding_register_memory = ModbusSequentialDataBlock(4001, [0])
        # 0x00: heater power

        self.input_registers_memory = ModbusSequentialDataBlock(3001, [0, 0])
        # 0x00: water level
        # 0x01: water temperature

        slave_context = ModbusSlaveContext(
            di=self.discrete_input_memory,
            co=self.coils_memory,
            ir=self.input_registers_memory,
            hr=self.holding_register_memory
        )

        self.modbus_context = ModbusServerContext(slave_context, True)

    def server_init(self):
        self.server_task = asyncio.create_task(
            StartAsyncTcpServer(
                context=self.modbus_context,  # Data storage
                identity=self.modbus_identification,  # server identify
                address=(None, 5020)
            )
        )

    async def check_memory(self):

        if self._burnout_alert:
            self.holding_register_memory.values[0] = 0

        if self._full_alert:
            self.coils_memory.values[0] = False

        self.discrete_input_memory.values[0] = self._boiling_alert
        self.discrete_input_memory.values[1] = self._full_alert
        self.discrete_input_memory.values[2] = self._burnout_alert

        self.input_registers_memory.values[0] = int(self._water_level)
        self.input_registers_memory.values[1] = self.temp_to_register(self._pot_temperature)

        self._in_pump = self.coils_memory.values[0]
        self._out_pump = self.coils_memory.values[1]
        self._heater_reg = min(self.holding_register_memory.values[0], 100)

    def update_ui(self):
        self.ui_table.set_in_pump(self._in_pump)
        self.ui_table.set_out_pump(self._out_pump)
        self.ui_table.set_power_reg(self._heater_reg)
        self.ui_table.set_temperature(self._pot_temperature)
        self.ui_table.set_water_level(self._water_level)
        self.ui_table.set_boiling_alert(self._boiling_alert)
        self.ui_table.set_burn_alert(self._burnout_alert)
        self.ui_table.set_full_alert(self._full_alert)

    def run_physical_model(self):
        power_in = self.max_heater_power * self._heater_reg / 100 if not self._burnout_alert else 0.0
        in_flow = self.pump_flow_rate if (self._in_pump and not self._full_alert) else 0.0

        self.boiling_pot.run(
            current_time=self.time,
            power_in=power_in,
            in_flow=in_flow,
            out_flow=self.pump_flow_rate if self._out_pump else 0.0
        )

        self._pot_temperature = self.boiling_pot.T
        self._water_level = self.boiling_pot.wat_h / self.boiling_pot.h_max * 100  # %
        self._boiling_alert = self.boiling_pot.boiling
        self._full_alert = self.boiling_pot.level_alert
        self._burnout_alert = self.boiling_pot.temperature_alert

    @staticmethod
    def register_to_temp(register_value: int) -> float:
        return register_value / 10 - 20

    @staticmethod
    def temp_to_register(temp_value: float) -> int:
        return max(int((temp_value + 20) * 10), 0)

    async def run(self):
        """
        Run the env main loop. Call close to terminate the loop.
        """

        self.server_init()

        with Live(self.ui_table, console=Console()):
            while not self.closing:
                await self.check_memory()
                self.run_physical_model()
                self.update_ui()
                await asyncio.sleep(self.time_step / self.time_mult)
                self.time += self.time_step / self.time_mult

        self.server_task.cancel()
        await self.server_task


class PotUI(Table):
    def __init__(self):
        super().__init__(title="Boiling pot master pro™", box=box.HEAVY_EDGE, expand=True, show_lines=True)
        self.add_column("Parameter", justify="center")
        self.add_column("Value", justify="center")

        self._in_pump_value = Text("OFF")
        self._out_pump_value = Text("OFF")
        self._power_reg_value = Text("0%")

        self._boiling_value = Text("OFF")
        self._full_value = Text("OFF")
        self._burn_value = Text("OFF")

        self._temp_value = Text("0 °C")
        self._water_value = Text("0%")

        self._in_pump_header = Text("Inlet pump")
        self._out_pump_header = Text("Drain pump")
        self._power_reg_header = Text("Heater regulation")

        self._boiling_header = Text("Boiling alert")
        self._full_header = Text("Full alert")
        self._burn_header = Text("Burnout alert")

        self._temp_header = Text("Temperature")
        self._water_header = Text("Water level")

        self.add_row(self._in_pump_header, self._in_pump_value)
        self.add_row(self._out_pump_header, self._out_pump_value)
        self.add_row(self._power_reg_header, self._power_reg_value)

        self.add_row(self._temp_header, self._temp_value)
        self.add_row(self._water_header, self._water_value)

        self.add_row(self._boiling_header, self._boiling_value)
        self.add_row(self._full_header, self._full_value)
        self.add_row(self._burn_header, self._burn_value)

    def set_in_pump(self, pump_state: bool):
        if pump_state:
            self._in_pump_value.plain = "ON"
        else:
            self._in_pump_value.plain = "OFF"

    def set_out_pump(self, pump_state: bool):
        if pump_state:
            self._out_pump_value.plain = "ON"
        else:
            self._out_pump_value.plain = "OFF"

    def set_power_reg(self, reg: float):
        self._power_reg_value.plain = f"{int(reg):d}%"

    def set_temperature(self, value: float):
        self._temp_value.plain = f"{value:.2f}°C"

    def set_water_level(self, reg: float):
        self._water_value.plain = f"{reg:.3f}%"

    def set_boiling_alert(self, status: bool):
        if status:
            self._boiling_value.plain = "ON"
            self.rows[5].style = Style(bgcolor="red", bold=True)
        else:
            self._boiling_value.plain = "OFF"
            self.rows[5].style = ""

    def set_full_alert(self, status: bool):
        if status:
            self._full_value.plain = "ON"
            self.rows[6].style = Style(bgcolor="red", bold=True)

        else:
            self._full_value.plain = "OFF"
            self.rows[6].style = ""

    def set_burn_alert(self, status: bool):
        if status:
            self._burn_value.plain = "ON"
            self.rows[7].style = Style(bgcolor="red", bold=True)
        else:
            self._burn_value.plain = "OFF"
            self._burn_value.style = ""
            self.rows[7].style = ""


async def main():
    engine = Engine(PotUI())
    await engine.run()


if __name__ == '__main__':
    asyncio.run(main())

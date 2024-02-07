from typing import Optional
from asyncua import Server, ua, uamethod
from asyncua.common.node import Node
from .CNC_machine import CNCMachine
from .constants import OPC_UA_ENDPOINT
from pathlib import Path
import asyncio

CNCStatus_strings = ["IDLE", "WORKING", "PAUSED"]


class Engine:
    """
    Manage terminal display and Opc-ua communication
    """

    current_task: Optional[asyncio.Task]
    axes_node: Optional[Node]
    heaters_node: Optional[Node]
    general_node: Optional[Node]

    feedrate_node: Optional[Node]
    status_node: Optional[Node]
    power_node: Optional[Node]

    x_axis: Optional[Node]
    x_axis_pos: Optional[Node]
    x_axis_speed: Optional[Node]
    x_axis_acc: Optional[Node]
    x_axis_target_pos: Optional[Node]
    x_axis_target_speed: Optional[Node]
    x_axis_power: Optional[Node]
    x_axis_settings: Optional[Node]
    x_axis_max_speed: Optional[Node]
    x_axis_max_acc: Optional[Node]

    y_axis: Optional[Node]
    y_axis_pos: Optional[Node]
    y_axis_speed: Optional[Node]
    y_axis_acc: Optional[Node]
    y_axis_target_pos: Optional[Node]
    y_axis_target_speed: Optional[Node]
    y_axis_power: Optional[Node]
    y_axis_settings: Optional[Node]
    y_axis_max_speed: Optional[Node]
    y_axis_max_acc: Optional[Node]

    z_axis: Optional[Node]
    z_axis_pos: Optional[Node]
    z_axis_speed: Optional[Node]
    z_axis_acc: Optional[Node]
    z_axis_target_pos: Optional[Node]
    z_axis_target_speed: Optional[Node]
    z_axis_power: Optional[Node]
    z_axis_settings: Optional[Node]
    z_axis_max_speed: Optional[Node]
    z_axis_max_acc: Optional[Node]

    e_axis: Optional[Node]
    e_axis_pos: Optional[Node]
    e_axis_speed: Optional[Node]
    e_axis_acc: Optional[Node]
    e_axis_target_pos: Optional[Node]
    e_axis_target_speed: Optional[Node]
    e_axis_power: Optional[Node]
    e_axis_settings: Optional[Node]
    e_axis_max_speed: Optional[Node]
    e_axis_max_acc: Optional[Node]

    nozzle: Optional[Node]
    nozzle_temp: Optional[Node]
    nozzle_target_temp: Optional[Node]
    nozzle_power: Optional[Node]
    nozzle_setting: Optional[Node]
    nozzle_kp: Optional[Node]
    nozzle_ki: Optional[Node]
    nozzle_wu: Optional[Node]
    nozzle_settle_window: Optional[Node]
    nozzle_settle_time: Optional[Node]

    plate: Optional[Node]
    plate_temp: Optional[Node]
    plate_target_temp: Optional[Node]
    plate_power: Optional[Node]
    plate_setting: Optional[Node]
    plate_kp: Optional[Node]
    plate_ki: Optional[Node]
    plate_wu: Optional[Node]
    plate_settle_window: Optional[Node]
    plate_settle_time: Optional[Node]

    read_gcode_line: Optional[Node]
    read_gcode_file: Optional[Node]
    pause_gcode_file: Optional[Node]
    resume_gcode_file: Optional[Node]
    abort_gcode_file: Optional[Node]

    def __init__(self, time_mult=1.0, time_step=0.05, draw=True):
        self.cnc_machine = CNCMachine()
        self.time_mult = time_mult
        self.time_step = time_step

        self.time = .0

        self.tasks = []
        self.current_task = None
        self.closing = False

        self.server = None
        self.enable_draw = draw

        # setting and measure nodes
        self.axes_node = None
        self.heaters_node = None
        self.general_node = None

        self.feedrate_node = None
        self.status_node = None
        self.power_node = None

        self.x_axis = None
        self.x_axis_pos = None
        self.x_axis_speed = None
        self.x_axis_acc = None
        self.x_axis_target_pos = None
        self.x_axis_target_speed = None
        self.x_axis_power = None
        self.x_axis_settings = None
        self.x_axis_max_speed = None
        self.x_axis_max_acc = None

        self.y_axis = None
        self.y_axis_pos = None
        self.y_axis_speed = None
        self.y_axis_acc = None
        self.y_axis_target_pos = None
        self.y_axis_target_speed = None
        self.y_axis_power = None
        self.y_axis_settings = None
        self.y_axis_max_speed = None
        self.y_axis_max_acc = None

        self.z_axis = None
        self.z_axis_pos = None
        self.z_axis_speed = None
        self.z_axis_acc = None
        self.z_axis_target_pos = None
        self.z_axis_target_speed = None
        self.z_axis_power = None
        self.z_axis_settings = None
        self.z_axis_max_speed = None
        self.z_axis_max_acc = None

        self.e_axis = None
        self.e_axis_pos = None
        self.e_axis_speed = None
        self.e_axis_acc = None
        self.e_axis_target_pos = None
        self.e_axis_target_speed = None
        self.e_axis_power = None
        self.e_axis_settings = None
        self.e_axis_max_speed = None
        self.e_axis_max_acc = None

        self.nozzle = None
        self.nozzle_temp = None
        self.nozzle_target_temp = None
        self.nozzle_power = None
        self.nozzle_setting = None
        self.nozzle_kp = None
        self.nozzle_ki = None
        self.nozzle_wu = None
        self.nozzle_settle_window = None
        self.nozzle_settle_time = None

        self.plate = None
        self.plate_temp = None
        self.plate_target_temp = None
        self.plate_power = None
        self.plate_setting = None
        self.plate_kp = None
        self.plate_ki = None
        self.plate_wu = None
        self.plate_settle_window = None
        self.plate_settle_time = None

        # actions
        self.read_gcode_line = None
        self.read_gcode_file = None
        self.pause_gcode_file = None
        self.resume_gcode_file = None
        self.abort_gcode_file = None

    async def server_init(self):
        """
        Initialize the OPC-UA communication and creates nodes
        """
        print("Starting opcua server...", end="\t")
        self.server = Server()
        await self.server.init()
        self.server.set_endpoint(OPC_UA_ENDPOINT)
        uri = "http://test_cnc_machine"
        idx = await self.server.register_namespace(uri)
        idx = ua.NodeId(0, int(idx))

        self.axes_node = await self.server.nodes.objects.add_object(idx, "Axes")
        self.heaters_node = await self.server.nodes.objects.add_object(idx, "Heaters")
        self.general_node = await self.server.nodes.objects.add_object(idx, "General")

        self.feedrate_node = await self.general_node.add_variable(idx, "Feedrate", self.cnc_machine.feedrate_override)
        self.status_node = await self.general_node.add_variable(idx, "Status", 0)
        self.power_node = await self.general_node.add_variable(idx, "Power", .0)

        await self.feedrate_node.set_writable()

        self.x_axis = await self.axes_node.add_object(idx, "X")
        self.x_axis_pos = await self.x_axis.add_variable(idx, "Current_pos", .0)
        self.x_axis_speed = await self.x_axis.add_variable(idx, "Current_speed", .0)
        self.x_axis_acc = await self.x_axis.add_variable(idx, "Current_acc", .0)
        self.x_axis_target_pos = await self.x_axis.add_variable(idx, "Target_pos", .0)
        self.x_axis_target_speed = await self.x_axis.add_variable(idx, "Target_speed", .0)
        self.x_axis_power = await self.x_axis.add_variable(idx, "Power", .0)

        self.x_axis_settings = await self.x_axis.add_object(idx, "Settings")
        self.x_axis_max_speed = await self.x_axis_settings.add_variable(idx, "Max_speed",
                                                                        self.cnc_machine.x_axis.max_speed)
        self.x_axis_max_acc = await self.x_axis_settings.add_variable(idx, "Max_acc", self.cnc_machine.x_axis.max_acc)

        await self.x_axis_max_speed.set_writable()
        await self.x_axis_max_acc.set_writable()

        self.y_axis = await self.axes_node.add_object(idx, "Y")
        self.y_axis_pos = await self.y_axis.add_variable(idx, "Current_pos", .0)
        self.y_axis_speed = await self.y_axis.add_variable(idx, "Current_speed", .0)
        self.y_axis_acc = await self.y_axis.add_variable(idx, "Current_acc", .0)
        self.y_axis_target_pos = await self.y_axis.add_variable(idx, "Target_pos", .0)
        self.y_axis_target_speed = await self.y_axis.add_variable(idx, "Target_speed", .0)
        self.y_axis_power = await self.y_axis.add_variable(idx, "Power", .0)

        self.y_axis_settings = await self.y_axis.add_object(idx, "Settings")
        self.y_axis_max_speed = await self.y_axis_settings.add_variable(idx, "Max_speed",
                                                                        self.cnc_machine.y_axis.max_speed)
        self.y_axis_max_acc = await self.y_axis_settings.add_variable(idx, "Max_acc", self.cnc_machine.y_axis.max_acc)

        await self.y_axis_max_speed.set_writable()
        await self.y_axis_max_acc.set_writable()

        self.z_axis = await self.axes_node.add_object(idx, "Z")
        self.z_axis_pos = await self.z_axis.add_variable(idx, "Current_pos", .0)
        self.z_axis_speed = await self.z_axis.add_variable(idx, "Current_speed", .0)
        self.z_axis_acc = await self.z_axis.add_variable(idx, "Current_acc", .0)
        self.z_axis_target_pos = await self.z_axis.add_variable(idx, "Target_pos", .0)
        self.z_axis_target_speed = await self.z_axis.add_variable(idx, "Target_speed", .0)
        self.z_axis_power = await self.z_axis.add_variable(idx, "Power", .0)

        self.z_axis_settings = await self.z_axis.add_object(idx, "Settings")
        self.z_axis_max_speed = await self.z_axis_settings.add_variable(idx, "Max_speed",
                                                                        self.cnc_machine.z_axis.max_speed)
        self.z_axis_max_acc = await self.z_axis_settings.add_variable(idx, "Max_acc", self.cnc_machine.z_axis.max_acc)

        await self.z_axis_max_speed.set_writable()
        await self.z_axis_max_acc.set_writable()

        self.e_axis = await self.axes_node.add_object(idx, "E")
        self.e_axis_pos = await self.e_axis.add_variable(idx, "Current_pos", .0)
        self.e_axis_speed = await self.e_axis.add_variable(idx, "Current_speed", .0)
        self.e_axis_acc = await self.e_axis.add_variable(idx, "Current_acc", .0)
        self.e_axis_target_pos = await self.e_axis.add_variable(idx, "Target_pos", .0)
        self.e_axis_target_speed = await self.e_axis.add_variable(idx, "Target_speed", .0)
        self.e_axis_power = await self.e_axis.add_variable(idx, "Power", .0)

        self.e_axis_settings = await self.e_axis.add_object(idx, "Settings")
        self.e_axis_max_speed = await self.e_axis_settings.add_variable(idx, "Max_speed",
                                                                        self.cnc_machine.e_axis.max_speed)
        self.e_axis_max_acc = await self.e_axis_settings.add_variable(idx, "Max_acc", self.cnc_machine.e_axis.max_acc)

        await self.e_axis_max_speed.set_writable()
        await self.e_axis_max_acc.set_writable()

        self.nozzle = await self.heaters_node.add_object(idx, "Nozzle")
        self.nozzle_temp = await self.nozzle.add_variable(idx, "Temperature", .0)
        self.nozzle_target_temp = await self.nozzle.add_variable(idx, "Target temperature", .0)
        self.nozzle_power = await self.nozzle.add_variable(idx, "Power", .0)
        self.nozzle_setting = await self.nozzle.add_object(idx, "Settings")
        self.nozzle_kp = await self.nozzle_setting.add_variable(idx, "Kp", self.cnc_machine.nozzle.control.kd)
        self.nozzle_ki = await self.nozzle_setting.add_variable(idx, "Ki", self.cnc_machine.nozzle.control.ki)
        self.nozzle_wu = await self.nozzle_setting.add_variable(idx, "wind_up", self.cnc_machine.nozzle.control.wind_up)
        self.nozzle_settle_window = await self.nozzle_setting.add_variable(idx, "settle_windows",
                                                                           self.cnc_machine.nozzle.reached_temp_threshold)
        self.nozzle_settle_time = await self.nozzle_setting.add_variable(idx, "settle_time",
                                                                         self.cnc_machine.nozzle.reached_time_threshold)

        await self.nozzle_kp.set_writable()
        await self.nozzle_ki.set_writable()
        await self.nozzle_wu.set_writable()
        await self.nozzle_settle_time.set_writable()
        await self.nozzle_settle_window.set_writable()

        self.plate = await self.heaters_node.add_object(idx, "plate")
        self.plate_temp = await self.plate.add_variable(idx, "Temperature", .0)
        self.plate_target_temp = await self.plate.add_variable(idx, "Target temperature", .0)
        self.plate_power = await self.plate.add_variable(idx, "Power", .0)
        self.plate_setting = await self.plate.add_object(idx, "Settings")
        self.plate_kp = await self.plate_setting.add_variable(idx, "Kp", self.cnc_machine.plate.control.kd)
        self.plate_ki = await self.plate_setting.add_variable(idx, "Ki", self.cnc_machine.plate.control.ki)
        self.plate_wu = await self.plate_setting.add_variable(idx, "wind_up", self.cnc_machine.plate.control.wind_up)
        self.plate_settle_window = await self.plate_setting.add_variable(idx, "settle_windows",
                                                                         self.cnc_machine.plate.reached_temp_threshold)
        self.plate_settle_time = await self.plate_setting.add_variable(idx, "plate_windows",
                                                                       self.cnc_machine.plate.reached_time_threshold)

        await self.plate_kp.set_writable()
        await self.plate_ki.set_writable()
        await self.plate_wu.set_writable()
        await self.plate_settle_time.set_writable()
        await self.plate_settle_window.set_writable()

        actions = await self.server.nodes.objects.add_object(idx, "Actions")

        self.read_gcode_line = await actions.add_method(idx, "Execute g-code line", self.ua_execute_gcode_line,
                                                        [ua.VariantType.LocalizedText])
        self.read_gcode_file = await actions.add_method(idx, "Execute g-code file", self.ua_execute_gcode_file,
                                                        [ua.VariantType.LocalizedText])
        self.pause_gcode_file = await actions.add_method(idx, "Pause g-code file", self.ua_pause_gcode_execution)
        self.resume_gcode_file = await actions.add_method(idx, "Resume g-code file", self.ua_resume_gcode_execution)
        self.abort_gcode_file = await actions.add_method(idx, "Abort g-code file", self.abort_gcode_execution)

        print("ok")

    async def update_opc_server(self):
        """
        Update opc-monitoring-nodes with the simulation value, update the simulation value with the opc-settings-nodes
        """

        # machine -> opcua
        await self.status_node.write_value(self.cnc_machine.status.value)
        await self.power_node.write_value(
            self.cnc_machine.x_axis.power +
            self.cnc_machine.y_axis.power +
            self.cnc_machine.z_axis.power +
            self.cnc_machine.e_axis.power +
            self.cnc_machine.nozzle.power +
            self.cnc_machine.plate.power)

        await self.x_axis_pos.write_value(self.cnc_machine.x_axis.get_virtual_position())
        await self.x_axis_speed.write_value(self.cnc_machine.x_axis.current_speed)
        await self.x_axis_acc.write_value(self.cnc_machine.x_axis.current_acc)
        await self.x_axis_target_pos.write_value(self.cnc_machine.x_axis._target_pos)
        await self.x_axis_target_speed.write_value(self.cnc_machine.x_axis.target_speed)
        await self.x_axis_power.write_value(self.cnc_machine.x_axis.power)

        await self.y_axis_pos.write_value(self.cnc_machine.y_axis.get_virtual_position())
        await self.y_axis_speed.write_value(self.cnc_machine.y_axis.current_speed)
        await self.y_axis_acc.write_value(self.cnc_machine.y_axis.current_acc)
        await self.y_axis_target_pos.write_value(self.cnc_machine.y_axis._target_pos)
        await self.y_axis_target_speed.write_value(self.cnc_machine.y_axis.target_speed)
        await self.y_axis_power.write_value(self.cnc_machine.y_axis.power)

        await self.z_axis_pos.write_value(self.cnc_machine.z_axis.get_virtual_position())
        await self.z_axis_speed.write_value(self.cnc_machine.z_axis.current_speed)
        await self.z_axis_acc.write_value(self.cnc_machine.z_axis.current_acc)
        await self.z_axis_target_pos.write_value(self.cnc_machine.z_axis._target_pos)
        await self.z_axis_target_speed.write_value(self.cnc_machine.z_axis.target_speed)
        await self.z_axis_power.write_value(self.cnc_machine.z_axis.power)

        await self.e_axis_pos.write_value(self.cnc_machine.e_axis.get_virtual_position())
        await self.e_axis_speed.write_value(self.cnc_machine.e_axis.current_speed)
        await self.e_axis_acc.write_value(self.cnc_machine.e_axis.current_acc)
        await self.e_axis_target_pos.write_value(self.cnc_machine.e_axis._target_pos)
        await self.e_axis_target_speed.write_value(self.cnc_machine.e_axis.target_speed)
        await self.e_axis_power.write_value(self.cnc_machine.e_axis.power)

        await self.nozzle_temp.write_value(self.cnc_machine.nozzle.current_temp)
        await self.nozzle_target_temp.write_value(self.cnc_machine.nozzle.get_set_point_temp())
        await self.nozzle_power.write_value(self.cnc_machine.nozzle.power)

        await self.plate_temp.write_value(self.cnc_machine.plate.current_temp)
        await self.plate_target_temp.write_value(self.cnc_machine.plate.get_set_point_temp())
        await self.plate_power.write_value(self.cnc_machine.plate.power)

        # opcua -> machine
        self.cnc_machine.feedrate_override = await self.feedrate_node.get_value()
        self.cnc_machine.x_axis.max_speed = await self.x_axis_max_speed.get_value()
        self.cnc_machine.x_axis.max_acc = await self.x_axis_max_acc.get_value()
        self.cnc_machine.y_axis.max_speed = await self.y_axis_max_speed.get_value()
        self.cnc_machine.y_axis.max_acc = await self.y_axis_max_acc.get_value()
        self.cnc_machine.z_axis.max_speed = await self.z_axis_max_speed.get_value()
        self.cnc_machine.z_axis.max_acc = await self.z_axis_max_acc.get_value()
        self.cnc_machine.e_axis.max_speed = await self.e_axis_max_speed.get_value()
        self.cnc_machine.e_axis.max_acc = await self.e_axis_max_acc.get_value()

        self.cnc_machine.nozzle.control.kd = await self.nozzle_kp.get_value()
        self.cnc_machine.nozzle.control.ki = await self.nozzle_ki.get_value()
        self.cnc_machine.nozzle.control.wind_up = await self.nozzle_wu.get_value()
        self.cnc_machine.nozzle.reached_temp_threshold = await self.nozzle_settle_window.get_value()
        self.cnc_machine.nozzle.reached_time_threshold = await self.nozzle_settle_time.get_value()

        self.cnc_machine.plate.control.kd = await self.plate_kp.get_value()
        self.cnc_machine.plate.control.ki = await self.plate_ki.get_value()
        self.cnc_machine.plate.control.wind_up = await self.plate_wu.get_value()
        self.cnc_machine.plate.reached_temp_threshold = await self.plate_settle_window.get_value()
        self.cnc_machine.plate.reached_time_threshold = await self.plate_settle_time.get_value()

        # self.cnc_machine.temperature = await self.temp_node.get_value()

    async def execute_gcode_line(self, line: str):
        """
        Execute a g-code command, the command is ignored if the machine is busy
        :param line: gcode command to be executed
        """
        if self.current_task is None or self.current_task.done():
            self.current_task = asyncio.create_task(self.cnc_machine.run_gcode_line(line))

    async def execute_gcode_file(self, file_path: str):
        """
        Execute a g-code file, the command is ignored if the machine is busy
        :param file_path: path to g-code file
        """
        if self.current_task is None or self.current_task.done():
            gcode_path = Path(file_path)
            if gcode_path.is_file():
                self.current_task = asyncio.create_task(self.cnc_machine.run_gcode_file(gcode_path))

    async def pause_gcode_execution(self):
        """
        The g-code execution is paused after the current line has been executed
        """
        if self.current_task is not None and not self.current_task.done():
            self.cnc_machine.pause()

    async def resume_gcode_execution(self):
        """
        The g-code execution is resumed if it has been paused
        """
        if self.current_task is not None and not self.current_task.done():
            self.cnc_machine.resume()

    async def abort_gcode_execution(self):
        """
        Abort the current g-code execution after the current line has been executed
        """
        if self.current_task is not None and not self.current_task.done():
            self.cnc_machine.abort()

    @uamethod
    async def ua_execute_gcode_line(self, parent, line):
        if isinstance(line, bytes) or isinstance(line, bytearray):
            line = line.decode('utf-8')
        elif isinstance(line, ua.LocalizedText):
            line = line.Text

        await self.execute_gcode_line(line)

    @uamethod
    async def ua_execute_gcode_file(self, parent, file_path):
        if isinstance(file_path, bytes) or isinstance(file_path, bytearray):
            file_path = file_path.decode('utf-8')
        elif isinstance(file_path, ua.LocalizedText):
            file_path = file_path.Text

        await self.execute_gcode_file(file_path)

    @uamethod
    async def ua_pause_gcode_execution(self, parent):
        await self.pause_gcode_execution()

    @uamethod
    async def ua_resume_gcode_execution(self, parent):
        await self.resume_gcode_execution()

    @uamethod
    async def ua_abort_gcode_execution(self, parent):
        await self.abort_gcode_execution()

    def draw(self):
        """
        Print the status of the machine on the terminal
        """

        s = [
            "t:{:.1f} x:{:.1f}/{:.1f} y:{:.1f}/{:.1f} z:{:.1f}/{:.1f} e:{:.1f}/{:.1f} Nozzle:{:.1f}/{:.1f} Plate:{:.1f}/{:.1f} Status: {}".format(
                self.time,
                self.cnc_machine.x_axis.get_virtual_position() * 1000,
                self.cnc_machine.x_axis.get_virtual_target() * 1000,
                self.cnc_machine.y_axis.get_virtual_position() * 1000,
                self.cnc_machine.y_axis.get_virtual_target() * 1000,
                self.cnc_machine.z_axis.get_virtual_position() * 1000,
                self.cnc_machine.z_axis.get_virtual_target() * 1000,
                self.cnc_machine.e_axis.get_virtual_position() * 1000,
                self.cnc_machine.e_axis.get_virtual_target() * 1000,
                self.cnc_machine.nozzle.current_temp,
                self.cnc_machine.nozzle.get_set_point_temp(),
                self.cnc_machine.plate.current_temp,
                self.cnc_machine.plate.get_set_point_temp(),
                CNCStatus_strings[self.cnc_machine.status.value]
            )]

        if self.cnc_machine.current_gcode_file is not None:
            s.append(f"{self.cnc_machine.current_gcode_file} - {self.cnc_machine.gcode_progress}%")

        if self.cnc_machine.current_gcode_line is not None:
            s.append(self.cnc_machine.current_gcode_line.rstrip())

        print(
            "\r{}".format(" - ".join(s)), end="")

    async def close(self):
        """
        Terminate tasks and axit the env main loop
        """
        self.cnc_machine.shutdown = True
        if self.current_task is not None:
            await self.current_task
        self.closing = True

    async def run(self):
        """
        Run the env main loop. Call close to terminate the loop.
        """

        async with self.server:
            while not self.closing:
                self.cnc_machine.run(self.time)
                if self.enable_draw:
                    self.draw()
                    self.tasks.append(asyncio.create_task(self.update_opc_server()))
                await asyncio.sleep(self.time_step / self.time_mult)
                for task in self.tasks:
                    await task
                self.tasks = []
                self.time += self.time_step / self.time_mult

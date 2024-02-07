import math
import random
from typing import Optional
import asyncio
import json
import struct
from components.mechanic import SingleAxis
from components.thermal import HeatingBody
from enum import IntEnum
import pygcode as pgc
from pygcode.exceptions import GCodeWordStrError
from pathlib import Path


# constants


class GCodeSetPlateTempBlocking(pgc.GCodeNonModal):
    """M190: Plate temperature"""
    param_letters = set('S')
    word_key = pgc.Word('M', 190)
    word_letter = 'M'


class GCodeSetPlateTempNonBlocking(pgc.GCodeNonModal):
    """M190: Plate temperature"""
    param_letters = set('S')
    word_key = pgc.Word('M', 140)
    word_letter = 'M'


class GCodeSetNozzleTempNonBlocking(pgc.GCodeNonModal):
    """M104: Nozzle temperature"""
    param_letters = set('S')
    word_key = pgc.Word('M', 104)
    word_letter = 'M'


class GCodeSetNozzleTempBlocking(pgc.GCodeNonModal):
    """M109: Nozzle temperature"""
    param_letters = set('S')
    word_key = pgc.Word('M', 109)
    word_letter = 'M'


pgc.gcodes.GCodeMotion.param_letters.add('E')  # we need E to be a valid parameter
pgc.gcodes.GCodeMotion.param_letters.add('F')  # we need E to be a valid parameter
pgc.gcodes.GCodeCoordSystemOffset.param_letters = set('XYZE')


class CNCStatus(IntEnum):
    IDLE = 0
    WORKING = 1
    PAUSED = 2


class CNCMachine:
    """
    Simulation of a simple 3D printer
    """

    def __init__(self):
        env_temp = 25

        self.x_axis = SingleAxis(min_pos=.0, max_pos=0.2, max_speed=0.1, max_acc=1.0, mass=0.5, friction=15)
        self.y_axis = SingleAxis(min_pos=.0, max_pos=0.2, max_speed=0.1, max_acc=1.0, mass=0.5, friction=13)
        self.z_axis = SingleAxis(min_pos=.0, max_pos=0.2, max_speed=0.01, max_acc=0.05, mass=1.5, friction=30)
        self.e_axis = SingleAxis(min_pos=.0, max_pos=0, max_speed=0.01, max_acc=0.05, mass=0.1, friction=100)
        self.plate = HeatingBody(env_temp, mass=0.3, surface=0.04, h_power=240, c_heat=420, k_heat=15)
        self.plate.control.kd = 20
        self.plate.control.ki = 2
        self.plate.control.wind_up = 30
        self.nozzle = HeatingBody(env_temp, mass=0.02, surface=0.001, h_power=120, c_heat=420, k_heat=25)
        self.nozzle.control.kd = 20
        self.nozzle.control.ki = 1
        self.nozzle.control.wind_up = 10
        self.status = CNCStatus.IDLE
        self.default_speed = 0.01
        self.homed = False
        self.gcode_progress = 0
        self.feedrate_override = 1.0
        self.pause_gcode_file = False
        self.abort_gcode_file = False
        self.current_gcode_file = None
        self.current_gcode_line = None
        self.shutdown = False

    def get_pos(self) -> tuple[float, float, float, float]:
        return self.x_axis.get_virtual_position(), self.y_axis.get_virtual_position(), self.z_axis.get_virtual_position(), self.e_axis.get_virtual_position()

    def get_temp(self) -> tuple[float, float]:
        return self.plate.current_temp, self.nozzle.current_temp

    def run(self, time: float):
        """
        Main function that compute the new parameters for the simulation
        :param time: simulation time [s]
        """

        self.x_axis.run(time)
        self.y_axis.run(time)
        self.z_axis.run(time)
        self.e_axis.run(time)

        self.plate.run(time)
        self.nozzle.run(time)

    def get_settings_json(self):
        out_dict = {
            "x-axis": self.x_axis.get_settings_dict(),
            "y-axis": self.x_axis.get_settings_dict(),
            "z-axis": self.x_axis.get_settings_dict(),
            "e-axis": self.x_axis.get_settings_dict()
        }

        return json.dumps(out_dict)

    def get_settings_bin(self):
        s = bytes()
        s += struct.pack('f', self.x_axis.max_speed)
        s += struct.pack('f', self.y_axis.max_speed)
        s += struct.pack('f', self.z_axis.max_speed)
        s += struct.pack('f', self.e_axis.max_speed)

        s += struct.pack('f', self.x_axis.max_acc)
        s += struct.pack('f', self.y_axis.max_acc)
        s += struct.pack('f', self.z_axis.max_acc)
        s += struct.pack('f', self.e_axis.max_acc)
        return s

    def set_settings_from_json(self, in_json: str):
        in_dict = json.loads(in_json)

        if "x-axis" in in_dict:
            self.x_axis.set_settings(in_dict["x-axis"])

        if "y-axis" in in_dict:
            self.y_axis.set_settings(in_dict["y-axis"])

        if "z-axis" in in_dict:
            self.z_axis.set_settings(in_dict["z-axis"])

        if "e-axis" in in_dict:
            self.e_axis.set_settings(in_dict["e-axis"])

    def set_settings_from_bin(self, in_bytes: bytes):
        x_speed, y_speed, z_speed, e_speed, x_acc, y_acc, z_acc, e_acc = \
            struct.unpack("ffffffff", in_bytes)

        self.x_axis.max_speed = x_speed
        self.x_axis.max_acc = x_acc
        self.x_axis.recompute_target()

        self.y_axis.max_speed = y_speed
        self.y_axis.max_acc = y_acc
        self.y_axis.recompute_target()

        self.z_axis.max_speed = z_speed
        self.z_axis.max_acc = z_acc
        self.z_axis.recompute_target()

        self.e_axis.max_speed = e_speed
        self.e_axis.max_acc = e_acc
        self.e_axis.recompute_target()

    def is_moving(self):
        """
        :return: True if any axis is moving, False otherwise
        """
        return self.x_axis.is_moving() or self.y_axis.is_moving() or self.z_axis.is_moving() or self.e_axis.is_moving()

    async def home(self):
        """
        Home all axis. With method always block execution until homing is complete
        """
        # always blocking

        speed = self.default_speed
        await self.set_target(x=self.x_axis.physical_to_virtual(0.), speed=0.01, blocking=True)
        self.x_axis.offset = .0
        await self.set_target(x=0.002, speed=0.01, blocking=True)
        await self.set_target(x=0, speed=0.001, blocking=True)

        await self.set_target(y=self.y_axis.physical_to_virtual(0.), speed=0.01, blocking=True)
        self.y_axis.offset = .0
        await self.set_target(y=0.002, speed=0.01, blocking=True)
        await self.set_target(y=0, speed=0.001, blocking=True)

        await self.set_target(z=self.z_axis.physical_to_virtual(0.), speed=0.01, blocking=True)
        self.z_axis.offset = .0
        await self.set_target(z=0.002, speed=0.01, blocking=True)
        await self.set_target(z=0, speed=0.001, blocking=True)
        self.homed = True
        self.default_speed = speed

    async def set_plate_temp(self, temp: float, blocking=False):
        """
        :param temp: set point temperature of the plate [°C]
        :param blocking: if true, will block until the plate reach the target temperature
        """

        self.plate.set_set_point_temp(temp)

        if not temp:
            blocking = False  # never block a stop heater command

        if blocking:
            while not self.plate.temp_reached and not self.shutdown:
                await asyncio.sleep(0.01)

    async def set_nozzle_temp(self, temp: float, blocking=False):
        """
        :param temp: set point temperature of the plate [°C]
        :param blocking: if true, will block until the plate reach the target temperature
        """

        if not temp:
            blocking = False  # never block a stop heater command

        self.nozzle.set_set_point_temp(temp)
        if blocking:
            while not self.nozzle.temp_reached and not self.shutdown:
                await asyncio.sleep(0.01)

    async def set_target(self,
                         x: Optional[float] = None,
                         y: Optional[float] = None,
                         z: Optional[float] = None,
                         e: Optional[float] = None,
                         speed: Optional[float] = None,
                         blocking: Optional[float] = False):
        """
        Set the motion of the machine toward a specific target
        :param x: x-axis target position [m]
        :param y: y-axis target position [m]
        :param z: z-axis target position [m]
        :param e: e-axis target position [m]
        :param speed: global speed of the movement [m/s]
        :param blocking: block until the target position in reach
        """

        s_x = abs(x - self.x_axis.get_virtual_position()) if x is not None else 0
        s_y = abs(y - self.y_axis.get_virtual_position()) if y is not None else 0
        s_z = abs(z - self.z_axis.get_virtual_position()) if z is not None else 0
        s_e = abs(e - self.e_axis.get_virtual_position()) if e is not None else 0

        if speed is None:
            speed = self.default_speed
        else:
            self.default_speed = speed

        speed = speed * self.feedrate_override

        # total space
        if x is not None or y is not None or z is not None:
            s = math.sqrt(s_x ** 2 + s_y ** 2 + s_z ** 2)
        elif e is not None:
            s = s_e
        else:
            return

        if s == 0:  # no movement
            return

        t = s / speed

        x_rs = s_x / t / self.x_axis.max_speed
        y_rs = s_y / t / self.y_axis.max_speed
        z_rs = s_z / t / self.z_axis.max_speed
        e_rs = s_e / t / self.e_axis.max_speed

        rate = max([x_rs, y_rs, z_rs, e_rs, 1.0])  # if every override is below 100% keep 100%

        if x is not None:
            self.x_axis.set_target(x, x_rs * self.x_axis.max_speed / rate)
        if y is not None:
            self.y_axis.set_target(y, y_rs * self.y_axis.max_speed / rate)
        if z is not None:
            self.z_axis.set_target(z, z_rs * self.z_axis.max_speed / rate)
        if e is not None:
            self.e_axis.set_target(e, e_rs * self.e_axis.max_speed / rate)

        if blocking:
            while self.is_moving() and not self.shutdown:
                await asyncio.sleep(0.01)

    async def run_gcode_line(self, line: str):
        """
        :param line: g-code line to execute
        """

        self.current_gcode_line = line

        try:
            gline = pgc.line.Line(line)
        except GCodeWordStrError:
            self.current_gcode_line = None
            return

        for gcode in gline.gcodes:
            if isinstance(gcode, pgc.GCodeLinearMove):  # linear move (G1)
                mov_dict = gcode.get_param_dict()
                await self.set_target(
                    x=mov_dict['X'] / 1000 if 'X' in mov_dict else None,
                    y=mov_dict['Y'] / 1000 if 'Y' in mov_dict else None,
                    z=mov_dict['Z'] / 1000 if 'Z' in mov_dict else None,
                    e=mov_dict['E'] / 1000 if 'E' in mov_dict else None,
                    speed=mov_dict['F'] / 60 / 1000 if 'F' in mov_dict else None,
                    blocking=True
                )

            elif isinstance(gcode, pgc.GCodeCoordSystemOffset):  # coord sys offset (G92)
                mov_dict = gcode.get_param_dict()

                if 'X' in mov_dict:
                    self.x_axis.set_offset(mov_dict['X'] / 1000)

                if 'Y' in mov_dict:
                    self.y_axis.set_offset(mov_dict['Y'] / 1000)

                if 'Z' in mov_dict:
                    self.z_axis.set_offset(mov_dict['Z'] / 1000)

                if 'E' in mov_dict:
                    self.e_axis.set_offset(mov_dict['E'] / 1000)

            elif isinstance(gcode, pgc.GCodeGotoPredefinedPosition):  # home axes (G28)
                await self.home()

            elif isinstance(gcode, GCodeSetPlateTempBlocking):  # set plate temp (M190)
                mov_dict = gcode.get_param_dict()
                await self.set_plate_temp(float(mov_dict['S']), blocking=True)

            elif isinstance(gcode, GCodeSetPlateTempNonBlocking):
                mov_dict = gcode.get_param_dict()
                await self.set_plate_temp(float(mov_dict['S']))

            elif isinstance(gcode, GCodeSetNozzleTempBlocking):  # set nozzle temp (M104)
                mov_dict = gcode.get_param_dict()
                await self.set_nozzle_temp(float(mov_dict['S']), blocking=True)

            elif isinstance(gcode, GCodeSetNozzleTempNonBlocking):  # set nozzle temp blocking
                mov_dict = gcode.get_param_dict()
                await self.set_nozzle_temp(float(mov_dict['S']))

        self.current_gcode_line = None

    async def hang(self):
        """
        wait until the  pause_gcode_file flag is set to false. Exit if shutdown is true
        """
        self.status = CNCStatus.PAUSED
        while self.pause_gcode_file and not self.shutdown:
            await asyncio.sleep(0.5)
        self.status = CNCStatus.WORKING

    async def run_gcode_file(self, gcode_path: Path):
        """
        Execute a gcode file une line at a time
        :param gcode_path: path of the gcode to execute
        """

        gfile = gcode_path.open("r")
        file_lines = gfile.readlines()
        n_lines = len(file_lines)

        self.current_gcode_file = gcode_path.stem

        self.status = CNCStatus.WORKING

        for i, line in enumerate(file_lines):
            self.gcode_progress = (10 + int(i / n_lines * 80))
            await self.run_gcode_line(line)
            if self.pause_gcode_file:
                await self.hang()
            if self.abort_gcode_file:
                self.abort_gcode_file = False
                break

        self.gcode_progress = 100
        self.status = CNCStatus.IDLE
        gfile.close()
        self.current_gcode_file = None

    def pause(self):
        if self.status == CNCStatus.WORKING:
            self.pause_gcode_file = True

    def resume(self):
        if self.status == CNCStatus.PAUSED:
            self.pause_gcode_file = False

    def abort(self):
        if self.status == CNCStatus.WORKING:
            self.abort_gcode_file = True

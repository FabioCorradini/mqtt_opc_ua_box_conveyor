from .general import PIRegulator

SIGMA = 5.670367e-8  # costante di Stefan-Boltzmann


class HeatingBody:
    """
    Simulation of a body heated by a PI controlled electrical heater
    """
    def __init__(self, env_temp=25.0, mass=1.0, surface=0.1, h_power=1, c_heat=420, k_heat=20):
        """
        :param env_temp: environment temperature  [°C]
        :param mass: heated mass [kg]
        :param surface:  surface exposed to the environment [m^2]
        :param h_power:  max heating power [W]
        :param c_heat:  specific heat capacity of the material  [J/(kg K)]
        :param k_heat: heat conductivity of the material [W/m^2]
        """
        self.temp_reached = True
        self.env_temp = env_temp
        self.current_temp = env_temp
        self.mass = mass
        self.surface = surface
        self.h_power = h_power
        self.c_heat = c_heat
        self.k_heat = k_heat
        self.control = PIRegulator(1.0, 0.1, 0, self.h_power, 0, 1000)
        self._set_point_temp = .0
        self._old_t = .0
        self._old_power = .0
        self.power = .0
        self.power_consumption = .0
        self.reached_time_threshold = .1  # s
        self.reached_temp_threshold = .1
        self._temp_reached_timer = .0

    def _run_temperature(self, time: float):

        if self._set_point_temp != .0:
            self.control.set_point = self._set_point_temp
            power_in = self.control.run(time, self.current_temp)
        else:
            power_in = .0

        power_out = self.surface * (
                (self.current_temp - self.env_temp) * self.k_heat +  # conduction-convection
                ((self.current_temp + 273.15) ** 4 - (self.env_temp + 273.15) ** 4) * SIGMA)  # radiation

        self.power_consumption = power_in

        self.power = power_in - power_out

        self.current_temp += (self.power + self._old_power) * (time - self._old_t) / 2 / self.c_heat / self.mass

        self._old_power = self.power

    def run(self, time: float):
        """
        Main function that compute the new parameters for the simulation
        :param time: simulation time [s]
        """
        self._run_temperature(time)
        self.check_temp_reached(time)
        self._old_t = time

    def get_set_point_temp(self):
        return self._set_point_temp

    def set_set_point_temp(self, value: float):
        """
        Set a new set point in the PI controller and reset the temp_reached flag
        :param value: new set point value [°C]
        """
        self._set_point_temp = value
        self.control.set_point = value
        self.temp_reached = False
        self._temp_reached_timer = .0

    def check_temp_reached(self, time: float):
        """
        if the current temperature is in a range of +- reached_temp_threshold around target temp for more than
        reached_time_threshold the temp_reached flag is set to True
        :param time: simulation time [ms]
        """
        if abs(self.current_temp - self._set_point_temp) < self.reached_temp_threshold:
            self._temp_reached_timer += time - self._old_t
            if self._temp_reached_timer > self.reached_time_threshold:
                self.temp_reached = True
        else:
            self.temp_reached = False
            self._temp_reached_timer = .0

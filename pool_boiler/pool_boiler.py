import math
import time


class BoilingPot:
    RHO_STEEL = 7850  # kg/m^3
    RHO_WAT = 1000  # kg/m^3
    BOILING_T = 100
    HC_STEEL = 470  # J/(kg K)
    HC_WAT = 4186  # J*(kg K)
    LH_WAT = 2.26e6  # J/kg
    SIGMA = 5.670367e-8  # costante di Stefan-Boltzmann
    T_LIMIT = 120

    def __init__(self, d=0.300, s=0.005, h=0.5, T_env=25.0, k_heat=20):
        self.A = d ** 2 * math.pi / 4
        self.steal_v = math.pi / 4 * ((d + 2 * s) ** 2 * (s + h) - d ** 2 * h)
        self.steel_m = self.steal_v * self.RHO_STEEL
        self.wat_v = 0.
        self.wat_h = 0.
        self.wat_m = 0.
        self.T_env = T_env
        self.T = T_env
        self._max_surf = math.pi * ((d + 2 * s) * (s + h) + (d + 2 * s) ** 2 / 4 + d * h)
        self.D_in = d
        self.h_max = h
        self._old_t = .0
        self._old_power = .0
        self._old_flow = .0
        self.k_heat = k_heat
        self.boiling = False
        self.level_alert = False
        self.temperature_alert = False

    def get_surface(self):
        return self._max_surf - math.pi * self.D_in * self.wat_h

    def run(self, current_time: float, power_in=0.0, in_flow=0.0, out_flow=0.0):
        dt = current_time - self._old_t

        surface = self.get_surface()

        power_out = surface * (
                (self.T - self.T_env) * self.k_heat +  # conduction-convection
                ((self.T + 273.15) ** 4 - (self.T_env + 273.15) ** 4) * self.SIGMA)  # radiation

        power = power_in - power_out

        flow = in_flow - out_flow

        d_energy = (power + self._old_power) * dt / 2

        d_vol = (flow + self._old_flow) * dt / 2

        old_energy = (self.wat_m * self.HC_WAT + self.steel_m * self.HC_STEEL) * (self.T - self.T_env)

        self.wat_v = max(self.wat_v + d_vol, 0.0)
        self.wat_h = self.wat_v / self.A
        self.wat_m = self.wat_v * self.RHO_WAT

        new_T = self.T_env + (old_energy + d_energy) / (self.wat_m * self.HC_WAT + self.steel_m * self.HC_STEEL)

        if new_T > 100.0 and self.wat_m > 0.0:
            self.boiling = True
            dT = 100.0 - self.T
            thermal_energy = dT * (self.wat_m * self.HC_WAT + self.steel_m * self.HC_STEEL)
            vaporized_mass = (d_energy - thermal_energy) / self.LH_WAT
            self.wat_m = max(self.wat_m - vaporized_mass, 0.0)
            self.wat_v = self.wat_m / self.RHO_WAT
            self.wat_h = self.wat_v / self.A
            self.T = 100.0
        else:
            self.boiling = False
            self.T = new_T

        self.check_alerts()

        self._old_t = current_time
        self._old_power = power
        self._old_flow = flow

    def check_alerts(self):
        if self.T > self.T_LIMIT:
            self.temperature_alert = True
        elif self.T <= self.T_LIMIT - 10.0:
            self.temperature_alert = False

        if self.wat_h > self.h_max:
            self.level_alert = True
            self.wat_h = self.h_max
            self.wat_v = self.wat_h * self.A
            self.wat_m = self.wat_v * self.RHO_WAT
        elif self.wat_h <= self.h_max - 0.001:
            self.level_alert = False


if __name__ == '__main__':
    bp = BoilingPot()
    dt = 0.1
    power = 8000
    in_flow = 1e-3
    t = 0

    print("time, temperature, power, mass")

    while bp.wat_h < 0.001:
        bp.run(t, power_in=0, in_flow=in_flow)
        print(f"{t:.2f}, {bp.T:3f}, {bp._old_power:.1f}, {bp.wat_m:.5f}")
        t += dt

    while bp.T < 110:
        bp.run(t, power_in=power)
        print(f"{t:.2f}, {bp.T:3f}, {bp._old_power:.1f}, {bp.wat_m:.5f}")
        t += dt

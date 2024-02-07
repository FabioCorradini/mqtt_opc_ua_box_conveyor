from typing import Optional


class PIRegulator:
    def __init__(self, kd: float,
                 ki: float,
                 set_point: float,
                 max_out: Optional[float] = None,
                 min_out: Optional[float] = None,
                 wind_up: Optional[float] = None):
        """
        :param kd: proportional gain
        :param ki: integral gain
        :param set_point: starting set point
        :param max_out: max output value
        :param min_out: min output value
        :param wind_up: anti wind up value (limit of the integral error)
        """

        self.kd = kd
        self.ki = ki
        self.set_point = set_point
        self.max_out = max_out
        self.min_out = min_out
        self.wind_up = wind_up
        self._ie = 0
        self._old_e = 0
        self._old_t = 0

    def run(self, time: float, input_val: float):
        """
        Main function that compute the new parameters for the simulation
        :param time: current time [s]
        :param input_val: current input value
        """
        e = self.set_point - input_val
        self._ie += (self._old_e + e) * (time - self._old_t) / 2
        if self.wind_up is not None and self._ie > self.wind_up:
            self._ie = self.wind_up

        self._old_e = e
        self._old_t = time

        out = self.kd * e + self.ki * self._ie

        if self.max_out is not None and out > self.max_out:
            return self.max_out
        if self.min_out is not None and out < self.min_out:
            return self.min_out

        return out

    def reset(self):
        self._ie = 0
        self._old_e = 0




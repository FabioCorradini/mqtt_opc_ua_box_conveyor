from typing import Optional
import math


class SingleAxis:
    def __init__(self, min_pos=.0, max_pos=100.0, max_speed=10.0, max_acc=100.0, mass=1.0, friction=10.0):
        """
        :param min_pos: the minimum position of the axis (CURRENTLY NOT USED)
        :param max_pos: the maximum position of the axis (CURRENTLY NOT USED)
        :param max_speed: max speed of the axis [m/s]
        :param max_acc: max acceleration of the axis [m/s^2]
        :param mass: mass of the moving parts of the axis [kg]
        :param friction: friction of the axis [N]
        """

        self._current_pos = .0
        self.current_speed = .0
        self.current_acc = .0

        self._target_pos = .0
        self.target_speed = .0

        self.min_pos = min_pos
        self.max_pos = max_pos
        self.max_speed = max_speed
        self.max_acc = max_acc

        self.mass = mass
        self.thrust = .0
        self.power = .0
        self.friction = friction

        self.trip = .0
        self.acc_trip = .0
        self.dec_trip = .0

        self.movement_time = .0
        self._movement_start_time = .0
        self._movement_start_pos = .0
        self.acc_time = .0
        self.dec_time = .0

        self.offset = .0

        self.direction = 1

    def get_virtual_position(self) -> float:
        """
        :return: the position used by the motion controller (not the physical one)
        """
        return self.physical_to_virtual(self._current_pos)

    def get_physical_position(self) -> float:
        """
        :return: the physical position of the axis (may differ from the position used by motion control)
        """
        return self._current_pos

    def get_virtual_target(self) -> float:
        """
        :return: the target position  of the motion controller (not the physical one)
        """
        return self.physical_to_virtual(self._target_pos)

    def get_physical_target(self):
        """
        :return: the physical target position of the axis (may differ from the position used by motion control)
        """
        return self._target_pos

    def set_offset(self, virtual_position: float):
        """
        :param virtual_position: position to force on the motion system
        """
        self.offset = virtual_position - self._current_pos

    def virtual_to_physical(self, virtual_value: float) -> float:
        return virtual_value - self.offset

    def physical_to_virtual(self, physical_value: float) -> float:
        return physical_value + self.offset

    def compute_dynamic(self):
        """
        Update thrust and power consumption
        """
        self.thrust = - self.current_acc * self.mass
        self.power = (self.current_acc * self.mass + self.friction * self.direction) * self.current_speed

    def recompute_target(self):
        self.set_target(self._target_pos, self.target_speed)

    def get_settings_dict(self):
        return {
            "max_speed": self.max_speed,
            "max_acc": self.max_acc
        }

    def set_settings(self, in_dict: dict):
        self.max_speed = in_dict["max_speed"]
        self.max_acc = in_dict["max_acc"]
        self.recompute_target()

    def set_target(self, virtual_target_pos: float, target_speed: Optional[float] = None):
        """
        Compute the motion from the current virtual position to the target virtual position
        :param virtual_target_pos: virtual target position
        :param target_speed: the speed of the movement (if None max speed will be used)
        """
        if target_speed is None:
            target_speed = self.max_speed

        target_pos = self.virtual_to_physical(virtual_target_pos)

        target_speed = min(target_speed, self.max_speed)

        self.trip = abs(target_pos - self._current_pos)

        if self.trip:
            if target_pos >= self._current_pos:
                self.direction = 1
            else:
                self.direction = -1

            acc_time = target_speed / self.max_acc
            acc_len = (0.5 * self.max_acc * acc_time ** 2)

            if not math.isclose(self.trip, acc_len * 2) and self.trip < (
                    acc_len * 2):  # no space for acceleration, changing target_speed
                crit_trip = self.trip / 2
                crit_time = math.sqrt(2 * (crit_trip / self.max_acc))
                self.set_target(self.physical_to_virtual(target_pos), target_speed=self.max_acc * crit_time)
            else:
                const_len = self.trip - 2 * acc_len
                self._movement_start_pos = self._current_pos
                self.target_speed = target_speed
                self._target_pos = target_pos
                self.acc_time = acc_time
                self.acc_trip = acc_len
                self.dec_time = acc_time + const_len / target_speed
                self.dec_trip = const_len + acc_len
                self.movement_time = 2 * acc_time + const_len / target_speed
                self._movement_start_time = 0

    def run(self, time: float):
        """
        Main function that compute the new parameters for the simulation
        :param time: current time [s]
        """

        if not math.isclose(self._target_pos, self._current_pos):
            if not self._movement_start_time:
                self._movement_start_time = time
            current_moving_time = time - self._movement_start_time
            if current_moving_time < self.acc_time:
                self._current_pos = self._movement_start_pos + self.direction * 0.5 * self.max_acc * current_moving_time ** 2
                self.current_speed = self.direction * self.max_acc * current_moving_time
                self.current_acc = self.direction * self.max_acc
            elif self.acc_time <= current_moving_time < self.dec_time:
                self._current_pos = self._movement_start_pos + self.direction * (
                        self.acc_trip + self.target_speed * (current_moving_time - self.acc_time))
                self.current_speed = self.direction * self.target_speed
                self.current_acc = .0
            elif self.dec_time <= current_moving_time < self.movement_time:
                t = current_moving_time - self.dec_time
                self._current_pos = self._movement_start_pos + self.direction * (
                        self.dec_trip +
                        self.target_speed * t -
                        0.5 * self.max_acc * t ** 2)
                self.current_speed = self.direction * (self.target_speed - self.max_acc * t)
                self.current_acc = - self.direction * self.max_acc
            else:
                self._current_pos = self._target_pos
                self._movement_start_time = .0
                self.current_speed = .0
                self.current_acc = .0
        else:
            self._current_pos = self._target_pos
            self._movement_start_time = .0
            self.current_speed = .0
            self.current_acc = .0

        self.compute_dynamic()

    def is_moving(self) -> bool:
        return not math.isclose(self._target_pos, self._current_pos)


if __name__ == '__main__':
    # for testing purpose
    xa = SingleAxis()
    time_lim = 6.0
    time_delta = 0.01

    elapsed_time = 0

    xa.set_target(50)

    print("Time, pos, speed, acc, power, thrust")

    while elapsed_time < time_lim:
        xa.run(elapsed_time)
        print(
            f"{elapsed_time:.2f}, {xa._current_pos:.3f}, {xa.current_speed:.3f}, {xa.current_acc:.3f}, {xa.power:.3f}, {xa.thrust:.3f}")
        elapsed_time += time_delta

    xa.max_acc = 5
    xa.max_speed = 20
    xa.set_target(0, 20)

    while elapsed_time < time_lim + 10:
        xa.run(elapsed_time)
        print(
            f"{elapsed_time:.2f}, {xa._current_pos:.3f}, {xa.current_speed:.3f}, {xa.current_acc:.3f}, {xa.power:.3f}, {xa.thrust:.3f}")
        elapsed_time += time_delta

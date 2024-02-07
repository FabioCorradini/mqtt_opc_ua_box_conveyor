import random
from typing import Optional
from asyncua import Server, ua, uamethod
from asyncua.common.node import Node
import asyncio
from paho.mqtt import client as mqtt_client
import json
import struct


# constants
MQTT_ADDR = "127.0.0.1"
MQTT_PORT = 1883
OPC_UA_ENDPOINT =  "opc.tcp://0.0.0.0:4841/conveyor/"


class Box:
    N_WIDTH = 50
    N_DEPTH = 80
    N_HEIGHT = 100

    def __init__(self):
        self.width = random.gauss(Box.N_WIDTH, Box.N_WIDTH * 0.1)
        self.depth = random.gauss(Box.N_DEPTH, Box.N_DEPTH * 0.1)
        self.height = random.gauss(Box.N_HEIGHT, Box.N_HEIGHT * 0.1)
        self.serial = f"{random.randint(0, 16777215):06X}"  # FFFFFF
        self.position = 0
        self.marked = False
        self.size = [self.width, self.depth, self.height]
        self.measures = [.0, .0, .0]

    def to_json(self):
        return json.dumps({"serial": self.serial,
                           "measures": self.measures,
                           "accepted": self.marked})

    def to_bin(self):
        s = bytes()
        s += (self.serial.encode('utf-8'))
        s += struct.pack("fff", *self.measures)
        s += struct.pack('?', self.marked)
        return s


class Conveyor:
    measuring: Optional[Box]
    server: Optional[Server]
    boxes: list[Box]

    def __init__(self):
        self.cells = 20
        self.boxes = []
        self.measuring = None
        self.mes_pos = 14
        self.speed = 1.0
        self.temperature = random.uniform(15.0, 35.0)
        self.thresholds = [Box.N_WIDTH * 0.1, Box.N_DEPTH * 0.1, Box.N_HEIGHT * 0.1]
        self.ref_mes = [Box.N_WIDTH, Box.N_DEPTH, Box.N_HEIGHT]
        self.boxes_count = 0
        self.boxes_rejected = 0
        self.boxes_accepted = 0
        self.paused = False
        self.max_accepted_boxes = None

    def advance(self):
        if not self.paused:
            if self.max_accepted_boxes is not None:
                if self.boxes_accepted >= self.max_accepted_boxes:
                    self.paused = True
                    return

            self.measuring = None
            to_del = []
            for i, box in enumerate(self.boxes):
                box.position += 1
                if box.position == self.mes_pos:
                    self.measuring = box
                    self.measure()
                    self.boxes_count += 1
                    if box.marked:
                        self.boxes_accepted += 1
                    else:
                        self.boxes_rejected += 1

                if box.position >= self.cells:
                    to_del.append(i)

            for del_n in to_del:
                self.boxes.pop(del_n)

            creation = random.randint(0, 2)
            if creation == 0:
                self.boxes.append(Box())

    def measure(self):
        if self.measuring is not None:
            for i, size in enumerate(self.measuring.size):
                mes = size + random.gauss(0, self.speed * 0.2)  # speed error
                mes = mes * (1 + 0.05 * (self.temperature - 25))  # temp error
                self.measuring.measures[i] = mes
                self.measuring.marked = self.evaluate()

    def is_measuring(self):
        return self.measuring is not None

    def evaluate(self):
        for i, size in enumerate(self.measuring.size):
            if self.ref_mes[i] + self.thresholds[i] >= size >= self.ref_mes[i] - self.thresholds[i]:
                pass
            else:
                return False
        return True

    def get_counters_json(self):
        return json.dumps({"boxes": self.boxes_count,
                           "accepted": self.boxes_accepted,
                           "rejected": self.boxes_rejected})

    def get_counters_bin(self):
        return struct.pack("iii", self.boxes_count, self.boxes_accepted, self.boxes_rejected)

    def get_settings_json(self):
        tols = []
        for i, tol in enumerate(self.thresholds):
            tols.append({"id": i, "value": tol})
        return json.dumps({"speed": self.speed,
                           "temperature": self.temperature,
                           "tolerances": tols})

    def get_settings_bin(self):
        s = bytes()
        s += struct.pack('f', self.speed)
        s += struct.pack('f', self.temperature)
        s += struct.pack('fff', *self.thresholds)
        return s

    def set_settings_from_json(self, in_json: str):
        in_dict = json.loads(in_json)

        if "speed" in in_dict:
            self.speed = float(in_dict["speed"])

        if "temperature" in in_dict:
            self.temperature = float(in_dict["temperature"])

        if "tolerances" in in_dict:
            for vec in in_dict["tolerances"]:
                self.thresholds[vec["id"]] = float(vec["value"])

        if "pause" in in_dict:
            self.paused = bool(in_dict['pause'])

    def set_settings_from_bin(self, in_bytes: bytes):
        self.speed, self.temperature, self.thresholds[0], self.thresholds[1], self.thresholds[2] =\
            struct.unpack("fffff", in_bytes)


class Engine:
    width_node: Optional[Node]
    depth_node: Optional[Node]
    height_node: Optional[Node]
    box_id_node: Optional[Node]
    box_accepted_node: Optional[Node]
    box_count_node: Optional[Node]
    accepted_count_node: Optional[Node]
    rejected_count_node: Optional[Node]
    temp_node: Optional[Node]
    frequency_node: Optional[Node]
    w_tol_node: Optional[Node]
    d_tol_node: Optional[Node]
    h_tol_node: Optional[Node]

    def __init__(self, time_mult=1.0):
        self.conveyor = Conveyor()
        self.time_mult = time_mult

        self.time = .0

        self.tasks = []

        self.server = None
        self.width_node = None
        self.depth_node = None
        self.height_node = None
        self.mes_node = None
        self.box_id_node = None
        self.box_accepted_node = None
        self.box_count_node = None
        self.accepted_count_node = None
        self.rejected_count_node = None
        self.temp_node = None
        self.frequency_node = None
        self.w_tol_node = None
        self.d_tol_node = None
        self.h_tol_node = None

        self.reset_node = None
        self.disable_ac_box_node = None
        self.max_ac_box_node = None
        self.pause_node = None

        self.mqtt_base_topic = "box_conveyor_topic"
        self.mqtt_gauge_topic = f"{self.mqtt_base_topic}/gauge"
        self.mqtt_settings_topic = f"{self.mqtt_base_topic}/settings"
        self.mqtt_counters_topic = f"{self.mqtt_base_topic}/counters"
        self.mqtt_error_topic = f"{self.mqtt_base_topic}/error"

        self.mqtt_width_topic = f"{self.mqtt_gauge_topic}/width"
        self.mqtt_depth_topic = f"{self.mqtt_gauge_topic}/depth"
        self.mqtt_height_topic = f"{self.mqtt_gauge_topic}/height"
        self.mqtt_box_json_topic = f"{self.mqtt_gauge_topic}/json_box"
        self.mqtt_box_bin_topic = f"{self.mqtt_gauge_topic}/bin_box"

        self.mqtt_counter_json_topic = f"{self.mqtt_counters_topic}/json"
        self.mqtt_counter_bin_topic = f"{self.mqtt_counters_topic}/bin"

        self.mqtt_frequency_topic = f"{self.mqtt_settings_topic}/frequency"
        self.mqtt_settings_json = f"{self.mqtt_settings_topic}/json"
        self.mqtt_settings_bin = f"{self.mqtt_settings_topic}/bin"
        self.mqtt_settings_set_json = f"{self.mqtt_settings_topic}/set/json"
        self.mqtt_settings_set_bin = f"{self.mqtt_settings_topic}/set/bin"

        self.mqtt_client = self.mqtt_client_init()

    def mqtt_client_init(self):
        print("Connecting to mqtt broker...", end="\t")
        client = mqtt_client.Client("box_conveyor_sim")
        try:
            res = client.connect(MQTT_ADDR, MQTT_PORT)
        except ConnectionError as e:
            print(str(e))
            res = -1

        if res == 0:
            print("Ok")
        else:
            print("Error")
            return None

        client.publish(self.mqtt_width_topic, str(.0))
        client.publish(self.mqtt_depth_topic, str(.0))
        client.publish(self.mqtt_height_topic, str(.0))
        client.publish(self.mqtt_frequency_topic, str(self.conveyor.speed))
        client.publish(self.mqtt_error_topic, "")

        client.subscribe(self.mqtt_settings_set_json, 2)
        client.subscribe(self.mqtt_settings_set_bin, 2)
        client.on_message = self.on_mqtt_message
        # client.loop_start()

        return client

    def on_mqtt_message(self, client, userdata, msg):
        # print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        try:
            if msg.topic == self.mqtt_settings_set_json:
                self.conveyor.set_settings_from_json(msg.payload.decode())
            elif msg.topic == self.mqtt_settings_set_bin:
                self.conveyor.set_settings_from_bin(msg.payload)
            self.tasks.append(asyncio.create_task(self.update_opcua_nodes()))
        except Exception as e:
            self.write_mqtt_error(msg.topic, str(e))

    async def update_opcua_nodes(self):
        await self.frequency_node.set_value(self.conveyor.speed)
        await self.temp_node.set_value(self.conveyor.temperature)
        await self.w_tol_node.set_value(self.conveyor.thresholds[0])
        await self.d_tol_node.set_value(self.conveyor.thresholds[1])
        await self.h_tol_node.set_value(self.conveyor.thresholds[2])

    async def update_mqtt_client(self):
        if self.mqtt_client is not None:
            if self.conveyor.is_measuring():
                self.mqtt_client.publish(self.mqtt_width_topic, self.conveyor.measuring.measures[0])
                self.mqtt_client.publish(self.mqtt_depth_topic, self.conveyor.measuring.measures[1])
                self.mqtt_client.publish(self.mqtt_height_topic, self.conveyor.measuring.measures[2])
                self.mqtt_client.publish(self.mqtt_box_json_topic, self.conveyor.measuring.to_json())
                self.mqtt_client.publish(self.mqtt_box_bin_topic, self.conveyor.measuring.to_bin())

            self.mqtt_client.publish(self.mqtt_counter_json_topic, self.conveyor.get_counters_json())
            self.mqtt_client.publish(self.mqtt_counter_bin_topic, self.conveyor.get_counters_bin())

            self.mqtt_client.publish(self.mqtt_settings_json, self.conveyor.get_settings_json())
            self.mqtt_client.publish(self.mqtt_settings_bin, self.conveyor.get_settings_bin())

            await self.mqtt_client_loop()

    def write_mqtt_error(self, topic: str, message: str):
        if self.mqtt_client is not None:
            msg = json.dumps({"topic": topic, "message": message})
            self.mqtt_client.publish(self.mqtt_error_topic, msg)

    async def server_init(self):
        print("Starting opcua server...", end="\t")
        self.server = Server()
        await self.server.init()
        self.server.set_endpoint(OPC_UA_ENDPOINT)
        uri = "http://test_dummy_machine"
        idx = await self.server.register_namespace(uri)
        gauge = await self.server.nodes.objects.add_object(idx, "Gauge")
        self.width_node = await gauge.add_variable(idx, "width", .0)
        self.depth_node = await gauge.add_variable(idx, "depth", .0)
        self.height_node = await gauge.add_variable(idx, "height", .0)
        self.mes_node = await gauge.add_variable(idx, "measures", [.0, .0, .0])
        self.box_id_node = await gauge.add_variable(idx, "Box id", "")
        self.box_accepted_node = await gauge.add_variable(idx, "Box accepted", True)

        counter = await self.server.nodes.objects.add_object(idx, "Counters")
        self.box_count_node = await counter.add_variable(idx, "Boxes", 0)
        self.accepted_count_node = await counter.add_variable(idx, "Accepted", 0)
        self.rejected_count_node = await counter.add_variable(idx, "Rejected", 0)

        settings = await self.server.nodes.objects.add_object(idx, "Settings")
        self.temp_node = await settings.add_variable(idx, "Temperature", self.conveyor.temperature)
        self.frequency_node = await settings.add_variable(idx, "Speed", self.conveyor.speed)
        self.w_tol_node = await settings.add_variable(idx, "width tolerance ", self.conveyor.thresholds[0])
        self.d_tol_node = await settings.add_variable(idx, "depth tolerance", self.conveyor.thresholds[1])
        self.h_tol_node = await settings.add_variable(idx, "height tolerance", self.conveyor.thresholds[2])

        actions = await self.server.nodes.objects.add_object(idx, "Actions")
        self.reset_node = await actions.add_method(idx, "Reset counter", self.reset_counter)
        self.pause_node = await actions.add_method(idx, "Start-stop conveyor", self.pause, [], [ua.VariantType.Boolean])
        self.max_ac_box_node = await actions.add_method(idx, "Set max accepted boxes", self.set_max_accepted_boxes,
                                                        [ua.VariantType.Int64])
        self.disable_ac_box_node = await actions.add_method(idx, "Disable accepted boxes",
                                                            self.disable_max_accepted_boxes)

        await self.temp_node.set_writable()
        await self.frequency_node.set_writable()
        await self.w_tol_node.set_writable()
        await self.d_tol_node.set_writable()
        await self.h_tol_node.set_writable()

        print("ok")

    async def update_opc_server(self):
        if self.conveyor.is_measuring():
            await self.width_node.write_value(self.conveyor.measuring.measures[0])
            await self.depth_node.write_value(self.conveyor.measuring.measures[1])
            await self.height_node.write_value(self.conveyor.measuring.measures[2])
            await self.mes_node.write_value(self.conveyor.measuring.measures)

            await self.box_id_node.write_value(self.conveyor.measuring.serial)
            await self.box_accepted_node.write_value(self.conveyor.measuring.marked)

        await self.box_count_node.write_value(self.conveyor.boxes_count)
        await self.accepted_count_node.write_value(self.conveyor.boxes_accepted)
        await self.rejected_count_node.write_value(self.conveyor.boxes_rejected)

        self.conveyor.temperature = await self.temp_node.get_value()
        self.conveyor.speed = await self.frequency_node.get_value()
        self.conveyor.thresholds[0] = await self.w_tol_node.get_value()
        self.conveyor.thresholds[1] = await self.d_tol_node.get_value()
        self.conveyor.thresholds[2] = await self.h_tol_node.get_value()

    @uamethod
    def reset_counter(self, parent):
        self.conveyor.boxes_count = 0
        self.conveyor.boxes_accepted = 0
        self.conveyor.boxes_rejected = 0

    @uamethod
    def pause(self, parent):
        self.conveyor.paused = not self.conveyor.paused
        return self.conveyor.paused

    @uamethod
    def set_max_accepted_boxes(self, parent, max_accepted_boxes: int):
        self.conveyor.max_accepted_boxes = max_accepted_boxes

    @uamethod
    def disable_max_accepted_boxes(self, parent):
        self.conveyor.max_accepted_boxes = None

    def get_mes_info(self) -> str:
        if self.conveyor.is_measuring():
            box_info = self.conveyor.measuring.serial
            w = f"{self.conveyor.measuring.measures[0] :6.3f}"
            d = f"{self.conveyor.measuring.measures[1] :6.3f}"
            h = f"{self.conveyor.measuring.measures[2] :6.3f}"
            if self.conveyor.measuring.marked:
                res = "OK"
            else:
                res = "NO"
        else:
            box_info = "______"
            w = f"{.0 :6.3f}"
            d = f"{.0 :6.3f}"
            h = f"{.0 :6.3f}"
            res = "__"

        return f"serial: {box_info} w:{w} mm d:{d} mm h:{h} mm - result: {res}"

    def draw(self):
        s = ["="] * self.conveyor.cells
        s[self.conveyor.mes_pos] = "x"
        for box in self.conveyor.boxes:
            if box.position == self.conveyor.mes_pos:
                s[box.position] = "⛝"
            else:
                if box.marked:
                    s[box.position] = "■"
                else:
                    s[box.position] = "□"

        if self.conveyor.paused:
            status = "STOPPED"
        else:
            status = "RUNNING"

        print("\r{} T:{:.1f}°C S:{:.1f} box/s B:{:d} A:{:d} R:{:d} status: {} {} time: {:.1f} s".format("".join(s),
                                                                                                        self.conveyor.temperature,
                                                                                                        self.conveyor.speed,
                                                                                                        self.conveyor.boxes_count,
                                                                                                        self.conveyor.boxes_accepted,
                                                                                                        self.conveyor.boxes_rejected,
                                                                                                        status,
                                                                                                        self.get_mes_info(),
                                                                                                        self.time),
              end="")

    async def mqtt_client_loop(self):
        self.mqtt_client.loop()

    async def run(self):
        async with self.server:
            while True:
                self.conveyor.advance()
                self.draw()
                self.tasks.append(asyncio.create_task(self.update_opc_server()))
                self.tasks.append(asyncio.create_task(self.update_mqtt_client()))
                await asyncio.sleep(1 / (self.conveyor.speed * self.time_mult))
                for task in self.tasks:
                    await task
                self.tasks = []
                self.time += 1 / self.conveyor.speed



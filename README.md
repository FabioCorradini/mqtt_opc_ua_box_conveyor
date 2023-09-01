# Box conveyor

The program simulates the operation of a conveyor for little boxes with a station that measures the boxes and evaluates
their conformity to the standard (50.0x80.0x100.0) mm.

The boxes are transported from the belt to the measuring station, where their dimensions are evaluated and compliant boxes are marked.
At the end of the line, unmarked boxes are discarded.

This station has a minimal HUD that allows the basic information to be seen and is equipped with an OPC UA server and MQTT
connection through which monitoring, and control is possible.

GUI:

==============x===== T:18.0°C S:1.0 box/s B:0 A:0 R:0 status: RUNNING serial: ______ w: 0.000 mm d: 0.000 mm h: 0.000 mm - result: __ time: 0.0 s

In the GUI (displayed on a single line and consisting only of characters) basic information is displayed:

- a simplified representation of the line as viewed from above
- the temperature of the room
- the speed of the line
- the counter of the measured boxes
- the counter of accepted boxes
- the counter of the rejected boxes
- the status of the system
- the serial number of the box being measured
- the measured dimensions of the box in the measuring station
- the result of the measurement of the box currently in the station
- the time of the simulation

## MQTT communication

At startup, the system attempts to connect without authentication with a mqtt broker at address 127.0.0.1:1883
( editable by the variables MQTT_ADDR, MQTT_PORT). If it fails, mqtt communication is disabled.

Through mqtt broker both data collection and system control is possible.

### Data collection
The data is published in the following topics:
- **box_conveyor_topic/gauge/width**: the width of the last measured chunk.
- **box_conveyor_topic/gauge/depth**: the depth of the last measured piece.
- **box_conveyor_topic/gauge/height**: the height of the last machined piece.
- **box_conveyor_topic/gauge/json_box**: The data of the last piece parsed in json format
    example:
    ```json
    {
      "serial": "BBF0A5",
      "measures":[63.18760077308758, 77.66134495358746, 108.78107721175384],
      "accepted": false
    }
    ```
- **box_conveyor_topic/gauge/bin_box**: The data of the last piece parsed in binary format (encoded according to the table)
    
    | Field         | Position | Encoding       |
    |---------------|----------|----------------|
    | Serial number | 0        | string (utf-8) |
    | width         | 6        | float32        |
    | depht         | 10       | float32        |
    | height        | 14       | float32        |
    | passed        | 18       | bool           |

- **box_conveyor_topic/counters/json**: all counters in json format
   ```json
    {
      "boxes": 1783,
      "accepted": 589,
      "rejected": 1194
    }
    ```
- **box_conveyor_topic/counters/bin**: all The counters in binary format

    | Field          | Position | Encoding |
    |----------------|----------|----------|
    | Boxes count    | 0        | int32    |
    | Accepted count | 4        | int32    |
    | Rejected count | 8        | int32    |

- **box_conveyor_topic/settings/json**: topic used for only **displaying** all settings in json format:
    ```json
    {
      "speed": 1.0,
      "temperature": 26.45,
      "tolerances": 
      [
        {"id": 0, "value": 5.0},
        {"id": 1, "value": 8.0},
        {"id": 2, "value": 10.0}
      ]
    }
    ```

-- **box_conveyor_topic/settings/bin**: used for only displaying all settings in binary format:


| Field            | Position | Encoding |
|------------------|----------|----------|
| Speed            | 0        | float32) |
| Temperature      | 4        | float32  |
| Width tolerance  | 8        | float32  |
| Depth tolerance  | 12       | float32  |
| Height tolerance | 16       | float32  |

### Change settings

To change settings post on topic **box_conveyor_topic/settings/set/json** in json format according to template:

```json
    {
      "speed": 1.0,
      "temperature": 26.45,
      "tolerances": 
      [
        {"id": 0, "value": 5.0},
        {"id": 1, "value": 8.0},
        {"id": 2, "value": 10.0}
      ],
      "pause": false
    }
```

Alternatively post in binary format in the topic **box_conveyor_topic/settings/set/bin** according to this table:

| Field            | Position | Encoding |
|------------------|----------|----------|
| Speed            | 0        | float32) |
| Temperature      | 4        | float32  |
| Width tolerance  | 8        | float32  |
| Depth tolerance  | 12       | float32  |
| Height tolerance | 16       | float32  |

Any parsing error will be published on topic: **box_conveyor_topic/}/error**

## OPC UA communication

The program include an OPC UA server that works at endpoint: *opc.tcp://0.0.0.0:4841/conveyor/* (editable via OPC_UA_ENDPOINT variable)

Nodes on the **Counters** and **Gauge** objects are readable only and can be used for monitoring, node on the **Settings** node
instead are writable and can be used to monitor or change system settings.

In addition, the **Actions** object contains useful function that can be used perform tasks:

 -  **Set max accepted boxes**: input: int. Enables a function that pauses the conveyor after a certain number of boxes have been accepted (definable as input)
 -  **Disable accepted boxes**: Disable the function that pauses the conveyor after a certain number of boxes have been accepted
 -  **Reset counter**: Reset all the counters.
 -  **Start-stop conveyor**: output: bool. Toggle the pause/working status of the conveyor, return True if the conveyor is paused 



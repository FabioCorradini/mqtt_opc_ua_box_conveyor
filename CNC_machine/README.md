# CNC Machine

The program simulates the operation of a simple 3-axis CNC (a 3D printer).

The system currently supports the following G-Code commands, other commands are ignored:
- **G1**: linear motion
- **G92**: set offset
- **G28**. Home axes
- **M190**: set the print bed temperature and wait for it to be reached
- **M140**: set the print bed temperature and continue
- **M109**: set nozzle temperature and wait for it to be reached
- **M104**: set the nozzle temperature and continue
- 
The simulator is able to plan trajectories (albeit in a simplified way compared to a real CNC).

To run:

```shell
python -m CNC_machine.main
```

## Terminal UI

The simulation provides a basic terminal UI that can be enabled with the global variable DRAW_ON_TERMINAL

```shell
t:107.9 x:79.4/313.0 y:44.4/175.0 z:5.0/5.0 e:0.0/0.0 Nozzle:163.3/200.0 Plate:41.4/40.0 Status: WORKING - job3 - 10% - G1 X313 Y175 F600
```

The data displayed is:

- **simulation time [s]**
- **Axis current and target position [mm]**
- **Nozzle current ant target temperature [°C]**
- **Plate current ant target temperature [°C]**
- **Status of the machine**
- **G-code file being executed (if any)**
- **Percentage of completion of the G-code file (if any)**
- **G-code file being executed (if any)**


## OPC-UA

The simulator has an opc-ua server that exposes several nodes, some to monitor, some to change settings, 
and some to execute commands. The OPC-UA address can be changed with global variable OPC_UA_ENDPOINT

### General nodes:

- **Feedrate**: (writable) can be used as a multiplier for the printer speed
- **Power**: Overall power consumption [W]
- **Status**: 0: "IDLE", 1: "WORKING", 2: "PAUSED"

### Axis Nodes

Every axis generate the following nodes:

- **Current_acc**: current acceleration in [m/s^2]
- **Current_acc**: current displayed position [m]
- **Current_speed**: current speed in [m/s]
- **Power**: current power consumption [W]
- **Target_pos**: target position of the current movement [m]
- **Target_speed**: target speed of the current movement [m/s]
- **Settings/Max_Acc**: (writable) maxim acceleration of the axis [m/s^2]
- **Settings/Max_speed**: (writable) maxim speed of the axis [m/s]

### Heater nodes

Every heater generates the following nodes

- **Power**: current power consumption [W]
- **Target temperature**: target temperature of the heater [°C]
- **Temperature**: current temperature of the heater [°C]
- **Settings/Ki**: (writable) the integral gain of the controller
- **Settings/Kp**: (writable) the proportional gain of the controller
- **Settings/settle_time**: (writable) The time after which, if the system remains at temperature, the system is considered to be at temperature [s]
- **Settings/settle_windows**: The temperature window within which the temperature must remain for a settle time to be considered in temperature [°C]
- **Settings/wind_up**: (writable) Limit the integral component of the PI output [W]

### Action nodes

These nodes can be used to execute commands on the machine:

- **Execute g-code file**: INPUT: path to the gcode file (Localized text), OUTPUT: None
- **Execute g-code line**: INPUT: g-code line to be executed (Localized text), OUTPUT: None
- **Pause g-code file**: INPUT: None, OUTPUT: None
- **Resume g-code file**: INPUT: None, OUTPUT: None
- **Abort g-code file**: INPUT: None, OUTPUT: None

## REST API ENDPOINTS

The system has some edpoints that can be used for control, the server address and port can be controlled by the variables SEVER_APP_ADDR, SEVER_APP_PORT.
The documentation is generated automatically at address: "http://SEVER_APP_ADDR:SEVER_APP_PORT/docs"

- **POST** */control/execute_line*, **Parameters**: line (required, string, query), **Function**: execute the provided gcode-line
- **POST** */control/execute_file*, **Parameters**: file (required, string, query), **Function**: execute the provided gcode-file
- **POST** */control/pause_gcode*, **Function**: pause the current gcode execution
- **POST** */control/resume_gcode*, **Function**: resume the current gcode execution
- **POST** */control/abort_gcode*, **Function**: abort the current gcode execution






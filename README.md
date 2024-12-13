This repository collects some python packages that simulate the operation of industrial machinery controllable by remote
protocols. The simulations are mainly for educational purposes and are not intended to be accurate.

| Machine          | OPC-UA | mqtt | custom API | Modbus TCP | README                                | command                     |
|------------------|--------|------|------------|------------|---------------------------------------|-----------------------------|
| **box conveyor** | yes    | yes  | no         | no         | [README.md](./box_conveyor/README.md) | python -m box_conveyor.main |
| **CNC machine**  | yes    | no   | yes        | no         | [README.md](./CNC_machine/README.md)  | python -m CNC_machine.main  |
| **pool boiler**  | no     | no   | no         | yes        | [README.md](./pool_boiler/README.md)  | python -m pool_boiler.main  |

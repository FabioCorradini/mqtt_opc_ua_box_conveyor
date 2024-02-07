This repository collects some python packages that simulate the operation of industrial machinery controllable by remote protocols. The simulations are mainly for educational purposes and are not intended to be accurate.

| Machine          | OPC-UA | mqtt | custom API | README                                | command                     |
|------------------|--------|------|------------|---------------------------------------|-----------------------------|
| **box conveyor** | yes    | yes  | no         | [README.md](./box_conveyor/README.md) | python -m box_conveyor.main |
| **CNC machine**  | yes    | no   | yes        | [README.md](./CNC_machine/README.md)  | python -m CNC_machine.main  |

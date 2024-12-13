# Boiling pot

## Coils (R/W)

### IN_PUMP coil (ADDR: 0)

It checks the system inlet valve

### IN_PUMP coil (ADDR: 1)

It checks the system drain valve

## Discrete inputs (R)

### BOILING ALERT input (ADDR: 1000)

This alarm is triggered if there is boiling liquid in the pot

### FULL ALERT input (ADDR: 1001)

This alarm is triggered when the pot is full beyond the safety limit.
When the alarm is triggered, the inlet pump closes and cannot be activated until the alarm has ceased.

### BURNOUT ALERT input (ADDR: 1002)

This alarm is triggered when the pot temperature is beyond the safety limit.
When the alarm is triggered, the heater is shut down and cannot be activated until the alarm has ceased.

## Holding register (R/W)

### HEATER REGULATION (ADDR 4000)

This register allows the heater power to be adjusted in percent (accepts values from 0 to 100)

## Input register (R)

### WATER LEVEL (ADDR 3000)

The filling percentage of the pot compared to the safety limit

### POT TEMPERATURE (ADDR 3001)

Pot temperatures indicated in tenths of a degree starting from -20 °C ( 200 -> 0 °C)



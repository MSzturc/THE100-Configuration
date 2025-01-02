# THE100-Configruation

In this repository you find the configuration for all of T100 / T250 builds. The configuration is modular and it was inspired by Klippain and RatOS configuration.

It offers the following features:
- TEST_RESONANCES: Automatically determines the center of the print bed
- Adaptive Bed Mesh Support: This feature dynamically adjusts the bed mesh to the positions where printing actually occurs.
- Z_TILT with Twist Compensation & Nozzle Collision Z-Offset
- CG28: Home only of not already homed
- Z_TILT: only of not already calibrated
- M109/M190: Skip dwell time after temp reached
- HEATSOAK_BED: Wait for a defined time after heatbed reaches temp
- PRIME_LINE: Prime Line to clean Nozzle before print starts
- SCREW_ADJUST: Manually adjust screw tension
- Automatic Bed size calculation
- Automatic BedMesh size calculation
- Automatic Stepper Tuning support

# gcode-pre-retract-slowdown
A stringing reduction method for 3D printing

Find retraction points, and slow down print a bit before retraction occurs to reduce nozzle pressure.

Use with PrusaSlicer output with "Wipe while retracting" OFF, and a non-zero amount of retraction.

Usage:
* Put your gocde, named as `print.gcode`, in the directory
* Run `python3 slowdown.py`
* Output will be `processed.gcode`

![](https://github.com/giuliojiang/gcode-pre-retract-slowdown/raw/main/wiki/Screenshot%202023-04-16%20111051.jpg)

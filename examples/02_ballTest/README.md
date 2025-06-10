# Blender Ball Test

This example renders a short animation of a ball moving inside a dark cube and
immediately converts the rendered frames to IEBCS event data. Both rendering and
sensor simulation are performed within the same Blender script.

Run the script from Blender in background mode:

```bash
blender -b -P ball_test.py
```

An output directory will be created next to the script containing the generated
`ball_events.dat` file.

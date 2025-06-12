# Ball Example

This script generates a simple animation of a sphere moving from left to right
and converts the rendered frames to IEBCS event data using `DvsSensor`.  The
virtual camera is configured with a resolution of **1280x720** pixels.

Run the script with Blender in background mode:

```bash
blender -b -P generate.py
```

Output video and event files will be created in `./output_ball`.

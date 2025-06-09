# Blender Ball Example

This example demonstrates how to generate IEBCS event data from a simple Blender
animation. A black 1x1x1 m room is created and a small ball moves from
`(0, 0.5, -0.3)` to `(1, 0.5, -0.3)`. The camera is placed at `(0.5, 0.5, -1)`
looking at the centre of the room and a point light is positioned `0.3` m above
the camera.

1. **Render frames with Blender**

   ```bash
   blender -b -P 0_generate_frames.py
   ```

   PNG images will be stored in the `frames/` directory.

2. **Convert frames to events**

   Run the conversion script using Python:

   ```bash
   python 1_frames_to_events.py
   ```

   The output event file `ball_events.dat` will be written to the `outputs/`
   directory.

# Blender Ball Example

This example demonstrates how to generate IEBCS event data from a simple Blender
animation. A black 1x1x1 m room is created and a small ball moves from
`(0, 0.5, -0.3)` to `(1, 0.5, -0.3)`. The camera is placed at `(0.5, 0.5, -0.8)`
inside the cube, looking at the centre of the room and a point light is
positioned `0.3` m above the camera.

The script `0_generate_frames.py` allows changing the output FPS and the
ball's motion using a set of variables defined at the top of the file.  The
number of frames is automatically computed from the specified speed and the
distance the ball travels, so the animation duration remains the same when the
FPS is changed.

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

## Customising the animation

The parameters controlling the ball motion and the output FPS are defined at
the top of `0_generate_frames.py`:

```python
FPS = 15                     # Output frame rate
BALL_START = (0.0, 0.5, -0.3)  # Start position
BALL_END = (1.0, 0.5, -0.3)    # End position
BALL_SPEED = 0.5             # Speed in metres per second
```

Adjust these values to change the resolution, the path or the speed.  The script
calculates how many frames are required based on the chosen FPS and speed so the
ball appears for the same amount of real time regardless of the FPS value.

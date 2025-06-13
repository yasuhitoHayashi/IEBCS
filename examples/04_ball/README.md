# Ball Example

This script generates a simple animation of a sphere moving from left to right

Run the script with Blender in background mode (the `bpy` package alone may not expose all features used here):

```bash
blender -b -P generate.py
```

The script now renders two passes per frame: one with only the sphere and another
containing only its shadow. Event streams are generated separately for each
pass. Object events are saved to `ball_object.dat` and shadow events to
`ball_shadow.dat` in the `./output_ball` directory. A normal video with shadows
is also produced.


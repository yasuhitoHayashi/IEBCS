import bpy
import os
import math

# ----------------------------
# Configuration parameters
# ----------------------------

# Output frame rate (frames per second)
FPS = 15

# Output resolution
RESOLUTION_X = 1280
RESOLUTION_Y = 720

# Ball motion parameters
# Starting and ending positions in metres
BALL_START = (0.0, 0.5, -0.3)
BALL_END = (1.0, 0.5, -0.3)
# Constant ball speed in metres per second
BALL_SPEED = 0.5

# Configure scene
scene = bpy.context.scene
scene.frame_start = 1

# Duration of the ball motion (computed from speed and distance)
distance = math.sqrt(sum((e - s) ** 2 for s, e in zip(BALL_START, BALL_END)))
duration = distance / BALL_SPEED

# Total frames of the animation determined by duration and FPS
total_frames = int(round(duration * FPS))
scene.frame_end = scene.frame_start + total_frames - 1

scene.render.fps = FPS
scene.render.resolution_x = RESOLUTION_X
scene.render.resolution_y = RESOLUTION_Y
scene.render.image_settings.file_format = 'PNG'

# Remove default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create black cube walls (1m cube)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.5, 0.5, -0.5))
cube = bpy.context.object
mat = bpy.data.materials.new(name="Black")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
bsdf.inputs["Roughness"].default_value = 1
cube.data.materials.append(mat)
# Flip normals so the cube is visible from inside
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.normals_make_consistent(inside=True)
bpy.ops.object.mode_set(mode='OBJECT')

# Empty at the center for camera tracking
bpy.ops.object.empty_add(location=(0.5, 0.5, -0.5))
center = bpy.context.object

# Create sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=BALL_START)
sphere = bpy.context.object
sphere.keyframe_insert(data_path="location", frame=scene.frame_start)
sphere.location = BALL_END
sphere.keyframe_insert(data_path="location", frame=scene.frame_end)

# Add camera inside the cube
bpy.ops.object.camera_add(location=(0.5, 0.5, -0.8))
cam = bpy.context.object
scene.camera = cam
track = cam.constraints.new(type='TRACK_TO')
track.target = center
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# Light 0.3m above the camera inside the cube
bpy.ops.object.light_add(type='POINT', location=(0.5, 0.8, -0.8))
light = bpy.context.object
light.data.energy = 1000

# Directory for rendered frames
frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
os.makedirs(frames_dir, exist_ok=True)

# Render all frames
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(frames_dir, f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

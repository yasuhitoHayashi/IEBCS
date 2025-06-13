import bpy
import cv2
import os
import sys
from mathutils import Vector


def set_visibility(obj, *, camera=None, shadow=None):
    """Set object visibility, handling Blender versions without cycles."""
    if camera is not None:
        if hasattr(obj, "cycles_visibility"):
            try:
                obj.cycles_visibility.camera = camera
            except AttributeError:
                pass
        if hasattr(obj, "visible_camera"):
            try:
                obj.visible_camera = camera
            except AttributeError:
                pass
        if not (hasattr(obj, "cycles_visibility") or hasattr(obj, "visible_camera")):
            obj.hide_render = not camera
    if shadow is not None:
        if hasattr(obj, "cycles_visibility"):
            try:
                obj.cycles_visibility.shadow = shadow
            except AttributeError:
                pass
        if hasattr(obj, "visible_shadow"):
            try:
                obj.visible_shadow = shadow
            except AttributeError:
                pass

# Add module path
sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_buffer import EventBuffer

# Output directory
base_path = "./output_ball/"
os.makedirs(base_path, exist_ok=True)

# Sensor and animation parameters
sensor_width = 1280
sensor_height = 720
frames = 120

# Ball movement from left to right
start_pos = Vector((-5.0, 0.0, 0.0))
end_pos   = Vector((5.0, 0.0, 0.0))
delta = (end_pos - start_pos) / (frames - 1)

dat_path_obj = os.path.join(base_path, "ball_object.dat")
dat_path_shadow = os.path.join(base_path, "ball_shadow.dat")
tmp_obj_path = os.path.join(base_path, "tmp_object.png")
tmp_shadow_path = os.path.join(base_path, "tmp_shadow.png")
video_path = os.path.join(base_path, "ball.avi")

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=start_pos)
ball = bpy.context.active_object
ball.name = "Ball"
bpy.ops.object.shade_smooth()

# Camera setup
bpy.ops.object.camera_add(location=(0, 0, -10))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 18
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
empty = bpy.context.active_object
empty.name = "CameraTarget"
track = cam.constraints.new(type='TRACK_TO')
track.target = empty
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'
bpy.context.scene.camera = cam

# Background plane
bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 5))
backdrop = bpy.context.active_object
backdrop.name = "BackDrop"

# Light above camera
light_data = bpy.data.lights.new(name="MainLight", type='POINT')
light_data.energy = 2000
light_obj = bpy.data.objects.new(name="MainLight", object_data=light_data)
bpy.context.collection.objects.link(light_obj)
light_obj.location = cam.location + Vector((0, 0, 2))

# Render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = sensor_width
scene.render.resolution_y = sensor_height
scene.render.image_settings.file_format = 'PNG'
scene.frame_start = 0
scene.frame_end = frames - 1
scene.cycles.device = 'GPU'

# Initialise sensor
sensor_obj = DvsSensor("ObjectSensor")
sensor_obj.initCamera(sensor_width, sensor_height,
                      lat=100, jit=100, ref=100, tau=300,
                      th_pos=0.15, th_neg=0.15, th_noise=0.05,
                      bgnp=0.0001, bgnn=0.0001)

sensor_shadow = DvsSensor("ShadowSensor")
sensor_shadow.initCamera(sensor_width, sensor_height,
                         lat=100, jit=100, ref=100, tau=300,
                         th_pos=0.15, th_neg=0.15, th_noise=0.05,
                         bgnp=0.0001, bgnn=0.0001)

buffer_obj = EventBuffer(0)
buffer_shadow = EventBuffer(0)

# Animation loop
for frame in range(frames):
    scene.frame_set(frame)
    ball.location = start_pos + delta * frame
    ball.keyframe_insert(data_path="location")

    # ----------------------
    # Object-only rendering
    # ----------------------
    set_visibility(ball, camera=True, shadow=False)
    backdrop.cycles.is_shadow_catcher = False
    scene.render.film_transparent = False
    scene.render.filepath = tmp_obj_path
    bpy.ops.render.render(write_still=True)
    color = cv2.imread(tmp_obj_path)
    if color is None:
        raise RuntimeError(f"Failed to load rendered image: {tmp_obj_path}")
    img_obj = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(float) / 255.0 * 1e4

    if frame == 0:
        sensor_obj.init_image(img_obj)
    else:
        events = sensor_obj.update(img_obj, 1000)
        buffer_obj.increase_ev(events)

    # ----------------------
    # Shadow-only rendering
    # ----------------------
    set_visibility(ball, camera=False, shadow=True)
    backdrop.cycles.is_shadow_catcher = True
    scene.render.film_transparent = True
    scene.render.filepath = tmp_shadow_path
    bpy.ops.render.render(write_still=True)
    color = cv2.imread(tmp_shadow_path)
    if color is None:
        raise RuntimeError(f"Failed to load rendered image: {tmp_shadow_path}")
    img_shadow = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(float) / 255.0 * 1e4

    if frame == 0:
        sensor_shadow.init_image(img_shadow)
    else:
        events = sensor_shadow.update(img_shadow, 1000)
        buffer_shadow.increase_ev(events)

# Save events
if buffer_obj.i > 0:
    buffer_obj.write(dat_path_obj)
    print(f"Generated object event data: {dat_path_obj}")
else:
    print("No object events generated.")

if buffer_shadow.i > 0:
    buffer_shadow.write(dat_path_shadow)
    print(f"Generated shadow event data: {dat_path_shadow}")
else:
    print("No shadow events generated.")

# Output video
set_visibility(ball, camera=True, shadow=True)
backdrop.cycles.is_shadow_catcher = False
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'AVI_JPEG'
scene.render.fps = 60
scene.render.filepath = video_path
bpy.ops.render.render(animation=True)
print(f"Generated video: {video_path}")

for p in (tmp_obj_path, tmp_shadow_path):
    if os.path.exists(p):
        os.remove(p)

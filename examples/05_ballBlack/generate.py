import bpy
import cv2
import math
import os
import sys
from mathutils import Vector

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

video_path = os.path.join(base_path, "ball_.avi")
dat_path = os.path.join(base_path, "ball.dat")
tmp_image_path = os.path.join(base_path, "tmp_ball.png")

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=start_pos)
ball = bpy.context.active_object
ball.name = "Ball"
bpy.ops.object.shade_smooth()

# ---------------------------------
#  Ball を黒くするマテリアル設定
# ---------------------------------
black_mat = bpy.data.materials.new(name="BlackMat")
black_mat.use_nodes = True
bsdf = black_mat.node_tree.nodes["Principled BSDF"]

# 完全な黒 + ハイライトが出ないように
bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
bsdf.inputs["Specular"].default_value   = 0.0  # 鏡面反射ゼロ
bsdf.inputs["Roughness"].default_value  = 0.5  # お好みで

# マテリアルをボールに割り当て
if ball.data.materials:
    ball.data.materials[0] = black_mat
else:
    ball.data.materials.append(black_mat)

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
light_obj.location = cam.location + Vector((0, 1, 2))

# Render settings
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = sensor_width
scene.render.resolution_y = sensor_height
scene.render.image_settings.file_format = 'PNG'
scene.frame_start = 0
scene.frame_end = frames - 1
scene.cycles.device = 'GPU'

# Initialise sensor
sensor = DvsSensor("BallSensor")
sensor.initCamera(sensor_width, sensor_height,
                  lat=100, jit=100, ref=100, tau=300,
                  th_pos=0.15, th_neg=0.15, th_noise=0.05,
                  bgnp=0.0001, bgnn=0.0001)

buffer = EventBuffer(0)

# Animation loop
for frame in range(frames):
    scene.frame_set(frame)
    ball.location = start_pos + delta * frame
    ball.keyframe_insert(data_path="location")
    scene.render.filepath = tmp_image_path
    bpy.ops.render.render(write_still=True)
    color = cv2.imread(tmp_image_path)
    if color is None:
        raise RuntimeError(f"Failed to load rendered image: {tmp_image_path}")
    img = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(float) / 255.0 * 1e4

    if frame == 0:
        sensor.init_image(img)
    else:
        events = sensor.update(img, 10000)
        buffer.increase_ev(events)

# Save events
if buffer.i > 0:
    buffer.write(dat_path)
    print(f"Generated event data: {dat_path}")
else:
    print("No events generated.")

# Output video
scene.render.image_settings.file_format = 'AVI_JPEG'
scene.render.fps = 60
scene.render.filepath = video_path
bpy.ops.render.render(animation=True)
print(f"Generated video: {video_path}")

if os.path.exists(tmp_image_path):
    os.remove(tmp_image_path)

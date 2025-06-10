import bpy
import cv2
import numpy as np
import os
import sys

# Access IEBCS modules
sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_buffer import EventBuffer

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TMP_IMAGE = os.path.join(OUTPUT_DIR, "tmp.png")
EVENT_FILE = os.path.join(OUTPUT_DIR, "ball_events.dat")
VIDEO_FILE = os.path.join(OUTPUT_DIR, "ball_video.avi")

# Sensor/image parameters
WIDTH = 640
HEIGHT = 480
FRAMES = 30
FPS = 30

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAMES
scene.render.fps = FPS
scene.render.resolution_x = WIDTH
scene.render.resolution_y = HEIGHT
scene.render.image_settings.file_format = 'PNG'

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Black cube room
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.5, 0.5, -0.5))
room = bpy.context.object
mat = bpy.data.materials.new(name="Black")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
bsdf.inputs["Roughness"].default_value = 1
room.data.materials.append(mat)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.normals_make_consistent(inside=True)
bpy.ops.object.mode_set(mode='OBJECT')

# Empty for camera tracking
bpy.ops.object.empty_add(location=(0.5, 0.5, -0.5))
center = bpy.context.object

# Moving ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0.5, -0.3))
ball = bpy.context.object
ball.keyframe_insert(data_path="location", frame=1)
ball.location = (1, 0.5, -0.3)
ball.keyframe_insert(data_path="location", frame=FRAMES)

# Camera inside cube
bpy.ops.object.camera_add(location=(0.5, 0.5, -0.8))
cam = bpy.context.object
track = cam.constraints.new(type='TRACK_TO')
track.target = center
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'
scene.camera = cam

# Light above camera
bpy.ops.object.light_add(type='POINT', location=(0.5, 0.8, -0.8))
light = bpy.context.object
light.data.energy = 1000

# Initialise DVS sensor
sensor = DvsSensor("BallSensor")
sensor.initCamera(WIDTH, HEIGHT, lat=100, jit=10, ref=100, tau=40,
                   th_pos=0.4, th_neg=0.4, th_noise=0.01, bgnp=0.1, bgnn=0.01)
sensor.init_bgn_hist("../../data/noise_pos_161lux.npy", "../../data/noise_neg_161lux.npy")

buffer = EventBuffer(1)
dt = int(1e6 / FPS)
fourcc = cv2.VideoWriter_fourcc(*"MJPG")
video = cv2.VideoWriter(VIDEO_FILE, fourcc, FPS, (WIDTH, HEIGHT))

for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    scene.render.filepath = TMP_IMAGE
    bpy.ops.render.render(write_still=True)

    color = cv2.imread(TMP_IMAGE)
    if color is None:
        raise RuntimeError(f"Failed to load rendered frame {frame}")
    video.write(color)
    img = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0 * 1e4

    if frame == scene.frame_start:
        sensor.init_image(img)
    else:
        events = sensor.update(img, dt)
        buffer.increase_ev(events)

# Finalize video file
video.release()

# Clean temporary frame
if os.path.exists(TMP_IMAGE):
    os.remove(TMP_IMAGE)

buffer.write(EVENT_FILE, width=WIDTH, height=HEIGHT)
print(f"Generated event file: {EVENT_FILE}")
print(f"Generated video: {VIDEO_FILE}")

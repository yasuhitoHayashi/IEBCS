"""Generate event data from rendered frames using IEBCS."""
import os
import cv2
import numpy as np
import sys

sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_buffer import EventBuffer

FRAME_DIR = "frames"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

frame_files = sorted(
    [os.path.join(FRAME_DIR, f) for f in os.listdir(FRAME_DIR) if f.endswith(".png")]
)
if not frame_files:
    raise RuntimeError("No frames found. Run 0_generate_frames.py in Blender first.")

# Read first frame to initialise the sensor
im = cv2.imread(frame_files[0], cv2.IMREAD_GRAYSCALE)
height, width = im.shape

th_pos = 0.4
th_neg = 0.4
th_noise = 0.01
lat = 100
tau = 40
jit = 10
bgnp = 0.1
bgnn = 0.01
ref = 100

sensor = DvsSensor("BallSensor")
sensor.initCamera(width, height, lat=lat, jit=jit, ref=ref, tau=tau,
                   th_pos=th_pos, th_neg=th_neg, th_noise=th_noise,
                   bgnp=bgnp, bgnn=bgnn)
sensor.init_bgn_hist("../../data/noise_pos_161lux.npy", "../../data/noise_neg_161lux.npy")

sensor.init_image(im.astype(np.float32) / 255.0 * 1e4)

dt = int(1e6 / 30)  # microseconds per frame at 30 fps
buffer = EventBuffer(1)

for f in frame_files[1:]:
    im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    im = im.astype(np.float32) / 255.0 * 1e4
    events = sensor.update(im, dt)
    buffer.increase_ev(events)

buffer.write(os.path.join(OUTPUT_DIR, "ball_events.dat"), width=width, height=height)

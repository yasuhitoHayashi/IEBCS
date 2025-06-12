"""Generate event data from rendered frames using IEBCS."""
import os
import cv2
import numpy as np
import sys

sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_display import EventDisplay
from event_buffer import EventBuffer
from arbiter import SynchronousArbiter, BottleNeckArbiter, RowArbiter

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

th_pos = 0.01        # ON threshold = 50% (ln(1.5) = 0.4)
th_neg = 0.01       # OFF threshold = 50%
th_noise= 0.01      # standard deviation of threshold noise
lat = 100           # latency in us
tau = 40            # front-end time constant at 1 klux in us
jit = 10            # temporal jitter standard deviation in us
bgnp = 0.1          # ON event noise rate in events / pixel / s
bgnn = 0.01         # OFF event noise rate in events / pixel / s
ref = 100           # refractory period in us
dt = 1           # time between frames in us
time = 0


sensor = DvsSensor("BallSensor")
sensor.initCamera(width, height, lat=lat, jit=jit, ref=ref, tau=tau,
                   th_pos=th_pos, th_neg=th_neg, th_noise=th_noise,
                   bgnp=bgnp, bgnn=bgnn)
sensor.init_bgn_hist("../../data/noise_pos_161lux.npy", "../../data/noise_neg_161lux.npy")

sensor.init_image(im.astype(np.float32) / 255.0 * 1e4)

dt = 1e6 / 120  # microseconds per frame at 30 fps
buffer = EventBuffer(1)
ea = SynchronousArbiter(0.1, time, im.shape[0])  # DVS346-like arbiter

render_timesurface = 1

ed = EventDisplay("Events", 
                  1280, 
                  720, 
                  dt, 
                  render_timesurface)

for f in frame_files[1:]:
    im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    im = im.astype(np.float32) / 255.0 * 1e4
    events = sensor.update(im, dt)
    ed.update(events, dt)
    buffer.increase_ev(events)

buffer.write(os.path.join(OUTPUT_DIR, "ball_events.dat"))

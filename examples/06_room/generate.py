# ============================================================
# 3 m × 3 m × 2 m の部屋で「斜め上を見上げる」EVSシミュレーション
#   • カメラ  : (1 m, 1 m, 1 m)
#   • 注視点  : (1.5 m, 1.5 m, 1.8 m)
#   • ボール  : 半径 0.25 m、水平面で半径 0.8 m の円軌道
#   • 1 周    : 240 フレーム（60 fps）
#   • DvsSensor / EventBuffer でイベント生成
#   • 出力    : ./output_ball/ball.avi  と  ball.dat
# ============================================================

import bpy
import cv2
import math
import os
import sys
from mathutils import Vector

# ------------------------------------------------------------
# 0. 依存モジュールパス追加（dvs_sensor.py / event_buffer.py）
# ------------------------------------------------------------
sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_buffer import EventBuffer

# ------------------------------------------------------------
# 1. パラメータ
# ------------------------------------------------------------
ROOM_X, ROOM_Y, ROOM_Z = 3.0, 3.0, 2.0        # 部屋サイズ (m)
CAM_POS                = Vector((1, 1, 1))    # カメラ位置
CIRCLE_CENTER          = Vector((1.5, 1.5, 1.8))
CIRCLE_RADIUS          = 0.8                  # ボール軌道半径
BALL_RADIUS            = 0.03                 # ボールサイズ
TOTAL_FRAMES           = 240                  # 1 周
FPS                    = 60

sensor_width, sensor_height = 1280, 720       # DVS & Render 解像度

base_path = "./output_ball/"
os.makedirs(base_path, exist_ok=True)
video_path      = os.path.join(base_path, "ball.avi")
dat_path        = os.path.join(base_path, "ball.dat")
tmp_image_path  = os.path.join(base_path, "tmp_ball.png")

# ------------------------------------------------------------
# 2. シーン初期化
# ------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ------------------------------------------------------------
# 3. 部屋（6 面の Plane）
# ------------------------------------------------------------
room_mat = bpy.data.materials.new(name="RoomMat")
room_mat.use_nodes = True                                  # ← ノードを有効化
bsdf = room_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1)  # 明るいグレー
bsdf.inputs["Specular"].default_value   = 0.0                 # ハイライト無し
bsdf.inputs["Roughness"].default_value  = 1.0                 # 拡散反射のみ

def add_wall(size_x, size_y, loc, rot=(0, 0, 0), name="Wall"):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    wall = bpy.context.active_object
    wall.scale = (size_x * 0.5, size_y * 0.5, 1)
    wall.data.materials.clear()               # 念のため既存をクリア
    wall.data.materials.append(room_mat)      # ← ６面すべて同じマテリアル
    wall.name = name
# 床・天井
add_wall(ROOM_X, ROOM_Y, (ROOM_X/2, ROOM_Y/2, 0.0),            (0, 0, 0),          "Floor")
add_wall(ROOM_X, ROOM_Y, (ROOM_X/2, ROOM_Y/2, ROOM_Z),         (math.pi, 0, 0),    "Ceiling")
# 壁 4 面
add_wall(ROOM_X, ROOM_Z, (ROOM_X/2, ROOM_Y,   ROOM_Z/2),       (math.pi/2, 0, 0),  "Wall_back")
add_wall(ROOM_X, ROOM_Z, (ROOM_X/2, 0.0,      ROOM_Z/2),       (-math.pi/2, 0, 0), "Wall_front")
add_wall(ROOM_Y, ROOM_Z, (0.0,      ROOM_Y/2, ROOM_Z/2),       (0, math.pi/2, 0),  "Wall_left")
add_wall(ROOM_Y, ROOM_Z, (ROOM_X,   ROOM_Y/2, ROOM_Z/2),       (0,-math.pi/2, 0),  "Wall_right")

# ------------------------------------------------------------
# 4. 黒いボール
# ------------------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=BALL_RADIUS,
                                     location=CIRCLE_CENTER + Vector((CIRCLE_RADIUS, 0, 0)))
ball = bpy.context.active_object
ball.name = "Ball"
bpy.ops.object.shade_smooth()

black_mat = bpy.data.materials.new(name="BlackMat")
black_mat.use_nodes = True
bsdf = black_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0, 0, 0, 0.5)
bsdf.inputs["Specular"].default_value   = 0
bsdf.inputs["Roughness"].default_value  = 0.5
ball.data.materials.append(black_mat)

# ------------------------------------------------------------
# 5. カメラ & ライト
# ------------------------------------------------------------
bpy.ops.object.camera_add(location=CAM_POS)
cam = bpy.context.active_object
cam.data.lens = 18
bpy.ops.object.empty_add(type='PLAIN_AXES', location=CIRCLE_CENTER)
target = bpy.context.active_object
track  = cam.constraints.new(type='TRACK_TO')
track.target = target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis    = 'UP_Y'
bpy.context.scene.camera = cam

light_data = bpy.data.lights.new(name="MainLight", type='POINT')
light_data.energy = 3000
light_obj = bpy.data.objects.new(name="MainLight", object_data=light_data)
light_obj.location = cam.location + Vector((0, 0, 0.5))
bpy.context.collection.objects.link(light_obj)

# ------------------------------------------------------------
# 6. レンダリング設定
# ------------------------------------------------------------
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = sensor_width
scene.render.resolution_y = sensor_height
scene.render.fps          = FPS
scene.render.image_settings.file_format = 'PNG'
scene.frame_start = 0
scene.frame_end   = TOTAL_FRAMES - 1
if hasattr(scene, "cycles"):
    scene.cycles.device = 'GPU'

# ------------------------------------------------------------
# 7. DVS センサー初期化
# ------------------------------------------------------------
sensor = DvsSensor("BallSensor")
sensor.initCamera(sensor_width, sensor_height,
                  lat=100, jit=100, ref=100, tau=300,
                  th_pos=0.15, th_neg=0.15, th_noise=0.05,
                  bgnp=0.0001, bgnn=0.0001)
buffer = EventBuffer(0)

# ------------------------------------------------------------
# 8. アニメーション & イベント生成
# ------------------------------------------------------------
omega = 2 * math.pi / TOTAL_FRAMES

for frame in range(TOTAL_FRAMES):
    scene.frame_set(frame)
    angle = omega * frame
    ball.location = CIRCLE_CENTER + Vector((CIRCLE_RADIUS * math.cos(angle),
                                            CIRCLE_RADIUS * math.sin(angle),
                                            0))
    ball.keyframe_insert(data_path="location")

    # --- レンダリング（静止画）
    scene.render.filepath = tmp_image_path
    bpy.ops.render.render(write_still=True)

    # --- 画像を DVS に渡す
    color = cv2.imread(tmp_image_path)
    if color is None:
        raise RuntimeError("Failed to load rendered frame.")
    gray_img = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(float) / 255.0 * 1e4

    if frame == 0:
        sensor.init_image(gray_img)
    else:
        events = sensor.update(gray_img, 10000)
        buffer.increase_ev(events)

# ------------------------------------------------------------
# 9. イベント保存
# ------------------------------------------------------------
if buffer.i > 0:
    buffer.write(dat_path)
    print("Generated event data:", dat_path)
else:
    print("No events generated.")

# ------------------------------------------------------------
# 10. 動画書き出し
# ------------------------------------------------------------
scene.render.image_settings.file_format = 'AVI_JPEG'
scene.render.filepath = video_path
bpy.ops.render.render(animation=True)
print("Generated video:", video_path)

# 一時 PNG 削除
if os.path.exists(tmp_image_path):
    os.remove(tmp_image_path)
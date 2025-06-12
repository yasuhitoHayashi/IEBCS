import bpy
import cv2
import math
import os
import sys
from mathutils import Vector

# モジュールのパスを追加（オリジナルコードと同じディレクトリ構成の場合）
sys.path.append("../../src")
from dvs_sensor import DvsSensor
from event_buffer import EventBuffer

# ---------------------------
# 透明性付きマテリアル作成用関数
# ---------------------------
def create_transparent_material(transparency):
    """
    与えられた透明度 (0:不透明, 1:完全透明) に応じたマテリアルを生成する。
    Diffuse と Transparent のシェーダーを MixShader で混合する。
    """
    mat = bpy.data.materials.new(name=f"MarineSnowMat_trans{int(transparency*100)}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # 既存のノードをすべて削除
    for node in list(nodes):
        nodes.remove(node)

    # 必要なノードを作成
    output      = nodes.new(type='ShaderNodeOutputMaterial')
    mix_shader  = nodes.new(type='ShaderNodeMixShader')
    diffuse     = nodes.new(type='ShaderNodeBsdfDiffuse')
    transparent = nodes.new(type='ShaderNodeBsdfTransparent')
    
    # MixShader の Factor に透明度を設定（0:完全Diffuse, 1:完全Transparent）
    mix_shader.inputs['Fac'].default_value = transparency

    # ノード接続（Diffuse を入力1、Transparent を入力2）
    links.new(diffuse.outputs[0], mix_shader.inputs[1])
    links.new(transparent.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], output.inputs['Surface'])
    
    return mat

# ---------------------------
# 各種パラメータ設定
# ---------------------------
base_path = "./output_marine_snow/"
os.makedirs(base_path, exist_ok=True)

sensor_width  = 200
sensor_height = 720
frames        = 150

# オブジェクトの移動設定（Y軸方向に start_pos → end_pos へ移動）
start_pos = Vector((0.0,  10.0, 0.0))
end_pos   = Vector((0.0, -10.0, 0.0))
delta     = (end_pos - start_pos) / (frames - 1)

# 透明性の値リスト（0:不透明, 0.3:やや透, 0.6:もっと透）
transparency_list = [0.0, 0.3, 0.6]

# ---------------------------
# 透明性ごとにループ処理してシミュレーション実行
# ---------------------------
for transparency in transparency_list:
    # 出力ファイル名
    video_path    = os.path.join(base_path, f"marine_snow_trans{int(transparency*100)}.avi")
    dat_path      = os.path.join(base_path, f"marine_snow_trans{int(transparency*100)}.dat")
    tmp_image_path = os.path.join(base_path, f"tmp_render_trans{int(transparency*100)}.png")
    
    # シーン初期化（全オブジェクト削除）
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # ----------------------------------------
    # Marine Snow (球体) の生成
    # ----------------------------------------
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=start_pos)
    obj = bpy.context.active_object
    obj.name = "MarineSnow"
    
    # Subsurf + Displace + スムーズシェーディング
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = subsurf.render_levels = 3
    disp_mod = obj.modifiers.new(name="Displace", type='DISPLACE')
    noise_tex = bpy.data.textures.new("NoiseTex", type='CLOUDS')
    disp_mod.texture = noise_tex
    disp_mod.strength = 0.3
    bpy.ops.object.shade_smooth()
    
    # 透明性マテリアル適用
    mat = create_transparent_material(transparency)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    # ----------------------------------------
    # カメラの配置（横から撮影・常に球を注視）
    # ----------------------------------------
    bpy.ops.object.camera_add(location=(0, 0, -10))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 18  # 広角レンズ
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 5))
    empty = bpy.context.active_object
    empty.name = "CameraTarget"
    track = cam.constraints.new(type='TRACK_TO')
    track.target = empty
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis    = 'UP_Y'
    bpy.context.scene.camera = cam
    
    # ----------------------------------------
    # 背景用プレーン (影を受けるスクリーン)
    # ----------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 1))
    backdrop = bpy.context.active_object
    backdrop.name = "BackDrop"
    mat_plane = bpy.data.materials.new(name="BackDropMat")
    mat_plane.use_nodes = True
    nodes = mat_plane.node_tree.nodes
    # Principled BSDF の Base Color を白に設定
    if "Principled BSDF" in nodes:
        nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
    backdrop.data.materials.append(mat_plane)
    
    # ----------------------------------------
    # メインライト (カメラの少し上に配置)
    # ----------------------------------------
    light_data = bpy.data.lights.new(name="MainLight", type='POINT')
    light_data.energy = 2000
    light_data.shadow_soft_size = 0.5
    light_data.use_shadow = True
    light_obj = bpy.data.objects.new(name="MainLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = cam.location + Vector((0, 0, 2))
    
    # ----------------------------------------
    # レンダリング & DVS センサシミュレーション 初期化
    # ----------------------------------------
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = sensor_width
    scene.render.resolution_y = sensor_height
    scene.render.image_settings.file_format = 'PNG'
    scene.frame_start = 0
    scene.frame_end   = frames - 1
    
    dvs = DvsSensor("MarineSnowSensor")
    dvs.initCamera(sensor_width, sensor_height,
                   lat=100, jit=100, ref=100, tau=300,
                   th_pos=0.15, th_neg=0.15, th_noise=0.05,
                   bgnp=0.0001, bgnn=0.0001)

    ev = EventBuffer(0)
    
    # ----------------------------------------
    # アニメーション＆レンダリングループ
    # ----------------------------------------
    for frame in range(frames):
        scene.frame_set(frame)
        
        # 位置・回転更新
        obj.location = start_pos + delta * frame
        obj.rotation_euler.y = math.radians(2 * frame)
        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        
        # レンダリング→画像読み込み→DVS入力
        scene.render.filepath = tmp_image_path
        bpy.ops.render.render(write_still=True)
        color = cv2.imread(tmp_image_path)
        if color is None:
            raise RuntimeError(f"Failed to load rendered image: {tmp_image_path}")
        img = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY).astype(float) / 255.0 * 1e4

        if frame == 0:
            dvs.init_image(img)
        else:
            events = dvs.update(img, 1000)
            ev.increase_ev(events)
    
    # イベントデータ書き出し
    if ev.i > 0:
        ev.write(dat_path)
        print(f"Generated event data: {dat_path}")
    else:
        print("No events generated.")
    
    # ----------------------------------------
    # 動画レンダリング (AVI_JPEG形式) & 一時ファイル削除
    # ----------------------------------------
    scene.render.image_settings.file_format = 'AVI_JPEG'
    scene.render.fps = 60
    scene.render.filepath = video_path
    bpy.ops.render.render(animation=True)
    print(f"Generated video: {video_path}")
    
    if os.path.exists(tmp_image_path):
        os.remove(tmp_image_path)
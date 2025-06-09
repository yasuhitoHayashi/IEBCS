import bpy
import os

# Configure scene
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 30
scene.render.fps = 30
scene.render.resolution_x = 640
scene.render.resolution_y = 480
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
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0.5, -0.3))
sphere = bpy.context.object
sphere.keyframe_insert(data_path="location", frame=1)
sphere.location = (1, 0.5, -0.3)
sphere.keyframe_insert(data_path="location", frame=30)

# Add camera
bpy.ops.object.camera_add(location=(0.5, 0.5, -1))
cam = bpy.context.object
track = cam.constraints.new(type='TRACK_TO')
track.target = center
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# Light 0.3m above the camera
bpy.ops.object.light_add(type='POINT', location=(0.5, 0.8, -1))
light = bpy.context.object
light.data.energy = 1000

# Directory for rendered frames
frames_dir = os.path.join(os.path.dirname(bpy.data.filepath), "frames")
os.makedirs(frames_dir, exist_ok=True)

# Render all frames
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(frames_dir, f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

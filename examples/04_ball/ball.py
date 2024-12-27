# Damien Joubert, 03-02-2020 (Modified for moving sphere simulation with camera adjustments)
import bpy
from mathutils import Vector
import cv2
import math
import os, sys
sys.path.append("../../src")
from dvs_sensor import *
from dvs_sensor_blender import Blender_DvsSensor
from event_display import EventDisplay

path_Sphere = os.path.abspath(os.getcwd()) + "/../../data/"

if not os.path.exists(path_Sphere + "tmp"):
    os.mkdir(path_Sphere + "tmp")
if not os.path.exists(path_Sphere + "tmp/events"):
    os.mkdir(path_Sphere + "tmp/events")
if not os.path.exists(path_Sphere + "tmp/render"):
    os.mkdir(path_Sphere + "tmp/render")

scene = bpy.context.scene

bpy.ops.object.select_all(action='DESELECT')

# Clean up default objects
if "Camera" in bpy.data.objects:
    bpy.data.objects['Camera'].select_set(True)
    bpy.ops.object.delete()
if "Light" in bpy.data.objects:
    bpy.data.objects['Light'].select_set(True)
    bpy.ops.object.delete()
if "Cube" in bpy.data.objects:
    bpy.data.objects['Cube'].select_set(True)
    bpy.ops.object.delete()

# Add light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))
light = bpy.context.active_object
light.data.energy = 2.0

# Add a sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
sphere = bpy.context.active_object
sphere.name = 'Sphere'

# Apply material to the sphere
matname = "SphereMaterial"
material = bpy.data.materials.new(name=matname)
material.use_nodes = True
sphere.data.materials.append(material)

# Add the camera and adjust its position
ppsee = Blender_DvsSensor("Sensor")
ppsee.set_sensor(nx=360, ny=160, pp=0.015)
ppsee.set_dvs_sensor(th_pos=0.15, th_neg=0.15, th_n=0.05, lat=500, tau=300, jit=100, bgn=0.0001)
ppsee.set_sensor_optics(8)
master_collection = bpy.context.collection
master_collection.objects.link(ppsee.cam)
scene.camera = ppsee.cam

# Adjust camera position and orientation to ensure the sphere is visible
ppsee.set_position([0.0, -15.0, 5.0])  # Move the camera back and up
ppsee.set_angle([math.radians(90), 0.0, 0.0])  # Tilt the camera towards the sphere

ppsee.init_tension()
ppsee.init_bgn_hist("../../data/noise_pos_161lux.npy", "../../data/noise_pos_161lux.npy")

# Configure rendering
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = ppsee.def_x
scene.render.resolution_y = ppsee.def_y
scene.render.filepath = path_Sphere + "tmp/render/sphere_image.png"

# Event data processing
ed = EventDisplay("Events", ppsee.def_x, ppsee.def_y, 10000)
fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
out = cv2.VideoWriter('sphere.avi', fourcc, 20.0, (ppsee.def_x, ppsee.def_y))
ev = EventBuffer(0)

# Animate the sphere
frames = 100
for frame in range(frames):
    sphere.location = Vector((math.sin(frame * 0.1) * 5, math.cos(frame * 0.1) * 5, frame * 0.1))
    ppsee.update_time(1/1000)
    ppsee.print_position()

    bpy.ops.render.render(write_still=1)
    im = cv2.imread(path_Sphere + "tmp/render/sphere_image.png")
    out.write(im)

    if frame == 0:
        ppsee.init_image(im)
    else:
        pk = ppsee.update(im, 1000)
        ed.update(pk, 1000)
        ev.increase_ev(pk)

    cv2.imshow("Blender", im)
    cv2.waitKey(1)

out.release()
ev.write(path_Sphere + "tmp/events/" + 'ev_sphere.dat')


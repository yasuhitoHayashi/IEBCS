# Joubert Damien, 03-02-2020
import bpy
import mathutils
import cv2
import math
import os, sys
sys.path.append("../../src")
from dvs_sensor import *
from dvs_sensor_blender import Blender_DvsSensor
from event_display import EventDisplay

scene = bpy.context.scene

# Remove Objects automatically generated by Blender, but not the the cube
bpy.ops.object.select_all(action='DESELECT')
bpy.data.objects['Camera'].select = True
bpy.data.objects['Cube'].select = True
bpy.ops.object.delete()

# Add texture
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
matname = "CheeseMapping"
texname = "texCheeseapping"
material = bpy.data.materials.new(matname)
material.diffuse_color = (0.5, .5, .5)
obj = bpy.context.scene.objects.active
obj = bpy.context.scene.objects['Cube']
obj.data.materials.append(material)
texUV = bpy.data.textures.new(texname, type="IMAGE")
image_path = os.path.expanduser(os.path.abspath(os.getcwd()) + "/../../data/img/Fourme_Ambert_02.jpg")
image = bpy.data.images.load(image_path)
texUV.image = image
bpy.data.materials[matname].texture_slots.add()
bpy.data.materials[matname].active_texture = texUV
bpy.data.materials[matname].texture_slots[0].texture_coords = "GLOBAL"
bpy.data.materials[matname].texture_slots[0].mapping = "CUBE"

# Move objects
bpy.data.objects['Cube'].location = mathutils.Vector((0, 0, 10))
bpy.data.objects['Cube'].rotation_euler = mathutils.Vector((3.14/4, 3.14/4, 0))
bpy.data.objects['Lamp'].location = mathutils.Vector((5, 5, 5))
bpy.data.objects['Lamp'].data.energy = 1

# Create the camera
ppsee = Blender_DvsSensor("Sensor")
ppsee.set_sensor(nx=360, ny=160, pp=0.015)
ppsee.set_dvs_sensor(th_pos=0.15, th_neg=0.15, th_n=0.05, lat=500, tau=300, jit=100, bgn=0.0001)
ppsee.set_sensor_optics(8)
scene.objects.link(ppsee.cam)
scene.camera = ppsee.cam
ppsee.set_angle([math.pi, 0.0, 0.0])
ppsee.set_position([0.0, 0.0, 0.0])
ppsee.set_speeds([0.0, 0, 0], [0.0, 0.0, 10])
ppsee.init_tension()
ppsee.init_bgn_hist("../../data/noise_pos_161lux.npy", "../../data/noise_pos_161lux.npy")

scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = "image.png"
scene.render.resolution_x = 2*ppsee.def_x
scene.render.resolution_y = 2*ppsee.def_y

ed = EventDisplay("Events", ppsee.def_x, ppsee.def_y, 10000)

for p in range(0, 100, 1):
    ppsee.update_time(1/1000)
    ppsee.print_position()
    bpy.ops.render.render(write_still=1)
    im = cv2.imread("image.png")
    if p == 0:
        ppsee.init_image(im)
    else:
        pk = ppsee.update(im, 1000)
        ed.update(pk, 1000)
        bpy.data.objects['Lamp'].data.energy += 0.01

    cv2.imshow("Blender", im)
    cv2.waitKey()

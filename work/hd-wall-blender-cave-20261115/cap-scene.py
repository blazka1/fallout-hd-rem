"""Bake the same Blender rock shader on the horizontal cutaway surface."""
import bpy,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/v13ent-wall-blender/cave-v3-20261115'
bpy.ops.wm.open_mainfile(filepath=str(O/'fallout-cave-walls.blend'))
for obj in list(bpy.data.objects):
 if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
mat=bpy.data.materials.get('Dry charcoal schist - continuous world grain')
for node in mat.node_tree.nodes:
 if node.type=='TEX_IMAGE':node.image=bpy.data.images.load(str(O/'reference-rock-periodic.png'));node.image.pack()
bpy.ops.mesh.primitive_plane_add(size=4,location=(0,0,2));bpy.context.object.data.materials.append(mat)
scene=bpy.context.scene;cam=scene.camera;cam.location=(0,0,10);cam.rotation_euler=(0,0,0);cam.data.ortho_scale=2/math.sqrt(3)
scene.render.resolution_x=768;scene.render.resolution_y=888;scene.render.resolution_percentage=100
bpy.data.lights['Fallout upper-left key'].energy=5.0;bpy.data.lights['Subtle sky fill'].energy=.8
scene.cycles.samples=48;scene.render.filepath=str(O/'cap-material-raw.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'cap-material.blend'));bpy.ops.render.render(write_still=True)

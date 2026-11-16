"""Author and render a solid, fractured cave corner in Blender (not image warping)."""
import bpy,math,random,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.noise import noise_vector
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/v13ent-wall-blender/natural-v2-20261115'
O.mkdir(parents=True,exist_ok=True)
rng=random.Random(15112026)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
# Calibrated projected ground axes: (+48,-12), (+32,+24).
# Blender Y is opposite to the second game axis, which is 2/sqrt(3) units long.
K=48/(math.sqrt(3)/2);e=math.asin(math.sqrt(3)/4)
RIGHT=Vector((math.sqrt(3)/2,-.5,0));UP=Vector((.5*math.sin(e),math.sqrt(3)/2*math.sin(e),math.cos(e)));OUT=RIGHT.cross(UP)
ORIGIN=(4240,400);BOX=[4184,280,4456,500];SCALE=4
def ground(x,y):
 dx=(x-ORIGIN[0])/K;dy=-(y-ORIGIN[1])/K/math.sin(e)
 return Vector((RIGHT.x*dx+.5*dy,RIGHT.y*dx+math.sqrt(3)/2*dy,0))
control=[(4182,413),(4200,414),(4225,414),(4250,413),(4280,412),(4310,414),(4336,418),(4352,424),(4368,434),(4384,446),(4402,459),(4420,473),(4445,492),(4460,504)]
path=[ground(*p) for p in control];lengths=[0.]
for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+(b-a).length)
L=lengths[-1];H=86/(K*math.cos(e));THICK=.70
def frame(s):
 s=max(0,min(L,s));i=next((i for i in range(len(lengths)-1) if s<=lengths[i+1]),len(lengths)-2)
 t=(s-lengths[i])/(lengths[i+1]-lengths[i]);p=path[i].lerp(path[i+1],t)
 # Interpolated directions prevent faceted joins at the authored path nodes.
 def tangent(j):return (path[min(len(path)-1,j+1)]-path[max(0,j-1)]).normalized()
 tan=tangent(i).lerp(tangent(i+1),t).normalized();n=Vector((tan.y,-tan.x,0))
 if n.dot(OUT)<0:n=-n
 return p,n
def ease(v):v=max(0,min(1,v));return v*v*(3-2*v)
def crest(s):
 p,_=frame(s);x=ORIGIN[0]+p.dot(RIGHT)*K
 # The two attachment shoulders rise into the existing higher rim. This is
 # actual mesh height, avoiding a vertical alpha step at the blend endpoints.
 shoulder=25*(1-ease((x-4194)/45))+24*ease((x-4405)/28)
 return H+shoulder/(K*math.cos(e))+.035*math.sin(s*6.1)+.023*math.sin(s*13.2+.7)
def point(s,z,d):
 p,n=frame(s);return p+n*d+Vector((0,0,z/H*crest(s)))
def mesh(name,verts,faces,mat):
 m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);o.data.materials.append(mat);return o
def rock_material():
 m=bpy.data.materials.new('Dry charcoal schist - continuous world grain');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');bs.inputs['Roughness'].default_value=.94;bs.inputs['Specular IOR Level'].default_value=.16;l.new(bs.outputs['BSDF'],out.inputs['Surface'])
 geo=n.new('ShaderNodeNewGeometry');co=geo.outputs['Position']
 large=n.new('ShaderNodeTexNoise');large.inputs['Scale'].default_value=3.8;large.inputs['Detail'].default_value=4.;large.inputs['Roughness'].default_value=.72;l.new(co,large.inputs['Vector'])
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.055,.058,.061,1);ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(.235,.242,.249,1);l.new(large.outputs['Fac'],ramp.inputs['Fac'])
 # Millimetric sand noise made V1 look like concrete. Use irregular chips
 # at the same apparent scale as geo-rock-01 / original rock03 instead.
 warp=n.new('ShaderNodeVectorMath');warp.operation='SCALE';warp.inputs['Scale'].default_value=.095;l.new(large.outputs['Color'],warp.inputs[0])
 add=n.new('ShaderNodeVectorMath');add.operation='ADD';l.new(co,add.inputs[0]);l.new(warp.outputs['Vector'],add.inputs[1])
 chips=n.new('ShaderNodeTexVoronoi');chips.feature='DISTANCE_TO_EDGE';chips.inputs['Scale'].default_value=12;l.new(add.outputs['Vector'],chips.inputs['Vector'])
 edge=n.new('ShaderNodeValToRGB');edge.color_ramp.elements[0].position=.007;edge.color_ramp.elements[0].color=(.70,.70,.70,1);edge.color_ramp.elements[1].position=.035;edge.color_ramp.elements[1].color=(1,1,1,1);l.new(chips.outputs['Distance'],edge.inputs['Fac'])
 mask=n.new('ShaderNodeValToRGB');mask.color_ramp.elements[0].position=.47;mask.color_ramp.elements[0].color=(0,0,0,1);mask.color_ramp.elements[1].position=.66;mask.color_ramp.elements[1].color=(.45,.45,.45,1);l.new(large.outputs['Fac'],mask.inputs['Fac'])
 multiply=n.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';l.new(mask.outputs['Color'],multiply.inputs[0]);l.new(ramp.outputs['Color'],multiply.inputs[1]);l.new(edge.outputs['Color'],multiply.inputs[2])
 # Low-strength material detail from a fully opaque patch of the neighboring
 # HD rock03. Box projection uses actual 3D positions, shared across the bend.
 density=n.new('ShaderNodeVectorMath');density.operation='SCALE';density.inputs['Scale'].default_value=1.45;l.new(co,density.inputs[0])
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'reference-rock-detail.png'));tex.image.pack();tex.projection='BOX';tex.projection_blend=.3;tex.extension='REPEAT';l.new(density.outputs['Vector'],tex.inputs['Vector'])
 matched=n.new('ShaderNodeMixRGB');matched.blend_type='MIX';matched.inputs[0].default_value=.42;l.new(multiply.outputs['Color'],matched.inputs[1]);l.new(tex.outputs['Color'],matched.inputs[2]);l.new(matched.outputs['Color'],bs.inputs['Base Color'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.016;l.new(chips.outputs['Distance'],bump.inputs['Height'])
 grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=45;grain.inputs['Detail'].default_value=2;l.new(co,grain.inputs['Vector'])
 b2=n.new('ShaderNodeBump');b2.inputs['Strength'].default_value=.35;b2.inputs['Distance'].default_value=.006;l.new(grain.outputs['Fac'],b2.inputs['Height']);l.new(bump.outputs['Normal'],b2.inputs['Normal'])
 chipbump=n.new('ShaderNodeBump');chipbump.inputs['Strength'].default_value=.32;chipbump.inputs['Distance'].default_value=.025;l.new(tex.outputs['Color'],chipbump.inputs['Height']);l.new(b2.outputs['Normal'],chipbump.inputs['Normal']);l.new(chipbump.outputs['Normal'],bs.inputs['Normal'])
 return m
mat=rock_material()
# One continuous exposed mesh. Sparse fault lines do not enclose every mass.
# No separately inset Voronoi polygons, bevelled plates, or mortar-like gaps.
faults=[]
for i in range(14):
 faults.append((rng.uniform(.1,L-.1),rng.uniform(.25,H*1.25),rng.uniform(.35,H),rng.uniform(-.65,.25),rng.uniform(.012,.032),rng.uniform(.09,.19),rng.uniform(0,20)))
def nv(s,z,f=1):return noise_vector(Vector((s*f,z*f,1.328))).x
def relief(s,z):
 # Broad ridges and oblique strata share one geological field across the bend.
 warp=.24*nv(s*.66,z*.8)
 q=s+z*.42+warp
 broad=.20*(1-abs(nv(q,z*.75,1.55)))
 medium=.075*(1-abs(nv(q+.6,z*.95,3.8)))
 small=.007*nv(s+z*.2,z,12.0)
 d=.015+broad+medium+small
 for ss,zz,extent,slope,width,depth,phase in faults:
  t=(z-zz)/extent
  if abs(t)>=1:continue
  center=ss+slope*(z-zz)+.025*math.sin(z*19+phase)+.018*nv(z*8,phase)
  distance=abs(s-center);taper=(1-t*t)**.7
  d-=depth*taper*math.exp(-(distance/(width*(.5+.5*taper)))**2)
 # Ground and upper lip remain supported by the common mesh.
 return d*(.65+.35*ease(z/.25))
N=360;M=150;C=22;verts=[];faces=[];stride=M+C+1
for j in range(N+1):
 s=L*j/N;topdepth=relief(s,H)
 for k in range(M+1):
  z=H*k/M;verts.append(point(s,z,relief(s,z)))
 for k in range(1,C+1):
  t=k/C;depth=topdepth*(1-t)-THICK*t
  # Shared top-front edge, gently broken rock surface above the vertical face.
  v=point(s,H,depth);v.z+=math.sin(math.pi*t)*(.025*nv(s*5,t*4)+.014*nv(s*14,t*9));verts.append(v)
for j in range(N):
 for k in range(stride-1):
  a=j*stride+k;b=a+stride
  faces.append((a,b,b+1,a+1))
core=mesh('Continuous eroded cave rock and crown',verts,faces,mat)
for f in core.data.polygons:f.use_smooth=True
# Close the solid along its back, base and both endpoints.
bottom=[];back=[]
for j in range(N+1):
 s=L*j/N;bottom.append(len(verts));verts.append(point(s,0,-THICK))
for j in range(N):
 faces.extend([(bottom[j],bottom[j+1],(j+1)*stride,j*stride),(j*stride+stride-1,(j+1)*stride+stride-1,bottom[j+1],bottom[j])])
faces.extend([tuple([bottom[0]]+list(range(stride-1,-1,-1))),tuple(list(range(N*stride,(N+1)*stride))+[bottom[-1]])])
oldmesh=core.data;m=bpy.data.meshes.new('Solid natural cave mesh');m.from_pydata(verts,[],faces);m.update();core.data=m;core.data.materials.append(mat);bpy.data.meshes.remove(oldmesh)
for f in m.polygons:f.use_smooth=False
# Chisel the continuous mass into irregular planar fracture faces. Collapsing
# the dense sculpt preserves the volume while avoiding both smooth clay and
# the uniform inset outlines of the discarded plate construction.
bpy.context.view_layer.objects.active=core;core.select_set(True)
dec=core.modifiers.new('Angular fracture planes','DECIMATE');dec.ratio=.035;dec.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=dec.name)
for f in core.data.polygons:f.use_smooth=True
core.data.set_sharp_from_angle(angle=math.radians(28))
core.select_set(False)
cell_count=0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=6
scene.world.color=(.32,.32,.32)
def light(name,location,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=location;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
light('Broad upper-left Fallout key',(-3,-4,8),950,4)
light('Restrained sky fill',(3,1,6),180,5)
camdata=bpy.data.cameras.new('Fallout calibrated orthographic');cam=bpy.data.objects.new('Fallout calibrated orthographic',camdata);bpy.context.collection.objects.link(cam)
cx=(BOX[0]+BOX[2])/2-ORIGIN[0];cy=(BOX[1]+BOX[3])/2-ORIGIN[1]
cam.location=RIGHT*(cx/K)+UP*(-cy/K)+OUT*30;cam.rotation_euler=Matrix((RIGHT,UP,OUT)).transposed().to_euler();camdata.type='ORTHO'
# Blender orthographic scale describes the larger (horizontal) dimension here.
camdata.ortho_scale=(BOX[2]-BOX[0])/K;scene.camera=cam
scene.render.resolution_x=(BOX[2]-BOX[0])*SCALE;scene.render.resolution_y=(BOX[3]-BOX[1])*SCALE;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.filepath=str(O/'corner-render.png')
bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view
def projected(p):
 v=world_to_camera_view(scene,cam,Vector(p));return (v.x*scene.render.resolution_x/SCALE,-v.y*scene.render.resolution_y/SCALE)
zero=projected((0,0,0));axes=[]
for p,expected in [((1,0,0),(48,-12)),((0,-2/math.sqrt(3),0),(32,24))]:
 q=projected(p);delta=[q[i]-zero[i] for i in range(2)];axes.append(delta);assert max(abs(delta[i]-expected[i]) for i in range(2))<.001,(delta,expected)
(O/'camera-calibration.json').write_text(json.dumps(dict(measured_ground_axes=axes,expected=[[48,-12],[32,24]],max_error_pixels=.001),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'fallout-wall-corner.blend'))
(O/'scene-registration.json').write_text(json.dumps(dict(box=BOX,scale=SCALE,origin=ORIGIN,ground_axes=[[48,-12],[32,24]],camera_elevation_degrees=math.degrees(e),pixels_per_blender_unit=K,physical_height=H,physical_thickness=THICK,fractured_rocks=cell_count,footprint_screen_control=control,seed=15112026,renderer='Blender Cycles CPU, 40 samples',source='authored 3D mesh and procedural stone material; no image atlas'),indent=2))
bpy.ops.render.render(write_still=True)

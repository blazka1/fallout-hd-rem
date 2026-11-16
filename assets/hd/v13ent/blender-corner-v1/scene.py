"""Author and render a solid, fractured cave corner in Blender (not image warping)."""
import bpy,math,random,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.noise import noise_vector
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/v13ent-wall-blender/pilot-20261115'
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
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.17;ramp.color_ramp.elements[0].color=(.065,.068,.070,1);ramp.color_ramp.elements[1].position=.83;ramp.color_ramp.elements[1].color=(.23,.23,.215,1);l.new(large.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
 grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=28;grain.inputs['Detail'].default_value=3;l.new(co,grain.inputs['Vector'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.63;bump.inputs['Distance'].default_value=.035;l.new(grain.outputs['Fac'],bump.inputs['Height'])
 fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=125;fine.inputs['Detail'].default_value=2;l.new(co,fine.inputs['Vector'])
 b2=n.new('ShaderNodeBump');b2.inputs['Strength'].default_value=.45;b2.inputs['Distance'].default_value=.008;l.new(fine.outputs['Fac'],b2.inputs['Height']);l.new(bump.outputs['Normal'],b2.inputs['Normal']);l.new(b2.outputs['Normal'],bs.inputs['Normal'])
 return m
mat=rock_material()
# Closed bedrock mass: upper face has physical thickness and joins both sides.
N=140;verts=[]
for j in range(N+1):
 s=L*j/N
 for z,d in [(0,-THICK),(0,-.025),(H,-.025),(H,-THICK)]:verts.append(point(s,z,d))
faces=[]
for j in range(N):
 for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
faces += [(3,2,1,0),(N*4,N*4+1,N*4+2,N*4+3)]
core=mesh('Solid continuous bedrock with crown',verts,faces,mat)
# Voronoi fracture cells in a sheared rock-face coordinate system. They are
# shallow 3D wedge volumes with chipped rims, not a rectangular brick pattern.
def metric(p):return Vector((p[0]+.62*p[1],p[1]*.43))
seeds=[]
for _ in range(1000):
 p=(rng.uniform(-.25,L+.25),rng.uniform(-.18,H+.18))
 if all((metric(p)-metric(q)).length>.29 for q in seeds):seeds.append(p)
 if len(seeds)>=56:break
def clip(poly,a,b,c):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  vp=a*p[0]+b*p[1]-c;vq=a*q[0]+b*q[1]-c
  if vp<=0:out.append(p)
  if (vp<0)!=(vq<0):
   t=vp/(vp-vq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return out
cell_count=0
for idx,p in enumerate(seeds):
 poly=[(0,0),(L,0),(L,H),(0,H)];pm=metric(p)
 for q in seeds:
  if q==p:continue
  qm=metric(q);d=qm-pm;c=(qm.length_squared-pm.length_squared)/2
  poly=clip(poly,d.x,.62*d.x+.43*d.y,c)
  if len(poly)<3:break
 if len(poly)<3:continue
 center=(sum(a for a,b in poly)/len(poly),sum(b for a,b in poly)/len(poly));count=len(poly)
 depth=rng.uniform(.035,.24);tilt=rng.uniform(-.10,.10);rim=rng.uniform(.12,.24)
 vs=[]
 for s,z in poly:
  si=s;zi=z
  if z==H:zi=H
  if z==0:zi=0
  vs.append(point(si,zi,.005))
 for s,z in poly:
  si=s+(center[0]-s)*rim;zi=z+(center[1]-z)*rim
  if z==H:zi=H
  if z==0:zi=0
  vs.append(point(si,zi,depth+tilt*(zi-center[1])))
 vs.append(point(center[0],center[1],depth+rng.uniform(-.015,.025)))
 fs=[]
 for k in range(count):fs.extend([(k,(k+1)%count,(k+1)%count+count,k+count),(k+count,(k+1)%count+count,count*2)])
 # For cells meeting the crest, continue their cap back into the solid crown.
 for k in range(count):
  a,b=poly[k],poly[(k+1)%count]
  if abs(a[1]-H)<1e-5 and abs(b[1]-H)<1e-5:
   a0=len(vs);vs.extend([point(a[0],H,-THICK),point(b[0],H,-THICK)]);fs.append((k,(k+1)%count,a0+1,a0))
 rock=mesh('Fractured stone %03d'%idx,vs,fs,mat)
 # Split the planes for small physical erosion. The same displacement field
 # is used on every stone, so touching edges move together.
 bpy.context.view_layer.objects.active=rock;rock.select_set(True)
 mod=rock.modifiers.new('Chipped face tessellation','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=3
 bpy.ops.object.modifier_apply(modifier=mod.name)
 for v in rock.data.vertices:
  q=v.co.copy();nv=noise_vector(q*11.7);fine=noise_vector(q*35.1)
  v.co+=nv*.018+fine*.0035
 for face in rock.data.polygons:face.use_smooth=True
 rock.select_set(False);cell_count+=1
# Fine crests on the crown break the featureless planar read without a jagged silhouette.
for j in range(20):
 s=L*(j+.5)/20;delta=rng.uniform(.08,.19);p,n=frame(s);t=Vector((-n.y,n.x,0))
 v=[]
 for ds,d,z in [(-delta,-.15,H),(.8*delta,-.15,H),(delta,-.55,H),(-delta*.7,-.58,H),(0,-.35,H+.025)]:
  v.append(point(s+ds,z,d))
 mesh('Crown fracture %02d'%j,v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mat)
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

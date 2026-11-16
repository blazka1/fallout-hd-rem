"""Continuous Blender cave surfaces, calibrated to Fallout's sprite camera."""
import bpy,math,json,random,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.noise import noise_vector
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/v13ent-wall-blender/cave-v3-20261115'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
mode=args[0] if args else 'proof'
inv=json.loads((O/'inventory.json').read_text());BOX=inv['box'];ORIGIN=(4240,400)
K=48/(math.sqrt(3)/2);e=math.asin(math.sqrt(3)/4);V=K*math.cos(e)
RIGHT=Vector((math.sqrt(3)/2,-.5,0));UP=Vector((.5*math.sin(e),math.sqrt(3)/2*math.sin(e),math.cos(e)));OUT=RIGHT.cross(UP)
def ground(x,y):
 dx=(x-ORIGIN[0])/K;dy=-(y-ORIGIN[1])/K/math.sin(e)
 return Vector((RIGHT.x*dx+.5*dy,RIGHT.y*dx+math.sqrt(3)/2*dy,0))
def ease(v):v=max(0,min(1,v));return v*v*(3-2*v)
def nv(s,z,f=1):return noise_vector(Vector((s*f,z*f,1.328))).x
def make_scene():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 # Load the exact accepted shader, including its packed reference stone image.
 source=R/'assets/generated/v13ent-wall-blender/natural-v2-20261115/fallout-wall-corner.blend'
 with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.materials=['Dry charcoal schist - continuous world grain']
 mat=dst.materials[0];assert mat is not None
 f=np.load(O/'mesh-guides.npz');mask=f['mask'];top=f['top'];bottom=f['bottom'];slope=f['deriv'];distance=f['distance']
 hh,ww=mask.shape;index=np.full(mask.shape,-1,np.int32);verts=[];faces=[];boundary=[]
 rng=random.Random(15112503);faults={}
 for bx in range(-2,ww//64+3):
  # Sparse open, oblique faults; independent spacing/depth, no cell outlines.
  faults[bx]=[(bx*64+BOX[0]+rng.uniform(-25,25),rng.uniform(.3,2.0),rng.uniform(.6,1.6),rng.uniform(-.7,.35),rng.uniform(.014,.035),rng.uniform(.09,.21),rng.uniform(0,20)) for _ in range(2)]
 for yy in range(hh):
  if yy%150==0:print('MESH ROW',yy,'/',hh,flush=True)
  for xx in np.flatnonzero(mask[yy]):
   wx=xx+BOX[0];wy=yy+BOX[1];b=float(bottom[yy,xx]);t=float(top[yy,xx]);dist=float(distance[yy,xx]);sl=float(slope[yy,xx])
   # A shallow crown is a true horizontal stone plane. Front and crown share
   # the same grid vertices along the lip, including every bend.
   crown=8.0;lip=t+crown;z=max(0,(b-max(wy,lip))/V)
   p=ground(wx,wy+V*z)+Vector((0,0,z))
   tangent=ground(wx+1,b+sl)-ground(wx-1,b-sl);n=Vector((tangent.y,-tangent.x,0)).normalized()
   if n.dot(OUT)<0:n=-n
   s=(wx-ORIGIN[0])/K;phase=(b-ORIGIN[1])/220
   warp=.24*nv(s*.66+phase,z*.8);q=s+z*.42+warp
   amplitude=.8+.35*(.5+.5*nv(s*.2,phase))
   relief=amplitude*(.015+.20*(1-abs(nv(q,z*.75+phase,1.55)))+.075*(1-abs(nv(q+.6,z*.95+phase,3.8)))+.007*nv(s+z*.2,z+phase,12))
   for key in range(int(xx)//64-2,int(xx)//64+3):
    for fx,zz,extent,lean,width,depth,ph in faults.get(key,[]):
     zz+=.2*math.sin(phase*3+ph);u=(z-zz)/extent
     if abs(u)>=1:continue
     center=(fx-ORIGIN[0])/K+lean*(z-zz)+.025*math.sin(z*19+ph)+.018*nv(z*8,ph+phase)
     taper=(1-u*u)**.7
     relief-=depth*taper*math.exp(-((s-center)/(width*(.5+.5*taper)))**2)
   # Relief fades at canvas limits and supporting contours, preventing spikes
   # into the vault frame, walking space, or a neighboring sprite's canvas.
   lip_blend=ease((wy-t-3)/7);support=ease(dist/5.)
   delta=n*relief*lip_blend*support*(.65+.35*ease(z/.25))
   delta.z+=.018*nv(p.x*4,p.y*4)*support*(1-lip_blend)
   # Bound displacement in projected pixels, not merely Blender units. This
   # keeps the actual sculpt within its support even on an oblique turn.
   projected=K*math.hypot(delta.dot(RIGHT),delta.dot(UP))
   delta*=min(1.,max(0.,dist-2.)/max(projected,1e-8));p+=delta
   if dist<5:boundary.append(len(verts))
   index[yy,xx]=len(verts);verts.append(tuple(p))
  if yy:
   ok=mask[yy,:-1]&mask[yy,1:]&mask[yy-1,:-1]&mask[yy-1,1:]
   for x in np.flatnonzero(ok):faces.append((int(index[yy-1,x]),int(index[yy,x]),int(index[yy,x+1]),int(index[yy-1,x+1])))
 m=bpy.data.meshes.new('Continuous cave faces and shared crowns');m.from_pydata(verts,[],faces);m.update()
 o=bpy.data.objects.new('Natural cave bedrock - all registered runs',m);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 group=o.vertex_groups.new(name='Sculpt interior');group.add(list(range(len(verts))),1.0,'REPLACE');group.add(boundary,0.,'REPLACE')
 print('DECIMATING',len(verts),len(faces),flush=True)
 dec=o.modifiers.new('Angular natural fractures','DECIMATE');dec.ratio=.09;dec.use_collapse_triangulate=True;dec.vertex_group=group.name;dec.vertex_group_factor=1.;bpy.ops.object.modifier_apply(modifier=dec.name)
 for poly in o.data.polygons:poly.use_smooth=True
 o.data.set_sharp_from_angle(angle=math.radians(55));o.select_set(False)
 # Constant directional illumination over the whole map, so there is no
 # lighting seam from separately rendered tiles or moving area lights.
 for name,location,power,angle in [('Fallout upper-left key',(-3,-4,8),5.0,.5),('Subtle sky fill',(3,1,6),.8,.7)]:
  d=bpy.data.lights.new(name,'SUN');d.energy=power;d.angle=angle
  l=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(l);l.rotation_euler=(Vector((0,0,1))-Vector(location)).to_track_quat('-Z','Y').to_euler()
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=8
 scene.world.color=(.32,.32,.32)
 camdata=bpy.data.cameras.new('Fallout calibrated orthographic');cam=bpy.data.objects.new('Fallout calibrated orthographic',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO'
 scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
 scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
 print('MESH COMPLETE',len(o.data.vertices),len(o.data.polygons),flush=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'fallout-cave-walls.blend'))
 (O/'scene-registration.json').write_text(json.dumps(dict(box=BOX,scale=4,origin=ORIGIN,ground_axes=[[48,-12],[32,24]],camera_elevation=math.degrees(e),vertices=len(o.data.vertices),polygons=len(o.data.polygons),seed=15112503,material_source=str(source.relative_to(R))),indent=2))
def render(box,scale,name):
 scene=bpy.context.scene;cam=scene.camera
 if 'gpu' in args:
  prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
  devices=[]
  for dev in prefs.devices:
   dev.use=dev.type=='OPTIX'
   if dev.use:devices.append(dev.name)
  assert devices,'No OptiX device';scene.cycles.device='GPU';scene.cycles.use_auto_tile=True;scene.cycles.tile_size=1024
  scene.cycles.denoiser='OPTIX'
  print('RENDER DEVICE',devices,flush=True)
 cx=(box[0]+box[2])/2-ORIGIN[0];cy=(box[1]+box[3])/2-ORIGIN[1]
 cam.location=RIGHT*(cx/K)+UP*(-cy/K)+OUT*100;cam.rotation_euler=Matrix((RIGHT,UP,OUT)).transposed().to_euler()
 scene.render.resolution_x=(box[2]-box[0])*scale;scene.render.resolution_y=(box[3]-box[1])*scale;scene.render.resolution_percentage=100
 cam.data.ortho_scale=max(box[2]-box[0],box[3]-box[1])/K
 scene.render.filepath=str(O/(name+'.png'));bpy.context.view_layer.update()
 from bpy_extras.object_utils import world_to_camera_view
 def project(p):
  q=world_to_camera_view(scene,cam,Vector(p));return(q.x*scene.render.resolution_x/scale,-q.y*scene.render.resolution_y/scale)
 zero=project((0,0,0));measured=[]
 for p,expected in [((1,0,0),(48,-12)),((0,-2/math.sqrt(3),0),(32,24))]:
  q=project(p);delta=[q[i]-zero[i] for i in range(2)];assert max(abs(delta[i]-expected[i]) for i in range(2))<.003;measured.append(delta)
 (O/(name+'-camera.json')).write_text(json.dumps(dict(box=box,scale=scale,axes=measured,blender=bpy.app.version_string,renderer='Cycles',device=scene.cycles.device,denoiser=scene.cycles.denoiser,samples=scene.cycles.samples,sharp_edge_threshold_degrees=55,color_transform='Standard',lights={'key':5.0,'fill':.8}),indent=2))
 if name=='cave-render':bpy.ops.wm.save_as_mainfile(filepath=str(O/'fallout-cave-walls.blend'))
 bpy.ops.render.render(write_still=True)
if mode in ['proof','build']:make_scene()
else:bpy.ops.wm.open_mainfile(filepath=str(O/'fallout-cave-walls.blend'))
bpy.data.lights['Fallout upper-left key'].energy=5.0
bpy.data.lights['Subtle sky fill'].energy=.8
if mode=='softproof':
 for obj in bpy.data.objects:
  if obj.type=='MESH':
   a=obj.data.attributes.get('sharp_edge')
   if a:obj.data.attributes.remove(a)
   for poly in obj.data.polygons:poly.use_smooth=True
   obj.data.set_sharp_from_angle(angle=math.radians(55))
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'fallout-cave-walls-soft.blend'))
 render([4190,290,4450,505],4,'soft-proof')
if mode=='proof':render([4180,270,4990,670],2,'proof')
elif mode=='preview':render([4180,270,4990,670],2,'proof-bright')
elif mode=='full':render(BOX,4,'cave-render')
elif mode=='overview':render(BOX,1,'overview')
elif mode=='crop':render([int(v) for v in args[1:5]],4,args[5])
elif mode=='tiles':
 mask=np.load(O/'reference-fields.npz')['canvas'];tiles=[];count=0
 for yy in range(BOX[1],BOX[3],384):
  for xx in range(BOX[0],BOX[2],512):
   if not mask[yy-BOX[1]:min(mask.shape[0],yy-BOX[1]+384),xx-BOX[0]:min(mask.shape[1],xx-BOX[0]+512)].any():continue
   count+=1;b=[xx-32,yy-32,xx+512+32,yy+384+32];name=f'tile-{count:02}'
   tiles.append(dict(name=name,box=b,core=[xx,yy,xx+512,yy+384]))
   print('RENDER TILE',count,b,flush=True);render(b,4,name)
 (O/'tile-layout.json').write_text(json.dumps(dict(box=BOX,scale=4,padding_native=32,tiles=tiles,method='Overlapping orthographic regions of one unchanged world-space Blender scene'),indent=2))

from prepare import *
inv=read(R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115/inventory.json');ps=inv['placements']
sources={a['path']:a for a in read(SRC/'manifest.json')['assets']}
box=[min(p['x'] for p in ps)-4,min(p['y'] for p in ps)-4,max(p['x']+p['width'] for p in ps)+4,max(p['y']+p['height'] for p in ps)+4]
x0,y0,x1,y1=box
img=Image.new('RGBA',(x1-x0,y1-y0));owner=np.zeros((y1-y0,x1-x0),np.int32);canvas=np.zeros_like(owner,bool)
for p in ps:
 a=Image.open(SRC/sources[p['source']]['rgba_png']).convert('RGBA');xx=p['x']-x0;yy=p['y']-y0
 img.alpha_composite(a,(xx,yy));v=owner[yy:yy+p['height'],xx:xx+p['width']];v[np.asarray(a)[:,:,3]>0]=p['id']
 canvas[yy:yy+p['height'],xx:xx+p['width']]=True
mask=np.asarray(img)[:,:,3]>0
lab,n=nd.label(nd.binary_closing(mask,iterations=2));regions=[]
rgb=Image.new('RGB',img.size,(0,0,0));rgb.paste(img,mask=img.getchannel('A'));draw=ImageDraw.Draw(rgb)
for i,sl in enumerate(nd.find_objects(lab),1):
 if sl is None:continue
 yy,xx=np.where(lab[sl]==i);size=len(xx)
 if size<80:continue
 ys,xs=sl;ids=np.unique(owner[sl][lab[sl]==i]);ids=ids[ids>0].tolist()
 regions.append(dict(id=i,box=[xs.start+x0,ys.start+y0,xs.stop+x0,ys.stop+y0],pixels=size,objects=ids))
 draw.rectangle((xs.start,ys.start,xs.stop-1,ys.stop-1),outline=(250,150,30),width=1)
 draw.text((xs.start+5,ys.start+5),str(i),fill=(255,80,60))
save(O/'inventory.json',dict(box=box,placements=ps,regions=regions))
np.savez_compressed(O/'reference-fields.npz',mask=mask,owner=owner,canvas=canvas,labels=lab)
img.save(O/'original-wall-map.png');rgb.save(B/'original-components.png')
print('box',box,'regions',[(r['id'],len(r['objects']),r['box']) for r in regions])
front=np.zeros_like(mask);rear=np.zeros_like(mask)
for p in ps:
 a=np.asarray(Image.open(SRC/sources[p['source']]['rgba_png']).convert('RGBA'))[:,:,3]>0
 xx=p['x']-x0;yy=p['y']-y0;n=int(Path(p['source']).stem[2:])
 target=rear if n==50 or 53<=n<=70 else front
 target[yy:yy+p['height'],xx:xx+p['width']]|=a
im=np.zeros((*mask.shape,3),np.uint8);im[front]=(150,160,170);im[rear]=(55,60,65)
im=Image.fromarray(im);d=ImageDraw.Draw(im);records=[]
for kind,field in [('face',front),('rear',rear)]:
 labels,num=nd.label(nd.binary_closing(field,iterations=2));count=0
 for idx,sl in enumerate(nd.find_objects(labels),1):
  if sl is None or np.count_nonzero(labels[sl]==idx)<100:continue
  count+=1;ys,xs=sl;b=[xs.start+x0,ys.start+y0,xs.stop+x0,ys.stop+y0]
  name=f'{kind}-{count:02}';d.text((xs.start+8,ys.start+10),name,fill=(255,80,60))
  records.append(dict(name=name,box=b,area=int(np.count_nonzero(labels[sl]==idx))))
  np.save(O/(name+'.npy'),labels[sl]==idx)
save(O/'surface-regions.json',records);im.save(B/'surface-regions.png');print(records)

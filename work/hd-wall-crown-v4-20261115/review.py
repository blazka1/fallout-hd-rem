from bake import *
from PIL import ImageDraw,ImageFont
def main():
 before=B/'before';after=B/'after-v1';out=B/'review';out.mkdir(exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
 pairs=[]
 specs=[('entrance-hd',(0,0,1920,880),.5,'Цельный участок: разрез и боковая стенка'),('cave-22662-hd',(640,55,1740,675),1.,'Верхняя плоскость, уступ и изгиб стены')]
 for name,box,scale,title in specs:
  a=Image.open(before/(name+'.png')).convert('RGB').crop(box);b=Image.open(after/(name+'.png')).convert('RGB').crop(box)
  if scale!=1:
   size=tuple(round(i*scale) for i in a.size);a=a.resize(size,Image.Resampling.LANCZOS);b=b.resize(size,Image.Resampling.LANCZOS)
  w,h=a.size;im=Image.new('RGB',(w*2,h+76),(25,28,32));d=ImageDraw.Draw(im)
  d.text((12,5),title,font=font,fill='white');d.text((12,42),'До: чёрный срез V3',font=font,fill='white');d.text((w+12,42),'После: каменная верхушка V4',font=font,fill='white')
  im.paste(a,(0,76));im.paste(b,(w,76));dest=out/(name+'-comparison.png');im.save(dest)
  pairs.append(dict(file=str(dest.relative_to(R)),before=str((before/(name+'.png')).relative_to(R)),after=str((after/(name+'.png')).relative_to(R)),crop=box,scale=scale,color_or_brightness_adjustments=False))
 classic=[]
 for p in before.glob('*classic*.png'):
  q=after/p.name
  if q.exists():classic.append(dict(file=p.name,exact=np.array_equal(np.asarray(Image.open(p)),np.asarray(Image.open(q)))))
 assert all(x['exact'] for x in classic)
 save(B/'comparison.json',dict(pairs=pairs,classic_frames=classic,classic_all_exact=True,checks=read(after/'result.json')))
 print('Compared complete entrance and upper wall; classic captures identical:',len(classic))
if __name__=='__main__':main()

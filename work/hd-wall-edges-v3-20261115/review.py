"""Juxtapose untouched SDL captures at identical native crop and scale."""
from bake_edges import *
from PIL import ImageDraw,ImageFont
def main():
 before=B/'before';after=B/'after-v2';out=B/'review';out.mkdir(exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
 pairs=[('entrance-hd','Вход: верхний край и примыкание к раме',(1060,75,1860,475)),
        ('cave-22662-hd','Изгиб стены: верхняя кромка и торец',(670,100,1670,650))]
 evidence=[]
 for name,title,box in pairs:
  a=Image.open(before/(name+'.png')).convert('RGB').crop(box)
  b=Image.open(after/(name+'.png')).convert('RGB').crop(box)
  w,h=a.size;im=Image.new('RGB',(w*2,h+75),(25,28,32));d=ImageDraw.Draw(im)
  d.text((12,5),title,font=font,fill='white');d.text((12,41),'До',font=font,fill='white');d.text((w+12,41),'После',font=font,fill='white')
  im.paste(a,(0,75));im.paste(b,(w,75));file=out/(name+'-comparison.png');im.save(file)
  evidence.append(dict(file=str(file.relative_to(R)),before=str((before/(name+'.png')).relative_to(R)),after=str((after/(name+'.png')).relative_to(R)),crop=box,scale=1,color_adjustments=False))
 classic=[]
 for p in before.glob('*classic*.png'):
  q=after/p.name
  if q.exists():
   equal=np.array_equal(np.asarray(Image.open(p)),np.asarray(Image.open(q)))
   classic.append(dict(file=p.name,exact=equal))
 assert all(x['exact'] for x in classic),classic
 assert read(after/'result.json')['failed']==0
 save(B/'comparison.json',dict(pairs=evidence,classic_frames=classic,classic_all_exact=True,before_checks=read(before/'result.json'),after_checks=read(after/'result.json')))
 print('Two unchanged-color comparison pairs; original frames identical:',len(classic))
if __name__=='__main__':main()

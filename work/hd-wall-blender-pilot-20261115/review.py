from pack import *
import sys
def main():
 after=B/(sys.argv[1] if len(sys.argv)>1 else 'after-v2');dest=B/'review';dest.mkdir(exist_ok=True)
 def load(d,n):
  p=d/(n+'.png')
  if not p.exists():p=d/(n+'.bmp')
  return Image.open(p).convert('RGB')
 before=B/('before-final' if (B/'before-final').exists() else 'before')
 box=(1210,170,1840,670);specs=[('Оригинал Fallout',before,'entrance-classic'),('До: прежний HD',before,'entrance-hd'),('После: участок из Blender',after,'entrance-hd')]
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22);w=box[2]-box[0];h=box[3]-box[1]
 im=Image.new('RGB',(w*3,h+48),(25,28,32));d=ImageDraw.Draw(im)
 for i,(title,folder,file) in enumerate(specs):
  d.text((i*w+12,10),title,fill='white',font=font);im.paste(load(folder,file).crop(box),(i*w,48))
 im.save(dest/'corner-comparison.png')
 pair=Image.new('RGB',(w*2,h+48),(25,28,32));pair.paste(im.crop((w,0,w*3,h+48)),(0,0));pair.save(dest/'before-after.png')
 classic=[]
 for p in before.glob('*classic*.png'):
  q=after/p.name
  if q.exists():classic.append(dict(file=p.name,exact=np.array_equal(np.asarray(Image.open(p)),np.asarray(Image.open(q)))))
 save(B/'comparison.json',dict(before=str(before.relative_to(R)),after=str(after.relative_to(R)),crop=box,scale=1,color_correction=False,classic_frames=classic,classic_all_exact=bool(classic) and all(a['exact'] for a in classic)))
 print('Created unretouched game comparisons; classic frames:',len(classic))
if __name__=='__main__':main()

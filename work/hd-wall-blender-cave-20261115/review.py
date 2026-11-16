from prepare import *
import sys
def main():
 after=B/(sys.argv[1] if len(sys.argv)>1 else 'after-v1');before=B/'before';dest=B/'review';dest.mkdir(exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
 names=['entrance','cave-18721','cave-22662','cave-27075','cave-27871']
 for name in names:
  out=Image.new('RGB',(1920,580),(24,27,31));draw=ImageDraw.Draw(out)
  for x,title,folder in [(0,'До: прежние стены',before),(960,'После: общий набор Blender',after)]:
   draw.text((x+16,7),title,font=font,fill='white')
   im=Image.open(folder/(name+'-hd.png')).convert('RGB');assert im.size==(1920,1080)
   out.paste(im.resize((960,540),Image.Resampling.LANCZOS),(x,40))
  out.save(dest/(name+'-comparison.png'))
 classic=[]
 for p in before.glob('*classic*.png'):
  q=after/p.name
  if q.exists():classic.append(dict(file=p.name,exact=np.array_equal(np.asarray(Image.open(p)),np.asarray(Image.open(q)))))
 save(B/'comparison.json',dict(before=str(before.relative_to(R)),after=str(after.relative_to(R)),scale=.5,color_correction=False,views=names,classic_frames=classic,classic_all_exact=bool(classic) and all(a['exact'] for a in classic)))
 # Render contact sheet for review of all camera positions, including those
 # not selected for the user-facing comparisons.
 frames=['entrance','cave-16290','cave-18721','cave-22662','cave-24097','cave-27075','cave-27871','actor-behind']
 sheet=Image.new('RGB',(1600,1000),(20,22,25));d=ImageDraw.Draw(sheet)
 for i,n in enumerate(frames):
  x=(i%2)*800;y=(i//2)*250;d.text((x+8,y),n,font=font,fill='white')
  im=Image.open(after/(n+'-hd.png')).convert('RGB');sheet.paste(im.resize((400,225),Image.Resampling.LANCZOS),(x,y+25))
  orig=Image.open(before/(n+'-hd.png')).convert('RGB');sheet.paste(orig.resize((400,225),Image.Resampling.LANCZOS),(x+400,y+25))
 sheet.save(dest/'all-views-after-before.png')
 print('Compared',len(classic),'classic frames; all exact:',all(a['exact'] for a in classic))
if __name__=='__main__':main()

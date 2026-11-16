from pipeline import *
before=R/'build/hd-wall-original-restore-20261116/after-v1';after=B/'after-v1';dest=B/'review';dest.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
names=['entrance','cave-18721','cave-22662','cave-27075','cave-27871']
for name in names:
 out=Image.new('RGB',(1920,580),(24,27,31));draw=ImageDraw.Draw(out)
 for x,title,folder in [(0,'До: синий оттенок оригинальной палитры',before),(960,'После: серый камень, прежняя геометрия',after)]:
  draw.text((x+16,7),title,font=font,fill='white');im=Image.open(folder/(name+'-hd.png')).convert('RGB');assert im.size==(1920,1080)
  out.paste(im.resize((960,540),Image.Resampling.LANCZOS),(x,40))
 out.save(dest/(name+'-comparison.png'))
classic=[]
for f in before.glob('*classic*.png'):
 g=after/f.name
 if g.exists():classic.append(dict(file=f.name,exact=np.array_equal(np.array(Image.open(f)),np.array(Image.open(g)))))
save(B/'comparison.json',dict(before=str(before.relative_to(R)),after=str(after.relative_to(R)),scale=.5,screenshot_color_correction=False,views=names,classic_frames=classic,classic_all_exact=bool(classic) and all(x['exact'] for x in classic)))
frames=['entrance','cave-16290','cave-18721','cave-22662','cave-24097','cave-27075','cave-27871','actor-behind']
sheet=Image.new('RGB',(1600,1000),(20,22,25));d=ImageDraw.Draw(sheet)
for i,n in enumerate(frames):
 x=(i%2)*800;y=(i//2)*250;d.text((x+8,y),n+' / grey | blue',font=font,fill='white')
 for dx,folder in [(0,after),(400,before)]:
  im=Image.open(folder/(n+'-hd.png')).convert('RGB');sheet.paste(im.resize((400,225),Image.Resampling.LANCZOS),(x+dx,y+25))
sheet.save(dest/'all-views.png')
print('Classic frames',len(classic),'all exact',all(x['exact'] for x in classic))

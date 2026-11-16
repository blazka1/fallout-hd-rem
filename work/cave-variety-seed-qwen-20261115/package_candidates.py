"""Package reviewed candidates only; never install them or allocate runtime IDs."""
from pathlib import Path
import shutil,json,sys
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
import pipeline as p
OUT=p.OUT;PACK=OUT/'candidate-pack';QA=OUT/'review'
def main():
    qa=p.read(QA/'asset-qa.json');assert qa['candidate_count']==66
    source={r['source']:r for r in p.read(OUT/'source-inventory.json')}
    choices=p.read(OUT/'qwen-selection.json');records=[]
    for m in qa['metrics']:
        assert m['exact_source_alpha'] and m['protected_rgb_unchanged']
        row=source[m['source']];kind='walls' if row['category']=='walls' else ('floor' if row['category']=='tiles' else ('formations' if m['panel']=='formations' else 'rocks'))
        rel=Path(kind)/(Path(m['source']).stem+'-'+m['variant']+'.png');dst=PACK/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        src=OUT/m['file'];assert p.sha(src)==m['sha256']
        if dst.exists():assert p.sha(dst)==m['sha256']
        else:shutil.copyfile(src,dst)
        records.append(dict(file=str(rel).replace('\\','/'),sha256=m['sha256'],source=m['source'],native_size=row['native'],size=m['size'],
            registration=row['registration'],source_sha256=row['source_sha256'],baseline_runtime_file=row['runtime_file'],baseline_runtime_sha256=row['runtime_sha256'],
            style=m['variant'],qwen_run=str(Path('qwen')/m['panel']/choices[m['panel']][m['variant']]),quality=m,
            status='material study; neighborhood transitions not approved for installation' if m['panel']=='floor' or m['panel'].startswith('wall') else 'candidate, not user approved or installed'))
    p.save(PACK/'manifest.json',dict(status='isolated candidate pack for visual selection',candidate_count=len(records),source_count=len(source),scale=4,
        scale_note='Final PNG canvas is native x4. Actual Qwen working resolution is recorded per job; no claim that resizing alone adds detail.',
        runtime_installed=False,runtime_ids_assigned=False,source_controls='../prepared/<group>/seed and seed-current',records=records))
    (PACK/'README.txt').write_text('66 кандидатов для художественного отбора. В игру не установлены.\nРазмер PNG = исходный холст ×4; альфа исходная. Регистрация в manifest.json.\nРекомендуемое количество используемых альтернатив после отбора: около 42, не обязательно все 66.\nГрафы, сырые генерации, контрольные основы SeedVR2 и сравнения находятся уровнем выше.\nДвижок не подключит этот каталог автоматически. Для вариантов камней/пола нужна отдельная доработка регистрации.\n',encoding='utf-8')
    # Two major repeated piles at identical x4 source density; no exposure corrections.
    cw=520;rh=510;sheet=Image.new('RGB',(cw*4,rh*2+65),(28,32,32));d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    for j,label in enumerate(['Текущая HD','A · сколы','B · слои','C · эрозия']):d.text((j*cw+18,14),label,font=font,fill='#e1ddce')
    for i,stem in enumerate(['rock03','rock06']):
        res=f'art/scenery/{stem}.frm';row=source[res]
        images=[Image.open(OUT/'sources'/(res+'.current.png')).convert('RGBA')]+[Image.open(PACK/'rocks'/f'{stem}-{v}.png').convert('RGBA') for v in 'abc']
        for j,im in enumerate(images):
            x=j*cw+(cw-im.width)//2;y=65+i*rh+(rh-im.height)//2
            sheet.paste(im,(x,y),im)
    sheet.save(QA/'rocks-main-comparison.png')
    p.save(QA/'source-integrity.json',{r['source']:dict(expected=r['runtime_sha256'],actual=p.sha(p.RUNTIME/r['runtime_file']),unchanged=p.sha(p.RUNTIME/r['runtime_file'])==r['runtime_sha256']) for r in source.values()})
    print(json.dumps(dict(pack=str(PACK),candidates=len(records))))
if __name__=='__main__':main()

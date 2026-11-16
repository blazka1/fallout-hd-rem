"""Publish a component report only after asset and isolated-engine checks pass."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,struct
from PIL import Image
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
P=R/'assets/hd/critter-rat/qwen21-seedvr2-v1-x4'
RT=R/'runtime/hd-rat-pilot';B=R/'build/hd-rat-20261115'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exe=sha(RT/'fallout-ce.exe');manifest=read(P/'manifest.json');qa=read(O/'review/asset-qa.json')
assert manifest['unique_images']==376 and manifest['world_animation_keys']==540
assert qa['prepared_unique']==376 and qa['failed']==0 and qa['aimed_technical_lines_exact']
reports={}
paths={'loaded':'preview/loaded-v4/manifest.json','missing_frame':'preview/missing-frame/manifest.json',
    'corrupt_frame':'preview/corrupt-frame/manifest.json','missing_aimed':'preview/missing-aimed/manifest.json',
    'corrupt_aimed':'preview/corrupt-aimed/manifest.json','world':'world-verified/manifest.json','menu':'menu-verified/manifest.json'}
for name,path in paths.items():
    p=B/path;j=read(p);result=j.get('result',j)
    assert j['executable_sha256'].lower()==exe,(name,'stale executable report')
    assert result['failed']==0,(name,'failed checks')
    reports[name]=dict(file=str(p.relative_to(R)).replace('\\','/'),passed=result['passed'],failed=result['failed'],sha256=sha(p))
loaded=read(B/'preview/loaded-v4/result.json')
assert loaded['world_frames']==540 and loaded['rendered_frames']==540 and loaded['missing_frames']==0
assert loaded['rat_keys']==540 and loaded['unique_loaded_frames']==375
for image in manifest['images']:
    png=P/'frames'/image['png'];rgba=RT/'data/art/hd/critter-rat'/image['runtime_file']
    assert sha(png)==image['png_sha256'] and sha(rgba)==image['runtime_sha256']
    decoded=Image.open(png).convert('RGBA');raw=rgba.read_bytes()
    assert struct.unpack('<4sIIII',raw[:20])==(b'F1HD',1,decoded.width,decoded.height,4)
    assert raw[20:]==decoded.tobytes()
manifest['status']='installed and checked in isolated hd-rat-pilot; visual test build'
manifest['executable_sha256']=exe
manifest['validation']=reports
(P/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
shutil.copy2(P/'manifest.json',RT/'data/art/hd/critter-rat/manifest.json')
report=dict(status='complete: full HD rat installed and checked in separate test build',
    created_utc=datetime.now(timezone.utc).isoformat(),component='Ordinary cave rat masrat, PID 0x01000030',
    qwen_panels=37,seedvr2_panels=37,prepared_base_panels=37,unique_images=376,world_animation_keys=540,
    aimed_diagram_images=1,all_original_directional_frames=546,runtime=str(RT.relative_to(R)),
    launcher='Start-Fallout-HD-Rat-Pilot.cmd',executable_sha256=exe,package=str(P.relative_to(R)),
    package_manifest_sha256=sha(P/'manifest.json'),asset_qa=dict(passed=qa['passed'],failed=0,
        report=str((O/'review/asset-qa.json').relative_to(R))),engine_reports=reports,
    checks_total=sum(v['passed'] for v in reports.values()),failed=0,original_dat_map_frm_modified=False,
    shared_runtime_modified_by_this_component=False,scope='Isolated snapshot; current main world runtime and later wall work were not replaced.',
    limits=['Existing cave floor boundary partial/full redraw differences are identical with the classic-rat control; HD rat introduces no additional differences.',
        'Automatic pose rendering and timed rat walking are checked; this is not a full combat playthrough.',
        'Original native-pixel world silhouette retained. Other creatures and maps are outside this component.'])
(B/'integration.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
state=dict(report,status='complete',resume_only_after_user_request=False,selected_package_created=True,hd_rat_assets_installed=True)
(W/'task.json').write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
text=f'''ОБЫЧНАЯ КРЫСА — ПОЛНЫЙ HD-НАБОР В ОТДЕЛЬНОМ ПИЛОТЕ

Статус: подключено и проверено в CE, отдельная тестовая сборка hd-rat-pilot.
Запуск из корня: Start-Fallout-HD-Rat-Pilot.cmd.
Сразу начинается новая игра в первой пещере; сохранения других runtime не меняются.
F11 переключает HD/оригинал мира. [remaster] hd_rat=0 отключает HD-крысу
после перезапуска. Игра допускает один экземпляр одновременно.

Qwen Image 2.1 и SeedVR2: 37/37 листов каждого этапа.
376 уникальных PNG x4: 375 игровых кадров и одна зелёная прицельная схема.
Все 540 исходных игровых сочетаний animation/direction/frame подключены.
Вместе с шестью ссылками на прицельную схему — 546 направленных кадров.
Оригинальные размеры, frame/direction offsets, FPS и action frame сохранены.
64 оригинальных FRM/FR0..FR5 и DAT/MAP не изменялись.

Выбранный пакет: assets/hd/critter-rat/qwen21-seedvr2-v1-x4.
PNG -> F1HD RGBA8 упакованы побайтно. Альфа игровых кадров — точная исходная
бинарная маска x4. Новая шерсть внутри тела, тонкие границы сохраняют исходный
цвет. Прицельная схема использует целую сетку Qwen, согласованную с исходным
зелёным цветом; её прямые линии наведения и внешний холст сохранены точно.
Выбрана prepared-aimed-v4; более ранние пробы сохранены, но не установлены.

Проверка ассетов: {qa['passed']} PASS, 0 FAIL.
Игровые отчёты: {json.dumps({k:v['passed'] for k,v in reports.items()},ensure_ascii=False)}; все 0 FAIL.
Проверены все 540 поз в настоящем SDL-рендере, 4K-кадр, реальная ходьба
через планировщик CE, отсутствие дополнительных следов относительно
классической крысы, красная обводка, настоящее окно
прицельной атаки и возврат к классике при отсутствии/повреждении кадров.
Это программные проверки и просмотр изображений, не полное прохождение боя.
Небольшие изменения пограничных ячеек пола при частичной перерисовке совпадают
с классическим контрольным прогоном. Этот прежний эффект окружения сохранён;
HD-крыса его не усиливает. Диагностика в preview/loaded-v4/*walk*.
EXE SHA256: {exe}
Отчёт: build/hd-rat-20261115/integration.json.

Исходники: work/hd-rat-20261115/source. Основные изменения: hd_rat.cc/.h,
подключение в hd_world_pilot и object.cc, прицельная схема в hd_hud/combat,
изолированный тест hd_rat_test.inc. Общий runtime пещеры этим компонентом
не заменялся. Пилот основан на сохранённом снимке окружения; более поздние
правки стен из других чатов не переносились автоматически.

Генерация и все job ID/workflow/API-prompt/history/хеши:
assets/generated/critter-rat/qwen21-seedvr2-v1-20261115.
Оригиналы и регистрация: source/raw, inventory.json.
Точные выбранные файлы: manifest.json пакета и selection.json генерации.
Сравнения и циклы анимаций: review/*.png, *.gif, *.webp.
Предыдущие паузы: pause-state.json, pause-history/. Они являются историей.
AGENTS.md / HD-TEXTURE-GUIDE.md не редактировались.
'''
for target in [W/'README.txt',O/'README.txt',P/'README.txt']:target.write_text(text,encoding='utf-8')
print(json.dumps(dict(status=report['status'],unique_images=376,world_frames=540,checks=report['checks_total'],failed=0,executable_sha256=exe)),flush=True)

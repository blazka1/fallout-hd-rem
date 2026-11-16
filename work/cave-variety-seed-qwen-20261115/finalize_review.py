"""Publish only the isolated review collection after generated assets and visual review exist."""
from pathlib import Path
import shutil
import pipeline as p
from new_geometry import GEO
import package_candidates,geometry_review

def main():
    geometry_review.review();package_candidates.main()
    qa=p.read(p.OUT/'review/asset-qa.json');geo=p.read(GEO/'review/geometry-qa.json')
    assert qa['candidate_count']==66 and geo['count']==16
    assert all(r['opaque_border_pixels']==0 and r['alpha_max_abs_change']<=1 for r in geo['records'])
    baseline=p.read(p.OUT/'review/baseline-check.json');integrity=p.read(p.OUT/'review/source-integrity.json')
    assert all(r['unchanged'] for r in baseline.values()) and all(r['unchanged'] for r in integrity.values())
    notes=p.read(p.OUT/'review/visual-review.json');assert notes['review_complete']
    pack=p.OUT/'candidate-pack';geopack=pack/'new-geometry';geopack.mkdir(exist_ok=True)
    records=[]
    for r in geo['records']:
        src=p.OUT/r['file'];dst=geopack/(r['id']+'.png');shutil.copyfile(src,dst)
        assert p.sha(dst)==r['sha256'];records.append({**r,'file':dst.name})
    p.save(geopack/'manifest.json',dict(count=16,original_alpha_reused=False,registration_status='new geometry: proposed anchors only; actual in-game footprint/lighting/occlusion untested',records=records))
    collection=dict(status='isolated comparison collection; not user selected or installed',total_candidate_png=82,material_variants=66,new_geometry_sprites=16,restored_original_controls=30,restored_current_hd_controls=30,
       manifests=['manifest.json','new-geometry/manifest.json'],source_controls='../prepared/<group>/seed and seed-current',runtime_writes=False,
       recommended_first_selection_scope=dict(new_rocks=12,new_formations=4,total_new_forms=16,wall_material_studies=12,floor_material_studies=8),
       recommendation_note='Prioritize selection among 16 new forms. The 20 wall/floor source pieces are material studies, not a seamless partial replacement: neighborhood review shows visible material mosaics. A chosen wall family needs a connected coverage pass across the 62 cave wall pieces, and floor needs neighboring transition tiles. All candidates remain uninstalled.')
    p.save(pack/'collection.json',collection)
    (pack/'README.txt').write_text('82 кандидата для сравнения: 66 вариантов материала и 16 совершенно новых по форме спрайтов.\nВ игру не установлены; пользовательский отбор ещё не выполнен.\nmanifest.json — 66 вариантов с исходной регистрацией и альфой.\nnew-geometry/manifest.json — 16 новых силуэтов и собственной альфой Qwen; опоры пока предложены, игровая регистрация не проверена.\ncollection.json — общая сводка. Контрольные SeedVR2-апскейлы находятся в ../prepared/.\nПосле уточнения пользователя первоочередной набор — 36 ассетов: 12 новых скал + 4 формации + 12 стен + 8 тайлов пола.\nЭто художественный план, а не автоматическое назначение на карту.\n',encoding='utf-8')
    index=p.OUT/'review/index.html';page=index.read_text(encoding='utf-8')
    block='''<section><h2>16 новых спрайтов с другой геометрией</h2><p>12 скал и 4 формации: другие пропорции, число вершин, пустоты и опоры. Исходные силуэты и маски не подставлялись. Это отдельные кандидаты; новые опоры, размеры в мире и перекрытия ещё требуют проверки в движке.</p><a href="../new-geometry/review/new-geometry-overview.png"><img src="../new-geometry/review/new-geometry-overview.png"></a><p><a href="../new-geometry/review/silhouette-comparison.png">Сравнение силуэтов без фактуры</a> · <a href="../new-geometry/review/alpha-review.png">Новая альфа на светлом и тёмном фоне</a> · <a href="../candidate-pack/new-geometry/manifest.json">16 PNG и параметры</a></p></section><section><h2>66 вариантов материала на старых формах</h2><p>Ниже — отдельная первоначальная серия. Она меняет материал внутри прежних контуров. Контрольный SeedVR2 исходников местами слишком гладкий и синий; это сравнение, а не рекомендация устанавливать его.</p></section>'''
    page=page.replace('<button onclick=',block+'<button onclick=',1)
    for title in ['Пол','Связанный участок стен 1','Связанный участок стен 3']:
        page=page.replace('<h2>'+title+'</h2>','<h2>'+title+'</h2><p class="note">Проба материала. В соседстве со старыми деталями видны переходы и мозаика фактур; к частичной установке не одобрено. Смотрите сборки соседних элементов ниже.</p>')
    page=page.replace('</main>','<p>Рекомендую начать будущую интеграцию с 36 ассетов: 12 новых скал, 4 новых формации, по одному согласованному варианту 12 стеновых фрагментов и 8 тайлов. Остальное — запас для отбора. Новых SDL-тестов не запускалось.</p><p><a href="../candidate-pack/collection.json">Сводка всех 82 кандидатов</a> · <a href="visual-review.json">Художественная оценка и ограничения</a></p></main>')
    index.write_text(page,encoding='utf-8')
    warning='Первый приоритет — отбор 16 новых форм. Пробы 12 стен и 8 тайлов показывают направление материала, но не готовы к частичной установке: в соседстве видна мозаика. Для выбранной стены нужен согласованный проход по семейству из 62 каменных фрагментов; для пола — по соседним переходам. Исходный ориентир 36 ассетов пересмотрен после этой проверки.'
    page=index.read_text(encoding='utf-8').replace('Рекомендую начать будущую интеграцию с 36 ассетов: 12 новых скал, 4 новых формации, по одному согласованному варианту 12 стеновых фрагментов и 8 тайлов. Остальное — запас для отбора.',warning)
    index.write_text(page,encoding='utf-8')
    (pack/'README.txt').write_text('82 кандидата: 66 вариантов материала и 16 новых по геометрии спрайтов. В игру не установлены.\nmanifest.json — материалы; new-geometry/manifest.json — новые формы; collection.json — общая сводка.\n'+warning+'\nНовые опоры в манифесте предварительные. Контрольные SeedVR2 находятся в ../prepared/.\n',encoding='utf-8')
    readme=p.OUT/'README.txt';s=readme.read_text(encoding='utf-8')
    s=s.replace('Статус: генерация и художественная проверка в процессе.','Статус: набор из 82 кандидатов подготовлен и просмотрен; художественный выбор пользователя впереди.')
    s=s.replace('когда эти файлы появятся. Наличие плана не означает выполнение всех его пунктов.','Эти отчёты созданы. Техническая проверка PNG не является игровой проверкой.')
    s=s.replace('План новых кандидатов:','Подготовлено вариантов материала:').replace('review/index.html — общий обзор (появится после подготовки).','review/index.html — общий обзор обеих серий.')
    s=s.replace('work/cave-variety-seed-qwen-20261115/run_batch.py','work/cave-variety-seed-qwen-20261115/run_full_batch.py')
    s+='\nУточнение пользователя: нужны кардинально новые силуэты\nПодготовлены ещё 16 спрайтов: 12 скал и 4 формации. Их генерация начинается\nс пустого холста; SeedVR2 текущей HD используется только как референс\nматериала и проекции. Исходные контуры и альфа не возвращаются.\nСкрипты new_geometry.py и geometry_review.py; результаты new-geometry/.\nИтого в candidate-pack/ — 82 PNG. Контрольные восстановления: 30 оригиналов\nи 30 текущих HD, отдельно в prepared/.\nПосле уточнения рекомендую начать будущий отбор с 36 ассетов: 16 новых\nформ + по одному варианту 12 стеновых фрагментов и 8 тайлов пола.\nОстальные кандидаты оставлены как альтернативы. Это пересмотр первоначального\nориентира около 42 материалов в пользу реального разнообразия геометрии.\nНовые формы имеют собственную мягкую альфу. В манифесте указан лишь\nпредлагаемый bottom-center; игровая опора, блокеры, свет и перекрытия\nдолжны быть проверены при отдельной интеграции.\n'
    readme.write_text(s,encoding='utf-8')
    s=readme.read_text(encoding='utf-8')
    start=s.find('После уточнения рекомендую начать будущий отбор с 36 ассетов:')
    end=s.find('Новые формы имеют собственную мягкую альфу.',start)
    if start>=0 and end>start:s=s[:start]+s[end:]
    s+='\nИТОГ ПРОВЕРКИ СОСЕДСТВА (уточняет ранние ориентиры выше)\n'+warning+'\nТочные края/альфа прошли технические проверки, но художественные переходы стен и пола не прошли отбор для установки.\nНовые формы имеют квантование мягкой альфы ComfyUI максимум на 1/255; исходная маска игры не подставлялась.\n'
    readme.write_text(s,encoding='utf-8')
    task=p.read(Path(__file__).parent/'task.json');task.update(status='complete: separate candidate collection and comparisons, no installation',running_at_checkpoint=[],remaining=[],plan='30 source resources restored; 66 material candidates plus 16 new geometry candidates. Prioritize the 16 new forms; wall/floor materials require coherent neighborhood coverage before any installation.',
       completed=['Guides and updated AGENTS read and baseline verified','30 original SeedVR2 x4 controls and 30 current-HD SeedVR2 controls','66 material alternatives generated, registered and checked','16 radically new geometry sprites generated with their own alpha','Visual comparisons, silhouettes, light/dark backgrounds and real-neighbor QA assemblies reviewed','82 PNG candidate pack and manifests; runtime baseline unchanged'],
       latest_steering='User explicitly requested radically different geometry; added 12 new rocks and 4 formations. Separate comparison scope remains.',output_counts=collection)
    p.save(Path(__file__).parent/'task.json',task)
    p.save(p.OUT/'review/completion.json',dict(complete=True,candidate_png=82,original_controls=30,current_hd_controls=30,baseline_files_unchanged=len(baseline),terrain_runtime_files_unchanged=len(integrity),engine_tests_run=False,installed=False))
    print('Complete isolated collection: 82 candidate PNG, 60 SeedVR2 controls, comparisons, unchanged baseline.')

if __name__=='__main__':main()

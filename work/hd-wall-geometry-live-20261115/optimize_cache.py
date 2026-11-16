"""Avoid invalidating opaque wall pixels when only their hidden background changed."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
source = work / 'source/src/game'
shared = root / 'work/hd-world-pilot/fallout1-ce-main/src/game'

def edit(name, changes):
    p = source / name
    assert p.read_bytes() == (shared / name).read_bytes(), ('Concurrent source change', name)
    backup = work / 'before-cache-optimization' / name
    assert not backup.exists(), ('Already patched', name)
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(p, backup)
    text = p.read_text(encoding='utf-8')
    for old, new in changes:
        assert text.count(old) == 1, (name, old[:80], text.count(old))
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    shutil.copy2(p, shared / name)

edit('hd_cave_variety.inc', [
('    std::vector<unsigned char> geometryRgba;',
 '    std::vector<unsigned char> geometryRgba;\n    // Native cell coverage: 0 empty, 1 mixed, 2 fully opaque at all 16 subpixels.\n    std::vector<unsigned char> geometryCoverage;'),
('''                const size_t uv=((size_t(texel/p.oldWidth)*4)*p.oldWidth*4+(texel%p.oldWidth)*4)*4;
                bool empty=true;
                for(int sy=0;sy<4 && empty;++sy) for(int sx=0;sx<4;++sx)
                    if(p.geometryRgba[uv+(size_t(sy)*p.oldWidth*4+sx)*4+3]) {empty=false;break;}
                if(empty) continue;''',
 '''                if(p.geometryCoverage[texel]==0) continue;'''),
])
edit('hd_wall_geometry.inc', [
('''        p.under.resize(size_t(p.width())*p.height());p.opacity.resize(p.under.size(),255);
        cavePlacements.push_back(std::move(p));''',
 '''        p.under.resize(size_t(p.width())*p.height());p.opacity.resize(p.under.size(),255);
        p.geometryCoverage.resize(p.under.size());
        for(size_t t=0;t<p.under.size();++t) {
            int minimum=255,maximum=0;
            const size_t origin=((t/p.oldWidth*4)*p.oldWidth*4+t%p.oldWidth*4)*4;
            for(int sy=0;sy<4;++sy) for(int sx=0;sx<4;++sx) {
                int alpha=p.geometryRgba[origin+(size_t(sy)*p.oldWidth*4+sx)*4+3];
                minimum=std::min(minimum,alpha);maximum=std::max(maximum,alpha);
            }
            p.geometryCoverage[t]=minimum==255?2:maximum==0?0:1;
        }
        cavePlacements.push_back(std::move(p));'''),
])
edit('hd_world_pilot.cc', [
('std::vector<unsigned char> presentedLights;',
 'std::vector<unsigned char> presentedLights;\nstd::vector<unsigned char> presentedCaveOpacity;'),
('        memmove(presentedLights.data() + target, presentedLights.data() + origin, copyWidth);',
 '        memmove(presentedLights.data() + target, presentedLights.data() + origin, copyWidth);\n        memmove(presentedCaveOpacity.data() + target, presentedCaveOpacity.data() + origin, copyWidth);'),
('        std::fill_n(presentedLights.data() + row + right, width - right, 128);',
 '        std::fill_n(presentedLights.data() + row + right, width - right, 128);\n        std::fill_n(presentedCaveOpacity.data() + row, left, 255);\n        std::fill_n(presentedCaveOpacity.data() + row + right, width - right, 255);'),
('    presentedLights.clear();', '    presentedLights.clear();\n    presentedCaveOpacity.clear();'),
('        presentedLights.resize(static_cast<size_t>(width) * height, 128);',
 '        presentedLights.resize(static_cast<size_t>(width) * height, 128);\n        presentedCaveOpacity.resize(static_cast<size_t>(width) * height, 255);'),
('''            // Actor colour also depends on the captured underlying pixel.''',
 '''            unsigned char caveOpacity=255;
            bool changedCaveCell=caveBackgroundChanged && isCaveOwner(owner>>24);
            if((owner>>24)==253) {
                unsigned int i=caveIndex(owner),t=caveTexel(owner);
                if(i<cavePlacements.size() && t<cavePlacements[i].opacity.size()) {
                    const auto& p=cavePlacements[i];caveOpacity=p.opacity[t];
                    // Opaque geometry cannot depend on its captured background.
                    // Retain both previous/current opacity so entering AND leaving
                    // the player's transparency egg still invalidate the cell.
                    if(p.geometryCoverage[t]==2 && caveOpacity==255
                        && presentedCaveOpacity[cacheRow+x]==255) changedCaveCell=false;
                }
            }
            // Actor colour also depends on the captured underlying pixel.'''),
('                && !(caveBackgroundChanged && isCaveOwner(owner >> 24))',
 '                && !changedCaveCell'),
('            oldLight = light;\n            dirtyLeft',
 '            oldLight = light;\n            presentedCaveOpacity[cacheRow+x]=caveOpacity;\n            dirtyLeft'),
])
print('Patched isolated and shared source; original release backups preserved.')

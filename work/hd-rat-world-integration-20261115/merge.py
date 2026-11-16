"""Apply the reviewed rat changes to the fresh world source, preserving wall work."""
from pathlib import Path
import difflib, hashlib, json
R=Path(__file__).resolve().parents[2]
S=R/'work/hd-world-pilot/fallout1-ce-main'
RAT=R/'work/hd-rat-20261115/source'
B=R/'build/hd-rat-world-integration-20261115'
baseline=json.loads((B/'baseline.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in baseline['source'].items():
    assert sha(S/name)==digest, ('Source changed since snapshot',name)
changes={};pending={}
def current(name):
    return pending[name] if name in pending else (S/name).read_text()
def write(name,text):
    p=S/name;old=p.read_text() if p.exists() else ''
    if old==text:return
    changes[name]=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='before/'+name,tofile='after/'+name))
    pending[name]=text
def edit(name,old,new,count=1):
    text=current(name);assert text.count(old)==count,(name,old,text.count(old))
    write(name,text.replace(old,new))

# These reviewed deltas contain only the rat hook/UI/test additions, no wall changes.
for name in ['CMakeLists.txt','src/game/combat.cc','src/game/combat.h','src/game/hd_hud.cc',
             'src/game/hd_player_test.cc','src/game/hd_player_test.h','src/game/main.cc','src/game/object.cc']:
    old=(S/name).read_text();new=(RAT/name).read_text()
    result=old.splitlines(True)
    opcodes=difflib.SequenceMatcher(None,result,new.splitlines(True),autojunk=False).get_opcodes()
    donor=new.splitlines(True)
    for tag,i,j,k,l in reversed(opcodes):
        if tag!='equal':result[i:j]=donor[k:l]
    write(name,''.join(result))

for name in ['src/game/hd_rat.cc','src/game/hd_rat.h','src/game/hd_rat_test.inc']:
    assert not (S/name).exists();write(name,(RAT/name).read_text())
edit('src/game/hd_rat.h','namespace fallout {','namespace fallout {\n// 253 belongs to the current connected cave walls.\nconstexpr unsigned int kHdRatOwner = 254;')
edit('src/game/hd_rat_test.inc','253','kHdRatOwner',3)

name='src/game/hd_world_pilot.cc'
edit(name,'#include "game/hd_player.h"','#include "game/hd_player.h"\n#include "game/hd_rat.h"')
edit(name,'int currentAsset = 0;','int currentAsset = 0;\nint currentRatFrame = -1;')
rat=(RAT/name).read_text()
sample=rat[rat.index('constexpr uint32_t kRatOwner'):rat.index('Asset skeletonAsset;')]
sample=sample.replace('kRatOwner = 253','kRatOwner = kHdRatOwner')
edit(name,'Asset skeletonAsset;',sample+'Asset skeletonAsset;')
edit(name,'id == kSkeletonOwner || width == 0','id == kSkeletonOwner || id == kRatOwner || width == 0')
edit(name,'id == kPlayerOwner || id == kSkeletonOwner\n','id == kPlayerOwner || id == kSkeletonOwner || id == kRatOwner\n')
edit(name,'    if (!currentAsset || offset >= currentSize || *p == 0 || *p >= 229) return 0;',
    '    if (currentRatFrame >= 0 && offset < currentSize && *p > 0 && *p < 229)\n'
    '        return (kRatOwner << 24) | (static_cast<uint32_t>(currentRatFrame) << 14) | static_cast<uint32_t>(offset);\n'
    '    if (!currentAsset || offset >= currentSize || *p == 0 || *p >= 229) return 0;')
edit(name,'void hdWorldEndArt()\n{\n    currentAsset = 0;',
    'void hdWorldEndArt()\n{\n    currentAsset = 0;\n    currentRatFrame = -1;')
begin=rat[rat.index('void hdWorldBeginRat('):rat.index('void hdWorldFillVaultTerminalRecess(')]
edit(name,'void hdWorldFillVaultTerminalRecess(',begin+'void hdWorldFillVaultTerminalRecess(')
edit(name,'    if (currentAsset && artOffset < currentSize) {',
    '    if (currentRatFrame >= 0 && artOffset < currentSize && *source > 0 && *source < 229) {\n'
    '        target->owners[offset] = (kRatOwner << 24) | (static_cast<uint32_t>(currentRatFrame) << 14) | static_cast<uint32_t>(artOffset);\n'
    '        target->lights[offset] = static_cast<unsigned char>(std::clamp(light, 0, 255));\n'
    '    } else if (currentAsset && artOffset < currentSize) {')
edit(name,'} else if (!currentAsset && !transparent) {','} else if (!currentAsset && currentRatFrame < 0 && !transparent) {')
edit(name,'= currentAsset ? artOwner(s + x) : 0;','= (currentAsset || currentRatFrame >= 0) ? artOwner(s + x) : 0;')
edit(name,'\n    if (isCaveOwner(underId)) {',
    '\n    if (underId == kRatOwner) {\n        sampleRat(saved.owner, saved.light, subX, subY, color);\n    } else if (isCaveOwner(underId)) {',2)
edit(name,'                        if (isCaveOwner(underId)) {',
    '                        if (underId == kRatOwner) {\n'
    '                            sampleRat(underOwner, underLight, samples[sx], samples[sy], bg);\n'
    '                        } else if (isCaveOwner(underId)) {')
start=rat.index('            if (id == kRatOwner) {',rat.index('bool hdWorldRender()'))
end=rat.index('            if (isCaveOwner(id)) {',start)
edit(name,'            if (isCaveOwner(id)) {',rat[start:end]+'            if (isCaveOwner(id)) {')
edit('src/game/hd_world_pilot.h','void hdWorldEndArt();',
    'void hdWorldEndArt();\nvoid hdWorldBeginRat(const Object* object, const unsigned char* source, int width, int height);')
edit('src/game/hd_cave_variety.inc','    if(isCaveOwner(id)) {sampleCave(screen,at,saved.owner,saved.light,sx,sy,palette,color,depth+1);return;}',
    '    if(id==kRatOwner) {sampleRat(saved.owner,saved.light,sx,sy,color);return;}\n'
    '    if(isCaveOwner(id)) {sampleCave(screen,at,saved.owner,saved.light,sx,sy,palette,color,depth+1);return;}')

# Do not replace the contemporary world regression or wall geometry include.
assert sha(S/'src/game/hd_world_pilot_test.cc')==baseline['source']['src/game/hd_world_pilot_test.cc']
assert sha(S/'src/game/hd_wall_geometry.inc')==baseline['source']['src/game/hd_wall_geometry.inc']
assert 'loadWallGeometry();' in current(name)
for rel,digest in baseline['source'].items():assert sha(S/rel)==digest,rel
for rel,text in pending.items():
    with (S/rel).open('w',encoding='utf-8',newline='\n') as f:f.write(text)
(B/'source-merge.diff').write_text('\n'.join(changes.values()),encoding='utf-8')
(B/'source-merge.json').write_text(json.dumps(dict(changed_files=list(changes),rat_owner=254,wall_owner=253,
    source_hashes={p.relative_to(S).as_posix():sha(p) for p in S.rglob('*') if p.is_file()}),indent=2)+'\n')
print(json.dumps(dict(changed_files=list(changes),rat_owner=254,wall_geometry_preserved=True)))

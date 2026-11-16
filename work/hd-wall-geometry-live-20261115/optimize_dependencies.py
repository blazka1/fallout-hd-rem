from pathlib import Path
import shutil
w=Path(__file__).resolve().parent
s=w/'source/src/game'
shared=w.parents[1]/'work/hd-world-pilot/fallout1-ce-main/src/game'
shutil.copy2(w/'before-profile.cc',s/'hd_world_pilot.cc')
shutil.copy2(w/'before-profile.inc',s/'hd_cave_variety.inc')
def edit(name,changes):
 p=s/name
 assert p.read_bytes()==(shared/name).read_bytes(),name
 backup=w/'before-dependency-optimization'/name
 assert not backup.exists()
 backup.parent.mkdir(exist_ok=True);shutil.copy2(p,backup)
 text=p.read_text()
 for old,new in changes:
  assert text.count(old)==1,(name,old[:80],text.count(old))
  text=text.replace(old,new)
 p.write_text(text);shutil.copy2(p,shared/name)
edit('hd_cave_variety.inc',[
('    std::vector<unsigned char> opacity;', '    std::vector<unsigned char> opacity;\n    std::vector<unsigned char> changedCells;'),
('static std::vector<CavePlacement> cavePlacements;', 'static std::vector<CavePlacement> cavePlacements;\nstatic std::vector<std::pair<size_t,size_t>> caveChangedCells;'),
('''// Diagnostic used by compositing checks:''', '''static void markCaveCellChanged(size_t i,size_t t)
{
    auto& p=cavePlacements[i];
    if(!p.changedCells[t]) {
        p.changedCells[t]=1;caveChangedCells.emplace_back(i,t);++caveRevision;
    }
}
static bool caveCellNeedsRefresh(uint32_t owner,int depth=0)
{
    if(!isCaveOwner(owner>>24) || depth>16) return false;
    unsigned int i=caveIndex(owner),t=caveTexel(owner);
    if(i>=cavePlacements.size() || t>=cavePlacements[i].under.size()) return false;
    const auto& p=cavePlacements[i];
    if(p.changedCells[t]) return true;
    const auto& bg=p.under[t];
    if(caveCellNeedsRefresh(bg.pixel.owner,depth+2)) return true;
    const auto id=bg.pixel.owner>>24;
    return (id==kPlayerOwner && caveCellNeedsRefresh(bg.player.owner,depth+2))
        || (id==kSkeletonOwner && caveCellNeedsRefresh(bg.skeleton.owner,depth+2));
}
static void clearCaveChanges()
{
    for(const auto& cell:caveChangedCells) cavePlacements[cell.first].changedCells[cell.second]=0;
    caveChangedCells.clear();
}

// Diagnostic used by compositing checks:'''),
('        p.opacity.resize(p.under.size(),255); cavePlacements.push_back(std::move(p));',
 '        p.opacity.resize(p.under.size(),255);p.changedCells.resize(p.under.size()); cavePlacements.push_back(std::move(p));'),
('{old=bg;++caveRevision;}', '{old=bg;markCaveCellChanged(i,t);}'),
('if(p.opacity[t]!=255) {p.opacity[t]=255;++caveRevision;}', 'if(p.opacity[t]!=255) {p.opacity[t]=255;markCaveCellChanged(i,t);}'),
('if(p.opacity[t]!=alpha) {p.opacity[t]=alpha;++caveRevision;}', 'if(p.opacity[t]!=alpha) {p.opacity[t]=alpha;markCaveCellChanged(caveDraw.frame,t);}'),
])
edit('hd_wall_geometry.inc',[
('        p.geometryCoverage.resize(p.under.size());','        p.geometryCoverage.resize(p.under.size());p.changedCells.resize(p.under.size());'),
])
edit('hd_world_pilot.cc',[
('bool changedCaveCell=caveBackgroundChanged && isCaveOwner(owner>>24);',
 'bool changedCaveCell=caveBackgroundChanged && owner==oldOwner && caveCellNeedsRefresh(owner);'),
('    // Initial texture memory is undefined;',
 '    clearCaveChanges();\n    // Initial texture memory is undefined;'),
])
print('Per-cell dependency invalidation installed in both source copies.')

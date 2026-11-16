from pathlib import Path
import shutil
w=Path(__file__).resolve().parent
s=w/'source/src/game';shared=w.parents[1]/'work/hd-world-pilot/fallout1-ce-main/src/game'
def edit(name,changes):
 p=s/name
 assert p.read_bytes()==(shared/name).read_bytes(),name
 text=p.read_text()
 for old,new in changes:
  assert text.count(old)==1,(name,old[:80],text.count(old));text=text.replace(old,new)
 p.write_text(text);shutil.copy2(p,shared/name)
edit('hd_cave_variety.inc',[
('static void markCaveCellChanged(size_t i,size_t t)', 'static void markCaveCellChanged(size_t i,size_t t,unsigned char flags=1)'),
('''        p.changedCells[t]=1;caveChangedCells.emplace_back(i,t);++caveRevision;
    }
}''', '''        caveChangedCells.emplace_back(i,t);++caveRevision;
    }
    p.changedCells[t]|=flags;
}'''),
('''    if(p.changedCells[t]) return true;
    const auto& bg=p.under[t];''', '''    // Hidden background changes cannot affect an opaque wall, including
    // walls reached through a transparent foreground prop's saved layer.
    if(p.assetId==253 && p.geometryCoverage[t]==2 && p.opacity[t]==255
        && !(p.changedCells[t]&2)) return false;
    if(p.changedCells[t]) return true;
    const auto& bg=p.under[t];'''),
('''    return (id==kPlayerOwner && caveCellNeedsRefresh(bg.player.owner,depth+2))
        || (id==kSkeletonOwner && caveCellNeedsRefresh(bg.skeleton.owner,depth+2));''', '''    return (id==kPlayerOwner && caveCellNeedsRefresh(bg.player.owner,depth+2))
        || ((id==kPlayerOwner || id==kSkeletonOwner) && caveCellNeedsRefresh(bg.skeleton.owner,depth+2));'''),
('p.opacity[t]=255;markCaveCellChanged(i,t);', 'p.opacity[t]=255;markCaveCellChanged(i,t,2);'),
('p.opacity[t]=alpha;markCaveCellChanged(caveDraw.frame,t);', 'p.opacity[t]=alpha;markCaveCellChanged(caveDraw.frame,t,2);'),
])
edit('hd_world_pilot.cc',[
('''            if (isCaveOwner(id)) {
                for (int sy=0;sy<density;++sy) {''', '''            if(id==253) {
                const unsigned int i=caveIndex(owner),t=caveTexel(owner);
                if(i<cavePlacements.size() && t<cavePlacements[i].opacity.size()) {
                    const auto& p=cavePlacements[i];
                    if(p.geometryCoverage[t]==2 && p.opacity[t]==255) {
                        const int u=(t%p.oldWidth)*4,v=(t/p.oldWidth)*4;
                        const auto* reds=lightColors[0][light];const auto* greens=lightColors[1][light];const auto* blues=lightColors[2][light];
                        for(int sy=0;sy<density;++sy) {
                            auto* row=overlayPixels.data()+size_t(y*density+sy)*overlayWidth+x*density;
                            const auto* srcRow=p.geometryRgba.data()+(size_t(v+samples[sy])*p.oldWidth*4+u)*4;
                            for(int sx=0;sx<density;++sx) {
                                const auto* src=srcRow+samples[sx]*4;
                                row[sx]=0xFF000000|(uint32_t(reds[src[0]])<<16)|(uint32_t(greens[src[1]])<<8)|blues[src[2]];
                            }
                        }
                        continue;
                    }
                }
            }
            if (isCaveOwner(id)) {
                for (int sy=0;sy<density;++sy) {'''),
])
edit('hd_world_pilot_test.cc',[
('''    Capture hdVisible = capture(directory / (name + "-hd.bmp"), true);
    compare(report, before, snapshot({}), name + " HD toggle");''', '''    Capture hdVisible = capture(directory / (name + "-hd.bmp"), true);
    hdWorldReleaseTextures();tile_refresh_display();
    const Capture freshVisible=capture({},true);
    report.check(hdVisible.valid && freshVisible.valid && hdVisible.pixels==freshVisible.pixels,
        name+" actor arrival / transparency cache matches uncached frame");
    compare(report, before, snapshot({}), name + " HD toggle");'''),
('''    Capture hdHidden = capture({}, true);
    obj_dude->flags = flags;''', '''    Capture hdHidden = capture({}, true);
    hdWorldReleaseTextures();tile_refresh_display();
    const Capture freshHidden=capture({},true);
    report.check(hdHidden.valid && freshHidden.valid && hdHidden.pixels==freshHidden.pixels,
        name+" actor departure / background cache matches uncached frame");
    obj_dude->flags = flags;'''),
])
print('Final opaque fast path, exact dirty dependencies and actor cache regression ready.')

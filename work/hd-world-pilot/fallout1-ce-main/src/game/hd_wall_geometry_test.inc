void wallGeometryRegression(const std::filesystem::path& output, Report& report)
{
    if(!hdWorldWallGeometryEnabled() || !hdWorldWallGeometryCount()) return;
    const int center=tile_center_tile;const Snapshot before=snapshot({});
    std::vector<Object*> assigned;std::set<int> fids,seen;
    for(auto* o:objects()) if(hdWorldCaveAssetForObject(o)==253) {
        assigned.push_back(o);fids.insert(o->fid);
        Object copy=*o;copy.tile=(copy.tile+1)%40000;
        report.check(hdWorldCaveAssetForObject(&copy)!=253,"wall identity registration "+std::to_string(o->id));
    }
    report.check(assigned.size()==417 && hdWorldWallGeometryCount()==417,"417 exact wall placements loaded; approved door remains separate");
    report.check(fids.size()==62,"all 62 cave wall resource types have registered geometry");
    int captures=0;
    for(auto* o:assigned) {
        if(seen.count(o->fid)) continue;
        tile_set_center(o->tile,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);tile_refresh_display();
        const unsigned int index=hdWorldCavePlacementForObject(o);
        int cells=0;for(auto owner:worldOwners()) if((owner>>24)==253 && ((owner>>15)&511)==index) ++cells;
        if(!cells) continue;
        seen.insert(o->fid);
        const auto originalPixels=worldPixels();
        Capture on=capture(captures++<6?output/("wall-geometry-"+std::to_string(o->fid)+".bmp"):std::filesystem::path{},true);
        Capture classic=capture({},false);
        hdWorldSetWallGeometryEnabled(false);tile_refresh_display();
        Capture off=capture({},true);Capture classicOff=capture({},false);
        report.check(originalPixels==worldPixels() && classic.pixels==classicOff.pixels,"wall geometry preserves classic pixels / F11 "+std::to_string(o->fid));
        report.check(on.valid && off.valid && on.pixels!=off.pixels,"registered geometry appears in SDL "+std::to_string(o->fid));
        hdWorldSetWallGeometryEnabled(true);tile_refresh_display();
        Capture again=capture({},true);hdWorldReleaseTextures();tile_refresh_display();Capture fresh=capture({},true);
        report.check(on.pixels==again.pixels && again.pixels==fresh.pixels,"wall geometry cached / fresh frames agree "+std::to_string(o->fid));
    }
    report.check(seen==fids,"every wall resource family seen in actual renderer");
    tile_set_center(center,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    compare(report,before,snapshot({}),"registered wall geometry does not alter map objects or collision");
}

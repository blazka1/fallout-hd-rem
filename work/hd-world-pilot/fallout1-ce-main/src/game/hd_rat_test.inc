// Included in the existing actor harness to reuse its real SDL capture helpers.
static std::filesystem::path ratAimPath;
static Capture ratAimCapture;
static void captureRatAimedDialog() { ratAimCapture = capture(ratAimPath); }

struct RatWalkDelta {
    bool valid=false;
    std::vector<std::array<uint32_t,3>> pixels;
};
static RatWalkDelta timedRatWalk(Report& report, Object* rat, const std::filesystem::path& output, bool hd)
{
    RatWalkDelta delta;
    std::filesystem::create_directories(output);
    const int savedCenter=tile_center_tile;
    hdRatSetEnabled(hd);
    tile_set_center(rat->tile,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    const Object saved=*rat;int destination=-1,pathLength=0;
    for(int distance=5;distance>=3 && destination<0;--distance) for(int d=0;d<6 && destination<0;++d) {
        const int tile=tile_num_in_direction(saved.tile,d,distance);
        if(!hexGridTileIsValid(tile)||obj_blocking_at(rat,tile,rat->elevation))continue;
        unsigned char path[2000] {};const int length=make_path(rat,saved.tile,tile,path,1);
        if(length>=3 && length<=8){destination=tile;pathLength=length;}
    }
    report.check(destination>=0,"rat has an original multi-hex walk path");
    if(destination<0) {
        tile_set_center(savedCenter,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        return delta;
    }
    register_clear(rat);
    const int begin=register_begin(ANIMATION_REQUEST_UNRESERVED);
    const int queued=begin==0?register_object_move_to_tile(rat,destination,rat->elevation,-1,0):-1;
    const int committed=queued==0?register_end():-1;
    report.check(committed==0,"CE animation scheduler accepts the HD rat walk");
    std::ofstream samples(output/"timed-rat-walk.tsv");samples<<"elapsed_ms\ttile\tx\ty\tdirection\tframe\tanimation\thd_index\n";
    const uint32_t start=SDL_GetTicks();std::set<int> framesSeen,tilesSeen;int visible=0,previousTile=-1,previousFrame=-1;
    while(committed==0 && SDL_GetTicks()-start<15000) {
        SDL_Delay(10);object_animate();
        if(rat->tile!=previousTile || rat->frame!=previousFrame) {
            const auto frame=capture();
            if(FID_ANIM_TYPE(rat->fid)==ANIM_WALK) {
                framesSeen.insert(rat->frame);tilesSeen.insert(rat->tile);
                if(frame.valid && (!hd || (hdRatResolve(rat)>=0 && hdWorldVisiblePixels(kHdRatOwner)>0)))++visible;
            }
            samples<<(SDL_GetTicks()-start)<<'\t'<<rat->tile<<'\t'<<rat->x<<'\t'<<rat->y<<'\t'<<rat->rotation<<'\t'<<rat->frame<<'\t'<<(FID_ANIM_TYPE(rat->fid))<<'\t'<<hdRatResolve(rat)<<'\n';
            previousTile=rat->tile;previousFrame=rat->frame;
        }
        if(anim_busy(rat)==0)break;
    }
    report.check(rat->tile==destination && anim_busy(rat)==0,"real timed rat walk reaches destination across "+std::to_string(pathLength)+" hexes");
    report.check(framesSeen.size()>=3 && tilesSeen.size()>=3 && visible>=5,"real scheduler displays multiple rat walk frames and tiles");
    const auto incremental=capture(output/"rat-walk-ended.bmp");
    const int nativeWidth=gSdlSurface->w,nativeHeight=gSdlSurface->h,pitch=gSdlSurface->pitch;
    auto* surface=static_cast<unsigned char*>(gSdlSurface->pixels);
    std::vector<uint32_t> beforeOwners(size_t(nativeWidth)*nativeHeight);
    std::vector<unsigned char> beforeIndices(beforeOwners.size()),beforeLights(beforeOwners.size());
    for(int y=0;y<nativeHeight;++y)for(int x=0;x<nativeWidth;++x) {
        const size_t at=size_t(y)*nativeWidth+x;const auto* pixel=surface+y*pitch+x;
        beforeOwners[at]=hdWorldOwnerAt(pixel);beforeIndices[at]=*pixel;beforeLights[at]=hdWorldLightAt(pixel);
    }
    tile_refresh_display();
    const auto rebuilt=capture(output/"rat-walk-rebuilt.bmp");
    size_t changed=0;int left=rebuilt.width,top=rebuilt.height,right=0,bottom=0;
    if(incremental.valid && rebuilt.valid) for(int y=0;y<rebuilt.height;++y)for(int x=0;x<rebuilt.width;++x) {
        const size_t at=size_t(y)*rebuilt.width+x;
        if(rebuilt.pixels[at]!=incremental.pixels[at]) {
            ++changed;left=std::min(left,x);top=std::min(top,y);right=std::max(right,x+1);bottom=std::max(bottom,y+1);
            delta.pixels.push_back({static_cast<uint32_t>(at),incremental.pixels[at],rebuilt.pixels[at]});
        }
    }
    std::ofstream diagnostic(output/"rat-walk-difference.json");
    diagnostic<<"{\"changed\":"<<changed<<",\"box\":["<<left<<','<<top<<','<<right<<','<<bottom<<"]}\n";
    std::ofstream cells(output/"rat-walk-changed-cells.tsv");cells<<"x\ty\told_owner\tnew_owner\told_index\tnew_index\told_light\tnew_light\n";
    for(int y=0;y<nativeHeight;++y)for(int x=0;x<nativeWidth;++x) {
        bool different=false;
        for(int py=y*rebuilt.height/nativeHeight;py<(y+1)*rebuilt.height/nativeHeight;++py)
            for(int px=x*rebuilt.width/nativeWidth;px<(x+1)*rebuilt.width/nativeWidth;++px)
                different|=rebuilt.pixels[size_t(py)*rebuilt.width+px]!=incremental.pixels[size_t(py)*rebuilt.width+px];
        if(different) {
            const size_t at=size_t(y)*nativeWidth+x;const auto* pixel=surface+y*pitch+x;
            cells<<x<<'\t'<<y<<'\t'<<beforeOwners[at]<<'\t'<<hdWorldOwnerAt(pixel)<<'\t'<<int(beforeIndices[at])<<'\t'<<int(*pixel)<<'\t'<<int(beforeLights[at])<<'\t'<<int(hdWorldLightAt(pixel))<<'\n';
        }
    }
    delta.valid=incremental.valid && rebuilt.valid;
    report.check(delta.valid,"timed rat walk partial/full comparison captures are valid");
    register_clear(rat);Rect dirty;
    obj_move_to_tile(rat,saved.tile,saved.elevation,&dirty);obj_change_fid(rat,saved.fid,&dirty);
    obj_set_rotation(rat,saved.rotation,&dirty);obj_set_frame(rat,saved.frame,&dirty);
    obj_offset(rat,saved.x-rat->x,saved.y-rat->y,&dirty);rat->flags=saved.flags;rat->outline=saved.outline;tile_refresh_display();
    tile_set_center(savedCenter,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    return delta;
}

int hdRatPreview(const char* directory)
{
    const std::filesystem::path output(directory);
    std::filesystem::create_directories(output);
    Report report(output);
    map_disable_bk_processes(); scr_disable(); cycle_disable(); gmouse_disable_scrolling(); mouse_hide();
    hdWorldSetTerminalPreviewPhase(0);
    const int expected = SDL_getenv("FALLOUT_HD_RAT_EXPECT_KEYS") ? std::atoi(SDL_getenv("FALLOUT_HD_RAT_EXPECT_KEYS")) : 540;
    const bool expectedAim=SDL_getenv("FALLOUT_HD_RAT_EXPECT_AIMED") ? std::atoi(SDL_getenv("FALLOUT_HD_RAT_EXPECT_AIMED"))!=0 : expected!=0;
    report.check(hdRatRegisteredKeyCount() == expected, "rat registry expected complete or fallback key count");
    report.check(expected==540 ? hdRatLoadedFrameCount()==375 : hdRatLoadedFrameCount()<=375, "unique rat cache complete, bounded and deduplicated");
    std::vector<Object*> rats;
    for (auto* object : allObjects()) if (object->pid == 0x01000030 && (object->fid & 0xFFF) == 24) rats.push_back(object);
    report.check(rats.size() == 20, "all twenty original ordinary cave rats retained");
    if (rats.empty()) return 42;
    const auto originalBlockers = blockers();
    const int center = tile_center_tile;
    Object* rat = rats.front();
    hdWorldSetEnabled(true);hdPlayerSetEnabled(true);hdRatSetEnabled(true);
    if(expected>0)for(auto* candidate:rats) {
        const int index=hdRatResolve(candidate);if(index<0)continue;
        tile_set_center(candidate->tile,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        const auto mask=spriteMask(candidate);auto* buffer=win_get_buf(display_win);
        const int pitch=win_width(display_win),height=win_height(display_win);int opaque=0,visible=0;
        for(int y=0;y<mask.height;++y)for(int x=0;x<mask.width;++x) {
            if(!mask.pixels[y*mask.width+x])continue;++opaque;
            const int sx=mask.x+x,sy=mask.y+y;if(sx<0||sy<0||sx>=pitch||sy>=height)continue;
            const unsigned int owner=hdWorldOwnerAt(buffer+sy*pitch+sx);
            if((owner>>24)==kHdRatOwner && ((owner>>14)&1023)==static_cast<unsigned int>(index))++visible;
        }
        if(visible>=12 && visible*4>=opaque*3){rat=candidate;break;}
    }
    const Object original = *rat;
    rat->flags &= ~(OBJECT_HIDDEN | OBJECT_FLAG_0xFC000); rat->outline = 0;
    tile_set_center(rat->tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    hdWorldSetEnabled(true); hdPlayerSetEnabled(true);
    hdRatSetEnabled(false); tile_refresh_display();
    const auto classic = capture(output / "rat-original.bmp");
    hdRatSetEnabled(true); tile_refresh_display();
    const auto replacement = capture(output / "rat-hd.bmp");
    report.check(classic.valid && replacement.valid && replacement.restored, "real rat SDL frames captured, renderer restored");
    report.check(expected ? classic.pixels != replacement.pixels : classic.pixels == replacement.pixels, "rat HD changes pixels or missing package gives exact fallback");
    report.check(sameHud(classic, replacement), "rat world replacement preserves the HUD");
    report.check(capture().pixels == replacement.pixels, "rat repeated presentation has stable pixels");
    rat->outline=OUTLINE_TYPE_HOSTILE;tile_refresh_display();
    const auto outlined=capture(output/"rat-outline-hd.bmp");
    report.check(expected!=540 || hdRatResolve(rat)>=0,"combat target outline keeps the HD rat body eligible");
    report.check(outlined.valid && outlined.restored,"hostile target outline renders with the HD rat");
    rat->outline=0;tile_refresh_display();
    tile_refresh_display(); report.check(capture().pixels == replacement.pixels, "rat repeated full refresh has stable pixels");
    hdWorldReleaseTextures(); report.check(capture().pixels == replacement.pixels, "rat texture recreation preserves pixels");
    const auto large = capture(output / "rat-hd-4k.bmp",3840,2160);
    report.check(large.valid && large.restored, "rat true 4K SDL render succeeds");
    saveCrop(large,output/"rat-detail-4k.bmp",rat->tile);
    int rendered = 0, originalFrames = 0, missing = 0;
    std::ofstream table(output/"frames.tsv"); table << "animation\tdirection\tframe\tavailable\tvisible\n";
    for (int a=0; a<64; ++a) for (int d=0; d<6; ++d) {
        int fid=art_id(OBJ_TYPE_CRITTER,24,a,0,d+1);
        if (!art_exists(fid)) continue;
        CacheEntry* handle = nullptr; Art* art=art_ptr_lock(fid,&handle);
        if(!art)continue;
        const int count=art->frameCount; art_ptr_unlock(handle);
        for(int f=0;f<count;++f) {
            ++originalFrames;
            Rect dirty;
            const bool pose=obj_change_fid(rat,fid,&dirty)==0 && obj_set_rotation(rat,d,&dirty)==0 && obj_set_frame(rat,f,&dirty)==0;
            const int available=hdRatResolve(rat);
            if(available<0)++missing;
            report.check(pose && (expected==540 ? available>=0 : expected==0 ? available<0 : true),"original rat pose "+std::to_string(a)+"/"+std::to_string(d)+"/"+std::to_string(f)+" resolves or falls back");
            if(!pose)continue;
            tile_refresh_display();
            const bool visible=hdWorldVisiblePixels(kHdRatOwner)>0;
            table << a << '\t' << d << '\t' << f << '\t' << (available>=0) << '\t' << visible << '\n';
            // Every pose passes through the actual owner writer and SDL renderer.
            const auto frame=capture();
            if(frame.valid && frame.restored)++rendered;
            if(f==0 || (a==1 && d==1) || (a==16 && d==1) || (a==20 && d==1)) {
                const std::string label="a"+std::to_string(a)+"-d"+std::to_string(d)+"-f"+std::to_string(f);
                saveCrop(frame,output/(label+".bmp"),rat->tile);
            }
        }
    }
    report.check(originalFrames==540 && rendered==originalFrames, "all 540 directional world frames rendered in CE");
    report.check(missing==540-expected, "complete HD coverage or exact per-frame classic fallback count");
    Rect dirty; obj_change_fid(rat,original.fid,&dirty); obj_set_rotation(rat,original.rotation,&dirty); obj_set_frame(rat,original.frame,&dirty);
    rat->flags=original.flags;rat->outline=original.outline;
    if(expected==540) {
        const auto classicWalk=timedRatWalk(report,rat,output/"walk-classic",false);
        const auto hdWalk=timedRatWalk(report,rat,output,true);
        report.check(classicWalk.valid && hdWalk.valid && classicWalk.pixels==hdWalk.pixels,
            "HD rat introduces no partial redraw differences beyond the identical classic-rat control");
        if(rat!=rats.front()) {
            const auto classicHidden=timedRatWalk(report,rats.front(),output/"walk-occluded-classic",false);
            const auto hdHidden=timedRatWalk(report,rats.front(),output/"walk-occluded",true);
            report.check(classicHidden.valid && hdHidden.valid && classicHidden.pixels==hdHidden.pixels,
                "occluded HD rat redraw differences match the classic-rat control");
        }
    }
    report.check(rat->tile==original.tile && rat->x==original.x && rat->y==original.y && rat->pid==original.pid
        && rat->data.critter.hp==original.data.critter.hp, "rat gameplay identity, position and HP remain unchanged");
    report.check(blockers()==originalBlockers, "all original map blockers preserved");
    hdHudSetItemEnabled(0x01400018, false);
    ratAimPath = output/"aimed-original.bmp";
    const int originalAimResult = combatPreviewRatCalledShot(rat, captureRatAimedDialog);
    const Capture originalAim = ratAimCapture;
    hdHudSetItemEnabled(0x01400018, true);
    ratAimPath = output/"aimed-hd.bmp";
    const int hdAimResult = combatPreviewRatCalledShot(rat, captureRatAimedDialog);
    report.check(originalAimResult == -1 && hdAimResult == -1 && originalAim.valid && ratAimCapture.valid,
        "real aimed-shot dialog opens, captures and cancels without attacking");
    report.check(expectedAim ? originalAim.pixels != ratAimCapture.pixels : originalAim.pixels == ratAimCapture.pixels,
        "actual aimed-shot rat diagram changes or falls back to classic");
    mouse_hide();
    hdWorldSetEnabled(false); tile_refresh_display(); const auto off=capture();
    hdRatSetEnabled(false); tile_refresh_display(); report.check(capture().pixels==off.pixels,"F11 classic world unaffected by HD rat cache");
    hdWorldSetEnabled(true);hdRatSetEnabled(true);
    tile_set_center(center,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    report.check(hdHudAvailable(0x01400018)==expectedAim,"HD aimed-shot diagram registered or classic fallback retained");
    std::ofstream summary(output/"result.json");
    summary<<"{\"passed\":"<<report.passed<<",\"failed\":"<<report.failed<<",\"world_frames\":"<<originalFrames
        <<",\"rendered_frames\":"<<rendered<<",\"missing_frames\":"<<missing<<",\"rat_keys\":"<<hdRatRegisteredKeyCount()
        <<",\"unique_loaded_frames\":"<<hdRatLoadedFrameCount()<<"}\n";
    report.text<<"TOTAL "<<report.passed<<" PASS "<<report.failed<<" FAIL"<<std::endl;
    return report.failed==0 && summary ? 0 : 42;
}

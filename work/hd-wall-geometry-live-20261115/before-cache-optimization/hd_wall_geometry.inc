// Position-registered wall blocks. Owner253 packs [placement:9][native texel:15].
// Metadata is optional and render-only. Indexed FRM drawing always executes.
static void loadWallGeometry()
{
    int configured=1;
    config_get_value(&game_config,"remaster","hd_wall_geometry",&configured);
    const char* value=SDL_getenv("FALLOUT_HD_WALL_GEOMETRY");
    wallGeometryEnabled=value?std::strcmp(value,"0")!=0:configured!=0;
    std::ifstream input("data/art/hd/world-pilot/wall-geometry.tsv");
    std::string line;
    size_t total=0;for(const auto& a:assets) total+=a.rgba.size();
    for(int row=0;row<1024 && std::getline(input,line);++row) {
        if(line.empty() || line[0]=='#' || line.size()>512) continue;
        CavePlacement p {};std::string file,extra;std::istringstream in(line);
        if(!(in>>p.objectId>>p.fid>>p.pid>>p.tile>>p.elevation>>p.x>>p.y>>p.rotation>>p.oldWidth>>p.oldHeight>>file) || (in>>extra)) continue;
        if(cavePlacements.size()>=512 || ((p.fid>>24)&15)!=3 || p.objectId==252
            || p.tile<0 || p.tile>=40000 || p.elevation!=0 || p.rotation<0 || p.rotation>5
            || p.oldWidth<1 || p.oldWidth>128 || p.oldHeight<1 || p.oldHeight>192
            || p.oldWidth*p.oldHeight>32767 || !safeAssetFilename(file)
            || total+size_t(p.oldWidth)*p.oldHeight*64>kMaximumAssetBytes) continue;
        const auto original=std::find_if(fidAssets.begin(),fidAssets.end(),[&](const auto& a){return a.first==artKey(p.fid,0);});
        if(original==fidAssets.end() || assets[original->second].floor
            || assets[original->second].width!=p.oldWidth || assets[original->second].height!=p.oldHeight) continue;
        if(std::any_of(cavePlacements.begin(),cavePlacements.end(),[&](const auto& a){return a.objectId==p.objectId;})) continue;
        Asset candidate;
        if(!loadAsset(candidate,("data/art/hd/world-pilot/"+file).c_str(),p.oldWidth,p.oldHeight)) continue;
        p.assetId=253;p.cropX=0;p.cropY=0;p.cropWidth=p.oldWidth*4;p.cropHeight=p.oldHeight*4;
        p.drawX=0;p.drawY=0;p.drawWidth=p.oldWidth;p.drawHeight=p.oldHeight;
        total+=candidate.rgba.size();p.geometryRgba=std::move(candidate.rgba);
        p.under.resize(size_t(p.width())*p.height());p.opacity.resize(p.under.size(),255);
        cavePlacements.push_back(std::move(p));
    }
}
int hdWorldWallGeometryCount()
{ hdWorldInit();return static_cast<int>(std::count_if(cavePlacements.begin(),cavePlacements.end(),[](const auto& p){return p.assetId==253;})); }
void hdWorldSetWallGeometryEnabled(bool state) { hdWorldInit();wallGeometryEnabled=state; }
bool hdWorldWallGeometryEnabled() { hdWorldInit();return wallGeometryEnabled; }

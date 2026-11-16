// Render-only instance appearances. Included after the private world renderer helpers.
// Owners 224..239 (scenery) and 252 (vault wall) contain [placement:8][native union texel:16]. Original indexed
// drawing always executes, so F11, saves, hit testing and collision stay classic.
struct CaveBackground { UnderPixel pixel, player, skeleton; };
struct CavePlacement {
    int objectId, fid, pid, tile, elevation, x, y, rotation, assetId;
    int oldWidth, oldHeight, cropX, cropY, cropWidth, cropHeight, drawX, drawY, drawWidth, drawHeight;
    int left() const { return std::min(0, drawX); }
    int top() const { return std::min(0, drawY); }
    int width() const { return std::max(oldWidth, drawX + drawWidth) - left(); }
    int height() const { return std::max(oldHeight, drawY + drawHeight) - top(); }
    std::vector<CaveBackground> under;
    std::vector<unsigned char> opacity;
    std::vector<unsigned char> geometryRgba;
    // Native cell coverage: 0 empty, 1 mixed, 2 fully opaque at all 16 subpixels.
    std::vector<unsigned char> geometryCoverage;
};
static std::vector<CavePlacement> cavePlacements;
static bool caveVarietyEnabled = true;
static bool wallGeometryEnabled = true;
static uint64_t caveRevision = 1, presentedCaveRevision = 0;
static PlayerDraw caveDraw;
static bool isCaveOwner(unsigned int id) { return (id >= 224 && id <= 239) || id == 252 || id == 253; }
static unsigned int caveIndex(uint32_t owner) { return (owner >> ((owner >> 24) == 253 ? 15 : 16)) & ((owner >> 24) == 253 ? 511 : 255); }
static unsigned int caveTexel(uint32_t owner) { return owner & ((owner >> 24) == 253 ? 32767 : 65535); }
static bool sameUnder(const UnderPixel& a, const UnderPixel& b)
{ return a.owner == b.owner && a.light == b.light && a.index == b.index; }

// Diagnostic used by compositing checks: transparent new shapes can reveal
// decorations that are below their render-only ownership rectangle.
static bool caveBackgroundHasAsset(unsigned int owner,int first,int last,int depth)
{
    if(depth>16) return false;
    const unsigned int i=caveIndex(owner),t=caveTexel(owner);
    if(!isCaveOwner(owner>>24) || i>=cavePlacements.size() || t>=cavePlacements[i].under.size()) return false;
    const auto& bg=cavePlacements[i].under[t];
    const unsigned int id=bg.pixel.owner>>24;
    if(id>=static_cast<unsigned int>(first) && id<=static_cast<unsigned int>(last)) return true;
    return caveBackgroundHasAsset(bg.pixel.owner,first,last,depth+1);
}
bool hdWorldCaveBackgroundHasAsset(unsigned int owner,int first,int last)
{ return caveBackgroundHasAsset(owner,first,last,0); }

static void loadCaveVariety()
{
    int setting = 1;
    config_get_value(&game_config, "remaster", "hd_cave_variety", &setting);
    const char* overrideValue = SDL_getenv("FALLOUT_HD_CAVE_VARIETY");
    caveVarietyEnabled = overrideValue ? std::strcmp(overrideValue, "0") != 0 : setting != 0;
    std::ifstream input("data/art/hd/world-pilot/cave-variety-assets.tsv");
    std::string line;
    size_t bytes = 0; for (const auto& a : assets) bytes += a.rgba.size();
    for (int row = 0; row < 32 && std::getline(input,line); ++row) {
        if (line.empty() || line[0]=='#' || line.size()>256) continue;
        int id,w,h; std::string file,extra; std::istringstream in(line);
        if (!(in>>id>>w>>h>>file) || (in>>extra) || id==253 || !isCaveOwner(id) || w!=128 || h!=128
            || !safeAssetFilename(file) || !assets[id].rgba.empty() || bytes+512*512*4>kMaximumAssetBytes) continue;
        Asset candidate;
        if (!loadAsset(candidate,("data/art/hd/world-pilot/"+file).c_str(),w,h,true)) continue;
        candidate.filename=file; bytes+=candidate.rgba.size(); assets[id]=std::move(candidate);
    }
    std::ifstream positions("data/art/hd/world-pilot/cave-variety-placements.tsv");
    for (int row=0; row<160 && std::getline(positions,line); ++row) {
        if (line.empty() || line[0]=='#' || line.size()>512) continue;
        int index; CavePlacement p {}; std::string extra; std::istringstream in(line);
        if (!(in>>index>>p.objectId>>p.fid>>p.pid>>p.tile>>p.elevation>>p.x>>p.y>>p.rotation>>p.assetId
            >>p.oldWidth>>p.oldHeight>>p.cropX>>p.cropY>>p.cropWidth>>p.cropHeight
            >>p.drawX>>p.drawY>>p.drawWidth>>p.drawHeight) || (in>>extra)) continue;
        // Keep indices stable even if one optional sprite is unavailable.
        if (index!=static_cast<int>(cavePlacements.size()) || index>=128 || !isCaveOwner(p.assetId)
            || p.tile<0 || p.tile>=40000 || p.elevation!=0 || p.rotation<0 || p.rotation>5
            || p.oldWidth<1 || p.oldWidth>128 || p.oldHeight<1 || p.oldHeight>128
            || p.cropX<0 || p.cropY<0 || p.cropWidth<1 || p.cropHeight<1
            || p.cropX+p.cropWidth>512 || p.cropY+p.cropHeight>512
            || p.drawWidth<1 || p.drawWidth>160 || p.drawHeight<1 || p.drawHeight>128
            || p.drawX < -32 || p.drawY < -16 || p.drawX>128 || p.drawY>128
            || p.width()*p.height()>65535
            || (p.assetId==252 ? (p.objectId!=252 || p.fid!=50331705 || p.pid!=50331855 || p.tile!=17285
                || p.x!=0 || p.y!=0 || p.rotation!=0 || p.oldWidth!=31 || p.oldHeight!=120)
                : ((p.fid>>24)&15)!=2)) continue;
        const auto base=std::find_if(fidAssets.begin(),fidAssets.end(),[&](const auto& v){return v.first==artKey(p.fid,0);});
        if (base==fidAssets.end() || assets[base->second].width!=p.oldWidth || assets[base->second].height!=p.oldHeight) continue;
        p.under.resize(static_cast<size_t>(p.width())*p.height());
        p.opacity.resize(p.under.size(),255); cavePlacements.push_back(std::move(p));
    }
}

int hdWorldCaveAssignmentCount() { hdWorldInit(); return static_cast<int>(std::count_if(cavePlacements.begin(),cavePlacements.end(),[](const auto& p){return p.assetId!=253;})); }
int hdWorldCaveAssetCount() { hdWorldInit(); int n=0; for(int i=0;i<kAssetCapacity;++i) if(isCaveOwner(i)) n+=!assets[i].rgba.empty(); return n; }
void hdWorldSetCaveVarietyEnabled(bool state) { hdWorldInit(); caveVarietyEnabled=state; }
bool hdWorldCaveVarietyEnabled() { hdWorldInit(); return caveVarietyEnabled; }
int hdWorldCavePlacementForObject(const Object* o)
{
    hdWorldInit();
    if (!caveVarietyEnabled || !hdWorldIsPilotMap() || !o || o->frame!=0) return -1;
    for (size_t i=0;i<cavePlacements.size();++i) {
        const auto& p=cavePlacements[i];
        if(p.assetId==253 && !wallGeometryEnabled) continue;
        if (o->id==p.objectId && o->fid==p.fid && o->pid==p.pid && o->tile==p.tile
            && o->elevation==p.elevation && o->x==p.x && o->y==p.y && o->rotation==p.rotation
            && (p.assetId==253 ? !p.geometryRgba.empty() : !assets[p.assetId].rgba.empty())) return static_cast<int>(i);
    }
    return -1;
}
int hdWorldCaveAssetForObject(const Object* o)
{ int i=hdWorldCavePlacementForObject(o); return i<0?0:cavePlacements[i].assetId; }

void hdWorldCaveBounds(const Object* o, Rect* rect)
{
    const int i=hdWorldCavePlacementForObject(o); if(i<0 || !rect) return;
    const auto& p=cavePlacements[i];
    rect->lrx=rect->ulx+p.left()+p.width()-1; rect->lry=rect->uly+p.top()+p.height()-1;
    rect->ulx+=p.left(); rect->uly+=p.top();
}

bool hdWorldBeginCaveScenery(const Object* o, unsigned char* base, int pitch,
    const Rect* art, const Rect* clip, int light)
{
    caveDraw.base=nullptr;
    const int i=hdWorldCavePlacementForObject(o);
    if (i<0 || !base || !art || !clip || pitch<=0
        || (o->flags & (OBJECT_HIDDEN | (OBJECT_FLAG_0xFC000 & ~OBJECT_TRANS_NONE)))
        || ((o->outline & OUTLINE_TYPE_MASK) && !(o->outline & OUTLINE_DISABLED))) return false;
    auto& p=cavePlacements[i];
    if(art->lrx-art->ulx+1!=p.oldWidth || art->lry-art->uly+1!=p.oldHeight) return false;
    Buffer* target=findBuffer(base); if(!target) return false;
    size_t start=base-target->base; int height=static_cast<int>((target->size-start)/pitch);
    Rect full {art->ulx+p.left(),art->uly+p.top(),art->ulx+p.left()+p.width()-1,art->uly+p.top()+p.height()-1};
    Rect area {std::max({full.ulx,clip->ulx,0}),std::max({full.uly,clip->uly,0}),
        std::min({full.lrx,clip->lrx,pitch-1}),std::min({full.lry,clip->lry,height-1})};
    if(area.ulx>area.lrx || area.uly>area.lry) return false;
    for(int y=area.uly;y<=area.lry;++y) for(int x=area.ulx;x<=area.lrx;++x) {
        size_t at=start+static_cast<size_t>(y)*pitch+x;
        size_t t=static_cast<size_t>(y-full.uly)*p.width()+x-full.ulx;
        uint32_t owner=target->owners[at];
        if(!(isCaveOwner(owner>>24) && caveIndex(owner)==static_cast<unsigned int>(i))) {
            CaveBackground bg {{owner,target->lights[at],target->base[at]},
                {target->playerUnderOwners[at],target->playerUnderLights[at],target->playerUnderIndices[at]},target->skeletonUnder[at]};
            auto& old=p.under[t];
            if(!sameUnder(old.pixel,bg.pixel)||!sameUnder(old.player,bg.player)||!sameUnder(old.skeleton,bg.skeleton)) {old=bg;++caveRevision;}
        }
        if(p.opacity[t]!=255) {p.opacity[t]=255;++caveRevision;}
    }
    caveDraw={base,pitch,i,std::clamp(light>>9,0,128),area,full}; return true;
}

void hdWorldCaveEgg(const unsigned char* mask,int pitch,const Rect* rect)
{
    if(!caveDraw.base || !mask || !rect || pitch<=0) return;
    auto& p=cavePlacements[caveDraw.frame];
    for(int y=std::max(rect->uly,caveDraw.clipped.uly);y<=std::min(rect->lry,caveDraw.clipped.lry);++y)
      for(int x=std::max(rect->ulx,caveDraw.clipped.ulx);x<=std::min(rect->lrx,caveDraw.clipped.lrx);++x) {
        int m=mask[(y-rect->uly)*pitch+x-rect->ulx];
        unsigned char alpha=static_cast<unsigned char>(m?std::min(255,m*255/128):255);
        size_t t=(y-caveDraw.art.uly)*p.width()+x-caveDraw.art.ulx;
        if(p.opacity[t]!=alpha) {p.opacity[t]=alpha;++caveRevision;}
      }
}

void hdWorldEndCaveScenery()
{
    if(!caveDraw.base) return;
    auto& p=cavePlacements[caveDraw.frame]; Buffer* target=findBuffer(caveDraw.base);
    if(target) {
        size_t start=caveDraw.base-target->base;
        for(int y=caveDraw.clipped.uly;y<=caveDraw.clipped.lry;++y)
          for(int x=caveDraw.clipped.ulx;x<=caveDraw.clipped.lrx;++x) {
            size_t at=start+static_cast<size_t>(y)*caveDraw.pitch+x;
            uint32_t texel=(y-caveDraw.art.uly)*p.width()+x-caveDraw.art.ulx;
            // Empty wall canvas is not a new foreground layer. Preserve actors
            // and decorations there instead of wrapping them in a wall owner.
            if(p.assetId==253 && currentSource && texel<currentSize && currentSource[texel]==0) {
                if(p.geometryCoverage[texel]==0) continue;
            }
            target->owners[at]=(uint32_t(p.assetId)<<24)|(uint32_t(caveDraw.frame)<<(p.assetId==253?15:16))|texel;
            target->lights[at]=static_cast<unsigned char>(caveDraw.light);
          }
    }
    caveDraw.base=nullptr;
}

static void sampleTerminal(const Buffer&,size_t,uint32_t,int,int,int,const SDL_Color*,unsigned char*);
static void sampleSkeleton(const Buffer&,size_t,uint32_t,int,int,int,const SDL_Color*,unsigned char*);
static void sampleCave(const Buffer&,size_t,uint32_t,int,int,int,const SDL_Color*,unsigned char*,int=0);

static void sampleCaveBackground(const Buffer& screen,size_t at,UnderPixel saved,const CaveBackground& context,
    int sx,int sy,const SDL_Color* palette,unsigned char* color,int depth)
{
    const auto indexed=palette[saved.index];color[0]=indexed.r;color[1]=indexed.g;color[2]=indexed.b;
    if(depth>16) return;
    int id=saved.owner>>24;unsigned int texel=saved.owner&0xFFFFFF;
    if(isCaveOwner(id)) {sampleCave(screen,at,saved.owner,saved.light,sx,sy,palette,color,depth+1);return;}
    if(id==kPlayerOwner) {
        sampleCaveBackground(screen,at,context.player,context,sx,sy,palette,color,depth+1);
        auto actor=hdPlayerFrameAt((saved.owner>>16)&255);unsigned int t=saved.owner&65535;
        if(actor && hdPlayerEnabled() && t<static_cast<unsigned int>(actor->width*actor->height)) {
            size_t uv=((t/actor->width*4+sy)*actor->width*4+t%actor->width*4+sx)*4;
            int alpha=actor->rgba[uv+3];for(int c=0;c<3;++c) color[c]=static_cast<unsigned char>((lightColors[c][saved.light][actor->rgba[uv+c]]*alpha+color[c]*(255-alpha)+127)/255);
        }
        return;
    }
    if(id==kSkeletonOwner) {
        sampleCaveBackground(screen,at,context.skeleton,context,sx,sy,palette,color,depth+1);
        if(texel<67*41 && !skeletonAsset.rgba.empty()) {
            size_t uv=((texel/67*4+sy)*268+texel%67*4+sx)*4;int alpha=skeletonAsset.rgba[uv+3];
            for(int c=0;c<3;++c) color[c]=static_cast<unsigned char>((lightColors[c][saved.light][skeletonAsset.rgba[uv+c]]*alpha+color[c]*(255-alpha)+127)/255);
        }
        return;
    }
    if(terminalSoftEdges && id==terminalBaseId) {sampleTerminal(screen,at,saved.owner,saved.light,sx,sy,palette,color);return;}
    const auto& a=assets[id];
    if(!a.rgba.empty() && texel<a.nativeIndices.size()) {
        size_t uv=((texel/a.width*4+sy)*a.width*4+texel%a.width*4+sx)*4;
        const auto& rgba=worldRgba(id);
        if(rgba[uv+3]) for(int c=0;c<3;++c) color[c]=lightColors[c][saved.light][rgba[uv+c]];
    }
}

static void sampleCave(const Buffer& screen,size_t at,uint32_t owner,int light,
    int sx,int sy,const SDL_Color* palette,unsigned char* color,int depth)
{
    unsigned int i=caveIndex(owner),t=caveTexel(owner);
    if(i>=cavePlacements.size() || depth>16) return;
    const auto& p=cavePlacements[i]; if(t>=p.under.size() || static_cast<int>(owner>>24)!=p.assetId) return;
    // Registered walls have a 1:1 canvas. An opaque texel needs no recursive
    // background sampling; avoid paying for all underlying wall/floor layers.
    if(p.assetId==253 && p.opacity[t]==255) {
        size_t uv=((size_t(t/p.oldWidth)*4+sy)*p.oldWidth*4+(t%p.oldWidth)*4+sx)*4;
        if(uv+3<p.geometryRgba.size() && p.geometryRgba[uv+3]==255) {
            for(int c=0;c<3;++c) color[c]=lightColors[c][light][p.geometryRgba[uv+c]];
            return;
        }
    }
    const auto& bg=p.under[t];sampleCaveBackground(screen,at,bg.pixel,bg,sx,sy,palette,color,depth+1);
    int x=static_cast<int>(t%p.width())+p.left()-p.drawX;
    int y=static_cast<int>(t/p.width())+p.top()-p.drawY;
    if(x<0 || y<0 || x>=p.drawWidth || y>=p.drawHeight) return;
    int u=p.cropX+(x*4+sx)*p.cropWidth/(p.drawWidth*4);
    int v=p.cropY+(y*4+sy)*p.cropHeight/(p.drawHeight*4);
    const auto& rgba=p.assetId==253?p.geometryRgba:assets[p.assetId].rgba;
    const int textureWidth=p.assetId==253?p.oldWidth*4:512;
    size_t uv=(static_cast<size_t>(v)*textureWidth+u)*4;
    if(uv+3>=rgba.size()) return;
    int alpha=(rgba[uv+3]*p.opacity[t]+127)/255;
    for(int c=0;c<3;++c) color[c]=static_cast<unsigned char>((lightColors[c][light][rgba[uv+c]]*alpha+color[c]*(255-alpha)+127)/255);
}

#include "game/hd_wall_geometry.inc"

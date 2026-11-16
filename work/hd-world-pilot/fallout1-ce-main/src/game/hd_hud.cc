#include "game/hd_hud.h"
#include <array>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "game/gconfig.h"
#include "game/hd_world_pilot.h"
#include "plib/gnw/svga.h"
#include "plib/gnw/mouse.h"

namespace fallout {
namespace {
struct Asset {
    int fid, width, height, pid;
    const char* path;
    std::vector<unsigned char> pixels;
    SDL_Texture* cursor = nullptr;
    bool enabled = true;
    int scale = 4;
};
std::array<Asset,10> assets {{
    {0x07000060,88,33,4,"data/art/hd/inventory/knife/knife.rgba"},
    {0x07000004,70,63,8,"data/art/hd/inventory/10mm-pistol/pistol.rgba"},
    {0x0700008C,81,65,21,"data/art/hd/inventory/brass-knuckles/knuckles.rgba"},
    {0x0700001F,83,58,29,"data/art/hd/inventory/10mm-jhp/ammo.rgba"},
    {0x0700001E,83,61,30,"data/art/hd/inventory/10mm-ap/ammo.rgba"},
    {0x07000073,89,61,40,"data/art/hd/inventory/stimpak/stimpak.rgba"},
    {0x0700003B,92,58,79,"data/art/hd/inventory/flare-unlit/flare.rgba"},
    {0x0700007B,80,59,205,"data/art/hd/inventory/flare-lit/flare.rgba"},
    {0x01400018,170,225,0x01000030,"data/art/hd/critter-rat/aimed.rgba"},
    {kHdHudPanelFid,640,100,-1,"data/art/hd/hud-panel/shell-monitor.rgba",{},nullptr,true,6}
}};
struct Fit { int asset, width, height; unsigned int base; };
std::vector<Fit> fits;
bool initialized=false, enabled=true;
bool panelEnabled=true;
std::vector<unsigned char*> panelArt;
int dragFid=-1;
unsigned int le32(const unsigned char* p) { return p[0] | (unsigned(p[1])<<8) | (unsigned(p[2])<<16) | (unsigned(p[3])<<24); }
int assetIndex(int fid) { for(size_t i=0;i<assets.size();++i) if(assets[i].fid==fid) return static_cast<int>(i); return -1; }
void init()
{
    if(initialized) return;
    initialized=true;
    int configured=1;
    config_get_value(&game_config,"remaster","hd_hud_icons",&configured);
    enabled=configured!=0;
    configured=1;
    config_get_value(&game_config,"remaster","hd_hud_panel",&configured);
    panelEnabled=configured!=0;
    unsigned int base=0;
    const bool preview=SDL_getenv("FALLOUT_HD_HUD_PREVIEW")!=nullptr;
    const char* pidText=preview?SDL_getenv("FALLOUT_HD_HUD_ITEM_PID"):nullptr;
    const int testPid=pidText?std::atoi(pidText):4;
    for(size_t i=0;i<assets.size();++i) {
        Asset& asset=assets[i];
        fits.push_back({static_cast<int>(i),asset.width,asset.height,base});
        base+=asset.width*asset.height;
        const char* path=asset.path;
        if(asset.fid==kHdHudPanelFid) {
            const char* overridePath=SDL_getenv("FALLOUT_HD_HUD_PANEL_ASSET");
            if(overridePath && overridePath[0]) path=overridePath;
        }
        if(preview && asset.pid==testPid) {
            const char* alternative=SDL_getenv("FALLOUT_HD_HUD_ASSET");
            if(alternative && alternative[0]) path=alternative;
        }
        FILE* file=fopen(path,"rb");
        if(!file) continue;
        std::array<unsigned char,20> header{};
        const unsigned int w=asset.width*asset.scale,h=asset.height*asset.scale;
        bool valid=fread(header.data(),1,header.size(),file)==header.size()
            && memcmp(header.data(),"F1HD",4)==0 && le32(header.data()+4)==1
            && le32(header.data()+8)==w && le32(header.data()+12)==h && le32(header.data()+16)==static_cast<unsigned int>(asset.scale);
        std::vector<unsigned char> candidate(w*h*4);
        if(valid) valid=fread(candidate.data(),1,candidate.size(),file)==candidate.size() && fgetc(file)==EOF;
        fclose(file);
        bool visible=false,transparent=false,opaque=true;
        if(valid) for(size_t at=3;at<candidate.size();at+=4) { visible|=candidate[at]>=240;transparent|=candidate[at]==0;opaque&=candidate[at]==255; }
        // The original rat targeting schematic has an opaque black display.
        const bool opaqueUi=(asset.fid==0x01400018 || asset.fid==kHdHudPanelFid) && opaque;
        if(valid && visible && (transparent || opaqueUi)) asset.pixels.swap(candidate);
    }
}
const Fit* findFit(unsigned int texel)
{
    for(const auto& fit:fits) if(texel>=fit.base && texel<fit.base+fit.width*fit.height) return &fit;
    return nullptr;
}
void drawFit(const Fit& fit,unsigned char* dest,int pitch,int light)
{
    for(int y=0;y<fit.height;++y) for(int x=0;x<fit.width;++x) {
        unsigned int texel=fit.base+y*fit.width+x;
        bool visible=false;
        for(int sy=0;sy<4;++sy) for(int sx=0;sx<4;++sx) visible|=hdHudTexel(texel,sx,sy)[3]!=0;
        if(visible) hdWorldMarkHudPixel(dest+y*pitch+x,texel,light);
    }
}
}
bool hdHudAvailable(int fid)
{
    init();int index=assetIndex(fid);
    return (fid==kHdHudPanelFid?panelEnabled:enabled) && index>=0 && assets[index].enabled && !assets[index].pixels.empty();
}
bool hdHudPanelAvailable() { return hdHudAvailable(kHdHudPanelFid); }
bool hdHudPanelTexel(unsigned int texel)
{
    // Native panel slot is stable and opaque; it can use the static RGB cache.
    return initialized && fits.size()>=assets.size()
        && texel>=fits[9].base && texel<fits[9].base+640*100;
}
void hdHudPanelPaint(unsigned char* dest,int width,int height,int pitch,int sourceX,int sourceY,bool pressed)
{
    if(!hdHudPanelAvailable() || sourceX<0 || sourceY<0 || sourceX+width>640 || sourceY+height>100
        || !hdWorldHudTarget(dest,width,height,pitch)) return;
    const auto& fit=fits[assetIndex(kHdHudPanelFid)];
    for(int y=0;y<height;++y) for(int x=0;x<width;++x)
        hdWorldMarkHudPixel(dest+y*pitch+x,fit.base+(sourceY+y)*640+sourceX+x,pressed?104:128);
}
void hdHudPanelRegisterArt(unsigned char* data,int width,int height,int sourceX,int sourceY,bool pressed)
{
    if(!data || !hdHudPanelAvailable() || std::find(panelArt.begin(),panelArt.end(),data)!=panelArt.end()) return;
    panelArt.push_back(data);hdWorldRegisterBuffer(data,width*height);
    const auto& fit=fits[assetIndex(kHdHudPanelFid)];
    // These are locked, shared classic FRMs: never change their palette indices.
    // Zero pixels remain transparent for GNW's original button masks.
    for(int y=0;y<height;++y) for(int x=0;x<width;++x) if(data[y*width+x])
        hdWorldMarkHudPixel(data+y*width+x,fit.base+(sourceY+y)*640+sourceX+x,pressed?104:128);
}
void hdHudPanelReleaseArt()
{
    for(auto* data:panelArt) hdWorldUnregisterBuffer(data);
    panelArt.clear();
}
bool hdHudDimensions(int fid,int* width,int* height)
{
    if(!width || !height || !hdHudAvailable(fid)) return false;
    auto& asset=assets[assetIndex(fid)];*width=asset.width;*height=asset.height;return true;
}
void hdHudSetEnabled(bool state) { init();enabled=state; }
void hdHudSetItemEnabled(int fid,bool state) {
    init();int index=assetIndex(fid);
    if(index>=0 && assets[index].enabled!=state) {
        assets[index].enabled=state;
        if(fid==kHdHudPanelFid) hdWorldReleaseTextures();
    }
}
bool hdHudTexelMatches(unsigned int texel,int fid) { init();auto* fit=findFit(texel);return fit && assets[fit->asset].fid==fid; }
const unsigned char* hdHudTexel(unsigned int texel,int subX,int subY)
{
    if(subX<0 || subX>3 || subY<0 || subY>3) return nullptr;
    const Fit* fit=findFit(texel);
    if(!fit || !hdHudAvailable(assets[fit->asset].fid)) return nullptr;
    const auto& asset=assets[fit->asset];
    const unsigned int local=texel-fit->base;
    // Native and scaled slots sample the original full-colour x4 asset directly.
    int x=((local%fit->width)*4+subX)*asset.width*asset.scale/(fit->width*4);
    int y=((local/fit->width)*4+subY)*asset.height*asset.scale/(fit->height*4);
    return asset.pixels.data()+(y*asset.width*asset.scale+x)*4;
}
void hdHudDraw(int fid,unsigned char* dest,int pitch,int x,int y,bool pressed)
{
    if(!hdHudAvailable(fid) || !dest || x<0 || y<0) return;
    int index=assetIndex(fid);const auto& fit=fits[index];
    if(x+fit.width>pitch || !hdWorldHudTarget(dest+y*pitch+x,fit.width,fit.height,pitch)) return;
    drawFit(fit,dest+y*pitch+x,pitch,pressed?124:128);
}
bool hdHudDrawFit(int fid,unsigned char* dest,int width,int height,int pitch)
{
    if(!hdHudAvailable(fid) || !hdWorldHudTarget(dest,width,height,pitch)) return false;
    int index=assetIndex(fid);const auto& asset=assets[index];
    int w=asset.width,h=asset.height;
    if(w>width || h>height) {
        if(height*asset.width>=width*asset.height) { w=width;h=width*asset.height/asset.width; }
        else { h=height;w=height*asset.width/asset.height; }
    }
    if(w<=0 || h<=0) return false;
    size_t selected=fits.size();
    for(size_t i=0;i<fits.size();++i) if(fits[i].asset==index && fits[i].width==w && fits[i].height==h) {selected=i;break;}
    if(selected==fits.size()) {
        unsigned int base=fits.back().base+fits.back().width*fits.back().height;
        if(base+w*h>=0xFFFFFF) return false;
        fits.push_back({index,w,h,base});
    }
    drawFit(fits[selected],dest+((height-h)/2)*pitch+(width-w)/2,pitch,128);
    return true;
}
void hdHudSetDragCursor(int fid) { dragFid=fid;if(fid!=-1 && !mouse_hidden()) mouse_show(); }
void hdHudReleaseCursorTexture()
{
    for(auto& asset:assets) { if(asset.cursor) SDL_DestroyTexture(asset.cursor);asset.cursor=nullptr; }
}
bool hdHudDragCursorActive()
{
    // Ordinary early-startup cursors must not initialize game-config assets.
    int index=assetIndex(dragFid);
    if(index<0 || !hdHudAvailable(dragFid) || !gSdlRenderer) return false;
    auto& asset=assets[index];
    if(!asset.cursor) {
        asset.cursor=SDL_CreateTexture(gSdlRenderer,SDL_PIXELFORMAT_RGBA32,SDL_TEXTUREACCESS_STATIC,asset.width*4,asset.height*4);
        if(!asset.cursor) return false;
        if(SDL_UpdateTexture(asset.cursor,nullptr,asset.pixels.data(),asset.width*16)!=0
            || SDL_SetTextureBlendMode(asset.cursor,SDL_BLENDMODE_BLEND)!=0
            || SDL_SetTextureScaleMode(asset.cursor,SDL_ScaleModeLinear)!=0) {
            SDL_DestroyTexture(asset.cursor);asset.cursor=nullptr;return false;
        }
    }
    return true;
}
void hdHudRenderDragCursor()
{
    if(mouse_hidden() || !hdHudDragCursorActive()) return;
    Rect rect;mouse_get_rect(&rect);
    SDL_Rect dest{rect.ulx,rect.uly,rect.lrx-rect.ulx+1,rect.lry-rect.uly+1};
    SDL_RenderCopy(gSdlRenderer,assets[assetIndex(dragFid)].cursor,nullptr,&dest);
}
}

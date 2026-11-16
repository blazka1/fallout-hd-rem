#include "game/hd_hud_test.h"
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include "game/anim.h"
#include "game/combat_defs.h"
#include "game/hd_hud.h"
#include "game/display.h"
#include "game/hd_world_pilot.h"
#include "game/intface.h"
#include "game/inventry.h"
#include "game/cycle.h"
#include "game/gmouse.h"
#include "game/item.h"
#include "game/protinst.h"
#include "game/queue.h"
#include "game/map.h"
#include "game/object.h"
#include "game/scripts.h"
#include "game/tile.h"
#include "plib/color/color.h"
#include "plib/gnw/gnw.h"
#include "plib/gnw/gnw_types.h"
#include "plib/gnw/mouse.h"
#include "plib/gnw/svga.h"
namespace fallout { namespace {
int kItemFid = 0x07000060;
int kItemPid = 4;
int itemWorldFid() { return kItemPid==79 || kItemPid==205 ? 46 : kItemPid==40 ? 15 : (kItemPid==29 || kItemPid==30 ? 1 : (kItemPid==21?47:(kItemPid==8?34:28))); }
struct Report {
    std::ofstream log; int passed=0,failed=0;
    explicit Report(const std::filesystem::path& p):log(p/"checks.txt"){}
    void check(bool ok,const std::string& text) { log<<(ok?"PASS ":"FAIL ")<<text<<std::endl; if(ok)++passed;else ++failed; }
};
struct Capture {
    int width = 0, height = 0;
    bool valid = false, restored = false;
    std::vector<uint32_t> pixels;
};

Capture capture(const std::filesystem::path& path = {}, int width = 0, int height = 0)
{
    Capture result;
    SDL_GetRendererOutputSize(gSdlRenderer, &result.width, &result.height);
    if (width > 0 && height > 0) { result.width = width; result.height = height; }
    if (result.width <= 0 || result.height <= 0) return result;
    SDL_Texture* oldTarget = SDL_GetRenderTarget(gSdlRenderer);
    int oldW, oldH;
    SDL_Rect oldViewport, oldClip;
    float oldX, oldY;
    SDL_RenderGetLogicalSize(gSdlRenderer, &oldW, &oldH);
    SDL_RenderGetViewport(gSdlRenderer, &oldViewport);
    SDL_RenderGetClipRect(gSdlRenderer, &oldClip);
    SDL_RenderGetScale(gSdlRenderer, &oldX, &oldY);
    SDL_bool oldClipped = SDL_RenderIsClipEnabled(gSdlRenderer);
    SDL_Texture* target = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_TARGET, result.width, result.height);
    if (!target) return result;
    SDL_SetRenderTarget(gSdlRenderer, target);
    SDL_RenderSetLogicalSize(gSdlRenderer, 0, 0);
    SDL_RenderSetLogicalSize(gSdlRenderer, screenGetWidth(), screenGetHeight());
    SDL_RenderSetClipRect(gSdlRenderer, nullptr);
    SDL_UpdateTexture(gSdlTexture, nullptr, gSdlTextureSurface->pixels, gSdlTextureSurface->pitch);
    SDL_SetRenderDrawColor(gSdlRenderer, 0, 0, 0, 255);
    SDL_RenderClear(gSdlRenderer);
    SDL_RenderCopy(gSdlRenderer, gSdlTexture, nullptr, nullptr);
    int beforeW, beforeH, afterW, afterH;
    SDL_Rect beforeViewport, afterViewport, beforeClip, afterClip;
    float beforeX, beforeY, afterX, afterY;
    SDL_RenderGetLogicalSize(gSdlRenderer, &beforeW, &beforeH);
    SDL_RenderGetViewport(gSdlRenderer, &beforeViewport);
    SDL_RenderGetClipRect(gSdlRenderer, &beforeClip);
    SDL_RenderGetScale(gSdlRenderer, &beforeX, &beforeY);
    SDL_bool beforeClipped = SDL_RenderIsClipEnabled(gSdlRenderer);
    hdWorldRender();
    hdHudRenderDragCursor();
    SDL_RenderGetLogicalSize(gSdlRenderer, &afterW, &afterH);
    SDL_RenderGetViewport(gSdlRenderer, &afterViewport);
    SDL_RenderGetClipRect(gSdlRenderer, &afterClip);
    SDL_RenderGetScale(gSdlRenderer, &afterX, &afterY);
    result.restored = beforeW == afterW && beforeH == afterH && beforeX == afterX && beforeY == afterY
        && std::memcmp(&beforeViewport, &afterViewport, sizeof(SDL_Rect)) == 0
        && beforeClipped == SDL_RenderIsClipEnabled(gSdlRenderer)
        && (!beforeClipped || std::memcmp(&beforeClip, &afterClip, sizeof(SDL_Rect)) == 0);
    SDL_Surface* surface = SDL_CreateRGBSurfaceWithFormat(0, result.width, result.height, 32, SDL_PIXELFORMAT_ARGB8888);
    if (surface) {
        SDL_RenderSetLogicalSize(gSdlRenderer, 0, 0);
        SDL_RenderSetScale(gSdlRenderer, 1, 1);
        SDL_RenderSetViewport(gSdlRenderer, nullptr);
        SDL_RenderSetClipRect(gSdlRenderer, nullptr);
        SDL_Rect full { 0, 0, result.width, result.height };
        result.valid = SDL_RenderReadPixels(gSdlRenderer, &full, surface->format->format, surface->pixels, surface->pitch) == 0;
        if (result.valid) {
            result.pixels.resize(static_cast<size_t>(result.width) * result.height);
            for (int y = 0; y < result.height; ++y) std::memcpy(result.pixels.data() + static_cast<size_t>(y) * result.width,
                static_cast<unsigned char*>(surface->pixels) + y * surface->pitch, result.width * sizeof(uint32_t));
            if (!path.empty()) result.valid = SDL_SaveBMP(surface, path.string().c_str()) == 0;
        }
        SDL_FreeSurface(surface);
    }
    SDL_SetRenderTarget(gSdlRenderer, oldTarget);
    SDL_RenderSetLogicalSize(gSdlRenderer, oldW, oldH);
    SDL_RenderSetScale(gSdlRenderer, oldX, oldY);
    SDL_RenderSetViewport(gSdlRenderer, &oldViewport);
    SDL_RenderSetClipRect(gSdlRenderer, oldClipped ? &oldClip : nullptr);
    SDL_DestroyTexture(target);
    return result;
}


bool sameRegion(const Capture& a,const Capture& b,const Rect& logical,bool inside)
{
    if(!a.valid||!b.valid||a.width!=b.width||a.height!=b.height)return false;
    float scale=std::min(float(a.width)/screenGetWidth(),float(a.height)/screenGetHeight());
    int ox=(a.width-int(screenGetWidth()*scale))/2,oy=(a.height-int(screenGetHeight()*scale))/2;
    int l=ox+int(logical.ulx*scale),t=oy+int(logical.uly*scale),r=ox+int((logical.lrx+1)*scale),bot=oy+int((logical.lry+1)*scale);
    for(int y=0;y<a.height;++y)for(int x=0;x<a.width;++x)if((x>=l&&x<r&&y>=t&&y<bot)==inside)
        if(a.pixels[size_t(y)*a.width+x]!=b.pixels[size_t(y)*a.width+x])return false;
    return true;
}
int hudOwners(int fid=kItemFid)
{
    int n=0;auto* screen=static_cast<unsigned char*>(gSdlSurface->pixels);
    for(int y=0;y<gSdlSurface->h;++y)for(int x=0;x<gSdlSurface->w;++x)
        { auto owner=hdWorldOwnerAt(screen+y*gSdlSurface->pitch+x); n+=(owner>>24)==251 && hdHudTexelMatches(owner&0xFFFFFF,fid); }
    return n;
}
void redraw(bool enabled,int fid=kItemFid,bool disabled=false,bool pressed=false)
{
    hdHudSetItemEnabled(kItemFid,enabled);
    // Select the image before disabling: GNW has no disabled image for this
    // button, so changing currentImage after disabling leaves its old pixels.
    intfaceHdHudTestPress(pressed);
    intfaceHdHudTestSet(fid,disabled);
    win_draw(intfaceHdHudTestWindow());
}
void captureEquippedItem(Report& report, const std::filesystem::path& out, bool expected)
{
    const Inventory original = obj_dude->data.inventory;
    const int hp = obj_dude->data.critter.hp, ap = obj_dude->data.critter.combat.ap;
    const int actorFid = obj_dude->fid, hand = intface_is_item_right_hand();
    std::vector<InventoryItem> items;
    std::vector<std::pair<Object*, int>> flags;
    Object* item = nullptr;
    for (int i = 0; i < original.length; ++i) {
        items.push_back(original.items[i]);
        Object* sourceItem = original.items[i].item;
        flags.emplace_back(sourceItem, sourceItem->flags);
        if (sourceItem->pid == kItemPid) item = sourceItem;
    }
    Object* temporary = nullptr;
    if (!item) {
        if (obj_new(&temporary, itemWorldFid(), kItemPid) == -1 || !temporary) {
            report.check(false, "create real selected item PID for equipped HUD preview");
            return;
        }
        item = temporary;
        temporary->flags |= OBJECT_HIDDEN | OBJECT_NO_SAVE;
        temporary->owner = obj_dude;
        items.push_back({ temporary, 1 });
    }
    const int originalAmmo = item_w_curr_ammo(item);
    // A temporary inventory view avoids stack merging or reallocating the
    // player's real inventory; equipment uses actual objects and hand flags.
    obj_dude->data.inventory = { static_cast<int>(items.size()), static_cast<int>(items.size()), items.data() };
    for (const auto& entry : flags) entry.first->flags &= ~OBJECT_IN_ANY_HAND;
    intface_update_items(false);
    item->flags |= hand == HAND_RIGHT ? OBJECT_IN_RIGHT_HAND : OBJECT_IN_LEFT_HAND;
    const int updated = intface_update_items(false);
    Object* selected = nullptr;
    int hitMode = -1;
    bool aiming = false;
    const bool selectedCorrectly=updated == 0 && intface_get_current_item(&selected) == 0 && selected == item
            && item_inv_fid(item) == kItemFid;
    if (kItemPid==29 || kItemPid==30 || kItemPid==40) {
        report.check(selectedCorrectly && item_get_type(item)==(kItemPid==40?ITEM_TYPE_DRUG:ITEM_TYPE_AMMO) && intface_get_attack(&hitMode,&aiming)==-1,
            "real equipped non-weapon resolves correct art and retains non-weapon action");
    } else {
    report.check(selectedCorrectly && intface_get_attack(&hitMode, &aiming) == 0 && !aiming
            && hitMode == (hand == HAND_RIGHT ? HIT_MODE_RIGHT_WEAPON_PRIMARY : HIT_MODE_LEFT_WEAPON_PRIMARY)
            && item_hit_with(obj_dude, hitMode) == item && item_w_anim(obj_dude, hitMode) == (kItemPid==79 || kItemPid==205?ANIM_THROW_ANIM:kItemPid==21?ANIM_THROW_PUNCH:(kItemPid==8?ANIM_FIRE_SINGLE:ANIM_SWING_ANIM))
            && item_w_mp_cost(obj_dude, hitMode, false) > 0,
        "real equipped item resolves inventory art, weapon animation and AP through intface_update_items");
    }
    hdHudSetItemEnabled(kItemFid,true);
    intface_update_items(false);
    win_draw(intfaceHdHudTestWindow());
    for (const auto& size : std::vector<std::pair<int, int>> { { 1920, 1080 }, { 3840, 2160 } }) {
        const std::string suffix = std::to_string(size.first) + "x" + std::to_string(size.second);
        auto equipped = capture(out / ("equipped-item-" + suffix + ".bmp"), size.first, size.second);
        report.check(equipped.valid && equipped.restored && (expected ? hudOwners() > 0 : hudOwners() == 0),
            suffix + " real equipped item capture and owners follow loaded/fallback state");
    }
    for (const auto& entry : flags) entry.first->flags = entry.second;
    obj_dude->data.inventory = original;
    // Drop the HUD's reference before destroying the temporary object.
    intface_update_items(false);
    report.check(item_w_curr_ammo(item)==originalAmmo,"equipped HD rendering preserves ammunition quantity");
    if (temporary) {
        temporary->owner = nullptr;
        report.check(obj_erase_object(temporary, nullptr) == 0, "temporary preview item removed from object registry");
    }
    bool restoredFlags = true;
    for (const auto& entry : flags) restoredFlags = restoredFlags && entry.first->flags == entry.second;
    report.check(restoredFlags && obj_dude->data.inventory.items == original.items
            && obj_dude->data.inventory.length == original.length && obj_dude->data.inventory.capacity == original.capacity
            && obj_dude->data.critter.hp == hp && obj_dude->data.critter.combat.ap == ap
            && obj_dude->fid == actorFid && intface_is_item_right_hand() == hand,
        "real equipped preview restores inventory allocation, flags, HP, AP and actor FID without saving");
}
void captureDragCursor(Report& report,const std::filesystem::path& out,bool expected,const Rect& inventoryRect)
{
    mouse_hide();auto base=capture();
    report.check(inventoryHdTest(7,kItemPid)!=-1,"real inventory drag shape initialized");
    report.check(hdHudDragCursorActive()==expected,"drag cursor HD availability or classic fallback");
    for(auto size:std::vector<std::pair<int,int>>{{1920,1080},{3840,2160}}) {
        int position=0;
        for(auto point:std::vector<std::pair<int,int>>{{inventoryRect.ulx+78,inventoryRect.uly+60},{inventoryRect.ulx+350,inventoryRect.uly+220},{10,10},{screenGetWidth()-1,screenGetHeight()-1}}) {
            mouse_hide();hdHudSetDragCursor(-1);mouse_set_position(point.first,point.second);mouse_show();
            auto classic=capture({},size.first,size.second);
            mouse_hide();auto background=capture({},size.first,size.second);
            std::vector<unsigned int> owners;
            auto* pixels=static_cast<unsigned char*>(gSdlSurface->pixels);
            for(int y=0;y<gSdlSurface->h;++y)for(int x=0;x<gSdlSurface->w;++x) owners.push_back(hdWorldOwnerAt(pixels+y*gSdlSurface->pitch+x));
            hdHudSetDragCursor(kItemFid);mouse_show();Rect cursor;mouse_get_rect(&cursor);
            std::string suffix=std::to_string(size.first)+"x"+std::to_string(size.second)+"-"+std::to_string(position++);
            auto hd=capture(out/("drag-"+suffix+".bmp"),size.first,size.second);
            report.check(hd.valid&&hd.restored&&(expected?hd.pixels!=classic.pixels:hd.pixels==classic.pixels),suffix+" drag HD detail or exact classic fallback");
            report.check(sameRegion(background,hd,cursor,false),suffix+" drag affects only cursor rectangle including screen clipping");
            if(expected) {
                bool same=true;size_t at=0;
                for(int y=0;y<gSdlSurface->h;++y)for(int x=0;x<gSdlSurface->w;++x) same &= owners[at++]==hdWorldOwnerAt(pixels+y*gSdlSurface->pitch+x);
                report.check(same,suffix+" cursor preserves underlying HD ownership without palette holes");
            }
            mouse_hide();report.check(capture({},size.first,size.second).pixels==background.pixels,suffix+" hiding dragged item restores exact background");
        }
    }
    mouse_set_position(inventoryRect.ulx+350,inventoryRect.uly+220);mouse_show();
    tile_refresh_display();win_refresh_all(&scr_size);auto before=capture();
    handleWindowSizeChanged();tile_refresh_display();win_refresh_all(&scr_size);mouse_show();
    report.check(capture().pixels==before.pixels,"renderer recreation restores active HD drag cursor exactly");
    // Exercise two different cached textures in one renderer, not just in
    // separate test processes. Preserve the real mouse hotspot during swaps.
    inventoryHdTest(8,kItemPid);
    int otherPid=kItemPid==4?8:4;
    int otherFid=otherPid==8?0x07000004:0x07000060;
    inventoryHdTest(7,otherPid);mouse_show();
    report.check(hdHudDragCursorActive()==hdHudAvailable(otherFid) && capture().pixels!=before.pixels,
        "switching between different item drag cursors selects distinct texture");
    inventoryHdTest(8,otherPid);
    inventoryHdTest(7,kItemPid);mouse_show();
    report.check(capture().pixels==before.pixels,"switching back restores exact target cursor and hotspot");
    inventoryHdTest(8,kItemPid);
    report.check(!hdHudDragCursorActive(),"release resets HD drag on ordinary inventory cursor");
    mouse_hide();
    report.check(capture().pixels==base.pixels,"drag cursor release leaves no trails in inventory");
}

void captureInventory(Report& report,const std::filesystem::path& out,bool expected)
{
    int quantity=inven_pid_quantity_carried(obj_dude,kItemPid);
    int hp=obj_dude->data.critter.hp, ap=obj_dude->data.critter.combat.ap;
    intface_hide();
    int window=inventoryHdTest(0,kItemPid);
    report.check(window!=-1 && quantity>0,"real inventory opened with selected item");
    if(window==-1) return;
    mouse_hide();
    Rect rect{};win_get_rect(window,&rect);
    for(auto size:std::vector<std::pair<int,int>>{{1920,1080},{3840,2160}}) {
        std::string suffix=std::to_string(size.first)+"x"+std::to_string(size.second);
        hdHudSetItemEnabled(kItemFid,false);inventoryHdTest(1,kItemPid);auto classic=capture(out/("inventory-classic-"+suffix+".bmp"),size.first,size.second);
        hdHudSetItemEnabled(kItemFid,true);inventoryHdTest(1,kItemPid);auto hd=capture(out/("inventory-hd-"+suffix+".bmp"),size.first,size.second);
        report.check(hd.valid&&hd.restored&&(expected?hd.pixels!=classic.pixels:hd.pixels==classic.pixels),suffix+" inventory HD or exact FRM fallback");
        report.check(sameRegion(classic,hd,rect,false),suffix+" inventory replacement does not affect pixels outside window");
        report.check(expected?hudOwners()>0:hudOwners()==0,suffix+" actual item list has HD ownership");
    }
    auto base=capture();
    captureDragCursor(report,out,expected,rect);
    inventoryHdTest(6,kItemPid);auto stacked=capture(out/"inventory-stack-3840x2160.bmp",3840,2160);
    report.check(stacked.valid,"stack quantity rendered over HD item");
    inventoryHdTest(1,kItemPid);report.check(capture().pixels==base.pixels,"removing quantity annotation restores exact item");
    inventoryHdTest(2,kItemPid);report.check(hudOwners()==0,"scrolling item off list removes HD pixels");
    inventoryHdTest(1,kItemPid);report.check(capture().pixels==base.pixels,"scrolling back restores exact inventory frame");
    int cover=win_add(rect.ulx,rect.uly,499,377,colorTable[31744],WINDOW_MODAL|WINDOW_MOVE_ON_TOP);
    win_draw(cover);report.check(hudOwners()==0,"upper opaque window hides all inventory HD pixels");
    win_delete(cover);report.check(capture().pixels==base.pixels,"closing upper window restores inventory item");
    inventoryHdTest(3,kItemPid);
    report.check(expected?hudOwners()>0:hudOwners()==0,"moving real item from list to hand uses HD slot");
    capture(out/"inventory-hand-3840x2160.bmp",3840,2160);
    inventoryHdTest(4,kItemPid);inventoryHdTest(1,kItemPid);
    report.check(expected?hudOwners()>0:hudOwners()==0,"moving item back to list restores HD icon");
    inventoryHdTest(5,kItemPid);mouse_hide();
    report.check(hudOwners()==0,"closing inventory leaves no stale HD icon");
    report.check(inven_pid_quantity_carried(obj_dude,kItemPid)==quantity&&obj_dude->data.critter.hp==hp&&obj_dude->data.critter.combat.ap==ap,"inventory rendering and transfers preserve item quantity HP and AP");
    intface_show();
}
void captureFlareIgnition(Report& report,const std::filesystem::path& out)
{
    const Inventory original=obj_dude->data.inventory;
    const int hp=obj_dude->data.critter.hp,ap=obj_dude->data.critter.combat.ap;
    const int hand=intface_is_item_right_hand();
    std::vector<InventoryItem> items;
    std::vector<std::pair<Object*,int>> flags;
    for(int i=0;i<original.length;++i) {
        items.push_back(original.items[i]);
        flags.emplace_back(original.items[i].item,original.items[i].item->flags);
    }
    Object* flare=nullptr;
    report.check(obj_new(&flare,46,79)==0 && flare,"create isolated unlit flare for actual ignition");
    if(!flare)return;
    flare->flags|=OBJECT_HIDDEN|OBJECT_NO_SAVE;flare->owner=obj_dude;
    items.push_back({flare,1});
    obj_dude->data.inventory={static_cast<int>(items.size()),static_cast<int>(items.size()),items.data()};
    for(const auto& entry:flags)entry.first->flags&=~OBJECT_IN_ANY_HAND;
    intface_update_items(false);
    flare->flags|=hand==HAND_RIGHT?OBJECT_IN_RIGHT_HAND:OBJECT_IN_LEFT_HAND;
    intface_update_items(false);win_draw(intfaceHdHudTestWindow());
    auto before=capture(out/"ignition-unlit-3840x2160.bmp",3840,2160);
    report.check(item_inv_fid(flare)==0x0700003B && !queue_find(flare,EVENT_TYPE_FLARE)
        && before.valid && (hudOwners(0x0700003B)>0)==hdHudAvailable(0x0700003B),"unlit flare uses unlit art without a burn timer");
    const int used=protinst_use_item(obj_dude,flare);
    report.check(used==0 && flare->pid==205 && item_inv_fid(flare)==0x0700007B
        && flare->lightDistance==8 && flare->lightIntensity==0x10000 && queue_find(flare,EVENT_TYPE_FLARE),
        "actual use changes the same object to lit PID/FID, light and burn timer");
    intface_update_items(false);win_draw(intfaceHdHudTestWindow());
    auto after=capture(out/"ignition-lit-3840x2160.bmp",3840,2160);
    report.check(after.valid && after.restored && before.pixels!=after.pixels && hudOwners(0x0700003B)==0
        && (hudOwners(0x0700007B)>0)==hdHudAvailable(0x0700007B),"same equipped object switches icon and clears unlit HD metadata");
    queue_remove(flare);
    for(const auto& entry:flags)entry.first->flags=entry.second;
    obj_dude->data.inventory=original;intface_update_items(false);
    flare->owner=nullptr;
    report.check(obj_erase_object(flare,nullptr)==0 && obj_dude->data.critter.hp==hp && obj_dude->data.critter.combat.ap==ap
        && obj_dude->data.inventory.items==original.items,"ignition fixture and timer removed without changing player inventory HP or AP");
}
} // namespace
int hdHudPreview(const char* directory)
{
    const char* pidText=SDL_getenv("FALLOUT_HD_HUD_ITEM_PID");
    kItemPid=pidText?std::atoi(pidText):4;
    if(kItemPid!=4 && kItemPid!=8 && kItemPid!=21 && kItemPid!=29 && kItemPid!=30 && kItemPid!=40 && kItemPid!=79 && kItemPid!=205) return 53;
    kItemFid=kItemPid==79?0x0700003B:kItemPid==205?0x0700007B:kItemPid==40?0x07000073:kItemPid==29?0x0700001F:(kItemPid==30?0x0700001E:(kItemPid==21?0x0700008C:(kItemPid==8?0x07000004:0x07000060)));
    hdHudSetEnabled(true);
    std::filesystem::path out(directory);std::filesystem::create_directories(out);Report report(out);
    map_disable_bk_processes();scr_disable();cycle_disable();gmouse_disable_scrolling();mouse_hide();
    bool expected=true;if(const char* s=SDL_getenv("FALLOUT_HD_HUD_EXPECT_LOADED"))expected=std::strcmp(s,"0")!=0;
    const int hp=obj_dude->data.critter.hp,ap=obj_dude->data.critter.combat.ap;
    auto* inventory=obj_dude->data.inventory.items;int inventoryCount=obj_dude->data.inventory.length;
    hdWorldSetEnabled(true);hdHudSetItemEnabled(kItemFid,true);intface_show();
    report.check(hdHudAvailable(kItemFid)==expected,"asset availability matches requested loaded/fallback case");
    int win=intfaceHdHudTestWindow();Rect wr{};report.check(win!=-1&&win_get_rect(win,&wr)==0,"real HUD window initialized");
    if(win==-1)return 51;
    if(const char* expectedPanel=SDL_getenv("FALLOUT_HD_HUD_PANEL_EXPECT")) {
        const bool panelExpected=std::strcmp(expectedPanel,"0")!=0;
        report.check(hdHudPanelAvailable()==panelExpected,"HUD panel exact asset dimensions/header or safe classic fallback");
        hdWorldSetTerminalPreviewPhase(0);
        for(auto size:std::vector<std::pair<int,int>>{{1920,1080},{3840,2160}}) {
            hdHudSetItemEnabled(kHdHudPanelFid,false);auto before=capture({},size.first,size.second);
            hdHudSetItemEnabled(kHdHudPanelFid,true);auto after=capture(out/("panel-shell-"+std::to_string(size.first)+".bmp"),size.first,size.second);
            report.check(before.valid&&after.valid&&after.restored,"panel SDL capture and renderer state restored "+std::to_string(size.first));
            report.check(sameRegion(before,after,wr,false),"panel never changes pixels outside its GNW window "+std::to_string(size.first));
            report.check(panelExpected?!sameRegion(before,after,wr,true):before.pixels==after.pixels,"panel detail or exact unavailable-asset fallback "+std::to_string(size.first));
        }
        auto closed=capture();intface_end_window_open(false);auto open=capture(out/"panel-combat-open.bmp");
        intface_end_window_close(false);auto reclosed=capture(out/"panel-combat-closed.bmp");
        report.check(closed.valid&&open.valid&&closed.pixels!=open.pixels,"real combat hatch opens to working buttons");
        if(panelExpected) report.check(closed.pixels==reclosed.pixels,"closing combat hatch restores exact approved panel");
        else {
            // iface.frm's baked hatch differs from endanim.frm frame zero in
            // the original game. Fallback must follow that actual animation,
            // then remain stable on subsequent open/close cycles.
            intface_end_window_open(false);intface_end_window_close(false);auto again=capture();
            Rect hatch{wr.ulx+580,wr.uly+38,wr.ulx+636,wr.uly+95};
            report.check(sameRegion(closed,reclosed,hatch,false)&&reclosed.pixels==again.pixels,
                "classic fallback hatch changes only its original animation area and remains stable");
        }
        Window* hudWindow=GNW_find(win);
        for(Button* b=hudWindow?hudWindow->buttonListHead:nullptr;b;b=b->next) {
            if(!b->normalImage||!b->pressedImage||b->id==intfaceHdHudTestButton()) continue;
            b->currentImage=b->normalImage;win_draw(win);auto up=capture();
            b->currentImage=b->pressedImage;win_draw(win);auto down=capture();
            b->currentImage=b->normalImage;win_draw(win);auto returned=capture();
            report.check(up.valid&&down.valid&&up.pixels!=down.pixels&&up.pixels==returned.pixels,
                "real GNW button pressed/normal restoration "+std::to_string(b->id));
        }
        char message[]="You see: Cave wall.";display_print(message);win_draw(win);
        int green=0,glass=0;auto* pixels=static_cast<unsigned char*>(gSdlSurface->pixels);
        for(int y=24;y<84;++y)for(int x=23;x<190;++x) {
            auto* cell=pixels+(wr.uly+y)*gSdlSurface->pitch+wr.ulx+x;
            green+=*cell==colorTable[992]&&hdWorldOwnerAt(cell)==0;
            auto owner=hdWorldOwnerAt(cell);glass+=(owner>>24)==251&&hdHudTexelMatches(owner&0xFFFFFF,kHdHudPanelFid);
        }
        report.check(green>0&&(!panelExpected||glass>0),"live log glyphs remain visible over HD glass without opaque text rectangles");
        capture(out/"panel-log-3840.bmp",3840,2160);
    }
    Rect button{wr.ulx+267,wr.uly+26,wr.ulx+267+187,wr.uly+26+66};
    for(const auto& size:std::vector<std::pair<int,int>>{{1920,1080},{3840,2160}}) {
        std::string suffix=std::to_string(size.first)+"x"+std::to_string(size.second);
        redraw(false);auto classic=capture(out/("classic-"+suffix+".bmp"),size.first,size.second);
        redraw(true);auto normal=capture(out/("normal-"+suffix+".bmp"),size.first,size.second);
        report.check(classic.valid&&normal.valid&&normal.restored,suffix+" actual SDL capture and renderer state restoration");
        report.check(sameRegion(classic,normal,button,false),suffix+" changes restricted to weapon button");
        report.check(expected?!sameRegion(classic,normal,button,true):classic.pixels==normal.pixels,suffix+" HD detail or exact classic fallback");
        report.check(expected?hudOwners()>0:hudOwners()==0,suffix+" HUD owners present only for loaded HD asset");
        redraw(true,kItemFid,false,true);auto down=capture(out/("pressed-"+suffix+".bmp"),size.first,size.second);
        report.check(down.valid&&down.restored&&down.pixels!=normal.pixels,suffix+" pressed state renders distinct image");
        redraw(false,kItemFid,false,true);auto downClassic=capture({},size.first,size.second);
        report.check(expected?!sameRegion(downClassic,down,button,true):downClassic.pixels==down.pixels,suffix+" pressed HD or exact fallback");
        redraw(true,kItemFid,true);auto disabled=capture(out/("disabled-"+suffix+".bmp"),size.first,size.second);
        redraw(false,kItemFid,true);auto disabledClassic=capture({},size.first,size.second);
        report.check(disabled.valid&&disabled.restored,suffix+" disabled actual SDL capture");
        report.check(expected?!sameRegion(disabledClassic,disabled,button,true):disabledClassic.pixels==disabled.pixels,suffix+" disabled HD or exact fallback");
        redraw(true);report.check(capture({},size.first,size.second).pixels==normal.pixels,suffix+" return to normal restores exact frame");
    }
    redraw(true);auto base=capture(out/"normal-native.bmp");
    hdWorldSetEnabled(false);redraw(false);auto classicWorld=capture();redraw(true);auto hdWithClassicWorld=capture(out/"hd-item-classic-world.bmp");
    report.check(expected?!sameRegion(classicWorld,hdWithClassicWorld,button,true):classicWorld.pixels==hdWithClassicWorld.pixels,"HUD operates independently from HD world toggle");
    hdWorldSetEnabled(true);redraw(true);
    int overlapOwners=0;auto* screenBeforeOverlay=static_cast<unsigned char*>(gSdlSurface->pixels);
    for(int y=button.uly+16;y<button.uly+52;++y)for(int x=button.ulx+66;x<button.ulx+118;++x)
        overlapOwners+=(hdWorldOwnerAt(screenBeforeOverlay+y*gSdlSurface->pitch+x)>>24)==251;
    report.check(!expected||overlapOwners>0,"occlusion test rectangle overlaps actual HD item pixels");
    int overlay=win_add(button.ulx+65,button.uly+15,54,38,colorTable[31744],WINDOW_MODAL|WINDOW_MOVE_ON_TOP);
    report.check(overlay!=-1,"opaque GNW window over item created");
    if(overlay!=-1){
        win_draw(overlay);auto covered=capture(out/"occluded.bmp");
        Rect region{button.ulx+66,button.uly+16,button.ulx+117,button.uly+51};
        redraw(false);win_draw(overlay);auto coveredClassic=capture();
        report.check(sameRegion(covered,coveredClassic,region,true),"HD never paints through higher GNW window");
        win_delete(overlay);redraw(true);report.check(capture().pixels==base.pixels,"removing occluder restores exact HUD frame");
    }
    gmouse_set_cursor(MOUSE_CURSOR_ARROW);unsigned char* shape=nullptr;int cw,ch,cp,hx,hy;char transparent;
    mouse_get_shape(&shape,&cw,&ch,&cp,&hx,&hy,&transparent);
    int cx=button.ulx+75,cy=button.uly+27,best=0;
    auto* cursorScreen=static_cast<unsigned char*>(gSdlSurface->pixels);
    // Select a location that exercises BOTH opaque and transparent cursor
    // pixels over actual HUD art; a fixed location can accidentally miss it.
    if(expected)for(int y=button.uly;y+ch<=button.lry+1;++y)for(int x=button.ulx;x+cw<=button.lrx+1;++x){
        int opaque=0,holes=0;
        for(int sy=0;sy<ch;++sy)for(int sx=0;sx<cw;++sx)if((hdWorldOwnerAt(cursorScreen+(y+sy)*gSdlSurface->pitch+x+sx)>>24)==251){
            if(shape[sy*cp+sx]==static_cast<unsigned char>(transparent))++holes;else ++opaque;
        }
        if(opaque>0&&holes>0&&opaque+holes>best){best=opaque+holes;cx=x;cy=y;}
    }
    report.check(!expected||best>0,"cursor test intersects opaque and transparent cursor pixels with actual HD item");
    std::vector<unsigned int> owners(size_t(cw)*ch);auto* screen=static_cast<unsigned char*>(gSdlSurface->pixels);
    for(int y=0;y<ch;++y)for(int x=0;x<cw;++x)owners[size_t(y)*cw+x]=hdWorldOwnerAt(screen+(cy+y)*gSdlSurface->pitch+cx+x);
    mouse_set_position(cx+hx,cy+hy);mouse_show();int bad=0,coveredHud=0,preservedTransparentHud=0;
    for(int y=0;y<ch;++y)for(int x=0;x<cw;++x){unsigned int owner=hdWorldOwnerAt(screen+(cy+y)*gSdlSurface->pitch+cx+x);auto before=owners[size_t(y)*cw+x];
        if(shape[y*cp+x]==static_cast<unsigned char>(transparent)){if(owner!=before)++bad;if((before>>24)==251)++preservedTransparentHud;}else{if(owner)++bad;if((before>>24)==251)++coveredHud;}}
    report.check(bad==0&&(!expected||(coveredHud>0&&preservedTransparentHud>0)),"real cursor clears opaque HUD owners and retains transparent holes");
    report.check(capture(out/"cursor.bmp").valid,"actual cursor capture");mouse_hide();gmouse_set_cursor(MOUSE_CURSOR_NONE);redraw(true);
    intface_hide();report.check(hudOwners()==0,"hidden HUD has no stale item owners");intface_show();redraw(true);
    redraw(true,-1);report.check(hudOwners()==0,"switching to empty hand removes item metadata");
    redraw(true);tile_refresh_display();win_refresh_all(&scr_size);auto beforeRecreate=capture();
    handleWindowSizeChanged();tile_refresh_display();redraw(true);win_refresh_all(&scr_size);
    auto recreated=capture(out/"renderer-recreated.bmp");
    report.check(recreated.valid&&recreated.restored&&recreated.pixels==beforeRecreate.pixels,"renderer recreation restores exact HD item");
    report.check(obj_dude->data.critter.hp==hp&&obj_dude->data.critter.combat.ap==ap&&obj_dude->data.inventory.items==inventory&&obj_dude->data.inventory.length==inventoryCount,"HUD preview leaves HP AP and inventory unchanged");
    captureEquippedItem(report, out, expected);
    // Test-only fixture for items absent from the starting inventory. Use the
    // actual engine allocation/transfer APIs and remove it before returning.
    Object* inventoryFixture=nullptr;
    const int priorQuantity=inven_pid_quantity_carried(obj_dude,kItemPid);
    if(priorQuantity==0) {
        bool created=obj_new(&inventoryFixture,itemWorldFid(),kItemPid)==0 && inventoryFixture;
        if(created) inventoryFixture->flags|=OBJECT_HIDDEN|OBJECT_NO_SAVE;
        bool added=created && item_add_force(obj_dude,inventoryFixture,1)==0;
        report.check(added,"create temporary real inventory item for absent starting equipment");
        if(added) {
            auto& entries=obj_dude->data.inventory;
            for(int i=0;i<entries.length;++i) if(entries.items[i].item==inventoryFixture) {
                std::rotate(entries.items,entries.items+i,entries.items+i+1);break;
            }
        }
    }
    captureInventory(report, out, expected);
    if(inventoryFixture) {
        bool removed=item_remove_mult(obj_dude,inventoryFixture,1)==0;
        if(removed) removed=obj_erase_object(inventoryFixture,nullptr)==0;
        report.check(removed && inven_pid_quantity_carried(obj_dude,kItemPid)==priorQuantity,
            "temporary inventory item removed without changing original quantity");
    }
    if(kItemPid==79 && expected)captureFlareIgnition(report,out);
    std::ofstream result(out/"result.json");result<<"{\n  \"passed\": "<<report.passed<<",\n  \"failed\": "<<report.failed<<",\n  \"expected_loaded\": "<<(expected?"true":"false")<<"\n}\n";
    report.log<<"TOTAL "<<report.passed<<" PASS "<<report.failed<<" FAIL"<<std::endl;
    return report.failed?52:0;
}
} // namespace fallout

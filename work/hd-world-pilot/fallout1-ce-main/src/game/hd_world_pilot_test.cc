#include "game/hd_world_pilot_test.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <set>
#include <string>
#include <vector>

#include "game/anim.h"
#include "game/art.h"
#include "game/cycle.h"
#include "game/combat.h"
#include "game/combat_message_compat.h"
#include "game/critter.h"
#include "game/hd_player.h"
#include "game/roll.h"
#include "game/stat.h"
#include "plib/gnw/input.h"
#include "game/config.h"
#include "game/game.h"
#include "game/gconfig.h"
#include "game/gmouse.h"
#include "game/graphlib.h"
#include "game/hd_world_pilot.h"
#include "game/intface.h"
#include "game/light.h"
#include "game/map.h"
#include "game/object.h"
#include "game/palette.h"
#include "game/proto.h"
#include "game/scripts.h"
#include "game/tile.h"
#include "plib/color/color.h"
#include "plib/gnw/gnw.h"
#include "plib/gnw/kb.h"
#include "plib/gnw/mouse.h"
#include "plib/gnw/svga.h"

namespace fallout {
namespace {

constexpr int kRockFid = 33554605;
constexpr int kRockPid = 33554510;
constexpr int kFloorId = 21;

int expectedAssetCount()
{
    const char* value = SDL_getenv("FALLOUT_HD_WORLD_EXPECT_COUNT");
    if (value == nullptr || value[0] == '\0') return 159;
    char* end = nullptr;
    long count = std::strtol(value, &end, 10);
    return end != value && *end == '\0' && count >= 159 && count < 256
        ? static_cast<int>(count) : -1;
}

struct Report {
    std::ofstream text;
    int passed = 0;
    int failed = 0;
    explicit Report(const std::filesystem::path& directory)
        : text(directory / "checks.txt") {}
    void check(bool ok, const std::string& name)
    {
        text << (ok ? "PASS " : "FAIL ") << name << std::endl;
        if (ok) ++passed;
        else ++failed;
    }
};

std::vector<Object*> objects()
{
    std::set<Object*> unique;
    for (Object* object = obj_find_first(); object != nullptr; object = obj_find_next()) {
        unique.insert(object);
    }
    return { unique.begin(), unique.end() };
}

struct Snapshot {
    std::vector<Object*> blockers;
    std::vector<int> squares;
    std::vector<std::array<int, 20>> objects;
    std::vector<std::vector<unsigned char>> paths;
    uint64_t collisionHash = 1469598103934665603ULL;
    int blocked = 0;
};

void hashWord(uint64_t& hash, int value)
{
    for (int byte = 0; byte < 4; ++byte) {
        hash ^= (static_cast<uint32_t>(value) >> (byte * 8)) & 255;
        hash *= 1099511628211ULL;
    }
}

Snapshot snapshot(const std::vector<int>& destinations)
{
    Snapshot result;
    result.blockers.reserve(ELEVATION_COUNT * HEX_GRID_SIZE);
    for (int elevation = 0; elevation < ELEVATION_COUNT; ++elevation) {
        for (int tile = 0; tile < HEX_GRID_SIZE; ++tile) {
            Object* blocker = obj_blocking_at(obj_dude, tile, elevation);
            result.blockers.push_back(blocker);
            if (blocker != nullptr) ++result.blocked;
            hashWord(result.collisionHash, blocker != nullptr ? blocker->id : -1);
            hashWord(result.collisionHash, blocker != nullptr ? blocker->pid : -1);
            hashWord(result.collisionHash, blocker != nullptr ? blocker->flags : 0);
        }
        result.squares.insert(result.squares.end(), square[elevation]->field_0,
            square[elevation]->field_0 + SQUARE_GRID_SIZE);
    }
    for (Object* object : objects()) {
        // sx/sy are render caches, so deliberately absent from game-state proof.
        result.objects.push_back({ object->id, object->tile, object->x, object->y,
            object->frame, object->rotation, object->fid, object->flags,
            object->elevation, object->pid, object->cid, object->lightDistance,
            object->lightIntensity, object->outline, object->sid, object->field_80,
            object->field_2C_array[0], object->field_2C_array[1],
            object->field_2C_array[2], object->field_2C_array[3] });
    }
    for (int destination : destinations) {
        unsigned char rotations[2000] = {};
        int length = make_path(obj_dude, obj_dude->tile, destination, rotations, 1);
        if (length < 0 || length > 2000) length = 0;
        result.paths.emplace_back(rotations, rotations + length);
    }
    return result;
}

void compare(Report& report, const Snapshot& before, const Snapshot& after,
    const std::string& name)
{
    report.check(before.blockers == after.blockers, name + " all 120000 hex blockers unchanged");
    report.check(before.squares == after.squares, name + " all 30000 floor/roof words unchanged");
    report.check(before.objects == after.objects, name + " original object game fields unchanged");
    report.check(before.paths == after.paths, name + " original pathfinder routes unchanged");
}

struct Capture {
    int width = 0;
    int height = 0;
    bool valid = false;
    bool hdDrawn = false;
    bool stateRestored = false;
    int floorPixels = 0;
    int rockPixels = 0;
    std::vector<uint32_t> pixels;
};

Capture capture(const std::filesystem::path& path, bool enabled, int targetWidth = 0, int targetHeight = 0)
{
    Capture result;
    hdWorldSetEnabled(enabled);
    SDL_GetRendererOutputSize(gSdlRenderer, &result.width, &result.height);
    if (targetWidth > 0 && targetHeight > 0) {
        result.width = targetWidth;
        result.height = targetHeight;
    }
    if (result.width <= 0 || result.height <= 0) return result;
    SDL_Texture* previousTarget = SDL_GetRenderTarget(gSdlRenderer);
    int savedW, savedH;
    SDL_Rect savedViewport, savedClip;
    float savedX, savedY;
    SDL_RenderGetLogicalSize(gSdlRenderer, &savedW, &savedH);
    SDL_RenderGetViewport(gSdlRenderer, &savedViewport);
    SDL_RenderGetClipRect(gSdlRenderer, &savedClip);
    SDL_RenderGetScale(gSdlRenderer, &savedX, &savedY);
    SDL_bool savedClipped = SDL_RenderIsClipEnabled(gSdlRenderer);
    SDL_Texture* target = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_TARGET, result.width, result.height);
    if (target == nullptr) return result;
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
    result.hdDrawn = hdWorldRender();
    result.floorPixels = hdWorldVisiblePixels(1);
    result.rockPixels = hdWorldVisiblePixels(2);
    SDL_RenderGetLogicalSize(gSdlRenderer, &afterW, &afterH);
    SDL_RenderGetViewport(gSdlRenderer, &afterViewport);
    SDL_RenderGetClipRect(gSdlRenderer, &afterClip);
    SDL_RenderGetScale(gSdlRenderer, &afterX, &afterY);
    result.stateRestored = beforeW == afterW && beforeH == afterH
        && beforeX == afterX && beforeY == afterY
        && std::memcmp(&beforeViewport, &afterViewport, sizeof(SDL_Rect)) == 0
        && beforeClipped == SDL_RenderIsClipEnabled(gSdlRenderer)
        && (beforeClipped == SDL_FALSE || std::memcmp(&beforeClip, &afterClip, sizeof(SDL_Rect)) == 0);
    SDL_Surface* surface = SDL_CreateRGBSurfaceWithFormat(0, result.width, result.height,
        32, SDL_PIXELFORMAT_ARGB8888);
    if (surface != nullptr) {
        // Read physical pixels before SDL_RenderPresent invalidates the backbuffer.
        SDL_RenderSetLogicalSize(gSdlRenderer, 0, 0);
        SDL_RenderSetScale(gSdlRenderer, 1.0F, 1.0F);
        SDL_RenderSetViewport(gSdlRenderer, nullptr);
        SDL_RenderSetClipRect(gSdlRenderer, nullptr);
        SDL_Rect full { 0, 0, result.width, result.height };
        result.valid = SDL_RenderReadPixels(gSdlRenderer, &full, surface->format->format,
            surface->pixels, surface->pitch) == 0;
        if (result.valid) {
            result.pixels.resize(static_cast<size_t>(result.width) * result.height);
            for (int y = 0; y < result.height; ++y) {
                std::memcpy(result.pixels.data() + static_cast<size_t>(y) * result.width,
                    static_cast<unsigned char*>(surface->pixels) + y * surface->pitch,
                    static_cast<size_t>(result.width) * sizeof(uint32_t));
            }
            if (!path.empty()) result.valid = SDL_SaveBMP(surface, path.string().c_str()) == 0;
        }
        SDL_FreeSurface(surface);
    }
    SDL_SetRenderTarget(gSdlRenderer, previousTarget);
    SDL_RenderSetLogicalSize(gSdlRenderer, savedW, savedH);
    SDL_RenderSetScale(gSdlRenderer, savedX, savedY);
    SDL_RenderSetViewport(gSdlRenderer, &savedViewport);
    SDL_RenderSetClipRect(gSdlRenderer, savedClipped == SDL_TRUE ? &savedClip : nullptr);
    SDL_DestroyTexture(target);
    return result;
}

void terminalRegression(const std::filesystem::path& output, Report& report)
{
    const char* expected = SDL_getenv("FALLOUT_HD_TERMINAL_EXPECT_LOADED");
    const bool shouldLoad = !expected || std::atoi(expected) != 0;
    report.check(hdWorldTerminalIndicatorLoaded() == shouldLoad, "terminal optional companion expected load state");
    report.check(hdWorldTerminalLampOnAt(0) && hdWorldTerminalLampOnAt(499)
        && !hdWorldTerminalLampOnAt(500) && !hdWorldTerminalLampOnAt(1599)
        && hdWorldTerminalLampOnAt(1600), "terminal 500ms on / 1100ms off clock boundaries");
    const Snapshot before = snapshot({});
    tile_refresh_display();
    const int id = hdWorldResolveAsset(0x0200006E);
    const Capture classic = capture({}, false);
    hdWorldSetTerminalPreviewPhase(0);
    const Capture off = capture(output / "terminal-off.bmp", true);
    hdWorldSetTerminalPreviewPhase(1);
    const Capture on = capture(output / "terminal-on.bmp", true);
    report.check(id > 0 && hdWorldVisiblePixels(id) > 0 && off.valid && on.valid,
        "original terminal visible in real entrance render");
    int changed = 0, outside = 0, green = 0;
    auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
    if (off.valid && on.valid && off.pixels.size() == on.pixels.size()) {
        for (int y = 0; y < on.height; ++y) for (int x = 0; x < on.width; ++x) {
            const size_t at = static_cast<size_t>(y) * on.width + x;
            if (off.pixels[at] == on.pixels[at]) continue;
            ++changed;
            const uint32_t owner = hdWorldOwnerAt(screen + y * screenGetHeight() / on.height * gSdlSurface->pitch
                + x * screenGetWidth() / on.width);
            const int texel = owner & 0xFFFFFF;
            if ((owner >> 24) != static_cast<unsigned int>(id) || texel % 32 < 23 || texel % 32 >= 28
                || texel / 32 < 13 || texel / 32 >= 19) ++outside;
            const uint32_t p = on.pixels[at];
            if (((p >> 8) & 255) > ((p >> 16) & 255) + 20 && ((p >> 8) & 255) > (p & 255) + 20) ++green;
        }
    }
    report.check(shouldLoad ? changed > 0 && changed < 400 && green > 0 && outside == 0 : off.pixels == on.pixels,
        "only tiny green lamp changes; case, door frame, ground and all other pixels stay exact");
    report.check(capture({}, true).pixels == on.pixels, "repeated on frame is stable");
    hdWorldSetTerminalPreviewPhase(0);
    report.check(capture({}, true).pixels == off.pixels, "lamp off restores cached pixels without full redraw");
    hdWorldSetTerminalPreviewPhase(1);
    report.check(capture({}, false).pixels == classic.pixels, "F11 classic ignores animated lamp");
    const Capture on4k = capture(output / "terminal-on-4k.bmp", true, 3840, 2160);
    hdWorldSetTerminalPreviewPhase(0);
    const Capture off4k = capture(output / "terminal-off-4k.bmp", true, 3840, 2160);
    report.check(on4k.valid && off4k.valid && (shouldLoad ? on4k.pixels != off4k.pixels : on4k.pixels == off4k.pixels),
        "terminal state survives output density changes at 4K");
    hdWorldSetTerminalPreviewPhase(1);
    report.check(capture({}, true).pixels == on.pixels, "return from 4K restores exact lit entrance");
    std::array<unsigned char,768> normal;
    std::memcpy(normal.data(), getSystemPalette(), normal.size());
    palette_set_to(black_palette);
    const Capture black = capture(output / "terminal-black-fade.bmp", true);
    report.check(black.valid && black.pixels == capture({}, false).pixels,
        "green lamp follows black fade without glowing through transition");
    palette_set_to(normal.data());
    report.check(capture({}, true).pixels == on.pixels, "palette restore keeps exact green lamp and metal");
    std::array<char,sizeof(map_data.name)> mapName;
    std::memcpy(mapName.data(),map_data.name,mapName.size());
    std::strcpy(map_data.name,"OTHER.MAP");
    report.check(capture({},true).pixels == off.pixels, "lamp is gated to original first cave");
    std::memcpy(map_data.name,mapName.data(),mapName.size());
    report.check(capture({},true).pixels == on.pixels, "return to cave resumes lamp without stale cache");
    Object* terminal = nullptr;
    for (auto* object : objects()) if (object->fid == 0x0200006E) { terminal = object; break; }
    if (terminal) {
        const int window = win_add(terminal->sx - 5, terminal->sy - 5, 45, 65,
            colorTable[31744], WINDOW_MODAL | WINDOW_MOVE_ON_TOP);
        report.check(window != -1, "terminal occlusion test creates real window");
        if (window != -1) {
            win_draw(window);
            hdWorldSetTerminalPreviewPhase(0); const Capture hiddenOff = capture({},true);
            hdWorldSetTerminalPreviewPhase(1); const Capture hiddenOn = capture({},true);
            report.check(hiddenOff.valid && hiddenOff.pixels == hiddenOn.pixels,
                "lamp cannot blink through an opaque interface window");
            win_delete(window);tile_refresh_display();
            report.check(capture({},true).pixels == on.pixels, "closing covering window restores lamp exactly");
        }
    } else report.check(false,"original terminal object found");
    hdWorldReleaseTextures();
    report.check(capture({},true).pixels == on.pixels,"lamp frame survives texture recreation");
    if (terminal && hdWorldTerminalSoftEdges()) {
        hdWorldSetTerminalPreviewPhase(0);
        const Capture edged = capture({},true);
        std::ifstream sprite("data/art/hd/world-pilot/asset-010.rgba",std::ios::binary);
        sprite.seekg(20);
        std::vector<unsigned char> rgba(128 * 212 * 4);
        sprite.read(reinterpret_cast<char*>(rgba.data()),rgba.size());
        std::vector<size_t> transparentEdge;
        int softened = 0;
        const int density = edged.width / screenGetWidth();
        if (sprite && density >= 1 && density <= 4) {
            for (int y=0;y<edged.height;++y) for (int x=0;x<edged.width;++x) {
                const uint32_t owner=hdWorldOwnerAt(screen+(y/density)*gSdlSurface->pitch+x/density);
                if ((owner>>24)!=static_cast<unsigned int>(id)) continue;
                const int t=owner&0xFFFFFF;
                const int u=(t%32)*4+(2*(x%density)+1)*2/density;
                const int v=(t/32)*4+(2*(y%density)+1)*2/density;
                const int alpha=rgba[(v*128+u)*4+3];
                if (alpha==0) transparentEdge.push_back(static_cast<size_t>(y)*edged.width+x);
                else if (alpha<255) ++softened;
            }
        }
        const int flags=terminal->flags;
        terminal->flags |= OBJECT_HIDDEN;
        tile_refresh_display();
        const Capture background=capture(output/"terminal-background.bmp",true);
        std::ifstream frameImage("data/art/hd/world-pilot/asset-016.rgba",std::ios::binary);
        frameImage.seekg(20 + ((180 * 4) * 1368 + 84 * 4) * 4 + 3);
        if (frameImage.get() == 255) {
            Object* frameObject = nullptr;
            for (auto* object : objects()) if (object->fid == 0x0200011A) { frameObject=object; break; }
            int cleanPanel=0, badPanel=0;
            if (frameObject) for (int y=166;y<190;++y) for (int x=79;x<99;++x) {
                const int px=frameObject->sx+x, py=frameObject->sy+y;
                if (px<0 || py<0 || px>=screenGetWidth() || py>=screenGetHeight()) continue;
                const uint32_t owner=hdWorldOwnerAt(screen+py*gSdlSurface->pitch+px);
                if ((owner>>24)==16 && (owner&0xFFFFFF)==static_cast<unsigned int>(y*342+x)) ++cleanPanel;
                else ++badPanel;
            }
            report.check(cleanPanel==480 && badPanel==0,
                "repaired terminal recess reveals continuous frame, no lower floor or green indexed grid ("
                +std::to_string(cleanPanel)+" clean, "+std::to_string(badPanel)+" wrong)");
        }
        // Preserve exact underlying ownership for diagnosing matte seams. A
        // matching hidden-terminal capture alone does not prove clean artwork.
        std::ofstream underReport(output/"terminal-background-owners.tsv");
        underReport << "x\ty\towner\tindex\n";
        for (int y=std::max(0,terminal->sy-8); y<std::min(screenGetHeight(),terminal->sy+61); ++y)
            for (int x=std::max(0,terminal->sx-8); x<std::min(screenGetWidth(),terminal->sx+40); ++x) {
                auto* pixel=screen+y*gSdlSurface->pitch+x;
                underReport << x << '\t' << y << '\t' << hdWorldOwnerAt(pixel) << '\t' << int(*pixel) << '\n';
            }
        int wrongBackground=0;
        if (edged.valid && background.valid) for (size_t at:transparentEdge)
            wrongBackground += edged.pixels[at]!=background.pixels[at];
        report.check(edged.valid && background.valid && transparentEdge.size()>20 && softened>10 && wrongBackground==0,
            "removed outline reveals exact real background; no old indexed fringe remains ("+std::to_string(transparentEdge.size())+" clear, "+std::to_string(softened)+" antialiased, "+std::to_string(wrongBackground)+" wrong)");
        terminal->flags=flags;
        tile_refresh_display();
        report.check(capture({},true).pixels==off.pixels,"soft terminal redraw is stable and never blends over itself");
        hdWorldSetTerminalPreviewPhase(1);
    }
    // Exercise the actual SDL timer and cache without world refreshes or fake ticks.
    if (shouldLoad) {
        hdWorldSetTerminalPreviewPhase(-1);
        const unsigned int started = SDL_GetTicks();
        bool sawOn = false, sawOff = false;
        while (SDL_GetTicks() - started < 1750) {
            const Capture timed = capture({},true);
            sawOn |= timed.valid && timed.pixels == on.pixels;
            sawOff |= timed.valid && timed.pixels == off.pixels;
            SDL_Delay(60);
        }
        report.check(sawOn && sawOff,"real SDL clock animates both states while world is stationary");
    }
    hdWorldSetTerminalPreviewPhase(0);
    compare(report,before,snapshot({}),"terminal render-only animation");
}

// Optional snippet for hd_world_pilot_test.cc, owned/integrated by the test agent.
// Place this function in its anonymous namespace after Capture/capture(). Call
// fadeRegression(output, report) after the existing black-palette test restores
// normalPalette. No world ticks should run between these captures.
// FALLOUT_HD_WORLD_FADE_BASELINE=1 captures the old renderer without counting
// expected regression failures against the existing integration checks.
void fadeRegression(const std::filesystem::path& output, Report& report)
{
    std::array<unsigned char, 768> normalPalette;
    std::memcpy(normalPalette.data(), getSystemPalette(), normalPalette.size());
    struct RestorePalette {
        const unsigned char* palette;
        ~RestorePalette() { palette_set_to(const_cast<unsigned char*>(palette)); }
    } restore { normalPalette.data() };
    const bool assertions = SDL_getenv("FALLOUT_HD_WORLD_FADE_BASELINE") == nullptr;
    const Capture normal = capture(output / "fade-normal-hd.bmp", true);
    const Capture normalClassic = capture(output / "fade-normal-classic.bmp", false);
    if (!normal.valid || !normalClassic.valid) {
        if (assertions) report.check(false, "fade regression normal captures");
        return;
    }
    const auto* indexed = static_cast<const unsigned char*>(gSdlSurface->pixels);
    SDL_Surface* mask = SDL_CreateRGBSurfaceWithFormat(0, screenGetWidth(), screenGetHeight(),
        32, SDL_PIXELFORMAT_ARGB8888);
    if (mask != nullptr) {
        for (int y = 0; y < mask->h; ++y) {
            auto* row = reinterpret_cast<uint32_t*>(static_cast<unsigned char*>(mask->pixels) + y * mask->pitch);
            for (int x = 0; x < mask->w; ++x) {
                row[x] = hdWorldOwnerAt(indexed + y * gSdlSurface->pitch + x) ? 0xFFFFFFFFU : 0xFF000000U;
            }
        }
        SDL_SaveBMP(mask, (output / "fade-owner-mask.bmp").string().c_str());
        SDL_FreeSurface(mask);
    }
    struct FadeCase { const char* name; int numerator; int denominator; bool white; };
    const std::array<FadeCase, 4> cases {{
        { "dark25", 1, 4, false }, { "dark50", 1, 2, false },
        { "white50", 1, 2, true }, { "white", 1, 1, true }
    }};
    std::ofstream metrics(output / "fade-metrics.txt");
    metrics << "name owned_pixels pixels_over_tolerance max_channel_error\n";
    for (const auto& spec : cases) {
        std::array<unsigned char, 768> palette;
        for (size_t i = 0; i < palette.size(); ++i) {
            int c = normalPalette[i];
            palette[i] = static_cast<unsigned char>(spec.white
                ? c + (63 - c) * spec.numerator / spec.denominator
                : c * spec.numerator / spec.denominator);
        }
        palette_set_to(palette.data());
        const Capture classic = capture(output / (std::string("fade-") + spec.name + "-classic.bmp"), false);
        const Capture hd = capture(output / (std::string("fade-") + spec.name + "-hd.bmp"), true);
        const bool endpoint = spec.white && spec.numerator == spec.denominator;
        bool valid = classic.valid && hd.valid && hd.width == normal.width && hd.height == normal.height;
        int checked = 0;
        int bad = 0;
        double maxError = 0.0;
        if (valid) {
            for (int y = 0; y < hd.height; ++y) {
                int ly = y * screenGetHeight() / hd.height;
                for (int x = 0; x < hd.width; ++x) {
                    int lx = x * screenGetWidth() / hd.width;
                    if (!hdWorldOwnerAt(indexed + ly * gSdlSurface->pitch + lx)) continue;
                    const size_t offset = static_cast<size_t>(y) * hd.width + x;
                    const double fraction = static_cast<double>(spec.numerator) / spec.denominator;
                    bool pixelBad = false;
                    for (int shift : { 0, 8, 16 }) {
                        const int reference = (normal.pixels[offset] >> shift) & 255;
                        const int actual = (hd.pixels[offset] >> shift) & 255;
                        // RGB6 maximum63 becomes RGB8 white252 in this renderer.
                        const double expected = endpoint ? static_cast<double>((classic.pixels[offset] >> shift) & 255)
                            : (spec.white ? reference * (1.0 - fraction) + 252.0 * fraction : reference * fraction);
                        const double error = std::abs(actual - expected);
                        maxError = std::max(maxError, error);
                        if (error > (endpoint ? 0.0 : 4.0)) pixelBad = true;
                    }
                    if (pixelBad) ++bad;
                    ++checked;
                }
            }
        }
        metrics << spec.name << ' ' << checked << ' ' << bad << ' ' << maxError << '\n';
        if (assertions) {
            report.check(valid && checked > 0 && bad == 0,
                std::string("HD smooth palette ") + spec.name + " without native-cell gain grid");
            if (endpoint) report.check(valid && hd.pixels == classic.pixels,
                "full white flash matches classic endpoint pixel exactly");
        }
    }
}

bool sameRegion(const Capture& a, const Capture& b, int left, int top, int width, int height)
{
    if (!a.valid || !b.valid || a.width != b.width || a.height != b.height) return false;
    int x0 = std::max(0, left * a.width / screenGetWidth());
    int y0 = std::max(0, top * a.height / screenGetHeight());
    int x1 = std::min(a.width, (left + width) * a.width / screenGetWidth());
    int y1 = std::min(a.height, (top + height) * a.height / screenGetHeight());
    for (int y = y0; y < y1; ++y) {
        for (int x = x0; x < x1; ++x) {
            size_t offset = static_cast<size_t>(y) * a.width + x;
            if (a.pixels[offset] != b.pixels[offset]) return false;
        }
    }
    return x1 > x0 && y1 > y0;
}

void viewportRegression(const std::filesystem::path& output, Report& report)
{
    bool enabled = true;
    configGetBool(&game_config, "remaster", "full_height_world", &enabled);
    const bool expanded = enabled && screenGetWidth() > INTERFACE_BAR_WIDTH;
    const int width = win_width(display_win);
    const int height = win_height(display_win);
    report.check(width == screenGetWidth()
        && height == screenGetHeight() - (expanded ? 0 : INTERFACE_BAR_HEIGHT),
        "world viewport uses full height only in enabled wide layouts");
    Rect hud {};
    report.check(win_get_rect(interfaceWindow, &hud) == 0
        && hud.ulx == (screenGetWidth() - INTERFACE_BAR_WIDTH) / 2
        && hud.uly == screenGetHeight() - INTERFACE_BAR_HEIGHT,
        "HUD retains its centered bottom placement");
    tile_refresh_display();
    const Capture before = capture(output / "viewport-hd.bmp", true);
    const Capture classic = capture(output / "viewport-classic.bmp", false);
    report.check(before.valid && classic.valid
        && sameRegion(before, classic, hud.ulx, hud.uly, INTERFACE_BAR_WIDTH, INTERFACE_BAR_HEIGHT),
        "full-height world never paints HD scenery over HUD");

    const int savedMode = gmouse_3d_get_mode();
    const int savedCursor = gmouse_get_cursor();
    const bool savedEnabled = gmouse_is_enabled();
    const bool saved3d = gmouse_3d_is_on();
    const bool savedModes = gmouse_3d_modes_are_enabled();
    const bool savedScrolling = gmouse_scrolling_is_enabled();
    int savedX, savedY;
    mouse_get_position(&savedX, &savedY);
    gmouse_enable();
    gmouse_disable_scrolling();
    gmouse_3d_enable_modes();
    gmouse_set_cursor(MOUSE_CURSOR_NONE);
    gmouse_3d_on();
    gmouse_3d_set_mode(GAME_MOUSE_MODE_MOVE);
    gmouse_handle_event(hud.ulx + 300, hud.uly + 40, MOUSE_EVENT_RIGHT_BUTTON_DOWN);
    report.check(gmouse_3d_get_mode() == GAME_MOUSE_MODE_MOVE,
        "real world input handler rejects clicks on HUD");

    if (expanded) {
        auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
        auto* world = win_get_buf(display_win);
        for (int side = 0; side < 2; ++side) {
            const int left = side == 0 ? 0 : hud.lrx + 1;
            const int right = side == 0 ? hud.ulx : width;
            int painted = 0, mismatched = 0, inputX = -1, inputY = -1;
            for (int y = hud.uly; y < height; ++y) {
                for (int x = left; x < right; ++x) {
                    auto* src = world + y * width + x;
                    auto* dst = screen + y * gSdlSurface->pitch + x;
                    if (*src != 0) ++painted;
                    if (*src != *dst || hdWorldOwnerAt(src) != hdWorldOwnerAt(dst)) ++mismatched;
                    if (inputX == -1 && x > left && x < right - 1
                        && tile_point_inside_bound(x, y)) { inputX = x; inputY = y; }
                }
            }
            const std::string label = side == 0 ? "left" : "right";
            report.check(painted > 50 && mismatched == 0,
                label + " HUD wing contains real world pixels and HD ownership");
            gmouse_3d_set_mode(GAME_MOUSE_MODE_MOVE);
            if (inputX != -1) {
                mouse_set_position(inputX, inputY);
                gmouse_handle_event(inputX, inputY, MOUSE_EVENT_RIGHT_BUTTON_DOWN);
            }
            report.check(inputX != -1 && gmouse_3d_get_mode() == GAME_MOUSE_MODE_ARROW,
                label + " lower world wing accepts real right-click mode switch");
            gmouse_3d_set_mode(GAME_MOUSE_MODE_MOVE);
            const int overlay = inputX == -1 ? -1
                : win_add(inputX, inputY, 1, 1, colorTable[31744], WINDOW_MODAL | WINDOW_MOVE_ON_TOP);
            if (overlay != -1) {
                gmouse_handle_event(inputX, inputY, MOUSE_EVENT_RIGHT_BUTTON_DOWN);
            }
            report.check(overlay != -1 && gmouse_3d_get_mode() == GAME_MOUSE_MODE_MOVE,
                label + " lower world wing rejects clicks through another window");
            if (overlay != -1) win_delete(overlay);
        }
    }
    gmouse_3d_set_mode(savedMode);
    if (!savedModes) gmouse_3d_disable_modes();
    if (!saved3d) gmouse_3d_off();
    if (!savedEnabled) gmouse_disable(0);
    if (savedScrolling) gmouse_enable_scrolling();
    else gmouse_disable_scrolling();
    gmouse_set_cursor(savedCursor);
    mouse_set_position(savedX, savedY);
    tile_refresh_display();
    const Capture restored = capture({}, true);
    report.check(before.valid && restored.valid && before.pixels == restored.pixels,
        "world and HUD redraw exactly after lower-wing input and overlays");
    intface_hide();
    report.check(!expanded || win_get_top_win(hud.ulx + 300, hud.uly + 40) == display_win,
        "hiding HUD exposes the underlying full-height world");
    intface_show();
    tile_refresh_display();
    report.check(capture({}, true).pixels == before.pixels,
        "showing HUD restores exact composition over full-height world");
}

void greyBufferRegression(const std::filesystem::path& output, Report& report)
{
    constexpr int width = 96, height = 96;
    const int pitch = win_width(display_win);
    const int worldHeight = win_height(display_win);
    auto* world = win_get_buf(display_win);
    int selectedX = -1, selectedY = -1;
    for (int y = 0; y < worldHeight && selectedX == -1; ++y) {
        for (int x = 0; x < pitch; ++x) {
            if (hdWorldOwnerAt(world + y * pitch + x) != 0) {
                selectedX = std::clamp(x - width / 2, 0, pitch - width);
                selectedY = std::clamp(y - height / 2, 0, worldHeight - height);
                break;
            }
        }
    }
    report.check(selectedX != -1, "grey_buf regression has real HD-owned world pixels");
    if (selectedX == -1) return;
    const Capture before = capture({}, true);
    grey_buf(world + selectedY * pitch + selectedX, width, height, pitch);
    win_draw(display_win);
    int remainingOwners = 0;
    for (int y = selectedY; y < selectedY + height; ++y) {
        for (int x = selectedX; x < selectedX + width; ++x) {
            if (hdWorldOwnerAt(world + y * pitch + x) != 0) ++remainingOwners;
        }
    }
    report.check(remainingOwners == 0, "grey_buf invalidates colored HD ownership in modified region");
    const Capture classic = capture(output / "grey-buffer-classic.bmp", false);
    const Capture hd = capture(output / "grey-buffer-hd.bmp", true);
    report.check(sameRegion(classic, hd, selectedX, selectedY, width, height),
        "grey_buf has no colored HD bleed over classic grayscale result");
    tile_refresh_display();
    const Capture restored = capture({}, true);
    report.check(before.valid && restored.valid && before.pixels == restored.pixels,
        "world refresh restores exact HD pixels after grayscale operation");
}

struct SpriteMask {
    int x = 0, y = 0, width = 0, height = 0;
    std::vector<unsigned char> pixels;
    bool at(int screenX, int screenY) const
    {
        int localX = screenX - x, localY = screenY - y;
        return localX >= 0 && localY >= 0 && localX < width && localY < height
            && pixels[static_cast<size_t>(localY) * width + localX] != 0;
    }
};

SpriteMask spriteMask(Object* object)
{
    SpriteMask mask;
    CacheEntry* handle = nullptr;
    Art* art = art_ptr_lock(object->fid, &handle);
    if (art == nullptr) return mask;
    mask.width = art_frame_width(art, object->frame, object->rotation);
    mask.height = art_frame_length(art, object->frame, object->rotation);
    int x = 0, y = 0;
    tile_coord(object->tile, &x, &y, object->elevation);
    mask.x = x + 16 + art->xOffsets[object->rotation] + object->x - mask.width / 2;
    mask.y = y + 8 + art->yOffsets[object->rotation] + object->y - mask.height + 1;
    unsigned char* data = art_frame_data(art, object->frame, object->rotation);
    mask.pixels.assign(data, data + static_cast<size_t>(mask.width) * mask.height);
    art_ptr_unlock(handle);
    return mask;
}

std::vector<unsigned char> worldPixels()
{
    unsigned char* data = win_get_buf(display_win);
    return { data, data + static_cast<size_t>(win_width(display_win)) * win_height(display_win) };
}

std::vector<unsigned int> worldOwners()
{
    auto* data = win_get_buf(display_win);
    size_t size = static_cast<size_t>(win_width(display_win)) * win_height(display_win);
    std::vector<unsigned int> result(size);
    for (size_t i = 0; i < size; ++i) result[i] = hdWorldOwnerAt(data + i);
    return result;
}

std::vector<unsigned char> worldLights()
{
    auto* data = win_get_buf(display_win);
    const size_t size = static_cast<size_t>(win_width(display_win)) * win_height(display_win);
    std::vector<unsigned char> result(size);
    for (size_t i = 0; i < size; ++i) result[i] = hdWorldLightAt(data + i);
    return result;
}

void checkCampfireShadow(const HdWorldDecoration& item, const std::filesystem::path& output, Report& report)
{
    const bool savedShadow = hdWorldCampfireShadowEnabled();
    hdWorldSetCampfireShadowEnabled(false);
    tile_refresh_display();
    const Capture off = capture(output / "campfire-shadow-off-hd.bmp", true);
    const Capture classicOff = capture({}, false);
    const auto indexedOff = worldPixels();
    const auto ownersOff = worldOwners();
    const auto lightsOff = worldLights();
    hdWorldSetCampfireShadowEnabled(true);
    tile_refresh_display();
    const Capture on = capture(output / "campfire-shadow-on-hd.bmp", true);
    const Capture classicOn = capture({}, false);
    capture({}, true);
    const auto ownersOn = worldOwners();
    const auto lightsOn = worldLights();
    const int pitch = win_width(display_win), height = win_height(display_win);
    int changed = 0, invalid = 0;
    std::set<int> factors;
    for (int y = 0; y < height; ++y) for (int x = 0; x < pitch; ++x) {
        const size_t pixel = static_cast<size_t>(y) * pitch + x;
        if (lightsOff[pixel] == lightsOn[pixel]) continue;
        ++changed;
        const int factor = hdWorldCampfireShadowFactorAt(x, y, item.elevation);
        factors.insert(factor);
        if (!hdWorldAssetIsFloor(ownersOn[pixel] >> 24) || ownersOff[pixel] != ownersOn[pixel]
            || factor < 64 || factor >= 128 || lightsOff[pixel] > 128
            || lightsOn[pixel] != (lightsOff[pixel] * factor + 64) / 128) ++invalid;
    }
    report.check(changed > 20 && invalid == 0 && factors.size() >= 3 && ownersOff == ownersOn,
        "campfire shadow changes only local floor light with a bounded soft gradient");
    report.check(indexedOff == worldPixels() && classicOff.valid && classicOn.valid && classicOff.pixels == classicOn.pixels,
        "campfire shadow preserves every indexed pixel and exact F11 classic frame");
    const bool valid = off.valid && on.valid && off.width == on.width && off.height == on.height;
    int bodyPixels = 0, changedBody = 0, changedRender = 0, outsideRender = 0;
    if (valid) for (int y = 0; y < on.height; ++y) for (int x = 0; x < on.width; ++x) {
        const int lx = x * screenGetWidth() / on.width, ly = y * screenGetHeight() / on.height;
        const size_t pixel = static_cast<size_t>(y) * on.width + x;
        const bool world = lx < pitch && ly < height;
        const size_t logical = static_cast<size_t>(ly) * pitch + lx;
        if (world && (ownersOn[logical] >> 24) == item.assetId) {
            ++bodyPixels;
            if (off.pixels[pixel] != on.pixels[pixel]) ++changedBody;
        }
        if (off.pixels[pixel] == on.pixels[pixel]) continue;
        ++changedRender;
        if (!world || !hdWorldAssetIsFloor(ownersOn[logical] >> 24)
            || hdWorldCampfireShadowFactorAt(lx, ly, item.elevation) >= 128
            || lightsOff[logical] == lightsOn[logical]) ++outsideRender;
    }
    report.check(valid && bodyPixels > 0 && changedBody == 0,
        "campfire shadow preserves every rendered opaque campfire pixel");
    report.check(valid && changedRender > 20 && outsideRender == 0,
        "campfire shadow RGB changes stay inside the floor contact fringe; HUD and other sprites unchanged");
    int cx = 0, cy = 0, width = 0, spriteHeight = 0;
    tile_coord(item.tile, &cx, &cy, item.elevation);
    hdWorldDecorationDimensions(item.assetId, &width, &spriteHeight);
    const int left = cx + 16 + item.offsetX - width / 2;
    const int top = cy + 8 + item.offsetY - spriteHeight + 1;
    std::ofstream geometry(output / "campfire-shadow-geometry.tsv");
    geometry << "tile\tleft\ttop\twidth\theight\tshadow_padding\tlogical_width\tlogical_height\tcapture_width\tcapture_height\n"
        << item.tile << '\t' << left << '\t' << top << '\t' << width << '\t' << spriteHeight
        << "\t6\t" << screenGetWidth() << '\t' << screenGetHeight() << '\t' << on.width << '\t' << on.height << '\n';
    tile_refresh_display();
    report.check(capture({}, true).pixels == on.pixels, "campfire shadow does not accumulate on repeated full refresh");
    Rect partial { left - 6, top - 6, left + width / 2, top + spriteHeight + 5 };
    tile_refresh_rect(&partial, item.elevation);
    report.check(capture({}, true).pixels == on.pixels, "campfire shadow clipped partial refresh matches complete frame");
    const std::array<std::array<int, 2>, 4> scrolls { { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } } };
    std::ofstream scrollMetrics(output / "campfire-shadow-scroll.tsv");
    scrollMetrics << "direction\tshadow_enabled\tmoved\tcenter_before\tcenter_after\tactor_tile\tpixel_diff\tmin_x\tmin_y\tmax_x\tmax_y\n";
    const auto logScroll = [&scrollMetrics](size_t direction, bool shadowEnabled, int moved, int before, int after,
        const Capture& incremental, const Capture& full) {
        int count = 0, minX = incremental.width, minY = incremental.height, maxX = -1, maxY = -1;
        if (incremental.valid && full.valid && incremental.pixels.size() == full.pixels.size()) {
            for (int y = 0; y < incremental.height; ++y) for (int x = 0; x < incremental.width; ++x) {
                const size_t pixel = static_cast<size_t>(y) * incremental.width + x;
                if (incremental.pixels[pixel] == full.pixels[pixel]) continue;
                ++count; minX = std::min(minX, x); minY = std::min(minY, y); maxX = std::max(maxX, x); maxY = std::max(maxY, y);
            }
        } else count = -1;
        scrollMetrics << direction << '\t' << shadowEnabled << '\t' << moved << '\t' << before << '\t' << after << '\t' << obj_dude->tile
            << '\t' << count << '\t' << minX << '\t' << minY << '\t' << maxX << '\t' << maxY << '\n';
        return count;
    };
    // map_scroll keeps the camera within the original actor-distance limit.
    // Put the actor beside this distant test subject before exercising all four
    // legal scroll directions; restore the exact original pose afterward.
    const int scrollActorTile = obj_dude->tile, scrollActorX = obj_dude->x, scrollActorY = obj_dude->y;
    Rect scrollActorRect;
    const bool actorStaged = obj_move_to_tile(obj_dude, item.tile, item.elevation, &scrollActorRect) == 0;
    obj_dude->x = 0; obj_dude->y = 0;
    for (size_t direction = 0; direction < scrolls.size(); ++direction) {
        tile_set_center(item.tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        capture({}, true);
        SDL_Delay(35);
        const int centerBefore = tile_center_tile;
        const int moved = map_scroll(scrolls[direction][0], scrolls[direction][1]);
        const int centerAfter = tile_center_tile;
        const std::string prefix = "campfire-shadow-scroll-" + std::to_string(direction);
        const Capture incremental = capture(output / (prefix + "-incremental.bmp"), true);
        hdWorldReleaseTextures();
        tile_refresh_display();
        const Capture full = capture(output / (prefix + "-full.bmp"), true);
        const int difference = logScroll(direction, true, moved, centerBefore, centerAfter, incremental, full);
        report.check(actorStaged && moved == 0 && incremental.valid && full.valid && incremental.pixels == full.pixels,
            "campfire shadow incremental scroll matches uncached redraw direction " + std::to_string(direction)
                + " (moved=" + std::to_string(moved) + ", pixel_diff=" + std::to_string(difference) + ")");
        if (moved != 0 || difference != 0) {
            hdWorldSetCampfireShadowEnabled(false);
            tile_set_center(item.tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
            capture({}, true);
            SDL_Delay(35);
            const int controlBefore = tile_center_tile;
            const int controlMoved = map_scroll(scrolls[direction][0], scrolls[direction][1]);
            const int controlAfter = tile_center_tile;
            const Capture controlIncremental = capture(output / (prefix + "-off-incremental.bmp"), true);
            hdWorldReleaseTextures();
            tile_refresh_display();
            const Capture controlFull = capture(output / (prefix + "-off-full.bmp"), true);
            logScroll(direction, false, controlMoved, controlBefore, controlAfter, controlIncremental, controlFull);
            hdWorldSetCampfireShadowEnabled(true);
        }
    }
    const bool actorRestored = obj_move_to_tile(obj_dude, scrollActorTile, item.elevation, &scrollActorRect) == 0;
    obj_dude->x = scrollActorX; obj_dude->y = scrollActorY;
    tile_set_center(item.tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    report.check(actorRestored && capture({}, true).pixels == on.pixels, "campfire shadow camera and actor return restore exact contact fringe");
    std::array<unsigned char, 768> normalPalette, whitePalette;
    std::memcpy(normalPalette.data(), getSystemPalette(), normalPalette.size());
    whitePalette.fill(63);
    for (int white = 0; white < 2; ++white) {
        palette_set_to(white ? whitePalette.data() : black_palette);
        const Capture classic = capture({}, false);
        const Capture hd = capture({}, true);
        report.check(classic.valid && hd.valid && classic.pixels == hd.pixels,
            white ? "campfire shadow follows full white palette flash" : "campfire shadow follows full black palette fade");
    }
    palette_set_to(normalPalette.data());
    hdWorldSetCampfireShadowEnabled(false);
    tile_refresh_display();
    report.check(capture({}, true).pixels == off.pixels, "disabling campfire shadow restores exact prior HD frame");
    hdWorldSetCampfireShadowEnabled(savedShadow);
    tile_refresh_display();
}

void checkCampfireShadowActor(const SpriteMask& actor, const std::filesystem::path& output, Report& report)
{
    const bool savedShadow = hdWorldCampfireShadowEnabled();
    hdWorldSetCampfireShadowEnabled(false);
    tile_refresh_display();
    const Capture off = capture(output / "campfire-shadow-actor-off.bmp", true);
    hdWorldSetCampfireShadowEnabled(true);
    tile_refresh_display();
    const Capture on = capture(output / "campfire-shadow-actor-on.bmp", true);
    int checked = 0, changed = 0;
    const bool valid = off.valid && on.valid && off.width == on.width && off.height == on.height;
    if (valid) for (int y = 0; y < on.height; ++y) for (int x = 0; x < on.width; ++x) {
        const int lx = x * screenGetWidth() / on.width, ly = y * screenGetHeight() / on.height;
        if (!actor.at(lx, ly)) continue;
        ++checked;
        const size_t pixel = static_cast<size_t>(y) * on.width + x;
        if (off.pixels[pixel] != on.pixels[pixel]) ++changed;
    }
    report.check(valid && checked > 0 && changed == 0, "actor walking over campfire keeps exact pixels with contact shadow enabled");
    hdWorldSetCampfireShadowEnabled(savedShadow);
    tile_refresh_display();
}

struct Pose {
    Object* rock = nullptr;
    int tile = -1;
    int overlapVisible = 0;
    int overlapHidden = 0;
};

void overlapCounts(const SpriteMask& actor, const SpriteMask& rock,
    const std::vector<unsigned char>& visible, const std::vector<unsigned char>& hidden,
    const std::vector<unsigned int>& owners,
    int& visibleCount, int& hiddenCount)
{
    visibleCount = hiddenCount = 0;
    int pitch = win_width(display_win);
    int height = win_height(display_win);
    for (int y = std::max(0, actor.y); y < std::min(height, actor.y + actor.height); ++y) {
        for (int x = std::max(0, actor.x); x < std::min(pitch, actor.x + actor.width); ++x) {
            if (actor.at(x, y) && rock.at(x, y)) {
                size_t offset = static_cast<size_t>(y) * pitch + x;
                // The exact-color front test needs a genuinely unobscured actor,
                // not an actor seen through a translucent cave-wall egg.
                if (visible[offset] != hidden[offset] && owners[offset]==0) ++visibleCount;
                // Equal palette colors alone do not prove occlusion. Only the
                // actual surviving rock write is accepted as hidden evidence.
                else if ((owners[offset] >> 24) == 2) ++hiddenCount;
            }
        }
    }
}

std::array<Pose, 2> findOverlapPoses(const std::vector<Object*>& rocks)
{
    std::array<Pose, 2> poses;
    hdWorldSetEnabled(false);
    for (Object* rock : rocks) {
        // Legacy mask assertions apply to retained original silhouettes only.
        if (hdWorldCaveAssetForObject(rock)) continue;
        if (tile_set_center(rock->tile, TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS) != 0) continue;
        for (int distance = 1; distance <= 4; ++distance) {
            for (int direction = 0; direction < ROTATION_COUNT; ++direction) {
                int tile = tile_num_in_direction(rock->tile, direction, distance);
                if (!hexGridTileIsValid(tile) || obj_blocking_at(obj_dude, tile, 0) != nullptr) continue;
                Rect rect;
                if (obj_move_to_tile(obj_dude, tile, 0, &rect) != 0) continue;
                SpriteMask actor = spriteMask(obj_dude);
                SpriteMask stone = spriteMask(rock);
                if (actor.x + actor.width <= stone.x || stone.x + stone.width <= actor.x
                    || actor.y + actor.height <= stone.y || stone.y + stone.height <= actor.y) continue;
                tile_refresh_display();
                auto visible = worldPixels();
                auto owners = worldOwners();
                int flags = obj_dude->flags;
                obj_dude->flags |= OBJECT_HIDDEN;
                tile_refresh_display();
                auto hidden = worldPixels();
                obj_dude->flags = flags;
                int visibleCount, hiddenCount;
                overlapCounts(actor, stone, visible, hidden, owners, visibleCount, hiddenCount);
                if (visibleCount > poses[0].overlapVisible) poses[0] = { rock, tile, visibleCount, hiddenCount };
                if (hiddenCount > poses[1].overlapHidden) poses[1] = { rock, tile, visibleCount, hiddenCount };
                if (poses[0].overlapVisible >= 20 && poses[1].overlapHidden >= 20) {
                    tile_refresh_display();
                    return poses;
                }
            }
        }
    }
    tile_refresh_display();
    return poses;
}

void checkOverlap(Report& report, const std::filesystem::path& directory,
    const Pose& pose, const std::string& name)
{
    if (pose.rock == nullptr || pose.tile < 0) {
        report.check(false, name + " a real free hex with actor/rock overlap exists");
        return;
    }
    Rect rect;
    report.check(obj_blocking_at(obj_dude, pose.tile, 0) == nullptr,
        name + " staged actor hex is originally passable");
    obj_move_to_tile(obj_dude, pose.tile, 0, &rect);
    tile_set_center(pose.rock->tile, TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    tile_refresh_display();
    const SpriteMask actorMask = spriteMask(obj_dude);
    const SpriteMask rockMask = spriteMask(pose.rock);
    const auto visibleOwners = worldOwners();
    Snapshot before = snapshot({});
    Capture classicVisible = capture(directory / (name + "-classic.bmp"), false);
    Capture hdVisible = capture(directory / (name + "-hd.bmp"), true);
    hdWorldReleaseTextures();tile_refresh_display();
    const Capture freshVisible=capture({},true);
    report.check(hdVisible.valid && freshVisible.valid && hdVisible.pixels==freshVisible.pixels,
        name+" actor arrival / transparency cache matches uncached frame");
    compare(report, before, snapshot({}), name + " HD toggle");
    int flags = obj_dude->flags;
    obj_dude->flags |= OBJECT_HIDDEN;
    tile_refresh_display();
    Capture classicHidden = capture({}, false);
    Capture hdHidden = capture({}, true);
    hdWorldReleaseTextures();tile_refresh_display();
    const Capture freshHidden=capture({},true);
    report.check(hdHidden.valid && freshHidden.valid && hdHidden.pixels==freshHidden.pixels,
        name+" actor departure / background cache matches uncached frame");
    obj_dude->flags = flags;
    tile_refresh_display();
    bool valid = classicVisible.valid && hdVisible.valid && classicHidden.valid && hdHidden.valid;
    report.check(valid, name + " actual renderer captures");
    if (!valid) return;
    int visiblePixels = 0, hiddenPixels = 0, overwritten = 0, leaked = 0;
    for (int y = 0; y < classicVisible.height; ++y) {
        for (int x = 0; x < classicVisible.width; ++x) {
            size_t offset = static_cast<size_t>(y) * classicVisible.width + x;
            int logicalX = x * screenGetWidth() / classicVisible.width;
            int logicalY = y * screenGetHeight() / classicVisible.height;
            if (!actorMask.at(logicalX, logicalY)) continue;
            size_t ownerOffset = static_cast<size_t>(logicalY) * win_width(display_win) + logicalX;
            if (logicalY >= win_height(display_win) || ownerOffset >= visibleOwners.size()) continue;
            // Old egg dithering leaves unowned wall pixels inside the actor's
            // rectangular mask. Only pixels changed by the actor are evidence
            // of visible actor color; the others may legitimately change wall art.
            if (visibleOwners[ownerOffset] == 0 && classicVisible.pixels[offset]!=classicHidden.pixels[offset]) {
                ++visiblePixels;
                if (hdVisible.pixels[offset] != classicVisible.pixels[offset]) ++overwritten;
            } else if ((visibleOwners[ownerOffset] >> 24) == 2 && rockMask.at(logicalX, logicalY)) {
                ++hiddenPixels;
                if (hdVisible.pixels[offset] != hdHidden.pixels[offset]) ++leaked;
            }
        }
    }
    report.check(visiblePixels > 0 && overwritten == 0,
        name + " visible actor pixels remain original (" + std::to_string(visiblePixels)
        + " checked; " + std::to_string(overwritten) + " overwritten)");
    report.check(hiddenPixels > 0 ? leaked == 0 : name == "actor-front",
        name + " originally occluded actor pixels remain occluded (" + std::to_string(hiddenPixels)
        + " checked; " + std::to_string(leaked) + " leaked)");
    report.check(hdVisible.hdDrawn && hdVisible.rockPixels > 0,
        name + " HD rock is visible in actual world");
}

void checkCursor(Report& report, const std::filesystem::path& output)
{
    gmouse_set_cursor(MOUSE_CURSOR_ARROW);
    unsigned char* shape = nullptr;
    int width, height, pitch, hotX, hotY;
    char transparent;
    mouse_get_shape(&shape, &width, &height, &pitch, &hotX, &hotY, &transparent);
    auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
    int cursorX = -1, cursorY = -1, best = 0;
    for (int y = 20; y + height < win_height(display_win); y += 8) {
        for (int x = 20; x + width < screenGetWidth(); x += 8) {
            int count = 0;
            for (int cy = 0; cy < height; ++cy) {
                for (int cx = 0; cx < width; ++cx) {
                    if (shape[cy * pitch + cx] == static_cast<unsigned char>(transparent)
                        && hdWorldOwnerAt(screen + (y + cy) * gSdlSurface->pitch + x + cx) != 0) ++count;
                }
            }
            if (count > best) { best = count; cursorX = x; cursorY = y; }
        }
    }
    report.check(best > 0, "cursor has transparent pixels over actual HD artwork");
    if (best == 0) { gmouse_set_cursor(MOUSE_CURSOR_NONE); return; }
    std::vector<unsigned int> before(static_cast<size_t>(width) * height);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            before[static_cast<size_t>(y) * width + x] =
                hdWorldOwnerAt(screen + (cursorY + y) * gSdlSurface->pitch + cursorX + x);
        }
    }
    mouse_set_position(cursorX + hotX, cursorY + hotY);
    mouse_show();
    int lostTransparent = 0, coveredOpaque = 0;
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            unsigned int owner = hdWorldOwnerAt(screen + (cursorY + y) * gSdlSurface->pitch + cursorX + x);
            if (shape[y * pitch + x] == static_cast<unsigned char>(transparent)) {
                if (owner != before[static_cast<size_t>(y) * width + x]) ++lostTransparent;
            } else if (owner != 0) ++coveredOpaque;
        }
    }
    report.check(lostTransparent == 0 && coveredOpaque == 0,
        "real cursor preserves transparent HD background and clears opaque cursor ownership");
    Capture cursor = capture(output / "cursor-hd.bmp", true);
    report.check(cursor.valid && cursor.hdDrawn, "actual cursor over HD world captured");
    mouse_hide();
    gmouse_set_cursor(MOUSE_CURSOR_NONE);
    tile_refresh_display();
}

void checkDoorFrames(Report& report, const std::filesystem::path& directory,
    const std::vector<int>& destinations, int fid, int firstAssetId, const char* label)
{
    Object* door = nullptr;
    int matchingObjects = 0;
    for (Object* object : objects()) {
        if ((object->fid & 0x0FFFFFFF) == fid && object->elevation == 0) {
            door = object;
            matchingObjects++;
        }
    }
    const std::string name(label);
    report.check(matchingObjects == 1 && door != nullptr, name + " original map object found exactly once");
    if (matchingObjects != 1 || door == nullptr) return;

    CacheEntry* handle = nullptr;
    Art* art = art_ptr_lock(door->fid, &handle);
    bool validArt = art != nullptr && art_frame_max_frame(art) == 15;
    if (art != nullptr) art_ptr_unlock(handle);
    Proto* prototype = nullptr;
    bool validPrototype = proto_ptr(door->pid, &prototype) == 0 && prototype != nullptr;
    report.check(validArt && validPrototype, name + " original 15-frame FRM and scenery prototype available");
    if (!validArt || !validPrototype) return;
    std::array<unsigned char, sizeof(SceneryProto)> originalPrototype;
    std::memcpy(originalPrototype.data(), &prototype->scenery, originalPrototype.size());

    const int originalFrame = door->frame;
    const int originalCenter = tile_center_tile;
    const bool originalEnabled = hdWorldEnabled();
    const Snapshot originalState = snapshot(destinations);
    bool centered = tile_set_center(door->tile,
        TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS) == 0;
    report.check(centered, name + " camera centers on the actual door");
    if (!centered) {
        tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        return;
    }
    const Capture initial = capture({}, true);
    // Select original FRM frames without invoking door scripts, changing flags,
    // altering its prototype, or pretending this is a timed gameplay animation.
    for (int frame = 0; frame < 15; frame++) {
        Rect dirty;
        bool selected = obj_set_frame(door, frame, &dirty) == 0;
        tile_refresh_display();
        const Snapshot beforeFrame = snapshot(destinations);
        const int assetId = firstAssetId + frame;
        const std::string frameName = name + "-frame-" + (frame < 10 ? "0" : "") + std::to_string(frame);
        const Capture classic = capture({}, false);
        const std::filesystem::path imagePath = frame == 0 || frame == 7 || frame == 14
            ? directory / (frameName + "-hd.bmp") : std::filesystem::path {};
        const Capture hd = capture(imagePath, true);
        int staleFramePixels = 0;
        for (int otherFrame = 0; otherFrame < 15; otherFrame++) {
            if (otherFrame != frame) staleFramePixels += hdWorldVisiblePixels(firstAssetId + otherFrame);
        }
        int changedDoorPixels = 0;
        if (classic.valid && hd.valid && classic.width == hd.width && classic.height == hd.height) {
            const auto* screen = static_cast<const unsigned char*>(gSdlSurface->pixels);
            for (int y = 0; y < hd.height; y++) {
                int nativeY = y * screenGetHeight() / hd.height;
                for (int x = 0; x < hd.width; x++) {
                    size_t offset = static_cast<size_t>(y) * hd.width + x;
                    if (classic.pixels[offset] == hd.pixels[offset]) continue;
                    int nativeX = x * screenGetWidth() / hd.width;
                    if ((hdWorldOwnerAt(screen + nativeY * gSdlSurface->pitch + nativeX) >> 24)
                        == static_cast<unsigned int>(assetId)) ++changedDoorPixels;
                }
            }
        }
        report.check(selected && hdWorldAssetLoaded(assetId) && hdWorldVisiblePixels(assetId) > 0
            && staleFramePixels == 0 && changedDoorPixels > 0,
            frameName + " real draw uses its own HD frame with visible changes and no stale frame owners");
        hdWorldReleaseTextures();
        const Capture uncached = capture({}, true);
        report.check(hd.valid && uncached.valid && hd.pixels == uncached.pixels,
            frameName + " cached pixels equal uncached rendering");
        const Snapshot afterFrame = snapshot(destinations);
        report.check(beforeFrame.blockers == afterFrame.blockers && beforeFrame.squares == afterFrame.squares
            && beforeFrame.objects == afterFrame.objects && beforeFrame.paths == afterFrame.paths,
            frameName + " HD rendering preserves original game fields collision and routes");
    }
    Rect restoredRect;
    obj_set_frame(door, originalFrame, &restoredRect);
    tile_refresh_display();
    const Capture restored = capture({}, true);
    report.check(initial.valid && restored.valid && initial.pixels == restored.pixels,
        name + " restoring original frame removes animation trails exactly");
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    hdWorldSetEnabled(originalEnabled);
    compare(report, originalState, snapshot(destinations), name + " restored after all 15 frame draws");
    prototype = nullptr;
    report.check(proto_ptr(door->pid, &prototype) == 0 && prototype != nullptr
        && std::memcmp(originalPrototype.data(), &prototype->scenery, originalPrototype.size()) == 0,
        name + " scenery prototype bytes remain unchanged");
}

#include "game/hd_wall_geometry_test.inc"

void wallAccentRegression(const std::filesystem::path& output, Report& report)
{
    // The new accents use the formerly vacant 175..198 slots. Verify actual
    // registered wall appearances rather than assuming an old animation range.
    if (expectedAssetCount()<246) return;
    const int center=tile_center_tile;
    const Snapshot before=snapshot({});
    std::set<int> registered,visible,replaced;
    std::ofstream rows(output/"wall-accent-visibility.tsv");
    rows<<"object\ttile\tappearance\tvisible_native_cells\n";
    const auto all=objects();
    for(auto* o:all) {
        if(((o->fid>>24)&15)!=3) continue;
        int id=hdWorldResolveAsset(o->fid,o->frame,o->tile,o->elevation);
        if(id<175 || id>198) continue;
        registered.insert(id);
        if(hdWorldCaveAssetForObject(o)==252 || hdWorldCaveAssetForObject(o)==253) {replaced.insert(id);continue;}
        if(visible.count(id)) continue;
        tile_set_center(o->tile,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        tile_refresh_display();
        auto owners=worldOwners();int cells=0;
        for(auto v:owners) if((v>>24)==static_cast<unsigned int>(id)) ++cells;
        rows<<o->id<<'\t'<<o->tile<<'\t'<<id<<'\t'<<cells<<'\n';
        if(!cells) continue;
        visible.insert(id);
        std::string name="wall-accent-"+std::to_string(id);
        const auto indexed=worldPixels();
        Capture enabled=capture(output/(name+"-hd.bmp"),true);
        Capture classicOn=capture({},false);
        hdWorldSetWallVariantsEnabled(false);tile_refresh_display();
        Capture base=capture(output/(name+"-base.bmp"),true);
        Capture classicOff=capture({},false);
        report.check(indexed==worldPixels() && classicOn.pixels==classicOff.pixels,name+" preserves indexed world and F11 classic");
        hdWorldSetWallVariantsEnabled(true);tile_refresh_display();
        Capture restored=capture({},true);
        hdWorldReleaseTextures();tile_refresh_display();Capture fresh=capture({},true);
        report.check(enabled.valid && base.valid && enabled.pixels!=base.pixels,name+" visible in actual cave renderer");
        report.check(enabled.pixels==restored.pixels && restored.pixels==fresh.pixels,name+" toggles and uncached redraw are exact");
    }
    report.check(registered.size()==24,"all 24 wall accents assigned to original wall objects");
    auto covered=visible;covered.insert(replaced.begin(),replaced.end());
    report.check(covered.size()==24,"all 24 wall accents visible or superseded by explicit connected wall geometry");
    tile_set_center(center,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    compare(report,before,snapshot({}),"wall accent visual variants");
}

void caveVarietyRegression(const std::filesystem::path& output, Report& report)
{
    if(!hdWorldCaveVarietyEnabled() || !hdWorldCaveAssignmentCount()) return;
    const int center=tile_center_tile;
    std::vector<Object*> assigned;
    std::set<int> variants;
    for(auto* o:objects()) if(hdWorldCaveAssetForObject(o) && hdWorldCaveAssetForObject(o)!=253) {assigned.push_back(o);variants.insert(hdWorldCaveAssetForObject(o));}
    const int vault=hdWorldAssetLoaded(252)?1:0;
    report.check(hdWorldCaveAssetCount()==16+vault,"16 scenery masters plus optional vault rock loaded in reserved slots");
    report.check(hdWorldCaveAssignmentCount()==76+vault && assigned.size()==76+vault,"76 scenery identities plus optional exact vault wall resolve");
    report.check(variants.size()==15+vault,"15 scenery forms plus optional vault rock used");
    Snapshot before=snapshot({});
    std::ofstream rows(output/"cave-appearance-assignments.tsv");
    rows<<"object_id\tfid\ttile\tasset_id\tplacement\tvisible_native_cells\n";
    std::set<int> captured;
    int visiblePlacements=0;
    for(auto* o:assigned) {
        int id=hdWorldCaveAssetForObject(o),index=hdWorldCavePlacementForObject(o);
        tile_set_center(o->tile,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        tile_refresh_display();
        auto owners=worldOwners();int count=0;
        for(auto owner:owners) if((owner>>24)==static_cast<unsigned int>(id) && ((owner>>16)&255)==static_cast<unsigned int>(index)) ++count;
        if(count) ++visiblePlacements;
        rows<<o->id<<'\t'<<o->fid<<'\t'<<o->tile<<'\t'<<id<<'\t'<<index<<'\t'<<count<<'\n';
        report.check(id==hdWorldCaveAssetForObject(o),"stable cave appearance object "+std::to_string(o->id));
        if(!count || !captured.insert(id).second) continue;
        const std::string name="new-form-"+std::to_string(id);
        Capture on=capture(output/(name+"-hd.bmp"),true);
        auto indexedOn=worldPixels();
        hdWorldSetCaveVarietyEnabled(false);tile_refresh_display();
        Capture off=capture(output/(name+"-previous-hd.bmp"),true);
        report.check(indexedOn==worldPixels(),name+" leaves original indexed framebuffer unchanged");
        Capture classicOff=capture({},false);
        hdWorldSetCaveVarietyEnabled(true);tile_refresh_display();
        Capture classicOn=capture({},false);
        report.check(classicOn.pixels==classicOff.pixels,name+" classic F11 is unchanged");
        Capture again=capture({},true);hdWorldReleaseTextures();tile_refresh_display();
        Capture fresh=capture({},true);
        report.check(on.valid && off.valid && on.pixels!=off.pixels,name+" visibly differs from previous HD");
        report.check(on.pixels==again.pixels && again.pixels==fresh.pixels,name+" repeated and uncached rendering is exact");
    }
    report.check(captured.size()==15+vault,"all assigned new forms visible in actual SDL captures");
    report.text<<"INFO visible new placements "<<visiblePlacements<<" of "<<assigned.size()<<std::endl;
    tile_set_center(center,TILE_SET_CENTER_REFRESH_WINDOW|TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    compare(report,before,snapshot({}),"new geometry camera and toggle checks");
}

void vaultRockRegression(const std::filesystem::path& output, Report& report)
{
    if(!hdWorldAssetLoaded(252)) return;
    Object* wall=nullptr;
    for(auto* o:objects()) if(o->id==252 && o->fid==50331705 && o->tile==17285) wall=o;
    report.check(wall && hdWorldCaveAssetForObject(wall)==252,"variant A assigned only to exact vault stone object");
    if(!wall) return;
    const auto before=snapshot({});
    tile_refresh_display();
    auto on=capture(output/"vault-rock-a-entrance.bmp",true);
    const int x=wall->sx,y=wall->sy,flags=wall->flags;
    int frameUnder=0;
    for(auto owner:worldOwners()) if((owner>>24)==252 && hdWorldCaveBackgroundHasAsset(owner,16,16)) ++frameUnder;
    report.check(frameUnder>100,"actual vault frame retained behind new transparent stone outline");
    wall->flags|=OBJECT_HIDDEN;tile_refresh_display();
    auto background=capture({},true);
    wall->flags=flags;tile_refresh_display();
    report.check(sameRegion(on,background,x+3,y+10,8,45),"removed upper teeth reveal exact underlying scene, without original FRM ghost");
    auto restored=capture({},true);
    report.check(on.pixels==restored.pixels,"vault stone background capture restores exactly after hiding and showing");
    compare(report,before,snapshot({}),"vault stone visual-only replacement");
}

} // namespace

int hdWorldPilotBenchmark(const char* directory)
{
    const std::filesystem::path output(directory);
    std::filesystem::create_directories(output);
    Report report(output);
    if (!report.text) return 30;
    constexpr int warmupCount = 4;
    constexpr int sampleCount = 24;
    const int originalCenter = tile_center_tile;
    const bool originalEnabled = hdWorldEnabled();
    int originalWindowWidth = 0, originalWindowHeight = 0;
    SDL_GetWindowSize(gSdlWindow, &originalWindowWidth, &originalWindowHeight);
    const Uint64 frequency = SDL_GetPerformanceFrequency();
    report.check(frequency != 0, "high resolution performance counter available");
    report.check(SDL_GetRenderTarget(gSdlRenderer) == nullptr, "benchmark uses real window presentation");
    report.check(screenGetWidth() == 960 && screenGetHeight() == 540,
        "fixed 960x540 logical game canvas");

    struct TimingRow {
        int width = 0, height = 0;
        int outputWidth = 0, outputHeight = 0;
        std::string mode;
        std::string workload;
        std::string renderer;
        Uint32 rendererFlags = 0;
        int successfulUpdates = 0;
        std::vector<double> samples;
    };
    std::vector<TimingRow> rows;
    const std::array<const char*, 4> workloads { "idle_present", "small_refresh_64x64", "full_world_refresh", "incremental_scroll" };
    for (const auto& dimensions : std::array<std::array<int, 2>, 2> { { { 1920, 1080 }, { 3840, 2160 } } }) {
        SDL_SetWindowSize(gSdlWindow, dimensions[0], dimensions[1]);
        SDL_PumpEvents();
        handleWindowSizeChanged();
        int outputWidth = 0, outputHeight = 0;
        SDL_GetRendererOutputSize(gSdlRenderer, &outputWidth, &outputHeight);
        const bool sizeMatches = outputWidth == dimensions[0] && outputHeight == dimensions[1];
        report.check(sizeMatches, "actual SDL window output " + std::to_string(dimensions[0]) + "x" + std::to_string(dimensions[1]));
        if (!sizeMatches || frequency == 0) continue;
        SDL_RendererInfo rendererInfo {};
        SDL_GetRendererInfo(gSdlRenderer, &rendererInfo);
        for (bool enabled : { false, true }) {
            for (int workload = 0; workload < static_cast<int>(workloads.size()); ++workload) {
                tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
                hdWorldSetEnabled(enabled);
                tile_refresh_display();
                win_refresh_all(&scr_size);
                renderPresent();
                TimingRow row;
                row.width = dimensions[0];
                row.height = dimensions[1];
                row.outputWidth = outputWidth;
                row.outputHeight = outputHeight;
                row.mode = enabled ? "hd_enabled" : "hd_disabled_same_pilot";
                row.workload = workloads[workload];
                row.renderer = rendererInfo.name != nullptr ? rendererInfo.name : "unknown";
                row.rendererFlags = rendererInfo.flags;
                int playerX = 0, playerY = 0;
                tile_coord(obj_dude->tile, &playerX, &playerY, map_elevation);
                const int smallX = std::clamp(playerX - 16, 0, win_width(display_win) - 64);
                const int smallY = std::clamp(playerY - 24, 0, win_height(display_win) - 64);
                Rect smallRect { smallX, smallY, smallX + 63, smallY + 63 };
                for (int frame = 0; frame < warmupCount + sampleCount; ++frame) {
                    SDL_PumpEvents();
                    // map_scroll's input throttle is outside the measured update/present work.
                    if (workload == 3) SDL_Delay(35);
                    const Uint64 begin = SDL_GetPerformanceCounter();
                    int updateResult = 0;
                    if (workload == 1) tile_refresh_rect(&smallRect, map_elevation);
                    else if (workload == 2) tile_refresh_display();
                    else if (workload == 3) updateResult = map_scroll((frame & 1) == 0 ? 1 : -1, 0);
                    renderPresent();
                    const Uint64 end = SDL_GetPerformanceCounter();
                    if (frame >= warmupCount) {
                        row.samples.push_back(static_cast<double>(end - begin) * 1000.0 / static_cast<double>(frequency));
                        if (updateResult == 0) ++row.successfulUpdates;
                    }
                }
                report.check(row.successfulUpdates == sampleCount,
                    row.mode + " " + row.workload + " completed " + std::to_string(sampleCount) + " real update/present samples");
                report.text << "TIMING " << row.width << "x" << row.height << " " << row.mode << " " << row.workload << std::endl;
                rows.push_back(std::move(row));
            }
        }
    }
    report.check(rows.size() == 16, "all 16 resolution/mode/workload cases recorded");
    report.check(hdWorldLoadedAssetCount() == expectedAssetCount(),
        std::to_string(expectedAssetCount()) + " selected resources/frames loaded during benchmark");
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    hdWorldSetEnabled(originalEnabled);
    SDL_SetWindowSize(gSdlWindow, originalWindowWidth, originalWindowHeight);
    SDL_PumpEvents();
    handleWindowSizeChanged();
    tile_refresh_display();
    win_refresh_all(&scr_size);

    std::ofstream result(output / "benchmark.json");
    result << std::fixed << std::setprecision(6)
        << "{\n  \"schema\":1,\n  \"passed\":" << report.passed << ",\n  \"failed\":" << report.failed
        << ",\n  \"map\":\"V13ENT.MAP\",\n  \"camera_tile\":" << originalCenter
        << ",\n  \"logical_width\":" << screenGetWidth() << ",\n  \"logical_height\":" << screenGetHeight()
        << ",\n  \"warmup_frames\":" << warmupCount << ",\n  \"sample_count\":" << sampleCount
        << ",\n  \"timing_unit\":\"milliseconds\",\n  \"scope\":\"CPU wall time through real renderPresent; hidden SDL window, no readback, not gameplay FPS\","
        << "\n  \"control\":\"hd_disabled_same_pilot retains ownership tracking and is not the original classic executable\","
        << "\n  \"excluded\":\"map load, resize, warmup, event pump, and 35ms scroll input-throttle wait\",\n  \"rows\":[\n";
    for (size_t index = 0; index < rows.size(); ++index) {
        const TimingRow& row = rows[index];
        std::vector<double> sorted = row.samples;
        std::sort(sorted.begin(), sorted.end());
        const double median = (sorted[sorted.size() / 2 - 1] + sorted[sorted.size() / 2]) / 2.0;
        const size_t p95Index = (sorted.size() * 95 + 99) / 100 - 1;
        result << "    {\"requested_width\":" << row.width << ",\"requested_height\":" << row.height
            << ",\"actual_width\":" << row.outputWidth << ",\"actual_height\":" << row.outputHeight
            << ",\"mode\":\"" << row.mode << "\",\"workload\":\"" << row.workload
            << "\",\"renderer\":\"" << row.renderer << "\",\"renderer_flags\":" << row.rendererFlags
            << ",\"successful_updates\":" << row.successfulUpdates << ",\"median_ms\":" << median
            << ",\"p95_ms\":" << sorted[p95Index] << ",\"min_ms\":" << sorted.front() << ",\"max_ms\":" << sorted.back()
            << ",\"samples_ms\":[";
        for (size_t sample = 0; sample < row.samples.size(); ++sample) {
            if (sample != 0) result << ',';
            result << row.samples[sample];
        }
        result << "]}" << (index + 1 < rows.size() ? "," : "") << '\n';
    }
    result << "  ]\n}\n";
    report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
    return report.failed == 0 && result ? 0 : 31;
}

int hdWorldPilotPreview(const char* directory)
{
    std::filesystem::path output(directory);
    std::filesystem::create_directories(output);
    Report report(output);
    if (!report.text) return 20;
    map_disable_bk_processes();
    scr_disable();
    cycle_disable();
    gmouse_disable_scrolling();
    mouse_hide();
    report.check(std::strcmp(map_data.name, "V13ENT.MAP") == 0 && map_data.version == 19,
        "real original V13ENT.MAP version 19 loaded");
    report.check(obj_dude != nullptr && obj_dude->elevation == 0 && hexGridTileIsValid(obj_dude->tile),
        "predefined player in actual cave");
    if (report.failed != 0) return 21;
    if (SDL_getenv("FALLOUT_HD_TERMINAL_ONLY")) {
        terminalRegression(output, report);
        std::ofstream result(output / "result.json");
        result << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed << "}\n";
        report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
        return report.failed == 0 ? 0 : 22;
    }
    if (SDL_getenv("FALLOUT_COMBAT_TEST")) {
        Object* rat = nullptr;
        for (Object* object = obj_find_first(); object != nullptr; object = obj_find_next()) {
            if (FID_TYPE(object->fid) == OBJ_TYPE_CRITTER && object != obj_dude
                && critter_kill_count_type(object) == KILL_TYPE_RAT) {
                rat = object;
                break;
            }
        }
        report.check(rat != nullptr, "original cave rat found");
        if (rat == nullptr) return 22;
        Attack attack;
        combat_ctd_init(&attack, rat, obj_dude, HIT_MODE_PUNCH, HIT_LOCATION_TORSO);
        attack.attackerFlags = DAM_HIT;
        attack.defenderDamage = 2;
        report.text << "REPRO rat hits player for 2 HP (original crash)" << std::endl;
        combat_display(&attack);
        report.check(true, "rat hit message returns without access violation");
        Capture frame = capture(output / "rat-hit-player.bmp", true);
        report.check(frame.valid && frame.hdDrawn, "combat message rendered over HD cave");
        // Assert wording/argument types, not just survival. All three subjects
        // use the later CE ABI, including the female and critical/aimed forms.
        auto expectText = [&](int id, const char* expected) {
            MessageListItem entry = {};
            entry.num = id;
            report.check(message_search(&combat_message_file, &entry)
                    && std::strcmp(entry.text, expected) == 0,
                "compatible combat template " + std::to_string(id));
        };
        expectText(513, "%s were hit for %d hit points");
        expectText(613, "%s was hit for %d hit points");
        expectText(713, "%s was hit for %d hit points");
        expectText(511, "%s were critically hit in the %s for %d hit points");
        expectText(612, "%s was hit in the %s for %d hit points");
        expectText(723, "%s was hit for 1 hit point");
        expectText(527, "%s were hit for no damage");
        expectText(608, "Oops! %s was hit instead of You!");
        expectText(509, "Oops! %s were hit instead of %s!");
        expectText(207, "were killed");
        expectText(257, "were killed");
        expectText(307, "was killed");
        expectText(407, "was killed");
        expectText(100, "You need %d action points.");
        expectText(101, "Out of ammo.");
        expectText(103, "Combat cannot end with nearby hostile creatures.");
        MessageListItem* normalizedEntries = combat_message_file.entries;
        report.check(combatNormalizeLegacyMessages(&combat_message_file)
                && combat_message_file.entries == normalizedEntries,
            "later message layout is unchanged on repeated normalization");
        if (report.failed != 0) return 22;

        for (Object* defender : { obj_dude, rat }) {
            for (int damage : { 0, 1, 2, 20 }) {
                for (int location : { HIT_LOCATION_TORSO, HIT_LOCATION_HEAD }) {
                    for (bool critical : { false, true }) {
                        combat_ctd_init(&attack, defender == rat ? obj_dude : rat,
                            defender, HIT_MODE_PUNCH, location);
                        attack.attackerFlags = DAM_HIT | (critical ? DAM_CRITICAL : 0);
                        attack.defenderDamage = damage;
                        attack.criticalMessageId = critical ? 5000 : -1;
                        combat_display(&attack);
                        report.check(true, std::string(defender == rat ? "rat" : "player")
                            + " hit display damage=" + std::to_string(damage)
                            + " location=" + std::to_string(location)
                            + (critical ? " critical" : " normal"));
                    }
                }
            }
            for (int damage : { 0, 1, 2 }) {
                combat_ctd_init(&attack, defender, defender == rat ? obj_dude : rat,
                    HIT_MODE_PUNCH, HIT_LOCATION_TORSO);
                attack.attackerFlags = DAM_CRITICAL;
                attack.attackerDamage = damage;
                combat_display(&attack);
                report.check(true, "critical miss/self damage " + std::to_string(damage));
            }
            combat_ctd_init(&attack, defender, defender == rat ? obj_dude : rat,
                HIT_MODE_PUNCH, HIT_LOCATION_TORSO);
            combat_display(&attack);
            report.check(true, "ordinary miss displayed");
            attack.attackerFlags = DAM_HIT;
            attack.defenderDamage = 20;
            attack.defenderFlags = DAM_DEAD;
            combat_display(&attack);
            report.check(true, "fatal hit displayed before damage application");
        }

        // Drive real attack registration, animations, completion callback, text
        // and HP changes. Only the isolated unsaved test map is affected.
        hdPlayerSetEnabled(true);
        Rect moved;
        int adjacent = -1;
        for (int direction = 0; direction < 6; ++direction) {
            int tile = tile_num_in_direction(obj_dude->tile, direction, 1);
            if (hexGridTileIsValid(tile) && obj_blocking_at(rat, tile, 0) == nullptr) {
                adjacent = tile;
                break;
            }
        }
        report.check(adjacent != -1 && obj_move_to_tile(rat, adjacent, 0, &moved) == 0,
            "rat positioned on free adjacent hex for animated combat");
        if (report.failed != 0) return 22;
        tile_refresh_display();
        unsigned int savedCombatState = combat_state;
        combat_state |= COMBAT_STATE_0x01;
        add_bk_process(object_animate);
        roll_set_seed(14112026);
        int bitesWithDamage = 0;
        for (int round = 0; round < 8; ++round) {
            critter_adjust_hits(obj_dude, stat_level(obj_dude, STAT_MAXIMUM_HIT_POINTS));
            int beforeHp = critter_get_hits(obj_dude);
            rat->data.critter.combat.ap = 20;
            report.text << "ANIMATION rat attack " << round << std::endl;
            int status = combat_attack(rat, obj_dude, HIT_MODE_PUNCH, HIT_LOCATION_TORSO);
            combat_turn_run();
            report.check(status == 0 && !combat_call_display, "rat attack and completion callback " + std::to_string(round));
            if (critter_get_hits(obj_dude) < beforeHp) ++bitesWithDamage;
        }
        report.check(bitesWithDamage > 0, "animated rat bites applied real HP damage");
        STRUCT_664980 damageOverride = {};
        damageOverride.minDamage = 100;
        damageOverride.maxDamage = 100;
        STRUCT_664980* savedOverride = gcsd;
        gcsd = &damageOverride;
        for (int round = 0; round < 8 && !critter_is_dead(rat); ++round) {
            obj_dude->data.critter.combat.ap = 20;
            report.text << "ANIMATION player attack " << round << std::endl;
            int status = combat_attack(obj_dude, rat, HIT_MODE_PUNCH, HIT_LOCATION_TORSO);
            combat_turn_run();
            report.check(status == 0 && !combat_call_display, "player attack and completion callback " + std::to_string(round));
        }
        gcsd = savedOverride;
        report.check(critter_is_dead(rat), "animated player attack kills rat through actual damage processing");
        remove_bk_process(object_animate);
        combat_state = savedCombatState;
        tile_refresh_display();
        frame = capture(output / "rat-combat-finished.bmp", true);
        report.check(frame.valid && frame.hdDrawn, "HD cave renders after animated combat");
        std::ofstream result(output / "result.json");
        result << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed << "}\n";
        report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
        return report.failed == 0 ? 0 : 22;
    }
    if (SDL_getenv("FALLOUT_HD_VIEWPORT_ONLY")) {
        viewportRegression(output, report);
        std::ofstream result(output / "result.json");
        result << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed << "}\n";
        report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
        return report.failed == 0 ? 0 : 22;
    }
    const char* benchmarkEnv = SDL_getenv("FALLOUT_HD_WORLD_BENCHMARK");
    const std::string benchmarkDirectory = benchmarkEnv != nullptr ? benchmarkEnv : "";
    if (!benchmarkDirectory.empty()) return hdWorldPilotBenchmark(benchmarkDirectory.c_str());
    if (SDL_getenv("FALLOUT_HD_CAVE_FALLBACK_TEST")) {
        const Snapshot before=snapshot({});
        report.check(hdWorldCaveAssetCount()==0,"missing or invalid optional cave masters rejected");
        report.check(hdWorldCaveAssignmentCount()==76,"optional failures keep stable placement indices");
        int selected=0;for(auto* o:objects()) selected+=hdWorldCaveAssetForObject(o)!=0;
        report.check(selected==0,"every unavailable new appearance falls back to original object art");
        tile_refresh_display();const Capture fallback=capture(output/"cave-fallback-hd.bmp",true);
        hdWorldSetCaveVarietyEnabled(false);tile_refresh_display();
        const Capture previous=capture({},true);
        report.check(fallback.valid && fallback.pixels==previous.pixels,"unavailable new pack restores exact previous HD frame");
        compare(report,before,snapshot({}),"optional cave fallback");
        std::ofstream result(output/"result.json");
        result<<"{\"passed\":"<<report.passed<<",\"failed\":"<<report.failed<<"}\n";
        report.text<<"TOTAL "<<report.passed<<" PASS "<<report.failed<<" FAIL"<<std::endl;
        return report.failed==0?0:23;
    }
    const char* expectedEnv = SDL_getenv("FALLOUT_HD_WORLD_EXPECT_ASSETS");
    const std::string expectedAssets = expectedEnv != nullptr ? expectedEnv : "";
    if (!expectedAssets.empty()) {
        int mask = std::atoi(expectedAssets.c_str());
        report.check(mask >= 0 && mask <= 3, "valid expected asset bitmask");
        tile_refresh_display();
        Snapshot before = snapshot({});
        Capture classic = capture(output / "fallback-classic.bmp", false);
        Capture replacement = capture(output / "fallback-hd.bmp", true);
        for (int id = 1; id <= 2; ++id) {
            bool expected = (mask & (1 << (id - 1))) != 0;
            report.check(hdWorldAssetLoaded(id) == expected,
                "fallback expected load state for asset " + std::to_string(id));
            report.check(expected || hdWorldVisiblePixels(id) == 0,
                "unavailable asset has no HD pixels " + std::to_string(id));
        }
        report.check(classic.valid && replacement.valid, "fallback actual renderer captures");
        report.check(mask != 0 || (!replacement.hdDrawn && classic.pixels == replacement.pixels),
            "both unavailable assets restore pixel exact classic frame");
        report.check(mask == 0 || replacement.hdDrawn, "available replacement remains usable");
        compare(report, before, snapshot({}), "missing/corrupt asset fallback");
        std::ofstream result(output / "result.json");
        result << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed
            << ",\"expected_assets\":" << mask << "}\n";
        return report.failed == 0 ? 0 : 23;
    }
    const int originalTile = obj_dude->tile;
    const int originalCenter = tile_center_tile;
    const bool originalEnabled = hdWorldEnabled();
    std::vector<Object*> rocks;
    if (SDL_getenv("FALLOUT_HD_WORLD_DECOR_LAYOUT")) {
        std::ofstream layout(output / "walkable-layout.tsv");
        layout << "tile\tx\ty\tblocked\tpath_length\tfloor\twall_distance\tscenery_distance\n";
        const auto mapObjects = objects();
        for (int tile = 0; tile < HEX_GRID_SIZE; ++tile) {
            int x, y; tile_coord(tile, &x, &y, 0); x += 16; y += 8;
            const int squareTile = square_num(x, y, 0);
            if (squareTile < 0 || squareTile >= SQUARE_GRID_SIZE) continue;
            const int floor = square[0]->field_0[squareTile] & 0xFFF;
            // Exclude the cutaway rock fill, metal vault floor and exterior void.
            if (floor < 21 || floor > 69) continue;
            const bool blocked = obj_blocking_at(obj_dude, tile, 0) != nullptr;
            if (blocked) continue;
            unsigned char path[2000] {};
            int length = make_path(obj_dude, originalTile, tile, path, 1);
            if (length <= 0) continue;
            int wallDistance = 200, sceneryDistance = 200;
            for (const auto* object : mapObjects) {
                if (object->elevation != 0 || object->tile < 0 || object->flags & OBJECT_HIDDEN) continue;
                const int type = (object->fid >> 24) & 15;
                if (type == 3) wallDistance = std::min(wallDistance, tile_dist(tile, object->tile));
                if (type == 2) sceneryDistance = std::min(sceneryDistance, tile_dist(tile, object->tile));
            }
            layout << tile << '\t' << x << '\t' << y << '\t' << blocked << '\t' << length
                << '\t' << floor << '\t' << wallDistance << '\t' << sceneryDistance << '\n';
        }
    }
    for (Object* object : objects()) {
        if (object->fid == kRockFid && object->elevation == 0) rocks.push_back(object);
    }
    std::sort(rocks.begin(), rocks.end(), [&](Object* a, Object* b) {
        return tile_dist(originalTile, a->tile) < tile_dist(originalTile, b->tile);
    });
    int floors = 0;
    for (int index = 0; index < SQUARE_GRID_SIZE; ++index) {
        if ((square[0]->field_0[index] & 0xFFF) == kFloorId) ++floors;
    }
    report.check(rocks.size() == 13 && std::all_of(rocks.begin(), rocks.end(),
        [](Object* rock) { return rock->pid == kRockPid; }), "13 original rock03 instances and prototype IDs");
    report.check(floors == 96, "96 original cav1000 floor placements");
    std::vector<int> destinations;
    for (int distance = 1; distance <= 12 && destinations.size() < 12; ++distance) {
        for (int direction = 0; direction < ROTATION_COUNT && destinations.size() < 12; ++direction) {
            int target = tile_num_in_direction(originalTile, direction, distance);
            if (!hexGridTileIsValid(target) || obj_blocking_at(obj_dude, target, 0) != nullptr) continue;
            unsigned char path[2000];
            if (make_path(obj_dude, originalTile, target, path, 1) > 0) destinations.push_back(target);
        }
    }
    report.check(destinations.size() >= 3, "multiple real pathfinder routes around cave entrance");
    tile_refresh_display();
    hdWorldSetEnabled(false);
    Snapshot original = snapshot(destinations);
    Capture classic = capture(output / "entrance-classic.bmp", false);
    Capture hd = capture(output / "entrance-hd.bmp", true);
    if (SDL_getenv("FALLOUT_HD_SEAM_DIAGNOSTIC")) {
        const auto owners=worldOwners();
        std::ofstream binary(output/"owners.bin",std::ios::binary);
        binary.write(reinterpret_cast<const char*>(owners.data()),owners.size()*sizeof(unsigned int));
        std::ofstream layout(output/"owners-size.txt");
        layout<<screenGetWidth()<<' '<<screenGetHeight()<<' '<<gSdlSurface->pitch<<'\n';
        std::ofstream placements(output/"objects.tsv");
        placements<<"id\tfid\ttile\tasset\tsx\tsy\n";
        for(auto* o:objects()) placements<<o->id<<'\t'<<o->fid<<'\t'<<o->tile<<'\t'
            <<hdWorldResolveAsset(o->fid,o->frame,o->tile,o->elevation)<<'\t'<<o->sx<<'\t'<<o->sy<<'\n';
        std::ofstream result(output/"result.json");
        result<<"{\"passed\":"<<report.passed<<",\"failed\":"<<report.failed<<"}\n";
        return report.failed==0?0:22;
    }
    report.check(classic.valid && hd.valid, "classic and HD native SDL captures");
    report.check(!classic.hdDrawn && hd.hdDrawn, "HD toggle controls rendering");
    report.check(hdWorldAssetLoaded(1) && hdWorldAssetLoaded(2), "both pilot reference assets loaded");
    report.check(hdWorldLoadedAssetCount() == expectedAssetCount(),
        "all " + std::to_string(expectedAssetCount()) + " selected environment resources/frames loaded");
    report.check(hd.floorPixels > 0 && hd.rockPixels > 0, "both replacements visible at original entrance");
    report.check(classic.valid && hd.valid && classic.pixels != hd.pixels, "HD changes visible world pixels");
    int misplacedPixels = 0;
    std::array<int, 256> changedByAsset {};
    std::array<Rect,512> geometryBounds {};
    std::array<bool,512> geometryBoundValid {};
    for(auto* o:objects()) if(hdWorldCaveAssetForObject(o)==253) {
        const int i=hdWorldCavePlacementForObject(o);
        if(i>=0 && i<512) {obj_bound(o,&geometryBounds[i]);geometryBoundValid[i]=true;}
    }
    Object* skeleton = nullptr;
    for (auto* object : objects()) if (object->pid == 211 && object->fid == 113 && object->tile == 17488) skeleton = object;
    if (classic.valid && hd.valid && classic.width == hd.width && classic.height == hd.height) {
        auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
        for (int y = 0; y < hd.height; ++y) {
            for (int x = 0; x < hd.width; ++x) {
                size_t offset = static_cast<size_t>(y) * hd.width + x;
                if (classic.pixels[offset] == hd.pixels[offset]) continue;
                int logicalX = x * screenGetWidth() / hd.width;
                int logicalY = y * screenGetHeight() / hd.height;
                const unsigned int owner = hdWorldOwnerAt(screen + logicalY * gSdlSurface->pitch + logicalX);
                unsigned int id = owner >> 24;
                // Soft skeleton ownership is a separate cache, outside the environment registry.
                // Validate its original object bounds and exact texel, rather than accepting any250.
                const bool skeletonCell = id == 250 && skeleton && hdWorldSkeletonLoaded()
                    && logicalX >= skeleton->sx && logicalX < skeleton->sx + 67
                    && logicalY >= skeleton->sy && logicalY < skeleton->sy + 41
                    && (owner & 0xFFFFFF) == static_cast<unsigned int>((logicalY - skeleton->sy) * 67 + logicalX - skeleton->sx);
                const unsigned int gi=(owner>>15)&511;
                const auto& gr=geometryBounds[gi];
                const bool geometryCell=id==253 && geometryBoundValid[gi]
                    && logicalX>=gr.ulx && logicalX<=gr.lrx && logicalY>=gr.uly && logicalY<=gr.lry
                    && (owner&32767)==static_cast<unsigned int>((logicalY-gr.uly)*(gr.lrx-gr.ulx+1)+logicalX-gr.ulx);
                if (id < 1 || id > 255 || (!hdWorldAssetLoaded(id) && !skeletonCell && !geometryCell)) ++misplacedPixels;
                else ++changedByAsset[id];
            }
        }
    }
    report.check(misplacedPixels == 0 && changedByAsset[1] > 0 && changedByAsset[2] > 0,
        "HD pixel changes align exactly with original screen ownership (" + std::to_string(misplacedPixels)
        + " misplaced; floor " + std::to_string(changedByAsset[1]) + "; rock " + std::to_string(changedByAsset[2]) + ")");
    report.check(classic.stateRestored && hd.stateRestored, "renderer logical scale viewport and clip preserved");
    compare(report, original, snapshot(destinations), "entrance HD toggle");
    if(SDL_getenv("FALLOUT_HD_WALL_OCCLUSION_ONLY")) {
        const auto poses=findOverlapPoses(rocks);
        checkOverlap(report,output,poses[0],"actor-front");checkOverlap(report,output,poses[1],"actor-behind");
        std::ofstream result(output/"result.json");result<<"{\"passed\":"<<report.passed<<",\"failed\":"<<report.failed<<"}\n";
        return report.failed==0?0:22;
    }
    if (hdWorldTileVariantCount() > 0 || SDL_getenv("FALLOUT_HD_TILE_EXPECT_COUNT")) {
        const char* expected = SDL_getenv("FALLOUT_HD_TILE_EXPECT_COUNT");
        if (expected) report.check(hdWorldTileVariantCount() == std::atoi(expected), "expected compatible floor/cutaway pages loaded");
        const bool wasEnabled = hdWorldTileVariantsEnabled();
        bool stable = true, valid = true, invalid = true;
        int varied = 0, plain = 0;
        std::ofstream assignments(output / "tile-variant-assignments.tsv");
        assignments << "square\tfid\tbase\tvariant_slot\n";
        std::array<std::set<int>, 256> choices;
        for (int cell = 0; cell < SQUARE_GRID_SIZE; ++cell) {
            const int fid = art_id(OBJ_TYPE_TILE, square[0]->field_0[cell] & 4095, 0, 0, 0);
            const int base = hdWorldResolveAsset(fid);
            const int slot = hdWorldResolveTileVariant(fid, cell, 0);
            valid &= slot >= 0 && slot <= 3 && (slot == 0 || (base > 0 && hdWorldAssetIsFloor(base)));
            stable &= slot == hdWorldResolveTileVariant(fid, cell, 0);
            invalid &= hdWorldResolveTileVariant(fid, -1, 0) == 0
                && hdWorldResolveTileVariant(fid, 10000, 0) == 0
                && hdWorldResolveTileVariant(fid, cell, -1) == 0
                && hdWorldResolveTileVariant(fid, cell, 3) == 0;
            if (slot) ++varied; else ++plain;
            if (base > 0 && base < 256) choices[base].insert(slot);
            assignments << cell << '\t' << fid << '\t' << base << '\t' << slot << '\n';
        }
        report.check(stable && valid && invalid, "tile variants stable, square-grid bounded and restricted to registered tiles");
        report.check(hdWorldResolveTileVariant(kRockFid, 1234, 0) == 0, "scenery cannot select tile pages");
        if (hdWorldTileVariantCount() == 30) {
            report.check(choices[62].size() == 4 && choices[63].size() == 4, "both upper cutaway bases use all four appearances (2 to 8)");
            for (int base : {1,34,35,36,47,51,53,56})
                report.check(choices[base].size() == 4, "floor base " + std::to_string(base) + " uses all four appearances");
        }
        if (hdWorldTileVariantCount() > 0 && wasEnabled) report.check(varied > 20 && plain > 20, "map retains base tiles and distributes multiple new floor/cutaway appearances");
        const auto indexed = worldPixels();
        hdWorldSetTileVariantsEnabled(false); tile_refresh_display();
        Capture baseTiles = capture(output / "tile-variants-before.bmp", true);
        Capture classicTiles = capture({}, false);
        bool disabledBase = true;
        for (int cell = 0; cell < SQUARE_GRID_SIZE; cell += 17) {
            const int fid = art_id(OBJ_TYPE_TILE, square[0]->field_0[cell] & 4095, 0, 0, 0);
            disabledBase &= hdWorldResolveTileVariant(fid, cell, 0) == 0;
        }
        report.check(disabledBase, "disabling tile variety selects exact existing base pages");
        hdWorldSetTileVariantsEnabled(wasEnabled); tile_refresh_display();
        Capture newTiles = capture(output / "tile-variants-after.bmp", true);
        report.check(classicTiles.pixels == classic.pixels, "tile variants preserve exact F11 classic pixels");
        report.check(indexed == worldPixels(), "tile variants preserve every original indexed framebuffer pixel");
        report.check(newTiles.pixels == hd.pixels, "restoring tile variants reproduces exact entrance frame");
        int changed = 0, outside = 0, blueArtifacts = 0;
        if (baseTiles.valid && newTiles.valid && baseTiles.pixels.size() == newTiles.pixels.size()) {
            auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
            for (int y = 0; y < newTiles.height; ++y) for (int x = 0; x < newTiles.width; ++x) {
                const size_t at = static_cast<size_t>(y) * newTiles.width + x;
                if (newTiles.pixels[at] == baseTiles.pixels[at]) continue;
                ++changed;
                int lx = x * screenGetWidth() / newTiles.width, ly = y * screenGetHeight() / newTiles.height;
                const auto token = hdWorldOwnerAt(screen + ly * gSdlSurface->pitch + lx);
                const int id = token >> 24;
                // Soft scenery/actors composite their saved floor underlay.
                const bool underlay = (id >= 224 && id <= 239) || id == 249 || id == 250 || id == 252 || id == 253;
                if (!hdWorldAssetIsFloor(id) && !underlay) ++outside;
                const auto blue = [](uint32_t pixel) {
                    return int(pixel & 255) > int((pixel >> 16) & 255) + 12
                        && int(pixel & 255) > int((pixel >> 8) & 255) + 12;
                };
                if ((hdWorldAssetIsFloor(id) || underlay) && blue(newTiles.pixels[at]) && !blue(baseTiles.pixels[at])) ++blueArtifacts;
            }
        }
        report.check(outside == 0 && (hdWorldTileVariantCount() == 0 || !wasEnabled || changed > 100),
            "new tile texture pixels stay on original floor/cutaway and soft underlays (" + std::to_string(changed) + " changed, " + std::to_string(outside) + " outside)");
        report.check(blueArtifacts == 0, "neutral tile pages introduce no indexed blue speckles under transparent scenery (" + std::to_string(blueArtifacts) + ")");
        Rect partial {screenGetWidth()/3, screenGetHeight()/5, screenGetWidth()*2/3, screenGetHeight()*3/4};
        tile_refresh_rect(&partial, 0);
        report.check(capture({}, true).pixels == newTiles.pixels, "clipped partial tile redraw agrees with complete frame");
        compare(report, original, snapshot(destinations), "floor/cutaway appearance variants");
    }
    if (SDL_getenv("FALLOUT_HD_TILE_VARIANT_SMOKE")) {
        std::ofstream summary(output / "result.json");
        summary << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed
            << ",\"tile_variants\":" << hdWorldTileVariantCount() << "}\n";
        return report.failed == 0 ? 0 : 22;
    }
    if (hdWorldWallVariantCount() > 0) {
        std::ofstream assignments(output / "wall-variant-assignments.tsv");
        assignments << "object\tfid\ttile\televation\tbase\tappearance\n";
        int varied = 0;
        bool valid = true, stable = true, restricted = true, invalidLocations = true;
        std::set<int> appearances;
        for (Object* object : objects()) {
            int base = hdWorldResolveAsset(object->fid, object->frame);
            int selected = hdWorldResolveAsset(object->fid, object->frame, object->tile, object->elevation);
            if (selected != base) {
                ++varied;
                valid &= selected >= 175 && selected <= 223 && hdWorldAssetLoaded(selected);
                restricted &= ((object->fid >> 24) & 15) == 3 && object->frame == 0;
                appearances.insert(selected);
            }
            stable &= selected == hdWorldResolveAsset(object->fid, object->frame, object->tile, object->elevation);
            invalidLocations &= base == hdWorldResolveAsset(object->fid, object->frame, -1, object->elevation)
                && base == hdWorldResolveAsset(object->fid, object->frame, 40000, object->elevation)
                && base == hdWorldResolveAsset(object->fid, object->frame, object->tile, 3);
            if (((object->fid >> 24) & 15) == 3)
                assignments << object->id << '\t' << object->fid << '\t' << object->tile << '\t'
                    << object->elevation << '\t' << base << '\t' << selected << '\n';
        }
        report.check(hdWorldWallVariantCount() == expectedAssetCount() - 174 - hdWorldDecorationAssetCount() - hdWorldCaveAssetCount(), "all optional wall appearances loaded");
        report.check(varied >= 20 && appearances.size() >= 8 && valid, "existing repeated walls receive multiple valid appearances");
        report.check(stable && restricted, "appearance selection stable and limited to existing static walls");
        report.check(invalidLocations, "invalid locations safely retain base appearances");
        hdWorldSetWallVariantsEnabled(false);
        tile_refresh_display();
        Capture plain = capture(output / "wall-variants-base.bmp", true);
        hdWorldSetWallVariantsEnabled(true);
        tile_refresh_display();
        Capture variedFrame = capture(output / "wall-variants-enabled.bmp", true);
        int changed = 0, outside = 0;
        if (plain.valid && variedFrame.valid && plain.pixels.size() == variedFrame.pixels.size()) {
            auto* screen = static_cast<unsigned char*>(gSdlSurface->pixels);
            for (int y = 0; y < variedFrame.height; ++y) for (int x = 0; x < variedFrame.width; ++x) {
                size_t pos = static_cast<size_t>(y) * variedFrame.width + x;
                if (plain.pixels[pos] == variedFrame.pixels[pos]) continue;
                ++changed;
                int lx = x * screenGetWidth() / variedFrame.width, ly = y * screenGetHeight() / variedFrame.height;
                const unsigned int token = hdWorldOwnerAt(screen + ly * gSdlSurface->pitch + lx);
                unsigned int owner = token >> 24;
                if (!appearances.count(owner) && !hdWorldCaveBackgroundHasAsset(token,175,223)) ++outside;
            }
        }
        report.check((hdWorldWallGeometryEnabled() && hdWorldWallGeometryCount() ? changed==0 : changed>100) && outside == 0, "wall variety visible or replaced by connected geometry; every other world/UI pixel preserved (" + std::to_string(changed) + " changed)");
        report.check(variedFrame.valid && variedFrame.pixels == hd.pixels, "restoring variants reproduces identical entrance frame");
        compare(report, original, snapshot(destinations), "wall appearances");
    }
    if (SDL_getenv("FALLOUT_HD_WORLD_VARIANT_SMOKE") != nullptr) {
        std::ofstream summary(output / "result.json");
        summary << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed
            << ",\"loaded_resources\":" << hdWorldLoadedAssetCount()
            << ",\"wall_variants\":" << hdWorldWallVariantCount() << "}\n";
        report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
        return report.failed == 0 ? 0 : 22;
    }
    if (hdWorldDecorationCount() > 0) {
        std::vector<int> decorDestinations;
        for (int i = 0; i < hdWorldDecorationCount(); ++i) decorDestinations.push_back(hdWorldDecorationAt(i)->tile);
        const Snapshot decorBefore = snapshot(decorDestinations);
        const auto indexedBefore = worldPixels();
        hdWorldSetDecorationsEnabled(false);
        tile_refresh_display();
        Capture noDecor = capture(output / "decor-disabled-hd.bmp", true);
        const Snapshot decorOff = snapshot(decorDestinations);
        report.check(indexedBefore == worldPixels(), "decorations leave every original indexed world pixel unchanged");
        hdWorldSetDecorationsEnabled(true);
        tile_refresh_display();
        Capture withDecor = capture(output / "decor-enabled-hd.bmp", true);
        compare(report, decorOff, decorBefore, "decorations enabled versus disabled");
        report.check(withDecor.valid && withDecor.pixels == hd.pixels,
            "decoration redraw restores exact entrance frame");
        auto* world = win_get_buf(display_win);
        int changed = 0, outside = 0;
        for (int y = 0; y < hd.height; ++y) for (int x = 0; x < hd.width; ++x) {
            const size_t offset = static_cast<size_t>(y) * hd.width + x;
            if (noDecor.pixels[offset] == withDecor.pixels[offset]) continue;
            ++changed;
            const int lx = x * screenGetWidth() / hd.width, ly = y * screenGetHeight() / hd.height;
            const unsigned int token = hdWorldOwnerAt(static_cast<unsigned char*>(gSdlSurface->pixels) + ly * gSdlSurface->pitch + lx);
            const unsigned int owner = token >> 24;
            if ((owner < 240 || owner > 248) && !hdWorldCaveBackgroundHasAsset(token,240,248)
                && (!hdWorldAssetIsFloor(owner) || hdWorldCampfireShadowFactorAt(lx, ly, 0) >= 128)) ++outside;
        }
        report.check(changed > 500 && outside == 0, "only decoration pixels or their declared floor shadow fringe differ; cave and HUD preserved");
        std::ofstream placementReport(output / "decor-placement-checks.tsv");
        placementReport << "asset\ttile\tvisible_pixels\tlight\tpath_length\n";
        const int savedX = obj_dude->x, savedY = obj_dude->y;
        for (int i = 0; i < hdWorldDecorationCount(); ++i) {
            const auto& item = *hdWorldDecorationAt(i);
            const std::string name = "decor " + std::to_string(item.assetId) + " tile " + std::to_string(item.tile);
            tile_set_center(item.tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
            const auto decorOwners = worldOwners();
            // Check only this placement, not other copies of the same image.
            int decorWidth = 0, decorHeight = 0;
            report.check(hdWorldDecorationDimensions(item.assetId, &decorWidth, &decorHeight), name + " registered dimensions available");
            int cx, cy; tile_coord(item.tile, &cx, &cy, 0);
            const int left = cx + 16 + item.offsetX - decorWidth/2;
            const int top = cy + 8 + item.offsetY - decorHeight + 1;
            int visible = 0, incorrectLight = 0;
            const int expectedLight = std::clamp(std::max(light_get_ambient(), light_get_tile(0, item.tile)) >> 9, 0, 128);
            for (int y = std::max(0,top); y < std::min(win_height(display_win),top+decorHeight); ++y)
                for (int x = std::max(0,left); x < std::min(win_width(display_win),left+decorWidth); ++x) {
                const size_t pixel = static_cast<size_t>(y)*win_width(display_win)+x;
                if ((decorOwners[pixel] >> 24) != item.assetId) continue;
                ++visible;
                if (hdWorldLightAt(world + pixel) != expectedLight) ++incorrectLight;
            }
            report.check(visible > 40, name + " visible at its location at game scale");
            report.check(incorrectLight == 0, name + " uses actual ambient/tile lighting");
            report.check(obj_blocking_at(obj_dude, item.tile, 0) == nullptr && !decorBefore.paths[i].empty(),
                name + " reachable by original pathfinder on a free hex");
            placementReport << item.assetId << '\t' << item.tile << '\t' << visible << '\t'
                << expectedLight << '\t' << decorBefore.paths[i].size() << '\n';
            capture(output / ("decor-" + std::to_string(item.assetId) + "-tile-" + std::to_string(item.tile) + ".bmp"), true);
            if (item.assetId == 248 && item.flat) checkCampfireShadow(item, output, report);
            // Stage the actor on the decoration's own hex: it must never cover their feet/body.
            Rect rect;
            const bool moved = obj_move_to_tile(obj_dude, item.tile, 0, &rect) == 0;
            const int flags = obj_dude->flags;
            obj_dude->flags |= OBJECT_HIDDEN;
            tile_refresh_display();
            const auto hiddenOwners = worldOwners();
            obj_dude->flags = flags;
            tile_refresh_display();
            const auto actorOwners = worldOwners();
            const SpriteMask actor = spriteMask(obj_dude);
            int overlaps = 0, coveredActor = 0;
            for (int y = std::max(0, actor.y); y < std::min(win_height(display_win), actor.y + actor.height); ++y)
                for (int x = std::max(0, actor.x); x < std::min(win_width(display_win), actor.x + actor.width); ++x) {
                    const size_t pixel = static_cast<size_t>(y) * win_width(display_win) + x;
                    if (actor.at(x, y) && (hiddenOwners[pixel] >> 24) == item.assetId) {
                        ++overlaps;
                        if ((actorOwners[pixel] >> 24) == item.assetId) ++coveredActor;
                    }
                }
            report.check(moved && overlaps > 0 && coveredActor == 0, name + " actor stands on decoration without overdraw");
            capture(output / ("decor-" + std::to_string(item.assetId) + "-tile-" + std::to_string(item.tile) + "-walkover.bmp"), true);
            if (item.assetId == 248 && item.flat) checkCampfireShadowActor(actor, output, report);
            obj_move_to_tile(obj_dude, originalTile, 0, &rect);
            obj_dude->x = savedX; obj_dude->y = savedY;
            tile_refresh_display();
        }
        // Find real front/back overlap on each standing prop using the same tile sorting as actors.
        std::set<int> checkedStandingImages;
        for (int i = 0; i < hdWorldDecorationCount(); ++i) {
            const auto& item = *hdWorldDecorationAt(i);
            if (item.flat || !checkedStandingImages.insert(item.assetId).second) continue;
            tile_set_center(item.tile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
            bool front = false, behind = false;
            for (int distance = 1; distance <= 2 && !(front && behind); ++distance)
                for (int direction = 0; direction < ROTATION_COUNT && !(front && behind); ++direction) {
                    const int tile = tile_num_in_direction(item.tile, direction, distance);
                    if (!hexGridTileIsValid(tile) || obj_blocking_at(obj_dude, tile, 0)) continue;
                    Rect rect; obj_move_to_tile(obj_dude, tile, 0, &rect);
                    const int flags = obj_dude->flags;
                    obj_dude->flags |= OBJECT_HIDDEN; tile_refresh_display();
                    const auto hiddenOwners = worldOwners();
                    obj_dude->flags = flags; tile_refresh_display();
                    const auto visibleOwners = worldOwners();
                    const SpriteMask actor = spriteMask(obj_dude);
                    int visible = 0, hidden = 0;
                    for (int y = std::max(0, actor.y); y < std::min(win_height(display_win), actor.y + actor.height); ++y)
                        for (int x = std::max(0, actor.x); x < std::min(win_width(display_win), actor.x + actor.width); ++x) {
                            const size_t pixel = static_cast<size_t>(y) * win_width(display_win) + x;
                            if (!actor.at(x, y) || (hiddenOwners[pixel] >> 24) != item.assetId) continue;
                            if ((visibleOwners[pixel] >> 24) == item.assetId) ++hidden;
                            else if (visibleOwners[pixel] == 0) ++visible;
                        }
                    if (visible > 5 && !front) {
                        front = true; capture(output / ("decor-" + std::to_string(item.assetId) + "-actor-front.bmp"), true);
                    }
                    if (hidden > 5 && !behind) {
                        behind = true; capture(output / ("decor-" + std::to_string(item.assetId) + "-actor-behind.bmp"), true);
                    }
                }
            report.check(front && behind, "standing decor " + std::to_string(item.assetId) + " sorts both in front of and behind actor");
        }
        Rect restoreRect;
        obj_move_to_tile(obj_dude, originalTile, 0, &restoreRect);
        obj_dude->x = savedX; obj_dude->y = savedY;
        tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        compare(report, decorBefore, snapshot(decorDestinations), "after walking across decorations");
        report.check(capture({}, true).pixels == hd.pixels, "decor walkover tests restore exact original view");
        const bool pilotMap = hdWorldDecorationsActive(0);
        std::array<char, sizeof(map_data.name)> name;
        std::memcpy(name.data(), map_data.name, name.size());
        std::strcpy(map_data.name, "OTHER.MAP");
        report.check(pilotMap && !hdWorldDecorationsActive(0) && !hdWorldDecorationsActive(1),
            "decorations limited to first cave and ground elevation");
        std::memcpy(map_data.name, name.data(), name.size());
    }
    hdWorldSetEnabled(false);
    game_handle_input(KEY_F11, false);
    report.check(hdWorldEnabled(), "real game F11 handler enables HD");
    game_handle_input(KEY_F11, false);
    report.check(!hdWorldEnabled(), "real game F11 handler restores classic");
    compare(report, original, snapshot(destinations), "real F11 toggles");

    // Simulate the map name left by map_load_in_game after loading saved state.
    // This checks the actual art-rendering gate, not a real savegame round trip.
    std::array<char, sizeof(map_data.name)> originalMapName;
    std::memcpy(originalMapName.data(), map_data.name, originalMapName.size());
    std::strcpy(map_data.name, "V13ENT.SAV");
    tile_refresh_display();
    Capture savedMapName = capture(output / "saved-map-name-hd.bmp", true);
    report.check(savedMapName.valid && savedMapName.hdDrawn
        && savedMapName.floorPixels > 0 && savedMapName.rockPixels > 0,
        "simulated post-load SAV name draws both real HD resources");
    report.check(savedMapName.valid && savedMapName.pixels == hd.pixels,
        "simulated post-load SAV name preserves exact MAP HD frame");
    game_handle_input(KEY_F11, false);
    report.check(!hdWorldEnabled(), "real F11 handler disables HD with SAV map name");
    game_handle_input(KEY_F11, false);
    report.check(hdWorldEnabled(), "real F11 handler enables HD with SAV map name");
    std::memcpy(map_data.name, originalMapName.data(), originalMapName.size());
    hdWorldSetEnabled(false);
    tile_refresh_display();
    compare(report, original, snapshot(destinations), "restored map after SAV name regression");

    int worldHeight = win_height(display_win);
    Rect hudRect;
    const bool hudRectValid = win_get_rect(interfaceWindow, &hudRect) == 0;
    report.check(hudRectValid && sameRegion(classic, hd, hudRect.ulx, hudRect.uly, INTERFACE_BAR_WIDTH, INTERFACE_BAR_HEIGHT),
        "entire classic HUD remains pixel identical");
    Capture classic4k = capture(output / "entrance-classic-4k.bmp", false, 3840, 2160);
    Capture hd4k = capture(output / "entrance-hd-4k.bmp", true, 3840, 2160);
    report.check(classic4k.valid && hd4k.valid && hd4k.hdDrawn && hd4k.stateRestored
        && hd4k.width == 3840 && hd4k.height == 2160 && classic4k.pixels != hd4k.pixels,
        "actual 4K SDL target renders HD at four samples per logical pixel");
    report.check(hudRectValid && sameRegion(classic4k, hd4k, hudRect.ulx, hudRect.uly, INTERFACE_BAR_WIDTH, INTERFACE_BAR_HEIGHT),
        "4K HD world preserves classic HUD pixels");
    Capture fallback = capture(output / "entrance-disabled.bmp", false);
    report.check(fallback.valid && classic.pixels == fallback.pixels, "disabling HD restores exact classic frame");
    std::array<unsigned char, 768> normalPalette;
    std::memcpy(normalPalette.data(), getSystemPalette(), normalPalette.size());
    palette_set_to(black_palette);
    Capture blackClassic = capture({}, false);
    Capture blackHd = capture(output / "palette-black.bmp", true);
    report.check(blackClassic.valid && blackHd.valid && blackClassic.pixels == blackHd.pixels
        && std::all_of(blackHd.pixels.begin(), blackHd.pixels.end(), [](uint32_t p) { return (p & 0xFFFFFF) == 0; }),
        "HD follows real black palette fade without glowing artwork");
    palette_set_to(normalPalette.data());
    fadeRegression(output, report);
    greyBufferRegression(output, report);

    const std::array<int, 4> cameraOffsets { -4, 4, -800, 800 };
    caveVarietyRegression(output,report);
    wallGeometryRegression(output,report);
    vaultRockRegression(output,report);
    wallAccentRegression(output,report);
    const std::array<const char*, 4> cameraNames { "camera-left", "camera-right", "camera-up", "camera-down" };
    for (size_t i = 0; i < cameraOffsets.size(); ++i) {
        int target = originalCenter + cameraOffsets[i];
        bool moved = tile_set_center(target, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS) == 0;
        report.check(moved && tile_center_tile == target, std::string(cameraNames[i]) + " real camera relocation");
        Capture frame = capture(output / (std::string(cameraNames[i]) + ".bmp"), true);
        report.check(frame.valid && frame.hdDrawn && frame.stateRestored, std::string(cameraNames[i]) + " refreshed HD frame");
        compare(report, original, snapshot(destinations), cameraNames[i]);
    }
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    Capture restored = capture(output / "camera-restored.bmp", true);
    report.check(restored.valid && restored.pixels == hd.pixels, "camera return restores exact frame without HD trails");
    const std::array<std::array<int, 2>, 4> scrolls { { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } } };
    for (size_t i = 0; i < scrolls.size(); ++i) {
        tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        SDL_Delay(35); // map_scroll has a 33 ms input throttle.
        int scrollResult = map_scroll(scrolls[i][0], scrolls[i][1]);
        report.check(scrollResult == 0, std::string(cameraNames[i]) + " actual incremental map_scroll");
        Capture incremental = capture(output / (std::string(cameraNames[i]) + "-incremental.bmp"), true);
        // Reconstruct RGB without the shifted cache so the reference cannot
        // silently share an incorrectly moved texture with the incremental frame.
        hdWorldReleaseTextures();
        tile_refresh_display();
        Capture full = capture({}, true);
        report.check(incremental.valid && full.valid && incremental.pixels == full.pixels,
            std::string(cameraNames[i]) + " incremental cache matches uncached full redraw");
    }
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    handleWindowSizeChanged();
    tile_refresh_display();
    win_refresh_all(&scr_size);
    Capture recreated = capture(output / "renderer-recreated.bmp", true);
    report.check(recreated.valid && recreated.pixels == hd.pixels,
        "SDL renderer recreation restores exact HD frame and texture resources");

    // Real views across the cave, including the 342x224 vault sprite (>65535 texels).
    const int sceneTiles[] = {16290, 18721, 22662, 24097, 27075, 27871};
    std::set<unsigned int> seenResources;
    unsigned int largestVaultOffset = 0;
    for (int sceneTile : sceneTiles) {
        bool moved = tile_set_center(sceneTile, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS) == 0;
        Capture scene = capture(output / ("cave-" + std::to_string(sceneTile) + "-hd.bmp"), true);
        Capture sceneClassic = capture(output / ("cave-" + std::to_string(sceneTile) + "-classic.bmp"), false);
        report.check(moved && scene.valid && sceneClassic.valid && scene.hdDrawn,
            "real full environment scene " + std::to_string(sceneTile));
        unsigned char* world = win_get_buf(display_win);
        int worldSize = win_width(display_win) * win_height(display_win);
        for (int pixel = 0; pixel < worldSize; pixel++) {
            unsigned int owner = hdWorldOwnerAt(world + pixel);
            if (owner) seenResources.insert(owner >> 24);
            if ((owner >> 24) == 16) largestVaultOffset = std::max(largestVaultOffset, owner & 0xFFFFFFU);
        }
    }
    report.check(seenResources.size() >= 30, "multiple floor wall scenery resources rendered across cave (" + std::to_string(seenResources.size()) + ")");
    report.check(largestVaultOffset > 65535, "large vault sprite retains texels beyond 16-bit offset");
    compare(report, original, snapshot(destinations), "full cave camera coverage");
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    if (hdWorldAssetLoaded(160)) {
        checkDoorFrames(report, output, destinations, 33554713, 160, "vault-outer-wheel");
    }
    const int innerDoorBase=hdWorldResolveAsset(33554715,0);
    if (innerDoorBase && hdWorldResolveAsset(33554715,1)==innerDoorBase+1) {
        checkDoorFrames(report, output, destinations, 33554715, innerDoorBase, "vault-inner-door");
    }
    hdWorldSetEnabled(true);
    checkCursor(report, output);

    // Test a real GNW opaque window over the scene, including an HD rock.
    Rect rockRect;
    if (!rocks.empty()) obj_bound(rocks.front(), &rockRect);
    else rockRect = { screenGetWidth() / 2, worldHeight / 2, 0, 0 };
    int overlayX = std::clamp(rockRect.ulx, 0, screenGetWidth() - 140);
    int overlayY = std::clamp(rockRect.uly, 0, worldHeight - 90);
    int overlay = win_add(overlayX, overlayY, 140, 90, colorTable[31744], WINDOW_MODAL | WINDOW_MOVE_ON_TOP);
    report.check(overlay != -1, "real GNW overlay created above world");
    if (overlay != -1) {
        win_draw(overlay);
        Capture uiClassic = capture(output / "overlay-classic.bmp", false);
        Capture uiHd = capture(output / "overlay-hd.bmp", true);
        report.check(sameRegion(uiClassic, uiHd, overlayX + 1, overlayY + 1, 138, 88),
            "HD does not paint through opaque GNW overlay");
        win_delete(overlay);
        tile_refresh_display();
    }

    std::array<Pose, 2> poses = findOverlapPoses(rocks);
    report.check(poses[0].overlapVisible >= 20, "free front hex with measurable actor/rock overlap");
    report.check(poses[1].overlapHidden >= 20, "free rear hex with measurable actor/rock overlap");
    checkOverlap(report, output, poses[0], "actor-front");
    checkOverlap(report, output, poses[1], "actor-behind");
    Rect restoreRect;
    obj_move_to_tile(obj_dude, originalTile, 0, &restoreRect);
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    hdWorldSetEnabled(originalEnabled);

    viewportRegression(output, report);

    std::ofstream summary(output / "result.json");
    summary << "{\n  \"passed\": " << report.passed << ",\n  \"failed\": " << report.failed
        << ",\n  \"map\": \"V13ENT.MAP\",\n  \"loaded_resources\": " << hdWorldLoadedAssetCount()
        << ",\n  \"scene_resources_seen\": " << seenResources.size()
        << ",\n  \"decoration_images\": " << hdWorldDecorationAssetCount()
        << ",\n  \"decoration_placements\": " << hdWorldDecorationCount()
        << ",\n  \"largest_vault_texel_offset\": " << largestVaultOffset
        << ",\n  \"floor_instances\": " << floors
        << ",\n  \"rock_instances\": " << rocks.size() << ",\n  \"collision_hexes_checked\": " << original.blockers.size()
        << ",\n  \"blocked_hexes\": " << original.blocked << ",\n  \"collision_hash\": \"" << original.collisionHash
        << "\",\n  \"path_routes_checked\": " << destinations.size()
        << ",\n  \"floor_visible_pixels\": " << hd.floorPixels << ",\n  \"rock_visible_pixels\": " << hd.rockPixels
        << ",\n  \"front_actor_tile\": " << poses[0].tile << ",\n  \"rear_actor_tile\": " << poses[1].tile
        << ",\n  \"capture_width\": " << hd.width << ",\n  \"capture_height\": " << hd.height << "\n}\n";
    report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
    return report.failed == 0 ? 0 : 22;
}

} // namespace fallout

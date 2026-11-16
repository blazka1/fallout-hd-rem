#include "game/hd_player_test.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <set>
#include <string>
#include <vector>

#include "game/anim.h"
#include "game/art.h"
#include "game/cycle.h"
#include "game/combat.h"
#include "game/game.h"
#include "game/gmouse.h"
#include "game/hd_player.h"
#include "game/hd_rat.h"
#include "game/hd_hud.h"
#include "game/hd_world_pilot.h"
#include "game/light.h"
#include "game/map.h"
#include "game/object.h"
#include "game/palette.h"
#include "game/scripts.h"
#include "game/stat.h"
#include "game/tile.h"
#include "plib/color/color.h"
#include "plib/gnw/gnw.h"
#include "plib/gnw/kb.h"
#include "plib/gnw/mouse.h"
#include "plib/gnw/svga.h"

namespace fallout {
namespace {
constexpr int kPlayerOwner = 249;

struct Report {
    std::ofstream text;
    int passed = 0, failed = 0;
    explicit Report(const std::filesystem::path& path) : text(path / "checks.txt") {}
    void check(bool ok, const std::string& name)
    {
        text << (ok ? "PASS " : "FAIL ") << name << std::endl;
        if (ok) ++passed; else ++failed;
    }
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

Capture refreshCapture(bool playerEnabled, const std::filesystem::path& path = {}, int width = 0, int height = 0)
{
    hdPlayerSetEnabled(playerEnabled);
    tile_refresh_display();
    return capture(path, width, height);
}

bool saveCrop(const Capture& frame, const std::filesystem::path& path, int anchorTile)
{
    if (!frame.valid) return false;
    int lx, ly; tile_coord(anchorTile, &lx, &ly, obj_dude->elevation);
    const int anchorX = (lx + 16) * frame.width / screenGetWidth();
    const int anchorY = (ly + 8) * frame.height / screenGetHeight();
    const int width = std::min(320, frame.width), height = std::min(320, frame.height);
    const int x = std::clamp(anchorX - width / 2, 0, frame.width - width);
    const int y = std::clamp(anchorY - height + 52, 0, frame.height - height);
    SDL_Surface* crop = SDL_CreateRGBSurfaceWithFormat(0, width, height, 32, SDL_PIXELFORMAT_ARGB8888);
    if (!crop) return false;
    for (int row = 0; row < height; ++row) std::memcpy(static_cast<unsigned char*>(crop->pixels) + row * crop->pitch,
        frame.pixels.data() + static_cast<size_t>(row + y) * frame.width + x, width * sizeof(uint32_t));
    const bool valid = SDL_SaveBMP(crop, path.string().c_str()) == 0;
    SDL_FreeSurface(crop);
    return valid;
}

struct Pose {
    int tile, elevation, fid, frame, rotation, x, y, flags, outline;
    explicit Pose(Object* object) : tile(object->tile), elevation(object->elevation), fid(object->fid), frame(object->frame),
        rotation(object->rotation), x(object->x), y(object->y), flags(object->flags), outline(object->outline) {}
    void restore() const
    {
        Rect dirty;
        obj_dude->flags = flags; obj_dude->outline = outline;
        obj_move_to_tile(obj_dude, tile, elevation, &dirty);
        obj_change_fid(obj_dude, fid, &dirty);
        obj_set_rotation(obj_dude, rotation, &dirty);
        obj_set_frame(obj_dude, frame, &dirty);
        obj_offset(obj_dude, x - obj_dude->x, y - obj_dude->y, &dirty);
    }
    bool equal() const
    {
        return obj_dude->tile == tile && obj_dude->elevation == elevation && obj_dude->fid == fid
            && obj_dude->frame == frame && obj_dude->rotation == rotation && obj_dude->x == x && obj_dude->y == y
            && obj_dude->flags == flags && obj_dude->outline == outline;
    }
};

bool setPose(int animation, int direction, int frame, int base = 11, int weapon = 0)
{
    Rect dirty;
    const int fid = art_id(OBJ_TYPE_CRITTER, base, animation, weapon, direction + 1);
    if (!art_exists(fid)) return false;
    return obj_change_fid(obj_dude, fid, &dirty) == 0
        && obj_set_rotation(obj_dude, direction, &dirty) == 0 && obj_set_frame(obj_dude, frame, &dirty) == 0;
}

uint64_t pixelHash(const Capture& image)
{
    uint64_t hash = 1469598103934665603ULL;
    for (auto pixel : image.pixels) { hash ^= pixel; hash *= 1099511628211ULL; }
    return hash;
}

std::vector<Object*> allObjects()
{
    std::set<Object*> result;
    for (Object* object = obj_find_first(); object; object = obj_find_next()) result.insert(object);
    return { result.begin(), result.end() };
}

std::vector<Object*> blockers()
{
    std::vector<Object*> result;
    for (int tile = 0; tile < HEX_GRID_SIZE; ++tile) result.push_back(obj_blocking_at(obj_dude, tile, obj_dude->elevation));
    return result;
}

std::vector<unsigned int> owners()
{
    auto* buffer = win_get_buf(display_win);
    const int size = win_width(display_win) * win_height(display_win);
    std::vector<unsigned int> result(size);
    for (int i = 0; i < size; ++i) result[i] = hdWorldOwnerAt(buffer + i);
    return result;
}

struct SpriteMask {
    int x = 0, y = 0, width = 0, height = 0;
    std::vector<unsigned char> pixels;
    bool at(int sx, int sy) const
    {
        const int dx = sx - x, dy = sy - y;
        return dx >= 0 && dy >= 0 && dx < width && dy < height && pixels[dy * width + dx] != 0;
    }
};

SpriteMask spriteMask(Object* object)
{
    SpriteMask mask;
    CacheEntry* handle = nullptr;
    Art* art = art_ptr_lock(object->fid, &handle);
    if (!art) return mask;
    mask.width = art_frame_width(art, object->frame, object->rotation);
    mask.height = art_frame_length(art, object->frame, object->rotation);
    int x, y; tile_coord(object->tile, &x, &y, object->elevation);
    mask.x = x + 16 + art->xOffsets[object->rotation] + object->x - mask.width / 2;
    mask.y = y + 8 + art->yOffsets[object->rotation] + object->y - mask.height + 1;
    auto* data = art_frame_data(art, object->frame, object->rotation);
    if (data && mask.width > 0 && mask.height > 0) mask.pixels.assign(data, data + mask.width * mask.height);
    art_ptr_unlock(handle);
    return mask;
}

bool sameHud(const Capture& a, const Capture& b)
{
    if (!a.valid || !b.valid || a.width != b.width || a.height != b.height) return false;
    const int y = win_height(display_win) * a.height / screenGetHeight();
    return std::equal(a.pixels.begin() + static_cast<size_t>(y) * a.width, a.pixels.end(),
        b.pixels.begin() + static_cast<size_t>(y) * b.width);
}

void checkFallback(Report& report, const std::filesystem::path& output, const std::string& label,
    int animation, int direction, int frame, int base = 11, int weapon = 0)
{
    report.check(setPose(animation, direction, frame, base, weapon), label + " original art pose exists");
    const auto original = refreshCapture(false);
    const auto replacement = refreshCapture(true, output / ("fallback-" + label + ".bmp"));
    report.check(!hdPlayerEligible(obj_dude), label + " renderer eligibility declines replacement");
    report.check(original.valid && replacement.valid && original.pixels == replacement.pixels,
        label + " pixel-exact classic actor fallback with HD cave retained");
    report.check(hdWorldVisiblePixels(kPlayerOwner) == 0, label + " no surviving player owner pixels");
}

void timedWalk(Report& report, const std::filesystem::path& output, bool requireCave = false);

void checkOcclusion(Report& report, const std::filesystem::path& output)
{
    const Pose saved(obj_dude);
    const int center = tile_center_tile;
    std::vector<Object*> geometry;
    for (Object* object : allObjects()) {
        const int type = FID_TYPE(object->fid);
        if (object->elevation == 0 && object->tile >= 0 && !(object->flags & OBJECT_HIDDEN)
            && (type == OBJ_TYPE_WALL || type == OBJ_TYPE_SCENERY)) geometry.push_back(object);
    }
    std::sort(geometry.begin(), geometry.end(), [&](Object* a, Object* b) {
        return tile_dist(saved.tile, a->tile) < tile_dist(saved.tile, b->tile);
    });
    bool found = false;
    int attempts = 0, checked = 0, translucent = 0, leaked = 0;
    bool stable = false;
    for (Object* wall : geometry) {
        if (found || attempts >= 160) break;
        tile_set_center(wall->tile, TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        for (int distance = 1; distance <= 3 && !found && attempts < 160; ++distance) {
            for (int direction = 0; direction < 6 && !found && attempts < 160; ++direction) {
                const int tile = tile_num_in_direction(wall->tile, direction, distance);
                if (!hexGridTileIsValid(tile) || obj_blocking_at(obj_dude, tile, 0)) continue;
                Rect dirty; obj_move_to_tile(obj_dude, tile, 0, &dirty); ++attempts;
                setPose(ANIM_WALK, 2, 0);
                hdPlayerSetEnabled(true); tile_refresh_display();
                const auto owner = owners();
                const auto mask = spriteMask(obj_dude);
                const int pitch = win_width(display_win), worldHeight = win_height(display_win);
                std::vector<unsigned char> hidden(static_cast<size_t>(pitch) * worldHeight);
                int hiddenCount = 0;
                for (int y = std::max(0, mask.y); y < std::min(worldHeight, mask.y + mask.height * 4 / 5); ++y) {
                    for (int x = std::max(0, mask.x); x < std::min(pitch, mask.x + mask.width); ++x) {
                        const size_t at = static_cast<size_t>(y) * pitch + x;
                        const int id = owner[at] >> 24;
                        if (mask.at(x, y) && id && id != kPlayerOwner && !hdWorldAssetIsFloor(id)) {
                            hidden[at] = hdWorldOwnerIsOpaque(owner[at]) ? 1 : 2; ++hiddenCount;
                        }
                    }
                }
                if (hiddenCount < 20 || hdWorldVisiblePixels(kPlayerOwner) < 20) continue;
                const auto visible = capture(output / "player-behind-geometry-hd.bmp");
                const int flags = obj_dude->flags; obj_dude->flags |= OBJECT_HIDDEN;
                tile_refresh_display();
                const auto absent = capture(output / "player-behind-geometry-hidden.bmp");
                obj_dude->flags = flags; tile_refresh_display();
                if (!visible.valid || !absent.valid) continue;
                hdWorldReleaseTextures(); tile_refresh_display();
                const auto fresh = capture();
                stable = fresh.valid && visible.pixels == fresh.pixels;
                for (int y = 0; y < visible.height; ++y) for (int x = 0; x < visible.width; ++x) {
                    const int lx = x * screenGetWidth() / visible.width;
                    const int ly = y * screenGetHeight() / visible.height;
                    if (ly < worldHeight && hidden[static_cast<size_t>(ly) * pitch + lx]) {
                        if (hidden[static_cast<size_t>(ly) * pitch + lx] == 2) { ++translucent; continue; }
                        ++checked;
                        const auto at = static_cast<size_t>(y) * visible.width + x;
                        if (visible.pixels[at] != absent.pixels[at]) ++leaked;
                    }
                }
                found = true;
            }
        }
    }
    report.check(found && checked + translucent > 0, "real passable cave position exposes visible and foreground-covered actor pixels");
    report.check(found && leaked == 0 && stable, "opaque geometry conceals player; translucent foreground cache matches fresh redraw ("
        + std::to_string(checked) + " opaque, " + std::to_string(translucent) + " translucent pixels)");
    if (found) {
        std::ofstream location(output / "cave-occlusion-location.json");
        location << "{\"tile\":" << obj_dude->tile << ",\"center\":" << tile_center_tile << "}";
        int savedPoses = 0, coveredPoses = 0;
        for (int direction = 0; direction < 6; ++direction) {
            for (int pose = -1; pose < 8; ++pose) {
                setPose(pose < 0 ? ANIM_STAND : ANIM_WALK, direction, std::max(0, pose));
                const auto frame = refreshCapture(true);
                const auto foreground = owners();
                if (std::any_of(foreground.begin(), foreground.end(), [](unsigned int owner) {
                    return !hdWorldOwnerIsOpaque(owner) && hdWorldCaveBackgroundHasAsset(owner, kPlayerOwner, kPlayerOwner);
                })) ++coveredPoses;
                char name[64];
                std::snprintf(name, sizeof(name), "cave-%s-d%d-f%03d.bmp", pose < 0 ? "stand" : "walk", direction, std::max(0, pose));
                if (saveCrop(frame, output / name, obj_dude->tile)) ++savedPoses;
            }
        }
        report.check(savedPoses == 54 && coveredPoses == 54,
            "all 54 poses captured through translucent cave foreground (" + std::to_string(coveredPoses) + " covered)");
        const auto walkOutput = output / "wall-walk";
        std::filesystem::create_directories(walkOutput);
        timedWalk(report, walkOutput, true);
    }
    saved.restore();
    tile_set_center(center, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
}

void timedWalk(Report& report, const std::filesystem::path& output, bool requireCave)
{
    const Pose saved(obj_dude);
    const int center = tile_center_tile;
    int destination = -1, pathLength = 0;
    for (int distance = 8; distance >= 4 && destination < 0; --distance) {
        for (int direction = 0; direction < 6; ++direction) {
            const int target = tile_num_in_direction(saved.tile, direction, distance);
            if (!hexGridTileIsValid(target) || obj_blocking_at(obj_dude, target, saved.elevation)) continue;
            unsigned char path[2000] = {};
            const int length = make_path(obj_dude, saved.tile, target, path, 1);
            if (length >= 4 && length <= 12) { destination = target; pathLength = length; break; }
        }
    }
    report.check(destination >= 0, "timed walk has a real multi-hex path");
    if (destination < 0) return;
    setPose(ANIM_STAND, saved.rotation, 0);
    hdPlayerSetEnabled(true); hdWorldSetEnabled(true); tile_refresh_display();
    report.check(compute_tpf(obj_dude, art_id(OBJ_TYPE_CRITTER, 11, ANIM_WALK, 0, 1)) == 100,
        "CE walk timing remains original 100 ms per frame");
    register_clear(obj_dude);
    const int begin = register_begin(ANIMATION_REQUEST_UNRESERVED);
    const int queued = begin == 0 ? register_object_move_to_tile(obj_dude, destination, saved.elevation, -1, 0) : -1;
    const int committed = queued == 0 ? register_end() : -1;
    report.check(begin == 0 && queued == 0 && committed == 0, "original CE animation queue accepts walk path");
    std::ofstream samples(output / "timed-walk.tsv");
    samples << "elapsed_ms\ttile\tx\ty\trotation\tframe\tanimation\tplayer_pixels\n";
    const uint32_t start = SDL_GetTicks();
    std::set<int> frames, tiles;
    int visibleSamples = 0, sampleCount = 0, caveSamples = 0;
    int lastTile = -1, lastFrame = -1, lastFid = -1;
    while (committed == 0 && SDL_GetTicks() - start < 12000) {
        SDL_Delay(10);
        object_animate(); // The real CE scheduler, not manual frame stepping.
        if (obj_dude->tile != lastTile || obj_dude->frame != lastFrame || obj_dude->fid != lastFid) {
            const auto frame = capture(); // Keep partial redraw path; do not force a refresh here.
            const int visible = hdWorldVisiblePixels(kPlayerOwner);
            if (FID_ANIM_TYPE(obj_dude->fid) == ANIM_WALK) {
                frames.insert(obj_dude->frame); tiles.insert(obj_dude->tile);
                if (frame.valid && visible > 0) ++visibleSamples;
                if (requireCave) {
                    const auto foreground = owners();
                    if (std::any_of(foreground.begin(), foreground.end(), [](unsigned int owner) {
                        return !hdWorldOwnerIsOpaque(owner) && hdWorldCaveBackgroundHasAsset(owner, kPlayerOwner, kPlayerOwner);
                    })) ++caveSamples;
                }
                if (sampleCount < 24) saveCrop(frame, output / ("timed-walk-" + std::to_string(sampleCount) + ".bmp"), obj_dude->tile);
                ++sampleCount;
            }
            samples << (SDL_GetTicks() - start) << '\t' << obj_dude->tile << '\t' << obj_dude->x << '\t' << obj_dude->y
                << '\t' << obj_dude->rotation << '\t' << obj_dude->frame << '\t' << (FID_ANIM_TYPE(obj_dude->fid)) << '\t' << visible << '\n';
            lastTile = obj_dude->tile; lastFrame = obj_dude->frame; lastFid = obj_dude->fid;
        }
        if (anim_busy(obj_dude) == 0) break;
    }
    report.check(obj_dude->tile == destination && anim_busy(obj_dude) == 0,
        "original CE timed walk reaches destination over " + std::to_string(pathLength) + " hexes");
    report.check(frames.size() >= 6 && tiles.size() >= 3 && visibleSamples >= 8,
        "timed movement visibly selects multiple real HD walk frames and tiles");
    if (requireCave) report.check(caveSamples > 0,
        "real CE timed walk exercises translucent foreground with player underneath (" + std::to_string(caveSamples) + " samples)");
    const auto incremental = capture(output / "timed-walk-ended.bmp");
    hdWorldReleaseTextures(); tile_refresh_display();
    const auto rebuilt = capture();
    report.check(incremental.valid && rebuilt.valid && incremental.pixels == rebuilt.pixels,
        "timed walk partial redraw has no trails versus uncached full redraw");
    register_clear(obj_dude);
    saved.restore();
    tile_set_center(center, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
}

void timings(Report& report, const std::filesystem::path& output)
{
    const bool playerEnabled = hdPlayerEnabled();
    int oldWidth, oldHeight;
    SDL_GetWindowSize(gSdlWindow, &oldWidth, &oldHeight);
    const Uint64 frequency = SDL_GetPerformanceFrequency();
    std::ofstream rows(output / "timings.json");
    rows << "{\"workload\":\"tile_refresh_display plus renderPresent\",\"samples_per_case\":12,"
        "\"warmup_per_case\":3,\"limit\":\"hidden SDL window CPU elapsed time, not guaranteed game FPS\",\"cases\":[\n";
    int cases = 0;
    for (const auto& dimensions : std::array<std::array<int, 2>, 2> { { { 1920, 1080 }, { 3840, 2160 } } }) {
        SDL_SetWindowSize(gSdlWindow, dimensions[0], dimensions[1]);
        SDL_PumpEvents(); handleWindowSizeChanged();
        int width, height; SDL_GetRendererOutputSize(gSdlRenderer, &width, &height);
        const bool correctSize = width == dimensions[0] && height == dimensions[1];
        report.check(correctSize, "timing SDL output " + std::to_string(dimensions[0]) + "x" + std::to_string(dimensions[1]));
        if (!correctSize || frequency == 0) continue;
        for (bool player : { false, true }) {
            hdPlayerSetEnabled(player);
            std::vector<double> samples;
            for (int sample = 0; sample < 15; ++sample) {
                SDL_PumpEvents();
                const Uint64 start = SDL_GetPerformanceCounter();
                tile_refresh_display(); renderPresent();
                const Uint64 end = SDL_GetPerformanceCounter();
                if (sample >= 3) samples.push_back(static_cast<double>(end - start) * 1000.0 / frequency);
            }
            std::sort(samples.begin(), samples.end());
            const double median = (samples[5] + samples[6]) * .5;
            if (cases++) rows << ",\n";
            rows << "{\"width\":" << width << ",\"height\":" << height << ",\"player_hd\":" << (player ? "true" : "false")
                << ",\"median_ms\":" << median << ",\"min_ms\":" << samples.front() << ",\"max_ms\":" << samples.back() << ",\"samples_ms\":[";
            for (size_t i = 0; i < samples.size(); ++i) rows << (i ? "," : "") << samples[i];
            rows << "]}";
            report.check(samples.size() == 12 && median > 0, "timing samples complete " + std::to_string(width) + "x"
                + std::to_string(height) + (player ? " player-on" : " player-off"));
        }
    }
    rows << "\n]}\n";
    report.check(cases == 4, "all four resolution/player timing cases recorded");
    hdPlayerSetEnabled(playerEnabled);
    SDL_SetWindowSize(gSdlWindow, oldWidth, oldHeight);
    SDL_PumpEvents(); handleWindowSizeChanged(); tile_refresh_display();
}

} // namespace

static void checkDoorSkeleton(Report& report, const std::filesystem::path& output)
{
    const char* expectedText = SDL_getenv("FALLOUT_HD_SKELETON_EXPECT");
    if (!expectedText) return;
    const bool expected = std::atoi(expectedText) != 0;
    report.check(hdWorldSkeletonLoaded() == expected, "skeleton package expected valid/absent state");
    Object* bones = nullptr;
    for (auto* object : allObjects()) if (object->pid == 211 && object->fid == 113 && object->tile == 17488) bones = object;
    report.check(bones && bones->elevation == 0 && (bones->flags & OBJECT_FLAT), "original flat skeleton container beside door found");
    if (!bones) return;
    const Object originalBones = *bones;
    std::vector<std::pair<Object*, int>> inventory;
    for (int i = 0; i < bones->data.inventory.length; ++i)
        inventory.emplace_back(bones->data.inventory.items[i].item, bones->data.inventory.items[i].quantity);
    report.check(inventory.size() == 2, "original skeleton has two inventory entries");
    const auto originalBlockers = blockers();
    hdWorldSetSkeletonEnabled(false);
    const auto off = refreshCapture(true, output / "skeleton-original-cave.bmp");
    hdWorldSetSkeletonEnabled(true);
    const auto on = refreshCapture(true, output / "skeleton-hd-cave.bmp");
    report.check(off.valid && on.valid && on.restored, "skeleton actual SDL captures restore renderer state");
    size_t changed = 0, outside = 0;
    if (off.valid && on.valid) for (int y = 0; y < on.height; ++y) for (int x = 0; x < on.width; ++x) {
        const size_t at = static_cast<size_t>(y) * on.width + x;
        if (on.pixels[at] == off.pixels[at]) continue;
        ++changed;
        const int lx = x * screenGetWidth() / on.width, ly = y * screenGetHeight() / on.height;
        if (lx < bones->sx || lx >= bones->sx + 67 || ly < bones->sy || ly >= bones->sy + 41) ++outside;
    }
    report.check(expected ? changed > 100 && outside == 0 && hdWorldVisiblePixels(250) > 0
                          : changed == 0 && hdWorldVisiblePixels(250) == 0,
        "skeleton change confined to original67x41 frame, or exact classic fallback");
    report.check(sameHud(off, on), "skeleton leaves HUD unchanged");
    report.check(refreshCapture(true).pixels == on.pixels, "skeleton repeated refresh does not accumulate alpha");
    if (expected) {
        Rect partial {bones->sx + 5, bones->sy + 3, bones->sx + 55, bones->sy + 34};
        tile_refresh_rect(&partial, map_elevation);
        report.check(capture().pixels == on.pixels, "skeleton clipped partial draw matches full frame");
        const Pose before(obj_dude);
        Rect dirty;
        const int moved = obj_move_to_tile(obj_dude, bones->tile, bones->elevation, &dirty);
        const auto overlap = refreshCapture(true, output / "skeleton-player-overlap.bmp");
        report.check(moved == 0 && overlap.valid && hdWorldVisiblePixels(249) > 0 && hdWorldVisiblePixels(250) > 0,
            "player and flat skeleton layers coexist on same tile");
        hdWorldReleaseTextures();
        report.check(capture().pixels == overlap.pixels, "player over skeleton survives texture recreation");
        tile_refresh_display();
        report.check(capture().pixels == overlap.pixels, "player over skeleton repeated full draw is identical");
        before.restore();
        report.check(refreshCapture(true).pixels == on.pixels, "moving player away restores exact skeleton and floor");
        const auto large = capture(output / "skeleton-hd-cave-4k.bmp", 3840, 2160);
        report.check(large.valid && large.restored, "skeleton real4K capture succeeds");
        tile_refresh_display();
    }
    hdWorldSetSkeletonEnabled(false);
    report.check(refreshCapture(true).pixels == off.pixels, "skeleton disable restores exact previous cave frame");
    hdWorldSetSkeletonEnabled(true); refreshCapture(true);
    bool sameInventory = bones->data.inventory.length == static_cast<int>(inventory.size())
        && bones->data.inventory.items == originalBones.data.inventory.items;
    for (int i = 0; sameInventory && i < bones->data.inventory.length; ++i)
        sameInventory = inventory[i] == std::make_pair(bones->data.inventory.items[i].item, bones->data.inventory.items[i].quantity);
    report.check(sameInventory && bones->id == originalBones.id && bones->pid == originalBones.pid
        && bones->fid == originalBones.fid && bones->tile == originalBones.tile && bones->flags == originalBones.flags
        && bones->frame == originalBones.frame && bones->rotation == originalBones.rotation
        && bones->x == originalBones.x && bones->y == originalBones.y && bones->sid == originalBones.sid,
        "skeleton original object, flags, placement, script and container inventory unchanged");
    report.check(blockers() == originalBlockers, "skeleton preserves all40000 cave collision cells");
}

#include "game/hd_player_shadow_test.inc"

int hdPlayerPreview(const char* directory)
{
    const std::filesystem::path output(directory);
    std::filesystem::create_directories(output);
    Report report(output);
    if (!report.text) return 40;
    map_disable_bk_processes(); scr_disable(); cycle_disable(); gmouse_disable_scrolling(); mouse_hide();
    report.check(obj_dude && obj_dude->elevation == 0 && std::strcmp(map_data.name, "V13ENT.MAP") == 0,
        "real V13ENT cave and premade player loaded");
    if (report.failed) return 41;
    hdPlayerInit();
    const Pose original(obj_dude);
    const int originalCenter = tile_center_tile;
    const bool oldWorld = hdWorldEnabled(), oldPlayer = hdPlayerEnabled();
    const int oldGender = stat_get_base(obj_dude, STAT_GENDER);
    const int oldAmbient = light_get_ambient();
    const auto originalBlockers = blockers();
    const int originalHp = obj_dude->data.critter.hp, originalAp = obj_dude->data.critter.combat.ap;
    auto* originalInventory = obj_dude->data.inventory.items;
    const int originalInventoryCount = obj_dude->data.inventory.length;
    int expected = 54;
    if (const char* value = SDL_getenv("FALLOUT_HD_PLAYER_EXPECT_COUNT")) expected = std::atoi(value);
    report.check(expected >= 0 && expected <= 54 && hdPlayerLoadedFrameCount() == expected,
        "player package expected decoded frame count " + std::to_string(expected));
    int expectedShadows = expected;
    if (const char* value = SDL_getenv("FALLOUT_HD_PLAYER_EXPECT_SHADOWS")) expectedShadows = std::atoi(value);
    int shadowCount = 0;
    for (int i = 0; i < hdPlayerLoadedFrameCount(); ++i)
        if (hdPlayerFrameAt(i)->poseShadowLoaded) ++shadowCount;
    report.check(shadowCount == expectedShadows, "bounded original-pose shadow masks loaded " + std::to_string(shadowCount));
    std::set<uint64_t> shadowHashes;
    for (int i = 0; i < hdPlayerLoadedFrameCount(); ++i) {
        const auto* frame = hdPlayerFrameAt(i);
        if (!frame->poseShadowLoaded || frame->animation != ANIM_WALK) continue;
        uint64_t hash = 1469598103934665603ULL;
        for (unsigned char value : frame->shadow) { hash ^= value; hash *= 1099511628211ULL; }
        shadowHashes.insert(hash);
    }
    report.check(expectedShadows < 54 || shadowHashes.size() == 48,
        "all 48 walking poses have distinct original-derived ground shadows");
    stat_set_base(obj_dude, STAT_GENDER, 0);
    obj_dude->flags &= ~(OBJECT_HIDDEN | OBJECT_FLAT | OBJECT_FLAG_0xFC000);
    obj_dude->outline = 0;
    hdWorldSetEnabled(true); hdPlayerSetEnabled(true);
    report.check(setPose(ANIM_STAND, 2, 0), "source male jumpsuit stand exists");
    const auto baseline = refreshCapture(false, output / "player-classic-cave-hd.bmp");
    const auto initial = refreshCapture(true, output / "player-hd-cave-hd.bmp");
    if (expected == 54) {
        int samples = 0;
        const int mismatches = hdWorldPlayerCaveSamplingMismatches(&samples);
        report.check(samples > 1000000 && mismatches == 0,
            "all player poses preserve body and floor shadow through cave background sampling ("
            + std::to_string(samples) + " samples, " + std::to_string(mismatches) + " mismatches)");
    }
    report.check(baseline.valid && initial.valid && initial.restored, "native SDL actor captures preserve renderer state");
    report.check(hdPlayerFrameAvailable(ANIM_STAND, 2, 0) ? baseline.pixels != initial.pixels : baseline.pixels == initial.pixels,
        "standing sprite changes only when its HD frame is available");
    report.check(sameHud(baseline, initial), "actor layer leaves entire HUD unchanged");
    checkDoorSkeleton(report, output);

    std::ofstream coverage(output / "pose-coverage.tsv");
    coverage << "animation\tdirection\tframe\tavailable\tvisible_pixels\trender_hash\n";
    std::set<uint64_t> walkingHashes;
    for (int direction = 0; direction < 6; ++direction) {
        for (int animation = 0; animation <= 1; ++animation) {
            const int count = animation == ANIM_STAND ? 1 : 8;
            for (int frame = 0; frame < count; ++frame) {
                const std::string label = (animation == ANIM_STAND ? "stand" : "walk") + std::string(" d")
                    + std::to_string(direction) + " f" + std::to_string(frame);
                const bool posed = setPose(animation, direction, frame);
                const bool available = hdPlayerFrameAvailable(animation, direction, frame);
                report.check(posed && (expected != 54 || available), label + " original pose and expected HD frame");
                const auto classicActor = refreshCapture(false);
                const auto hdActor = refreshCapture(true);
                const int visible = hdWorldVisiblePixels(kPlayerOwner);
                report.check(hdActor.valid && classicActor.valid && hdActor.restored
                    && (available ? (visible > 0 && hdActor.pixels != classicActor.pixels)
                                  : (visible == 0 && hdActor.pixels == classicActor.pixels)),
                    label + " actual render selection or missing-frame fallback");
                char name[64]; std::snprintf(name, sizeof(name), "%s-d%d-f%03d.bmp", animation == ANIM_STAND ? "stand" : "walk", direction, frame);
                report.check(saveCrop(hdActor, output / name, obj_dude->tile), label + " actual cave crop saved");
                if (available) checkPlayerShadow(report, output, label, name);
                const uint64_t hash = pixelHash(hdActor);
                if (animation == ANIM_WALK && available) walkingHashes.insert(hash);
                coverage << animation << '\t' << direction << '\t' << frame << '\t' << available << '\t' << visible << '\t' << hash << '\n';
            }
        }
    }
    report.check(expected != 54 || walkingHashes.size() == 48, "all 48 walk selections produce distinct rendered cave frames");
    report.check(!hdPlayerFrameAvailable(ANIM_WALK, 0, 8) && !hdPlayerFrameAvailable(ANIM_RUNNING, 0, 0)
        && !hdPlayerFrameAvailable(ANIM_WALK, -1, 0) && !hdPlayerFrameAvailable(ANIM_WALK, 6, 0),
        "unsupported action frame and direction keys are rejected");

    if (expected == 54) {
        checkShadowApron(report, output);
        setPose(ANIM_STAND, 2, 0);
        const auto still = refreshCapture(true);
        report.check(setPose(ANIM_STAND, 2, 11), "last original idle frame exists");
        const auto lastIdle = refreshCapture(true);
        report.check(hdPlayerFrameAvailable(ANIM_STAND, 2, 11) && hdWorldVisiblePixels(kPlayerOwner) > 0,
            "static directional idle wildcard covers original idle frame 11");
        report.check(still.valid && lastIdle.valid && still.pixels == lastIdle.pixels,
            "static idle wildcard frame 0 to 11 preserves exact visible pose without original frame remnants");
        Object copy = *obj_dude;
        report.check(!hdPlayerEligible(&copy), "same male FID on another Object is not eligible");
        checkFallback(report, output, "female", ANIM_STAND, 2, 0, 4);
        checkFallback(report, output, "leather-armour", ANIM_STAND, 2, 0, 12);
        checkFallback(report, output, "running", ANIM_RUNNING, 2, 0);
        checkFallback(report, output, "punch", ANIM_THROW_PUNCH, 2, 0);
        checkFallback(report, output, "armed", ANIM_STAND, 2, 0, 11, 1);
        setPose(ANIM_STAND, 2, 0);
        stat_set_base(obj_dude, STAT_GENDER, 1);
        const auto genderOff = refreshCapture(false), genderOn = refreshCapture(true);
        report.check(!hdPlayerEligible(obj_dude) && genderOff.valid && genderOn.valid && genderOff.pixels == genderOn.pixels,
            "female player stat rejects male replacement even with stale male FID");
        stat_set_base(obj_dude, STAT_GENDER, 0);
        for (int direction : { 0, 3 }) {
            setPose(ANIM_STAND, direction, 11);
            refreshCapture(true);
            Rect dirty;
            const int outlined = obj_outline_object(obj_dude, OUTLINE_TYPE_FRIENDLY, &dirty);
            if (outlined == 0) tile_refresh_rect(&dirty, obj_dude->elevation);
            const auto incrementalOutline = capture();
            tile_refresh_display();
            const auto fullOutline = capture();
            report.check(outlined == 0 && !hdPlayerEligible(obj_dude) && incrementalOutline.valid && fullOutline.valid
                && incrementalOutline.pixels == fullOutline.pixels,
                "outline fallback clears previous HD bounds with ordinary dirty rectangle d" + std::to_string(direction));
            const int removed = obj_remove_outline(obj_dude, &dirty);
            if (removed == 0) tile_refresh_rect(&dirty, obj_dude->elevation);
            const auto incrementalNormal = capture();
            tile_refresh_display();
            const auto fullNormal = capture();
            report.check(removed == 0 && hdPlayerEligible(obj_dude) && incrementalNormal.valid && fullNormal.valid
                && incrementalNormal.pixels == fullNormal.pixels,
                "outline removal restores HD bounds with ordinary dirty rectangle d" + std::to_string(direction));
        }
        const int normalFlags = obj_dude->flags;
        obj_dude->flags |= OBJECT_TRANS_GLASS;
        const auto glassOff = refreshCapture(false), glassOn = refreshCapture(true);
        report.check(!hdPlayerEligible(obj_dude) && glassOff.valid && glassOn.valid && glassOff.pixels == glassOn.pixels,
            "translucent actor mode retains classic compositing");
        obj_dude->flags = normalFlags;

        setPose(ANIM_WALK, 2, 2);
        light_set_ambient(65536, true);
        const auto bright = refreshCapture(true);
        light_set_ambient(16384, true);
        const auto dark = refreshCapture(true, output / "player-low-light.bmp");
        report.check(bright.valid && dark.valid && bright.pixels != dark.pixels && hdWorldVisiblePixels(kPlayerOwner) > 0,
            "player renders in real changed map lighting");
        light_set_ambient(oldAmbient, true);
        std::array<unsigned char, 768> palette;
        std::memcpy(palette.data(), getSystemPalette(), palette.size());
        palette_set_to(black_palette);
        const auto black = capture(output / "player-black-palette.bmp");
        report.check(black.valid && std::all_of(black.pixels.begin(), black.pixels.end(), [](uint32_t p) { return (p & 0xFFFFFF) == 0; }),
            "HD player obeys full black palette fade");
        palette_set_to(palette.data());

        hdPlayerSetEnabled(true); hdWorldSetEnabled(false); tile_refresh_display();
        const auto classic = capture();
        game_handle_input(KEY_F11, false); tile_refresh_display();
        const auto toggled = capture();
        report.check(hdWorldEnabled() && toggled.valid && classic.valid && toggled.pixels != classic.pixels,
            "real F11 enables HD cave and actor");
        game_handle_input(KEY_F11, false); tile_refresh_display();
        const auto disabled = capture();
        report.check(!hdWorldEnabled() && disabled.valid && disabled.pixels == classic.pixels,
            "real F11 disables HD and restores exact classic frame");
        hdWorldSetEnabled(true); tile_refresh_display();
        const auto full4k = capture(output / "player-hd-4k.bmp", 3840, 2160);
        const auto actorOff4k = refreshCapture(false, {}, 3840, 2160);
        report.check(full4k.valid && full4k.restored && full4k.width == 3840 && full4k.height == 2160
            && actorOff4k.valid && full4k.pixels != actorOff4k.pixels && sameHud(full4k, actorOff4k),
            "real 4K SDL target shows actor detail without HUD changes");
        hdPlayerSetEnabled(true); tile_refresh_display();
        const int center = tile_center_tile;
        for (const auto& scroll : std::array<std::array<int, 2>, 4> { { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } } }) {
            tile_set_center(center, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
            SDL_Delay(35);
            const int moved = map_scroll(scroll[0], scroll[1]);
            const auto incremental = capture();
            hdWorldReleaseTextures(); tile_refresh_display();
            const auto uncached = capture();
            report.check(moved == 0 && incremental.valid && uncached.valid && incremental.pixels == uncached.pixels,
                "actor incremental scroll matches full uncached redraw " + std::to_string(scroll[0]) + "," + std::to_string(scroll[1]));
        }
        tile_set_center(center, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
        const auto beforeRecreate = capture();
        handleWindowSizeChanged(); tile_refresh_display(); win_refresh_all(&scr_size);
        const auto afterRecreate = capture();
        report.check(beforeRecreate.valid && afterRecreate.valid && beforeRecreate.pixels == afterRecreate.pixels,
            "SDL renderer recreation preserves the actor frame exactly");
        checkOcclusion(report, output);
        original.restore();
        obj_dude->flags &= ~(OBJECT_HIDDEN | OBJECT_FLAT | OBJECT_FLAG_0xFC000); obj_dude->outline = 0;
        timedWalk(report, output);
        setPose(ANIM_WALK, 2, 2);
        timings(report, output);
    }

    register_clear(obj_dude);
    original.restore();
    stat_set_base(obj_dude, STAT_GENDER, oldGender);
    light_set_ambient(oldAmbient, true);
    tile_set_center(originalCenter, TILE_SET_CENTER_REFRESH_WINDOW | TILE_SET_CENTER_FLAG_IGNORE_SCROLL_RESTRICTIONS);
    hdPlayerSetEnabled(oldPlayer); hdWorldSetEnabled(oldWorld); tile_refresh_display();
    report.check(original.equal(), "test restores original player pose and flags");
    report.check(blockers() == originalBlockers, "all 40000 current-elevation blockers remain unchanged");
    report.check(obj_dude->data.critter.hp == originalHp && obj_dude->data.critter.combat.ap == originalAp
        && obj_dude->data.inventory.items == originalInventory && obj_dude->data.inventory.length == originalInventoryCount,
        "actor HP AP and inventory remain unchanged");
    std::ofstream summary(output / "result.json");
    summary << "{\"passed\":" << report.passed << ",\"failed\":" << report.failed
        << ",\"loaded_player_frames\":" << hdPlayerLoadedFrameCount() << ",\"expected_player_frames\":" << expected
        << ",\"walk_poses_captured\":48,\"idle_directions_captured\":6,\"distinct_walk_renders\":" << walkingHashes.size()
        << ",\"timed_movement_requested\":" << (expected == 54 ? "true" : "false")
        << ",\"runtime_map\":\"V13ENT.MAP\"}\n";
    report.text << "TOTAL " << report.passed << " PASS " << report.failed << " FAIL" << std::endl;
    return report.failed == 0 && summary ? 0 : 42;
}

#include "game/hd_rat_test.inc"
} // namespace fallout

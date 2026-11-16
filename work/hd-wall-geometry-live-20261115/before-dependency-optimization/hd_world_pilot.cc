#include "game/hd_world_pilot.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "game/gconfig.h"
#include "game/hd_player.h"
#include "game/hd_hud.h"
#include "game/map.h"
#include "game/object.h"
#include "game/tile.h"
#include "plib/gnw/rect.h"
#include "plib/color/color.h"
#include "plib/gnw/svga.h"

namespace fallout {
namespace {
struct UnderPixel {
    uint32_t owner = 0;
    unsigned char light = 128;
    unsigned char index = 0;
};
struct Buffer {
    unsigned char* base;
    size_t size;
    std::vector<uint32_t> owners;
    std::vector<unsigned char> lights;
    // Meaningful only for owner249. Propagated with all screen/buffer copies.
    std::vector<uint32_t> playerUnderOwners;
    std::vector<unsigned char> playerUnderLights;
    std::vector<unsigned char> playerUnderIndices;
    // Separate lower layer: the player can stand over the flat skeleton.
    std::vector<UnderPixel> skeletonUnder;
    // The original cave has one doorcomp instance. Index its saved background
    // by native FRM texel, not viewport pixel: 13 KiB instead of a full screen.
    std::vector<UnderPixel> terminalUnder;
    uint64_t terminalUnderRevision = 0;
};
struct Asset {
    int width = 0;
    int height = 0;
    int scale = 4;
    std::vector<unsigned char> rgba;
    std::vector<unsigned char> nativeIndices;
    std::vector<unsigned char> contactShadow;
    bool floor = false;
    // Optional floor variants are appended as vertical atlas pages. Ownership
    // retains the original asset ID; the native texel selects the atlas page.
    std::array<int, 3> tileVariantPages {};
    std::string filename;
};
std::vector<Buffer> buffers;
Buffer* recentBuffer = nullptr;
constexpr int kAssetCapacity = 256;
constexpr size_t kMaximumAssetBytes = 256 * 1024 * 1024;
std::array<Asset, kAssetCapacity> assets;
std::vector<std::pair<uint64_t, int>> fidAssets;
std::array<std::array<int, 2>, kAssetCapacity> wallVariants {};
bool wallVariantsEnabled = true;
std::vector<HdWorldDecoration> decorations;
std::array<bool, 40000> decorationTiles {};
std::array<bool, kAssetCapacity> decorationAssets {};
bool decorationsEnabled = true;
bool campfireShadowEnabled = true;
constexpr int kContactShadowPadding = 6;
bool initialized = false;
bool enabled = false;
int currentAsset = 0;
bool currentTerminalSoft = false;
bool currentVaultFrame = false;
const unsigned char* currentSource = nullptr;
size_t currentSize = 0;
size_t currentTileOffset = 0;
bool tileVariantsEnabled = true;
SDL_Texture* overlay = nullptr;
int overlayWidth = 0;
int overlayHeight = 0;
std::vector<uint32_t> overlayPixels;
std::vector<uint32_t> presentedOwners;
std::vector<unsigned char> presentedLights;
std::vector<unsigned char> presentedCaveOpacity;
int overlayLogicalWidth = 0;
int overlayLogicalHeight = 0;
bool overlayNeedsUpload = false;
bool overlayScrollUpload = false;
bool paletteReady = false;
std::array<unsigned char, 228 * 6> previousPalette;
unsigned char lightColors[3][256][256];
constexpr uint32_t kPlayerOwner = 249;
constexpr uint32_t kSkeletonOwner = 250;
constexpr uint32_t kHudOwner = 251;
Asset skeletonAsset;
bool skeletonEnabled = true;
// A companion image changes only one recessed lamp on doorcomp.frm. The
// original object, FRM frame and owner remain unchanged throughout the blink.
Asset terminalLitAsset;
int terminalAssetId = 0;
int terminalBaseId = 0;
bool terminalSoftEdges = false;
uint64_t presentedTerminalUnderRevision = 0;
std::array<bool, 32 * 53> terminalLampTexels {};
bool terminalLampOn = false;
int terminalPreviewPhase = -1;
struct PlayerDraw {
    unsigned char* base = nullptr;
    int pitch = 0;
    int frame = -1;
    int light = 128;
    Rect clipped {};
    Rect art {};
} playerDraw;
PlayerDraw skeletonDraw;

bool contains(const Buffer& buffer, const unsigned char* p)
{
    uintptr_t address = reinterpret_cast<uintptr_t>(p);
    uintptr_t first = reinterpret_cast<uintptr_t>(buffer.base);
    return address >= first && address - first < buffer.size;
}

Buffer* findBuffer(const unsigned char* p)
{
    if (recentBuffer && contains(*recentBuffer, p)) return recentBuffer;
    for (auto& buffer : buffers) {
        if (contains(buffer, p)) {
            recentBuffer = &buffer;
            return &buffer;
        }
    }
    return nullptr;
}

bool refreshLightColors(const SDL_Color* palette)
{
    std::array<unsigned char, 228 * 6> snapshot;
    for (int i = 1; i <= 228; i++) {
        const int offset = (i - 1) * 6;
        for (int c = 0; c < 3; c++) snapshot[offset + c] = cmap[i * 3 + c] * 4;
        snapshot[offset + 3] = palette[i].r;
        snapshot[offset + 4] = palette[i].g;
        snapshot[offset + 5] = palette[i].b;
    }
    // Cycling colors are drawn by the original renderer and cannot invalidate this layer.
    if (paletteReady && snapshot == previousPalette) return false;
    previousPalette = snapshot;
    paletteReady = true;

    for (int c = 0; c < 3; c++) {
        int sums[256] = {};
        int counts[256] = {};
        int global[256] = {};
        for (int i = 0; i < 228; i++) {
            int base = snapshot[i * 6 + c];
            sums[base] += snapshot[i * 6 + c + 3];
            counts[base]++;
        }
        int first = 0;
        while (first < 255 && counts[first] == 0) first++;
        global[first] = (sums[first] + counts[first] / 2) / counts[first];
        std::fill_n(global, first, global[first]);
        int previous = first;
        for (int value = first + 1; value < 256; value++) {
            if (!counts[value]) continue;
            global[value] = (sums[value] + counts[value] / 2) / counts[value];
            for (int middle = previous + 1; middle < value; middle++) {
                global[middle] = ((value - middle) * global[previous]
                    + (middle - previous) * global[value] + (value - previous) / 2) / (value - previous);
            }
            previous = value;
        }
        std::fill(global + previous + 1, global + 256, global[previous]);
        for (int light = 0; light < 256; light++) {
            for (int value = 0; value < 256; value++) {
                // Apply map lighting before the shared palette fade/gamma. This preserves
                // the replacement's RGB detail without reintroducing original palette noise.
                int lit = light <= 128 ? (value * light + 64) / 128
                    : value + ((252 - value) * (light - 128) + 64) / 128;
                lightColors[c][light][value] = static_cast<unsigned char>(global[std::clamp(lit, 0, 255)]);
            }
        }
    }
    return true;
}

bool loadAsset(Asset& asset, const char* path, int width, int height, bool softAlpha = false)
{
    if (width < 1 || height < 1 || width > 1024 || height > 1024) return false;
    FILE* file = fopen(path, "rb");
    if (!file) return false;
    unsigned char magic[4];
    uint32_t header[4];
    bool valid = fread(magic, 1, 4, file) == 4
        && memcmp(magic, "F1HD", 4) == 0
        && fread(header, sizeof(uint32_t), 4, file) == 4
        && header[0] == 1 && header[1] == static_cast<uint32_t>(width * 4)
        && header[2] == static_cast<uint32_t>(height * 4) && header[3] == 4;
    if (valid) {
        std::vector<unsigned char> pixels(static_cast<size_t>(width) * height * 16 * 4);
        valid = fread(pixels.data(), 1, pixels.size(), file) == pixels.size()
            && fgetc(file) == EOF;
        // Pilot assets must retain the original binary alpha at native pixel boundaries.
        for (int y = 0; valid && !softAlpha && y < height * 4; y++) {
            for (int x = 0; x < width * 4; x++) {
                int alpha = pixels[(static_cast<size_t>(y) * width * 4 + x) * 4 + 3];
                int cellAlpha = pixels[(static_cast<size_t>(y / 4 * 4) * width * 4 + x / 4 * 4) * 4 + 3];
                if ((alpha != 0 && alpha != 255) || alpha != cellAlpha) { valid = false; break; }
            }
        }
        if (valid && softAlpha) {
            bool transparent = false, visible = false;
            for (size_t i = 3; i < pixels.size(); i += 4) {
                transparent |= pixels[i] == 0;
                visible |= pixels[i] >= 240;
            }
            valid = transparent && visible;
        }
        if (valid) {
            asset.width = width;
            asset.height = height;
            asset.rgba = std::move(pixels);
        }
    }
    fclose(file);
    return valid;
}

bool parseNumber(const std::string& token, uint32_t& value)
{
    const auto parsed = std::from_chars(token.data(), token.data() + token.size(), value);
    return parsed.ec == std::errc() && parsed.ptr == token.data() + token.size();
}

uint64_t artKey(uint32_t fid, uint32_t frame)
{
    return (static_cast<uint64_t>(fid & 0x0FFFFFFF) << 32) | frame;
}

bool safeAssetFilename(const std::string& filename)
{
    if (filename.empty() || filename.size() > 128 || filename.find("..") != std::string::npos
        || filename.size() < 6 || filename.compare(filename.size() - 5, 5, ".rgba") != 0) return false;
    return std::all_of(filename.begin(), filename.end(), [](unsigned char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
            || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
    });
}

bool loadRegistry()
{
    constexpr const char* path = "data/art/hd/world-pilot/registry.tsv";
    std::error_code error;
    bool exists = std::filesystem::exists(path, error);
    if (!exists && !error) return false;
    std::ifstream registry(path);
    if (!registry.is_open()) return true;
    size_t totalBytes = 0;
    std::string line;
    for (int lineNumber = 0; lineNumber < 4096 && std::getline(registry, line); ++lineNumber) {
        if (line.empty() || line.size() > 512 || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string idToken, fidToken, widthToken, heightToken, filename, frameToken, extra;
        if (!(fields >> idToken >> fidToken >> widthToken >> heightToken >> filename)) continue;
        uint32_t id, fid, width, height, frame = 0;
        // Five-field static registries retain their original frame-zero meaning.
        // The optional sixth field is an exact FRM frame, never an animation rate.
        if ((fields >> frameToken) && (!parseNumber(frameToken, frame) || frame > 4095)) continue;
        if (fields >> extra) continue;
        if (!parseNumber(idToken, id) || !parseNumber(fidToken, fid)
            || !parseNumber(widthToken, width) || !parseNumber(heightToken, height)
            || id == 0 || id >= kAssetCapacity || id == kPlayerOwner || id == kSkeletonOwner || width == 0 || height == 0
            || width > 1024 || height > 1024 || !safeAssetFilename(filename)) continue;
        const uint64_t key = artKey(fid, frame);
        const auto existingFid = std::find_if(fidAssets.begin(), fidAssets.end(),
            [key](const auto& entry) { return entry.first == key; });
        if (existingFid != fidAssets.end()) continue;
        Asset& asset = assets[id];
        if (asset.rgba.empty()) {
            size_t bytes = static_cast<size_t>(width) * height * 64;
            if (bytes > kMaximumAssetBytes - totalBytes) continue;
            const std::string assetPath = "data/art/hd/world-pilot/" + filename;
            const bool terminal = fid == 0x0200006E && frame == 0 && width == 32 && height == 53;
            if (!loadAsset(asset, assetPath.c_str(), static_cast<int>(width), static_cast<int>(height), terminal)) continue;
            totalBytes += bytes;
            asset.filename = filename;
        } else if (asset.width != static_cast<int>(width) || asset.height != static_cast<int>(height)
            || asset.filename != filename) {
            continue;
        }
        asset.floor |= ((fid >> 24) & 15) == 4;
        fidAssets.emplace_back(key, static_cast<int>(id));
        if (fid == 0x0200006E && frame == 0 && width == 32 && height == 53) {
            terminalBaseId = static_cast<int>(id);
            for (size_t pixel = 3; pixel < asset.rgba.size(); pixel += 4)
                terminalSoftEdges |= asset.rgba[pixel] > 0 && asset.rgba[pixel] < 255;
        }
    }
    // Existing but malformed/empty registry deliberately leaves those resources classic.
    return true;
}

void loadTerminalIndicator()
{
    const auto found = std::find_if(fidAssets.begin(), fidAssets.end(), [](const auto& entry) {
        return entry.first == artKey(0x0200006E, 0); // Original doorcomp.frm.
    });
    if (found == fidAssets.end()) return;
    const Asset& base = assets[found->second];
    if (base.width != 32 || base.height != 53) return;
    const char* overridePath = SDL_getenv("FALLOUT_HD_TERMINAL_LIT_ASSET");
    const char* path = overridePath && *overridePath ? overridePath
        : "data/art/hd/world-pilot/terminal-indicator-on.rgba";
    Asset candidate;
    if (!loadAsset(candidate, path, 32, 53, true)) return;
    std::array<bool, 32 * 53> changed {};
    int changedPixels = 0;
    for (int y = 0; y < 212; ++y) for (int x = 0; x < 128; ++x) {
        const size_t uv = (y * 128 + x) * 4;
        // Fail closed if this is an unrelated image, different silhouette or
        // an old companion paired with a newly installed base. No halo/frame flicker.
        if (candidate.rgba[uv + 3] != base.rgba[uv + 3]) return;
        if (std::memcmp(&candidate.rgba[uv], &base.rgba[uv], 3) == 0) continue;
        if (!base.rgba[uv + 3] || x < 92 || x >= 112 || y < 52 || y >= 76) return;
        changed[y / 4 * 32 + x / 4] = true;
        ++changedPixels;
    }
    if (changedPixels == 0) return;
    terminalAssetId = found->second;
    terminalLampTexels = changed;
    terminalLitAsset = std::move(candidate);
}

const std::vector<unsigned char>& worldRgba(int id)
{
    return terminalLampOn && id == terminalAssetId ? terminalLitAsset.rgba : assets[id].rgba;
}

void captureTerminalUnder(Buffer& buffer, size_t offset, size_t texel)
{
    if (texel >= 32 * 53 || (buffer.owners[offset] >> 24) == static_cast<unsigned int>(terminalBaseId)) return;
    if (buffer.terminalUnder.empty()) buffer.terminalUnder.resize(32 * 53);
    auto& old = buffer.terminalUnder[texel];
    if (old.owner != buffer.owners[offset] || old.light != buffer.lights[offset] || old.index != buffer.base[offset]) {
        old = {buffer.owners[offset], buffer.lights[offset], buffer.base[offset]};
        ++buffer.terminalUnderRevision;
    }
}

#if defined(_MSC_VER)
__declspec(noinline)
#endif
void copyTerminalUnderPixel(Buffer& target, const Buffer& origin, size_t offset)
{
    if (origin.terminalUnder.empty()) return;
    uint32_t owner = target.owners[offset];
    if ((owner >> 24) == kPlayerOwner) owner = target.playerUnderOwners[offset];
    if ((owner >> 24) == kSkeletonOwner) owner = target.skeletonUnder[offset].owner;
    if ((owner >> 24) != static_cast<unsigned int>(terminalBaseId) || (owner & 0xFFFFFF) >= 32 * 53) return;
    if (target.terminalUnder.empty()) target.terminalUnder.resize(32 * 53);
    auto& old = target.terminalUnder[owner & 0xFFFFFF];
    const auto& next = origin.terminalUnder[owner & 0xFFFFFF];
    if (old.owner != next.owner || old.light != next.light || old.index != next.index) {
        old = next;
        ++target.terminalUnderRevision;
    }
}

void loadWallVariants()
{
    std::ifstream input("data/art/hd/world-pilot/variants.tsv");
    if (!input.is_open()) return;
    size_t totalBytes = 0;
    for (const auto& asset : assets) totalBytes += asset.rgba.size();
    std::string line;
    for (int number = 0; number < 512 && std::getline(input, line); ++number) {
        if (line.empty() || line.size() > 256 || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string baseToken, slotToken, idToken, filename, extra;
        uint32_t baseId, slot, id;
        if (!(fields >> baseToken >> slotToken >> idToken >> filename) || (fields >> extra)
            || !parseNumber(baseToken, baseId) || !parseNumber(slotToken, slot) || !parseNumber(idToken, id)
            || baseId == 0 || baseId >= kAssetCapacity || id == 0 || id >= kAssetCapacity || id == kPlayerOwner || id == kSkeletonOwner
            || slot < 1 || slot > 2 || !safeAssetFilename(filename)) continue;
        const Asset& original = assets[baseId];
        if (original.rgba.empty() || !assets[id].rgba.empty() || wallVariants[baseId][slot - 1]) continue;
        // Only registered frame-zero WALL art can acquire these appearance variants.
        bool wall = std::any_of(fidAssets.begin(), fidAssets.end(), [baseId](const auto& entry) {
            return entry.second == static_cast<int>(baseId)
                && static_cast<uint32_t>(entry.first) == 0
                && ((entry.first >> 56) & 0xF) == 3;
        });
        if (!wall || original.rgba.size() > kMaximumAssetBytes - totalBytes) continue;
        Asset candidate;
        const std::string path = "data/art/hd/world-pilot/" + filename;
        if (!loadAsset(candidate, path.c_str(), original.width, original.height)) continue;
        bool matchingAlpha = true;
        for (size_t pixel = 3; pixel < original.rgba.size(); pixel += 4) {
            if (candidate.rgba[pixel] != original.rgba[pixel]) { matchingAlpha = false; break; }
        }
        if (!matchingAlpha) continue;
        candidate.filename = filename;
        assets[id] = std::move(candidate);
        wallVariants[baseId][slot - 1] = static_cast<int>(id);
        totalBytes += assets[id].rgba.size();
    }
}

void prepareCampfireShadow(Asset& asset)
{
    // Authored effect for the extinguished campfire only. Its original RGB,
    // binary alpha and registration remain untouched. One-pixel dilation and
    // a radius-three binomial blur retain the original contact fringe. A second
    // lobe extends two pixels toward the viewer, below the front silhouette only.
    const int width = asset.width + 2 * kContactShadowPadding;
    const int height = asset.height + 2 * kContactShadowPadding;
    std::vector<unsigned char> dilated(static_cast<size_t>(width) * height);
    const auto opaque = [&asset](int x, int y) {
        return x >= 0 && x < asset.width && y >= 0 && y < asset.height
            && asset.nativeIndices[static_cast<size_t>(y) * asset.width + x] != 0;
    };
    for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
        for (int dy = -1; dy <= 1; ++dy) for (int dx = -1; dx <= 1; ++dx) {
            if (opaque(x - kContactShadowPadding + dx, y - kContactShadowPadding + dy))
                dilated[static_cast<size_t>(y) * width + x] = 1;
        }
    }
    constexpr int weights[] = {1, 6, 15, 20, 15, 6, 1};
    std::vector<int> blurred(static_cast<size_t>(width) * height);
    for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
        int sum = 0;
        for (int dy = -3; dy <= 3; ++dy) for (int dx = -3; dx <= 3; ++dx) {
            const int sx = x + dx, sy = y + dy;
            if (sx >= 0 && sx < width && sy >= 0 && sy < height)
                sum += dilated[static_cast<size_t>(sy) * width + sx] * weights[dx + 3] * weights[dy + 3];
        }
        blurred[static_cast<size_t>(y) * width + x] = sum;
    }
    std::vector<int> frontEdge(width, -1);
    for (int x = 0; x < width; ++x) {
        // Conservative neighboring contour permits soft lateral falloff without
        // lifting the stronger shade above a foreground stone or log.
        for (int dx = -3; dx <= 3; ++dx) for (int y = 0; y < asset.height; ++y)
            if (opaque(x - kContactShadowPadding + dx, y)) frontEdge[x] = std::max(frontEdge[x], y);
    }
    asset.contactShadow.resize(static_cast<size_t>(width) * height);
    for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
        if (opaque(x - kContactShadowPadding, y - kContactShadowPadding)) continue;
        const size_t index = static_cast<size_t>(y) * width + x;
        int amount = (blurred[index] * 45 + 2048) / 4096;
        if (frontEdge[x] >= 0 && y - kContactShadowPadding > frontEdge[x] && y >= 2) {
            const int forward = (blurred[static_cast<size_t>(y - 2) * width + x] * 64 + 2048) / 4096;
            amount = std::max(amount, forward);
        }
        // Old upper/side shadow is unchanged; the lower lobe is capped at 50%.
        asset.contactShadow[index] = static_cast<unsigned char>(amount);
    }
}

void loadDecorations()
{
    // Do not activate an extension against an incomplete base package/fallback fixture.
    for (int id = 1; id <= 174; ++id) if (assets[id].rgba.empty()) return;
    size_t totalBytes = 0;
    for (const auto& asset : assets) totalBytes += asset.rgba.size();
    std::ifstream input("data/art/hd/world-pilot/decor.tsv");
    std::string line;
    for (int number = 0; number < 64 && std::getline(input, line); ++number) {
        if (line.empty() || line.size() > 256 || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string idToken, widthToken, heightToken, filename, extra;
        uint32_t id, width, height;
        if (!(fields >> idToken >> widthToken >> heightToken >> filename) || (fields >> extra)
            || !parseNumber(idToken, id) || !parseNumber(widthToken, width) || !parseNumber(heightToken, height)
            || id < 240 || id > 248 || width < 1 || width > 128 || height < 1 || height > 128
            || !assets[id].rgba.empty() || !safeAssetFilename(filename)) continue;
        const size_t bytes = static_cast<size_t>(width) * height * 64;
        if (bytes > kMaximumAssetBytes - totalBytes) continue;
        Asset candidate;
        const std::string path = "data/art/hd/world-pilot/" + filename;
        if (!loadAsset(candidate, path.c_str(), width, height)) continue;
        candidate.filename = filename;
        candidate.nativeIndices.resize(static_cast<size_t>(width) * height);
        for (uint32_t y = 0; y < height; ++y) for (uint32_t x = 0; x < width; ++x)
            candidate.nativeIndices[y * width + x] = candidate.rgba[(y * 4 * width * 4 + x * 4) * 4 + 3] ? 1 : 0;
        if (id == 248) prepareCampfireShadow(candidate);
        assets[id] = std::move(candidate);
        decorationAssets[id] = true;
        totalBytes += bytes;
    }
    std::ifstream placements("data/art/hd/world-pilot/decor-placements.tsv");
    for (int number = 0; number < 128 && decorations.size() < 64 && std::getline(placements, line); ++number) {
        if (line.empty() || line.size() > 256 || line[0] == '#') continue;
        std::istringstream fields(line);
        HdWorldDecoration item {};
        int flat; std::string extra;
        if (!(fields >> item.assetId >> item.tile >> item.elevation >> item.offsetX >> item.offsetY >> flat)
            || (fields >> extra) || item.assetId < 240 || item.assetId > 248 || !decorationAssets[item.assetId]
            || item.tile < 0 || item.tile >= 40000 || item.elevation != 0
            || item.offsetX < -64 || item.offsetX > 64 || item.offsetY < -64 || item.offsetY > 64
            || (flat != 0 && flat != 1)) continue;
        item.flat = flat != 0;
        const bool duplicate = std::any_of(decorations.begin(), decorations.end(), [&item](const auto& other) {
            return item.assetId == other.assetId && item.tile == other.tile;
        });
        if (duplicate) continue;
        decorations.push_back(item);
        decorationTiles[item.tile] = true;
    }
}

#include "game/hd_tile_variants.inc"

uint32_t artOwner(const unsigned char* p)
{
    if (!p) return 0;
    uintptr_t offset = reinterpret_cast<uintptr_t>(p) - reinterpret_cast<uintptr_t>(currentSource);
    if (!currentAsset || offset >= currentSize || *p == 0 || *p >= 229) return 0;
    // 24-bit native texel offset and 8-bit asset id. Large vault sprites exceed 65535 pixels.
    // Cyclic colors stay in the original renderer instead of freezing their effects.
    return (static_cast<uint32_t>(currentAsset) << 24) | static_cast<uint32_t>(offset + currentTileOffset);
}
}

#include "game/hd_cave_variety.inc"

void hdWorldInit()
{
    if (initialized) return;
    initialized = true;
    int configured = 0;
    config_get_value(&game_config, "remaster", "hd_world_pilot", &configured);
    enabled = configured != 0;
    int configuredVariants = 1;
    config_get_value(&game_config, "remaster", "hd_world_wall_variants", &configuredVariants);
    wallVariantsEnabled = configuredVariants != 0;
    int configuredDecorations = 1;
    config_get_value(&game_config, "remaster", "hd_world_decorations", &configuredDecorations);
    decorationsEnabled = configuredDecorations != 0;
    int configuredCampfireShadow = 1;
    config_get_value(&game_config, "remaster", "hd_world_campfire_shadow", &configuredCampfireShadow);
    campfireShadowEnabled = configuredCampfireShadow != 0;
    if (!loadRegistry()) {
        // Preserve the first two-resource pilot when no registry is installed.
        if (loadAsset(assets[1], "data/art/hd/world-pilot/cav1000.rgba", 80, 36)) fidAssets.emplace_back(artKey(0x04000015, 0), 1);
        if (loadAsset(assets[2], "data/art/hd/world-pilot/rock03.rgba", 123, 103)) fidAssets.emplace_back(artKey(0x020000AD, 0), 2);
    }
    loadWallVariants();
    int configuredTileVariants = 1;
    config_get_value(&game_config, "remaster", "hd_world_tile_variants", &configuredTileVariants);
    tileVariantsEnabled = configuredTileVariants != 0;
    loadTileVariants();
    loadDecorations();
    loadTerminalIndicator();
    loadCaveVariety();
    loadWallGeometry();
    // Existing capture suites compare exact frames over time. Freeze only in
    // those explicitly requested test processes; normal gameplay uses SDL time.
    for (const char* name : {"FALLOUT_HD_WORLD_PREVIEW", "FALLOUT_HD_PLAYER_PREVIEW", "FALLOUT_HD_HUD_PREVIEW"}) {
        const char* value = SDL_getenv(name);
        if (value && *value) terminalPreviewPhase = 0;
    }
    int configuredSkeleton = 1;
    config_get_value(&game_config, "remaster", "hd_v13_skeleton", &configuredSkeleton);
    skeletonEnabled = configuredSkeleton != 0;
    loadAsset(skeletonAsset, "data/art/hd/v13bones/v13bones.rgba", 67, 41, true);
}

void hdWorldRegisterBuffer(unsigned char* base, int size)
{
    if (!base || size <= 0) return;
    hdWorldUnregisterBuffer(base);
    buffers.push_back({base, static_cast<size_t>(size), std::vector<uint32_t>(size), std::vector<unsigned char>(size, 128),
        std::vector<uint32_t>(size), std::vector<unsigned char>(size, 128), std::vector<unsigned char>(size),
        std::vector<UnderPixel>(size)});
    recentBuffer = nullptr;
}

void hdWorldUnregisterBuffer(unsigned char* base)
{
    // Vector erasure/reallocation invalidates cached Buffer pointers.
    recentBuffer = nullptr;
    buffers.erase(std::remove_if(buffers.begin(), buffers.end(),
        [base](const Buffer& buffer) { return buffer.base == base; }), buffers.end());
}

bool hdWorldIsPilotMap()
{
    // The same cave is named .SAV after loading its saved map state.
    return SDL_strcasecmp(map_data.name, "V13ENT.MAP") == 0
        || SDL_strcasecmp(map_data.name, "V13ENT.SAV") == 0;
}

bool hdWorldTerminalIndicatorLoaded() { hdWorldInit(); return terminalAssetId != 0; }
bool hdWorldTerminalSoftEdges() { hdWorldInit(); return terminalSoftEdges; }
bool hdWorldTerminalLampOnAt(unsigned int milliseconds) { return milliseconds % 1600 < 500; }
void hdWorldSetTerminalPreviewPhase(int phase) { terminalPreviewPhase = std::clamp(phase, -1, 1); }

int hdWorldDecorationAssetCount()
{
    return static_cast<int>(std::count(decorationAssets.begin(), decorationAssets.end(), true));
}
int hdWorldDecorationCount() { return static_cast<int>(decorations.size()); }
bool hdWorldDecorationDimensions(int id, int* width, int* height)
{
    if (id < 240 || id > 248 || !decorationAssets[id] || !width || !height) return false;
    *width = assets[id].width;
    *height = assets[id].height;
    return true;
}
const HdWorldDecoration* hdWorldDecorationAt(int index)
{
    return index >= 0 && index < static_cast<int>(decorations.size()) ? &decorations[index] : nullptr;
}
void hdWorldSetDecorationsEnabled(bool value) { decorationsEnabled = value; }
bool hdWorldCampfireShadowEnabled() { return campfireShadowEnabled; }
void hdWorldSetCampfireShadowEnabled(bool value) { campfireShadowEnabled = value; }
bool hdWorldAssetIsFloor(int id) { return id > 0 && id < kAssetCapacity && assets[id].floor; }
int hdWorldCampfireShadowFactorAt(int x, int y, int elevation)
{
    if (!campfireShadowEnabled || !hdWorldDecorationsActive(elevation)) return 128;
    int factor = 128;
    for (const auto& item : decorations) {
        if (item.assetId != 248 || !item.flat || item.elevation != elevation) continue;
        const Asset& asset = assets[item.assetId];
        if (asset.contactShadow.empty()) continue;
        int cx, cy;
        if (tile_coord(item.tile, &cx, &cy, elevation) != 0) continue;
        const int left = cx + 16 + item.offsetX - asset.width / 2 - kContactShadowPadding;
        const int top = cy + 8 + item.offsetY - (asset.height - 1) - kContactShadowPadding;
        const int width = asset.width + 2 * kContactShadowPadding;
        const int height = asset.height + 2 * kContactShadowPadding;
        if (x >= left && x < left + width && y >= top && y < top + height)
            factor = (factor * (128 - asset.contactShadow[static_cast<size_t>(y - top) * width + x - left]) + 64) / 128;
    }
    return factor;
}
bool hdWorldDecorationsActive(int elevation)
{
    hdWorldInit();
    // Keep ownership available while F11 is off; toggling needs no world refresh.
    return decorationsEnabled && !decorations.empty() && elevation == 0 && hdWorldIsPilotMap();
}
bool hdWorldHasDecoration(int tile)
{
    return tile >= 0 && tile < 40000 && decorationTiles[tile];
}
void hdWorldDrawDecorationsAt(int tile, bool flat, unsigned char* buffer, int pitch,
    const Rect* clip, int elevation, int light)
{
    if (!buffer || !clip || pitch <= 0 || !hdWorldHasDecoration(tile)) return;
    Buffer* target = findBuffer(buffer);
    if (!target) return;
    const size_t bufferOffset = buffer - target->base;
    const int bufferHeight = static_cast<int>((target->size - bufferOffset) / pitch);
    int centerX, centerY;
    if (tile_coord(tile, &centerX, &centerY, elevation) != 0) return;
    const auto intensity = static_cast<unsigned char>(std::clamp(light >> 9, 0, 128));
    for (const auto& item : decorations) {
        if (item.tile != tile || item.elevation != elevation || item.flat != flat) continue;
        const Asset& asset = assets[item.assetId];
        const int left = centerX + 16 + item.offsetX - asset.width / 2;
        const int top = centerY + 8 + item.offsetY - (asset.height - 1);
        if (campfireShadowEnabled && item.flat && !asset.contactShadow.empty()) {
            const int shadowWidth = asset.width + 2 * kContactShadowPadding;
            const int shadowHeight = asset.height + 2 * kContactShadowPadding;
            const int shadowLeft = left - kContactShadowPadding, shadowTop = top - kContactShadowPadding;
            const int sx0 = std::max({shadowLeft, clip->ulx, 0});
            const int sy0 = std::max({shadowTop, clip->uly, 0});
            const int sx1 = std::min({shadowLeft + shadowWidth - 1, clip->lrx, pitch - 1});
            const int sy1 = std::min({shadowTop + shadowHeight - 1, clip->lry, bufferHeight - 1});
            for (int y = sy0; y <= sy1; ++y) for (int x = sx0; x <= sx1; ++x) {
                const int amount = asset.contactShadow[static_cast<size_t>(y - shadowTop) * shadowWidth + x - shadowLeft];
                if (!amount) continue;
                const size_t offset = bufferOffset + static_cast<size_t>(y) * pitch + x;
                const int ownerId = target->owners[offset] >> 24;
                // Preserve all other sprites and skip affine overbright light:
                // no classic shadow was written to support its fallback path.
                if (!ownerId || !assets[ownerId].floor || target->lights[offset] > 128) continue;
                target->lights[offset] = static_cast<unsigned char>((target->lights[offset] * (128 - amount) + 64) / 128);
            }
        }
        const int x0 = std::max({left, clip->ulx, 0});
        const int y0 = std::max({top, clip->uly, 0});
        const int x1 = std::min({left + asset.width - 1, clip->lrx, pitch - 1});
        const int y1 = std::min({top + asset.height - 1, clip->lry, bufferHeight - 1});
        for (int y = y0; y <= y1; ++y) for (int x = x0; x <= x1; ++x) {
            const size_t texel = static_cast<size_t>(y - top) * asset.width + x - left;
            if (!asset.nativeIndices[texel]) continue;
            const size_t offset = bufferOffset + static_cast<size_t>(y) * pitch + x;
            target->owners[offset] = (static_cast<uint32_t>(item.assetId) << 24) | static_cast<uint32_t>(texel);
            target->lights[offset] = intensity;
            // The classic framebuffer is deliberately untouched.
        }
    }
}

int hdWorldResolveAsset(int fid, int frame, int tile, int elevation)
{
    hdWorldInit();
    if (!hdWorldIsPilotMap() || frame < 0 || frame > 4095) return 0;
    const uint64_t key = artKey(static_cast<uint32_t>(fid), static_cast<uint32_t>(frame));
    const auto mapping = std::find_if(fidAssets.begin(), fidAssets.end(),
        [key](const auto& entry) { return entry.first == key; });
    if (mapping == fidAssets.end()) return 0;
    int id = mapping->second;
    if (!wallVariantsEnabled || frame != 0 || ((fid >> 24) & 0xF) != 3
        || tile < 0 || tile >= 40000 || elevation < 0 || elevation > 2
        || (wallVariants[id][0] == 0 && wallVariants[id][1] == 0)) return id;
    // No RNG, object mutation, camera coordinates or save-format dependence.
    // Missing slots keep their original choice and fall back to the base image.
    uint32_t hash = static_cast<uint32_t>(tile) * 0x9E3779B9U
        ^ (static_cast<uint32_t>(fid) & 0x0FFFFFFFU) * 0x85EBCA6BU
        ^ static_cast<uint32_t>(elevation) * 0xC2B2AE35U;
    hash ^= hash >> 16;
    hash *= 0x7FEB352DU;
    hash ^= hash >> 15;
    hash *= 0x846CA68BU;
    hash ^= hash >> 16;
    int choice = static_cast<int>(hash % 3);
    return choice && wallVariants[id][choice - 1] ? wallVariants[id][choice - 1] : id;
}

int hdWorldWallVariantCount()
{
    int count = 0;
    for (const auto& slots : wallVariants) for (int id : slots) if (id) ++count;
    return count;
}

bool hdWorldWallVariantsEnabled() { return wallVariantsEnabled; }

void hdWorldSetWallVariantsEnabled(bool value) { wallVariantsEnabled = value; }

bool hdWorldTileVariantsEnabled() { hdWorldInit(); return tileVariantsEnabled; }
void hdWorldSetTileVariantsEnabled(bool value) { tileVariantsEnabled = value; }
int hdWorldTileVariantCount()
{
    hdWorldInit();
    int count = 0;
    for (const auto& asset : assets) for (int page : asset.tileVariantPages) if (page) ++count;
    return count;
}
int hdWorldResolveTileVariant(int fid, int squareTile, int elevation)
{
    const int id = hdWorldResolveAsset(fid);
    if (!id || !tileVariantsEnabled || ((fid >> 24) & 15) != 4
        || squareTile < 0 || squareTile >= 10000 || elevation < 0 || elevation > 2) return 0;
    uint32_t hash = static_cast<uint32_t>(squareTile) * 0x9E3779B9U
        ^ static_cast<uint32_t>(fid) * 0x85EBCA6BU ^ static_cast<uint32_t>(elevation) * 0xC2B2AE35U;
    hash ^= hash >> 16; hash *= 0x7FEB352DU;
    hash ^= hash >> 15; hash *= 0x846CA68BU; hash ^= hash >> 16;
    const int choice = hash % 4;
    return choice && assets[id].tileVariantPages[choice - 1] ? choice : 0;
}

void hdWorldBeginArt(int fid, const unsigned char* base, int width, int height, int frame, int tile, int elevation)
{
    hdWorldEndArt();
    const int id = hdWorldResolveAsset(fid, frame, tile, elevation);
    if (!id) return;
    Asset& asset = assets[id];
    if (!base || asset.rgba.empty() || width != asset.width || height != asset.height) return;
    if (asset.nativeIndices.empty()) {
        // Keep source palette indices independent of HD density and of art-cache lifetime.
        const size_t pageSize = static_cast<size_t>(width) * height;
        const size_t pages = asset.floor ? asset.rgba.size() / (pageSize * 64) : 1;
        asset.nativeIndices.reserve(pageSize * pages);
        for (size_t page = 0; page < pages; ++page)
            asset.nativeIndices.insert(asset.nativeIndices.end(), base, base + pageSize);
    }
    currentAsset = id;
    currentTerminalSoft = terminalSoftEdges && id == terminalBaseId;
    currentVaultFrame = (fid & 0x0FFFFFFF) == 0x0200011A && frame == 0
        && width == 342 && height == 224;
    currentSource = base;
    currentSize = static_cast<size_t>(width) * height;
    const int slot = frame == 0 ? hdWorldResolveTileVariant(fid, tile, elevation) : 0;
    currentTileOffset = slot ? currentSize * asset.tileVariantPages[slot - 1] : 0;
}

void hdWorldEndArt()
{
    currentAsset = 0;
    currentTerminalSoft = false;
    currentVaultFrame = false;
    currentSource = nullptr;
    currentSize = 0;
    currentTileOffset = 0;
}

void hdWorldFillVaultTerminalRecess(unsigned char* base, int pitch, const Rect* art, const Rect* clip, int light)
{
    if (!currentVaultFrame || !base || pitch <= 0 || !art || !clip) return;
    Buffer* target = findBuffer(base);
    if (!target) return;
    const auto& asset = assets[currentAsset];
    const size_t start = base - target->base;
    const int height = static_cast<int>((target->size - start) / pitch);
    // Only the original missing panel behind doorcomp, never the main door
    // opening. An old/unpatched asset has zero alpha here and remains a no-op.
    const int x0 = std::max({art->ulx + 73, clip->ulx, 0});
    const int y0 = std::max({art->uly + 157, clip->uly, 0});
    const int x1 = std::min({art->ulx + 105, clip->lrx, pitch - 1});
    const int y1 = std::min({art->uly + 209, clip->lry, height - 1});
    for (int y = y0; y <= y1; ++y) for (int x = x0; x <= x1; ++x) {
        const size_t texel = (y - art->uly) * 342 + x - art->ulx;
        const size_t uv = ((texel / 342 * 4) * 1368 + texel % 342 * 4) * 4;
        if (texel >= currentSize || currentSource[texel] || asset.rgba[uv + 3] != 255) continue;
        const size_t offset = start + static_cast<size_t>(y) * pitch + x;
        target->owners[offset] = (static_cast<uint32_t>(currentAsset) << 24) | static_cast<uint32_t>(texel);
        target->lights[offset] = static_cast<unsigned char>(std::clamp(light >> 9, 0, 255));
        // Do not touch the classic framebuffer, object, mask, or collision.
        // Later objects and windows retain their ordinary occlusion order.
    }
}

void hdWorldCaptureTerminalBackground(unsigned char* base, int pitch, const Rect* art, const Rect* clip)
{
    if (!currentTerminalSoft || !base || pitch <= 0 || !art || !clip) return;
    Buffer* target = findBuffer(base);
    if (!target) return;
    const size_t start = base - target->base;
    const int height = static_cast<int>((target->size - start) / pitch);
    const int x0 = std::max({art->ulx, clip->ulx, 0});
    const int y0 = std::max({art->uly, clip->uly, 0});
    const int x1 = std::min({art->lrx, clip->lrx, pitch - 1});
    const int y1 = std::min({art->lry, clip->lry, height - 1});
    for (int y = y0; y <= y1; ++y) for (int x = x0; x <= x1; ++x) {
        const size_t texel = (y - art->uly) * 32 + x - art->ulx;
        if (texel < currentSize && currentSource[texel])
            captureTerminalUnder(*target, start + static_cast<size_t>(y) * pitch + x, texel);
    }
}

bool hdWorldSkeletonLoaded() { hdWorldInit(); return !skeletonAsset.rgba.empty(); }
void hdWorldSetSkeletonEnabled(bool state) { hdWorldInit(); skeletonEnabled = state; }

bool hdWorldBeginSkeleton(const Object* object, unsigned char* base, int pitch,
    const Rect* artRect, const Rect* clip, int light)
{
    skeletonDraw.base = nullptr;
    // This is the original flat container. No object, inventory, or FRM is changed.
    if (!hdWorldSkeletonLoaded() || !skeletonEnabled || !hdWorldIsPilotMap() || !object
        || object->fid != 113 || object->pid != 211 || object->frame != 0
        || object->tile < 0 || object->tile >= 40000 || object->elevation != map_elevation
        || !(object->flags & OBJECT_FLAT) || (object->flags & (OBJECT_HIDDEN | (OBJECT_FLAG_0xFC000 & ~OBJECT_TRANS_NONE)))
        || ((object->outline & OUTLINE_TYPE_MASK) && !(object->outline & OUTLINE_DISABLED))
        || !base || pitch <= 0 || !artRect || !clip
        || artRect->lrx - artRect->ulx + 1 != 67 || artRect->lry - artRect->uly + 1 != 41) return false;
    Buffer* target = findBuffer(base);
    if (!target) return false;
    const size_t start = base - target->base;
    const int height = static_cast<int>((target->size - start) / pitch);
    Rect area {std::max({artRect->ulx, clip->ulx, 0}), std::max({artRect->uly, clip->uly, 0}),
        std::min({artRect->lrx, clip->lrx, pitch - 1}), std::min({artRect->lry, clip->lry, height - 1})};
    if (area.ulx > area.lrx || area.uly > area.lry) return false;
    for (int y = area.uly; y <= area.lry; ++y) for (int x = area.ulx; x <= area.lrx; ++x) {
        const size_t at = start + static_cast<size_t>(y) * pitch + x;
        if ((target->owners[at] >> 24) == kSkeletonOwner) continue;
        target->skeletonUnder[at] = {target->owners[at], target->lights[at], target->base[at]};
    }
    skeletonDraw = {base, pitch, 0, std::clamp(light >> 9, 0, 128), area, *artRect};
    return true;
}

void hdWorldEndSkeleton()
{
    if (!skeletonDraw.base) return;
    Buffer* target = findBuffer(skeletonDraw.base);
    if (target) {
        const size_t start = skeletonDraw.base - target->base;
        for (int y = skeletonDraw.clipped.uly; y <= skeletonDraw.clipped.lry; ++y)
            for (int x = skeletonDraw.clipped.ulx; x <= skeletonDraw.clipped.lrx; ++x) {
                const size_t at = start + static_cast<size_t>(y) * skeletonDraw.pitch + x;
                target->owners[at] = (kSkeletonOwner << 24)
                    | static_cast<uint32_t>((y - skeletonDraw.art.uly) * 67 + x - skeletonDraw.art.ulx);
                target->lights[at] = static_cast<unsigned char>(skeletonDraw.light);
            }
    }
    skeletonDraw.base = nullptr;
}

bool hdWorldBeginPlayer(int frameIndex, unsigned char* base, int pitch,
    const Rect* classicRect, const Rect* hdRect, const Rect* clip, int light)
{
    playerDraw.base = nullptr;
    if (!hdWorldIsPilotMap() || !hdPlayerEnabled() || !base || pitch <= 0
        || !classicRect || !hdRect || !clip || !hdPlayerFrameAt(frameIndex)) return false;
    Buffer* target = findBuffer(base);
    if (!target) return false;
    const size_t start = base - target->base;
    const int height = static_cast<int>((target->size - start) / pitch);
    Rect area {
        std::max({std::min(classicRect->ulx, hdRect->ulx), clip->ulx, 0}),
        std::max({std::min(classicRect->uly, hdRect->uly), clip->uly, 0}),
        std::min({std::max(classicRect->lrx, hdRect->lrx), clip->lrx, pitch - 1}),
        std::min({std::max(classicRect->lry, hdRect->lry), clip->lry, height - 1}) };
    if (area.ulx > area.lrx || area.uly > area.lry) return false;
    for (int y = area.uly; y <= area.lry; y++) for (int x = area.ulx; x <= area.lrx; x++) {
        const size_t at = start + static_cast<size_t>(y) * pitch + x;
        // Repeated partial draws must never capture a player over itself.
        if ((target->owners[at] >> 24) == kPlayerOwner) continue;
        target->playerUnderOwners[at] = target->owners[at];
        target->playerUnderLights[at] = target->lights[at];
        target->playerUnderIndices[at] = target->base[at];
    }
    playerDraw = {base, pitch, frameIndex, std::clamp(light >> 9, 0, 128), area, *hdRect};
    return true;
}

void hdWorldEndPlayer()
{
    if (!playerDraw.base) return;
    Buffer* target = findBuffer(playerDraw.base);
    const HdPlayerFrame* frame = hdPlayerFrameAt(playerDraw.frame);
    if (target && frame) {
        const size_t start = playerDraw.base - target->base;
        for (int y = playerDraw.clipped.uly; y <= playerDraw.clipped.lry; y++) {
            for (int x = playerDraw.clipped.ulx; x <= playerDraw.clipped.lrx; x++) {
                const int u = x - playerDraw.art.ulx, v = y - playerDraw.art.uly;
                const uint32_t texel = u >= 0 && v >= 0 && u < frame->width && v < frame->height
                    ? static_cast<uint32_t>(v * frame->width + u) : 0xFFFF;
                const size_t at = start + static_cast<size_t>(y) * playerDraw.pitch + x;
                target->owners[at] = (kPlayerOwner << 24) | (static_cast<uint32_t>(playerDraw.frame) << 16) | texel;
                target->lights[at] = static_cast<unsigned char>(playerDraw.light);
            }
        }
    }
    playerDraw.base = nullptr;
}

void hdWorldWrite(unsigned char* dest, const unsigned char* source, int light)
{
    auto* target = findBuffer(dest);
    if (!target) return;
    size_t offset = dest - target->base;
    // Art writes dominate this path. Check their known span before scanning buffers.
    uintptr_t artOffset = reinterpret_cast<uintptr_t>(source) - reinterpret_cast<uintptr_t>(currentSource);
    if (currentAsset && artOffset < currentSize) {
        target->owners[offset] = artOwner(source);
        target->lights[offset] = static_cast<unsigned char>(std::clamp(light, 0, 255));
    } else if (source) {
        auto* origin = findBuffer(source);
        target->owners[offset] = origin ? origin->owners[source - origin->base] : 0;
        target->lights[offset] = origin ? origin->lights[source - origin->base] : 128;
        if (origin && ((target->owners[offset] >> 24) == kPlayerOwner || (target->owners[offset] >> 24) == kSkeletonOwner || (target->owners[offset] >> 24) == kHudOwner || (target->owners[offset] >> 24) == static_cast<unsigned int>(terminalBaseId))) {
            const size_t from = source - origin->base;
            target->playerUnderOwners[offset] = origin->playerUnderOwners[from];
            target->playerUnderLights[offset] = origin->playerUnderLights[from];
            target->playerUnderIndices[offset] = origin->playerUnderIndices[from];
            target->skeletonUnder[offset] = origin->skeletonUnder[from];
            copyTerminalUnderPixel(*target, *origin, offset);
        }
    } else {
        target->owners[offset] = 0;
        target->lights[offset] = 128;
    }
}

void hdWorldShade(unsigned char* dest, int light)
{
    auto* target = findBuffer(dest);
    if (!target) return;
    size_t offset = dest - target->base;
    if (!target->owners[offset]) return;
    int factor = std::clamp(light, 0, 128);
    if (factor == 128) return;
    if (!target->terminalUnder.empty() && ((target->owners[offset] >> 24) == static_cast<unsigned int>(terminalBaseId)
        || ((target->owners[offset] >> 24) == kPlayerOwner && (target->playerUnderOwners[offset] >> 24) == static_cast<unsigned int>(terminalBaseId)))) {
        const uint32_t owner = (target->owners[offset] >> 24) == kPlayerOwner
            ? target->playerUnderOwners[offset] : target->owners[offset];
        auto& under = target->terminalUnder[owner & 0xFFFFFF];
        under.index = intensityColorTable[under.index][factor];
        if (under.light <= 128) under.light = static_cast<unsigned char>((under.light * factor + 64) / 128);
        else { under.owner = 0; under.light = 128; }
        ++target->terminalUnderRevision;
    }
    if ((target->owners[offset] >> 24) == kSkeletonOwner
        || ((target->owners[offset] >> 24) == kPlayerOwner && (target->playerUnderOwners[offset] >> 24) == kSkeletonOwner)) {
        auto& under = target->skeletonUnder[offset];
        under.index = intensityColorTable[under.index][factor];
        if (under.light <= 128) under.light = static_cast<unsigned char>((under.light * factor + 64) / 128);
        else { under.owner = 0; under.light = 128; }
    }
    if ((target->owners[offset] >> 24) == kPlayerOwner) {
        target->playerUnderIndices[offset] = intensityColorTable[target->playerUnderIndices[offset]][factor];
        if (target->playerUnderLights[offset] <= 128) {
            target->playerUnderLights[offset] = static_cast<unsigned char>((target->playerUnderLights[offset] * factor + 64) / 128);
        } else {
            target->playerUnderOwners[offset] = 0;
            target->playerUnderLights[offset] = 128;
        }
    }
    if (target->lights[offset] <= 128) {
        target->lights[offset] = static_cast<unsigned char>((target->lights[offset] * factor + 64) / 128);
    } else {
        // A shadow after an overbright affine light cannot be represented by one byte.
        // Keep the exact original indexed result for this exceptional combination.
        target->owners[offset] = 0;
        target->lights[offset] = 128;
    }
}

void hdWorldScrollCache(int sourceDx, int sourceDy)
{
    const int width = overlayLogicalWidth;
    const int height = overlayLogicalHeight;
    if (!enabled || !overlay || overlayNeedsUpload || width <= 0 || height <= 0
        || (sourceDx == 0 && sourceDy == 0)
        || sourceDx <= -width || sourceDx >= width
        || sourceDy <= -height || sourceDy >= height) return;
    const int density = overlayWidth / width;
    const int sourceX = std::max(0, sourceDx);
    const int sourceY = std::max(0, sourceDy);
    const int destX = std::max(0, -sourceDx);
    const int destY = std::max(0, -sourceDy);
    const int copyWidth = width - std::abs(sourceDx);
    const int copyHeight = height - std::abs(sourceDy);
    // Rows must follow the same overlap direction as the original map scroll.
    // Horizontal overlap within each row is handled by memmove.
    for (int row = 0; row < copyHeight; row++) {
        int y = sourceDy < 0 ? copyHeight - row - 1 : row;
        size_t origin = static_cast<size_t>(sourceY + y) * width + sourceX;
        size_t target = static_cast<size_t>(destY + y) * width + destX;
        memmove(presentedOwners.data() + target, presentedOwners.data() + origin, copyWidth * sizeof(uint32_t));
        memmove(presentedLights.data() + target, presentedLights.data() + origin, copyWidth);
        memmove(presentedCaveOpacity.data() + target, presentedCaveOpacity.data() + origin, copyWidth);
    }
    for (int row = 0; row < copyHeight * density; row++) {
        int y = sourceDy < 0 ? copyHeight * density - row - 1 : row;
        size_t origin = static_cast<size_t>(sourceY * density + y) * overlayWidth + sourceX * density;
        size_t target = static_cast<size_t>(destY * density + y) * overlayWidth + destX * density;
        memmove(overlayPixels.data() + target, overlayPixels.data() + origin, copyWidth * density * sizeof(uint32_t));
    }
    for (int y = 0; y < height; y++) {
        bool copiedRow = y >= destY && y < destY + copyHeight;
        int left = copiedRow ? destX : width;
        int right = copiedRow ? destX + copyWidth : width;
        size_t row = static_cast<size_t>(y) * width;
        std::fill_n(presentedOwners.data() + row, left, 0);
        std::fill_n(presentedLights.data() + row, left, 128);
        std::fill_n(presentedOwners.data() + row + right, width - right, 0);
        std::fill_n(presentedLights.data() + row + right, width - right, 128);
        std::fill_n(presentedCaveOpacity.data() + row, left, 255);
        std::fill_n(presentedCaveOpacity.data() + row + right, width - right, 255);
        for (int sy = 0; sy < density; sy++) {
            uint32_t* pixels = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth;
            std::fill_n(pixels, left * density, 0);
            std::fill_n(pixels + right * density, (width - right) * density, 0);
        }
    }
    // A scroll moves pixels even when their owner/light values remain unchanged.
    // Upload the moved image, but do not invalidate its already shaded RGB cells.
    overlayScrollUpload = true;
}

void hdWorldCopy(const unsigned char* src, int width, int height, int srcPitch,
    unsigned char* dest, int destPitch, bool transparent)
{
    auto* target = findBuffer(dest);
    if (!target || !src || width <= 0 || height <= 0) return;
    auto* origin = findBuffer(src);
    // Scrolling within the same buffer does not move native FRM texels. Across
    // buffers copy the one small background snapshot once, never per scanline.
    if (origin && origin != target && !origin->terminalUnder.empty()) {
        const bool same = target->terminalUnder.size() == origin->terminalUnder.size()
            && std::equal(target->terminalUnder.begin(), target->terminalUnder.end(), origin->terminalUnder.begin(),
                [](const UnderPixel& a, const UnderPixel& b) { return a.owner == b.owner && a.light == b.light && a.index == b.index; });
        if (!same) {
            target->terminalUnder = origin->terminalUnder;
            ++target->terminalUnderRevision;
        }
    }
    for (int y = 0; y < height; y++) {
        const unsigned char* s = src + y * srcPitch;
        unsigned char* d = dest + y * destPitch;
        size_t offset = d - target->base;
        if (offset >= target->size || static_cast<size_t>(width) > target->size - offset) return;
        if (origin) {
            size_t sourceOffset = s - origin->base;
            if (sourceOffset >= origin->size || static_cast<size_t>(width) > origin->size - sourceOffset) return;
            if (!transparent) {
                memmove(target->owners.data() + offset, origin->owners.data() + sourceOffset, width * sizeof(uint32_t));
                memmove(target->lights.data() + offset, origin->lights.data() + sourceOffset, width);
                memmove(target->playerUnderOwners.data() + offset, origin->playerUnderOwners.data() + sourceOffset, width * sizeof(uint32_t));
                memmove(target->playerUnderLights.data() + offset, origin->playerUnderLights.data() + sourceOffset, width);
                memmove(target->playerUnderIndices.data() + offset, origin->playerUnderIndices.data() + sourceOffset, width);
                memmove(target->skeletonUnder.data() + offset, origin->skeletonUnder.data() + sourceOffset, width * sizeof(UnderPixel));
            } else {
                for (int x = 0; x < width; x++) {
                    if (s[x] == 0) continue;
                    target->owners[offset + x] = origin->owners[sourceOffset + x];
                    target->lights[offset + x] = origin->lights[sourceOffset + x];
                    target->playerUnderOwners[offset + x] = origin->playerUnderOwners[sourceOffset + x];
                    target->playerUnderLights[offset + x] = origin->playerUnderLights[sourceOffset + x];
                    target->playerUnderIndices[offset + x] = origin->playerUnderIndices[sourceOffset + x];
                    target->skeletonUnder[offset + x] = origin->skeletonUnder[sourceOffset + x];
                }
            }
        } else if (!currentAsset && !transparent) {
            // Most UI/background copies are untracked: clear whole rows without lookup.
            std::fill_n(target->owners.data() + offset, width, 0);
            std::fill_n(target->lights.data() + offset, width, 128);
        } else {
            for (int x = 0; x < width; x++) {
                if (transparent && s[x] == 0) continue;
                target->owners[offset + x] = currentAsset ? artOwner(s + x) : 0;
                target->lights[offset + x] = 128;
            }
        }
    }
}

void hdWorldClear(unsigned char* dest, int width, int height, int pitch)
{
    auto* target = findBuffer(dest);
    if (!target || width <= 0 || height <= 0) return;
    for (int y = 0; y < height; y++) {
        size_t offset = dest + y * pitch - target->base;
        if (offset >= target->size || static_cast<size_t>(width) > target->size - offset) return;
        std::fill_n(target->owners.data() + offset, width, 0);
        std::fill_n(target->lights.data() + offset, width, 128);
    }
}

bool hdWorldHudTarget(unsigned char* dest, int width, int height, int pitch)
{
    auto* target = findBuffer(dest);
    return target && width > 0 && height > 0 && pitch >= width
        && static_cast<size_t>(dest-target->base) + static_cast<size_t>(height-1)*pitch + width <= target->size;
}

void hdWorldMarkHudPixel(unsigned char* dest, unsigned int texel, int light)
{
    auto* target = findBuffer(dest);
    if (!target || texel >= 0xFFFFFF) return;
    size_t at = dest-target->base;
    target->owners[at] = (kHudOwner << 24) | texel;
    target->lights[at] = static_cast<unsigned char>(light);
    target->playerUnderIndices[at] = *dest;
    // Transparent GNW buttons skip index zero. Preserve that actual background
    // separately while ensuring the new icon cell reaches the presentation buffer.
    if (*dest == 0) *dest = 1;
}

unsigned int hdWorldOwnerAt(const unsigned char* pixel)
{
    auto* buffer = findBuffer(pixel);
    return buffer ? buffer->owners[pixel - buffer->base] : 0;
}

unsigned char hdWorldLightAt(const unsigned char* pixel)
{
    auto* buffer = findBuffer(pixel);
    return buffer && buffer->owners[pixel - buffer->base] ? buffer->lights[pixel - buffer->base] : 128;
}

void hdWorldSetEnabled(bool state) { hdWorldInit(); enabled = state; }
bool hdWorldEnabled() { hdWorldInit(); return enabled; }
bool hdWorldAssetLoaded(int id) { hdWorldInit(); return id > 0 && id < kAssetCapacity && !assets[id].rgba.empty(); }
int hdWorldAssetCapacity() { return kAssetCapacity; }
int hdWorldLoadedAssetCount()
{
    hdWorldInit();
    return static_cast<int>(std::count_if(assets.begin() + 1, assets.end(),
        [](const Asset& asset) { return !asset.rgba.empty(); }));
}

int hdWorldVisiblePixels(int id)
{
    if (!enabled || !gSdlSurface) return 0;
    auto* screen = findBuffer(static_cast<unsigned char*>(gSdlSurface->pixels));
    if (!screen) return 0;
    return static_cast<int>(std::count_if(screen->owners.begin(), screen->owners.end(),
        [id](uint32_t owner) { return id == 0 ? owner != 0 : (owner >> 24) == static_cast<uint32_t>(id); }));
}

void hdWorldReleaseTextures()
{
    if (overlay) SDL_DestroyTexture(overlay);
    overlay = nullptr;
    overlayWidth = overlayHeight = 0;
    overlayLogicalWidth = overlayLogicalHeight = 0;
    overlayPixels.clear();
    presentedOwners.clear();
    presentedLights.clear();
    presentedCaveOpacity.clear();
    overlayNeedsUpload = false;
    overlayScrollUpload = false;
}

// Blend against the real pre-terminal background, never the already drawn
// indexed FRM outline. Keeping both owner and palette index preserves the door
// frame at HD and classic pixels through light changes, clipping and scrolling.
static void sampleTerminal(const Buffer& screen, size_t at, uint32_t owner, int light,
    int subX, int subY, const SDL_Color* palette, unsigned char* color)
{
    const unsigned int texel = owner & 0xFFFFFF;
    const UnderPixel saved = texel >= screen.terminalUnder.size() ? UnderPixel {} : screen.terminalUnder[texel];
    const SDL_Color indexed = palette[saved.index];
    color[0] = indexed.r; color[1] = indexed.g; color[2] = indexed.b;
    const int underId = saved.owner >> 24;
    const unsigned int underTexel = saved.owner & 0xFFFFFF;
    const auto& under = assets[underId];
    if (isCaveOwner(underId)) {
        sampleCave(screen,at,saved.owner,saved.light,subX,subY,palette,color);
    } else if (underId != terminalBaseId && !under.rgba.empty() && underTexel < under.nativeIndices.size()) {
        const size_t uv = ((underTexel / under.width * 4 + subY) * under.width * 4
            + underTexel % under.width * 4 + subX) * 4;
        if (under.rgba[uv + 3]) for (int c = 0; c < 3; ++c)
            color[c] = lightColors[c][saved.light][under.rgba[uv + c]];
    }
    const size_t uv = ((texel / 32 * 4 + subY) * 128 + texel % 32 * 4 + subX) * 4;
    const auto& rgba = worldRgba(terminalBaseId);
    if (uv + 3 >= rgba.size()) return;
    const unsigned int alpha = rgba[uv + 3];
    for (int c = 0; c < 3; ++c) color[c] = static_cast<unsigned char>(
        (lightColors[c][light][rgba[uv + c]] * alpha + color[c] * (255 - alpha) + 127) / 255);
}

// Composite the flat skeleton over its own saved floor. The player's separate
// saved layer may point here, preserving both alphas when they overlap.
static void sampleSkeleton(const Buffer& screen, size_t at, uint32_t owner, int light,
    int subX, int subY, const SDL_Color* palette, unsigned char* color)
{
    const auto& saved = screen.skeletonUnder[at];
    const SDL_Color indexed = palette[saved.index];
    color[0] = indexed.r; color[1] = indexed.g; color[2] = indexed.b;
    const int underId = saved.owner >> 24;
    const unsigned int underTexel = saved.owner & 0xFFFFFF;
    const auto& under = assets[underId];
    if (isCaveOwner(underId)) {
        sampleCave(screen,at,saved.owner,saved.light,subX,subY,palette,color);
    } else if (terminalSoftEdges && underId == terminalBaseId) {
        sampleTerminal(screen, at, saved.owner, saved.light, subX, subY, palette, color);
    } else if (underId != kPlayerOwner && underId != kSkeletonOwner && !under.rgba.empty()
        && underTexel < under.nativeIndices.size()) {
        const size_t uv = ((underTexel / under.width * 4 + subY) * under.width * 4
            + underTexel % under.width * 4 + subX) * 4;
        const auto& rgba = worldRgba(underId);
        if (rgba[uv + 3]) for (int c = 0; c < 3; ++c)
            color[c] = lightColors[c][saved.light][rgba[uv + c]];
    }
    const unsigned int texel = owner & 0xFFFFFF;
    if (!skeletonAsset.rgba.empty() && texel < 67 * 41) {
        const size_t uv = ((texel / 67 * 4 + subY) * 268 + texel % 67 * 4 + subX) * 4;
        const unsigned int alpha = skeletonAsset.rgba[uv + 3];
        for (int c = 0; c < 3; ++c) color[c] = static_cast<unsigned char>(
            (lightColors[c][light][skeletonAsset.rgba[uv + c]] * alpha + color[c] * (255 - alpha) + 127) / 255);
    }
}

bool hdWorldRender()
{
    if (!gSdlSurface || !gSdlRenderer) return false;
    auto* screen = findBuffer(static_cast<unsigned char*>(gSdlSurface->pixels));
    if (!screen || std::none_of(screen->owners.begin(), screen->owners.end(), [](uint32_t p) { return p != 0; })) return false;
    if (!enabled && std::none_of(screen->owners.begin(), screen->owners.end(), [](uint32_t p) { return (p >> 24) == kHudOwner; })) return false;
    int width = gSdlSurface->w;
    int height = gSdlSurface->h;
    float scaleX = 1.0F, scaleY = 1.0F;
    SDL_RenderGetScale(gSdlRenderer, &scaleX, &scaleY);
    int density = std::clamp(static_cast<int>(std::ceil(std::max(scaleX, scaleY))), 1, 4);
    // Match output density up to the source's x4 maximum, avoiding unused x4 work at 1080p.
    if (!overlay || overlayWidth != width * density || overlayHeight != height * density
        || overlayLogicalWidth != width || overlayLogicalHeight != height) {
        hdWorldReleaseTextures();
        overlayWidth = width * density;
        overlayHeight = height * density;
        overlayLogicalWidth = width;
        overlayLogicalHeight = height;
        overlay = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, overlayWidth, overlayHeight);
        if (!overlay) return false;
        SDL_SetTextureBlendMode(overlay, SDL_BLENDMODE_BLEND);
        SDL_SetTextureScaleMode(overlay, SDL_ScaleModeNearest);
        overlayPixels.resize(static_cast<size_t>(overlayWidth) * overlayHeight);
        presentedOwners.resize(static_cast<size_t>(width) * height);
        presentedLights.resize(static_cast<size_t>(width) * height, 128);
        presentedCaveOpacity.resize(static_cast<size_t>(width) * height, 255);
        overlayNeedsUpload = true;
    }
    const auto* palette = gSdlSurface->format->palette->colors;
    bool paletteChanged = refreshLightColors(palette);
    bool refreshAll = paletteChanged || overlayNeedsUpload;
    const bool nextLampOn = terminalAssetId && enabled && hdWorldIsPilotMap()
        && (terminalPreviewPhase < 0 ? hdWorldTerminalLampOnAt(SDL_GetTicks()) : terminalPreviewPhase != 0);
    const bool lampChanged = nextLampOn != terminalLampOn;
    terminalLampOn = nextLampOn;
    const bool terminalBackgroundChanged = presentedTerminalUnderRevision != screen->terminalUnderRevision;
    presentedTerminalUnderRevision = screen->terminalUnderRevision;
    const bool caveBackgroundChanged = presentedCaveRevision != caveRevision;
    presentedCaveRevision = caveRevision;
    int dirtyLeft = width, dirtyTop = height, dirtyRight = 0, dirtyBottom = 0;
    int samples[4];
    for (int s = 0; s < density; s++) samples[s] = (2 * s + 1) * 2 / density;
    for (int y = 0; y < height; y++) {
        size_t screenRow = static_cast<size_t>(y) * gSdlSurface->pitch;
        size_t cacheRow = static_cast<size_t>(y) * width;
        for (int x = 0; x < width; x++) {
            uint32_t owner = screen->owners[screenRow + x];
            if (!enabled && (owner >> 24) != kHudOwner) owner = 0;
            unsigned char light = screen->lights[screenRow + x];
            uint32_t& oldOwner = presentedOwners[cacheRow + x];
            unsigned char& oldLight = presentedLights[cacheRow + x];
            const bool changedLampCell = lampChanged && terminalAssetId
                && (owner >> 24) == static_cast<unsigned int>(terminalAssetId)
                && (owner & 0xFFFFFF) < terminalLampTexels.size()
                && terminalLampTexels[owner & 0xFFFFFF];
            unsigned char caveOpacity=255;
            bool changedCaveCell=caveBackgroundChanged && isCaveOwner(owner>>24);
            if((owner>>24)==253) {
                unsigned int i=caveIndex(owner),t=caveTexel(owner);
                if(i<cavePlacements.size() && t<cavePlacements[i].opacity.size()) {
                    const auto& p=cavePlacements[i];caveOpacity=p.opacity[t];
                    // Opaque geometry cannot depend on its captured background.
                    // Retain both previous/current opacity so entering AND leaving
                    // the player's transparency egg still invalidate the cell.
                    if(p.geometryCoverage[t]==2 && caveOpacity==255
                        && presentedCaveOpacity[cacheRow+x]==255) changedCaveCell=false;
                }
            }
            // Actor colour also depends on the captured underlying pixel. It can
            // change without a different actor frame/texel, so recomposite these
            // few cells while retaining the existing cache for the whole world.
            if (owner == oldOwner && (owner >> 24) != kPlayerOwner && (owner >> 24) != kSkeletonOwner && (owner >> 24) != kHudOwner
                && !changedCaveCell
                && !(terminalBackgroundChanged && terminalSoftEdges && (owner >> 24) == static_cast<unsigned int>(terminalBaseId))
                && !changedLampCell && (!owner || (!refreshAll && light == oldLight))) continue;
            oldOwner = owner;
            oldLight = light;
            presentedCaveOpacity[cacheRow+x]=caveOpacity;
            dirtyLeft = std::min(dirtyLeft, x);
            dirtyRight = std::max(dirtyRight, x + 1);
            dirtyTop = std::min(dirtyTop, y);
            dirtyBottom = y + 1;
            int id = owner >> 24;
            unsigned int texel = owner & 0x00FFFFFF;
            if (isCaveOwner(id)) {
                for (int sy=0;sy<density;++sy) {
                    uint32_t* row=overlayPixels.data()+static_cast<size_t>(y*density+sy)*overlayWidth+x*density;
                    for (int sx=0;sx<density;++sx) {
                        unsigned char color[3] {};
                        sampleCave(*screen,screenRow+x,owner,light,samples[sx],samples[sy],palette,color);
                        row[sx]=0xFF000000|(uint32_t(color[0])<<16)|(uint32_t(color[1])<<8)|color[2];
                    }
                }
                continue;
            }
            if (terminalSoftEdges && id == terminalBaseId) {
                for (int sy = 0; sy < density; ++sy) {
                    uint32_t* row = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth + x * density;
                    for (int sx = 0; sx < density; ++sx) {
                        unsigned char color[3];
                        sampleTerminal(*screen, screenRow + x, owner, light, samples[sx], samples[sy], palette, color);
                        row[sx] = 0xFF000000 | (uint32_t(color[0]) << 16) | (uint32_t(color[1]) << 8) | color[2];
                    }
                }
                continue;
            }
            if (id == kHudOwner) {
                const SDL_Color bg = palette[screen->playerUnderIndices[screenRow+x]];
                for (int sy = 0; sy < density; ++sy) {
                    uint32_t* row = overlayPixels.data()+static_cast<size_t>(y*density+sy)*overlayWidth+x*density;
                    for (int sx = 0; sx < density; ++sx) {
                        const unsigned char* rgba = hdHudTexel(texel, samples[sx], samples[sy]);
                        unsigned char out[3] {bg.r, bg.g, bg.b};
                        if (rgba) for (int c = 0; c < 3; ++c)
                            out[c] = static_cast<unsigned char>((lightColors[c][light][rgba[c]]*rgba[3]+out[c]*(255-rgba[3])+127)/255);
                        row[sx] = 0xFF000000 | (uint32_t(out[0])<<16) | (uint32_t(out[1])<<8) | out[2];
                    }
                }
                continue;
            }
            if (id == kSkeletonOwner) {
                for (int sy = 0; sy < density; ++sy) {
                    uint32_t* row = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth + x * density;
                    for (int sx = 0; sx < density; ++sx) {
                        unsigned char color[3];
                        sampleSkeleton(*screen, screenRow + x, owner, light, samples[sx], samples[sy], palette, color);
                        row[sx] = 0xFF000000 | (static_cast<uint32_t>(color[0]) << 16)
                            | (static_cast<uint32_t>(color[1]) << 8) | color[2];
                    }
                }
                continue;
            }
            if (id == kPlayerOwner) {
                const HdPlayerFrame* actor = hdPlayerFrameAt((owner >> 16) & 0xFF);
                const unsigned int actorTexel = owner & 0xFFFF;
                const size_t at = screenRow + x;
                const uint32_t underOwner = screen->playerUnderOwners[at];
                const int underId = underOwner >> 24;
                const unsigned int underTexel = underOwner & 0xFFFFFF;
                const Asset& under = assets[underId];
                const int underLight = screen->playerUnderLights[at];
                const SDL_Color indexed = palette[screen->playerUnderIndices[at]];
                const bool hasUnder = underId != kPlayerOwner && !under.rgba.empty()
                    && underTexel < under.nativeIndices.size();
                for (int sy = 0; sy < density; sy++) {
                    uint32_t* row = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth + x * density;
                    for (int sx = 0; sx < density; sx++) {
                        if (!actor || !hdPlayerEnabled()) { row[sx] = 0; continue; }
                        unsigned char bg[3] {indexed.r, indexed.g, indexed.b};
                        if (isCaveOwner(underId)) {
                            sampleCave(*screen,at,underOwner,underLight,samples[sx],samples[sy],palette,bg);
                        } else if (terminalSoftEdges && underId == terminalBaseId) {
                            sampleTerminal(*screen, at, underOwner, underLight, samples[sx], samples[sy], palette, bg);
                        } else if (underId == kSkeletonOwner) {
                            sampleSkeleton(*screen, at, underOwner, underLight, samples[sx], samples[sy], palette, bg);
                        } else if (hasUnder) {
                            const size_t uv = ((underTexel / under.width * 4 + samples[sy]) * under.width * 4
                                + underTexel % under.width * 4 + samples[sx]) * 4;
                            const auto& rgba = worldRgba(underId);
                            if (rgba[uv + 3]) for (int c = 0; c < 3; c++)
                                bg[c] = lightColors[c][underLight][rgba[uv + c]];
                        }
                        unsigned char out[3] {bg[0], bg[1], bg[2]};
                        if (actorTexel < static_cast<unsigned int>(actor->width * actor->height)) {
                            const size_t uv = ((actorTexel / actor->width * 4 + samples[sy]) * actor->width * 4
                                + actorTexel % actor->width * 4 + samples[sx]) * 4;
                            const unsigned int alpha = actor->rgba[uv + 3];
                            for (int c = 0; c < 3; c++) out[c] = static_cast<unsigned char>(
                                (lightColors[c][light][actor->rgba[uv + c]] * alpha + bg[c] * (255 - alpha) + 127) / 255);
                        }
                        row[sx] = 0xFF000000 | (static_cast<uint32_t>(out[0]) << 16)
                            | (static_cast<uint32_t>(out[1]) << 8) | out[2];
                    }
                }
                continue;
            }
            const Asset& asset = assets[id];
            if (!owner || asset.rgba.empty() || texel >= asset.nativeIndices.size()) {
                // A classic sprite, window or cursor now owns this cell. Remove the
                // previously presented HD pixels, including their whole density block.
                for (int sy = 0; sy < density; sy++) {
                    uint32_t* row = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth + x * density;
                    std::fill_n(row, density, 0);
                }
                continue;
            }
            int u = (texel % asset.width) * 4;
            int v = (texel / asset.width) * 4;
            const unsigned char* reds = lightColors[0][light];
            const unsigned char* greens = lightColors[1][light];
            const unsigned char* blues = lightColors[2][light];
            const auto& rgba = worldRgba(id);
            for (int sy = 0; sy < density; sy++) {
                uint32_t* row = overlayPixels.data() + static_cast<size_t>(y * density + sy) * overlayWidth + x * density;
                const unsigned char* sourceRow = rgba.data() + (static_cast<size_t>(v + samples[sy]) * asset.width * 4 + u) * 4;
                for (int sx = 0; sx < density; sx++) {
                    const unsigned char* src = sourceRow + samples[sx] * 4;
                    row[sx] = src[3] ? 0xFF000000 | (static_cast<uint32_t>(reds[src[0]]) << 16)
                        | (static_cast<uint32_t>(greens[src[1]]) << 8) | blues[src[2]] : 0;
                }
            }
        }
    }
    // Initial texture memory is undefined; upload its transparent background too.
    // Later frames reuse unchanged pixels and upload only the affected rectangle.
    if (overlayNeedsUpload || overlayScrollUpload) {
        if (SDL_UpdateTexture(overlay, nullptr, overlayPixels.data(), overlayWidth * sizeof(uint32_t)) != 0) {
            overlayNeedsUpload = true;
            return false;
        }
        overlayNeedsUpload = false;
        overlayScrollUpload = false;
    } else if (dirtyLeft < dirtyRight && dirtyTop < dirtyBottom) {
        SDL_Rect dirty = {dirtyLeft * density, dirtyTop * density,
            (dirtyRight - dirtyLeft) * density, (dirtyBottom - dirtyTop) * density};
        const uint32_t* pixels = overlayPixels.data() + static_cast<size_t>(dirty.y) * overlayWidth + dirty.x;
        if (SDL_UpdateTexture(overlay, &dirty, pixels, overlayWidth * sizeof(uint32_t)) != 0) {
            overlayNeedsUpload = true;
            return false;
        }
    }
    SDL_Rect dest = {0, 0, width, height};
    return SDL_RenderCopy(gSdlRenderer, overlay, nullptr, &dest) == 0;
}
} // namespace fallout

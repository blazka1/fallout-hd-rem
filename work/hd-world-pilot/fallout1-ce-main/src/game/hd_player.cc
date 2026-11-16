#include "game/hd_player.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <utility>

#include "game/anim.h"
#include "game/gconfig.h"
#include "game/hd_world_pilot.h"
#include "game/map.h"
#include "game/object.h"
#include "game/stat.h"

namespace fallout {
namespace {
constexpr int kMaximumFrames = 64;
constexpr int kMaximumNativeDimension = 128;
constexpr size_t kMaximumNativeTexels = 16384;
constexpr const char* kDirectory = "data/art/hd/player-male-vault13/";
bool initialized = false;
bool enabled = true;
bool shadowEnabled = true;
std::vector<HdPlayerFrame> frames;

void prepareShadow(HdPlayerFrame& frame, const std::string& filename)
{
    const int width = frame.canvasWidth() * 4;
    const int height = frame.canvasHeight() * 4;
    frame.shadow.resize(static_cast<size_t>(width) * height);
    // A bounded per-pose mask extracted from the original FRM. Do not replace
    // absent/broken data with the old generic ellipse or a stale frame's mask.
    const std::string path = std::string(kDirectory)
        + filename.substr(0, filename.size() - 5) + ".shadow-mask";
    FILE* file = fopen(path.c_str(), "rb");
    if (!file) return;
    std::vector<unsigned char> mask(static_cast<size_t>(frame.width) * frame.height);
    bool valid = fread(mask.data(), 1, mask.size(), file) == mask.size() && fgetc(file) == EOF;
    fclose(file);
    valid = valid && std::all_of(mask.begin(), mask.end(), [](unsigned char a) { return a <= 1; })
        && std::any_of(mask.begin(), mask.end(), [](unsigned char a) { return a == 1; });
    if (!valid) return;
    frame.poseShadowLoaded = true;
    // Smooth the decoded shape at x4 (sigma=0.85 native pixels). The silhouette
    // changes with the actual CE pose; only the floor receives this darkening.
    constexpr int radius = 9;
    std::array<float, radius * 2 + 1> weights {};
    float sum = 0;
    for (int i = -radius; i <= radius; ++i) {
        weights[i + radius] = std::exp(-float(i * i) / (2 * 3.4f * 3.4f));
        sum += weights[i + radius];
    }
    for (float& weight : weights) weight /= sum;
    std::vector<float> horizontal(static_cast<size_t>(width) * height);
    const int apronX = kHdPlayerShadowPadX * 4;
    for (int y = 0; y < frame.height * 4; ++y) for (int x = 0; x < width; ++x) {
        float value = 0;
        for (int dx = -radius; dx <= radius; ++dx) {
            const int u = x + dx - apronX;
            if (u >= 0 && u < frame.width * 4)
                value += weights[dx + radius] * mask[static_cast<size_t>(y / 4) * frame.width + u / 4];
        }
        horizontal[static_cast<size_t>(y) * width + x] = value;
    }
    for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
        float value = 0;
        for (int dy = -radius; dy <= radius; ++dy) {
            const int v = y + dy;
            if (v >= 0 && v < height) value += weights[dy + radius] * horizontal[static_cast<size_t>(v) * width + x];
        }
        frame.shadow[static_cast<size_t>(y) * width + x] = static_cast<unsigned char>(value * 145 + 0.5f);
    }
}

bool parseInteger(const std::string& token, int& value)
{
    const auto result = std::from_chars(token.data(), token.data() + token.size(), value);
    return result.ec == std::errc() && result.ptr == token.data() + token.size();
}

bool safeFilename(const std::string& filename)
{
    if (filename.size() < 6 || filename.size() > 128
        || filename.find("..") != std::string::npos
        || filename.compare(filename.size() - 5, 5, ".rgba") != 0) return false;
    return std::all_of(filename.begin(), filename.end(), [](unsigned char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
            || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
    });
}

uint32_t littleEndian32(const unsigned char* bytes)
{
    return static_cast<uint32_t>(bytes[0])
        | (static_cast<uint32_t>(bytes[1]) << 8)
        | (static_cast<uint32_t>(bytes[2]) << 16)
        | (static_cast<uint32_t>(bytes[3]) << 24);
}

bool loadFrame(HdPlayerFrame& frame, const std::string& filename)
{
    if (frame.width < 1 || frame.height < 1
        || frame.width > kMaximumNativeDimension || frame.height > kMaximumNativeDimension
        || static_cast<size_t>(frame.width) * frame.height > kMaximumNativeTexels) return false;
    const std::string path = std::string(kDirectory) + filename;
    FILE* file = fopen(path.c_str(), "rb");
    if (!file) return false;
    std::array<unsigned char, 20> header {};
    bool valid = fread(header.data(), 1, header.size(), file) == header.size()
        && memcmp(header.data(), "F1HD", 4) == 0
        && littleEndian32(header.data() + 4) == 1
        && littleEndian32(header.data() + 8) == static_cast<uint32_t>(frame.width * 4)
        && littleEndian32(header.data() + 12) == static_cast<uint32_t>(frame.height * 4)
        && littleEndian32(header.data() + 16) == 4;
    if (valid) {
        // At most 1 MiB per frame, 64 MiB for the complete immutable cache.
        std::vector<unsigned char> rgba(static_cast<size_t>(frame.width) * frame.height * 64);
        valid = fread(rgba.data(), 1, rgba.size(), file) == rgba.size() && fgetc(file) == EOF;
        bool transparent = false;
        bool visible = false;
        for (size_t i = 3; valid && i < rgba.size(); i += 4) {
            transparent |= rgba[i] == 0;
            visible |= rgba[i] >= 240;
        }
        valid = valid && transparent && visible;
        if (valid) frame.rgba = std::move(rgba);
    }
    fclose(file);
    return valid;
}

bool supportedKey(int animation, int direction, int frame)
{
    return direction >= 0 && direction < ROTATION_COUNT
        && ((animation == ANIM_STAND && frame >= 0 && frame < 12)
            || (animation == ANIM_WALK && frame >= 0 && frame < 8));
}

int findFrame(int animation, int direction, int frame)
{
    if (!supportedKey(animation, direction, frame)) return -1;
    const int storedFrame = animation == ANIM_STAND ? -1 : frame;
    for (int index = 0; index < static_cast<int>(frames.size()); ++index) {
        const auto& candidate = frames[index];
        if (candidate.animation == animation && candidate.direction == direction
            && candidate.frame == storedFrame) return index;
    }
    return -1;
}
}

void hdPlayerInit()
{
    if (initialized) return;
    initialized = true;
    int configured = 1;
    config_get_value(&game_config, "remaster", "hd_player_male", &configured);
    enabled = configured != 0;
    int configuredShadow = 1;
    config_get_value(&game_config, "remaster", "hd_player_shadow", &configuredShadow);
    shadowEnabled = configuredShadow != 0;
    const std::string registryPath = std::string(kDirectory) + "registry.tsv";
    FILE* registry = fopen(registryPath.c_str(), "rb");
    if (!registry) return;
    frames.reserve(kMaximumFrames);
    // Bound registry line storage as well as frame allocations. An overlong
    // record is discarded as one record, never interpreted in fragments.
    char line[512];
    for (int number = 0; number < 512 && static_cast<int>(frames.size()) < kMaximumFrames
         && fgets(line, sizeof(line), registry); ++number) {
        if (!strchr(line, '\n') && !feof(registry)) {
            int next;
            while ((next = fgetc(registry)) != EOF && next != '\n') { }
            continue;
        }
        if (line[0] == '#') continue;
        std::istringstream fields(line);
        std::string animationToken, directionToken, frameToken, widthToken, heightToken, filename, extra;
        HdPlayerFrame candidate;
        if (!(fields >> animationToken >> directionToken >> frameToken >> widthToken >> heightToken >> filename)
            || (fields >> extra)
            || !parseInteger(animationToken, candidate.animation)
            || !parseInteger(directionToken, candidate.direction)
            || !parseInteger(frameToken, candidate.frame)
            || !parseInteger(widthToken, candidate.width)
            || !parseInteger(heightToken, candidate.height)
            || !safeFilename(filename)) continue;
        if (candidate.direction < 0 || candidate.direction >= ROTATION_COUNT
            || !((candidate.animation == ANIM_STAND && candidate.frame == -1)
                || (candidate.animation == ANIM_WALK && candidate.frame >= 0 && candidate.frame < 8))) continue;
        const int queryFrame = candidate.animation == ANIM_STAND ? 0 : candidate.frame;
        if (findFrame(candidate.animation, candidate.direction, queryFrame) >= 0) continue;
        if (loadFrame(candidate, filename)) {
            prepareShadow(candidate, filename);
            frames.push_back(std::move(candidate));
        }
    }
    fclose(registry);
}

bool hdPlayerEnabled()
{
    hdPlayerInit();
    return enabled;
}

void hdPlayerSetEnabled(bool value)
{
    hdPlayerInit();
    enabled = value;
}

bool hdPlayerShadowEnabled() { hdPlayerInit(); return shadowEnabled; }
void hdPlayerSetShadowEnabled(bool value) { hdPlayerInit(); shadowEnabled = value; }

bool hdPlayerEligible(const Object* object)
{
    hdPlayerInit();
    // Test the original object FID before art_alias_fid can share an animation
    // with women or NPCs. None of these guards mutates gameplay or animation.
    if (!enabled || !object || object != obj_dude || !hdWorldIsPilotMap()
        || FID_TYPE(object->fid) != OBJ_TYPE_CRITTER || (object->fid & 0xFFF) != 11
        || (object->fid & 0xF000) != 0
        || object->tile < 0 || object->tile >= 40000 || object->elevation != map_elevation
        || (object->flags & (OBJECT_HIDDEN | OBJECT_FLAT | OBJECT_FLAG_0xFC000)) != 0
        || ((object->outline & OUTLINE_TYPE_MASK) != 0 && (object->outline & OUTLINE_DISABLED) == 0)
        || stat_level(obj_dude, STAT_GENDER) != GENDER_MALE) return false;
    return supportedKey(FID_ANIM_TYPE(object->fid), object->rotation, object->frame);
}

int hdPlayerResolve(const Object* object)
{
    return hdPlayerEligible(object) ? findFrame(FID_ANIM_TYPE(object->fid), object->rotation, object->frame) : -1;
}

bool hdPlayerFrameAvailable(int animation, int direction, int frame)
{
    hdPlayerInit();
    return findFrame(animation, direction, frame) >= 0;
}

int hdPlayerLoadedFrameCount()
{
    hdPlayerInit();
    return static_cast<int>(frames.size());
}

const HdPlayerFrame* hdPlayerFrameAt(int index)
{
    hdPlayerInit();
    return index >= 0 && index < static_cast<int>(frames.size()) ? &frames[index] : nullptr;
}

const HdPlayerFrame* hdPlayerBoundsFrame(const Object* object)
{
    hdPlayerInit();
    // The original male FID remains the geometry identity here. Deliberately
    // ignore enabled, sex-stat, hidden/outline/translucency flags: these can
    // change before CE asks for the dirty area covering the previous HD draw.
    if (!object || object != obj_dude || !hdWorldIsPilotMap()
        || FID_TYPE(object->fid) != OBJ_TYPE_CRITTER || (object->fid & 0xFFF) != 11
        || (object->fid & 0xF000) != 0 || object->tile < 0 || object->tile >= 40000
        || object->elevation != map_elevation) return nullptr;
    const int index = findFrame(FID_ANIM_TYPE(object->fid), object->rotation, object->frame);
    return index >= 0 ? &frames[index] : nullptr;
}
} // namespace fallout

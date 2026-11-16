#ifndef FALLOUT_GAME_HD_PLAYER_H_
#define FALLOUT_GAME_HD_PLAYER_H_

#include <vector>

namespace fallout {
struct Object;

// Render-only apron. Original FRM size, offsets and costume pixels stay intact.
constexpr int kHdPlayerShadowPadX = 16;
constexpr int kHdPlayerShadowPadBottom = 8;

// Immutable x4 RGBA data; IDs remain stable for the lifetime of this process.
// Idle frame -1 is one static directional pose serving CE idle frames 0..11.
struct HdPlayerFrame {
    int width = 0;
    int height = 0;
    int animation = 0;
    int direction = 0;
    int frame = 0;
    std::vector<unsigned char> rgba;
    std::vector<unsigned char> shadow;
    bool poseShadowLoaded = false;
    int canvasWidth() const { return width + 2 * kHdPlayerShadowPadX; }
    int canvasHeight() const { return height + kHdPlayerShadowPadBottom; }
};

void hdPlayerInit();
bool hdPlayerEnabled();
void hdPlayerSetEnabled(bool enabled);
bool hdPlayerShadowEnabled();
void hdPlayerSetShadowEnabled(bool enabled);
bool hdPlayerEligible(const Object* object);
// Returns -1 if the object/state is unsupported or its individual frame is absent.
int hdPlayerResolve(const Object* object);
// Resource-only query, independent of enabled state. Frame is a CE frame number.
bool hdPlayerFrameAvailable(int animation, int direction, int frame);
int hdPlayerLoadedFrameCount();
const HdPlayerFrame* hdPlayerFrameAt(int index);
// Potential render bounds, even while a toggle/outline/visibility transition
// has made the current draw ineligible. Includes old HD extent in dirty areas.
const HdPlayerFrame* hdPlayerBoundsFrame(const Object* object);
}

#endif

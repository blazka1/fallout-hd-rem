#ifndef FALLOUT_GAME_HD_RAT_H_
#define FALLOUT_GAME_HD_RAT_H_
#include <vector>
namespace fallout {
// 253 belongs to the current connected cave walls.
constexpr unsigned int kHdRatOwner = 254;
struct Object;
struct HdRatFrame {
    int width = 0, height = 0;
    std::vector<unsigned char> rgba;
};
void hdRatInit();
bool hdRatEnabled();
void hdRatSetEnabled(bool value);
int hdRatResolve(const Object* object);
int hdRatFind(int animation, int direction, int frame);
int hdRatLoadedFrameCount();
int hdRatRegisteredKeyCount();
const HdRatFrame* hdRatFrameAt(int index);
}
#endif

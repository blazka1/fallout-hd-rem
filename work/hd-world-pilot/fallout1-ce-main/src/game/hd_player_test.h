#ifndef FALLOUT_GAME_HD_PLAYER_TEST_H_
#define FALLOUT_GAME_HD_PLAYER_TEST_H_

namespace fallout {
// Isolated process only, after loading the real V13ENT map and premade player.
int hdPlayerPreview(const char* directory);
int hdRatPreview(const char* directory);
}

#endif

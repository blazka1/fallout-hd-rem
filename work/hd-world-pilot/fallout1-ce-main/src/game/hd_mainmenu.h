#ifndef FALLOUT_GAME_HD_MAINMENU_H_
#define FALLOUT_GAME_HD_MAINMENU_H_

namespace fallout {

// Optional native-resolution presentation; gameplay keeps its logical canvas.
bool hdMainMenuCreate(const unsigned char* pixels, const unsigned char* palette);
void hdMainMenuDestroy();
void hdMainMenuReleaseTextures();
bool hdMainMenuEnabled();
void hdMainMenuSetVisible(bool visible);
bool hdMainMenuRender();
int hdMainMenuInput(int keyCode);

// Developer-only offscreen rendering and interaction checks, enabled by env var.
int hdMainMenuPreview(const char* directory);

} // namespace fallout

#endif

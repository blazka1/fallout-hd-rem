#ifndef FALLOUT_GAME_HD_HUD_H_
#define FALLOUT_GAME_HD_HUD_H_
namespace fallout {
constexpr int kHdHudPanelFid = 0x06000010;
bool hdHudPanelAvailable();
bool hdHudPanelTexel(unsigned int texel);
void hdHudPanelPaint(unsigned char* dest, int width, int height, int pitch, int sourceX, int sourceY, bool pressed = false);
void hdHudPanelRegisterArt(unsigned char* data, int width, int height, int sourceX, int sourceY, bool pressed = false);
void hdHudPanelReleaseArt();
bool hdHudAvailable(int fid);
bool hdHudDimensions(int fid, int* width, int* height);
void hdHudSetItemEnabled(int fid, bool enabled);
bool hdHudTexelMatches(unsigned int texel, int fid);
void hdHudSetEnabled(bool enabled);
void hdHudDraw(int fid, unsigned char* dest, int pitch, int x, int y, bool pressed);
bool hdHudDrawFit(int fid, unsigned char* dest, int width, int height, int pitch);
const unsigned char* hdHudTexel(unsigned int texel, int subX, int subY);
void hdHudSetDragCursor(int fid);
bool hdHudDragCursorActive();
void hdHudRenderDragCursor();
void hdHudReleaseCursorTexture();
}
#endif

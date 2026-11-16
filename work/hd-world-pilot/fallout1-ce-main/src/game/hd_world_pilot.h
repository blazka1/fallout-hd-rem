#ifndef FALLOUT_GAME_HD_WORLD_PILOT_H_
#define FALLOUT_GAME_HD_WORLD_PILOT_H_

namespace fallout {
bool hdWorldHudTarget(unsigned char* dest, int width, int height, int pitch);
struct Rect;
struct Object;
int hdWorldCaveAssignmentCount();
int hdWorldCaveAssetCount();
bool hdWorldCaveBackgroundHasAsset(unsigned int owner, int first, int last);
int hdWorldCavePlacementForObject(const Object* object);
int hdWorldCaveAssetForObject(const Object* object);
bool hdWorldCaveVarietyEnabled();
void hdWorldSetCaveVarietyEnabled(bool enabled);
void hdWorldCaveBounds(const Object* object, Rect* rect);
bool hdWorldBeginCaveScenery(const Object* object, unsigned char* base, int pitch,
    const Rect* art, const Rect* clip, int light);
void hdWorldCaveEgg(const unsigned char* mask, int pitch, const Rect* rect);
void hdWorldEndCaveScenery();
bool hdWorldSkeletonLoaded();
void hdWorldSetSkeletonEnabled(bool enabled);
bool hdWorldBeginSkeleton(const Object* object, unsigned char* buffer, int pitch,
    const Rect* artRect, const Rect* clip, int light);
void hdWorldEndSkeleton();
struct HdWorldDecoration {
    int assetId, tile, elevation, offsetX, offsetY;
    bool flat;
};
// Render-only placements: no Object, PID, FID, collision or save data is created.
int hdWorldDecorationAssetCount();
int hdWorldDecorationCount();
bool hdWorldDecorationDimensions(int assetId, int* width, int* height);
const HdWorldDecoration* hdWorldDecorationAt(int index);
void hdWorldSetDecorationsEnabled(bool enabled);
bool hdWorldCampfireShadowEnabled();
void hdWorldSetCampfireShadowEnabled(bool enabled);
// Native screen-space multiplier (128 = unchanged); introspection for shadow QA.
int hdWorldCampfireShadowFactorAt(int x, int y, int elevation);
bool hdWorldAssetIsFloor(int assetId);
bool hdWorldDecorationsActive(int elevation);
bool hdWorldHasDecoration(int tile);
void hdWorldDrawDecorationsAt(int tile, bool flat, unsigned char* buffer, int pitch,
    const Rect* clip, int elevation, int light);
// Render-only metadata. Never changes original art, object, map or pathfinding data.
void hdWorldInit();
bool hdWorldIsPilotMap();
bool hdWorldTerminalIndicatorLoaded();
bool hdWorldTerminalSoftEdges();
void hdWorldCaptureTerminalBackground(unsigned char* base, int pitch, const Rect* art, const Rect* clip);
// HD-only fill of the old terminal cutout in the original Vault frame.
void hdWorldFillVaultTerminalRecess(unsigned char* base, int pitch, const Rect* art, const Rect* clip, int light);
bool hdWorldTerminalLampOnAt(unsigned int milliseconds);
// Deterministic capture override: -1 real SDL clock, 0 off, 1 on.
void hdWorldSetTerminalPreviewPhase(int phase);
void hdWorldRegisterBuffer(unsigned char* base, int size);
void hdWorldUnregisterBuffer(unsigned char* base);
// Registry rows: id fid nativeWidth nativeHeight filename.rgba [frame].
// Omitting frame preserves the original static frame-zero registration.
void hdWorldBeginArt(int fid, const unsigned char* base, int width, int height, int frame = 0,
    int tile = -1, int elevation = 0);
// Optional variants.tsv: baseAssetId slot(1..2) variantAssetId filename.rgba.
// Appearance is selected only from original wall FID/frame and map coordinates.
int hdWorldResolveAsset(int fid, int frame = 0, int tile = -1, int elevation = 0);
int hdWorldWallVariantCount();
int hdWorldWallGeometryCount();
void hdWorldSetWallGeometryEnabled(bool enabled);
bool hdWorldWallGeometryEnabled();
bool hdWorldWallVariantsEnabled();
void hdWorldSetWallVariantsEnabled(bool enabled);
// Render-only square-tile pages. Stable map-cell selection; missing pages keep
// their own slot and fall back to the base without changing other assignments.
int hdWorldTileVariantCount();
int hdWorldResolveTileVariant(int fid, int squareTile, int elevation);
bool hdWorldTileVariantsEnabled();
void hdWorldSetTileVariantsEnabled(bool enabled);
void hdWorldEndArt();
void hdWorldBeginRat(const Object* object, const unsigned char* source, int width, int height);
// Capture diagnostic: opaque foreground cells must fully conceal the actor.
bool hdWorldOwnerIsOpaque(unsigned int owner);
// Preview-only differential regression: direct actor vs captured cave background.
int hdWorldPlayerCaveSamplingMismatches(int* samples);
// The classic draw still executes unchanged between Begin/End. Only render
// metadata records the soft-alpha actor over the original underlying pixels.
bool hdWorldBeginPlayer(int frameIndex, unsigned char* buffer, int pitch,
    const Rect* classicRect, const Rect* hdRect, const Rect* clip, int light);
void hdWorldEndPlayer();
void hdWorldWrite(unsigned char* dest, const unsigned char* source, int light = 128);
void hdWorldShade(unsigned char* dest, int light);
// Reuse presented RGB cells after a successful camera translation. The next
// render validates every shifted owner/light against the actual framebuffer.
void hdWorldScrollCache(int sourceDx, int sourceDy);
void hdWorldCopy(const unsigned char* src, int width, int height, int srcPitch,
    unsigned char* dest, int destPitch, bool transparent = false);
void hdWorldClear(unsigned char* dest, int width, int height, int pitch);
// Opaque button backgrounds with a soft-alpha native-resolution HUD icon.
void hdWorldMarkHudPixel(unsigned char* dest, unsigned int texel, int light);
bool hdWorldRender();
void hdWorldReleaseTextures();
void hdWorldSetEnabled(bool enabled);
bool hdWorldEnabled();
bool hdWorldAssetLoaded(int id);
int hdWorldLoadedAssetCount();
// Valid asset IDs are 1 .. capacity-1. ID 0 in VisiblePixels sums all assets.
int hdWorldAssetCapacity();
int hdWorldVisiblePixels(int id);
// Introspection for coverage/occlusion assertions in the isolated integration test.
unsigned int hdWorldOwnerAt(const unsigned char* pixel);
unsigned char hdWorldLightAt(const unsigned char* pixel);
}

#endif

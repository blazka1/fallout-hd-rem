#include "game/hd_mainmenu.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <cwchar>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

#include "game/gconfig.h"
#include "plib/gnw/input.h"
#include "plib/gnw/svga.h"

namespace fallout {
namespace {

constexpr int kCount = 5;
constexpr int kKeys[kCount] = { KEY_LOWERCASE_I, KEY_LOWERCASE_N,
    KEY_LOWERCASE_L, KEY_LOWERCASE_C, KEY_LOWERCASE_E };
constexpr const wchar_t* kLabels[kCount] = {
    L"INTRO", L"NEW GAME", L"LOAD GAME", L"CREDITS", L"EXIT" };

bool enabled = false;
bool visible = false;
bool preview = false;
SDL_Texture* background = nullptr;
std::vector<Uint32> backgroundPixels;
int backgroundWidth = 640;
int backgroundHeight = 480;
SDL_Rect backgroundSource { 8, 12, 380, 456 };
bool backgroundFromHd = false;
constexpr int kButtonWidth = 1020;
constexpr int kButtonHeight = 152;
enum class ButtonState { Normal, Hover, Pressed };
constexpr const char* kButtonFiles[] = { "normal.bmp", "hover.bmp", "pressed.bmp" };
struct ButtonImage {
    std::vector<Uint32> pixels;
    SDL_Texture* texture = nullptr;
};
std::array<ButtonImage, 3> buttonImages;
bool buttonsFromHd = false;
int selected = 0;
int pressed = -1;
bool keyboardFocus = true;
bool keyboardPressed = false;
int lastMouseX = -1;
int lastMouseY = -1;
bool textFailed = false;

struct TextImage {
    SDL_Texture* texture = nullptr;
    int width = 0;
    int height = 0;
};
std::map<std::wstring, TextImage> textCache;
int cacheHeight = 0;

// Runtime art is a lossless BMP copy of the selected ComfyUI PNG. SDL can load
// it without a new decoder dependency. Failure leaves the original FRM intact.
bool loadHdPortrait(const char* path)
{
    SDL_Surface* loaded = SDL_LoadBMP(path);
    if (loaded == nullptr) return false;
    // Accept the archival portrait or the full widescreen background.
    bool valid = loaded->w >= 380 && loaded->h >= 456
        && loaded->w <= 4096 && loaded->h <= 4096
        && (loaded->w * 6 == loaded->h * 5 || loaded->w * 9 == loaded->h * 16);
    if (!valid) {
        SDL_FreeSurface(loaded);
        return false;
    }
    SDL_Surface* rgba = SDL_ConvertSurfaceFormat(loaded, SDL_PIXELFORMAT_ARGB8888, 0);
    SDL_FreeSurface(loaded);
    if (rgba == nullptr) return false;
    std::vector<Uint32> pixels(static_cast<size_t>(rgba->w) * rgba->h);
    for (int y = 0; y < rgba->h; y++) {
        std::memcpy(pixels.data() + static_cast<size_t>(y) * rgba->w,
            static_cast<const unsigned char*>(rgba->pixels) + y * rgba->pitch,
            static_cast<size_t>(rgba->w) * sizeof(Uint32));
    }
    backgroundWidth = rgba->w;
    backgroundHeight = rgba->h;
    backgroundSource = { 0, 0, rgba->w, rgba->h };
    backgroundPixels.swap(pixels);
    backgroundFromHd = true;
    SDL_FreeSurface(rgba);
    return true;
}

// Install all three states atomically. A partial/malformed asset set must never
// change the shape or appearance midway through a click.
bool loadButtonImages(const std::filesystem::path& directory)
{
    std::array<std::vector<Uint32>, 3> pixels;
    for (size_t i = 0; i < pixels.size(); i++) {
        SDL_Surface* loaded = SDL_LoadBMP((directory / kButtonFiles[i]).string().c_str());
        if (loaded == nullptr) return false;
        bool valid = loaded->w == kButtonWidth && loaded->h == kButtonHeight;
        SDL_Surface* rgba = valid
            ? SDL_ConvertSurfaceFormat(loaded, SDL_PIXELFORMAT_ARGB8888, 0) : nullptr;
        SDL_FreeSurface(loaded);
        if (rgba == nullptr) return false;
        pixels[i].resize(static_cast<size_t>(kButtonWidth) * kButtonHeight);
        for (int y = 0; y < kButtonHeight; y++) {
            std::memcpy(pixels[i].data() + static_cast<size_t>(y) * kButtonWidth,
                static_cast<const unsigned char*>(rgba->pixels) + y * rgba->pitch,
                static_cast<size_t>(kButtonWidth) * sizeof(Uint32));
        }
        SDL_FreeSurface(rgba);
    }
    for (size_t i = 0; i < pixels.size(); i++) {
        SDL_DestroyTexture(buttonImages[i].texture);
        buttonImages[i].texture = nullptr;
        buttonImages[i].pixels.swap(pixels[i]);
    }
    buttonsFromHd = true;
    return true;
}

SDL_Texture* buttonTexture(ButtonState state)
{
    if (!buttonsFromHd) return nullptr;
    auto& image = buttonImages[static_cast<size_t>(state)];
    if (image.texture == nullptr) {
        image.texture = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
            SDL_TEXTUREACCESS_STATIC, kButtonWidth, kButtonHeight);
        if (image.texture != nullptr) {
            if (SDL_UpdateTexture(image.texture, nullptr, image.pixels.data(), kButtonWidth * 4) != 0) {
                SDL_DestroyTexture(image.texture);
                image.texture = nullptr;
            } else {
                SDL_SetTextureScaleMode(image.texture, SDL_ScaleModeLinear);
            }
        }
    }
    return image.texture;
}

struct Layout {
    int width;
    int height;
    float scale;
    float x;
    float panelWidth;
    std::array<SDL_FRect, kCount> buttons;
};

Layout layoutFor(int width, int height)
{
    Layout l {};
    l.width = width;
    l.height = height;
    l.scale = std::min(height / 1080.0f, width / 1440.0f);
    l.panelWidth = 430.0f * l.scale;
    l.x = width - 96.0f * l.scale - l.panelWidth;
    float top = 0.06f * height;
    for (int i = 0; i < kCount; i++) {
        l.buttons[i] = { l.x, top + i * 80.0f * l.scale,
            l.panelWidth, 64 * l.scale };
    }
    return l;
}

void outputSize(int& width, int& height)
{
    SDL_Texture* target = SDL_GetRenderTarget(gSdlRenderer);
    if (target != nullptr) {
        SDL_QueryTexture(target, nullptr, nullptr, &width, &height);
    } else {
        SDL_GetRendererOutputSize(gSdlRenderer, &width, &height);
    }
}

int hitTest(const Layout& l, int x, int y)
{
    // SDL's fractional rectangles cover pixel centers, including their edge pixels.
    float px = x + 0.5f;
    float py = y + 0.5f;
    for (int i = 0; i < kCount; i++) {
        const auto& r = l.buttons[i];
        if (px >= r.x && px < r.x + r.w && py >= r.y && py < r.y + r.h) {
            return i;
        }
    }
    return -1;
}

bool buttonActive(const Layout& l, int index)
{
    return keyboardFocus ? selected == index : hitTest(l, lastMouseX, lastMouseY) == index;
}

ButtonState buttonState(const Layout& l, int index)
{
    if (pressed == index) {
        return keyboardPressed || hitTest(l, lastMouseX, lastMouseY) == index
            ? ButtonState::Pressed : ButtonState::Normal;
    }
    return buttonActive(l, index) ? ButtonState::Hover : ButtonState::Normal;
}

int processInput(const Layout& l, int key, int x, int y, int mouseButtons, bool shift)
{
    int hit = hitTest(l, x, y);
    if (x != lastMouseX || y != lastMouseY) {
        keyboardFocus = false;
        if (hit != -1) selected = hit;
        lastMouseX = x;
        lastMouseY = y;
    }
    if ((mouseButtons & MOUSE_EVENT_LEFT_BUTTON_DOWN)
        && !(mouseButtons & MOUSE_EVENT_LEFT_BUTTON_REPEAT)) {
        pressed = hit;
        keyboardPressed = false;
        keyboardFocus = false;
        if (hit != -1) selected = hit;
    }
    if (mouseButtons & MOUSE_EVENT_LEFT_BUTTON_UP) {
        int action = pressed == hit && hit != -1 ? kKeys[hit] : key;
        pressed = -1;
        keyboardPressed = false;
        return action;
    }
    if (key == KEY_ARROW_DOWN || (key == KEY_TAB && !shift)) {
        keyboardFocus = true;
        pressed = -1;
        keyboardPressed = false;
        selected = (selected + 1) % kCount;
        return -1;
    }
    if (key == KEY_ARROW_UP || (key == KEY_TAB && shift)) {
        keyboardFocus = true;
        pressed = -1;
        keyboardPressed = false;
        selected = (selected + kCount - 1) % kCount;
        return -1;
    }
    if (key == KEY_RETURN) {
        pressed = selected;
        keyboardFocus = keyboardPressed = true;
        return kKeys[selected];
    }
    for (int i = 0; i < kCount; i++) {
        if (key == kKeys[i] || key == kKeys[i] - 'a' + 'A') {
            selected = pressed = i;
            keyboardFocus = keyboardPressed = true;
            return key;
        }
    }
    return key;
}

void fill(float x, float y, float width, float height, SDL_Color color)
{
    SDL_SetRenderDrawColor(gSdlRenderer, color.r, color.g, color.b, color.a);
    SDL_FRect r { x, y, width, height };
    SDL_RenderFillRectF(gSdlRenderer, &r);
}

void outline(SDL_FRect r, SDL_Color color)
{
    SDL_SetRenderDrawColor(gSdlRenderer, color.r, color.g, color.b, color.a);
    SDL_RenderDrawRectF(gSdlRenderer, &r);
}

void fade(float x, float width, float height, bool reverse = false)
{
    SDL_Color left { 18, 23, 20, static_cast<Uint8>(reverse ? 255 : 0) };
    SDL_Color right { 18, 23, 20, static_cast<Uint8>(reverse ? 0 : 255) };
    SDL_Vertex vertices[4] = {
        { { x, 0 }, left, { 0, 0 } }, { { x + width, 0 }, right, { 0, 0 } },
        { { x + width, height }, right, { 0, 0 } }, { { x, height }, left, { 0, 0 } },
    };
    const int indices[6] { 0, 1, 2, 0, 2, 3 };
    SDL_RenderGeometry(gSdlRenderer, nullptr, vertices, 4, indices, 6);
}

TextImage makeText(const wchar_t* text, int height, bool heading)
{
    TextImage result;
#ifdef _WIN32
    HDC dc = CreateCompatibleDC(nullptr);
    if (dc == nullptr) return result;
    HFONT font = CreateFontW(-height, 0, 0, 0, heading ? FW_BOLD : FW_NORMAL,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        ANTIALIASED_QUALITY, DEFAULT_PITCH, heading ? L"Bahnschrift" : L"Consolas");
    if (font == nullptr) { DeleteDC(dc); return result; }
    HGDIOBJ oldFont = SelectObject(dc, font);
    int length = static_cast<int>(wcslen(text));
    SIZE size {};
    GetTextExtentPoint32W(dc, text, length, &size);
    result.width = size.cx + 4;
    result.height = size.cy + 4;
    BITMAPINFO info {};
    info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth = result.width;
    info.bmiHeader.biHeight = -result.height;
    info.bmiHeader.biPlanes = 1;
    info.bmiHeader.biBitCount = 32;
    info.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr;
    HBITMAP bitmap = CreateDIBSection(dc, &info, DIB_RGB_COLORS, &bits, nullptr, 0);
    if (bitmap != nullptr && bits != nullptr) {
        HGDIOBJ oldBitmap = SelectObject(dc, bitmap);
        size_t count = static_cast<size_t>(result.width) * result.height;
        memset(bits, 0, count * sizeof(Uint32));
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 255, 255));
        TextOutW(dc, 2, 2, text, length);
        GdiFlush();
        auto* pixels = static_cast<Uint32*>(bits);
        // Grayscale coverage, not ClearType: safe for transparent SDL textures.
        for (size_t i = 0; i < count; i++) {
            Uint32 coverage = pixels[i] & 255;
            pixels[i] = (coverage << 24) | 0x00FFFFFF;
        }
        result.texture = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
            SDL_TEXTUREACCESS_STATIC, result.width, result.height);
        if (result.texture != nullptr) {
            SDL_UpdateTexture(result.texture, nullptr, bits, result.width * 4);
            SDL_SetTextureBlendMode(result.texture, SDL_BLENDMODE_BLEND);
        }
        SelectObject(dc, oldBitmap);
        DeleteObject(bitmap);
    }
    SelectObject(dc, oldFont);
    DeleteObject(font);
    DeleteDC(dc);
#endif
    return result;
}

void text(const wchar_t* value, float x, float y, float size, SDL_Color color, bool heading = false)
{
    int height = std::max(8, static_cast<int>(std::lround(size)));
    std::wstring key = std::to_wstring(height) + (heading ? L"H" : L"B") + value;
    auto it = textCache.find(key);
    if (it == textCache.end()) {
        it = textCache.emplace(key, makeText(value, height, heading)).first;
    }
    const auto& t = it->second;
    if (t.texture == nullptr) { textFailed = true; return; }
    SDL_SetTextureColorMod(t.texture, color.r, color.g, color.b);
    SDL_SetTextureAlphaMod(t.texture, color.a);
    SDL_FRect dst { std::round(x), std::round(y), static_cast<float>(t.width), static_cast<float>(t.height) };
    SDL_RenderCopyF(gSdlRenderer, t.texture, nullptr, &dst);
}

// All temporary renderer state is restored before any classic screen is drawn.
struct RenderState {
    int logicalWidth, logicalHeight;
    float scaleX, scaleY;
    SDL_Rect viewport, clip;
    SDL_bool clipped;
    SDL_BlendMode blend;
    SDL_Color color;
    RenderState()
    {
        SDL_RenderGetLogicalSize(gSdlRenderer, &logicalWidth, &logicalHeight);
        SDL_RenderGetScale(gSdlRenderer, &scaleX, &scaleY);
        SDL_RenderGetViewport(gSdlRenderer, &viewport);
        SDL_RenderGetClipRect(gSdlRenderer, &clip);
        clipped = SDL_RenderIsClipEnabled(gSdlRenderer);
        SDL_GetRenderDrawBlendMode(gSdlRenderer, &blend);
        SDL_GetRenderDrawColor(gSdlRenderer, &color.r, &color.g, &color.b, &color.a);
        SDL_RenderSetLogicalSize(gSdlRenderer, 0, 0);
        SDL_RenderSetScale(gSdlRenderer, 1, 1);
        SDL_RenderSetViewport(gSdlRenderer, nullptr);
        SDL_RenderSetClipRect(gSdlRenderer, nullptr);
        SDL_SetRenderDrawBlendMode(gSdlRenderer, SDL_BLENDMODE_BLEND);
    }
    ~RenderState()
    {
        SDL_RenderSetLogicalSize(gSdlRenderer, logicalWidth, logicalHeight);
        SDL_RenderSetScale(gSdlRenderer, scaleX, scaleY);
        SDL_RenderSetViewport(gSdlRenderer, &viewport);
        SDL_RenderSetClipRect(gSdlRenderer, clipped ? &clip : nullptr);
        SDL_SetRenderDrawBlendMode(gSdlRenderer, blend);
        SDL_SetRenderDrawColor(gSdlRenderer, color.r, color.g, color.b, color.a);
    }
};

void cursor(const Layout& l)
{
    if (mouse_hidden() || preview) return;
    int x, y;
    mouse_get_position(&x, &y);
    float px = x * static_cast<float>(l.width) / screenGetWidth();
    float py = y * static_cast<float>(l.height) / screenGetHeight();
    float s = std::max(1.0f, l.scale);
    SDL_Vertex vertices[3] = {
        { { px, py }, { 238, 223, 176, 255 }, { 0, 0 } },
        { { px + 7 * s, py + 25 * s }, { 179, 151, 91, 255 }, { 0, 0 } },
        { { px + 19 * s, py + 17 * s }, { 238, 223, 176, 255 }, { 0, 0 } },
    };
    SDL_RenderGeometry(gSdlRenderer, nullptr, vertices, 3, nullptr, 0);
    SDL_SetRenderDrawColor(gSdlRenderer, 10, 12, 10, 255);
    SDL_FPoint border[4] { vertices[0].position, vertices[1].position,
        vertices[2].position, vertices[0].position };
    SDL_RenderDrawLinesF(gSdlRenderer, border, 4);
}

} // namespace

bool hdMainMenuCreate(const unsigned char* pixels, const unsigned char* palette)
{
    hdMainMenuDestroy();
    int requested = 0;
    config_get_value(&game_config, "remaster", "hd_main_menu", &requested);
#ifdef _WIN32
    if (requested != 0) {
        TextImage probe = makeText(L"FALLOUT", 32, true);
        if (probe.texture == nullptr) return false;
        SDL_DestroyTexture(probe.texture);
        backgroundPixels.resize(640 * 480);
        for (size_t i = 0; i < backgroundPixels.size(); i++) {
            int index = pixels[i] * 3;
            backgroundPixels[i] = 0xFF000000
                | (static_cast<Uint32>(palette[index] << 2) << 16)
                | (static_cast<Uint32>(palette[index + 1] << 2) << 8)
                | static_cast<Uint32>(palette[index + 2] << 2);
        }
        int useHdBackground = 1;
        config_get_value(&game_config, "remaster", "hd_background", &useHdBackground);
        if (useHdBackground) {
            const char* portraitPath = "data/art/hd/main-menu/menu-background-v2.bmp";
            char* configuredPath = nullptr;
            if (config_get_string(&game_config, "remaster", "hd_background_file", &configuredPath)
                && configuredPath != nullptr && configuredPath[0] != '\0') {
                portraitPath = configuredPath;
            }
            if (!loadHdPortrait(portraitPath)) {
                SDL_Log("HD menu: could not load portrait %s; using original FRM", portraitPath);
            }
        }
        int useHdButton = 1;
        if (!config_get_value(&game_config, "remaster", "hd_menu_buttons", &useHdButton)) {
            // Retain configurations from the original single-button prototype.
            config_get_value(&game_config, "remaster", "hd_new_game_button", &useHdButton);
        }
        if (useHdButton && !loadButtonImages("data/art/hd/main-menu/new-game")) {
            SDL_Log("HD menu: incomplete shared button skin; using native fallback buttons");
        }
        enabled = true;
    }
#endif
    return enabled;
}

void hdMainMenuReleaseTextures()
{
    SDL_DestroyTexture(background);
    background = nullptr;
    for (auto& image : buttonImages) {
        SDL_DestroyTexture(image.texture);
        image.texture = nullptr;
    }
    for (auto& item : textCache) SDL_DestroyTexture(item.second.texture);
    textCache.clear();
    cacheHeight = 0;
}

void hdMainMenuDestroy()
{
    hdMainMenuReleaseTextures();
    backgroundPixels.clear();
    backgroundWidth = 640;
    backgroundHeight = 480;
    backgroundSource = { 8, 12, 380, 456 };
    backgroundFromHd = false;
    for (auto& image : buttonImages) image.pixels.clear();
    buttonsFromHd = false;
    pressed = -1;
    keyboardFocus = true;
    keyboardPressed = false;
    enabled = visible = false;
}

bool hdMainMenuEnabled() { return enabled; }

void hdMainMenuSetVisible(bool value)
{
    visible = value && enabled;
    pressed = -1;
    keyboardFocus = true;
    keyboardPressed = false;
    lastMouseX = lastMouseY = -1;
    if (visible) selected = 0;
}

bool hdMainMenuRender()
{
    if (!enabled || !visible || gSdlRenderer == nullptr) return false;
    int width = 0, height = 0;
    outputSize(width, height);
    if (width <= 0 || height <= 0) return false;
    Layout l = layoutFor(width, height);
    if (cacheHeight != static_cast<int>(l.scale * 1080)) {
        hdMainMenuReleaseTextures();
        cacheHeight = static_cast<int>(l.scale * 1080);
    }
    if (background == nullptr) {
        background = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
            SDL_TEXTUREACCESS_STATIC, backgroundWidth, backgroundHeight);
        if (background == nullptr) return false;
        SDL_UpdateTexture(background, nullptr, backgroundPixels.data(), backgroundWidth * 4);
        SDL_SetTextureScaleMode(background, SDL_ScaleModeLinear);
    }
    RenderState state;
    SDL_SetRenderDrawColor(gSdlRenderer, 18, 23, 20, 255);
    SDL_RenderClear(gSdlRenderer);
    float s = l.scale;
    // Preserve the artwork's own exposure and proportions; no UI tint or fade.
    const float factor = std::max(width / static_cast<float>(backgroundSource.w),
        height / static_cast<float>(backgroundSource.h));
    SDL_FRect art { 0, 0, backgroundSource.w * factor, backgroundSource.h * factor };
    SDL_SetTextureColorMod(background, 255, 255, 255);
    SDL_RenderCopyF(gSdlRenderer, background, &backgroundSource, &art);
    SDL_Color cream { 225, 216, 184, 255 };
    SDL_Color amber { 216, 181, 108, 255 };

    for (int i = 0; i < kCount; i++) {
        const auto& r = l.buttons[i];
        bool active = buttonActive(l, i);
        bool down = pressed == i && (keyboardPressed || hitTest(l, lastMouseX, lastMouseY) == i);
        fill(r.x + 3 * s, r.y + 5 * s, r.w, r.h, { 4, 8, 6, 180 });
        // All menu rows reuse the same approved art; each selects its own state.
        SDL_Texture* skin = buttonTexture(buttonState(l, i));
        if (skin != nullptr) {
            SDL_RenderCopyF(gSdlRenderer, skin, nullptr, &r);
        } else {
            fill(r.x, r.y, r.w, r.h, down ? SDL_Color { 69, 63, 42, 255 }
                : active ? SDL_Color { 50, 52, 37, 255 } : SDL_Color { 29, 35, 29, 255 });
            outline(r, active ? amber : SDL_Color { 86, 91, 72, 255 });
            if (active) fill(r.x, r.y, 4 * s, r.h, amber);
            fill(r.x + 23 * s, r.y + 30 * s, 14 * s, 14 * s, { 8, 12, 9, 255 });
            fill(r.x + 27 * s, r.y + 34 * s, 6 * s, 6 * s,
                active ? amber : SDL_Color { 103, 117, 78, 255 });
        }
        float textX = r.x + (skin != nullptr ? 84 : 57) * s;
        float textY = r.y + (19 + (skin != nullptr && down ? 1 : 0)) * s;
        if (skin != nullptr) text(kLabels[i], textX + s, textY + s, 31 * s, { 6, 9, 6, 255 }, true);
        text(kLabels[i], textX, textY, 31 * s,
            active ? cream : skin != nullptr ? SDL_Color { 197, 202, 173, 255 }
                                            : SDL_Color { 184, 191, 161, 255 }, true);
    }
    cursor(l);
    return true;
}

int hdMainMenuInput(int keyCode)
{
    if (!enabled || !visible) return keyCode;
    int width = 0, height = 0, x, y;
    outputSize(width, height);
    mouse_get_position(&x, &y);
    x = static_cast<int>(x * static_cast<float>(width) / screenGetWidth());
    y = static_cast<int>(y * static_cast<float>(height) / screenGetHeight());
    bool shift = keys[SDL_SCANCODE_LSHIFT] != KEY_STATE_UP
        || keys[SDL_SCANCODE_RSHIFT] != KEY_STATE_UP;
    return processInput(layoutFor(width, height), keyCode, x, y, mouse_get_buttons(), shift);
}

int hdMainMenuPreview(const char* directory)
{
    if (!enabled) return 2;
    const std::filesystem::path outputDirectory(directory);
    std::error_code error;
    std::filesystem::create_directories(outputDirectory, error);
    if (error) return 3;
    std::ofstream report(outputDirectory / "checks.txt");
    if (!report) return 4;
    preview = true;
    visible = true;
    int failures = 0;
    auto check = [&](bool pass, const std::string& name) {
        report << (pass ? "PASS " : "FAIL ") << name << '\n';
        if (!pass) failures++;
    };
    const char* expectHd = SDL_getenv("FALLOUT_HD_MENU_EXPECT_HD");
    if (expectHd != nullptr && expectHd[0] == '1') {
        check(backgroundFromHd && backgroundWidth == 3840 && backgroundHeight == 2160,
            "selected HD background actually loaded at 3840x2160");
        check(buttonsFromHd, "shared HD button states actually loaded at 1020x152");
    }
    report << "Background: " << (backgroundFromHd ? "HD" : "original FRM")
           << " " << backgroundWidth << "x" << backgroundHeight << '\n';
    const auto savedPixels = backgroundPixels;
    int savedWidth = backgroundWidth, savedHeight = backgroundHeight;
    check(!loadHdPortrait("") && backgroundPixels == savedPixels
            && backgroundWidth == savedWidth && backgroundHeight == savedHeight,
        "missing replacement leaves current background intact");
    std::string invalidPath = (outputDirectory / "invalid-background.fixture").string();
    { std::ofstream invalid(invalidPath, std::ios::binary); invalid << "not a bitmap"; }
    check(!loadHdPortrait(invalidPath.c_str()) && backgroundPixels == savedPixels,
        "corrupt replacement leaves current background intact");
    SDL_Surface* wrongAspect = SDL_CreateRGBSurfaceWithFormat(0, 640, 480, 32, SDL_PIXELFORMAT_ARGB8888);
    if (wrongAspect != nullptr) {
        SDL_FillRect(wrongAspect, nullptr, 0);
        bool saved = SDL_SaveBMP(wrongAspect, invalidPath.c_str()) == 0;
        SDL_FreeSurface(wrongAspect);
        check(saved && !loadHdPortrait(invalidPath.c_str()) && backgroundPixels == savedPixels,
            "full-frame replacement rejected without squeezing the helmet");
    } else {
        check(false, "create aspect-ratio test surface");
    }
    if (buttonsFromHd) {
        check(buttonImages[0].pixels != buttonImages[1].pixels
                && buttonImages[1].pixels != buttonImages[2].pixels
                && buttonImages[0].pixels != buttonImages[2].pixels,
            "shared normal, hover and pressed artwork is distinct");
        std::array<std::vector<Uint32>, 3> savedButtonPixels;
        for (size_t i = 0; i < savedButtonPixels.size(); i++) savedButtonPixels[i] = buttonImages[i].pixels;
        auto unchanged = [&]() {
            for (size_t i = 0; i < savedButtonPixels.size(); i++) {
                if (savedButtonPixels[i] != buttonImages[i].pixels) return false;
            }
            return buttonsFromHd;
        };
        auto fixture = outputDirectory / "button-fixture";
        std::filesystem::create_directories(fixture, error);
        // Make the first state valid, so rejection of later states proves atomic loading.
        std::filesystem::copy_file("data/art/hd/main-menu/new-game/normal.bmp", fixture / "normal.bmp",
            std::filesystem::copy_options::overwrite_existing, error);
        check(!loadButtonImages(fixture / "absent") && unchanged(),
            "missing button set preserves working skin");
        { std::ofstream invalid(fixture / "hover.bmp", std::ios::binary); invalid << "not a bitmap"; }
        check(!loadButtonImages(fixture) && unchanged(),
            "corrupt second state cannot partially replace working skin");
        SDL_Surface* wrongSize = SDL_CreateRGBSurfaceWithFormat(0, 510, 76, 32, SDL_PIXELFORMAT_ARGB8888);
        bool invalidSaved = false;
        if (wrongSize != nullptr) {
            SDL_FillRect(wrongSize, nullptr, 0);
            invalidSaved = SDL_SaveBMP(wrongSize, (fixture / "hover.bmp").string().c_str()) == 0;
            SDL_FreeSurface(wrongSize);
        }
        check(invalidSaved && !loadButtonImages(fixture) && unchanged(),
            "wrong-sized state rejected without changing working skin");
    }
    const int sizes[][2] = { { 1920, 1080 }, { 2560, 1440 }, { 3840, 2160 },
        { 3440, 1440 }, { 1280, 960 }, { 640, 480 } };
    for (const auto& size : sizes) {
        int width = size[0], height = size[1];
        std::string name = std::to_string(width) + "x" + std::to_string(height);
        Layout l = layoutFor(width, height);
        selected = 0;
        pressed = -1;
        keyboardFocus = true;
        keyboardPressed = false;
        lastMouseX = lastMouseY = -1;
        bool geometry = true;
        bool clicks = true;
        for (int i = 0; i < kCount; i++) {
            const auto& b = l.buttons[i];
            geometry &= b.x >= 0 && b.y >= 0 && b.x + b.w <= width && b.y + b.h <= height;
            // Exercise both edges, center, and click cancellation on drag-out.
            for (float fraction : { 0.02f, 0.5f, 0.98f }) {
                int x = static_cast<int>(b.x + b.w * fraction);
                int y = static_cast<int>(b.y + b.h * fraction);
                processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_DOWN, false);
                clicks &= processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_UP, false) == kKeys[i];
                processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_DOWN, false);
                clicks &= processInput(l, -1, 0, 0, MOUSE_EVENT_LEFT_BUTTON_UP, false) == -1;
            }
        }
        check(geometry, name + " layout in bounds");
        check(clicks, name + " all buttons, edges, drag cancellation");
        const auto& newGame = l.buttons[1];
        int nx = static_cast<int>(newGame.x + newGame.w / 2);
        int ny = static_cast<int>(newGame.y + newGame.h / 2);
        std::array<bool, 6> mouseStates { true, true, true, true, true, true };
        bool independentStates = true;
        for (int i = 0; i < kCount; i++) {
            const auto& b = l.buttons[i];
            int x = static_cast<int>(b.x + b.w / 2);
            int y = static_cast<int>(b.y + b.h / 2);
            processInput(l, -1, x, y, 0, false);
            mouseStates[0] &= buttonState(l, i) == ButtonState::Hover;
            mouseStates[1] &= processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_DOWN, false) == -1
                && buttonState(l, i) == ButtonState::Pressed;
            for (int other = 0; other < kCount; other++) {
                if (other != i) independentStates &= buttonState(l, other) == ButtonState::Normal;
            }
            processInput(l, -1, 0, 0, MOUSE_EVENT_LEFT_BUTTON_REPEAT, false);
            mouseStates[2] &= buttonState(l, i) == ButtonState::Normal;
            processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_REPEAT, false);
            mouseStates[3] &= buttonState(l, i) == ButtonState::Pressed;
            mouseStates[4] &= processInput(l, -1, x, y, MOUSE_EVENT_LEFT_BUTTON_UP, false) == kKeys[i]
                && buttonState(l, i) == ButtonState::Hover;
            processInput(l, -1, 0, 0, 0, false);
            mouseStates[5] &= buttonState(l, i) == ButtonState::Normal;
        }
        check(mouseStates[0], name + " all rows hover");
        check(mouseStates[1], name + " all rows depressed while held, not activated on down");
        check(mouseStates[2], name + " all rows drag out removes depression");
        check(mouseStates[3], name + " all rows drag back restores depression");
        check(mouseStates[4], name + " all rows release dispatches correct action and restores hover");
        check(mouseStates[5], name + " all rows pointer leave restores normal");
        check(independentStates, name + " pressing one row leaves other rows normal");
        selected = 0;
        processInput(l, KEY_ARROW_UP, 0, 0, 0, false);
        check(processInput(l, KEY_RETURN, 0, 0, 0, false) == KEY_LOWERCASE_E, name + " keyboard wrap up");
        processInput(l, KEY_TAB, 0, 0, 0, false);
        check(processInput(l, KEY_RETURN, 0, 0, 0, false) == KEY_LOWERCASE_I, name + " tab wrap down");
        processInput(l, KEY_TAB, 0, 0, 0, true);
        check(processInput(l, KEY_RETURN, 0, 0, 0, false) == KEY_LOWERCASE_E, name + " shift tab");
        bool focused = true, confirmed = true, shortcuts = true;
        for (int i = 0; i < kCount; i++) {
            processInput(l, KEY_TAB, 0, 0, 0, false);
            focused &= buttonState(l, i) == ButtonState::Hover;
            confirmed &= processInput(l, KEY_RETURN, 0, 0, 0, false) == kKeys[i]
                && buttonState(l, i) == ButtonState::Pressed;
            for (int key : { kKeys[i], kKeys[i] - 'a' + 'A' }) {
                shortcuts &= processInput(l, key, 0, 0, 0, false) == key
                    && buttonState(l, i) == ButtonState::Pressed;
            }
        }
        check(focused, name + " keyboard focus uses hover for all rows");
        check(confirmed, name + " keyboard confirmation presses the selected row");
        check(shortcuts, name + " lower and uppercase shortcuts preserve dispatch and press their row");
        selected = 0;
        pressed = -1;
        keyboardFocus = true;
        keyboardPressed = false;
        SDL_Texture* target = SDL_CreateTexture(gSdlRenderer, SDL_PIXELFORMAT_ARGB8888,
            SDL_TEXTUREACCESS_TARGET, width, height);
        check(target != nullptr, name + " render target");
        if (target == nullptr) continue;
        SDL_SetRenderTarget(gSdlRenderer, target);
        int beforeW, beforeH;
        SDL_RenderGetLogicalSize(gSdlRenderer, &beforeW, &beforeH);
        textFailed = false;
        check(hdMainMenuRender() && !textFailed, name + " native render and fonts");
        int afterW, afterH;
        SDL_RenderGetLogicalSize(gSdlRenderer, &afterW, &afterH);
        check(beforeW == afterW && beforeH == afterH, name + " logical canvas restored");
        SDL_Surface* surface = SDL_CreateRGBSurfaceWithFormat(0, width, height, 32, SDL_PIXELFORMAT_ARGB8888);
        bool saved = false;
        if (surface != nullptr) {
            // Capture the whole target, independent of the restored logical viewport.
            RenderState state;
            SDL_Rect full { 0, 0, width, height };
            saved = SDL_RenderReadPixels(gSdlRenderer, &full, surface->format->format,
                        surface->pixels, surface->pitch) == 0
                && SDL_SaveBMP(surface, (outputDirectory / (name + ".bmp")).string().c_str()) == 0;
            SDL_FreeSurface(surface);
        }
        check(saved, name + " screenshot");
        if (width == 3840 && buttonsFromHd) {
            SDL_Surface* strip = SDL_CreateRGBSurfaceWithFormat(0, static_cast<int>(newGame.w),
                static_cast<int>(newGame.h) * 3 + 32, 32, SDL_PIXELFORMAT_ARGB8888);
            bool captured = strip != nullptr;
            if (strip != nullptr) SDL_FillRect(strip, nullptr, 0xFF121714);
            processInput(l, -1, 1, 1, 0, false);
            for (int i = 0; i < 3 && strip != nullptr; i++) {
                // Drive real mouse input, then capture the actual renderer including text.
                processInput(l, -1, i == 0 ? 0 : nx, i == 0 ? 0 : ny,
                    i == 2 ? MOUSE_EVENT_LEFT_BUTTON_DOWN : 0, false);
                captured &= static_cast<int>(buttonState(l, 1)) == i && hdMainMenuRender();
                SDL_Surface* crop = SDL_CreateRGBSurfaceWithFormat(0, static_cast<int>(newGame.w),
                    static_cast<int>(newGame.h), 32, SDL_PIXELFORMAT_ARGB8888);
                if (crop == nullptr) { captured = false; continue; }
                {
                    RenderState state;
                    SDL_Rect bounds { static_cast<int>(newGame.x), static_cast<int>(newGame.y),
                        static_cast<int>(newGame.w), static_cast<int>(newGame.h) };
                    captured &= SDL_RenderReadPixels(gSdlRenderer, &bounds, crop->format->format,
                        crop->pixels, crop->pitch) == 0;
                }
                std::string stateName = i == 0 ? "normal" : i == 1 ? "hover" : "pressed";
                captured &= SDL_SaveBMP(crop, (outputDirectory / ("new-game-" + stateName + ".bmp")).string().c_str()) == 0;
                SDL_Rect destination { 0, i * (static_cast<int>(newGame.h) + 16), static_cast<int>(newGame.w), static_cast<int>(newGame.h) };
                captured &= SDL_BlitSurface(crop, nullptr, strip, &destination) == 0;
                SDL_FreeSurface(crop);
            }
            if (strip != nullptr) {
                captured &= SDL_SaveBMP(strip, (outputDirectory / "new-game-states.bmp").string().c_str()) == 0;
                SDL_FreeSurface(strip);
            }
            check(captured, "4K New Game state captures from real input and renderer");
            processInput(l, -1, 0, 0, MOUSE_EVENT_LEFT_BUTTON_UP, false);
        }
        SDL_SetRenderTarget(gSdlRenderer, nullptr);
        SDL_DestroyTexture(target);
    }
    hdMainMenuReleaseTextures();
    textFailed = false;
    bool recreated = hdMainMenuRender() && !textFailed;
    if (buttonsFromHd) {
        for (auto state : { ButtonState::Normal, ButtonState::Hover, ButtonState::Pressed }) {
            recreated &= buttonTexture(state) != nullptr;
        }
    }
    check(recreated, "texture recreation after release, including all button states");
    bool hadButton = buttonsFromHd;
    buttonsFromHd = false;
    check(hdMainMenuRender(), "missing skin keeps native fallback menu functional");
    buttonsFromHd = hadButton;
    hdMainMenuSetVisible(false);
    check(!hdMainMenuRender(), "hidden menu yields to classic rendering");
    hdMainMenuSetVisible(true);
    check(hdMainMenuRender(), "return to menu");
    report << "Failures: " << failures << '\n';
    preview = false;
    return failures == 0 ? 0 : 5;
}

} // namespace fallout


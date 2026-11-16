// Optional snippet for hd_world_pilot_test.cc, owned/integrated by the test agent.
// Place this function in its anonymous namespace after Capture/capture(). Call
// fadeRegression(output, report) after the existing black-palette test restores
// normalPalette. No world ticks should run between these captures.
// FALLOUT_HD_WORLD_FADE_BASELINE=1 captures the old renderer without counting
// expected regression failures against the existing integration checks.
void fadeRegression(const std::filesystem::path& output, Report& report)
{
    std::array<unsigned char, 768> normalPalette;
    std::memcpy(normalPalette.data(), getSystemPalette(), normalPalette.size());
    struct RestorePalette {
        const unsigned char* palette;
        ~RestorePalette() { palette_set_to(const_cast<unsigned char*>(palette)); }
    } restore { normalPalette.data() };
    const bool assertions = SDL_getenv("FALLOUT_HD_WORLD_FADE_BASELINE") == nullptr;
    const Capture normal = capture(output / "fade-normal-hd.bmp", true);
    const Capture normalClassic = capture(output / "fade-normal-classic.bmp", false);
    if (!normal.valid || !normalClassic.valid) {
        if (assertions) report.check(false, "fade regression normal captures");
        return;
    }
    const auto* indexed = static_cast<const unsigned char*>(gSdlSurface->pixels);
    SDL_Surface* mask = SDL_CreateRGBSurfaceWithFormat(0, screenGetWidth(), screenGetHeight(),
        32, SDL_PIXELFORMAT_ARGB8888);
    if (mask != nullptr) {
        for (int y = 0; y < mask->h; ++y) {
            auto* row = reinterpret_cast<uint32_t*>(static_cast<unsigned char*>(mask->pixels) + y * mask->pitch);
            for (int x = 0; x < mask->w; ++x) {
                row[x] = hdWorldOwnerAt(indexed + y * gSdlSurface->pitch + x) ? 0xFFFFFFFFU : 0xFF000000U;
            }
        }
        SDL_SaveBMP(mask, (output / "fade-owner-mask.bmp").string().c_str());
        SDL_FreeSurface(mask);
    }
    struct FadeCase { const char* name; int numerator; int denominator; bool white; };
    const std::array<FadeCase, 4> cases {{
        { "dark25", 1, 4, false }, { "dark50", 1, 2, false },
        { "white50", 1, 2, true }, { "white", 1, 1, true }
    }};
    std::ofstream metrics(output / "fade-metrics.txt");
    metrics << "name owned_pixels pixels_over_tolerance max_channel_error\n";
    for (const auto& spec : cases) {
        std::array<unsigned char, 768> palette;
        for (size_t i = 0; i < palette.size(); ++i) {
            int c = normalPalette[i];
            palette[i] = static_cast<unsigned char>(spec.white
                ? c + (63 - c) * spec.numerator / spec.denominator
                : c * spec.numerator / spec.denominator);
        }
        palette_set_to(palette.data());
        const Capture classic = capture(output / (std::string("fade-") + spec.name + "-classic.bmp"), false);
        const Capture hd = capture(output / (std::string("fade-") + spec.name + "-hd.bmp"), true);
        const bool endpoint = spec.white && spec.numerator == spec.denominator;
        bool valid = classic.valid && hd.valid && hd.width == normal.width && hd.height == normal.height;
        int checked = 0;
        int bad = 0;
        double maxError = 0.0;
        if (valid) {
            for (int y = 0; y < hd.height; ++y) {
                int ly = y * screenGetHeight() / hd.height;
                for (int x = 0; x < hd.width; ++x) {
                    int lx = x * screenGetWidth() / hd.width;
                    if (!hdWorldOwnerAt(indexed + ly * gSdlSurface->pitch + lx)) continue;
                    const size_t offset = static_cast<size_t>(y) * hd.width + x;
                    const double fraction = static_cast<double>(spec.numerator) / spec.denominator;
                    bool pixelBad = false;
                    for (int shift : { 0, 8, 16 }) {
                        const int reference = (normal.pixels[offset] >> shift) & 255;
                        const int actual = (hd.pixels[offset] >> shift) & 255;
                        // RGB6 maximum63 becomes RGB8 white252 in this renderer.
                        const double expected = endpoint ? static_cast<double>((classic.pixels[offset] >> shift) & 255)
                            : (spec.white ? reference * (1.0 - fraction) + 252.0 * fraction : reference * fraction);
                        const double error = std::abs(actual - expected);
                        maxError = std::max(maxError, error);
                        if (error > (endpoint ? 0.0 : 4.0)) pixelBad = true;
                    }
                    if (pixelBad) ++bad;
                    ++checked;
                }
            }
        }
        metrics << spec.name << ' ' << checked << ' ' << bad << ' ' << maxError << '\n';
        if (assertions) {
            report.check(valid && checked > 0 && bad == 0,
                std::string("HD smooth palette ") + spec.name + " without native-cell gain grid");
            if (endpoint) report.check(valid && hd.pixels == classic.pixels,
                "full white flash matches classic endpoint pixel exactly");
        }
    }
}

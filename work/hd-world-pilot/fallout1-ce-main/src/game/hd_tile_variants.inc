// Included inside hd_world_pilot.cc's private namespace.
// Sidecar pages avoid consuming the scarce 8-bit object ownership IDs.
void loadTileVariants()
{
    std::ifstream input("data/art/hd/world-pilot/tile-variants.tsv");
    if (!input.is_open()) return;
    size_t totalBytes = 0;
    for (const auto& asset : assets) totalBytes += asset.rgba.size();
    std::string line;
    for (int number = 0; number < 512 && std::getline(input, line); ++number) {
        if (line.empty() || line.size() > 256 || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string baseToken, slotToken, filename, extra;
        uint32_t baseId, slot;
        if (!(fields >> baseToken >> slotToken >> filename) || (fields >> extra)
            || !parseNumber(baseToken, baseId) || !parseNumber(slotToken, slot)
            || !baseId || baseId >= kAssetCapacity || slot < 1 || slot > 3
            || !safeAssetFilename(filename)) continue;
        Asset& base = assets[baseId];
        if (!base.floor || base.rgba.empty() || base.tileVariantPages[slot - 1]) continue;
        const size_t pageBytes = static_cast<size_t>(base.width) * base.height * 64;
        if (pageBytes > kMaximumAssetBytes - totalBytes) continue;
        const bool registered = std::any_of(fidAssets.begin(), fidAssets.end(), [baseId](const auto& entry) {
            return entry.second == static_cast<int>(baseId) && static_cast<uint32_t>(entry.first) == 0
                && ((entry.first >> 56) & 15) == 4;
        });
        if (!registered) continue;
        Asset candidate;
        const std::string path = "data/art/hd/world-pilot/" + filename;
        if (!loadAsset(candidate, path.c_str(), base.width, base.height)) continue;
        bool compatible = true;
        const int width = base.width * 4, height = base.height * 4;
        for (int y = 0; y < height && compatible; ++y) for (int x = 0; x < width; ++x) {
            const size_t uv = (static_cast<size_t>(y) * width + x) * 4;
            const bool edge = x < 12 || y < 12 || x >= width - 12 || y >= height - 12;
            if (candidate.rgba[uv + 3] != base.rgba[uv + 3]
                || (edge && std::memcmp(&candidate.rgba[uv], &base.rgba[uv], 4) != 0)) {
                compatible = false; break;
            }
        }
        if (!compatible) continue;
        base.tileVariantPages[slot - 1] = static_cast<int>(base.rgba.size() / pageBytes);
        base.rgba.insert(base.rgba.end(), candidate.rgba.begin(), candidate.rgba.end());
        totalBytes += pageBytes;
    }
}

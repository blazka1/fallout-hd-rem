// Isolated contact-shadow trial: exercise real SDL output and original owners.
void checkPlayerShadow(Report& report, const std::filesystem::path& output,
    const std::string& label, const std::string& filename)
{
    const auto mask = spriteMask(obj_dude);
    const auto* hdFrame = hdPlayerFrameAt(hdPlayerResolve(obj_dude));
    const bool shadowAvailable = hdFrame && hdFrame->poseShadowLoaded;
    const int flags = obj_dude->flags;
    obj_dude->flags |= OBJECT_HIDDEN;
    tile_refresh_display();
    const auto groundOwners = owners();
    obj_dude->flags = flags;
    hdPlayerSetShadowEnabled(false);
    const auto off = refreshCapture(true);
    const auto ownerBefore = owners();
    hdPlayerSetShadowEnabled(true);
    const auto on = capture(); // Toggle must also work without rebuilding owners.
    const int pitch = win_width(display_win), worldHeight = win_height(display_win);
    int changed = 0, brighter = 0, nonFloor = 0, distant = 0;
    for (int y = 0; y < on.height; ++y) for (int x = 0; x < on.width; ++x) {
        const size_t at = static_cast<size_t>(y) * on.width + x;
        if (on.pixels[at] == off.pixels[at]) continue;
        ++changed;
        const int lx = x * screenGetWidth() / on.width;
        const int ly = y * screenGetHeight() / on.height;
        if (ly >= worldHeight || !hdWorldAssetIsFloor(groundOwners[static_cast<size_t>(ly) * pitch + lx] >> 24)) ++nonFloor;
        if (ly < mask.y + mask.height * 2 / 3 - 4 || ly > mask.y + mask.height + 8) ++distant;
        for (int shift : {0, 8, 16})
            if (((on.pixels[at] >> shift) & 255) > ((off.pixels[at] >> shift) & 255)) ++brighter;
    }
    report.check(on.valid && off.valid && (shadowAvailable ? changed > 0 : changed == 0) && brighter == 0 && nonFloor == 0 && distant == 0
        && sameHud(on, off), label + " pose shadow darkens only nearby floor or safely falls back, preserves foreground and HUD ("
        + std::to_string(changed) + " pixels, nonfloor " + std::to_string(nonFloor) + ")");
    hdPlayerSetShadowEnabled(false);
    report.check(capture().pixels == off.pixels && owners() == ownerBefore,
        label + " shadow toggles reversibly without changing classic ownership");
    saveCrop(off, output / ("no-shadow-" + filename), obj_dude->tile);
    hdPlayerSetShadowEnabled(true);
    tile_refresh_display();
    report.check(capture().pixels == on.pixels, label + " repeated shadow draw has no accumulation");
}

void checkShadowApron(Report& report, const std::filesystem::path& output)
{
    const auto full = refreshCapture(true);
    const auto mask = spriteMask(obj_dude);
    // A dirty strip intersects the new shadow but none of the original FRM.
    Rect strip {mask.x - 16, mask.y + mask.height, mask.x + mask.width + 16, mask.y + mask.height + 8};
    tile_refresh_rect(&strip, obj_dude->elevation);
    report.check(capture().pixels == full.pixels, "shadow-only dirty strip matches full redraw beyond original FRM");
    const int flags = obj_dude->flags;
    // Use CE's actual visibility transition: it also invalidates the wall
    // transparency egg and the player's light footprint beyond sprite bounds.
    Rect dirty;
    const bool hidden = obj_turn_off(obj_dude, &dirty) == 0;
    tile_refresh_rect(&dirty, obj_dude->elevation);
    const auto hiddenPartial = capture(output / "hidden-partial.bmp");
    tile_refresh_display();
    report.check(hidden && capture(output / "hidden-full.bmp").pixels == hiddenPartial.pixels,
        "CE obj_turn_off clears shadow, wall transparency and light with ordinary dirty rectangle");
    obj_turn_on(obj_dude, &dirty);
    obj_dude->flags = flags;
    tile_refresh_display();
}

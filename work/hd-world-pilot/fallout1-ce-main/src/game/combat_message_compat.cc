#include "game/combat_message_compat.h"

#include <map>
#include <string>
#include <utility>

namespace fallout {

bool combatNormalizeLegacyMessages(MessageList* messages)
{
    MessageListItem probe = {};
    probe.num = 100;
    if (message_search(messages, &probe)) return true;
    probe.num = 513;
    if (!message_search(messages, &probe)
        || std::string(probe.text).find("%s %s") == std::string::npos) return true;

    // 1.0 supplies a separate was/were argument, whereas CE's later message
    // layout embeds it and separates player/male/female templates. Passing
    // CE's (name, damage) to 1.0's (%s, %s, %d) dereferences damage as a pointer.
    // Snapshot every string before replacing entries or reallocating the list.
    using Entry = std::pair<std::string, std::string>; // audio, text
    std::map<int, Entry> original;
    for (int i = 0; i < messages->entries_num; ++i) {
        const MessageListItem& entry = messages->entries[i];
        original.emplace(entry.num, Entry(entry.audio, entry.text));
    }
    auto normalized = original;
    const int miscIds[] = { 503, 504, 505, 519, 529, 530, 531, 532, 518 };
    for (int i = 0; i < 9; ++i) {
        auto source = original.find(miscIds[i]);
        if (source == original.end()) return false;
        normalized[100 + i] = source->second;
    }
    for (int id : { 506, 507, 508, 509 }) {
        if (original.find(id) == original.end()) return false;
    }
    const int templateIds[] = { 509, 510, 511, 512, 513, 514, 515,
        520, 521, 522, 523, 524, 525, 526, 527, 528, 533, 534 };
    for (int base : { 500, 600, 700 }) {
        const std::string& verb = original.at(base == 500 ? 507 : 508).second;
        for (int id : templateIds) {
            auto source = original.find(id);
            if (source == original.end()) return false;
            Entry entry = source->second;
            const bool hasVerb = id == 509 || (id >= 511 && id <= 513)
                || (id >= 520 && id <= 528);
            if (hasVerb) {
                size_t first = entry.second.find("%s");
                size_t second = first == std::string::npos ? first : entry.second.find("%s", first + 2);
                if (second == std::string::npos) return false;
                entry.second.replace(second, 2, verb);
            }
            normalized[base + id - 500] = entry;
            if (id == 509) {
                // CE uses a separate template when the intended target is You.
                size_t target = entry.second.rfind("%s");
                if (target == std::string::npos) return false;
                entry.second.replace(target, 2, original.at(506).second);
                normalized[base + 8] = entry;
            }
        }
        for (int bit = 0; bit <= 22; ++bit) {
            auto source = original.find(200 + bit);
            if (source == original.end()) return false;
            Entry entry = source->second;
            // Passive results need the subject's verb; active results such as
            // "lost next turn" already stand alone in the original messages.
            if (bit == 0 || bit == 1 || bit == 6 || bit == 7 || bit == 10 || bit == 22) {
                entry.second = verb + " " + entry.second;
            }
            normalized[base - 300 + bit] = entry;
        }
    }
    normalized[257] = normalized.at(207); // female player's critical death

    // Commit atomically. Original DAT/patch files and gameplay remain unchanged.
    MessageList replacement;
    message_init(&replacement);
    for (auto& pair : normalized) {
        MessageListItem entry { pair.first, pair.second.first.data(), pair.second.second.data() };
        if (!message_add(&replacement, &entry)) {
            message_exit(&replacement);
            return false;
        }
    }
    message_exit(messages);
    *messages = replacement;
    return true;
}

} // namespace fallout

#ifndef FALLOUT_GAME_COMBAT_MESSAGE_COMPAT_H_
#define FALLOUT_GAME_COMBAT_MESSAGE_COMPAT_H_

#include "game/message.h"

namespace fallout {

// Adapt the original English 1.0 message layout in memory. Later layouts pass
// through unchanged. Failure leaves the caller's message list untouched.
bool combatNormalizeLegacyMessages(MessageList* messages);

} // namespace fallout

#endif

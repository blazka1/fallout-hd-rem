#ifndef FALLOUT_GAME_HD_WORLD_PILOT_TEST_H_
#define FALLOUT_GAME_HD_WORLD_PILOT_TEST_H_

namespace fallout {

// Runs only in the isolated preview process after loading V13ENT.MAP.
int hdWorldPilotPreview(const char* directory);

// Actual presentation timings in the isolated preview process; no pixel readback.
int hdWorldPilotBenchmark(const char* directory);

} // namespace fallout

#endif

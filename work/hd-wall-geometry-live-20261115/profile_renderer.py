from pathlib import Path
import shutil
w=Path(__file__).resolve().parent
p=w/'source/src/game/hd_world_pilot.cc'
shutil.copy2(p,w/'before-profile.cc')
s=p.read_text()
s=s.replace('std::vector<unsigned char> presentedCaveOpacity;', 'std::vector<unsigned char> presentedCaveOpacity;\nstatic uint64_t wallProfileCalls[18] {};')
s=s.replace('    int dirtyLeft = width, dirtyTop = height, dirtyRight = 0, dirtyBottom = 0;', '''    const Uint64 profileStart=SDL_GetPerformanceCounter();
    std::fill(std::begin(wallProfileCalls),std::end(wallProfileCalls),0);
    unsigned int profileKinds[6] {};
    int dirtyLeft = width, dirtyTop = height, dirtyRight = 0, dirtyBottom = 0;''')
s=s.replace('            oldOwner = owner;', '''            if((owner>>24)==253) {
                const auto& p=cavePlacements[caveIndex(owner)];const auto t=caveTexel(owner);
                ++profileKinds[p.geometryCoverage[t]+(p.opacity[t]!=255?3:0)];
            }
            oldOwner = owner;''')
s=s.replace('    // Initial texture memory is undefined;', '''    if(const char* file=SDL_getenv("FALLOUT_HD_WALL_PROFILE")) {
        if(FILE* f=std::fopen(file,"a")) {
            std::fprintf(f,"%d %d %.3f",density,enabled,double(SDL_GetPerformanceCounter()-profileStart)*1000/SDL_GetPerformanceFrequency());
            for(auto count:profileKinds) std::fprintf(f," %u",count);
            for(auto count:wallProfileCalls) std::fprintf(f," %llu",static_cast<unsigned long long>(count));
            std::fprintf(f,"\\n");std::fclose(f);
        }
    }
    // Initial texture memory is undefined;''')
p.write_text(s)
p=w/'source/src/game/hd_cave_variety.inc'
shutil.copy2(p,w/'before-profile.inc')
s=p.read_text().replace('    unsigned int i=caveIndex(owner),t=caveTexel(owner);','    ++wallProfileCalls[std::min(depth,17)];\n    unsigned int i=caveIndex(owner),t=caveTexel(owner);')
p.write_text(s)

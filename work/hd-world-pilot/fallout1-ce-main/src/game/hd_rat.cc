#include "game/hd_rat.h"
#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <sstream>
#include <string>
#include <tuple>
#include "game/anim.h"
#include "game/gconfig.h"
#include "game/hd_world_pilot.h"
#include "game/map.h"
#include "game/object.h"
namespace fallout {
namespace {
constexpr const char* directory = "data/art/hd/critter-rat/";
constexpr int maximumFrames = 512;
bool initialized = false, enabled = true;
std::vector<HdRatFrame> frames;
std::map<std::tuple<int,int,int>,int> keys;
bool number(const std::string& token, int& value) {
    const auto r = std::from_chars(token.data(),token.data()+token.size(),value);
    return r.ec == std::errc() && r.ptr == token.data()+token.size();
}
uint32_t le32(const unsigned char* p) {
    return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
}
bool load(HdRatFrame& frame, const std::string& name) {
    // Native texel is 14 bits in the render owner; index is 10 bits.
    if (frame.width<1 || frame.height<1 || frame.width>128 || frame.height>128
        || frame.width*frame.height>=16384 || name.size()>40 || name.size()<6
        || name.substr(name.size()-5)!=".rgba" || name.find("..")!=std::string::npos
        || !std::all_of(name.begin(),name.end(),[](unsigned char c) {
            return (c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.';
        })) return false;
    FILE* file=fopen((std::string(directory)+name).c_str(),"rb");
    if (!file) return false;
    std::array<unsigned char,20> header {};
    bool ok=fread(header.data(),1,20,file)==20 && memcmp(header.data(),"F1HD",4)==0
        && le32(header.data()+4)==1 && le32(header.data()+8)==uint32_t(frame.width*4)
        && le32(header.data()+12)==uint32_t(frame.height*4) && le32(header.data()+16)==4;
    if (ok) {
        frame.rgba.resize(size_t(frame.width)*frame.height*64);
        ok=fread(frame.rgba.data(),1,frame.rgba.size(),file)==frame.rgba.size() && fgetc(file)==EOF;
        bool visible=false,clear=false;
        for (int y=0;ok && y<frame.height*4;++y) for(int x=0;x<frame.width*4;++x) {
            const auto alpha=frame.rgba[(size_t(y)*frame.width*4+x)*4+3];
            const auto blockAlpha=frame.rgba[(size_t(y/4*4)*frame.width*4+x/4*4)*4+3];
            ok=alpha==blockAlpha && (alpha==0 || alpha==255);
            visible|=alpha==255;clear|=alpha==0;
        }
        ok=ok && visible && clear;
    }
    fclose(file);
    if(!ok)frame.rgba.clear();
    return ok;
}
}
void hdRatInit() {
    if(initialized)return;
    initialized=true;
    int value=1;config_get_value(&game_config,"remaster","hd_rat",&value);enabled=value!=0;
    FILE* file=fopen((std::string(directory)+"registry.tsv").c_str(),"rb");
    if(!file)return;
    std::map<std::string,int> loaded;
    char line[512];
    for(int n=0;n<1024 && fgets(line,sizeof(line),file);++n) {
        if(!strchr(line,'\n')&&!feof(file)){int c;while((c=fgetc(file))!=EOF&&c!='\n'){}continue;}
        if(line[0]=='#')continue;
        std::istringstream fields(line);
        std::array<std::string,5> tokens;std::string name,extra;
        if(!(fields>>tokens[0]>>tokens[1]>>tokens[2]>>tokens[3]>>tokens[4]>>name)||(fields>>extra))continue;
        int a,d,f,w,h;
        if(!number(tokens[0],a)||!number(tokens[1],d)||!number(tokens[2],f)||!number(tokens[3],w)||!number(tokens[4],h)
            ||a<0||a>=64||d<0||d>=6||f<0||f>=64)continue;
        const auto key=std::make_tuple(a,d,f);
        if(keys.count(key))continue;
        auto found=loaded.find(name);int index=-1;
        if(found!=loaded.end()) {
            index=found->second;
            if(frames[index].width!=w||frames[index].height!=h)continue;
        } else if(frames.size()<maximumFrames) {
            HdRatFrame candidate;candidate.width=w;candidate.height=h;
            if(!load(candidate,name))continue;
            index=int(frames.size());frames.push_back(std::move(candidate));loaded[name]=index;
        }
        if(index>=0)keys.emplace(key,index);
    }
    fclose(file);
}
bool hdRatEnabled(){hdRatInit();return enabled;}
void hdRatSetEnabled(bool value){hdRatInit();enabled=value;}
int hdRatFind(int a,int d,int f){hdRatInit();auto it=keys.find({a,d,f});return it==keys.end()?-1:it->second;}
int hdRatResolve(const Object* object) {
    if(!hdRatEnabled()||!object||!hdWorldIsPilotMap()||FID_TYPE(object->fid)!=OBJ_TYPE_CRITTER
        ||(object->fid&0xFFF)!=24||(object->fid&0xF000)!=0||object->tile<0||object->tile>=40000
        ||object->elevation!=map_elevation||(object->flags&(OBJECT_HIDDEN|OBJECT_FLAG_0xFC000))!=0)return -1;
    // Exact native coverage permits CE's outline pass to remain on top of HD.
    return hdRatFind(FID_ANIM_TYPE(object->fid),object->rotation,object->frame);
}
int hdRatLoadedFrameCount(){hdRatInit();return int(frames.size());}
int hdRatRegisteredKeyCount(){hdRatInit();return int(keys.size());}
const HdRatFrame* hdRatFrameAt(int index){hdRatInit();return index>=0&&index<int(frames.size())?&frames[index]:nullptr;}
}

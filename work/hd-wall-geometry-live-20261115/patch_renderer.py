from pathlib import Path
P=Path(__file__).parent/'source/src/game'
f=P/'hd_cave_variety.inc';s=f.read_text()
assert 'geometryRgba' not in s
s=s.replace('std::vector<unsigned char> opacity;', 'std::vector<unsigned char> opacity;\n    std::vector<unsigned char> geometryRgba;')
s=s.replace('static bool caveVarietyEnabled = true;', 'static bool caveVarietyEnabled = true;\nstatic bool wallGeometryEnabled = true;')
s=s.replace('|| id == 252;','|| id == 252 || id == 253;')
s=s.replace('static bool sameUnder', '''static unsigned int caveIndex(uint32_t owner) { return (owner >> ((owner >> 24) == 253 ? 15 : 16)) & ((owner >> 24) == 253 ? 511 : 255); }
static unsigned int caveTexel(uint32_t owner) { return owner & ((owner >> 24) == 253 ? 32767 : 65535); }
static bool sameUnder''')
s=s.replace('const unsigned int i=(owner>>16)&255,t=owner&65535;', 'const unsigned int i=caveIndex(owner),t=caveTexel(owner);')
s=s.replace('unsigned int i=(owner>>16)&255,t=owner&65535;', 'unsigned int i=caveIndex(owner),t=caveTexel(owner);')
s=s.replace('|| !isCaveOwner(id) || w!=128', '|| id==253 || !isCaveOwner(id) || w!=128')
s=s.replace('return static_cast<int>(cavePlacements.size());', 'return static_cast<int>(std::count_if(cavePlacements.begin(),cavePlacements.end(),[](const auto& p){return p.assetId!=253;}));')
s=s.replace('const auto& p=cavePlacements[i];\n        if (o->id', 'const auto& p=cavePlacements[i];\n        if(p.assetId==253 && !wallGeometryEnabled) continue;\n        if (o->id')
s=s.replace('&& !assets[p.assetId].rgba.empty())', '&& (p.assetId==253 ? !p.geometryRgba.empty() : !assets[p.assetId].rgba.empty()))')
s=s.replace('((owner>>16)&255)==static_cast<unsigned int>(i)', 'caveIndex(owner)==static_cast<unsigned int>(i)')
s=s.replace('(uint32_t(caveDraw.frame)<<16)|texel', '(uint32_t(caveDraw.frame)<<(p.assetId==253?15:16))|texel')
s=s.replace('const auto& rgba=assets[p.assetId].rgba;size_t uv=(static_cast<size_t>(v)*512+u)*4;', 'const auto& rgba=p.assetId==253?p.geometryRgba:assets[p.assetId].rgba;\n    const int textureWidth=p.assetId==253?p.oldWidth*4:512;\n    size_t uv=(static_cast<size_t>(v)*textureWidth+u)*4;')
s+='\n#include "game/hd_wall_geometry.inc"\n'
f.write_text(s)
f=P/'hd_world_pilot.cc';s=f.read_text().replace('loadCaveVariety();','loadCaveVariety();\n    loadWallGeometry();');f.write_text(s)
f=P/'hd_world_pilot.h';s=f.read_text().replace('int hdWorldWallVariantCount();','int hdWorldWallVariantCount();\nint hdWorldWallGeometryCount();\nvoid hdWorldSetWallGeometryEnabled(bool enabled);\nbool hdWorldWallGeometryEnabled();');f.write_text(s)
f=P/'hd_world_pilot_test.cc';s=f.read_text()
s=s.replace('if(hdWorldCaveAssetForObject(o)==252) {replaced.insert(id);continue;}', 'if(hdWorldCaveAssetForObject(o)==252 || hdWorldCaveAssetForObject(o)==253) {replaced.insert(id);continue;}')
s=s.replace('explicit vault rock appearance','explicit connected wall geometry')
s=s.replace('for(auto* o:objects()) if(hdWorldCaveAssetForObject(o)) {assigned.push_back', 'for(auto* o:objects()) if(hdWorldCaveAssetForObject(o) && hdWorldCaveAssetForObject(o)!=253) {assigned.push_back')
s=s.replace('|| id == 250 || id == 252;', '|| id == 250 || id == 252 || id == 253;')
f.write_text(s)
print('Patched isolated renderer only')

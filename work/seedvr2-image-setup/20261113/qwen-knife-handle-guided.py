import importlib.util,sys
from pathlib import Path
p=Path(__file__).with_name('qwen-knife-handle.py');s=importlib.util.spec_from_file_location('handle',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=m.ROOT/'assets/generated/inventory-knife/qwen21-handle-fill-v6-20261113'
m.REFERENCE_OVERRIDE=m.OUT/'reference-guide.png'
m.PROMPT='''Finish the small filled-in brown patches on the underside of this knife handle. The lower grip has already been filled to indicate the intended solid silhouette. Keep those filled regions OPAQUE and blend their grain, shading and dark brown material smoothly into the adjacent grip. Remove the small vertical streaks or flat patch boundaries from the provisional fill. Refine the lower grip outline into one continuous, gently curved edge; no holes, missing chunks, bite marks, rectangular notches or torn edges. The entire brown grip between guard and pommel is solid material. Keep its current size, both golden fasteners, the upper edge and original overall contour.
Make no changes elsewhere: preserve the whole blade including its repaired tip, central groove, matte steel, existing small rust patches, rusty guard, silver pommel, lighting and framing. Keep the guard connected to the grip with no hole or gap. Do not add contrast, sharpening, gloss or more rust. One knife, same position and size, genuinely transparent surroundings. Only refine the local brown fill and smooth its lower boundary.'''
{'submit':m.submit,'collect':m.collect}[sys.argv[1]]()

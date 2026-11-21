"""Read original wheel and symmetric attachment mounts for each converted slot."""
import json,struct
import numpy as np
from inspect_assets import ROOT,cartypes,chunks,flatten
from extract_assets import payload,skip_words


def profiles(inventory_path=None):
    cars={car['name']:car for car in cartypes((ROOT/'GLOBAL/GLOBALB.BUN').read_bytes())};result={}
    for character in json.loads((inventory_path or ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
        slot=character['nfs_slot'];data=(ROOT/'CARS'/slot/'GEOMETRY.BIN').read_bytes();positions={0x9b971511:[],0x0ee87ec4:[]}
        for node in flatten(chunks(data)):
            if node['id']!='0x0013401a':continue
            raw=payload(data,node)
            for at in range(skip_words(raw),len(raw),80):
                key=struct.unpack_from('<I',raw,at)[0]
                if key in positions:positions[key].append(struct.unpack_from('<3f',raw,at+64))
        sides=[]
        for values in positions.values():
            if not values or not np.allclose(values,values[0],atol=1e-4):raise ValueError('Ambiguous side attachment coordinates')
            sides.append(values[0])
        wheels=[[w['longitudinal'],w['lateral'],w['height']] for w in cars[slot]['wheels']];values=np.array([*wheels,*sides],dtype='<f4')
        if values.shape!=(6,3) or not np.isfinite(values).all() or np.max(np.abs(values))>4:raise ValueError('Invalid vehicle attachment profile')
        result[character['id']]={'bytes':values.tobytes(),'slot':slot,'wheel':wheels,'side':sides,'cartype_offset':cars[slot]['offset'],'grounding_unverified':True}
    return result

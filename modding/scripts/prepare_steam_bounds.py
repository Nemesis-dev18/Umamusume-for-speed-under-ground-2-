"""Expand only active Corolla body bounds for the retargeted motion; stage, never install."""
import hashlib
import json
import struct
import numpy as np
from inspect_assets import ROOT,chunks,flatten
from extract_assets import geometry,payload

def prepare(source,minimum,maximum):
    result=bytearray(source);nodes={n['offset']:n for n in flatten(chunks(source))};changes=[]
    bodies=geometry(source,'_KIT00_BODY_')
    if {b['name'] for b in bodies}!={f'COROLLA_KIT00_BODY_{lod}' for lod in 'ABCD'}:raise ValueError('Unexpected body set')
    for mesh in bodies:
        leaves={n['id']:n for n in flatten(nodes[mesh['solid_offset']]['children'])}
        header=leaves['0x00134011'];ranges=leaves['0x00134b02'];raw=payload(source,ranges);lead=len(raw)%60
        active=[at for at in range(lead,len(raw),60) if struct.unpack_from('<I',raw,at+12)[0]]
        if len(active)!=1 or struct.unpack_from('<I',raw,active[0]+12)[0]!=len(mesh['indices']):raise ValueError('Unexpected active material range')
        for node,start in [(header,32),(ranges,active[0])]:
            for delta,values,operation in [(0,minimum,min),(16,maximum,max)]:
                for axis,value in enumerate(values):
                    at=node['payload']+start+delta+axis*4;old=struct.unpack_from('<f',source,at)[0];new=struct.pack('<f',operation(old,float(value)))
                    if source[at:at+4]!=new:result[at:at+4]=new;changes.append({'part':mesh['name'],'offset':at,'before':source[at:at+4].hex(),'after':new.hex()})
    if chunks(result)!=chunks(source):raise ValueError('Container layout changed')
    return bytes(result),changes

def main():
    report=json.loads((ROOT/'modding/animation-steam-retarget/retarget-report.json').read_text())
    target=ROOT/'CARS/COROLLA/GEOMETRY.BIN';backup=target.with_name('GEOMETRY.BIN.before-steam-motion.bak');source=(backup if backup.exists() else target).read_bytes()
    lower=np.array(report['minimum'])-.2;upper=np.array(report['maximum'])+.2;candidate,changes=prepare(source,lower,upper)
    (ROOT/'modding/staged-runtime/GEOMETRY-steam-motion.BIN').write_bytes(candidate)
    result={'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'bytes':len(candidate),'source_envelope_margin':.2,'minimum':lower.tolist(),'maximum':upper.tolist(),'fields':changes,'installed':False}
    (ROOT/'modding/steam-motion-bounds-plan.json').write_text(json.dumps(result,indent=2)+'\n');print('Staged body bounds:',len(changes),'four-byte fields;',result['after_sha256'])

if __name__=='__main__':main()

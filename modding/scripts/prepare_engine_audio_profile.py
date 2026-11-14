"""Compile public default audio tables into a strict data-only runtime signature."""
import configparser
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from inspect_assets import ROOT

REPO=ROOT/'modding/audio-tools/NFSU2CarSoundTuner'

def read(path):
    c=configparser.ConfigParser();c.read(path);return c

def main():
    data=REPO/'CarSoundData';engines=[];mapping=[]
    fields=[('UseDualGinsu','i'),('GinsuDecelID','i'),('AccelFromIdleID','i'),('MaxRPM','f'),('MinRPM','f'),('AEMSVol','i'),('GinsuAccelVol','i'),('AccelDeltaRPMThreshold','f'),('AEMSMixLRPM','f'),('GinsuMixLRPM','f'),('AEMSMixSRPM','f'),('GinsuMixSRPM','f'),('UnkFloat1','f'),('UnkFloat2','f'),('Unk2','i')]
    for i in range(43):
        c=read(data/'EngineData'/f'{i:02d}.ini')['EngineData'];words=[c.getint('CarID')]
        for name,kind in fields:
            value=c.getfloat(name) if kind=='f' else c.getint(name);words.append(struct.unpack('<I',struct.pack('<'+kind,value))[0])
        engines.append(words)
    paths=sorted((data/'CarDataMapping').glob('*.ini'))
    if [int(p.stem) for p in paths]!=list(range(len(paths))):raise ValueError('Noncontiguous mapping IDs')
    for path in paths:
        c=read(path)
        mapping.append([c[upgrade].getint(field) for upgrade in ['Stock','Street','Pro','Extreme'] for field in ['EngineData','ShiftPattern','TurboDataSet']])
    if any(3 in row[::3] for row in mapping):raise ValueError('Engine slot 3 is already used')
    if mapping[6][::3]!=[18,2,19,19]:raise ValueError('Unexpected Corolla mapping')
    header='/* Default numeric audio data from NFSU2CarSoundTuner; no game addresses or code. */\n#ifndef UMA_ENGINE_PROFILE_H\n#define UMA_ENGINE_PROFILE_H\n#include <stdint.h>\n'
    for name,rows in [('uma_engine_profile',engines),('uma_mapping_profile',mapping)]:
        header+=f'static const uint32_t {name}[{len(rows)}][{len(rows[0])}]={{\n'+''.join('{'+','.join(hex(x) for x in row)+'},\n' for row in rows)+'};\n'
    header+='#endif\n';(ROOT/'modding/runtime/uma_engine_profile.h').write_text(header)
    report={'source':'https://github.com/nlgxzef/NFSU2CarSoundTuner','commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'engines':len(engines),'mappings':len(mapping),'corolla_mapping':6,'unused_engine_slot':3,'engine_stride':76,'mapping_stride':48,'strategy':'Require unique exact match of all numeric defaults in writable main-image data; reject altered or unsupported profiles. No executable file or instruction patch.','installed':False}
    (ROOT/'modding/engine-audio-profile.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()

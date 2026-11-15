"""Silence native car samples without changing bank programs, metadata or sample lengths."""
import hashlib
import json
from pathlib import Path
import struct
from inspect_assets import ROOT
from read_ea_sound import abk_samples

def mute_gin(source):
    if len(source)<32 or source[:4]!=b'Gnsu':raise ValueError('Unsupported GIN header')
    a,b,samples,rate=struct.unpack_from('<4I',source,16);start=32+(a+b+2)*4;size=((samples+31)//32)*19
    if not samples or not 8000<=rate<=192000 or start+size>len(source):raise ValueError('GIN payload outside file')
    out=bytearray(source);out[start:start+size]=b'\0'*size
    return bytes(out),[{'offset':start,'bytes':size,'samples':samples,'codec':'EA-XAS v0; zero histories/filter/residuals'}]

def mute_abk(source):
    records=abk_samples(source);out=bytearray(source);ranges=[];headers=[]
    for row in records:
        # Locate the existing PT header from its native relative directory entry.
        entry=row['bank_base']+20+row['index']*4;at=entry+struct.unpack_from('<i',source,entry)[0];headers.append((at,row['end']))
    for row in records:
        t=row['tags']
        if row['platform']!=0 or t.get(128)!=2 or t.get(130,1)!=1 or t.get(160,10)!=10 or 131 in t:raise ValueError('Unsupported mechanical sample codec')
        samples=t.get(133,0);start=row['bank_base']+t.get(136,-1);at=start;raw_count=0
        if not 0<samples<=10000000 or start<row['bank_base']+20:raise ValueError('Invalid EA sample bounds')
        for _ in range((samples+27)//28):
            if at>=row['bank_end']:raise ValueError('Truncated EA-XA frame')
            raw=source[at]==238;size=61 if raw else 15
            if at+size>row['bank_end']:raise ValueError('EA-XA frame outside sample bank')
            if raw:out[at+1:at+size]=b'\0'*(size-1);raw_count+=1
            else:out[at:at+size]=b'\0'*size
            at+=size
        if any(start<end and at>begin for begin,end in headers):raise ValueError('Sample overlaps a PT header')
        ranges.append({'index':row['index'],'offset':start,'bytes':at-start,'samples':samples,'raw_pcm_frames':raw_count,'codec':'EA-XA v2; raw markers retained, silent histories/residuals'})
    if abk_samples(bytes(out))!=records:raise ValueError('Bank metadata changed')
    return bytes(out),ranges

def sources():
    files=[]
    for folder in ['ENGINE','SHIFTING','TURBO','SKIDS']:files.extend(sorted((ROOT/'SOUND'/folder).glob('*.abk')))
    files.extend(sorted((ROOT/'SOUND/ENGINE').glob('*.gin')));files.extend(sorted((ROOT/'SOUND/IG_GLOBAL').glob('ROADNOISE*.abk')))
    return files

def main():
    entries=[];base=ROOT/'modding/staged-runtime/mechanical-silence'
    for target in sources():
        backup=target.with_name(target.name+'.before-uma-silence.bak');source=(backup if backup.exists() else target).read_bytes()
        candidate,ranges=(mute_gin if target.suffix.lower()=='.gin' else mute_abk)(source)
        relative=target.relative_to(ROOT);path=base/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(candidate)
        entries.append({'target':str(relative),'candidate':str(path.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),'bytes':len(source),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'sample_ranges':ranges})
    report={'files':entries,'scope':'Native engine, engine sweetener, shifting, turbo, skids and road noise for all cars; original Uma footsteps remain character-only. Music, voices, general ambience and impacts untouched.','installed':False,'gameplay_verified':False}
    (ROOT/'modding/mechanical-silence-plan.json').write_text(json.dumps(report,indent=2)+'\n');print('Staged',len(entries),'mechanical banks/GIN files;',sum(len(x['sample_ranges']) for x in entries),'sample ranges; no game files replaced')

if __name__=='__main__':main()

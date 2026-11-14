"""Stage removal of shared car accessories by degenerating only triangle indices."""
import hashlib
import json
from inspect_assets import ROOT,chunks
from extract_assets import geometry

PARTS=('MIRRORS_BODY','MIRRORS_POST','MIRRORS_SUV','MIRRORS_HUMMER','SPOILER','SPOILER_HATCH','SPOILER_SUV','PLATES','EXHAUST','ROOF','BRAKES','AUDIO')

def prepare(source):
    meshes=geometry(source,'');out=bytearray(source);ranges=[]
    if not meshes:raise ValueError('Shared part file contains no supported meshes')
    for mesh in meshes:
        start=mesh['index_data_offset'];size=len(mesh['indices'])*2
        if start<0 or start+size>len(source) or len(mesh['indices'])%3:raise ValueError('Invalid triangle range')
        out[start:start+size]=b'\0'*size;ranges.append({'name':mesh['name'],'offset':start,'bytes':size,'triangles':len(mesh['indices'])//3})
    if chunks(out)!=chunks(source):raise ValueError('Chunk layout changed')
    return bytes(out),ranges

def main():
    root=ROOT/'modding/staged-runtime/shared-parts';root.mkdir(exist_ok=True);files=[]
    for part in PARTS:
        relative=f'CARS/{part}/GEOMETRY.BIN';target=ROOT/relative;backup=target.with_name('GEOMETRY.BIN.before-uma-parts.bak')
        source=(backup if backup.exists() else target).read_bytes();candidate,ranges=prepare(source)
        path=root/(part+'.BIN');path.write_bytes(candidate)
        files.append({'target':relative,'candidate':str(path.relative_to(ROOT)),'bytes':len(source),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'index_ranges':ranges})
    plan={'scope':'All cars: shared mirrors/spoilers/plates/exhaust/roof/brakes/trunk-audio geometry only; main car bodies preserved','method':'Set each triangle index to zero, preserving all vertices, material ranges, sizes and alignment','files':files,'installed':False}
    (ROOT/'modding/shared-parts-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('Staged',len(files),'files;',sum(len(x['index_ranges']) for x in files),'meshes; no game files replaced')

if __name__=='__main__':main()

"""Stage light meshes and flare markers removal for selectable cars, preserving wheels."""
import hashlib,json,struct
from inspect_assets import ROOT,cartypes,chunks,flatten
from extract_assets import geometry,payload,skip_words
from disable_car_effects import rename_markers,string_hash

LIGHT_MARKERS=('LEFT_HEADLIGHT','RIGHT_HEADLIGHT','CENTRE_HEADLIGHT','LEFT_BRAKELIGHT','RIGHT_BRAKELIGHT','CENTRE_BRAKELIGHT')


def prepare(source):
    existing=set()
    for node in flatten(chunks(source)):
        if node['id']!='0x0013401a':continue
        raw=payload(source,node);lead=skip_words(raw)
        if (len(raw)-lead)%80:raise ValueError('Partial marker')
        existing.update(struct.unpack_from('<I',raw,at)[0] for at in range(lead,len(raw),80))
    active=[name for name in LIGHT_MARKERS if string_hash(name) in existing]
    output,markers=rename_markers(source,active,())
    output=bytearray(output);indices=[]
    for token in ('HEADLIGHT','BRAKELIGHT'):
        for mesh in geometry(source,token):
            at=mesh['index_data_offset'];size=len(mesh['indices'])*2
            if at<0 or at+size>len(source) or size%6:raise ValueError('Invalid light mesh indices')
            output[at:at+size]=bytes(size)
            indices.append(dict(name=mesh['name'],offset=at,bytes=size))
    if chunks(source)!=chunks(output):raise ValueError('Container layout changed')
    return bytes(output),markers,indices


def main():
    global_data=(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes();rows=[];missing=[]
    for car in cartypes(global_data):
        if struct.unpack_from('<I',global_data,car['offset']+0x844)[0]!=0:continue
        target=ROOT/'CARS'/car['name']/'GEOMETRY.BIN'
        if not target.exists():
            if car['name'] not in {'CIVIC','RSX'}:raise FileNotFoundError(target)
            missing.append(car['name']);continue
        source=target.read_bytes();output,markers,indices=prepare(source)
        if output==source:continue
        relative=target.relative_to(ROOT);candidate=ROOT/'modding/staged-runtime/selectable-lights'/relative
        candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(output)
        rows.append(dict(target=str(relative),candidate=str(candidate.relative_to(ROOT)),backup=str(relative)+'.before-no-lights.bak',before_sha256=hashlib.sha256(source).hexdigest(),after_sha256=hashlib.sha256(output).hexdigest(),bytes=len(output),markers=markers,index_ranges=indices))
    plan=dict(files=rows,missing_regional_resources=missing,installed=False,scope='All present UsageType0 selectable cars: head/brake light meshes and flare marker names only. Body, wheels, collision and physics preserved.')
    (ROOT/'modding/selectable-lights-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Staged',len(rows),'car geometry files;',sum(len(r['index_ranges']) for r in rows),'light meshes; no installed geometry overwritten')

if __name__=='__main__':main()

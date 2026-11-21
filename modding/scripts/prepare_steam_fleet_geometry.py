"""Stage seven compact native containers and humanoid hulls; never install them."""
import hashlib,json,re,struct,subprocess
from pathlib import Path
import numpy as np
from inspect_assets import ROOT,chunks,flatten
from extract_assets import payload,skip_words
from fleet_carrier import carrier
from fleet_anchors import profiles
from prepare_character_collision import prepare as collision,LOWER,UPPER
from disable_car_effects import NAMES,rename_markers,string_hash
RLIB=Path('/home/nemesis/Documents/Codex/2026-11-13/tu-x20/work/modbuild/target/debug/deps/libgizmo_nfs-0396edd5db1643f5.rlib')


def solid_map(data):
    result={}
    for node in flatten(chunks(data)):
        if node['id']!='0x80134010':continue
        leaves={n['id']:n for n in flatten(node['children'])};header=payload(data,leaves['0x00134011']);key=struct.unpack_from('<I',header,16)[0]
        if key in result:raise ValueError('Duplicate solid hash')
        result[key]=(node,leaves,header)
    return result


def verify(source,candidate,identity,bounds,slot):
    before=solid_map(source);after=solid_map(candidate)
    if before.keys()!=after.keys():raise ValueError('Solid identities changed')
    bodies=0
    for key,(node,leaves,header) in after.items():
        old_node,old_leaves,old_header=before[key];name=max(re.findall(rb'[!-~]{4,}',header),key=len).decode();body='_BODY_' in name
        if body:bodies+=1
        if not name.startswith(slot+'_') or node['offset']%128:raise ValueError('Solid name/alignment')
        for identifier,leaf in leaves.items():
            if leaf.get('children'):continue
            if identifier in {'0x00000000','0x00134011','0x00134900','0x00134b01','0x00134b02','0x00134b03'}:continue
            if identifier not in old_leaves or payload(candidate,leaf)!=payload(source,old_leaves[identifier]):raise ValueError(f'Opaque solid leaf changed: {name}/{identifier}')
        allowed=np.zeros(len(header),bool);allowed[20:24]=True;allowed[32:44]=True;allowed[48:60]=True
        if body:allowed[64:128]=True
        if len(header)!=len(old_header) or np.any((np.frombuffer(header,'u1')!=np.frombuffer(old_header,'u1'))&~allowed):raise ValueError('Unknown solid header field changed')
        mh=payload(candidate,leaves['0x00134900']);mh=mh[skip_words(mh):];nv=struct.unpack_from('<I',mh,52)[0];nt=struct.unpack_from('<I',mh,36)[0]
        expected=(6,2) if body else (3,1)
        if (nv,nt)!=expected:raise ValueError('Native mesh counts')
        if struct.unpack_from('<I',header,20)[0]!=nt:raise ValueError('Solid triangle total')
        vb=leaves['0x00134b01'];at=vb['payload']+vb['size']-nv*36;vertices=candidate[at:at+nv*36]
        if at%128:raise ValueError('Vertex alignment')
        ib=leaves['0x00134b03'];index_at=ib['payload']+skip_words(payload(candidate,ib))
        if index_at%16 or struct.unpack_from('<'+'H'*(nt*3),candidate,index_at)!=tuple(range(nt*3)):raise ValueError('Index layout')
        if body:
            if vertices!=identity or not np.array_equal(np.array(struct.unpack_from('<16f',header,64)).reshape(4,4),np.eye(4)):raise ValueError('Carrier identity/orientation')
            if header[32:44]!=bounds[:12] or header[48:60]!=bounds[12:]:raise ValueError('Pose bounds')
        else:
            for v in range(nv):
                if struct.unpack_from('<3f',vertices,v*36)!=(0,0,0):raise ValueError('Original car surface remains')
        ranges=leaves['0x00134b02'];raw=payload(candidate,ranges);lead=len(raw)%60
        if (ranges['payload']+lead)%16:raise ValueError('Material range alignment')
        counts=[struct.unpack_from('<I',raw,a+12)[0] for a in range(lead,len(raw),60)]
        if sum(counts)!=nt*3 or sum(n>0 for n in counts)!=1:raise ValueError('Material ranges do not tile carrier')
    if bodies!=20:raise ValueError('Not all kits/LODs replaced')
    tree=chunks(candidate);nodes=flatten(tree);info=next(n for n in nodes if n['id']=='0x00134002');off,size=struct.unpack_from('<II',candidate,info['payload']+104)
    col=next(n for n in tree if n['id']=='0x80034020');oldcol=next(n for n in chunks(source) if n['id']=='0x80034020')
    if off!=col['offset'] or off%64 or size!=col['size']+8 or payload(source,oldcol)!=payload(candidate,col):raise ValueError('Collision relocation/payload')
    records=0
    for node in nodes:
        if node['id']!='0x00134004':continue
        raw=payload(candidate,node)
        if len(raw)%24:raise ValueError('Partial directory record')
        for at in range(0,len(raw),24):
            key,offset,length,duplicate,a,b=struct.unpack_from('<6I',raw,at)
            if a or b or length!=duplicate or key not in after or after[key][0]['offset']!=offset or after[key][0]['size']+8!=length:raise ValueError('Solid directory relocation')
            records+=1
    if records!=len(after):raise ValueError('Incomplete directory')
    return {'solids':len(after),'body_carriers':bodies,'hidden_original_parts':len(after)-bodies,'directory_records':records,'collision_relocated':True,'opaque_leaves_preserved':True,'bytes':len(candidate)}


def main(inventory_path=None):
    if hashlib.sha256(RLIB.read_bytes()).hexdigest()!='03a5461701f4f86a251cba6e0e0725d504cfd4ef8ee50bd236af0282e9c4aa0f':raise ValueError('Unreviewed gizmo-nfs library')
    subprocess.run(['rustc','--edition=2021','-O',str(ROOT/'modding/runtime/prepare_fleet_geometry.rs'),'--extern',f'gizmo_nfs={RLIB}','-L',f'dependency={RLIB.parent}','-o',str(ROOT/'modding/runtime/prepare-fleet-geometry')],check=True,cwd=ROOT)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(ROOT/'modding/runtime/fleet_bounds.c'),'-lm','-o',str(ROOT/'modding/runtime/test-build/fleet-bounds')],check=True,cwd=ROOT)
    rows=[];anchors=profiles(inventory_path)
    for character in json.loads((inventory_path or ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
        identifier=character['id'];slot=character['nfs_slot'];target=ROOT/'CARS'/slot/'GEOMETRY.BIN';source=target.read_bytes();folder=ROOT/'modding/staged-runtime/fleet'/str(identifier);folder.mkdir(parents=True,exist_ok=True);identity=carrier(identifier);(folder/'carrier.bin').write_bytes(identity)
        (folder/'anchors.bin').write_bytes(anchors[identifier]['bytes'])
        (folder/'anchors.json').write_text(json.dumps({k:v for k,v in anchors[identifier].items() if k!='bytes'},indent=2)+'\n')
        previous=folder/'geometry.json';output=folder/'GEOMETRY.BIN'
        if previous.exists() and output.exists():
            row=json.loads(previous.read_text())
            if row['before_sha256']==hashlib.sha256(source).hexdigest() and row['after_sha256']==hashlib.sha256(output.read_bytes()).hexdigest():
                rows.append(row);print(slot,'retained verified staged container',flush=True);continue
        model=ROOT/'modding/uma-steam/fleet'/str(identifier)/'runtime/model-atlas.umab';receipt=json.loads(model.with_name('atlas.json').read_text())
        if hashlib.sha256(model.read_bytes()).hexdigest()!=receipt['model_sha256']:raise ValueError('Stale native model')
        sampled=subprocess.run([str(ROOT/'modding/runtime/test-build/fleet-bounds'),str(model)],check=True,cwd=ROOT,capture_output=True);bounds=sampled.stdout
        if len(bounds)!=24:raise ValueError('Bounds result length')
        (folder/'bounds.bin').write_bytes(bounds);built=subprocess.run([str(ROOT/'modding/runtime/prepare-fleet-geometry'),slot,str(identifier)],check=True,cwd=ROOT,capture_output=True);raw=built.stdout;verified=verify(source,raw,identity,bounds,slot)
        scale=character['height_cm']/162;candidate,hulls,ranges=collision(raw,slot,LOWER*scale,UPPER*scale)
        hashes=set()
        for node in flatten(chunks(candidate)):
            if node['id']=='0x0013401a':
                data=payload(candidate,node);hashes.update(struct.unpack_from('<I',data,a)[0] for a in range(skip_words(data),len(data),80))
        candidate,markers=rename_markers(candidate,[name for name in (*NAMES,'CENTRE_HEADLIGHT') if string_hash(name) in hashes],())
        allowed=np.zeros(len(raw),bool)
        for r in ranges:allowed[r['offset']:r['offset']+r['bytes']]=True
        for r in markers:allowed[r['offset']:r['offset']+4]=True
        if len(raw)!=len(candidate) or np.any((np.frombuffer(raw,'u1')!=np.frombuffer(candidate,'u1'))&~allowed):raise ValueError('Unplanned collider/effect change')
        if target.read_bytes()!=source:raise ValueError('Source changed during staging')
        output=folder/'GEOMETRY.BIN';output.write_bytes(candidate);(folder/'build.log').write_text((sampled.stderr+built.stderr).decode())
        row={'id':identifier,'slot':slot,'target':str(target.relative_to(ROOT)),'candidate':str(output.relative_to(ROOT)),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'bytes_before':len(source),'bytes_after':len(candidate),'verification':verified,'bounds':struct.unpack('<6f',bounds),'collision_hulls':hulls,'collision_point_ranges':ranges,'disabled_markers':markers,'installed':False};rows.append(row)
        (folder/'geometry.json').write_text(json.dumps(row,indent=2)+'\n');print(slot,len(source),'->',len(candidate),'bytes;',len(hulls),'humanoid hulls',flush=True)
    (ROOT/('modding/diamond-geometry-plan.json' if inventory_path else 'modding/fleet-geometry-plan.json')).write_text(json.dumps({'characters':rows,'installed':False,'scope':'Staging only:20 carriers per car, original native surfaces collapsed, collision hulls scaled; no active resource overwritten'},indent=2)+'\n')

if __name__=='__main__':main()

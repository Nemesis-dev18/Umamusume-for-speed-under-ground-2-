"""Build a geometry candidate in memory and save only a review report, never game bytes."""
import hashlib
import struct
import subprocess
from inspect_assets import ROOT,chunks,flatten,data_path,save_json
from extract_assets import geometry,payload

SOURCE_HASH='cedf717c16c342b449c32e312351bd2f93d21533446b9501488dd0b5a3664389'

def reviewed_source():
    for relative in ('CARS/COROLLA/GEOMETRY.BIN','CARS/COROLLA/GEOMETRY.BIN.before-runtime.bak'):
        path=data_path(relative)
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==SOURCE_HASH:return path
    raise ValueError('Reviewed prototype source or exact backup required')

def verify_compaction(original,raw):
    oldtree=chunks(original);newtree=chunks(raw)
    oldmeshes={m['asset_hash']:m for m in geometry(original,'COROLLA_')}
    newmeshes={m['asset_hash']:m for m in geometry(raw,'COROLLA_')}
    if oldmeshes.keys()!=newmeshes.keys():raise ValueError('Part names changed')
    oldnodes={n['offset']:n for n in flatten(oldtree)}
    newnodes={n['offset']:n for n in flatten(newtree)}
    edited_ids={'0x00134011','0x00134900','0x00134b01','0x00134b02','0x00134b03'}
    changes=[]
    for name,old in oldmeshes.items():
        new=newmeshes[name]
        if old['name']!=new['name']:raise ValueError('Display name changed')
        oldsolid=oldnodes[old['solid_offset']];newsolid=newnodes[new['solid_offset']]
        oldleaves=[n for n in flatten(oldsolid.get('children',[])) if not n.get('children') and n['id'] not in edited_ids and n['id']!='0x00000000']
        newleaves=[n for n in flatten(newsolid.get('children',[])) if not n.get('children') and n['id'] not in edited_ids and n['id']!='0x00000000']
        if len(oldleaves)!=len(newleaves):raise ValueError('Unknown leaf set changed')
        for before,after in zip(oldleaves,newleaves):
            if before['id']!=after['id'] or payload(original,before)!=payload(raw,after):raise ValueError('Opaque solid data changed')
        collapsed=all(all(v==0 for v in p) for p in old['positions'])
        if collapsed:
            if len(new['positions'])!=3 or len(new['indices'])!=3 or any(any(v!=0 for v in p) for p in new['positions']):raise ValueError(f'Invalid compact degenerate mesh: {name}; {len(new["positions"])} vertices, {len(new["indices"])} indices')
            changes.append({'asset_hash':name,'part':old['name'],'old_offset':old['solid_offset'],'new_offset':new['solid_offset'],'vertices_before':len(old['positions']),'vertices_after':3,'triangles_before':len(old['indices'])//3,'triangles_after':1})
        else:
            before=old['vertex_data_offset'];after=new['vertex_data_offset'];length=len(old['positions'])*old['stride']
            if original[before:before+length]!=raw[after:after+length]:raise ValueError('Visible vertex records changed')
            for key in ('positions','normals','uv','indices','markers','transform','material_runs'):
                if old[key]!=new[key]:raise ValueError(f'Visible mesh changed: {name}/{key}')
        if old['markers']!=new['markers'] or old['transform']!=new['transform']:raise ValueError('Anchors changed')
    records_checked=0
    for n in flatten(newtree):
        if n['id']=='0x80134010' and n['offset']%128:raise ValueError('Solid alignment')
        if n['id']=='0x00134004':
            records=payload(raw,n)
            if len(records)%24:raise ValueError('Partial solid directory')
            for at in range(0,len(records),24):
                key,offset,size1,size2,a,b=struct.unpack_from('<6I',records,at)
                if a or b or size1!=size2 or offset+size1>len(raw):raise ValueError('Invalid directory record')
                tag,size=struct.unpack_from('<2I',raw,offset)
                if tag!=0x80134010 or size+8!=size1:raise ValueError('Directory relocation failed')
                solid_header=next(x for x in flatten(chunks(raw,offset,offset+size1)) if x['id']=='0x00134011')
                if struct.unpack_from('<I',raw,solid_header['payload']+16)[0]!=key:raise ValueError('Directory identity mismatch')
                records_checked+=1
    if records_checked!=len(oldmeshes):raise ValueError('Solid directory count mismatch')
    info=next(n for n in flatten(newtree) if n['id']=='0x00134002')
    off,size=struct.unpack_from('<2I',raw,info['payload']+104)
    if off%64 or off+size>len(raw) or struct.unpack_from('<2I',raw,off)!=(0x80034020,size-8):raise ValueError('Collision relocation failed')
    oldcol=next(n for n in oldtree if n['id']=='0x80034020')
    if payload(original,oldcol)!=raw[off+8:off+size]:raise ValueError('Collision payload changed')
    return {'source':'CARS/COROLLA/GEOMETRY.BIN','source_sha256':hashlib.sha256(original).hexdigest(),'result_sha256':hashlib.sha256(raw).hexdigest(),'bytes_before':len(original),'bytes_after':len(raw),'collapsed_solids_compacted':len(changes),'vertices_before':sum(len(m['positions']) for m in oldmeshes.values()),'vertices_after':sum(len(m['positions']) for m in newmeshes.values()),'solid_directory_records_verified':records_checked,'collision_pointer_before':oldcol['offset'],'collision_pointer_after':off,'collision_payload_unchanged':True,'noncollapsed_geometry_unchanged':True,'visible_vertex_records_unchanged':True,'other_solid_leaf_payloads_unchanged':True,'part_names_markers_transforms_preserved':True,'installed':False,'binary_saved':False,'approval_required':True,'limits':'Does not prove race visibility or fix body-kit selection, material bounds, running integration or residual shared wheels. Diagnostic candidate only.','changes':changes}

def main():
    source=reviewed_source();original=source.read_bytes()
    if hashlib.sha256(original).hexdigest()!=SOURCE_HASH:raise ValueError('Expected reviewed prototype source')
    build=subprocess.run([str(ROOT/'modding/runtime/compact-hidden-dry-run'),str(source.relative_to(ROOT))],cwd=ROOT,stdout=subprocess.PIPE,check=True,timeout=120)
    report=verify_compaction(original,build.stdout)
    if source.read_bytes()!=original:raise ValueError('Source changed during planning')
    save_json('hidden-compaction-plan.json',report)
    print({k:v for k,v in report.items() if k!='changes'})

if __name__=='__main__':main()

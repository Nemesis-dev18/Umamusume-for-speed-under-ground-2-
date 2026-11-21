"""Stage omitted native garment support metadata, preserving source values. No installation."""
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    source=ROOT/'modding/uma-steam/secondary-native'
    inventory=json.loads((source/'structural-summary.json').read_text())
    out=ROOT/'modding/staged-runtime/native-garment-support';out.mkdir(exist_ok=True)
    summary=[]
    for character in inventory:
        ident=character['id'];model=(ROOT/f'modding/runtime/fleet/{ident}/model.umab').read_bytes()
        nv,_,nb=struct.unpack_from('<3I',model,8)
        metadata=ROOT/('modding/staged-runtime/diamond/model.json' if ident==1067 else f'modding/staged-runtime/fleet-secondary/{ident}/model.json')
        names=json.loads(metadata.read_text())['bone_names'];assert len(names)==nb
        counts=Counter(names);remap={name:i for i,name in enumerate(names) if counts[name]==1}
        source_names={node.get('name') for node in json.loads((ROOT/f'modding/uma-steam/fleet/{ident}/source.gltf').read_text())['nodes']}
        positions=[struct.unpack_from('<3f',model,44+nv*60+16*b) for b in range(nb)]
        links=[];skirts=[];raw_sources=[]
        for asset in character['assets']:
            if not (asset['logical'].endswith('_cloth00') or asset.get('skirt')):continue
            raw=(source/(asset['hash']+'.json')).read_bytes();raw_sources.append({'logical':asset['logical'],'sha256':hashlib.sha256(raw).hexdigest()})
            for obj in json.loads(raw):
                if obj['type']!='MonoBehaviour':continue
                tree=obj.get('tree',{})
                if asset['logical'].endswith('_cloth00'):
                    for link in tree.get('ConnectedBoneList',[]):
                        a,b=remap[link['Bone1']],remap[link['Bone2']]
                        intensity=float(link['Intensity']);assert a!=b and math.isfinite(intensity) and 0<=intensity<=1
                        length=math.dist(positions[a],positions[b]);assert .0001<length<2
                        links.append({'bone_a':a,'bone_b':b,'name_a':link['Bone1'],'name_b':link['Bone2'],'rest_distance_m':length,'intensity':intensity,'is_fold':bool(link['IsFold']),'source':asset['logical']})
                if '_skirtBone' in tree:
                    rows=[]
                    for entry in tree['_skirtBone']:
                        a,b=remap.get(entry['_rootBoneName']),remap.get(entry['_childBoneName'])
                        if a is not None and b is not None:assert a!=b
                        reason=None if a is not None and b is not None else 'bone_absent_from_source' if entry['_rootBoneName'] not in source_names or entry['_childBoneName'] not in source_names else 'bone_not_unambiguously_exported'
                        rows.append({'root_bone':a,'child_bone':b,'resolved':a is not None and b is not None,'unresolved_reason':reason,'native':entry})
                    fields={k:v for k,v in tree.items() if k not in ('m_GameObject','m_Enabled','m_Script','m_Name','_skirtBone')}
                    skirts.append({'source':asset['logical'],'native_parameters':fields,'panels':rows})
        report={'character_id':ident,'scope':'Omitted original connections/skirt controller metadata only. Rest distances use active UMAB bind coordinates; native skirt parameters are retained raw and have not been converted to runtime units/behavior. Not a solver-equivalence claim.','source_model_sha256':hashlib.sha256(model).hexdigest(),'source_json':raw_sources,'base_cloth_connections':links,'skirt_controllers':skirts,'runtime_integrated':False,'accepted_for_game':False}
        (out/f'{ident}.json').write_text(json.dumps(report,indent=2)+'\n')
        summary.append({'id':ident,'connections':len(links),'fold_connections':sum(l['is_fold'] for l in links),'skirt_variants':len(skirts),'panel_counts':[len(s['panels']) for s in skirts],'unresolved_panels':[sum(not p['resolved'] for p in s['panels']) for s in skirts]})
    assert len(summary)==8
    (out/'inventory.json').write_text(json.dumps({'scope':'Read-only extraction to staged metadata; active files unchanged.','characters':summary,'runtime_integrated':False},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()

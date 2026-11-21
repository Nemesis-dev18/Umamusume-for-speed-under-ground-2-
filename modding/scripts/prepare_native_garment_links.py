"""Pack preserved original links into standalone staged UMALv1 data; never install."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    folder=ROOT/'modding/staged-runtime/native-garment-support';rows=[]
    for path in sorted(folder.glob('*.json')):
        if not path.stem.isdecimal():continue
        report=json.loads(path.read_text());ident=report['character_id'];model=(ROOT/f'modding/runtime/fleet/{ident}/model.umab').read_bytes()
        assert hashlib.sha256(model).hexdigest()==report['source_model_sha256']
        bones=struct.unpack_from('<I',model,16)[0];links=report['base_cloth_connections'];assert len(links)<=256
        data=struct.pack('<4s3I',b'UMAL',1,bones,len(links))
        for link in links:data+=struct.pack('<HHffI',link['bone_a'],link['bone_b'],link['rest_distance_m'],link['intensity'],int(link['is_fold']))
        assert len(data)==16+len(links)*16
        target=folder/f'{ident}.umal';target.write_bytes(data)
        rows.append({'id':ident,'candidate':str(target.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'links':len(links),'fold_links_unsupported':sum(l['is_fold'] for l in links),'installed':False})
    assert len(rows)==8
    (folder/'link-candidates.json').write_text(json.dumps({'scope':'Staged UMALv1 only; runtime does not discover these files. Fold links are preserved but rejected by experimental integrator.','files':rows,'installed':False},indent=2)+'\n')
    print([(r['id'],r['links'],r['fold_links_unsupported']) for r in rows])


if __name__=='__main__':main()

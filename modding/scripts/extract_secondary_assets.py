"""Read cached native secondary-motion bundles; never fetch or modify Steam data."""
import hashlib,importlib.util,json,sys,subprocess
from pathlib import Path
import extract_uma_fleet as f

def main(inventory_path=None):
    out=f.WORK/'secondary-native';out.mkdir(exist_ok=True)
    helper=f.verify_reader()
    spec=importlib.util.spec_from_file_location('secondary_decoder',helper);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
    db=f.apsw.Connection(str(f.WORK/'meta.snapshot'),flags=f.apsw.SQLITE_OPEN_READONLY)
    db.pragma('cipher','chacha20');db.pragma('cipher_page_size',4096);db.pragma('hexkey',d.get_db_hex_key('global'))
    fleet=json.loads((inventory_path or f.ROOT/'modding/fleet-source-inventory.json').read_text());report=json.loads((out/'inventory.json').read_text()) if inventory_path and (out/'inventory.json').exists() else {'characters':[],'bundles':{}};report.update(reader_revision=f.REV,reader_source_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),metadata_snapshot_sha256=hashlib.sha256((f.WORK/'meta.snapshot').read_bytes()).hexdigest());incoming={c['id'] for c in fleet['characters']};report['characters']=[c for c in report['characters'] if c['id'] not in incoming]
    for ch in fleet['characters']:
        entry={'id':ch['id'],'parts':{}};report['characters'].append(entry)
        for part in ch['parts']:
            if part['part'] not in ('body','head','tail'):continue
            prefix=part['logical'].rsplit('/',1)[0]+'/clothes/'
            rows=list(db.execute('SELECT n,h,e FROM a WHERE n LIKE ? ORDER BY n',(prefix+'%',)))
            entry['parts'][part['part']]=[{'logical':n,'hash':h,'cached':(f.SOURCE/'dat'/h[:2]/h).is_file()} for n,h,k in rows]
            for n,h,k in rows:
                if h in report['bundles']:continue
                assert h.isalnum() and len(h)==32
                src=f.SOURCE/'dat'/h[:2]/h
                if not src.is_file():report['bundles'][h]={'logical':n,'cached':False};continue
                before=src.stat();assert 0<before.st_size<256*1024*1024
                raw=src.read_bytes();decoded=bytes(d.decrypt_bundle(bytearray(raw),key=k,base_keys=d.ASSET_BASE_KEYS_JAPAN))
                assert decoded.startswith(b'UnityFS\0')
                after=src.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
                (out/(h+'.unity3d')).write_bytes(decoded)
                env=f.UnityPy.load(decoded);objects=[]
                for obj in env.objects:
                    if obj.type.name not in ('MonoBehaviour','MonoScript','GameObject','Transform'):continue
                    try:tree=obj.read_typetree();objects.append({'type':obj.type.name,'path_id':obj.path_id,'tree':tree})
                    except Exception as exc:objects.append({'type':obj.type.name,'path_id':obj.path_id,'error':str(exc)})
                (out/(h+'.json')).write_text(json.dumps(objects,indent=2,allow_nan=False)+'\n')
                report['bundles'][h]={'logical':n,'cached':True,'source_sha256':hashlib.sha256(raw).hexdigest(),'decoded_sha256':hashlib.sha256(decoded).hexdigest(),'objects':len(objects)}
    db.close();(out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    summary=[]
    for ch in report['characters']:
        raw=json.loads((f.WORK/'fleet'/str(ch['id'])/'raw-model.json').read_text())
        names={o['data'].get('m_Name') for o in raw['objects'] if o['type']=='GameObject'}
        entries=[]
        for part,assets in ch['parts'].items():
            for asset in assets:
                if not asset['cached']:continue
                objects=json.loads((out/(asset['hash']+'.json')).read_text())
                for obj in objects:
                    if obj['type']!='MonoBehaviour':continue
                    tree=obj.get('tree',{});chains=tree.get('springParam',[])
                    nodes=[node for root in chains for node in [root]+root.get('_childElements',[])]
                    entries.append({'part':part,'logical':asset['logical'],'hash':asset['hash'],'chains':[[n['_boneName'] for n in [root]+root.get('_childElements',[])] for root in chains], 'node_count':len(nodes),'missing_model_bones':sorted({n['_boneName'] for n in nodes}-names),'ranges':{k:[min(n[k] for n in nodes),max(n[k] for n in nodes)] for k in ('_stiffnessForce','_dragForce','_gravity','_collisionRadius') if nodes},'colliders':tree.get('collisionParam',[]),'skirt':tree if '_skirtBone' in tree else None,'nodes':nodes})
        summary.append({'id':ch['id'],'assets':entries})
    (out/'structural-summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    assert incoming<={c['id'] for c in report['characters']} and all(b['cached'] for b in report['bundles'].values())
    assert all(not o.get('error') for h in report['bundles'] for o in json.loads((out/(h+'.json')).read_text()))
    print('Decoded',len(report['bundles']),'bundles; all type trees and character summaries verified')
if __name__=='__main__':main()

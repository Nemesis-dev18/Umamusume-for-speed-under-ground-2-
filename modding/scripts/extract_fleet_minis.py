"""Extract cached mini-prefab dependencies for local badge authoring only."""
import hashlib,importlib.util,json,subprocess
from extract_uma_fleet import ROOT,WORK,SOURCE,REV,apsw,UnityPy


def main():
    repo=WORK/'tools/UmaExporter';helper=repo/'src/core/decryptor.py'
    if helper.read_bytes()!=subprocess.check_output(['git','-C',str(repo),'show',REV+':src/core/decryptor.py']):raise ValueError('Reader source mismatch')
    spec=importlib.util.spec_from_file_location('mini_reader',helper);decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    db=apsw.Connection(str(WORK/'meta.snapshot'),flags=apsw.SQLITE_OPEN_READONLY);db.pragma('cipher','chacha20');db.pragma('cipher_page_size',4096);db.pragma('hexkey',decoder.get_db_hex_key('global'))
    destination=WORK/'mini-bundles';destination.mkdir(exist_ok=True);receipts={};reports=[]
    for character in json.loads((ROOT/'modding/fleet-mini-inventory.json').read_text())['characters']:
        dependencies={}
        face={'logical':'3d/chara/mini/head/mchr0001_00/pfb_mchr0001_00_face0'}
        for prefab in [*character['selected_prefabs'],face]:
            rows=list(db.execute('SELECT i FROM a WHERE n=?',(prefab['logical'],)))
            if len(rows)!=1:raise ValueError('Ambiguous mini prefab')
            for name,hashed,key in db.execute("WITH RECURSIVE deps(id) AS (VALUES(?) UNION SELECT r.t FROM r JOIN deps ON r.f=deps.id WHERE r.d!='0') SELECT a.n,a.h,a.e FROM deps JOIN a ON a.i=deps.id WHERE a.h IS NOT NULL AND a.h!=''",(rows[0][0],)):dependencies[hashed]=(name,key)
        for prefix in (f"3d/chara/mini/head/mchr{character['id']}_00/textures/",'3d/chara/mini/head/mchr0001_00/textures/tex_mchr0001_00_face0_'):
            for name,hashed,key in db.execute("SELECT n,h,e FROM a WHERE n LIKE ? AND h!=''",(prefix+'%',)):
                if (SOURCE/'dat'/hashed[:2]/hashed).is_file():dependencies[hashed]=(name,key)
        paths=[]
        for hashed,(name,key) in dependencies.items():
            if not hashed.isalnum():raise ValueError('Unsafe asset filename')
            source=SOURCE/'dat'/hashed[:2]/hashed;target=destination/(hashed+'.unity3d');before=source.stat()
            if not 0<before.st_size<=256*1024*1024:raise ValueError('Bundle outside size bound')
            original=source.read_bytes();decoded=bytes(decoder.decrypt_bundle(bytearray(original),key=key,base_keys=decoder.ASSET_BASE_KEYS_JAPAN))
            if not decoded.startswith(b'UnityFS\0'):raise ValueError('Invalid decoded bundle')
            if target.exists() and target.read_bytes()!=decoded:raise ValueError('Conflicting extraction')
            if not target.exists():target.write_bytes(decoded)
            after=source.stat()
            if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('Steam source changed')
            receipts[hashed]={'logical':name,'source_sha256':hashlib.sha256(original).hexdigest(),'decoded_sha256':hashlib.sha256(decoded).hexdigest(),'source_unchanged':True};paths.append(str(target))
        env=UnityPy.load(*paths);meshes=[];textures=[]
        for obj in env.objects:
            if obj.type.name not in ('Mesh','Texture2D'):continue
            tree=obj.read_typetree();entry={'name':tree.get('m_Name'),'path_id':obj.path_id}
            if obj.type.name=='Mesh':entry['vertices']=tree.get('m_VertexData',{}).get('m_VertexCount');meshes.append(entry)
            else:entry.update(width=tree.get('m_Width'),height=tree.get('m_Height'));textures.append(entry)
        if not meshes or not textures:raise ValueError('Mini dependencies incomplete')
        reports.append({'id':character['id'],'name':character['name'],'bundles':sorted(dependencies),'meshes':meshes,'textures':textures,'rendered':False});print(character['name'],len(dependencies),'bundles;',len(meshes),'meshes',flush=True)
        (destination/'inventory.json').write_text(json.dumps({'characters':reports,'reader_revision':REV,'receipts':receipts,'steam_modified':False,'game_integrated':False},indent=2)+'\n')
    db.close()

if __name__=='__main__':main()

"""Copy/decode only cached character dependencies into the isolated project."""
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'modding/uma-steam'
SOURCE=Path('/home/nemesis/.local/share/Steam/steamapps/common/UmamusumePrettyDerby/UmamusumePrettyDerby_Data/Persistent')
REV='dca091dad2947d13f99a0510bcccdec82941df0c'
sys.path.insert(0,str(WORK/'python-deps'))
import apsw
import UnityPy


def verify_reader():
 helper=WORK/'tools/UmaExporter/src/core/decryptor.py'
 if hashlib.sha256(helper.read_bytes()).hexdigest()!='871745184e71f1d780473d1215ec797a1e3cc174838f6c9163673f65188904ea' or helper.read_bytes()!=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(helper.relative_to(ROOT))]):raise ValueError('Vendored reader source changed')
 return helper

def main(inventory_path=None):
    helper=verify_reader()
    spec=importlib.util.spec_from_file_location('fleet_reader',helper);decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    db=apsw.Connection(str(WORK/'meta.snapshot'),flags=apsw.SQLITE_OPEN_READONLY)
    db.pragma('cipher','chacha20');db.pragma('cipher_page_size',4096);db.pragma('hexkey',decoder.get_db_hex_key('global'))
    fleet=json.loads((inventory_path or ROOT/'modding/fleet-source-inventory.json').read_text());destination=WORK/'fleet-bundles';destination.mkdir(exist_ok=True);receipt_path=destination/'source-receipts.json';previous=json.loads(receipt_path.read_text()) if receipt_path.exists() else {};receipts=previous.get('bundles',{});assert not previous or previous['reader_revision']==REV
    for character in fleet['characters']:
        dependencies={}
        for part in character['parts']:
            rows=list(db.execute('SELECT i FROM a WHERE n=?',(part['logical'],)))
            if len(rows)!=1:raise ValueError('Ambiguous character catalog entry')
            rows=db.execute("WITH RECURSIVE deps(id) AS (VALUES(?) UNION SELECT r.t FROM r JOIN deps ON r.f=deps.id WHERE r.d!='0') SELECT a.n,a.h,a.e FROM deps JOIN a ON a.i=deps.id WHERE a.h IS NOT NULL AND a.h!=''",(rows[0][0],))
            for name,hashed,key in rows:dependencies[hashed]=(name,key)
        paths=[]
        for hashed,(name,key) in sorted(dependencies.items()):
            if not hashed.isalnum():raise ValueError('Unsafe asset filename')
            source=SOURCE/'dat'/hashed[:2]/hashed;target=destination/(hashed+'.unity3d')
            if hashed in receipts and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=receipts[hashed]['decoded_sha256']:raise ValueError('Cached bundle no longer matches receipt')
            if hashed not in receipts or not target.exists():
                before=source.stat()
                if not 0<before.st_size<=256*1024*1024:raise ValueError('Bundle outside bounds')
                original=source.read_bytes();decoded=bytes(decoder.decrypt_bundle(bytearray(original),key=key,base_keys=decoder.ASSET_BASE_KEYS_JAPAN))
                if not decoded.startswith(b'UnityFS\0'):raise ValueError('Unexpected decoded format')
                if target.exists() and target.read_bytes()!=decoded:raise ValueError('Conflicting existing extraction')
                if not target.exists():target.write_bytes(decoded)
                after=source.stat()
                if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('Steam source changed')
                receipts[hashed]=dict(logical_name=name,source_sha256=hashlib.sha256(original).hexdigest(),decoded_sha256=hashlib.sha256(decoded).hexdigest(),bytes=len(decoded),source_unchanged=True)
            paths.append(str(target))
        env=UnityPy.load(*paths);counts={};meshes=[];textures=[]
        for obj in env.objects:
            kind=obj.type.name;counts[kind]=counts.get(kind,0)+1
            if kind=='Mesh':
                tree=obj.read_typetree();meshes.append(dict(name=tree.get('m_Name'),path_id=obj.path_id,vertices=tree.get('m_VertexData',{}).get('m_VertexCount'),submeshes=len(tree.get('m_SubMeshes',[]))))
            elif kind=='AnimationClip':
                clip=obj.read_typetree();motion=WORK/'fleet'/str(character['id'])/'motions';motion.mkdir(parents=True,exist_ok=True)
                clipname=clip['m_Name']
                if not clipname.replace('_','').isalnum():raise ValueError('Unsafe animation name')
                (motion/(clipname+'.json')).write_text(json.dumps(clip,allow_nan=False)+'\n')
            elif kind=='Texture2D':
                tree=obj.read_typetree();textures.append(dict(name=tree.get('m_Name'),width=tree.get('m_Width'),height=tree.get('m_Height')))
        if not counts.get('Mesh') or not counts.get('SkinnedMeshRenderer'):raise ValueError('Character has no skinned meshes')
        folder=WORK/'fleet'/str(character['id']);folder.mkdir(parents=True,exist_ok=True)
        report=dict(id=character['id'],name=character['name'],nfs_slot=character['nfs_slot'],dependencies=sorted(dependencies),object_counts=counts,meshes=meshes,textures=textures,game_integrated=False)
        (folder/'source-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
        (destination/'source-receipts.json').write_text(json.dumps(dict(reader_revision=REV,reader_source_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),bundles=receipts),indent=2)+'\n')
        print(character['name'],len(dependencies),'bundles;',len(meshes),'meshes;',len(textures),'textures',flush=True)
    db.close()

if __name__=='__main__':main()

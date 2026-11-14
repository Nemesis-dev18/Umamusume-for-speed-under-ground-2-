"""Extract three local Unity bundles; never open Steam sources for writing."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'modding/uma-steam'
sys.path.insert(0,str(WORK/'python-deps'))
import apsw
import UnityPy

SOURCE=Path('/home/nemesis/.local/share/Steam/steamapps/common/UmamusumePrettyDerby/UmamusumePrettyDerby_Data/Persistent')
COMMIT='dca091dad2947d13f99a0510bcccdec82941df0c'
ASSETS={
 'anm_rac_type03_run02_base':'3d/motion/racemain/body/type03/anm_rac_type03_run02_base',
 'anm_rac_type03_run03_base':'3d/motion/racemain/body/type03/anm_rac_type03_run03_base',
 'kitasan-body':'3d/chara/body/bdy1068_00/pfb_bdy1068_00',
}

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    repo=WORK/'tools/UmaExporter'
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=COMMIT:raise ValueError('Reader revision changed')
    helper=repo/'src/core/decryptor.py'
    if helper.read_bytes()!=subprocess.check_output(['git','-C',str(repo),'show',f'{COMMIT}:src/core/decryptor.py']):raise ValueError('Reader source changed')
    spec=importlib.util.spec_from_file_location('uma_decryptor_helper',helper);decryptor=importlib.util.module_from_spec(spec);spec.loader.exec_module(decryptor)
    snapshot=WORK/'meta.snapshot';shutil.copyfile(SOURCE/'meta',snapshot)
    db=apsw.Connection(str(snapshot),flags=apsw.SQLITE_OPEN_READONLY)
    db.execute("PRAGMA cipher='chacha20'");db.execute('PRAGMA cipher_page_size=4096')
    db.execute(f'''PRAGMA hexkey='{decryptor.get_db_hex_key("global")}' ''')
    output=WORK/'bundles';output.mkdir(exist_ok=True)
    for name,logical in ASSETS.items():
        rows=list(db.execute('SELECT h,e FROM a WHERE n=?',(logical,)))
        if len(rows)!=1:raise ValueError(f'Catalog entry not unique: {logical}')
        hashed,key=rows[0]
        if not hashed.isalnum():raise ValueError('Invalid catalog filename')
        source=SOURCE/'dat'/hashed[:2]/hashed;original=source.read_bytes()
        decoded=bytes(decryptor.decrypt_bundle(bytearray(original),key=key,base_keys=decryptor.ASSET_BASE_KEYS_JAPAN))
        if not decoded.startswith(b'UnityFS\0'):raise ValueError('Invalid bundle header')
        env=UnityPy.load(decoded)
        if name=='kitasan-body':
            data=[{'path_id':obj.path_id,'type':obj.type.name,'data':obj.read_typetree()} for obj in env.objects if obj.type.name in ('GameObject','Transform','Avatar','Animator')]
            if sum(x['type']=='Avatar' for x in data)!=1:raise ValueError('Expected single source avatar')
            destination=output/'kitasan-body-rig.json'
        else:
            clips=[obj.read_typetree() for obj in env.objects if obj.type.name=='AnimationClip']
            if len(clips)!=1 or clips[0]['m_Name']!=name:raise ValueError('Unexpected animation clip')
            data=clips[0];destination=output/(name+'.json')
        if source.read_bytes()!=original:raise ValueError('Steam source changed during extraction')
        (output/(name+'.unity3d')).write_bytes(decoded)
        destination.write_text(json.dumps(data,ensure_ascii=False)+'\n')
        receipt={'logical_name':logical,'physical_file':str(source),'source_sha256':digest(original),'decoded_sha256':digest(decoded),'catalog_region':'global','bundle_base_keys':'upstream JP constant validated by successful parsing','game_source_unchanged':True,'reader_commit':COMMIT}
        (output/(name+'.source.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        print(name,receipt['source_sha256'],'source unchanged')
    db.close()

if __name__=='__main__':main()

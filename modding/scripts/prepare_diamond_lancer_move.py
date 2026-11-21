"""Stage Diamond on the selectable Lancer and restore Celica; repair Doto badge aliases."""
import hashlib,json
from inspect_assets import ROOT,jdlz,cartypes
from prepare_fleet_badges import directory
from prepare_tiremask import rewrite_jdlz
from prepare_character_name import entries,prepare_names
from disable_car_effects import string_hash

def main():
 previous=json.loads((ROOT/'modding/diamond-preview-install-plan.json').read_text());assert previous['installed'] and previous['user_approved']
 backups={r['target']:ROOT/r['backup'] for r in previous['files'] if r['backup']}
 for r in previous['files']:
  if r['backup']:assert hashlib.sha256(backups[r['target']].read_bytes()).hexdigest()==r['before']
 folder=ROOT/'modding/staged-runtime/diamond-lancer-move';folder.mkdir(exist_ok=True)
 original=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();raw=jdlz(original);out=bytearray(raw);table=directory(raw);before=jdlz(backups['FRONTEND/FrontB.lzc'].read_bytes());old=directory(before);changes=[]
 for target,source,data,lookup in [('SECONDARY_LOGO_CELICA','SECONDARY_LOGO_CELICA',before,old),('SECONDARY_LOGO_LANCEREVO8','SECONDARY_LOGO_CELICA',raw,table),('CARSELECT_MANUFACTURER_OPEL','CARSELECT_MANUFACTURER_DOTO',raw,table),('CARSELECT_MANUFACTURER_VAUXHALL','CARSELECT_MANUFACTURER_DOTO',raw,table)]:
  a,n,_=table[string_hash(target)];b,m,_=lookup[string_hash(source)];assert n==m;out[a:a+n]=data[b:b+m];changes.append({'texture':target,'source':source,'offset':a,'bytes':n})
 allowed={i for c in changes for i in range(c['offset'],c['offset']+c['bytes'])};assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,out)))
 outputs={'FRONTEND/FrontB.lzc':rewrite_jdlz(original,bytes(out))};assert jdlz(outputs['FRONTEND/FrontB.lzc'])==out
 for target in ('LANGUAGES/English.bin','LANGUAGES/Spanish.bin'):
  old_names={k:v for k,v,_ in entries(backups[target].read_bytes())[2]};outputs[target]=prepare_names((ROOT/target).read_bytes(),{'CELICA':old_names[string_hash('CAR_NAME_CELICA')].decode('ascii'),'LANCEREVO8':'Satono Diamond'})
 fields=[]
 for target in ('GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc'):
  original=(ROOT/target).read_bytes();raw=jdlz(original) if original.startswith(b'JDLZ') else original;out=bytearray(raw);prior=backups[target].read_bytes();prior=jdlz(prior) if prior.startswith(b'JDLZ') else prior;cars={c['name']:c for c in cartypes(raw)};oldcars={c['name']:c for c in cartypes(prior)};allowed=set()
  for slot,brand in [('CELICA',prior[oldcars['CELICA']['offset']+192:oldcars['CELICA']['offset']+208]),('LANCEREVO8',b'DIAMOND'.ljust(16,b'\0'))]:
   at=cars[slot]['offset']+192;assert len(brand)==16;out[at:at+16]=brand;allowed.update(range(at,at+16));fields.append({'target':target,'slot':slot,'decoded_offset':at,'bytes':16,'value':brand.split(b'\0')[0].decode()})
  assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,out)));outputs[target]=rewrite_jdlz(original,bytes(out)) if original.startswith(b'JDLZ') else bytes(out)
 assert jdlz(outputs['GLOBAL/GlobalB.lzc'])==outputs['GLOBAL/GLOBALB.BUN']
 for name in ('GEOMETRY.BIN','TEXTURES.BIN'):outputs['CARS/CELICA/'+name]=backups['CARS/CELICA/'+name].read_bytes()
 geo=ROOT/'modding/staged-runtime/fleet/1067';report=json.loads((geo/'geometry.json').read_text());assert report['slot']=='LANCEREVO8' and report['before_sha256']==hashlib.sha256((ROOT/'CARS/LANCEREVO8/GEOMETRY.BIN').read_bytes()).hexdigest()
 outputs['CARS/LANCEREVO8/GEOMETRY.BIN']=(geo/'GEOMETRY.BIN').read_bytes();outputs['CARS/LANCEREVO8/TEXTURES.BIN']=(ROOT/'modding/staged-runtime/diamond/TEXTURES.BIN').read_bytes();outputs['modding/runtime/fleet/1067/anchors.bin']=(geo/'anchors.bin').read_bytes()
 rows=[]
 for target,data in outputs.items():
  dest=folder/target;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);rows.append({'target':target,'candidate':str(dest.relative_to(ROOT)),'before':hashlib.sha256((ROOT/target).read_bytes()).hexdigest(),'after':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 assert len(rows)==10
 (folder/'plan.json').write_text(json.dumps({'files':rows,'fields':fields,'texture_changes':changes,'installed':False,'user_approved':False,'gameplay_verified':False,'scope':'Move Diamond to selectable LANCEREVO8; restore Celica original assets/name/manufacturer; Doto portrait on both regional brand aliases. Existing ASI and cloth unchanged.'},indent=2)+'\n');print('PASS ten staged files; unrelated menu/global fields preserved; no active files changed')
if __name__=='__main__':main()

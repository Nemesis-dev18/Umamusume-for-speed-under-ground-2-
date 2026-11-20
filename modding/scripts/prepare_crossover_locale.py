"""Stage the approved local Spanish text table and missing character badges."""
import datetime,hashlib,json,shutil
from pathlib import Path
from PIL import Image
from inspect_assets import ROOT,jdlz,cartypes
from prepare_character_name import entries,prepare_names
from prepare_fleet_badges import directory,NAMES
from prepare_kitasan_badge import badge,compress_jdlz
from prepare_selection_label import dxt3
from prepare_tiremask import rewrite_jdlz
from jdlz_native import finish_native,validate_native
from disable_car_effects import string_hash

EXPECTED={
 'LANGUAGES/English.bin':(280444,'6fde51111c4fd288823c8127aa57d4760c14c41209885fb5882bde6128ab7687'),
 'LANGUAGES/Spanish.bin':(280444,'6fde51111c4fd288823c8127aa57d4760c14c41209885fb5882bde6128ab7687'),
 'FRONTEND/FrontB.lzc':(2004213,'2ec4c960cf03156177ecc671b2833c7cd7f9171c0460f1f8f709c67c054bb4d3'),
 'GLOBAL/GLOBALB.BUN':(8008064,'390bb1551ca3f30f9f8126fc77e36f8052db91f5be083dd2e4afbf4605e5776d'),
 'GLOBAL/GlobalB.lzc':(5145851,'871d38d35e87fffb3191ec05a4fecfeefef5a4b2e4845129d467cc472ad4fb00')}
sha=lambda data:hashlib.sha256(data).hexdigest()

def build():
 spanish=(ROOT/'LANGUAGES/Spanish.bin').read_bytes();english=(ROOT/'LANGUAGES/English.bin').read_bytes()
 es={k:v for k,v,_ in entries(spanish)[2]};en={k:v for k,v,_ in entries(english)[2]};assert es.keys()==en.keys() and len(es)==3925
 texts=prepare_names(spanish,{'350Z':'Gentildonna'});names=json.loads((ROOT/'modding/fleet-language-plan.json').read_text())['names'];names['350Z']='Gentildonna'
 translated={k:v for k,v,_ in entries(texts)[2]}
 for slot,name in names.items():assert translated[string_hash('CAR_NAME_'+slot)]==name.encode('ascii')
 changed={k for k in es if es[k]!=translated[k]};assert changed=={string_hash('CAR_NAME_350Z')}
 source=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();original=jdlz(source);raw=original;old=directory(original);fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters'];mapping={};added=[]
 for char in fleet:
  identifier=char['id'];name=NAMES[identifier];key=string_hash('CARSELECT_MANUFACTURER_'+name);mapping[char['nfs_slot']]=name
  if key in directory(raw):continue
  folder=ROOT/'modding/uma-steam/mini-fleet'/str(identifier);meta=json.loads((folder/'badge-review.json').read_text());assert meta['source_gltf_sha256']==sha((folder/'source.gltf').read_bytes())
  assert meta['shading']=='Unlit diffuse with source alpha for UI badge'
  with Image.open(folder/'badge-review.png') as image:
   image=image.convert('RGBA');box=image.getchannel('A').getbbox();assert box;image=image.crop(box);image.thumbnail((62,62),Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(128,64));canvas.alpha_composite(image,((128-image.width)//2,(64-image.height)//2))
  raw,newkey=badge(raw,dxt3(canvas),name);assert newkey==key;added.append(name)
 assert added==['URARA','TACHYON','MAMBO','OPERA','OGURI','DOTO'];new=directory(raw)
 for key,(at,size,_) in old.items():
  pos,length,_=new[key];assert size==length and original[at:at+size]==raw[pos:pos+length]
 for brand in [*NAMES.values(),'GENTILDONNA']:assert string_hash('CARSELECT_MANUFACTURER_'+brand) in new
 encoded=finish_native(compress_jdlz(raw));assert validate_native(encoded)==raw
 outputs={'LANGUAGES/English.bin':texts,'LANGUAGES/Spanish.bin':texts,'FRONTEND/FrontB.lzc':encoded};fields=[]
 global_raw=(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes();global_packed=(ROOT/'GLOBAL/GlobalB.lzc').read_bytes();assert jdlz(global_packed)==global_raw
 for name in ['GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc']:
  before=(ROOT/name).read_bytes();base=jdlz(before) if before.startswith(b'JDLZ') else before;data=bytearray(base);cars={c['name']:c for c in cartypes(base)};ranges=[]
  for slot,brand in mapping.items():
   at=cars[slot]['offset']+0xc0;value=brand.encode().ljust(16,b'\0')
   if base[at:at+16]!=value:data[at:at+16]=value;ranges.append((at,at+16));fields.append({'target':name,'slot':slot,'decoded_offset':at,'bytes':16,'value':brand})
  assert len(ranges)==6
  allowed={i for lo,hi in ranges for i in range(lo,hi)};assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(base,data)))
  out=rewrite_jdlz(before,bytes(data)) if before.startswith(b'JDLZ') else bytes(data)
  if out.startswith(b'JDLZ'):assert validate_native(out)==data
  outputs[name]=out
 for name,data in outputs.items():assert (len(data),sha(data))==EXPECTED[name],f'Approved candidate changed: {name}'
 return outputs,fields

def main():
 outputs,fields=build();folder=ROOT/'modding/staged-runtime/crossover-locale';backup=ROOT/'modding/backups'/('before-crossover-locale-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S'));backup.mkdir(exist_ok=False);rows=[]
 for name,data in outputs.items():
  source=ROOT/name;target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);copy=backup/(name+'.bak');copy.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,copy);assert sha(copy.read_bytes())==sha(source.read_bytes())
  rows.append({'target':name,'candidate':str(target.relative_to(ROOT)),'before':sha(source.read_bytes()),'after':sha(data),'bytes':len(data),'backup':str(copy.relative_to(ROOT))})
 plan={'backup_root':str(backup.relative_to(ROOT)),'files':rows,'fields':fields,'installed':False,'gameplay_verified':False,'scope':'Approved Spanish text resources, Gentildonna internal name, six missing chibi badges; original title texture pixels retained','user_approved':True}
 (ROOT/'modding/crossover-locale-install.json').write_text(json.dumps(plan,indent=2)+'\n');print('PASS five exact approved candidates, all eight names/badges, existing texture pixels preserved, native JDLZ validated; backups prepared')
if __name__=='__main__':main()

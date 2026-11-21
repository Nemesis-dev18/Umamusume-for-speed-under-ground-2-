"""Stage regional character title aliases; preserve all unrelated frontend pixels."""
import hashlib,io,json
from pathlib import Path
from PIL import Image,ImageDraw
from inspect_assets import ROOT,jdlz,chunks
from prepare_fleet_badges import directory
from prepare_tiremask import rewrite_jdlz
from disable_car_effects import string_hash
from extract_assets import dds_header

def build(source):
 raw=jdlz(source);table=directory(raw);output=bytearray(raw);pairs=[]
 aliases={'MIATA':['MX5'],'COROLLA':['TRUENO'],'CORSA':['OPEL_CORSA'],'350Z':['FAIRLADYZ']}
 for canonical,regional in aliases.items():
  key=string_hash('SECONDARY_LOGO_'+canonical);at,size,header=table[key];targets=[(string_hash('SECONDARY_LOGO_'+alias),'SECONDARY_LOGO_'+alias) for alias in regional]
  if canonical=='MIATA':targets +=[(k,h[12:36].split(b'\0')[0].decode('ascii')) for k,(_,_,h) in table.items() if h[12:36].split(b'\0')[0]==b'SECONDARY_LOGO_MIATA_RO']
  for target,name in targets:
   pos,length,h=table[target];assert (size,length)==(16384,16384) and header[74]==h[74]==0x24 and header[78]==h[78]==1
   output[pos:pos+length]=raw[at:at+size];pairs.append({'source':canonical,'alias':name,'hash':hex(target),'pixel_offset':pos,'bytes':length})
 assert len(pairs)==5;allowed={p for item in pairs for p in range(item['pixel_offset'],item['pixel_offset']+item['bytes'])};assert len(output)==len(raw)
 assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,output))) and chunks(raw)==chunks(output)
 encoded=rewrite_jdlz(source,bytes(output));assert jdlz(encoded)==output
 return encoded,pairs,raw,output

def main():
 source=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();encoded,pairs,before,after=build(source);folder=ROOT/'modding/staged-runtime/regional-character-titles';folder.mkdir(exist_ok=True);(folder/'FrontB.lzc').write_bytes(encoded)
 sheet=Image.new('RGBA',(768,len(pairs)*96),(32,36,43,255));draw=ImageDraw.Draw(sheet)
 for i,pair in enumerate(pairs):
  pos=pair['pixel_offset'];header=dds_header(256,64,b'DXT3',16384)
  for col,data in enumerate([before,after]):
   with Image.open(io.BytesIO(header+data[pos:pos+16384])) as im:sheet.alpha_composite(im.convert('RGBA'),(col*384+64,i*96+24))
  draw.text((8,i*96+4),pair['alias']+'  antes / candidato',fill='white')
 out=ROOT/'modding/diagnostics/regional-character-titles';out.mkdir(exist_ok=True);sheet.convert('RGB').save(out/'comparison.png')
 plan={'target':'FRONTEND/FrontB.lzc','candidate':str((folder/'FrontB.lzc').relative_to(ROOT)),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest(),'before_bytes':len(source),'bytes':len(encoded),'aliases':pairs,'installed':False,'gameplay_verified':False};(folder/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('PASS five regional aliases, unrelated decoded bytes/layout unchanged; staged',len(encoded),'bytes')
if __name__=='__main__':main()

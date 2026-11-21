"""Stage original 350Z collision only to isolate native dynamics from character rendering."""
import hashlib,json
from inspect_assets import ROOT,chunks,flatten
from extract_assets import payload

def main():
 receipt=json.loads((ROOT/'modding/gentildonna-install-plan.json').read_text());before=next(r for r in receipt['files'] if r['target']=='CARS/350Z/GEOMETRY.BIN');source=ROOT/before['backup'];native=source.read_bytes();assert hashlib.sha256(native).hexdigest()==before['before']
 target=ROOT/'CARS/350Z/GEOMETRY.BIN';original=target.read_bytes();a=[n for n in flatten(chunks(native)) if n['id']=='0x80034020'];b=[n for n in flatten(chunks(original)) if n['id']=='0x80034020'];assert len(a)==len(b)==1;a,b=a[0],b[0]
 assert a['size']==b['size'] and len(a['children'])==len(b['children'])==15
 for x,y in zip(a['children'],b['children']):
  assert x['id']==y['id'] and x['size']==y['size']
  if x['id']!='0x00039201':assert payload(native,x)==payload(original,y)
 result=bytearray(original);result[b['payload']:b['end']]=native[a['payload']:a['end']]
 assert len(result)==len(original) and chunks(result)==chunks(original)
 assert result[:b['payload']]==original[:b['payload']] and result[b['end']:]==original[b['end']:]
 for node in flatten(chunks(result)):
  if node['id']=='0x00134002':
   import struct
   raw=payload(result,node)
   if len(raw)>=112:assert struct.unpack_from('<2I',raw,104)==(b['offset'],b['size']+8)
 folder=ROOT/'modding/staged-runtime/gentildonna-original-collision';folder.mkdir(exist_ok=True);candidate=folder/'GEOMETRY.BIN';candidate.write_bytes(result)
 plan={'files':[{'target':str(target.relative_to(ROOT)),'candidate':str(candidate.relative_to(ROOT)),'before':hashlib.sha256(original).hexdigest(),'after':hashlib.sha256(result).hexdigest(),'bytes':len(result)}],'source_backup':str(source.relative_to(ROOT)),'collision_payload_offset':b['payload'],'collision_payload_bytes':b['size'],'hulls':5,'installed':False,'user_approved':False,'gameplay_verified':False,'diagnostic_only':True,'scope':'Restore exact original 350Z collision payload, keep current character carriers and all other bytes. Test wall/ground contact separately from render tracking.','limits':['Temporarily restores car-sized collision, not intended final humanoid hitbox','Does not prove native physical stability until in-game test','Character cloth and crash animation remain incomplete']};(folder/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('PASS staged original collision payload only; character render geometry and all unrelated bytes unchanged;',len(result),'bytes')
if __name__=='__main__':main()

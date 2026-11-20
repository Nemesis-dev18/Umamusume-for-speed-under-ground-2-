"""Stage skirt-only dynamic/surface parameters; leave the active character untouched."""
import hashlib,json,math,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 source=ROOT/'modding/runtime/fleet/9001/secondary.bin';original=source.read_bytes();data=bytearray(original);model=(ROOT/'modding/runtime/fleet/9001/model.umab').read_bytes()
 names=json.loads((ROOT/'modding/staged-runtime/gentildonna/secondary.json').read_text())['nodes'];magic,version,bones,nodes,colliders,refs=struct.unpack_from('<4s5I',data)
 assert (magic,version,bones,nodes,colliders)==(b'UMAS',1,271,123,5) and len(names)==nodes and bones==struct.unpack_from('<I',model,16)[0]
 changed=[];mask=bytearray(bones)
 for i,name in enumerate(names):
  if 'スカート' not in name:continue
  at=24+i*48;old=struct.unpack_from('<4H10f',original,at);node=list(old);depth=int(re.search(r'(\d+)$',name).group(1));assert 1<=depth<=6
  node[1]|=512;node[7]=max(1.6,2.6-.2*depth);node[8]=1.05;node[9]=1.6;node[11]=math.radians(min(18,9+1.5*depth));node[12]=.001;node[13]=.75
  struct.pack_into('<4H10f',data,at,*node);mask[node[0]]=1;changed.append({'name':name,'bone':node[0],'offset':at,'before':old,'after':node})
 assert len(changed)==48
 joint_start=40+struct.unpack_from('<I',model,8)[0]*60
 for i in range(bones):
  parent=struct.unpack_from('<h',model,joint_start+i*16)[0]
  assert -1<=parent<i
  if parent>=0 and mask[parent]:mask[i]=1
 changed_bytes=set(k for c in changed for k in range(c['offset'],c['offset']+48));assert all(a==b or i in changed_bytes for i,(a,b) in enumerate(zip(original,data)))
 folder=ROOT/'modding/staged-runtime/gentildonna-cloth';folder.mkdir(exist_ok=True);(folder/'secondary.bin').write_bytes(data);(folder/'surface-mask.bin').write_bytes(mask)
 report={'target':'modding/runtime/fleet/9001/secondary.bin','bytes':len(data),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'model_sha256':hashlib.sha256(model).hexdigest(),'changed_nodes':changed,'surface_bones':sum(mask),'installed':False,'gameplay_verified':False,'scope':'48 skirt springs only, flags512 enables edge-length projection without cape group averaging'}
 (folder/'plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Staged 48 skirt nodes;',sum(mask),'surface bones;',len(data),'bytes; active files untouched')
if __name__=='__main__':main()

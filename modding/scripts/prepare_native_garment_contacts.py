"""Stage source-specific Unity garment contacts without changing spring tuning or active files."""
import hashlib,json,struct
from inspect_assets import ROOT

def prepare(original,meta):
 magic,version,bones,nodes,colliders,refs=struct.unpack_from('<4s5I',original)
 assert magic==b'UMAS' and version==1 and nodes==len(meta['spring_nodes'])
 start=24+nodes*48;end=start+colliders*36;tail=end+refs*2
 assert len(original)==tail+(-tail)%4 and not any(original[tail:])
 oldrefs=struct.unpack_from('<'+'H'*refs,original,end);names={}
 records=[]
 for i,source in enumerate(meta['spring_nodes']):
  row=list(struct.unpack_from('<4H10f',original,24+i*48));assert row[0]==source['bone'] and row[3]==len(source['colliders'])
  # Metadata lists names by collider-table order, not by each spring's reference order.
  current=sorted(oldrefs[row[2]:row[2]+row[3]]);assert len(current)==row[3] and len(set(current))==row[3]
  for name,index in zip(source['colliders'],current):
   assert index<colliders and names.setdefault(name,index)==index
  records.append(row)
 newrefs=[];changes=[]
 for row,source in zip(records,meta['spring_nodes']):
  wanted=source['native']['_collisionNameList'];missing=[n for n in wanted if n not in names]
  selected=[n for n in wanted if n in names]
  # Unsupported original planes retain the existing fallback until their geometry is implemented.
  if missing:selected +=[n for n in source['colliders'] if n.startswith('Runtime')]
  selected=list(dict.fromkeys(selected));indices=[names[n] for n in selected];row[2]=len(newrefs);row[3]=len(indices);newrefs.extend(indices)
  if selected!=source['colliders']:changes.append({'bone':source['bone'],'name':source['name'],'before':source['colliders'],'after':selected,'unresolved_original':missing})
 assert len(newrefs)<=4096
 result=struct.pack('<4s5I',magic,version,bones,nodes,colliders,len(newrefs))+b''.join(struct.pack('<4H10f',*r) for r in records)+original[start:end]+struct.pack('<'+'H'*len(newrefs),*newrefs)
 result+=bytes((-len(result))%4)
 assert result[start:end]==original[start:end]
 for i in range(nodes):
  at=24+i*48;assert result[at:at+4]==original[at:at+4] and result[at+8:at+48]==original[at+8:at+48]
 return result,changes

def main():
 rows=[]
 for identifier in (1068,1052,1032,1062,1015,1006,1058,1067):
  source=ROOT/f'modding/runtime/fleet/{identifier}/secondary.bin';folder=ROOT/f'modding/staged-runtime/fleet-secondary/{identifier}'
  if identifier==1067:folder=ROOT/'modding/staged-runtime/diamond'
  meta=json.loads((folder/'secondary.json').read_text());original=source.read_bytes();data,changes=prepare(original,meta);out=ROOT/f'modding/staged-runtime/native-garment-contacts/{identifier}';out.mkdir(parents=True,exist_ok=True);(out/'secondary.bin').write_bytes(data)
  rows.append({'id':identifier,'target':str(source.relative_to(ROOT)),'candidate':str((out/'secondary.bin').relative_to(ROOT)),'before':hashlib.sha256(original).hexdigest(),'after':hashlib.sha256(data).hexdigest(),'bytes':len(data),'changed_contacts':changes,'physics_coefficients_and_colliders_unchanged':True})
  print(identifier,len(changes),'source contact associations repaired; staged',len(data),'bytes')
 plan={'files':rows,'installed':False,'user_approved':False,'gameplay_verified':False,'scope':'Native collision-name associations instead of blanket generic body contacts; unsupported source planes keep existing fallback. Does not add cloth surface/body collision or promise zero clipping.'};(ROOT/'modding/staged-runtime/native-garment-contacts/plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()

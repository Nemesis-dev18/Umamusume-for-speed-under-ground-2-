"""Inventory actual racer slots, installed characters and remaining stock cars without game writes."""
import hashlib,json,struct
from inspect_assets import ROOT,cartypes
from prepare_character_name import entries
from disable_car_effects import string_hash
from fleet_carrier import carrier

def build():
 data=(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes();cars=cartypes(data);assert len({c['name'] for c in cars})==len(cars)
 strings={k:v for k,v,_ in entries((ROOT/'LANGUAGES/English.bin').read_bytes())[2]};characters=[]
 for name in ('fleet-source-inventory.json','diamond-source-inventory.json'):characters+=json.loads((ROOT/'modding'/name).read_text())['characters']
 characters.append({'id':9001,'name':'Gentildonna','nfs_slot':'350Z'})
 assert len({c['id'] for c in characters})==len({c['nfs_slot'] for c in characters})==9
 installed={c['nfs_slot']:c for c in characters};rows=[];traffic=[]
 for car in cars:
  slot=car['name'];at=car['offset'];usage=struct.unpack_from('<I',data,at+0x844)[0];assert usage in (0,2)
  if usage==2:traffic.append(slot);continue
  brand=data[at+0xc0:at+0xd0].split(b'\0')[0].decode('ascii');label=strings.get(string_hash('CAR_NAME_'+slot),slot.encode()).decode('latin1');row={'slot':slot,'display_name':label,'manufacturer':brand,'usage':usage,'cartype_offset':at,'character':None,'status':'stock_car'}
  if slot in installed:
   c=installed[slot];folder=ROOT/f"modding/runtime/fleet/{c['id']}";model=(folder/'model.umab').read_bytes();assert model[:4]==b'UMAB' and struct.unpack_from('<I',model,4)[0]==3
   assert (folder/'atlas.dds').is_file() and (folder/'secondary.bin').is_file()
   geometry=(ROOT/f'CARS/{slot}/GEOMETRY.BIN').read_bytes();hits=geometry.count(carrier(c['id']));assert hits==20,(slot,hits)
   row.update(character=c['name'],character_id=c['id'],status='installed_unfinished',render_carriers=hits,vertices=struct.unpack_from('<I',model,8)[0],quality_complete=False)
  rows.append(row)
 assert len(rows)==31 and sum(r['character'] is not None for r in rows)==9
 isolation=json.loads((ROOT/'modding/gentildonna-collision-isolation-install-plan.json').read_text());return {'scope':'Racer records UsageType0 in this local copy; menu visibility can differ by region/unlocks. Installed means native model/assets and20 body carriers present, not finished quality.','global_sha256':hashlib.sha256(data).hexdigest(),'usage_offset':'CarTypeInfo+0x844','counts':{'racer_slots':len(rows),'character_slots':9,'remaining_stock_racers':len(rows)-9,'traffic_records':len(traffic)},'racers':rows,'traffic_excluded':traffic,'gentildonna_collision_diagnostic_installed':isolation['installed'],'open_issues':['Cruces de paredes/suelo e inclinación tras choques pendientes de verificar','Tirones en modo profesional','Intersecciones entre ropa, extremidades, cabello y cola','Colisión humanoide final pendiente; Gentildonna conserva temporalmente la colisión original del coche']}

def main():
 report=build();(ROOT/'modding/roster-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');lines=['# Roster local: 9 personajes instalados, 22 casillas pendientes','','Inventario de las casillas Racer de esta copia. Se verificaron archivos del personaje y 20 portadores de malla por casilla; no implica calidad final ni desbloqueo en el menú.','','| Personaje | Casilla sustituida |','|---|---|']
 for r in report['racers']:
  if r['character']:lines.append(f"| {r['character']} | {r['slot']} |")
 lines+=['','## Pendientes','']
 for r in report['racers']:
  if not r['character']:lines.append(f"- {r['manufacturer']} {r['display_name']} (`{r['slot']}`)")
 lines+=['','## Calidad pendiente','']+['- '+issue for issue in report['open_issues']]+['','Se excluyen 15 vehículos de tráfico. Las 31 casillas incluyen variantes regionales; no se afirma que todas estén visibles/desbloqueadas en esta sesión.']
 (ROOT/'modding/ROSTER.md').write_text('\n'.join(lines)+'\n');print(json.dumps(report['counts']));print('Remaining:',', '.join(r['slot'] for r in report['racers'] if not r['character']))
if __name__=='__main__':main()

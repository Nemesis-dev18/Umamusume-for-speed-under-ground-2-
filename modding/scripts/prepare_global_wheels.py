"""Stage removal of stock and aftermarket rim meshes; preserve vehicle physics."""
import hashlib
import json
from inspect_assets import ROOT
from prepare_shared_parts import prepare


def stock_wheel(name):
    return any(token in name for token in ('_WHEEL_','_TIRE_','_TYRE_'))


def removed_part(car,name):
    if car=='COROLLA':return name not in {f'COROLLA_KIT00_BODY_{lod}' for lod in 'ABCD'}
    return stock_wheel(name)


def main():
    rows=[]
    for target in sorted((ROOT/'CARS').glob('*/GEOMETRY*.BIN')):
        backup=target.with_name(target.name+'.before-global-wheels.bak')
        source=(backup if backup.exists() else target).read_bytes()
        shared=target.parent.name=='WHEELS'
        if shared and len(source)==64:continue  # Empty wheel-list placeholder.
        if not shared and not any(token in source for token in (b'_WHEEL_',b'_TIRE_',b'_TYRE_')):continue
        output,ranges=prepare(source,None if shared else lambda name:removed_part(target.parent.name,name))
        if output==source:continue
        relative=target.relative_to(ROOT);candidate=ROOT/'modding/staged-runtime/global-wheels'/relative
        candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(output)
        rows.append({'target':str(relative),'candidate':str(candidate.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),'bytes':len(source),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(output).hexdigest(),'index_ranges':ranges})
    plan={'files':rows,'installed':False,'scope':'All named stock wheel/tire meshes and all aftermarket rims; Corolla preserves only the four character BODY LODs. Only triangle indices changed. Separate front-end TIREMASK fix is required. Collision, suspension and wheel radii untouched.'}
    (ROOT/'modding/global-wheels-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Staged',len(rows),'files;',sum(len(x['index_ranges']) for x in rows),'wheel meshes; no installed files changed')


if __name__=='__main__':main()

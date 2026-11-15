"""Stage removal of stock and aftermarket rim meshes; preserve vehicle physics."""
import hashlib
import json
from inspect_assets import ROOT
from prepare_shared_parts import prepare


def stock_wheel(name):
    return '_FRONT_WHEEL_' in name or '_REAR_WHEEL_' in name


def main():
    rows=[]
    for target in sorted((ROOT/'CARS').glob('*/GEOMETRY*.BIN')):
        backup=target.with_name(target.name+'.before-global-wheels.bak')
        source=(backup if backup.exists() else target).read_bytes()
        shared=target.parent.name=='WHEELS'
        if shared and len(source)==64:continue  # Empty wheel-list placeholder.
        if not shared and b'_FRONT_WHEEL_' not in source and b'_REAR_WHEEL_' not in source:continue
        output,ranges=prepare(source,None if shared else stock_wheel)
        if output==source:continue
        relative=target.relative_to(ROOT);candidate=ROOT/'modding/staged-runtime/global-wheels'/relative
        candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(output)
        rows.append({'target':str(relative),'candidate':str(candidate.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),'bytes':len(source),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(output).hexdigest(),'index_ranges':ranges})
    plan={'files':rows,'installed':False,'scope':'All stock wheel meshes and all aftermarket rim meshes; only triangle indices changed. Procedural tire drawing still requires trace attribution. Collision, suspension and wheel radii untouched.'}
    (ROOT/'modding/global-wheels-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Staged',len(rows),'files;',sum(len(x['index_ranges']) for x in rows),'wheel meshes; no installed files changed')


if __name__=='__main__':main()

"""Reproduce native fleet CPU/material/GPU checks without starting either game."""
import hashlib,json,os,sys
from PIL import Image
from verify_runtime import CC,FLAGS,RUNTIME,ROOT,WORK,WINE,run


def main():
    for test in ('test_fleet_runtime_pack.py','test_fleet_materials.py'):
        run([sys.executable,'-m','unittest','discover','-s','modding/tests','-p',test,'-v'])
    output=RUNTIME/'fleet-gpu';output.mkdir(exist_ok=True)
    run([CC,*FLAGS,'-Wno-unused-function',RUNTIME/'fleet_renderer_test.c','-o',RUNTIME/'test-build/fleet-renderer-test.exe','-ld3d9','-luser32','-lm'])
    run([WINE,RUNTIME/'test-build/fleet-renderer-test.exe'],env=dict(os.environ,WINEPREFIX=str(WORK/'proton-prefix/pfx'),WINEDEBUG='-all'))
    lines=(output/'result.txt').read_text().splitlines();characters=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters'];assets=[]
    if len(lines)!=len(characters) or not all(line.startswith('PASS ') for line in lines):raise RuntimeError('Fleet GPU checks incomplete')
    for character,line in zip(characters,lines):
        identifier=character['id']
        if not line.startswith(f'PASS id={identifier} '):raise RuntimeError('GPU character order mismatch')
        folder=ROOT/'modding/uma-steam/fleet'/str(identifier)/'runtime';hashes={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ('model.umab','model-atlas.umab','atlas.dds','face-baked.png')}
        assets.append({'id':identifier,'slot':character['nfs_slot'],'sha256':hashes,'gpu_result':line})
        for frame in range(3):
            path=output/f'{identifier}-{frame}.ppm'
            with Image.open(path) as image:image.save(path.with_suffix('.png'))
    report={'scope':'Independent C and D3D9 hosts; no NFSU2 or Steam game launch','characters':assets,'native_skin_reference_cases':56,'iris':'Neutral face texture bake; original animated gaze and blink are not implemented','gameplay_verified':False,'installed':False}
    (RUNTIME/'fleet-runtime-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'verified_characters':len(assets),'native_skin_reference_cases':56,'gameplay_verified':False}))

if __name__=='__main__':main()

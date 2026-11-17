"""Stage original vector racing labels in the seven existing FrontB texture ranges."""
import hashlib,html,json,subprocess
from PIL import Image
import numpy as np
from inspect_assets import ROOT,jdlz,chunks
from prepare_selection_label import dxt3
from prepare_kitasan_badge import compress_jdlz
LINES={1068:('KITASAN','BLACK'),1052:('HARU','URARA'),1032:('AGNES','TACHYON'),1062:('MATIKANE','TANNHAUSER'),1015:('T.M.','OPERA O'),1006:('OGURI','CAP'),1058:('MEISHO','DOTO')}


def main():
    source=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();inventory=json.loads((ROOT/'modding/fleet-menu-label-inventory.json').read_text())
    if hashlib.sha256(source).hexdigest()!=inventory['source_sha256']:raise ValueError('FrontB changed since mapping')
    raw=jdlz(source);out=bytearray(raw);mask=np.zeros(len(raw),bool);folder=ROOT/'modding/menu-art/labels';folder.mkdir(parents=True,exist_ok=True)
    for entry in inventory['fleet_mapping']:
        identifier=entry['character_id'];lines=LINES[identifier]
        if (entry['width'],entry['height'],entry['format'],entry['mips'],entry['bytes'])!=(256,64,36,1,16384):raise ValueError('Unexpected label format')
        text=[]
        for i,line in enumerate(lines):
            width=min(840,len(line)*89);x=(1024-width)/2
            text.append(f'<text x="{x}" y="{111+i*110}" textLength="{width}" lengthAdjust="spacingAndGlyphs" fill="url(#g{i})">{html.escape(line)}</text>')
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="256" viewBox="0 0 1024 256"><defs><linearGradient id="g0" x2="0" y2="1"><stop stop-color="#c8fffa"/><stop offset="1" stop-color="#24cfcb"/></linearGradient><linearGradient id="g1" x2="0" y2="1"><stop stop-color="#ffdbf0"/><stop offset="1" stop-color="#f14fa3"/></linearGradient></defs><g font-family="DejaVu Sans" font-weight="bold" font-style="oblique" font-size="108" paint-order="stroke fill" stroke="#18283d" stroke-width="13" stroke-linejoin="round">'+''.join(text)+'</g><path d="M92 235H865l-18 9H74Z" fill="#26ccc5"/><path d="M888 235h44l-18 9h-44Z" fill="#f059aa"/></svg>'
        path=folder/f'{identifier}.svg';path.write_text(svg)
        png=folder/f'{identifier}.png';subprocess.run(['magick','-background','none',str(path),'-resize','256x64!',str(png)],check=True,cwd=ROOT,timeout=30)
        with Image.open(png) as image:
            image=image.convert('RGBA')
            if image.getextrema()[3]!=(0,255):raise ValueError('Label transparency lost')
            pixels=dxt3(image)
        start=entry['pixel_offset'];end=start+entry['bytes']
        if len(pixels)!=entry['bytes'] or end>len(out) or mask[start:end].any():raise ValueError('Invalid label range')
        out[start:end]=pixels;mask[start:end]=True
    if chunks(raw)!=chunks(out) or np.any((np.frombuffer(raw,'u1')!=np.frombuffer(out,'u1'))&~mask):raise ValueError('Unrelated frontend bytes changed')
    encoded=compress_jdlz(bytes(out))
    if len(encoded)>=len(out) or jdlz(encoded)!=out:raise ValueError('Frontend compression validation failed')
    destination=ROOT/'modding/staged-runtime/FrontB.fleet-labels.lzc';destination.write_bytes(encoded)
    (ROOT/'modding/fleet-menu-label-plan.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source).hexdigest(),'candidate_sha256':hashlib.sha256(encoded).hexdigest(),'candidate':str(destination.relative_to(ROOT)),'labels':inventory['fleet_mapping'],'installed':False,'visual_approved':False,'chibi_badges_pending':True},indent=2)+'\n')
    print('Staged seven vector labels; all other frontend bytes preserved; chibi badges pending')

if __name__=='__main__':main()

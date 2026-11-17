"""Review decoded installed menu textures; this is not a screenshot of NFS."""
import hashlib,io,json
from PIL import Image,ImageDraw,ImageFont
from inspect_assets import ROOT,jdlz
from prepare_fleet_badges import directory,NAMES
from disable_car_effects import string_hash
from extract_assets import dds_header


def main():
    compressed=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();raw=jdlz(compressed);entries=directory(raw);fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters'];output=ROOT/'modding/diagnostics/fleet-menu-installed';output.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGBA',(960,len(fleet)*176),(24,29,35,255));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf',18);reports=[]
    for index,character in enumerate(fleet):
        assets=[]
        for logical,width,height in [('CARSELECT_MANUFACTURER_'+NAMES[character['id']],128,64),('SECONDARY_LOGO_'+character['nfs_slot'],256,64)]:
            key=string_hash(logical);at,size,header=entries[key]
            if size!=width*height or header[74]!=0x24 or header[78]!=1:raise ValueError('Unexpected installed UI format')
            pixels=raw[at:at+size]
            with Image.open(io.BytesIO(dds_header(width,height,b'DXT3',size)+pixels)) as decoded:image=decoded.convert('RGBA')
            if image.getextrema()[3]!=(0,255):raise ValueError('Badge/label transparency lost')
            image.save(output/(logical+'.png'));assets.append(image)
        y=index*176;draw.rectangle((8,y+8,952,y+168),fill=(45,50,57,255),outline=(92,101,108,255),width=2);sheet.alpha_composite(assets[0].resize((256,128),Image.Resampling.NEAREST),(22,y+32));sheet.alpha_composite(assets[1].resize((512,128),Image.Resampling.NEAREST),(300,y+32));draw.text((22,y+10),character['nfs_slot']+' / '+character['name'],font=font,fill='white');reports.append({'id':character['id'],'slot':character['nfs_slot'],'installed_badge_and_label_decoded':True})
    sheet.convert('RGB').save(output/'review-sheet.png');(output/'review.json').write_text(json.dumps({'source_sha256':hashlib.sha256(compressed).hexdigest(),'characters':reports,'scope':'Decoded installed textures laid out for inspection; not an in-game screenshot','game_menu_verified':False},indent=2)+'\n');print(output/'review-sheet.png')

if __name__=='__main__':main()

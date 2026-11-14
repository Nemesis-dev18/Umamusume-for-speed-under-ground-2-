"""Offline textured contact sheet for retargeted Steam animation, not a game screenshot."""
from PIL import Image,ImageDraw
from inspect_assets import ROOT
from retarget_uma_motion import UmaRetarget
import render_authored_motion as renderer

retarget=UmaRetarget();sheet=Image.new('RGB',(1280,1050),(24,28,34))
for i,phase in enumerate([0,.125,.25,.375]):
    r,t,_,_=retarget.pose(phase);renderer.p,renderer.norm=retarget.target.skin(r,t)
    frame=Image.new('RGB',(640,525),(24,28,34));frame.paste(renderer.render([0,-3,1.7]),(0,30));frame.paste(renderer.render([3,2,1.8]),(320,30))
    ImageDraw.Draw(frame).text((10,10),f'OFFLINE - Steam type03 run02 - phase {phase}',fill='white')
    sheet.paste(frame,((i%2)*640,(i//2)*525));print('Rendered original-motion phase',phase,flush=True)
sheet.save(ROOT/'modding/animation-steam-retarget/contact-preview.png')

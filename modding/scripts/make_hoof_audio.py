"""Create original hoof impacts and a listening preview; never replace engine banks."""
import hashlib
import json
from pathlib import Path
import wave
import numpy as np
from inspect_assets import ROOT

RATE=22050

def impact(seed):
    rng=np.random.default_rng(seed);t=np.arange(int(RATE*.18))/RATE
    noise=rng.standard_normal(len(t));bright=noise-np.convolve(noise,np.ones(9)/9,mode='same')
    attack=1-np.exp(-t/.0006)
    body=np.sin(2*np.pi*(190+seed%11)*t)*np.exp(-t/.027)
    shell=(np.sin(2*np.pi*1320*t)+.6*np.sin(2*np.pi*2380*t))*np.exp(-t/.010)
    sound=attack*(.33*body+.25*shell+.16*bright*np.exp(-t/.009))
    for delay,gain in [(.027,.09),(.048,.035)]:
        shift=int(delay*RATE);sound[shift:]+=gain*sound[:-shift].copy()
    sound*=np.minimum(1,(len(t)-1-np.arange(len(t)))/(RATE*.02))**2;sound[-1]=0
    return sound

def pcm(values):
    if values.ndim!=1 or not np.isfinite(values).all() or np.max(np.abs(values),initial=0)>1:raise ValueError('Invalid or clipping audio')
    return np.rint(values*32767).astype('<i2').tobytes()

def write_wave(path,values):
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(RATE);output.writeframes(pcm(values))

def main():
    out=ROOT/'modding/audio-hoof';out.mkdir(exist_ok=True)
    steps=[impact(10),impact(23)];peak=max(float(np.max(np.abs(s))) for s in steps)
    steps=[s*.72/peak for s in steps]
    for i,step in enumerate(steps):write_wave(out/f'hoof-{i}.wav',step)
    preview=np.zeros(RATE*7);contacts=np.arange(.6,6.5,.3)
    for i,contact in enumerate(contacts):
        at=round(contact*RATE);sample=steps[i%2];preview[at:at+len(sample)]+=sample
    write_wave(out/'hoof-preview.wav',preview)
    report={'origin':'Original deterministic synthesis; no external recordings','rate':RATE,'format':'mono PCM16 little endian','impacts':2,'peak':float(np.max(np.abs(preview))),'source_loop_seconds':.6,'preview_contact_seconds':contacts.tolist(),'installed':False,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.wav'))}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()

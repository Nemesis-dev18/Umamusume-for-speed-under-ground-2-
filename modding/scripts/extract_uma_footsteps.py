"""Extract authentic race-footstep variants from the user's local Uma race bank."""
import hashlib
import json
import re
import struct
import subprocess
import wave
import numpy as np
from inspect_assets import ROOT
from read_cri_audio import utf,awb

FOLDER=ROOT/'modding/uma-steam/audio'

def cue_waves(header,name):
    tables={key:utf(header[key])[1] for key in ['CueNameTable','CueTable','WaveformTable','SynthTable','SequenceTable','TrackTable','TrackEventTable']}
    names=[r for r in tables['CueNameTable'] if r['CueName']==name]
    if len(names)!=1:raise ValueError('Cue absent or ambiguous')
    cue=tables['CueTable'][names[0]['CueIndex']];found=[]
    def resolve(kind,index,path=()):
        if len(path)>16 or (kind,index) in path:raise ValueError('CRI cue cycle or excessive depth')
        path=path+((kind,index),)
        if kind==1:
            row=tables['WaveformTable'][index]
            if row['Streaming'] or row['MemoryAwbId']==65535:raise ValueError('Expected embedded race footstep')
            found.append({'waveform_index':index,'awb_id':row['MemoryAwbId'],'rate':row['SamplingRate'],'channels':row['NumChannels'],'samples':row['NumSamples']})
        elif kind==2:
            items=tables['SynthTable'][index]['ReferenceItems']
            if len(items)%4:raise ValueError('Truncated CRI synth reference')
            for k,i in struct.iter_unpack('>HH',items):
                if k:resolve(k,i,path)
        elif kind==3:
            row=tables['SequenceTable'][index];tracks=row['TrackIndex']
            if len(tracks)!=row['NumTracks']*2:raise ValueError('Track count mismatch')
            for (track,) in struct.iter_unpack('>H',tracks):
                command=tables['TrackEventTable'][tables['TrackTable'][track]['EventIndex']]['Command'];at=0
                while at<len(command):
                    if at+3>len(command):raise ValueError('Truncated CRI command')
                    opcode,length=struct.unpack_from('>HB',command,at);at+=3
                    if at+length>len(command):raise ValueError('Truncated CRI command payload')
                    if opcode in (2000,2003):
                        if length<4:raise ValueError('Invalid CRI note event')
                        k,i=struct.unpack_from('>HH',command,at);resolve(k,i,path)
                    at+=length
        else:raise ValueError(f'Unsupported CRI reference kind {kind}')
    resolve(cue['ReferenceType'],cue['ReferenceIndex'])
    return list({r['awb_id']:r for r in found}.values())

def main():
    bank=FOLDER/'snd_sfx_race_000.acb';data=bank.read_bytes()
    provenance=json.loads((FOLDER/'source.json').read_text())
    if hashlib.sha256(data).hexdigest()!=provenance['sha256']:raise ValueError('Staged race bank changed')
    tool=ROOT/'modding/uma-steam/audio-tools/clhca';reader=json.loads((tool/'source.json').read_text())
    for filename,expected in reader['files'].items():
        if hashlib.sha256((tool/filename).read_bytes()).hexdigest()!=expected:raise ValueError('Pinned HCA reader source changed')
    subprocess.run(['gcc','-std=c11','-O2','-c',str(tool/'clhca.c'),'-o',str(tool/'clhca.o')],check=True)
    subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(tool/'decode_local.c'),str(tool/'clhca.o'),'-lm','-o',str(tool/'decode-local')],check=True)
    name,rows=utf(data)
    if name!='Header' or len(rows)!=1:raise ValueError('Expected one ACB header')
    header=rows[0];subkey,entries=awb(header['AwbFile']);waves=dict(entries)
    viewer=ROOT/'modding/uma-steam/tools/UmaViewer'
    if subprocess.check_output(['git','-C',str(viewer),'rev-parse','HEAD'],text=True).strip()!='9bc1dd8fcb10ab13c17ada92e005643b463f8e2c':raise ValueError('Pinned UmaViewer reader revision changed')
    config=subprocess.check_output(['git','-C',str(viewer),'show','HEAD:Assets/Scripts/Config.cs'],text=True)
    match=re.search(r'DefaultAudioKeyText\s*=\s*"([0-9A-Fa-f]+)"',config)
    if not match:raise ValueError('Pinned reader audio key absent')
    base=int(match[1],16);key=(base*((subkey<<16)|((~subkey&65535)+2)))&((1<<64)-1)
    decoder=ROOT/'modding/uma-steam/audio-tools/clhca/decode-local';out=FOLDER/'race-footsteps';out.mkdir(exist_ok=True);reports=[]
    for foot,side in [(0,'R'),(1,'L')]:
        cue=f'snd_sfx_race_foot_turf_{side}';variants=cue_waves(header,cue)
        if len(variants)!=10:raise ValueError('Expected original ten-variant footstep cue')
        for variant,entry in enumerate(variants):
            encoded=waves[entry['awb_id']];hca=out/f'wave-{entry["awb_id"]}.hca';pcm=hca.with_suffix('.s16le');hca.write_bytes(encoded)
            process=subprocess.run([str(decoder),str(hca),f'{key:x}',str(pcm)],check=True,capture_output=True,text=True);info=json.loads(process.stdout)
            if (info['rate'],info['channels'],info['frames'])!=(entry['rate'],entry['channels'],entry['samples']):raise ValueError('Decoded HCA metadata differs from WaveformTable')
            resample=subprocess.run(['ffmpeg','-v','error','-f','s16le','-ar',str(info['rate']),'-ac',str(info['channels']),'-i',str(pcm),'-ar','22050','-ac','1','-f','s16le','pipe:1'],check=True,capture_output=True)
            raw=resample.stdout;values=np.frombuffer(raw,'<i2')
            if not len(values) or not np.any(values) or len(raw)>32000:raise ValueError('Footstep empty or too long for runtime')
            path=out/f'hoof-{foot}-{variant}.wav'
            with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(raw)
            reports.append(dict(entry,foot=foot,variant=variant,cue=cue,file=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),seconds=len(values)/22050,peak=float(np.max(np.abs(values.astype(float))))/32768,key_validation_blocks=info['key_validation_blocks']))
        print('Decoded',cue,len(variants),'original variants',flush=True)
    manifest={'source_bank_sha256':hashlib.sha256(data).hexdigest(),'reader_uma_viewer_commit':subprocess.check_output(['git','-C',str(viewer),'rev-parse','HEAD'],text=True).strip(),'clhca_source':json.loads((decoder.parent/'source.json').read_text()),'samples':reports,'processing':'Original HCA decoded, encoder delay/padding removed, mono 22050 PCM16 conversion; no synthesis, pitch change or amplitude normalization','installed':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Prepared',len(reports),'original footstep samples')

if __name__=='__main__':main()

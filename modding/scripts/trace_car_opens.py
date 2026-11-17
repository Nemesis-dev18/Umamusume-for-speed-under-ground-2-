"""Observe CARS file opens; inotify does not identify which process opened a file."""
import ctypes
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import tempfile
import time
from inspect_assets import ROOT


class Watch:
    def __init__(self,paths):
        self.lib=ctypes.CDLL(None,use_errno=True)
        self.fd=self.lib.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
        if self.fd<0:raise OSError(ctypes.get_errno(),'inotify_init1')
        self.paths={}
        try:
            for path in paths:
                key=self.lib.inotify_add_watch(self.fd,os.fsencode(path),0x20)
                if key<0:raise OSError(ctypes.get_errno(),str(path))
                self.paths[key]=path
        except BaseException:self.close();raise
    def close(self):
        if self.fd>=0:os.close(self.fd);self.fd=-1
    def read(self,seconds):
        if not select.select([self.fd],[],[],seconds)[0]:return []
        data=os.read(self.fd,65536);at=0;events=[]
        while at<len(data):
            if at+16>len(data):raise ValueError('Truncated inotify event')
            key,mask,cookie,size=struct.unpack_from('iIII',data,at);at+=16
            if at+size>len(data):raise ValueError('Truncated inotify name')
            name=os.fsdecode(data[at:at+size].split(b'\0')[0]);at+=size
            if mask&0x4000:raise RuntimeError('inotify queue overflow; trace incomplete')
            if mask&0x20 and key in self.paths:events.append(self.paths[key]/name)
        return events


def main():
    if sys.argv[1:]==['--self-test']:
        with tempfile.TemporaryDirectory(dir=ROOT/'modding',prefix='watch-test-') as folder:
            path=Path(folder);sample=path/'GEOMETRY.BIN';sample.write_bytes(b'test');watch=Watch([path])
            try:
                assert sample.read_bytes()==b'test';assert sample in watch.read(1)
            finally:watch.close()
        print('PASS real filesystem open observed; temporary fixture removed');return
    if sys.argv[1:]:raise ValueError('Unexpected arguments')
    paths=[p for p in (ROOT/'CARS').iterdir() if p.is_dir()]+[ROOT/name for name in ('TRACKS','GLOBAL','NIS') if (ROOT/name).is_dir()]
    watch=Watch(paths);started=time.monotonic();seen=False
    log=ROOT/'modding/diagnostics/car-open-trace.jsonl'
    try:
        with log.open('x') as out:
            out.write(json.dumps({'scope':'inotify opens in isolated CARS/TRACKS/GLOBAL/NIS; opener PID unavailable','started':time.time()})+'\n');out.flush()
            while time.monotonic()-started<600:
                for path in watch.read(.5):
                    if path.suffix.upper() in ('.BIN','.BUN','.LZC','.BIK'):
                        out.write(json.dumps({'time':time.time(),'path':str(path.relative_to(ROOT))})+'\n');out.flush()
                live=subprocess.run(['pgrep','-x','SPEED2.EXE'],capture_output=True).returncode
                if live not in (0,1):raise RuntimeError('Process status unavailable')
                if live==0:seen=True
                elif seen or time.monotonic()-started>60:break
            out.write(json.dumps({'ended':time.time(),'observed_game_process':seen})+'\n')
    finally:watch.close()

if __name__=='__main__':main()

"""Exact six-vertex identity carried by each native body kit/LOD."""
import struct


def carrier(identifier):
    if identifier not in (1068,1052,1032,1062,1015,1006,1058):raise ValueError('Unknown fleet character')
    positions=((0,0,0),(0,.25,0),(0,.5,0),(0,0,0),(0,0,1),(0,0,2))
    return b''.join(struct.pack('<6f4B2f',*point,1,0,0,255,255,255,255,(identifier+i*17)/4096,(identifier+i*29)/8192) for i,point in enumerate(positions))

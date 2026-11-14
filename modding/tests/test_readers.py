import sys
import struct
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_assets import chunks, data_path, jdlz

class Readers(unittest.TestCase):
    def test_literal_and_overlapping_copy(self):
        body = bytes([2, 1, 65, 0, 0])
        stream = b'JDLZ\x02\x10\0\0' + struct.pack('<II', 4, 16 + len(body)) + body
        self.assertEqual(jdlz(stream), b'AAAA')
    def test_corrupt_jdlz(self):
        for stream in (b'JDLZ', b'JDLZ\x02\x10\0\0' + struct.pack('<II', 2**30, 16),
                       b'JDLZ\x02\x10\0\0' + struct.pack('<II', 3, 20) + bytes([1,1,0,0])):
            with self.assertRaises(ValueError): jdlz(stream)
    def test_parent_boundary(self):
        child = struct.pack('<II', 1, 12)
        parent = struct.pack('<II', 0x80134000, len(child)) + child
        with self.assertRaises(ValueError): chunks(parent)
    def test_nested_offsets(self):
        data = struct.pack('<IIII', 0x80134000, 8, 0x134011, 0)
        tree = chunks(data)
        self.assertEqual(tree[0]['children'][0]['offset'], 8)
    def test_scope(self):
        for name in ('../SPEED2.EXE','SPEED2.EXE','CARS/../SPEED2.EXE','CARS/test.dll'):
            with self.assertRaises(ValueError): data_path(name)


class Geometry(unittest.TestCase):
    def test_real_corolla_and_source_stability(self):
        import hashlib
        from inspect_assets import ROOT
        from extract_assets import geometry
        path=ROOT/'CARS/COROLLA/GEOMETRY.BIN'
        before=hashlib.sha256(path.read_bytes()).digest()
        parts=geometry(path.read_bytes(),'KIT00_BODY_')
        self.assertEqual(len(parts),4)
        for part in parts:
            self.assertEqual(len(part['positions']),14512)
            self.assertEqual(len(part['indices']),16557*3)
            self.assertLess(max(part['indices']),len(part['positions']))
            self.assertIsNone(part['native_bones'])
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).digest())
    def test_globalb_golden_pair(self):
        from inspect_assets import ROOT
        self.assertEqual(jdlz((ROOT/'GLOBAL/GlobalB.lzc').read_bytes()),(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes())
    def test_dds_header(self):
        from extract_assets import dds_header
        header=dds_header(8,8,b'DXT1',32)
        self.assertEqual(len(header),128)
        self.assertEqual(header[84:88],b'DXT1')

class Huffman(unittest.TestCase):
    def test_minimal_canonical_stream(self):
        from inspect_assets import huff
        # Two one-bit symbols (0 and 1), clue 255, one zero byte output.
        bits=f'{0x30fb:016b}'+f'{1:024b}'+f'{255:08b}'+'110'+'100'+'100'+'0'
        bits+='0'*(-len(bits)%8)
        body=int(bits,2).to_bytes(len(bits)//8,'big')
        stream=b'HUFF\x01\x10\0\0'+struct.pack('<II',1,len(body))+body
        self.assertEqual(huff(stream),b'\0')
        with self.assertRaises(ValueError):huff(stream[:-1])
    def test_real_headers(self):
        from inspect_assets import chunks,flatten,huff,ROOT
        data=(ROOT/'CARS/COROLLA/TEXTURES.BIN').read_bytes();count=0
        for node in flatten(chunks(data)):
            if node['id']!='0x33310003':continue
            for i in range(node['payload'],node['end'],24):
                key,off,size,out,back,_=struct.unpack_from('<6I',data,i)
                if data[off:off+4]!=b'HUFF':continue
                pool=huff(data[off:off+size])
                self.assertEqual(len(pool),out)
                self.assertEqual(struct.unpack_from('<I',pool,out-back+0x88)[0],key)
                count+=1
        self.assertEqual(count,13)


class Mips(unittest.TestCase):
    def test_exact_chain(self):
        from extract_assets import mip_layout
        levels=mip_layout(32,32,0x24,1344)
        self.assertEqual([(p['width'],p['bytes']) for p in levels],[(32,1024),(16,256),(8,64)])
        for size in (0,1343,1345,2000):
            with self.assertRaises(ValueError):mip_layout(32,32,0x24,size)
    def test_mip_dds(self):
        from extract_assets import dds_header
        header=dds_header(32,32,b'DXT3',1024,3)
        self.assertEqual(struct.unpack_from('<I',header,28)[0],3)
        self.assertTrue(struct.unpack_from('<I',header,8)[0]&0x20000)


class CarTypes(unittest.TestCase):
    def test_real_table_and_empty_rejection(self):
        from inspect_assets import ROOT,cartypes
        self.assertEqual(cartypes(b'CARS/COROLLA/GEOMETRY.BIN'),[])
        records=cartypes((ROOT/'GLOBAL/GLOBALB.BUN').read_bytes())
        self.assertEqual(len(records),46)
        self.assertEqual(len([r for r in records if r['name']=='COROLLA']),1)
        for record in records:self.assertEqual(len(record['wheels']),4)


class AnimationBanks(unittest.TestCase):
    def banks(self,relative,tag):
        from inspect_assets import ROOT,chunks,flatten
        from extract_assets import skip_words
        data=(ROOT/relative).read_bytes()
        return [(data[n['payload']+skip_words(data[n['payload']:n['end']]):n['end']],n['payload']+skip_words(data[n['payload']:n['end']]))
                for n in flatten(chunks(data)) if n['id']==tag]
    def test_float4_curves_and_truncation(self):
        from extract_animation_banks import inspect_bank
        banks=self.banks('CARS/COROLLA/PARTS_ANIMATIONS.bin','0x00e34010')
        self.assertEqual(len(banks),21)
        decoded=[]
        for raw,offset in banks:
            result=inspect_bank(raw,offset);decoded.extend(c for c in result['channels'] if c['decoded'])
            with self.assertRaises(ValueError):inspect_bank(raw[:51],offset)
        self.assertEqual(len(decoded),21)
        self.assertEqual(sum(len(c['values']) for c in decoded),611)
        for curve in decoded:
            self.assertLess(abs(curve['norm_min']-1),1e-5)
            self.assertLess(abs(curve['norm_max']-1),1e-5)
    def test_native_skeletons_and_transforms(self):
        import numpy as np
        from extract_animation_banks import inspect_skeleton
        banks=self.banks('NIS/Scene_IntroNis01_BundleB.bun','0x00e34009')
        self.assertEqual(len(banks),3)
        sizes=[]
        for raw,offset in banks:
            rig=inspect_skeleton(raw,offset);bones=rig['bones'];sizes.append(len(bones))
            self.assertFalse(rig['skeleton'].startswith(':'))
            worlds=[np.linalg.inv(np.array(b['matrix_raw16']).reshape(4,4).T) for b in bones]
            for bone,world in zip(bones,worlds):
                self.assertEqual(bone['index_lane_raw'],bone['index'])
                x,y,z,w=bone['rotation_raw4']
                q=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
                local=np.eye(4);local[:3,:3]=q@np.diag(bone['scale_raw']);local[:3,3]=bone['translation_raw3']
                parent=bone['parent'];actual=world if parent<0 else np.linalg.inv(worlds[parent])@world
                self.assertLess(float(np.max(np.abs(actual-local))),2e-5)
            mutated=bytearray(raw)
            data_section=next(s for s in rig['sections'] if s['name']=='.data')
            parent_at=data_section['offset_in_elf']+rig['skeleton_offset_in_pool']+16+12
            struct.pack_into('<i',mutated,parent_at,0)
            with self.assertRaises(ValueError):inspect_skeleton(mutated,offset)
        self.assertEqual(sizes,[24,24,35])
    def test_executable_sections_rejected(self):
        from extract_animation_banks import inspect_data_elf
        raw,offset=self.banks('CARS/COROLLA/PARTS_ANIMATIONS.bin','0x00e34010')[0]
        mutated=bytearray(raw);section_table=struct.unpack_from('<I',raw,32)[0]
        struct.pack_into('<I',mutated,section_table+40+8,7)
        with self.assertRaises(ValueError):inspect_data_elf(mutated,offset)


class HeaderRepairPreview(unittest.TestCase):
    def test_exact_eight_byte_repair_only(self):
        from inspect_assets import ROOT,chunks
        from plan_header_repair import repair_preview
        source=ROOT/'CARS/COROLLA/GEOMETRY.BIN'
        backup=source.with_name(source.name+'.bak')
        data=(backup if backup.exists() else source).read_bytes()
        corrected,changes=repair_preview(data)
        if backup.exists():self.assertEqual(source.read_bytes(),corrected)
        self.assertEqual(len(changes),4)
        self.assertEqual(len(corrected),len(data))
        self.assertEqual(chunks(data),chunks(corrected))
        expected={c['offset']+i for c in changes for i in (2,3)}
        actual={i for i,(a,b) in enumerate(zip(data,corrected)) if a!=b}
        self.assertEqual(actual,expected)
        for c in changes:self.assertEqual(struct.unpack_from('<I',corrected,c['offset'])[0],16557)
        with self.assertRaises(ValueError):repair_preview(corrected)
    def test_other_car_rejected(self):
        from inspect_assets import ROOT
        from plan_header_repair import repair_preview
        with self.assertRaises(ValueError):repair_preview((ROOT/'CARS/240SX/GEOMETRY.BIN').read_bytes())


class NativeSkin(unittest.TestCase):
    def test_real_skin_and_corrupt_weight(self):
        from inspect_assets import ROOT
        from extract_native_skin import read_skin
        data=(ROOT/'NIS/Scene_IntroNis01_BundleB.bun').read_bytes()
        meshes=read_skin(data)
        self.assertEqual(len(meshes),5)
        self.assertEqual(sum(len(m['weights']) for m in meshes),4265)
        self.assertEqual([m['bone_count_byte'] for m in meshes],[24,24,24,24,35])
        for mesh in meshes:
            self.assertEqual(sum(r['count'] for r in mesh['skin_runs']),len(mesh['indices']))
            for run in mesh['skin_runs']:
                self.assertEqual(len(run['palette16_raw']),16)
                self.assertLess(max(run['candidate_global_bone_indices_used']),mesh['bone_count_byte'])
        mutated=bytearray(data);at=meshes[0]['vertex_data_absolute_offset']
        struct.pack_into('<f',mutated,at+36,1.5)
        with self.assertRaises(ValueError):read_skin(mutated)
        mutated=bytearray(data);struct.pack_into('<f',mutated,at+48,16)
        with self.assertRaises(ValueError):read_skin(mutated)

if __name__ == '__main__': unittest.main()

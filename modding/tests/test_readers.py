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
    def test_vertex_offsets_address_decoded_records(self):
        from extract_assets import geometry
        for car in ('COROLLA','240SX'):
            data=data_path(f'CARS/{car}/GEOMETRY.BIN').read_bytes()
            meshes=geometry(data,'BODY_')
            self.assertTrue(meshes)
            for mesh in meshes:
                at=mesh['vertex_data_offset'];stride=mesh['stride']
                for index in (0,len(mesh['positions'])-1):
                    self.assertEqual(struct.unpack_from('<3f',data,at+index*stride),mesh['positions'][index],mesh['name'])
                self.assertEqual(struct.unpack_from('<2f',data,at+stride-8),mesh['uv'][0],mesh['name'])
    def test_current_character_upload_signature(self):
        from extract_assets import geometry
        from inspect_assets import ROOT
        asset=(ROOT/'modding/runtime/kitasan.umab').read_bytes()
        count=struct.unpack_from('<I',asset,8)[0];expected=asset[32:32+count*36]
        self.assertEqual(len(expected),522432)
        data=data_path('CARS/COROLLA/GEOMETRY.BIN').read_bytes()
        meshes=geometry(data,'KIT00_BODY_');self.assertEqual(len(meshes),4)
        for mesh in meshes:
            start=mesh['vertex_data_offset']
            self.assertEqual(data[start:start+len(expected)],expected,mesh['name'])
    def test_binary_identity_survives_truncated_name_collisions(self):
        from extract_assets import geometry,payload
        from inspect_assets import flatten
        for car in ('COROLLA','240SX'):
            data=data_path(f'CARS/{car}/GEOMETRY.BIN').read_bytes();meshes=geometry(data,'')
            identities={mesh['asset_hash']:mesh for mesh in meshes}
            self.assertEqual(len(identities),len(meshes))
            self.assertLess(len({mesh['name'] for mesh in meshes}),len(meshes))
            count=0
            for node in flatten(chunks(data)):
                if node['id']!='0x00134004':continue
                records=payload(data,node)
                for at in range(0,len(records),24):
                    key,offset=struct.unpack_from('<2I',records,at)
                    self.assertEqual(identities[f'0x{key:08x}']['solid_offset'],offset)
                    count+=1
            self.assertEqual(count,len(meshes))
    def test_compaction_verifier_rejects_uncompacted_source(self):
        from plan_hidden_compaction import verify_compaction,reviewed_source
        data=reviewed_source().read_bytes()
        with self.assertRaisesRegex(ValueError,'Invalid compact degenerate mesh'):
            verify_compaction(data,data)
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
        if backup.exists():
            material_baseline=source.with_name(source.name+'.before-material.bak')
            self.assertEqual((material_baseline if material_baseline.exists() else source).read_bytes(),corrected)
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


class MaterialProbe(unittest.TestCase):
    def test_exact_material_only_preview(self):
        from inspect_assets import ROOT,chunks
        from plan_material_probe import material_preview
        source=ROOT/'CARS/COROLLA/GEOMETRY.BIN'
        backup=source.with_name(source.name+'.before-material.bak')
        data=(backup if backup.exists() else source).read_bytes()
        result,changes=material_preview(data)
        self.assertEqual(len(changes),4)
        self.assertEqual(chunks(data),chunks(result))
        expected={c['offset']+i for c in changes for i in range(4)}
        self.assertEqual({i for i,(a,b) in enumerate(zip(data,result)) if a!=b},expected)
        if backup.exists():
            from plan_hidden_compaction import reviewed_source
            self.assertEqual(reviewed_source().read_bytes(),result)
        with self.assertRaises(ValueError):material_preview(result)
    def test_native_material_definition(self):
        from inspect_assets import ROOT,chunks,flatten
        from extract_assets import payload
        data=(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes()
        definitions=[payload(data,n) for n in flatten(chunks(data)) if n['id']=='0x00135200']
        matches=[r for r in definitions if struct.unpack_from('<I',r,12)[0]==0x0fedee40]
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0][20:48].split(b'\0')[0],b'DULLPLASTIC')


class CharacterBounds(unittest.TestCase):
    def test_exact_fields_and_full_geometry_containment(self):
        from inspect_assets import ROOT,chunks,flatten
        from extract_assets import geometry,payload
        from plan_bounds_repair import bounds_preview
        source=ROOT/'CARS/COROLLA/GEOMETRY.BIN';backup=source.with_name(source.name+'.before-bounds.bak')
        from plan_hidden_compaction import reviewed_source
        data=(backup if backup.exists() else reviewed_source()).read_bytes();result,changes=bounds_preview(data)
        self.assertEqual(chunks(data),chunks(result));self.assertEqual(len(changes),4)
        allowed={f['offset']+j for c in changes for f in c['fields'] for j in range(4)}
        changed={i for i,(a,b) in enumerate(zip(data,result)) if a!=b}
        self.assertEqual(len(changed),85);self.assertTrue(changed<=allowed)
        nodes={n['offset']:n for n in flatten(chunks(result))}
        for mesh in geometry(result,'_KIT00_BODY_'):
            solid=nodes[mesh['solid_offset']]
            r=next(n for n in flatten(solid['children']) if n['id']=='0x00134b02')
            raw=payload(result,r);lead=len(raw)%60
            lower=struct.unpack_from('<3f',raw,lead);upper=struct.unpack_from('<3f',raw,lead+16)
            for index in mesh['indices']:
                for axis in range(3):self.assertLessEqual(lower[axis],mesh['positions'][index][axis]);self.assertGreaterEqual(upper[axis],mesh['positions'][index][axis])
        with self.assertRaises(ValueError):bounds_preview(result)
        if backup.exists():
            from plan_hidden_compaction import reviewed_source
            self.assertEqual(reviewed_source().read_bytes(),result)
    def test_unrelated_car_rejected(self):
        from inspect_assets import ROOT
        from plan_bounds_repair import bounds_preview
        with self.assertRaises(ValueError):bounds_preview((ROOT/'CARS/240SX/GEOMETRY.BIN').read_bytes())


class AuthoredMotion(unittest.TestCase):
    def test_rotation_alignment_edges(self):
        import numpy as np
        from animate_kitasan import align
        for a,b in [([1,0,0],[1,0,0]),([1,0,0],[-1,0,0]),([0,0,-1],[1,0,0])]:
            r=align(a,b);self.assertTrue(np.allclose(r@np.array(a),b,atol=1e-7));self.assertAlmostEqual(np.linalg.det(r),1)
        with self.assertRaises(ValueError):align([0,0,0],[1,0,0])
    def test_rest_loop_and_planted_feet(self):
        import numpy as np
        from animate_kitasan import Rig,leg_target
        rig=Rig();identity=np.repeat(np.eye(3)[None],len(rig.bones),0)
        _,rest=rig.world(identity,np.zeros_like(rig.rest));p,n=rig.skin(identity,rest-rig.rest)
        self.assertTrue(np.allclose(p,rig.records[:,:3],atol=1e-5))
        a=rig.pose(0)[0:2];b=rig.pose(1)[0:2]
        for x,y in zip(a,b):self.assertTrue(np.array_equal(x,y))
        ankle=rig.rest[rig.named['左足首D']]
        x0,_,stance0=leg_target(.1,ankle,1);x1,_,stance1=leg_target(.2,ankle,1)
        self.assertTrue(stance0 and stance1);self.assertEqual(x0[2],x1[2]);self.assertAlmostEqual((x1[0]-x0[0])/.1,-.62/.38)
    def test_pose_floor_limb_lengths_and_arms(self):
        import numpy as np
        from animate_kitasan import Rig
        rig=Rig()
        for amount in (0,.5,1):
            for phase in (0,.125,.25,.5,.75):
                rotation,offset,joints,feet=rig.pose(phase,amount);p,n=rig.skin(rotation,offset)
                self.assertGreater(float(p[:,2].min()),-.005);self.assertLess(float(np.abs(p).max()),4)
                self.assertTrue(np.allclose(np.linalg.norm(n,axis=1),1,atol=1e-5))
                for foot in feet:self.assertLess(float(np.linalg.norm(joints[foot['ankle']]-foot['target'])),.005)
                for side in ('左','右'):
                    ids=[rig.named[side+j+'D'] for j in ('足','ひざ','足首')]
                    for a,b in zip(ids,ids[1:]):self.assertAlmostEqual(float(np.linalg.norm(joints[b]-joints[a])),float(np.linalg.norm(rig.rest[b]-rig.rest[a])),places=6)
                    upper,elbow=[rig.named[side+j] for j in ('腕','ひじ')]
                    self.assertLess(joints[elbow,2],joints[upper,2]-.1)
        with self.assertRaises(ValueError):rig.pose(float('nan'))
        with self.assertRaises(ValueError):rig.pose(0,2)
    def test_native_winding_calibration(self):
        import numpy as np
        from inspect_assets import ROOT
        from extract_assets import geometry
        for m in geometry((ROOT/'CARS/240SX/GEOMETRY.BIN').read_bytes(),'240SX_KIT00_BODY_D'):
            p=np.array(m['positions']);n=np.array(m['normals']);t=np.array(m['indices']).reshape(-1,3)
            cross=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])
            valid=np.linalg.norm(cross,axis=1)>1e-10
            self.assertGreater(float(((cross*n[t].mean(1)).sum(1)[valid]>0).mean()),.99)

if __name__ == '__main__': unittest.main()

class CapturedShaderProfiles(unittest.TestCase):
    def test_real_programs_and_skinning_rejection(self):
        from inspect_assets import ROOT
        from profile_captured_shaders import matrix_rows
        programs={}
        for line in (ROOT/'modding/diagnostics/game-pipeline-session-1.log').read_text().splitlines():
            if line.startswith('VS '):programs[int(line.split('id=')[1].split()[0])]=[int(v,16) for v in line.split('words=')[1].split()]
        self.assertEqual(matrix_rows(programs[5]),[(10,1),(11,1),(12,1),(13,1)])
        with self.assertRaises(ValueError):matrix_rows(programs[9])
    def test_temporary_moves_and_overwrite_rejection(self):
        from profile_captured_shaders import matrix_rows
        code=[0xfffe0101]
        for k in range(4):code += [9,0x80000000|((1<<k)<<16),0x90e40000,0xa0e40000+k]
        code += [1,0xc00f0000,0x80e40000,65535]
        self.assertEqual(matrix_rows(code),[(k,1) for k in range(4)])
        with self.assertRaises(ValueError):matrix_rows(code[:-1]+[2,0xc0010000,0x80e40000,0xa0e40001,65535])
    def test_relative_constants_and_truncation_rejected(self):
        from profile_captured_shaders import matrix_rows
        code=[0xfffe0101,20,0xc00f0000,0x90e40000,0xa0e40000,65535]
        self.assertEqual(matrix_rows(code),[(k,1) for k in range(4)])
        bad=code.copy();bad[4]|=0x2000
        for raw in (bad,code[:-1],[0xfffe0101,0x7fff_fffe,65535]):
            with self.assertRaises(ValueError):matrix_rows(raw)
        defined=[0xfffe0101,81,0xa00f0000,0,0,0,0]+code[1:]
        with self.assertRaises(ValueError):matrix_rows(defined)

class InstalledRuntimeGeometry(unittest.TestCase):
    def test_installed_compact_geometry_and_motion_bounds(self):
        import hashlib,json
        from inspect_assets import ROOT
        from plan_hidden_compaction import verify_compaction,reviewed_source
        receipt=json.loads((ROOT/'modding/runtime-geometry-applied.json').read_text())
        data=data_path('CARS/COROLLA/GEOMETRY.BIN.before-skin-slot.bak').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),receipt['installed_sha256'])
        report=verify_compaction(reviewed_source().read_bytes(),data)
        self.assertEqual(report['collapsed_solids_compacted'],567)
        self.assertEqual(report['vertices_after'],59749)
        self.assertEqual(report['solid_directory_records_verified'],571)
        for field in receipt['fields']:
            self.assertEqual(data[field['offset']:field['offset']+4].hex(),field['after'])

class BodyMaterialRoute(unittest.TestCase):
    def test_only_reviewed_material_fields_changed(self):
        import hashlib,json
        from inspect_assets import ROOT
        from route_body_material import route_body
        source=(ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-skin-slot.bak').read_bytes()
        plan=json.loads((ROOT/'modding/staged-runtime/geometry-plan.json').read_text())
        expected,changes=route_body(source,plan['minimum'],plan['maximum'])
        self.assertEqual(expected,(ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-effects.bak').read_bytes())
        self.assertEqual(len(changes),36)
        self.assertEqual(hashlib.sha256(expected).hexdigest(),'20498c7d93be4bdc57a19db72d246ae79f56cfbd3bd13235199524ebc545cf28')
        with self.assertRaises(ValueError):route_body(expected,plan['minimum'],plan['maximum'])

class CarEffectCandidates(unittest.TestCase):
    def test_exact_optional_marker_hash_edits(self):
        from inspect_assets import ROOT
        from disable_car_effects import disable_effects
        from extract_assets import geometry
        source=(ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-effects.bak').read_bytes()
        candidate,changes=disable_effects(source)
        self.assertEqual(candidate,(ROOT/'modding/staged-runtime/GEOMETRY-effects.BIN').read_bytes())
        self.assertEqual(len(changes),214)
        mask=bytearray(len(source))
        for c in changes:mask[c['offset']:c['offset']+4]=b'\1'*4
        self.assertTrue(all(x==y or mask[i] for i,(x,y) in enumerate(zip(source,candidate))))
        old,new=geometry(source,''),geometry(candidate,'')
        for a,b in zip(old,new):
            for field in ('asset_hash','positions','normals','uv','indices','transform','material_runs'):self.assertEqual(a[field],b[field])
            self.assertEqual([m['matrix'] for m in a['markers']],[m['matrix'] for m in b['markers']])
        with self.assertRaises(ValueError):disable_effects(candidate)

    def test_shadow_format_and_unrelated_texture_preservation(self):
        from inspect_assets import ROOT
        from verify_foot_shadow import verify
        original=(ROOT/'CARS/COROLLA/TEXTURES.BIN.before-foot-shadow.bak').read_bytes()
        candidate=(ROOT/'modding/staged-runtime/TEXTURES-shadow.BIN').read_bytes()
        result=verify(original,candidate)
        self.assertEqual(result['textures'],56)
        self.assertTrue(result['metadata_unchanged'])
        with self.assertRaises(ValueError):verify(original,candidate[:-1])

"""Stage 350Z's compact character shadow with the validated native JDLZ ending."""
import hashlib,json,struct
from inspect_assets import ROOT
from prepare_shadow_guard import descriptors
from verify_foot_shadow import pools,verify
from prepare_kitasan_badge import compress_jdlz
from jdlz_native import finish_native,validate_native
from disable_car_effects import string_hash


def main(slot='350Z', staging='gentildonna'):
 source=ROOT/'CARS'/slot/'TEXTURES.BIN';original=source.read_bytes();out=bytearray(original);entries=descriptors(original);old=pools(original);template=pools((ROOT/'CARS/COROLLA/TEXTURES.BIN').read_bytes())
 for suffix in ('FE','IG'):
  key=string_hash(slot+'_SHADOW'+suffix);at,entry=entries[key];pool,header=old[key];sample,sample_header=template[string_hash('COROLLA_SHADOW'+suffix)];size=struct.unpack_from('<I',pool,header+20)[0];assert size==10880 and size==struct.unpack_from('<I',sample,sample_header+20)[0]
  edited=sample[:size]+pool[size:];encoded=finish_native(compress_jdlz(edited));assert len(encoded)<=entry[2];validate_native(encoded)
  out[entry[1]:entry[1]+len(encoded)]=encoded;struct.pack_into('<I',out,at+8,len(encoded))
 result=verify(original,bytes(out),slot);folder=ROOT/'modding/staged-runtime'/staging;(folder/'TEXTURES.BIN').write_bytes(out);(folder/'shadow.json').write_text(json.dumps({'target':f'CARS/{slot}/TEXTURES.BIN','before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(out).hexdigest(),'verification':result,'installed':False},indent=2)+'\n');print(result)

if __name__=='__main__':main()

"""Read-only BVH audit of actual non-spring body triangles versus dynamic garments."""
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import blender_diamond_intersections as source
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def main():
    root=source.ROOT
    garments=source.sets['garment']
    body=[]
    for group in source.meta['groups']:
        if not group['material'].startswith('mtl_bdy'):continue
        for t in range(group['first_index']//3,(group['first_index']+group['index_count'])//3):
            ids=source.triangles[t]
            if len(set(ids))==3 and max(source.weights[v] for v in ids)<=.05:body.append((t,ids))
    assert body and garments
    out=root/'modding/diagnostics/triangle-contact-prototype'
    rows=[]
    for path in sorted((out/'native-poses').glob('*.umap')):
        data=path.read_bytes();assert struct.unpack_from('<4s2I',data)==(b'UMAP',1,source.nv)
        vertices=[Vector(struct.unpack_from('<3f',data,12+v*36)) for v in range(source.nv)]
        left=BVHTree.FromPolygons(vertices,[ids for _,ids in garments],all_triangles=True)
        right=BVHTree.FromPolygons(vertices,[ids for _,ids in body],all_triangles=True)
        hits=[]
        for i,j in left.overlap(right):
            ti,a=garments[i];tj,b=body[j]
            if set(a).intersection(b):continue
            if source.crossing([vertices[v] for v in a],[vertices[v] for v in b]):hits.append([ti,tj])
        rows.append({'pose':path.stem,'crossing_pairs':len(hits),'pairs':hits})
        print(path.stem,len(hits),flush=True)
    report={'scope':'Exact noncoplanar triangle crossings against non-spring-weighted body material geometry; not an anatomically labelled or necessarily closed skin surface. Excludes shared-index faces and tangencies. Native garment contacts are not modified.',
            'body_triangles':len(body),'garment_triangles':len(garments),'results':rows}
    (out/'diamond-body-crossing-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

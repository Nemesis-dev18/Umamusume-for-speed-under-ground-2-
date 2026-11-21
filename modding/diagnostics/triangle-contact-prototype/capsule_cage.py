"""Closed experimental limb collision cages; native rendered meshes are unchanged."""
import json
import math
import unittest
from collections import Counter
from pathlib import Path


def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return [x-y for x,y in zip(a,b)]


def build(contacts):
    vertices=[];faces=[];owners=[]
    for contact in contacts:
        a,b,r=contact['a'],contact['b'],contact['radius']
        axis=sub(b,a);length=math.sqrt(dot(axis,axis));assert length>1e-6 and .001<r<1
        axis=[v/length for v in axis]
        ref=[0.,0.,0.];ref[min(range(3),key=lambda k:abs(axis[k]))]=1
        u=cross(axis,ref);norm=math.sqrt(dot(u,u));u=[v/norm for v in u];v=cross(axis,u)
        offset=len(vertices);local=[[a[k]-r*axis[k] for k in range(3)]]
        for center,angles in ((a,(-3*math.pi/8,-math.pi/4,-math.pi/8,0)),(b,(0,math.pi/8,math.pi/4,3*math.pi/8))):
            for theta in angles:
                for j in range(16):
                    phi=2*math.pi*j/16
                    local.append([center[k]+r*math.sin(theta)*axis[k]+r*math.cos(theta)*(u[k]*math.cos(phi)+v[k]*math.sin(phi)) for k in range(3)])
        local.append([b[k]+r*axis[k] for k in range(3)])
        triangles=[(0,1+j,1+(j+1)%16) for j in range(16)]
        for ring in range(7):
            for j in range(16):
                p,q=1+ring*16+j,1+ring*16+(j+1)%16
                triangles.extend(((p,q,q+16),(p,q+16,p+16)))
        triangles.extend((129,113+j,113+(j+1)%16) for j in range(16))
        for face in triangles:
            p,q,t=(local[i] for i in face);normal=cross(sub(q,p),sub(t,p));center=[(p[k]+q[k]+t[k])/3 for k in range(3)]
            along=max(0,min(length,dot(sub(center,a),axis)));radial=[center[k]-a[k]-along*axis[k] for k in range(3)]
            assert dot(normal,normal)>1e-20
            if dot(normal,radial)<0:face=(face[0],face[2],face[1])
            faces.append(tuple(offset+i for i in face))
        vertices.extend(local);owners.extend([contact['bone_a']]*len(local))
    counts=Counter(tuple(sorted((face[j],face[(j+1)%3]))) for face in faces for j in range(3))
    assert counts and all(n==2 for n in counts.values())
    return vertices,faces,owners


class CageTests(unittest.TestCase):
    def test_closed_capsule_bounds_and_surface(self):
        c={'a':[0,0,0],'b':[0,0,1],'radius':.1,'bone_a':0}
        vertices,faces,owners=build([c]);self.assertEqual((len(vertices),len(faces),len(owners)),(130,256,130))
        self.assertAlmostEqual(min(p[2] for p in vertices),-.1)
        self.assertAlmostEqual(max(p[2] for p in vertices),1.1)
        for p in vertices:self.assertAlmostEqual(math.sqrt(p[0]**2+p[1]**2+(p[2]-max(0,min(1,p[2])))**2),.1)

    def test_zero_length_is_rejected(self):
        with self.assertRaises(AssertionError):build([{'a':[0,0,0],'b':[0,0,0],'radius':.1,'bone_a':0}])


def main():
    here=Path(__file__).resolve().parent;out=here.parent/'blender-cloth-trial'
    contacts=json.loads((out/'limb-contacts-fit.json').read_text())['contacts']
    vertices,faces,owners=build(contacts)
    report={'scope':'Closed outward-oriented limb-only cage for offline collision trials, not a render model or accepted body fit.','vertices':vertices,'triangles':faces,'bone_owner':owners,'accepted_for_game':False}
    (out/'limb-contact-cage.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
    print('PASS closed cage',len(vertices),'vertices',len(faces),'triangles')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CageTests)
    result=unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    main()

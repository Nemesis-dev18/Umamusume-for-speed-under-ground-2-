import unittest
from mesh import physical_mesh


class PhysicalMeshTests(unittest.TestCase):
    def fixture(self):
        return {'weights':{'0':0,'1':1,'2':1,'3':1},'candidate_seams':[[1,3]],'triangles':[[0,1,2],[0,2,3]]}

    def test_seam_shares_particle_and_retains_pinned_attachment(self):
        roots,mapping,triangles,edges,mass=physical_mesh(self.fixture())
        self.assertEqual(roots,[0,1,2])
        self.assertEqual(mapping[1],mapping[3])
        self.assertEqual(mass,[0,1,1])
        self.assertEqual(len(triangles),2)
        self.assertEqual(len(edges),3)

    def test_incompatible_attachment_is_rejected(self):
        data=self.fixture();data['weights']['3']=0
        with self.assertRaises(AssertionError):physical_mesh(data)

    def test_collapsed_triangle_is_rejected(self):
        data=self.fixture();data['triangles']=[[0,1,3]]
        with self.assertRaises(AssertionError):physical_mesh(data)


if __name__=='__main__':unittest.main()

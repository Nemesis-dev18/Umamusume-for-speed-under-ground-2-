import unittest
from mesh import physical_mesh,root_attachment_weights,proximal_attachment_weights


class PhysicalMeshTests(unittest.TestCase):
    def test_native_chain_root_attaches_but_distal_bones_remain_free(self):
        parents=[-1,0,1,2,0]
        skins=[([0],[1]),([1],[1]),([2],[1]),([3],[1]),([4],[1]),([1,2],[.25,.75])]
        self.assertEqual(root_attachment_weights(parents,{1,2},skins),[1,1,0,0,1,.25])

    def test_invalid_hierarchy_is_rejected(self):
        with self.assertRaises(AssertionError):root_attachment_weights([1,-1],{0},[])

    def test_proximal_seam_retains_attachment_and_frees_distal_panel(self):
        parents=[-1,0,1];skins=[([1],[1]) for _ in range(4)]
        weights=proximal_attachment_weights(parents,{1,2},skins,[[0,0,z] for z in (0,.1,.2,.3)],{1:[0,0,0]},{1:[0,0,1]},[(0,1),(1,2),(2,3)])
        self.assertEqual(weights,[1,1,.5,0])

    def test_child_only_piece_does_not_gain_an_invented_attachment(self):
        weights=proximal_attachment_weights([-1,0,1],{1,2},[([2],[1])],[[0,0,1]],{1:[0,0,0]},{1:[0,0,1]},[])
        self.assertEqual(weights,[0])

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

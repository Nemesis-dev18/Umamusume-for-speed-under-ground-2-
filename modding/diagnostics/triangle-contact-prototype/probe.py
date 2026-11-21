"""Offline experiment: coupled triangle/capsule and edge constraints. Not used by the game."""
import math
import unittest


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def closest_triangle(p, tri):
    a, b, c = tri
    ab, ac = sub(b, a), sub(c, a)
    normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
    nn = dot(normal, normal)
    candidates = []
    if nn > 1e-20:
        distance = dot(sub(p, a), normal)/nn
        projected = [p[k]-distance*normal[k] for k in range(3)]
        v = sub(projected, a)
        aa, bb, cc = dot(ab, ab), dot(ab, ac), dot(ac, ac)
        denom = aa*cc-bb*bb
        if denom > 1e-20:
            y = (dot(v, ab)*cc-dot(v, ac)*bb)/denom
            z = (dot(v, ac)*aa-dot(v, ab)*bb)/denom
            bary = [1-y-z, y, z]
            if min(bary) >= 0:
                candidates.append((projected, bary))
    for i, j in ((0, 1), (1, 2), (2, 0)):
        edge = sub(tri[j], tri[i])
        length = dot(edge, edge)
        t = max(0, min(1, dot(sub(p, tri[i]), edge)/length)) if length else 0
        q = [tri[i][k]+t*edge[k] for k in range(3)]
        bary = [0., 0., 0.]
        bary[i], bary[j] = 1-t, t
        candidates.append((q, bary))
    return min(candidates, key=lambda item: dot(sub(item[0], p), sub(item[0], p)))


def closest_capsule_axis(start, end, tri):
    # Squared distance to a convex triangle is convex along a segment.
    def sample(t):
        center = [start[k]+t*(end[k]-start[k]) for k in range(3)]
        q, bary = closest_triangle(center, tri)
        return dot(sub(q, center),sub(q, center)), q, bary, center
    lo, hi = 0., 1.
    for _ in range(72):
        a, b = (2*lo+hi)/3, (lo+2*hi)/3
        if sample(a)[0] <= sample(b)[0]:
            hi = b
        else:
            lo = a
    _, q, bary, center = min((sample(0),sample(1),sample((lo+hi)/2)), key=lambda item:item[0])
    return q, bary, center


def contact(tri, mass, center, radius, end=None):
    if end is None:
        q, bary = closest_triangle(center, tri)
    else:
        q, bary, center = closest_capsule_axis(center, end, tri)
    delta = sub(q, center)
    distance = math.sqrt(dot(delta, delta))
    if distance >= radius:
        return 0
    denom = sum(m*b*b for m, b in zip(mass, bary))
    if denom <= 1e-20 or distance <= 1e-12:
        return radius-distance  # exact overlap needs a temporally persistent side
    for i in range(3):
        amount = mass[i]*bary[i]*(radius-distance)/denom/distance
        for k in range(3):
            tri[i][k] += amount*delta[k]
    return radius-distance


def solve(tri, mass, center, radius, iterations=100, end=None):
    lengths = {(i,j): math.dist(tri[i], tri[j]) for i,j in ((0,1),(1,2),(2,0))}
    for _ in range(iterations):
        for (i,j), original in lengths.items():
            delta = sub(tri[j], tri[i])
            length = math.sqrt(dot(delta, delta))
            if not length or not mass[i]+mass[j]:
                continue
            correction = (length-original)/(length*(mass[i]+mass[j]))
            for k in range(3):
                tri[i][k] += mass[i]*correction*delta[k]
                tri[j][k] -= mass[j]*correction*delta[k]
        contact(tri, mass, center, radius, end)
    return max(abs(math.dist(tri[i], tri[j])/length-1) for (i,j),length in lengths.items())


class Probe(unittest.TestCase):
    def test_interior_separates_without_panel_stretch(self):
        tri = [[-.2,-.2,.02],[.2,-.2,.02],[0,.2,.02]]
        self.assertTrue(all(math.dist(p,[0,0,0])>.05 for p in tri))
        strain = solve(tri,[1,1,1],[0,0,0],.053)
        point,_ = closest_triangle([0,0,0],tri)
        self.assertGreaterEqual(math.dist(point,[0,0,0]),.053-1e-6)
        self.assertLess(strain,.001)

    def test_pinned_corner_stays_fixed(self):
        tri = [[-.2,-.2,.02],[.2,-.2,.02],[0,.2,.02]]
        pinned = tri[0][:]
        strain = solve(tri,[0,1,1],[0,0,0],.053)
        self.assertEqual(tri[0],pinned)
        point,_ = closest_triangle([0,0,0],tri)
        self.assertGreaterEqual(math.dist(point,[0,0,0]),.053-1e-6)
        self.assertLess(strain,.001)

    def test_capsule_middle_detected_when_end_spheres_are_remote(self):
        tri = [[-.2,-.2,.02],[.2,-.2,.02],[0,.2,.02]]
        start, end = [-1,0,0],[1,0,0]
        for p in (start,end):
            point,_ = closest_triangle(p,tri)
            self.assertGreater(math.dist(point,p),.053)
        point, bary, axis = closest_capsule_axis(start,end,tri)
        self.assertAlmostEqual(math.dist(point,axis),.02,places=8)
        self.assertAlmostEqual(sum(bary),1)
        strain = solve(tri,[1,1,1],start,.053,end=end)
        point,_,axis = closest_capsule_axis(start,end,tri)
        self.assertGreaterEqual(math.dist(point,axis),.053-1e-6)
        self.assertLess(strain,.001)

    def test_capsule_axis_piercing_reports_unresolved_contact(self):
        tri = [[-.2,-.2,0],[.2,-.2,0],[0,.2,0]]
        before = [p[:] for p in tri]
        point,_,axis = closest_capsule_axis([0,0,-1],[0,0,1],tri)
        self.assertLess(math.dist(point,axis),1e-12)
        self.assertGreater(contact(tri,[1,1,1],[0,0,-1],.053,end=[0,0,1]),0)
        self.assertEqual(tri,before)

    def test_zero_length_capsule_matches_sphere(self):
        tri = [[-.2,-.2,.02],[.2,-.2,.02],[0,.2,.02]]
        sphere = [p[:] for p in tri]
        contact(tri,[1,1,1],[0,0,0],.053,end=[0,0,0])
        contact(sphere,[1,1,1],[0,0,0],.053)
        self.assertEqual(tri,sphere)

    def test_fully_pinned_panel_reports_unresolved_contact(self):
        tri = [[-.2,-.2,.02],[.2,-.2,.02],[0,.2,.02]]
        before = [p[:] for p in tri]
        self.assertGreater(contact(tri,[0,0,0],[0,0,0],.053),0)
        self.assertEqual(tri,before)

    def test_exact_overlap_is_not_silently_claimed_resolved(self):
        tri = [[-.2,-.2,0],[.2,-.2,0],[0,.2,0]]
        before = [p[:] for p in tri]
        self.assertGreater(contact(tri,[1,1,1],[0,0,0],.053),0)
        self.assertEqual(tri,before)

    def test_remote_and_degenerate_triangle(self):
        tri = [[2.,0,0]]*3
        self.assertEqual(contact(tri,[1,1,1],[0,0,0],.05),0)
        self.assertEqual(tri,[[2.,0,0]]*3)


if __name__ == '__main__':
    unittest.main()

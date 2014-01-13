import clustering
import unittest

class Test(unittest.TestCase):

    def test_dist(self):
        self.assertEqual(clustering.dist([3,4], [0,0]), 5.0)
        self.assertEqual(clustering.dist([0,0], [3,4]), 5.0)

    def test_find_closest_centroids(self):
        data_pts = [["",0,1], ["",3,1], ["",6,1]]
        centroids = [[0,0], [3,4], [6,0]]
        idx = clustering.find_closest_centroids(data_pts, centroids)
        self.assertEqual(idx, [0,1,2])

    def test_compute_centroids(self):
        data_pts = [["",0,1], ["",3,3], ["",6,1]]
        idx = [0,1,0]
        k = 2
        centroids = clustering.compute_centroids(data_pts, idx, k)
        self.assertEqual(centroids, [[3,1], [3,3]])


if __name__ == "__main__":
    unittest.main()
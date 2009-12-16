import calc
import logging
import sys

import unittest

class TestTimeScore(unittest.TestCase):
    def test_base(self):
        sc = calc.Score()
        self.assertEqual(sc.score, 1.0)
        self.assertEqual(sc.log_score, 0.0)
        self.assertEqual(sc.time_last, 0)
        sc.increment(0)
        self.assertEqual(sc.score, 1.0)
        self.assertEqual(sc.log_score, 0.0)
        
    def test_incr(self):
        sc = calc.Score()
        sc.increment(1)
        self.assertEqual(sc.score, 2.0)
        sc.increment(1,1)
        self.assertEqual(sc.score, 2.0)
        
    def test_series(self):
        sc = calc.Score()
        for t in range(1,10):
            sc.increment(1, t)
        self.assertAlmostEqual(sc.score, 2.0, 2)

        for t in range(10,20):
            sc.increment(1, t)
        self.assertAlmostEqual(sc.score, 2.0, 5)
        
    def test_series24(self):
        sc = calc.Score(time_half=24)
        
        for t in range(1,20):
            sc.increment(1, t*24)
        self.assertAlmostEqual(sc.score, 2.0, 5)
        
    def test_zero(self):
        sc = calc.Score(log_score=0)
        sLog = sc.log_score
        sc.increment(0)
        self.assertEqual(sc.log_score, sLog)
        sc.increment(0, 1)
        self.assertEqual(sc.log_score, sLog)

class TestRateLimit(unittest.TestCase):
    def test_base(self):
        rate = calc.RateLimit(0)
        self.assertEqual(rate.current_value(10), 0)
        v = rate.current_value(20, 100)
        self.assertEqual(v, 100)
        self.assertEqual(rate.current_value(20), 100)
        self.assertAlmostEqual(rate.current_value(80), 50)
        self.assertAlmostEqual(rate.current_value(140), 25)
        
        rate = calc.RateLimit(0)
        v = rate.current_value(1)
        for x in range(1, 100):
            v2 = rate.current_value(x,1)
            self.assert_(v2 > v)
            self.assert_(v2 < 100)
            v = v2

    def test_limits(self):
        rate = calc.RateLimit(75)
        for x in range(1,200):
            v = rate.current_value(x)
            self.assert_(v <= 75)
            if rate.is_exceeded(x):
                break
        self.assert_(x > 100)
        
    def test_converge(self):
        for half in range(1,50,10):
            rate = calc.RateLimit(100,half)
            limit = 1.0/(1.0 - rate.k)
            for x in xrange(half*10):
                rate.is_exceeded(x)
            #print "Half life: %d -> %.2f" % (half, rate.current_value(x))           
            self.assertAlmostEqual(rate.current_value(x), limit, 0)
        
if __name__ == '__main__':
    unittest.main()
#! /usr/bin/env python

"""Test the timing between the old and new condition.py functions
"""
import timeit
import numpy as np
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils.condition import condition
from jwql.instrument_monitors.miri_monitors.data_trending.utils.condition import condition as old_condition


c = condition(4)
#good = [0., 1., 2., 3., 4., 7., 8., 9., 12., 14., 15., 16., 18., 19., 20.]
#bad = [5, 6, 10, 11, 13, 17]

tf = [True] * 5
for i in range(30):
    tf = tf + [False]*10
    tf = tf + [True]*10
tf = np.array(tf, dtype=int)

dt = 0.5  # seconds between entries
good = np.where(tf == 1)[0]
good = list(good.astype(float) * dt)
bad = np.where(tf == False)[0]
bad = list(bad.astype(float) * dt)

t = timeit.timeit(lambda: c.generate_time_pairs(good, bad), number=10)
print(t)
# 0.013202833999999997 seconds


oldc = old_condition(4)
oldt = timeit.timeit(lambda: oldc.generate_time_pairs(good, bad), number=10)
print(oldt)
# 0.797673369999999999 seconds

# Hurray! The new code is much faster!!

print('Inputs:')
print(good[0:10])

print('New function results:')
print(c.generate_time_pairs(good, bad))

print('Old function results:')
print(oldc.generate_time_pairs(good, bad))

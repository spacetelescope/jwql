#! /usr/bin/env python


import itertools


limits = [(3,10), (4,11), (2,6), (8,11), (9,11)]
ranges = [range(*lim) for lim in  limits]

results = []
for comb in itertools.combinations(ranges,3):
    intersection = set(comb[0]).intersection(comb[1])
    intersection = intersection.intersection(comb[2])
    if intersection and intersection not in results and\
       not any(map(intersection.issubset, results)):
        results = filter(lambda res: not intersection.issuperset(res),results)
        results.append(intersection)


result_limits =  [(res[0], res[-1]+1) for res in map(list,results)]

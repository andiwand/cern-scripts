#!/usr/bin/env python3

import argparse
import numpy as np
import uproot

parser = argparse.ArgumentParser()
parser.add_argument("a")
parser.add_argument("b")
args = parser.parse_args()

a_data = uproot.open(args.a)
b_data = uproot.open(args.b)

a_sort_index = np.argsort(a_data["event_nr"].array(library="np"), kind="stable")
b_sort_index = np.argsort(b_data["event_nr"].array(library="np"), kind="stable")

for key in a_data.keys():
    if key == "event_nr":
        continue

    a_vals = a_data[key].array(library="np")
    a_vals = a_vals[a_sort_index]

    b_vals = b_data[key].array(library="np")
    b_vals = b_vals[b_sort_index]

    for event, (a, b) in enumerate(zip(a_vals, b_vals)):
        if type(a) in [np.int32, np.uint32]:
            if a != b:
                print("event", event, "key", key)
                print("a", a, "b", b)
        elif type(a) == np.ndarray:
            if not np.array_equal(a, b, equal_nan=True):
                print("event", event, "key", key)
                print("a", a, "b", b)
        else:
            for aa, bb in zip(a, b):
                if not np.array_equal(aa, bb, equal_nan=True):
                    print("event", event, "key", key)
                    print("a", aa, "b", bb)

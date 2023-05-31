##
## Copyright 2022 Zachary Espiritu and Evangelia Anna Markatou and
##                Francesca Falzon and Roberto Tamassia and William Schor
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##
from ortools.sat.python import cp_model
from ortools.sat import sat_parameters_pb2
from ers.schemes.common.emm import EMM, EMMEngine
from ers.structures.point import Point
from ers.schemes.qdag_src import QdagSRC 
from ers.structures.quad_tree_src import get_quad_divisions, get_intermediate_divisions
from ers.structures.rect import Rect
from typing import *
from collections import defaultdict
from ers.util.crypto import SecureRandom
from tqdm import tqdm, trange

#import util
import unittest
import secrets
import pprint
import itertools
import argparse
import json
import math
import functools
import csv

Multimap = Dict[Point, List[bytes]]

MAX_DOCUMENT_LENGTH = 16

def next_power_of_2(x):
    return 1 if x == 0 else 2**(x - 1).bit_length()

def points_to_multimap(pts: List[List[int]]):
    mm = defaultdict(list)

    max_x = 0
    max_y = 0
    for x,y in pts:
        mm[Point(x, y)].append(SecureRandom(MAX_DOCUMENT_LENGTH))
        if x > max_x:
            max_x = x
        if y > max_y:
            max_y = y
    x_size, y_size = next_power_of_2(max_x), next_power_of_2(max_y)
    bound = max(x_size, y_size)
    return mm, bound, bound

def get_octo_divisions(plaintext_rect: Rect) -> Dict:
    corner_length = int(plaintext_rect.x_length() / 4)
    southwest = Rect(
        Point(plaintext_rect.start_x(),
              plaintext_rect.start_y()),
        Point(plaintext_rect.start_x() + corner_length,
              plaintext_rect.start_y() + corner_length)
    )
    northwest = Rect(
        Point(plaintext_rect.start_x(),
              plaintext_rect.end_y() - corner_length),
        Point(plaintext_rect.start_x() + corner_length,
              plaintext_rect.end_y())
    )
    northeast = Rect(
        Point(plaintext_rect.end_x() - corner_length,
              plaintext_rect.end_y() - corner_length),
        Point(plaintext_rect.end_x(),
              plaintext_rect.end_y())
    )
    southeast = Rect(
        Point(plaintext_rect.end_x() - corner_length,
              plaintext_rect.start_y()),
        Point(plaintext_rect.end_x(),
              plaintext_rect.start_y() + corner_length)
    )

    # Get the intermediate nodes:
    [north, south, west, east, center] = get_intermediate_divisions(plaintext_rect)

    return {
        "adds": [southwest, northwest, northeast, southeast, north, south, west, east],
        "sub": center
    }

def attack(output_file, db):
    mm, bound_x, bound_y = None, None, None

    mm, bound_x, bound_y = points_to_multimap(db)


    print("[*] Starting attack with the bounds x:", bound_x, "y:", bound_y)
    emm_engine = EMMEngine(bound_x, bound_y)
    qdag_sse   = QdagSRC(emm_engine)
    qdag_key   = qdag_sse.setup(16)
    print("[*] Building index...")
    qdag_sse.build_index(qdag_key, mm)

    # Generate all possible queries:
    print("[*] Generating queries (this will take a while)...")
    translation = {}
    volumes = {}
    p_volumes = defaultdict(lambda: 0)
    counts = defaultdict(lambda: 0)
    p_counts = defaultdict(lambda: 0)

    for point_a in tqdm(list((Point(x, y) for x in range(bound_x) for y in range(bound_y)))):
        for point_b in (Point(v, w) for v in range(point_a.x, bound_x) for w in range(point_a.y, bound_y)):
            plaintext_query  = Rect(point_a, Point(point_b.x + 1, point_b.y + 1))
            ciphertext_query = qdag_sse.trapdoor(qdag_key, point_a, point_b)
            if ciphertext_query not in translation:
                ciphertext_response = qdag_sse.search(ciphertext_query)

                # Capture the response volume:
                response_volume = len(ciphertext_response)
                plaintext_query  = Rect(point_a, point_b)

                # Plaintext transaction matrices solely for human-readable output, not necessary for attack:
                translation[ciphertext_query] = qdag_sse.qdag.get_single_range_cover(plaintext_query)
                volumes[ciphertext_query] = response_volume

                p_volumes[qdag_sse.qdag.get_single_range_cover(Rect(point_a, point_b))] = response_volume

            # Count vector:
            p_counts[qdag_sse.qdag.get_single_range_cover(Rect(point_a, point_b))] += 1
            counts[ciphertext_query] += 1

    max_volume = max(p_volumes.values())

    print("[*] Making model...")
    solver = cp_model.CpSolver()
    solver.parameters = sat_parameters_pb2.SatParameters(num_search_workers=16,log_search_progress=True)
    model = cp_model.CpModel()

    print("[*] Calculating expected frequencies...")
    count_restricted_values = defaultdict(list)
    count_restricted_variables = defaultdict(list)
    plaintext_rect_var_map = {}
    for token, count in counts.items():
        token_var = model.NewIntVar(0, max_volume, str(token))
        token_volume = volumes[token]

        count_restricted_values[count].append(token_volume)
        count_restricted_variables[count].append(token_var)

        plaintext_rect = translation[token]
        plaintext_rect_var_map[plaintext_rect] = token_var

    #
    # This loop creates the equations from Equation (3). 
    #
    print("[*] Creating boolean matrix constraint...")
    for count, var_list in count_restricted_variables.items():
        value_restrictions = count_restricted_values[count]
        num_possible_values = len(value_restrictions)

        var_lower_bound = min(value_restrictions)
        var_upper_bound = max(value_restrictions)

        # Create boolean array:
        bool_vars = [None] * len(var_list)
        for var_index, var in enumerate(var_list):
            bool_vars[var_index] = [None] * num_possible_values
            sumExpr = None

            for val_index in range(num_possible_values):
                indicator_var = model.NewBoolVar("(" + str(var_index) + ", " + str(val_index) + ")")
                bool_vars[var_index][val_index] = indicator_var

                corresponding_val = value_restrictions[val_index]
                # If indicator_var, then var == corresponding_val.
                if sumExpr is None:
                    sumExpr = (corresponding_val * indicator_var)
                else:
                    sumExpr = sumExpr + (corresponding_val * indicator_var)

            # The node var's volume must equal the sum of the indicator_var expression:
            # Equation 3.1 
            model.Add(var == sumExpr)
            # Optimization to restrict the values of var:
            model.Add(var_lower_bound <= var)
            model.Add(var <= var_upper_bound)

            # Only 1 indicator variable per row may be 1:
            # Equation 3.2
            model.Add(sum(bool_vars[var_index]) == 1)

        # Create the constraints along the column of the boolean matrix
        # that enforce that each volume instance can only be used once:
        for bool_index in range(num_possible_values):
            tmp = [None] * len(var_list)
            for var_index, var in enumerate(var_list):
                tmp[var_index] = bool_vars[var_index][bool_index]
            # Only 1 indicator variable per column may be 1:
            # Equation 3.3
            model.Add(sum(tmp) == 1)


    # Make volume assignments (Equation (2)). 
    print("[*] Making summation constraints...")
    for token in counts.keys():
        plaintext_rect = translation[token]
        parent_var = plaintext_rect_var_map[plaintext_rect]

        if (plaintext_rect.x_length() >= 2):
            quad_divisions = get_quad_divisions(plaintext_rect)
            quad_vars = map(lambda rect: plaintext_rect_var_map[rect], quad_divisions)

            # Enforce that the sum of all child nodes == sum of the parent:
            model.Add(sum(quad_vars) == parent_var)

            if p_volumes[plaintext_rect] != sum(p_volumes[r] for r in quad_divisions):
                print("[-] ERROR:", plaintext_rect, "=", quad_divisions)
                print("[*] ERROR:", p_volumes[plaintext_rect], "=", list((r, p_volumes[r]) for r in quad_divisions))

    print("[*] Solving...")
    status = solver.Solve(model)
    print("[*] Done.")

    assigned_volumes = defaultdict(lambda: 0)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        user_time_s = solver.UserTime()
        wall_time_s = solver.WallTime()
        print("[+] Was able to find a solution in %f seconds!" % user_time_s)
        print('[+] Maximum of objective function: %i (should be 0)' % solver.ObjectiveValue())
        for plaintext_rect, variable in plaintext_rect_var_map.items():
            assigned_volumes[plaintext_rect] = solver.Value(variable)

        sorted_volumes = dict(sorted(assigned_volumes.items(), key=lambda item: item[1]))

        print("[*] Writing solution to %s file." % output_file)
        with open(output_file, 'w+', newline='') as csvfile:
            resultwriter = csv.writer(csvfile)
            resultwriter.writerow(["size", "start_x", "start_y", "end_x", "end_y", "assigned_volume", "true_volume", "user_time_s", "wall_time_s", "num_branches"])

            for plaintext_rect, variable in sorted_volumes.items():
                assigned_volume = assigned_volumes[plaintext_rect]
                true_volume = p_volumes[plaintext_rect]

                start_x = plaintext_rect.start_x()
                start_y = plaintext_rect.start_y()
                end_x = plaintext_rect.end_x()
                end_y = plaintext_rect.end_y()

                size = end_x - start_x

                resultwriter.writerow([size, start_x, start_y, end_x, end_y, assigned_volume, true_volume, user_time_s, wall_time_s, solver.NumBranches()])

    else:
        print("[-] Couldn't find a solution!")

if __name__ == '__main__':
    main()

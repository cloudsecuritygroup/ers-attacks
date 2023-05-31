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
from ers.structures.point import Point
from ers.structures.range_tree import RangeTree
from typing import *

import numpy as np
import networkx as nx
from matplotlib import cm
from tqdm import tqdm, trange
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.ticker import LinearLocator

import multiprocessing
import functools
import itertools
import time
import math
import csv



## Type Declarations

Multimap = Dict[Point, List[bytes]]


def draw_vol_3d(arr, bound_x, bound_y, name: str):
    plt.clf()
    plt.cla()
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})

    x = np.arange(0, bound_x)
    y = np.arange(0, bound_y)
    x, y = np.meshgrid(x, y)

    # Plot the surface.
    surf = ax.plot_surface(x, y, arr, cmap=cm.coolwarm, linewidth=0, antialiased=False)

    # Customize the z axis.
    ax.set_zlim(0, np.amax(arr))
    ax.zaxis.set_major_locator(LinearLocator(10))
    # A StrMethodFormatter is used automatically
    ax.zaxis.set_major_formatter('{x:.02f}')

    # Add a color bar which maps values to colors.
    fig.colorbar(surf, shrink=0.5, aspect=5)

    fig.tight_layout()

    print("Showing")
    plt.savefig(name+"-3d.png", dpi=400)



def draw_vol_arr(arr, name:str):
    x = []
    y = []
    c = []

    for i, row in enumerate(arr):
        for j, vol in enumerate(row):
            if vol > 0:
                x.append(i)
                y.append(j)
                c.append(vol)


    plt.scatter(x,y,c=c)
    plt.colorbar()
    plt.savefig(name+"-output.png", dpi=400)


def next_power_of_2(x):  
    return 2**(x - 1).bit_length()

def draw_brc_graph(G, edge_counts, interior):
    color_map = []
    for node in G:
        if node in interior:
            color_map.append("red")
        else:
            color_map.append("#A0CBE2")

    edge_map = []
    for edge in G.edges:
        if edge_counts[frozenset(edge)] == 1:
            edge_map.append("red")
        elif edge_counts[frozenset(edge)] == 2:
            edge_map.append("blue")
        else:
            edge_map.append("black")

    pos = nx.kamada_kawai_layout(G)
    labels = nx.get_node_attributes(G, "range_cover")
    nx.draw(G, pos, node_color=color_map, edge_color=edge_map, labels=labels, font_color="black", font_size=10)
    plt.show()


def grid_graph_to_arr(G, corners, bound_x, bound_y):
    bl = corners[0]
    tr = corners[1]
    tl = corners[2]
    br = corners[3]

    arr = np.zeros((bound_x, bound_y))
    
    bottom_axis = nx.shortest_path(G, source=bl, target=br)
    top_axis = nx.shortest_path(G, source=tl, target=tr)

    i = 0
    for bot, top in zip(bottom_axis, top_axis):
        arr[:, i] = list(map(lambda node: G.nodes[node]["volume"], nx.shortest_path(G, source=bot, target=top)))
        i += 1

    return arr


def Q_process(the_input):
    S, E = the_input

    query_edges = set(filter(lambda edge: edge[0] in S and edge[1] in S, E))
    query_G = nx.Graph()
    query_G.add_edges_from(query_edges)

    min_degree_node = min(query_G.nodes, key=lambda x: query_G.degree[x])
    min_degree = query_G.degree[min_degree_node]
    corners = set(filter(lambda x: query_G.degree[x] == min_degree, query_G.nodes))

    # Remove the corners and add them to I:
    I = S.difference(corners)

    # Remove all edges between the interior nodes:
    edges_to_remove = list(filter(lambda edge: edge[0] not in corners and edge[1] not in corners, query_edges))

    # Look at all edges that are along the same block slice:
    to_add = []
    if len(corners) == 2:
        for edge in query_edges:
            to_add.append(frozenset(edge))

    return (I, edges_to_remove, to_add)

def range_tree_brc_reconstruction_attack(db: Multimap, bound_x, bound_y, output_file_path):
    dataset = np.ones((bound_x, bound_y), dtype=int)
    for tup in db.keys():
        dataset[tup[0], tup[1]] = db[tup]
    print(dataset)

    prefix_sums = np.cumsum(np.cumsum(dataset, axis=0), axis=1) # Sum over rows

    # Generate range tree:
    x_tree_height = math.ceil(math.log2(bound_x))
    y_tree_height = math.ceil(math.log2(bound_y))
    x_tree = RangeTree.initialize_tree(x_tree_height)
    y_tree = RangeTree.initialize_tree(y_tree_height)

    @functools.lru_cache(maxsize=None)
    def get_x_brc_range_cover(rng):
        return x_tree.get_brc_range_cover(rng)

    @functools.lru_cache(maxsize=None)
    def get_y_brc_range_cover(rng):
        return y_tree.get_brc_range_cover(rng)

    @functools.lru_cache(maxsize=None)
    def get_prefix_sums_for_ranges(x_range, y_range):
        add1 = prefix_sums[x_range[0] - 1, y_range[0] - 1] if (x_range[0] > 0 and y_range[0] > 0) else 0
        add2 = prefix_sums[x_range[1],     y_range[1]]
        sub1 = prefix_sums[x_range[1],     y_range[0] - 1] if (y_range[0] > 0) else 0
        sub2 = prefix_sums[x_range[0] - 1, y_range[1]]     if (x_range[0] > 0) else 0
        return add2 + add1 - sub1 - sub2

    print(f"Generating all possible queries for bounds x: {bound_x} / y: {bound_y}...")
    M = {}
    T = {}
    for x1 in trange(bound_x):
        for x2 in range(x1, bound_x):
            x_covers = get_x_brc_range_cover((x1, x2))
            for y1 in range(bound_y):
                for y2 in range(y1, bound_y):
                    y_covers = get_y_brc_range_cover((y1, y2))
                    prod_covers = frozenset(itertools.product(x_covers, y_covers))
                    volume = 0
                    for x_range, y_range in prod_covers:
                        result = get_prefix_sums_for_ranges(x_range, y_range)
                        volume += result

                    M[prod_covers] = volume
                    T[prod_covers] = tuple(prod_covers)

    # Attack starts here:
    print("Actual attack starting...")
    wall_time0 = time.time_ns()
    user_time0 = time.process_time_ns()
    E = list(map(lambda search_tokens: tuple(search_tokens), filter(lambda search_tokens: len(search_tokens) == 2, M.keys())))
    Q = list(filter(lambda search_tokens: len(search_tokens) >= 2, M.keys()))

    # Construct undirected graph G with edges the elements of E:
    print("Construct undirected graph G with edges the elements of E...")
    G = nx.Graph()
    G.add_edges_from(E)
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    print("Loop over Q...")
    interior = set()
    edge_counts = defaultdict(lambda: 0)

    with multiprocessing.Pool(processes=16) as pool:
        for result in tqdm(pool.imap_unordered(Q_process, zip(Q, itertools.repeat(E)), 1000), total=len(Q)):
            I, edges_to_remove, to_add = result

            interior.update(I)
            G.remove_edges_from(edges_to_remove)
            for edge in to_add:
                edge_counts[edge] += 1



    def edge_is_blue(edge):
        return edge_counts[frozenset(edge)] == 2

    red_nodes = [(node, set(filter(lambda neighbor: edge_is_blue((node, neighbor)), G.neighbors(node)))) for node in interior if node in G]
    
    nodes_to_remove = set()
    for red_node, blue_neighbors in red_nodes:
        if len(blue_neighbors) == 0:
            nodes_to_remove.add(red_node)
            continue
            
        min_node = min(blue_neighbors, key=lambda x: M[frozenset([x])])
        nodes_to_remove.update([n for n in blue_neighbors if n != min_node])

    G.remove_nodes_from(nodes_to_remove)
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    for rn in interior:
        if rn in G:
            if G.degree(rn) == 2:
                edges = list(G.edges(rn))
                G.add_edge(edges[0][1], edges[1][1])
                G.remove_node(rn)


    # Add volumes to each node:
    for node in G.nodes:
        query = frozenset([node])
        if query in M:
            G.nodes[node]["range_cover"] = T[query]
            G.nodes[node]["volume"] = M[query]


    
    bl = (((0,1), (0,1)),)
    tr = (((bound_x - 2, bound_y - 1), (bound_x - 2, bound_y - 1)),)
    tl = (((bound_x - 2, bound_y - 1), (0, 1)),)
    br = (((0,1), (bound_x - 2, bound_y - 1)),)
    c0 = None
    c1 = None
    c2 = None
    c3 = None
    for node in G.nodes:
        if G.nodes[node]["range_cover"] == bl:
            c0 = node
        if G.nodes[node]["range_cover"] == tr:
            c1 = node           
        if G.nodes[node]["range_cover"] == tl:
            c2 = node 
        if G.nodes[node]["range_cover"] == br:
            c3 = node 

    # Do the swaps:
    vol_arr = grid_graph_to_arr(G.copy(), [c0, c1, c2, c3], bound_x, bound_y)
    x_max = bound_x - 1
    y_max = bound_y - 1
    for i in range(1, x_max, 2):
        vol_arr[:, [i,i+1]] = vol_arr[:, [i+1,i]]
    for i in range(1, y_max, 2):
        vol_arr[[i,i+1], :] = vol_arr[[i+1,i], :]

    # Do the subtractions around the border:
    for x in range(1, bound_x - 1):
        vol_arr[x, 0]     = vol_arr[x, 0]     - vol_arr[x, 1]
        vol_arr[x, y_max] = vol_arr[x, y_max] - vol_arr[x, y_max - 1]
    for y in range(1, bound_y - 1):
        vol_arr[0,     y] = vol_arr[0,     y] - vol_arr[1,         y]
        vol_arr[x_max, y] = vol_arr[x_max, y] - vol_arr[x_max - 1, y]

    # Do the subtraction for the corners:
    vol_arr[0, 0] = vol_arr[0, 0] - vol_arr[0, 1] - vol_arr[1, 0] - vol_arr[1, 1]
    vol_arr[0, y_max] = vol_arr[0, y_max] - vol_arr[1, y_max] - vol_arr[0, y_max - 1] - vol_arr[1, y_max - 1]
    vol_arr[x_max, 0] = vol_arr[x_max, 0] - vol_arr[x_max, 1] - vol_arr[x_max - 1, 0] - vol_arr[x_max - 1, 1]
    vol_arr[x_max, y_max] = vol_arr[x_max, y_max] - vol_arr[x_max - 1, y_max] - vol_arr[x_max, y_max - 1] - vol_arr[x_max - 1, y_max - 1]
    


    wall_time1 = time.time_ns()
    user_time1 = time.process_time_ns()
    total_wall_time_ns = wall_time1 - wall_time0
    total_user_time_ns = user_time1 - user_time0
    print("Wall time:", total_wall_time_ns / 1000000000, "s")
    print("User time:", total_user_time_ns / 1000000000, "s")


    # Disable numpy wrapping on print:
    np.set_printoptions(linewidth=np.inf)

    dataset = dataset.astype(int)
    vol_arr = vol_arr.astype(int)

    print("Original")
    print("--------")
    print(dataset)

    print("Reconstruction")
    print("--------------")
    print(vol_arr)

    print("Are they equal?")
    print("---------------")
    print(np.array_equal(dataset,vol_arr))

    print("[*] Writing solution to %s file." % output_file_path)
    with open(output_file_path, 'w', newline='') as csvfile:
        resultwriter = csv.writer(csvfile)
        resultwriter.writerow(["x", "y", "assigned_volume", "true_volume", "wall_time_ns", "user_time_ns"])

        for x in range(bound_x):
            for y in range(bound_y):
                true_volume = dataset[x, y]
                assigned_volume = vol_arr[x, y]
                resultwriter.writerow([x, y, assigned_volume, true_volume, total_wall_time_ns, total_user_time_ns])

    return vol_arr




def attack(name: str, db: Multimap, output_file_path):
    scheme_constructor, attack_algorithm = RangeTree, range_tree_brc_reconstruction_attack

    bound_x = next_power_of_2(max(db.keys(), key=lambda p: p[0])[0])
    bound_y = next_power_of_2(max(db.keys(), key=lambda p: p[1])[1])
    true_bound = max(bound_x, bound_y)
    bound_x = true_bound
    bound_y = true_bound

    A = attack_algorithm(db, bound_x, bound_y, output_file_path)
    draw_vol_arr(A, name)
    draw_vol_3d(A, bound_x, bound_y, name)

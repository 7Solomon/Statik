from collections import defaultdict, deque
from typing import List, Set, Tuple, Dict, Any
from data.custome_class_definitions import ProblemDefinition, Joint
from analyze.bool_checker import has_full_xyzM

def _joint_lists(problem: ProblemDefinition, a: str, b: str):
    """
    Returns (list joints at a referencing b, list joints at b referencing a)
    """
    na = problem.node(a)
    nb = problem.node(b)
    ja = [r for r in na.reactions if isinstance(r, Joint) and r.to_node == b]
    jb = [r for r in nb.reactions if isinstance(r, Joint) and r.to_node == a]
    return ja, jb

def _all_undirected_edges(problem: ProblemDefinition) -> Set[Tuple[str,str]]:
    edges = set()
    for c in problem.connections:
        a, b = c.from_node, c.to_node
        if a == b:
            continue
        if a > b:
            a, b = b, a
        edges.add((a, b))
    return edges


###
#    -------------
###


def _find_triangles(edges: Set[Tuple[str,str]]) -> List[Tuple[str,str,str]]:
    adj = defaultdict(set)
    for a,b in edges:
        adj[a].add(b)
        adj[b].add(a)
    triangles = []
    nodes = sorted(adj.keys())
    for i,a in enumerate(nodes):
        for b in adj[a]:
            if b <= a:
                continue
            # intersection
            common = adj[a].intersection(adj[b])
            for c in common:
                if c <= b:
                    continue
                triangles.append((a,b,c))
    #print(f"Found {len(triangles)} triangles: {triangles}")
    return triangles

def _find_directed_moment_capable_joints(
                    problem: ProblemDefinition, 
                    all_edges: Set[Tuple[str,str]],
                    edge_joint_cache: Dict[Tuple[str,str], Tuple[List[Joint], List[Joint]]]
                 ) -> Set[Tuple[str,str]]:
    
    directed_moment_capable: Set[Tuple[str,str]] = set()
    for a,b in all_edges:
        ja, jb = _joint_lists(problem, a, b)  # ja: joints at a referencing b, jb: at b referencing a
        edge_joint_cache[(a,b)] = (ja,jb)

        if has_full_xyzM(j.vector for j in ja):
            #print(f"moment capable direction: {a} -> {b}")
            directed_moment_capable.add((a,b))
        if has_full_xyzM(j.vector for j in jb):
            #print(f"moment capable direction: {b} -> {a}")
            directed_moment_capable.add((b,a))
    return directed_moment_capable



##
#     --------
##

def _find_stiff_system(directed_moment_capable: Set[Tuple[str, str]]) -> List[Set[str]]:
    # 1. Find nodes that are part of a bi-directional stiff connection
    stiff_adj = defaultdict(set)
    for a, b in directed_moment_capable:
        if (b, a) in directed_moment_capable:
            stiff_adj[a].add(b)
            stiff_adj[b].add(a)

    # 2. Group these nodes into connected stiff systems
    systems: List[Set[str]] = []
    visited = set()
    for node in stiff_adj:
        if node not in visited:
            # Start a new system and find all connected stiff nodes
            new_system = set()
            q = deque([node])
            visited.add(node)
            while q:
                curr = q.popleft()
                new_system.add(curr)
                for neighbor in stiff_adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)
            systems.append(new_system)

    # 3. Iteratively expand systems with uni-directionally attached nodes
    while True:
        nodes_added_in_pass = 0
        for system in systems:
            # Find all nodes reachable from the current system
            reachable_nodes = set()
            for a, b in directed_moment_capable:
                if a in system:
                    reachable_nodes.add(b)
            
            # Add new nodes to the system
            new_nodes = reachable_nodes - system
            if new_nodes:
                system.update(new_nodes)
                nodes_added_in_pass += len(new_nodes)

        if nodes_added_in_pass == 0:
            break # No more nodes can be added, expansion is complete

    return systems


def _find_triangle_systems(triangles: List[Tuple[str, str, str]]) -> List[Set[str]]:
    triangle_systems = []
    visited = set()

    for a, b, c in triangles:
        if (a, b, c) in visited:
            continue

        # Start a new system
        new_system = {a, b, c}
        visited.add((a, b, c))

        # Find all connected triangles
        for x, y, z in triangles:
            if (x, y, z) in visited:
                continue
            if x in new_system or y in new_system or z in new_system:
                new_system.update({x, y, z})
                visited.add((x, y, z))

        triangle_systems.append(new_system)
    return triangle_systems

def _find_rest_systems(stiff_systems: List[Set[str]], triangle_systems: List[Set[str]], all_edges: Set[Tuple[str, str]]) -> List[Set[str]]:
    all_systems = stiff_systems + triangle_systems
    
    # 1. Find edges that are not fully contained within any single system
    uncovered_edges = set()
    for edge in all_edges:
        a, b = edge
        is_covered = False
        for system in all_systems:
            if a in system and b in system:
                is_covered = True
                break
        if not is_covered:
            uncovered_edges.add(edge)

    # 2. Build an adjacency list for the graph of uncovered edges
    adj = defaultdict(set)
    nodes_in_rest = set()
    for a, b in uncovered_edges:
        adj[a].add(b)
        adj[b].add(a)
        nodes_in_rest.add(a)
        nodes_in_rest.add(b)

    # 3. Find the connected components of the uncovered graph
    rest_systems: List[Set[str]] = []
    visited = set()
    for node in nodes_in_rest:
        if node not in visited:
            component = set()
            q = deque([node])
            visited.add(node)
            while q:
                curr = q.popleft()
                component.add(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)
            rest_systems.append(component)

    return rest_systems

##
#   -  
##

def find_rigid_subsystems(problem: ProblemDefinition) -> List[Dict[str,Any]]:
    all_edges = _all_undirected_edges(problem)

    edge_joint_cache: Dict[Tuple[str,str], Tuple[List[Joint], List[Joint]]] = {}

    # 1 stiffstuff
    directed_moment_capable = _find_directed_moment_capable_joints(
        problem, all_edges, edge_joint_cache
    )
    stiff_systems = _find_stiff_system(directed_moment_capable)

    # 2 triangles
    triangles = _find_triangles(all_edges)
    triangle_systems = _find_triangle_systems(triangles)

    # rest
    rest_systems = _find_rest_systems(stiff_systems, triangle_systems, all_edges)

    #print(f"Identified {len(stiff_systems)} stiff systems, {len(triangle_systems)} triangle systems, and {len(rest_systems)} rest systems.")
    systems = stiff_systems + triangle_systems + rest_systems
    #print(systems)
    return systems

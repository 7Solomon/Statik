import copy
import numpy as np
from typing import List, Dict, Set, Tuple

from models.analyze_models import StructuralSystem, Node, Member, NodalLoad

class SystemSimplifier:
    """
    Analyzes a StructuralSystem and simplifies statically determinate appendages.
    [Systemvereinfachung]
    """

    def __init__(self, system: StructuralSystem):
        # Work on a copy to avoid modifying the original system
        self.system = copy.deepcopy(system)
        
        # Helper maps
        self.node_map = {n.id: n for n in self.system.nodes}
        self.member_map = {m.id: m for m in self.system.members}
        
        # Adjacency List: node_id -> list of member_ids
        self.adjacency: Dict[int, List[int]] = {n.id: [] for n in self.system.nodes}
        for m in self.system.members:
            self.adjacency[m.start_node.id].append(m.id)
            self.adjacency[m.end_node.id].append(m.id)

    def get_load_at_node(self, node_id: int) -> np.ndarray:
        """Sums up all loads (Fx, Fy, M) currently acting on a node."""
        res = np.zeros(3) # [Fx, Fy, M]
        for load in self.system.loads:
            if load.node_id == node_id:
                res += load.to_vector()
        return res

    def add_load(self, node_id: int, force_vec: np.ndarray):
        """Adds a new equivalent load to a node."""
        new_id = len(self.system.loads)
        self.system.loads.append(NodalLoad(new_id, node_id, force_vec[0], force_vec[1], force_vec[2]))

    def simplify(self) -> Tuple[StructuralSystem, List[NodalLoad]]:
        """
        Iteratively prunes 'Cantilevers' (Kragarme).
        Returns the simplified system and the new equivalent loads.
        """
        changed = True
        while changed:
            changed = False
            
            # Find candidate nodes for pruning
            # Condition: Connected to exactly 1 member AND has no rigid supports
            nodes_to_prune = []
            for n_id, member_ids in self.adjacency.items():
                if len(member_ids) == 1:
                    node = self.node_map[n_id]
                    # Check if it is a true "Free End" (no supports)
                    if not (node.fix_x or node.fix_y or node.fix_m):
                        nodes_to_prune.append(n_id)

            for tip_node_id in nodes_to_prune:
                # 1. Identify Geometry
                member_id = self.adjacency[tip_node_id][0]
                member = self.member_map[member_id]
                
                # Find the "Root" node (the one we keep)
                if member.start_node.id == tip_node_id:
                    root_node = member.end_node
                else:
                    root_node = member.start_node
                
                # 2. Calculate Equilibrium / Transfer Forces
                # Get loads on the tip
                F_tip = self.get_load_at_node(tip_node_id) # [Fx, Fy, M]
                
                # Distance vector from Root to Tip
                r = self.node_map[tip_node_id].coordinates - root_node.coordinates
                
                # Forces are simply transferred (Action = Reaction)
                F_root_x = F_tip[0]
                F_root_y = F_tip[1]
                
                # Moment at root = Moment at tip + (r x F)
                # 2D Cross product: r_x * F_y - r_y * F_x
                M_transport = r[0] * F_tip[1] - r[1] * F_tip[0]
                M_root = F_tip[2] + M_transport
                
                # 3. Apply Equivalent Load to Root
                self.add_load(root_node.id, np.array([F_root_x, F_root_y, M_root]))
                
                # 4. Prune (Remove Member and Tip Node)
                # Remove member from system list
                self.system.members = [m for m in self.system.members if m.id != member_id]
                del self.member_map[member_id]
                
                # Remove tip node from system list
                self.system.nodes = [n for n in self.system.nodes if n.id != tip_node_id]
                del self.node_map[tip_node_id]
                
                # Update Adjacency
                self.adjacency[root_node.id].remove(member_id)
                del self.adjacency[tip_node_id]
                
                print(f" -> Pruned Member {member_id} (Node {tip_node_id} -> Node {root_node.id})")
                changed = True # System changed, re-scan for new leaves (recursive chains)
                
        return self.system, self.system.loads


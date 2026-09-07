"""Random but *valid* plane structural systems, in pixel space.

The previous generator splattered nodes at random, chained them by x-order and
sprinkled supports and hinges by coin flip. That produces pictures no engineer
would draw: members crossing mid-air, members running straight through nodes
they are not connected to, and systems that are kinematic mechanisms roughly as
often as not. A detector trained on that learns a symbol prior that does not
match the systems it will actually be shown.

This version builds from four archetypes that cover most of a statics course -
Traeger, Kragarm, Rahmen, Fachwerk - and is gravity aligned: ground is at the
bottom, supports sit under the structure, loads point down. Releases live on the
member end they belong to (`ImageMember.start_hinge` / `end_hinge`), never on a
node, because "there is a hinge at this joint" is ambiguous as soon as three
members meet there.
"""

import math
import random
import uuid
from typing import Dict, List, Optional, Sequence, Tuple

from src.models.image_models import ImageLoad, ImageMember, ImageNode, ImageSystem
from src.plugins.generator.image.stanli_symbols import (
    BeamType,
    HingeType,
    LoadType,
    SupportType,
)

# Reaction components restrained per support, matching ImageNode._convert_support_type.
_REACTIONS = {
    SupportType.FREIES_ENDE: 0,
    SupportType.FESTLAGER: 2,
    SupportType.LOSLAGER: 1,
    SupportType.FESTE_EINSPANNUNG: 3,
    SupportType.GLEITLAGER: 1,
    SupportType.FEDER: 1,
    SupportType.TORSIONSFEDER: 1,
}

# Which equilibrium component each release frees, matching
# ImageMember._convert_hinges_to_releases.
_RELEASED_COMPONENT = {
    HingeType.VOLLGELENK: "mz",
    HingeType.HALBGELENK: "mz",
    HingeType.SCHUBGELENK: "fy",
    HingeType.NORMALKRAFTGELENK: "fx",
    HingeType.BIEGESTEIFE_ECKE: None,  # a rigid corner releases nothing
}

MIN_MEMBER_PX = 45.0
_COLLINEAR_TOL_PX = 4.0
#: Most stations a beam may have before neighbouring support symbols collide.
MAX_BEAM_STATIONS = 5


def _nid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# validity
# ---------------------------------------------------------------------------

def member_ends_by_node(system: ImageSystem) -> Dict[str, List[Tuple[ImageMember, str]]]:
    ends: Dict[str, List[Tuple[ImageMember, str]]] = {}
    for m in system.members:
        ends.setdefault(m.start_node_id, []).append((m, "start"))
        ends.setdefault(m.end_node_id, []).append((m, "end"))
    return ends


def count_release_conditions(system: ImageSystem) -> int:
    """Independent release conditions.

    At a joint with j member ends only j-1 releases of the same component are
    independent - releasing every end just turns the joint itself into a pin.
    Counting all j is the classic way to talk yourself into believing a
    mechanism is statically determinate.
    """
    total = 0
    for node_id, attached in member_ends_by_node(system).items():
        j = len(attached)
        if j < 2:
            continue
        per_component: Dict[str, int] = {}
        for member, which in attached:
            ht = getattr(member, f"{which}_hinge", None)
            comp = _RELEASED_COMPONENT.get(ht) if ht else None
            if comp:
                per_component[comp] = per_component.get(comp, 0) + 1
        for count in per_component.values():
            total += min(count, j - 1)
    return total


def static_indeterminacy(system: ImageSystem) -> int:
    """Abzaehlkriterium. n < 0 is a mechanism, n == 0 statically determinate.

    Necessary, not sufficient - it cannot see an unstable arrangement that
    happens to have the right counts - but it is what `enforce_static_determinacy`
    promises, and it catches the mechanisms the old generator produced wholesale.
    """
    k = len(system.nodes)
    s = len(system.members)
    a = sum(_REACTIONS.get(n.support_type, 0) for n in system.nodes)

    if s and all(m.beam_type == BeamType.FACHWERK for m in system.members):
        return a + s - 2 * k  # pin-jointed truss

    return a + 3 * s - 3 * k - count_release_conditions(system)


def _point_segment_distance(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def validate_system(system: ImageSystem, require_determinate: bool = False) -> Optional[str]:
    """None when the system is drawable and physically meaningful, else the reason."""
    if len(system.nodes) < 2 or not system.members:
        return "empty system"

    nodes = {n.id: n for n in system.nodes}
    seen = set()
    for m in system.members:
        if m.start_node_id == m.end_node_id:
            return "self-loop member"
        if m.start_node_id not in nodes or m.end_node_id not in nodes:
            return "member references missing node"
        key = tuple(sorted((m.start_node_id, m.end_node_id)))
        if key in seen:
            return "duplicate member"
        seen.add(key)
        a, b = nodes[m.start_node_id], nodes[m.end_node_id]
        if math.hypot(b.pixel_x - a.pixel_x, b.pixel_y - a.pixel_y) < MIN_MEMBER_PX:
            return "member too short"

    # A node sitting on a member it is not attached to reads as a joint in the
    # image but is not one in the label. Nothing downstream can recover from that.
    for m in system.members:
        a, b = nodes[m.start_node_id], nodes[m.end_node_id]
        for n in system.nodes:
            if n.id in (m.start_node_id, m.end_node_id):
                continue
            d = _point_segment_distance((n.pixel_x, n.pixel_y),
                                        (a.pixel_x, a.pixel_y), (b.pixel_x, b.pixel_y))
            if d < _COLLINEAR_TOL_PX:
                return "node lies on an unrelated member"

    adjacency: Dict[str, List[str]] = {n.id: [] for n in system.nodes}
    for m in system.members:
        adjacency[m.start_node_id].append(m.end_node_id)
        adjacency[m.end_node_id].append(m.start_node_id)
    stack, reached = [system.nodes[0].id], set()
    while stack:
        cur = stack.pop()
        if cur in reached:
            continue
        reached.add(cur)
        stack.extend(adjacency[cur])
    if len(reached) != len(system.nodes):
        return "disconnected system"

    if not any(_REACTIONS.get(n.support_type, 0) for n in system.nodes):
        return "no supports"

    n_ind = static_indeterminacy(system)
    if n_ind < 0:
        return f"kinematic mechanism (n={n_ind})"
    if require_determinate and n_ind != 0:
        return f"statically indeterminate (n={n_ind})"

    return None


# ---------------------------------------------------------------------------
# generator
# ---------------------------------------------------------------------------

class RandomStructureGenerator:
    """Builds gravity-aligned systems from statics archetypes."""

    ARCHETYPES = ("beam", "cantilever", "frame", "truss")

    def __init__(self, width: int = 800, height: int = 600, padding: int = 60,
                 enforce_static_determinacy: bool = True,
                 archetype_weights: Optional[Sequence[float]] = None):
        self.width = width
        self.height = height
        self.padding = padding
        self.enforce_static_determinacy = enforce_static_determinacy
        self.archetype_weights = list(archetype_weights) if archetype_weights else [0.32, 0.18, 0.28, 0.22]

    # --- entry point ----------------------------------------------------

    def generate(self, max_attempts: int = 40) -> ImageSystem:
        last_reason = "no attempt made"
        for _ in range(max_attempts):
            archetype = random.choices(self.ARCHETYPES, weights=self.archetype_weights, k=1)[0]
            system = getattr(self, f"_build_{archetype}")()
            self._add_loads(system)
            reason = validate_system(system, self.enforce_static_determinacy)
            if reason is None:
                return system
            last_reason = reason
        raise RuntimeError(f"could not build a valid system in {max_attempts} attempts: {last_reason}")

    # --- helpers --------------------------------------------------------

    def _span_box(self) -> Tuple[float, float, float, float]:
        """Usable drawing area (x0, y0, x1, y1) with room for symbols."""
        return (float(self.padding), float(self.padding),
                float(self.width - self.padding), float(self.height - self.padding))

    def _node(self, x: float, y: float, support: SupportType = SupportType.FREIES_ENDE,
              rotation: float = 0.0) -> ImageNode:
        return ImageNode(id=_nid(), pixel_x=float(x), pixel_y=float(y),
                         support_type=support, hinge_type=None, rotation=rotation)

    def _member(self, a: ImageNode, b: ImageNode, beam_type: BeamType,
                start_hinge: Optional[HingeType] = None,
                end_hinge: Optional[HingeType] = None) -> ImageMember:
        return ImageMember(id=_nid(), start_node_id=a.id, end_node_id=b.id,
                           beam_type=beam_type, start_hinge=start_hinge, end_hinge=end_hinge)

    def _bending_beam_type(self) -> BeamType:
        return random.choice([BeamType.BIEGUNG_OHNE_FASER, BeamType.BIEGUNG_MIT_FASER])

    @staticmethod
    def _ground_support(allow_gleitlager: bool = True) -> SupportType:
        choices = [SupportType.LOSLAGER]
        if allow_gleitlager:
            choices.append(SupportType.GLEITLAGER)
        return random.choice(choices)

    # --- archetypes -----------------------------------------------------

    def _build_beam(self) -> ImageSystem:
        """Einfeld-, Durchlauf- or Gerbertraeger, optionally with overhangs.

        Each support beyond the first two adds one redundancy, so exactly one
        Gerber hinge is inserted per extra support to stay determinate.
        """
        x0, y0, x1, y1 = self._span_box()
        n_spans = random.randint(1, 4)
        y = random.uniform(y0 + (y1 - y0) * 0.35, y0 + (y1 - y0) * 0.6)

        left_over = random.random() < 0.25
        right_over = random.random() < 0.25
        # Support symbols are ~95px wide whatever the span, so only about five
        # stations fit across the frame. Overhangs consume stations without
        # adding supports, so they have to come out of the span budget - past
        # that the ground lines simply overlap each other.
        n_spans = max(1, min(n_spans, MAX_BEAM_STATIONS - 1 - int(left_over) - int(right_over)))
        n_stations = n_spans + 1 + int(left_over) + int(right_over)
        step = (x1 - x0) / (n_stations - 1)
        if step < MIN_MEMBER_PX * 1.3:
            n_spans = 1
            left_over = right_over = False
            n_stations = 2
            step = x1 - x0

        xs = [x0 + i * step for i in range(n_stations)]
        support_slice = xs[int(left_over): n_stations - int(right_over)]

        nodes: List[ImageNode] = []
        support_nodes: List[ImageNode] = []
        for x in xs:
            if x in support_slice:
                idx = support_slice.index(x)
                st = SupportType.FESTLAGER if idx == 0 else self._ground_support()
                node = self._node(x, y, st)
                support_nodes.append(node)
            else:
                node = self._node(x, y)
            nodes.append(node)

        beam_type = self._bending_beam_type()
        members = [self._member(nodes[i], nodes[i + 1], beam_type) for i in range(len(nodes) - 1)]
        system = ImageSystem(width=self.width, height=self.height, nodes=nodes, members=members)

        # One Gerber hinge per redundancy, each in the middle of its own span so
        # it reads as a hinge in the beam rather than a hinge at a support.
        n_hinges = max(0, len(support_nodes) - 2)
        if n_hinges:
            self._insert_span_hinges(system, n_hinges, beam_type)
        return system

    @staticmethod
    def _release_type() -> HingeType:
        """Which release to put in a span.

        All three free exactly one condition, so any of them keeps the system
        determinate. Vollgelenk dominates because that is what dominates real
        drawings, but the other two have to appear often enough to be learnable
        - a class the generator never emits is a class the model never learns.
        """
        return random.choices(
            (HingeType.VOLLGELENK, HingeType.SCHUBGELENK, HingeType.NORMALKRAFTGELENK),
            weights=(0.6, 0.2, 0.2), k=1,
        )[0]

    def _insert_span_hinges(self, system: ImageSystem, count: int, beam_type: BeamType,
                            hinge_type: Optional[HingeType] = None):
        """Split `count` distinct members and release one side of the new joint."""
        nodes = {n.id: n for n in system.nodes}

        def span_length(m):
            a, b = nodes[m.start_node_id], nodes[m.end_node_id]
            return math.hypot(b.pixel_x - a.pixel_x, b.pixel_y - a.pixel_y)

        # Longest spans first. A hinge dropped into a short span ends up inside
        # the ~95px-wide ground line of the support next to it, which puts two
        # ground-truth boxes over one patch of ink.
        candidates = sorted(system.members, key=span_length, reverse=True)

        for member in candidates[:count]:
            a, b = nodes[member.start_node_id], nodes[member.end_node_id]
            t = random.uniform(0.45, 0.55)
            hx = a.pixel_x + (b.pixel_x - a.pixel_x) * t
            hy = a.pixel_y + (b.pixel_y - a.pixel_y) * t
            if (math.hypot(hx - a.pixel_x, hy - a.pixel_y) < MIN_MEMBER_PX
                    or math.hypot(b.pixel_x - hx, b.pixel_y - hy) < MIN_MEMBER_PX):
                continue

            hinge_node = self._node(hx, hy)
            system.nodes.append(hinge_node)
            nodes[hinge_node.id] = hinge_node
            system.members.remove(member)
            # Exactly one of the two ends is released: that is one condition,
            # which is what a Gerber hinge is.
            system.members.append(self._member(a, hinge_node, beam_type,
                                               end_hinge=hinge_type or self._release_type()))
            system.members.append(self._member(hinge_node, b, beam_type))

    def _build_cantilever(self) -> ImageSystem:
        """Kragarm: one Einspannung, everything else free. Always determinate."""
        x0, y0, x1, y1 = self._span_box()
        shape = random.choice(["horizontal", "horizontal", "L"])
        beam_type = self._bending_beam_type()

        if shape == "horizontal":
            n = random.randint(1, 3)
            y = random.uniform(y0 + (y1 - y0) * 0.35, y0 + (y1 - y0) * 0.65)
            step = (x1 - x0) / n
            from_left = random.random() < 0.5
            xs = [x0 + i * step for i in range(n + 1)]
            if not from_left:
                xs.reverse()
            # Hatching faces the wall the beam is built into.
            rot = 270.0 if from_left else 90.0
            nodes = [self._node(xs[0], y, SupportType.FESTE_EINSPANNUNG, rot)]
            nodes += [self._node(x, y) for x in xs[1:]]
        else:
            # Column standing on the ground with a horizontal arm on top.
            cx = random.uniform(x0, x0 + (x1 - x0) * 0.35)
            top_y = random.uniform(y0, y0 + (y1 - y0) * 0.35)
            arm_x = random.uniform(cx + (x1 - cx) * 0.5, x1)
            base = self._node(cx, y1, SupportType.FESTE_EINSPANNUNG, 0.0)
            top = self._node(cx, top_y)
            tip = self._node(arm_x, top_y)
            nodes = [base, top, tip]

        members = [self._member(nodes[i], nodes[i + 1], beam_type) for i in range(len(nodes) - 1)]
        return ImageSystem(width=self.width, height=self.height, nodes=nodes, members=members)

    def _build_frame(self) -> ImageSystem:
        """Rahmen. Either two-hinged with a roller, or a Dreigelenkrahmen."""
        x0, y0, x1, y1 = self._span_box()
        beam_type = self._bending_beam_type()

        ground_y = y1
        top_y = random.uniform(y0, y0 + (y1 - y0) * 0.45)
        left_x = random.uniform(x0, x0 + (x1 - x0) * 0.2)
        right_x = random.uniform(x1 - (x1 - x0) * 0.2, x1)
        if right_x - left_x < MIN_MEMBER_PX * 2 or ground_y - top_y < MIN_MEMBER_PX:
            left_x, right_x, top_y = x0, x1, y0

        three_hinged = random.random() < 0.45

        if three_hinged:
            # 2x Festlager (a=4) + one girder hinge (z=1) -> n = 0
            bl = self._node(left_x, ground_y, SupportType.FESTLAGER)
            br = self._node(right_x, ground_y, SupportType.FESTLAGER)
        else:
            # Festlager + Loslager (a=3) -> n = 0
            bl = self._node(left_x, ground_y, SupportType.FESTLAGER)
            br = self._node(right_x, ground_y, self._ground_support())

        tl = self._node(left_x, top_y)
        tr = self._node(right_x, top_y)
        nodes = [bl, tl, tr, br]
        members = [
            self._member(bl, tl, beam_type),
            self._member(tl, tr, beam_type),
            self._member(tr, br, beam_type),
        ]
        system = ImageSystem(width=self.width, height=self.height, nodes=nodes, members=members)

        if three_hinged:
            girder = system.members[1]
            system.members.remove(girder)
            apex = self._node((left_x + right_x) / 2 + random.uniform(-30, 30), top_y)
            system.nodes.append(apex)
            system.members.append(self._member(tl, apex, beam_type, end_hinge=HingeType.VOLLGELENK))
            system.members.append(self._member(apex, tr, beam_type))

        return system

    def _build_truss(self) -> ImageSystem:
        """Pratt-style Fachwerk. Pin-jointed, so no release symbols are drawn."""
        x0, y0, x1, y1 = self._span_box()
        n_bays = random.randint(3, 6)
        step = (x1 - x0) / n_bays
        if step < MIN_MEMBER_PX:
            n_bays = max(3, int((x1 - x0) // MIN_MEMBER_PX))
            step = (x1 - x0) / n_bays

        bottom_y = random.uniform(y0 + (y1 - y0) * 0.55, y1)
        height = random.uniform(max(MIN_MEMBER_PX, (y1 - y0) * 0.25), (y1 - y0) * 0.55)
        top_y = bottom_y - height

        bottom = []
        for i in range(n_bays + 1):
            st = SupportType.FREIES_ENDE
            if i == 0:
                st = SupportType.FESTLAGER
            elif i == n_bays:
                st = self._ground_support()
            bottom.append(self._node(x0 + i * step, bottom_y, st))

        top = [self._node(x0 + i * step, top_y) for i in range(1, n_bays)]

        nodes = bottom + top
        members = []
        bt = BeamType.FACHWERK
        for i in range(n_bays):
            members.append(self._member(bottom[i], bottom[i + 1], bt))
        for i in range(len(top) - 1):
            members.append(self._member(top[i], top[i + 1], bt))
        for i, t in enumerate(top):
            members.append(self._member(bottom[i + 1], t, bt))
        # End diagonals plus one per interior bay keeps n = a + s - 2k = 0.
        members.append(self._member(bottom[0], top[0], bt))
        members.append(self._member(top[-1], bottom[-1], bt))
        for i in range(len(top) - 1):
            members.append(self._member(top[i], bottom[i + 2], bt))

        return ImageSystem(width=self.width, height=self.height, nodes=nodes, members=members)

    # --- loads ----------------------------------------------------------

    def _add_loads(self, system: ImageSystem):
        """Point loads and moments at nodes. Gravity points down; wind is horizontal."""
        # Keep loads off joints that already carry a symbol. A force arrow drawn
        # through a hinge circle gives the detector two ground-truth boxes over
        # one blob of ink, and neither can be localised cleanly.
        busy = {
            node_id
            for node_id, attached in member_ends_by_node(system).items()
            if any(getattr(m, f"{w}_hinge", None) for m, w in attached)
        }
        free = [n for n in system.nodes
                if _REACTIONS.get(n.support_type, 0) == 0 and n.id not in busy]
        pool = free or [n for n in system.nodes if n.id not in busy] or list(system.nodes)
        n_loads = min(len(pool), random.randint(1, 3))
        targets = random.sample(pool, n_loads)  # no two loads stacked on one node

        loads = []
        for node in targets:
            if random.random() < 0.15:
                load_type = random.choice([LoadType.MOMENT_UHRZEIGER,
                                           LoadType.MOMENT_GEGEN_UHRZEIGER])
                angle = 0.0
                text = f"{random.randint(5, 60)}kNm"
            else:
                load_type = LoadType.EINZELLAST
                if random.random() < 0.18:
                    angle = random.choice([0.0, 180.0])  # horizontal / wind
                else:
                    angle = 270.0 + random.uniform(-8.0, 8.0)  # gravity, slightly skewed
                text = f"{random.randint(5, 60)}kN"

            loads.append(ImageLoad(
                id=_nid(),
                node_id=node.id,
                pixel_x=node.pixel_x,
                pixel_y=node.pixel_y,
                angle_deg=angle,
                load_type=load_type,
                label_text=text,
            ))

        loads.extend(self._distributed_loads(system))
        system.loads = loads

    #: Share of samples that get at least one Streckenlast. Real exercise sheets
    #: are full of them, and a class the generator rarely draws is a class the
    #: detector never learns - see the instance counts in _report_class_histogram.
    DIST_LOAD_PROBABILITY = 0.45
    #: A member shorter than this carries a block too small to read as a load.
    DIST_LOAD_MIN_LENGTH_PX = 70.0

    def _distributed_loads(self, system: ImageSystem) -> List[ImageLoad]:
        """Streckenlasten on whole or partial members.

        Attached to a member, not a node: the symbol spans the member and its
        `start_ratio`/`end_ratio` are the same fractions the FEM reads back as a
        partial-span distributed load.
        """
        if random.random() > self.DIST_LOAD_PROBABILITY:
            return []

        nodes = {n.id: n for n in system.nodes}

        def length_of(member) -> float:
            a, b = nodes.get(member.start_node_id), nodes.get(member.end_node_id)
            if a is None or b is None:
                return 0.0
            return math.hypot(b.pixel_x - a.pixel_x, b.pixel_y - a.pixel_y)

        usable = [m for m in system.members
                  if length_of(m) >= self.DIST_LOAD_MIN_LENGTH_PX]
        if not usable:
            return []

        out: List[ImageLoad] = []
        for member in random.sample(usable, min(len(usable), random.randint(1, 2))):
            if random.random() < 0.35:
                # Partial span, which is what makes start/end ratio worth having.
                start = random.uniform(0.0, 0.45)
                end = random.uniform(max(start + 0.3, 0.55), 1.0)
            else:
                start, end = 0.0, 1.0
            out.append(ImageLoad(
                id=_nid(),
                member_id=member.id,
                load_type=LoadType.STRECKENLAST,
                start_ratio=start,
                end_ratio=end,
                label_text=f"{random.randint(2, 40)}kN/m",
            ))
        return out

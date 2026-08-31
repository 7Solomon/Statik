"""Loads and the time signals that drive the dynamic analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class DynamicSignal:
    type: Literal['HARMONIC', 'STEP', 'PULSE', 'RAMP']
    amplitude: float
    start_time: float = 0.0
    frequency: float = 0.0
    phase: float = 0.0
    end_time: float = 0.0
    offset: float = 0.0

    def to_dict(self):
        return {
            "type": self.type,
            "amplitude": self.amplitude,
            "startTime": self.start_time,
            "frequency": self.frequency,
            "phase": self.phase,
            "endTime": self.end_time,
            "offset": self.offset
        }


@dataclass
class Load:
    id: str
    scope: Literal['NODE', 'MEMBER']
    type: Literal['POINT', 'MOMENT', 'DISTRIBUTED', 'DYNAMIC_FORCE', 'DYNAMIC_MOMENT']
    value: float = 0.0 # Default to 0 for dynamic loads
    
    # -- Linkage --
    node_id: Optional[str] = None
    member_id: Optional[str] = None
    
    # -- Geometry --
    angle: float = 0.0
    is_global: bool = True
    
    # -- Member Positioning --
    ratio: Optional[float] = None
    
    # -- Distributed Params --
    start_ratio: Optional[float] = None
    end_ratio: Optional[float] = None
    start_value: Optional[float] = None
    end_value: Optional[float] = None

    signal: Optional[DynamicSignal] = None 

    def to_dict(self):
        base = {
            "id": self.id,
            "scope": self.scope,
            "type": self.type,
            "value": self.value,
            "isGlobal": self.is_global
        }

        # Add Signal if present
        if self.signal:
            base["signal"] = self.signal.to_dict()

        if self.scope == 'NODE':
            base["nodeId"] = self.node_id
            base["angle"] = self.angle
        
        elif self.scope == 'MEMBER':
            base["memberId"] = self.member_id
            if self.type == 'POINT':
                base["ratio"] = self.ratio
                base["angle"] = self.angle
            elif self.type == 'DISTRIBUTED':
                base["startRatio"] = self.start_ratio
                base["endRatio"] = self.end_ratio
                if self.start_value is not None: base["startValue"] = self.start_value
                if self.end_value is not None: base["endValue"] = self.end_value

        return base

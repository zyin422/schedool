"""
Soft constraints for the school scheduler.

Each constraint has:
- type: The type of constraint
- weight: How many points this constraint is worth
- applies_to: Who/what the constraint applies to (teacher, room, class)
- parameters: Additional parameters for the constraint
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum


class ConstraintType(Enum):
    TEACHER_MORNING_PREF = "teacher_morning_pref"
    TEACHER_AFTERNOON_PREF = "teacher_afternoon_pref"
    ROOM_UNAVAILABLE = "room_unavailable"
    MAX_CONSECUTIVE = "max_consecutive"
    SPREAD_CLASS_SECTIONS = "spread_class_sections"


@dataclass
class Constraint:
    """Represents a soft constraint for scheduling"""
    constraint_type: str
    weight: int
    applies_to: str  # teacher name, room name, or class name
    parameters: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.constraint_type,
            "weight": self.weight,
            "applies_to": self.applies_to,
            "parameters": self.parameters,
            "id": self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Constraint':
        return cls(
            constraint_type=data["type"],
            weight=data["weight"],
            applies_to=data["applies_to"],
            parameters=data.get("parameters", {}),
            id=data.get("id")
        )


def evaluate_teacher_morning_pref(constraint: Constraint, periods: List, sections: List) -> bool:
    """
    Check if teacher has at least one section in their preferred morning periods.
    satisfied = True if teacher teaches in at least one preferred period.
    """
    preferred_periods = constraint.parameters.get("preferred_periods", [])
    if not preferred_periods:
        return False
    
    # Find all sections assigned to this teacher
    teacher_sections = [s for s in sections 
                        if s.assigned_teacher and s.assigned_teacher.name == constraint.applies_to]
    
    # Check if any section is in a preferred period
    for section in teacher_sections:
        for period in periods:
            if section in period.assigned_sections and period.period_id in preferred_periods:
                return True
    
    return False


def evaluate_teacher_afternoon_pref(constraint: Constraint, periods: List, sections: List) -> bool:
    """
    Check if teacher has at least one section in their preferred afternoon periods.
    satisfied = True if teacher teaches in at least one preferred period.
    """
    preferred_periods = constraint.parameters.get("preferred_periods", [])
    if not preferred_periods:
        return False
    
    # Find all sections assigned to this teacher
    teacher_sections = [s for s in sections 
                        if s.assigned_teacher and s.assigned_teacher.name == constraint.applies_to]
    
    # Check if any section is in a preferred period
    for section in teacher_sections:
        for period in periods:
            if section in period.assigned_sections and period.period_id in preferred_periods:
                return True
    
    return False


def evaluate_room_unavailable(constraint: Constraint, periods: List, sections: List) -> bool:
    """
    Check if a room is NOT used during blocked periods.
    satisfied = True if room stays free during blocked period.
    """
    blocked_period = constraint.parameters.get("blocked_period")
    if not blocked_period:
        return False
    
    # Find the period
    target_period = None
    for p in periods:
        if p.period_id == blocked_period:
            target_period = p
            break
    
    if target_period is None:
        return False
    
    # Check if any section in this period uses the specified room
    for section in target_period.assigned_sections:
        if section.assigned_classroom and section.assigned_classroom.name == constraint.applies_to:
            return False  # Room was used - constraint violated
    
    return True  # Room stayed free - constraint satisfied


def evaluate_max_consecutive(constraint: Constraint, periods: List, sections: List) -> bool:
    """
    Check if teacher's longest consecutive teaching block is within limit.
    satisfied = True if max consecutive periods ≤ max_consecutive.
    """
    max_consecutive = constraint.parameters.get("max_consecutive", 3)
    
    # Find all sections assigned to this teacher
    teacher_sections = [s for s in sections 
                        if s.assigned_teacher and s.assigned_teacher.name == constraint.applies_to]
    
    # Build list of periods where teacher has a class
    teaching_periods = set()
    for section in teacher_sections:
        for period in periods:
            if section in period.assigned_sections:
                teaching_periods.add(period.period_id)
    
    # Sort periods and find longest consecutive streak
    sorted_periods = sorted(teaching_periods, key=lambda p: int(p.replace("Period ", "").replace("P", "")))
    
    if not sorted_periods:
        return True  # No classes = no violation
    
    # Extract numeric values for comparison
    def get_period_num(p):
        return int(p.replace("Period ", "").replace("P", ""))
    
    max_streak = 1
    current_streak = 1
    
    for i in range(1, len(sorted_periods)):
        prev_num = get_period_num(sorted_periods[i-1])
        curr_num = get_period_num(sorted_periods[i])
        
        if curr_num == prev_num + 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1
    
    return max_streak <= max_consecutive


def evaluate_spread_class_sections(constraint: Constraint, periods: List, sections: List) -> bool:
    """
    Check if all sections of a class are on different periods.
    satisfied = True if all sections are on different periods.
    """
    # Find all sections for this class
    class_sections = [s for s in sections if s.class_name == constraint.applies_to]
    
    if len(class_sections) <= 1:
        return True  # Single section = always spread
    
    # Extract periods for each section
    section_periods = set()
    for section in class_sections:
        for period in periods:
            if section in period.assigned_sections:
                section_periods.add(period.period_id)
                break
    
    # Satisfied if number of unique periods == number of sections
    return len(section_periods) == len(class_sections)


# Mapping of constraint types to evaluation functions
EVALUATOR_MAP = {
    "teacher_morning_pref": evaluate_teacher_morning_pref,
    "teacher_afternoon_pref": evaluate_teacher_afternoon_pref,
    "room_unavailable": evaluate_room_unavailable,
    "max_consecutive": evaluate_max_consecutive,
    "spread_class_sections": evaluate_spread_class_sections,
}


def evaluate_constraint(constraint: Constraint, periods: List, sections: List) -> bool:
    """Evaluate a single constraint against a schedule"""
    evaluator = EVALUATOR_MAP.get(constraint.constraint_type)
    if evaluator is None:
        return False  # Unknown constraint type
    return evaluator(constraint, periods, sections)


def get_constraint_display_name(constraint_type: str) -> str:
    """Get a human-readable name for a constraint type"""
    names = {
        "teacher_morning_pref": "Teacher Morning Preference",
        "teacher_afternoon_pref": "Teacher Afternoon Preference",
        "room_unavailable": "Room Unavailable",
        "max_consecutive": "Max Consecutive Periods",
        "spread_class_sections": "Spread Class Sections",
    }
    return names.get(constraint_type, constraint_type)


def get_constraint_parameters_schema(constraint_type: str) -> List[Dict[str, str]]:
    """Get the parameter fields needed for each constraint type"""
    schemas = {
        "teacher_morning_pref": [
            {"name": "preferred_periods", "label": "Preferred Morning Periods", "type": "multiselect", 
             "options": ["Period 1", "Period 2", "Period 3"]}
        ],
        "teacher_afternoon_pref": [
            {"name": "preferred_periods", "label": "Preferred Afternoon Periods", "type": "multiselect",
             "options": ["Period 3", "Period 4", "Period 5"]}
        ],
        "room_unavailable": [
            {"name": "blocked_period", "label": "Blocked Period", "type": "select",
             "options": ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"]}
        ],
        "max_consecutive": [
            {"name": "max_consecutive", "label": "Maximum Consecutive Periods", "type": "number", "default": "3"}
        ],
        "spread_class_sections": [
            # No additional parameters needed
        ],
    }
    return schemas.get(constraint_type, [])

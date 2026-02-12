from dataclasses import dataclass, field
from typing import List, Set, Optional


@dataclass
class Classroom:
    name: str
    size: int
    purposes: Set[str]
    
    def is_suitable_for(self, class_type: str) -> bool:
        return class_type in self.purposes


@dataclass
class Class:
    name: str
    num_sections: int
    required_classroom_type: str

    def get_sections(self) -> List[str]:
        return [f"{self.name}-{i+1}" for i in range(self.num_sections)]


@dataclass
class Teacher:
    name: str
    subjects: Set[str]
    max_sections: int
    assigned_count: int


@dataclass
class Section:
    section_id: str
    class_name: str
    required_classroom_type: str
    assigned_teacher: Optional[str] = None
    assigned_classroom: Optional[str] = None
    
    def is_fully_assigned(self) -> bool:
        return all([self.assigned_teacher, self.assigned_classroom])


@dataclass
class Period:
    period_id: str
    assigned_sections: List[Section] = field(default_factory=list)

    def get_assigned_sections(self) -> List:
        result = []
        for i in self.assigned_sections:
            classroom = i.assigned_classroom.name if i.assigned_classroom else "UNASSIGNED"
            teacher = i.assigned_teacher.name if i.assigned_teacher else "UNASSIGNED"
            result.append((i.section_id, classroom, teacher))
        return result


def generate_sections(classes):
    # convert Class objects to Section objects
    sections = []
    for cls in classes:
        for section_id in cls.get_sections():
            sections.append(Section(
                section_id=section_id,
                class_name=cls.name,
                required_classroom_type=cls.required_classroom_type
            ))
    return sections


def assign_sections_to_periods(sections, periods, classroom_types):
    # assign sections to periods (round-robin by classroom type priority)
    period_idx = 0
    for c_type in classroom_types:
        for section in sections:
            if section.required_classroom_type != c_type:
                continue
            periods[period_idx % len(periods)].assigned_sections.append(section)
            period_idx += 1


def assign_classrooms_to_sections(periods, classrooms, classroom_types):
    # assign classrooms to sections within each period
    for p in periods:
        used_rooms = []
        for c_type in classroom_types:
            for room in classrooms:
                if room in used_rooms:
                    continue
                for section in p.assigned_sections:
                    if c_type not in room.purposes or c_type != section.required_classroom_type:
                        continue
                    if section.assigned_classroom:
                        continue
                    section.assigned_classroom = room
                    used_rooms.append(room)
                    break


def assign_teachers_to_sections(sections, teachers, class_list, periods):
    # assign teachers to sections
    for p in periods:
        used_teachers = []
        for c in class_list:
            for section in sections:
                if section.assigned_teacher or c != section.class_name:
                    continue
                for t in teachers:
                    if t in used_teachers or t.assigned_count >= t.max_sections:
                        continue
                    if c not in t.subjects:
                        continue
                    section.assigned_teacher = t
                    t.assigned_count += 1
                    used_teachers.append(t)


def run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods):
    # main scheduling algorithm - runs all assignment steps
    # Generate sections from classes
    sections = generate_sections(classes)
    
    # Run assignment steps
    assign_sections_to_periods(sections, periods, classroom_types)
    assign_classrooms_to_sections(periods, classrooms, classroom_types)
    assign_teachers_to_sections(sections, teachers, class_list, periods)
    
    return sections


def check(periods):
    # validate schedule for conflicts
    for p in periods:
        used_sections = []
        used_teachers = []
        used_classrooms = []
        
        for s in p.assigned_sections:
            # Check for duplicate sections
            if s in used_sections:
                raise Exception(
                    f"CONFLICT in {p.period_id}: Section '{s.section_id}' is scheduled twice in the same period. "
                    f"This section appears multiple times when it should only appear once."
                )
            used_sections.append(s)

            # Check for teacher conflicts
            t = s.assigned_teacher
            if t is not None:
                if t in used_teachers:
                    conflicting_sections = [sec.section_id for sec in p.assigned_sections if sec.assigned_teacher == t]
                    raise Exception(
                        f"CONFLICT in {p.period_id}: Teacher '{t.name}' is assigned to multiple sections simultaneously. "
                        f"Conflicting sections: {', '.join(conflicting_sections)}. "
                        f"A teacher cannot teach multiple classes at the same time."
                    )
                used_teachers.append(t)
            
            # Check for classroom conflicts
            c = s.assigned_classroom
            if c is not None:
                if c in used_classrooms:
                    conflicting_sections = [sec.section_id for sec in p.assigned_sections if sec.assigned_classroom == c]
                    raise Exception(
                        f"CONFLICT in {p.period_id}: Classroom '{c.name}' is assigned to multiple sections simultaneously. "
                        f"Conflicting sections: {', '.join(conflicting_sections)}. "
                        f"A classroom cannot host multiple classes at the same time."
                    )
                used_classrooms.append(c)
    
    print("✅ Check passed - No scheduling conflicts detected")
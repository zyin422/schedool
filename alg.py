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
    required_classroom_type: str # there will only be one; for rooms that can do either general or specific, go general

    # generates section names
    def get_sections(self) -> List[str]:
        return [f"{self.name}-{i+1}" for i in range(self.num_sections)]


@dataclass
class Teacher:
    name: str
    subjects: Set[str]  # subject/class names they're qualified for
    max_sections: int
    assigned_count: int
    #assigned_sections: List[str] = field(default_factory=list)
    
    def can_take_class(self, section_name: str) -> bool:
        return (section_name in self.subjects and 
                len(self.assigned_sections) < self.max_sections)
    
    def assign_class(self, section_name: str) -> bool:
        if self.can_take_class(section_name):
            self.assigned_sections.append(section_name)
            return True
        return False
    
    
@dataclass
class Section:
    section_id: str
    class_name: str
    required_classroom_type: str
    assigned_teacher: Optional[str] = None
    assigned_classroom: Optional[str] = None
    assigned_period: Optional[str] = None
    
    def is_fully_assigned(self) -> bool:
        # check if section has teacher, classroom, and timeslot
        return all([self.assigned_teacher, self.assigned_classroom, self.assigned_period])

@dataclass
class Period:
    period_id: str
    assigned_sections: List[Section] = field(default_factory=list)

    def get_assigned_sections(self) -> List:
        return [(i.section_id, i.assigned_classroom.name, i.assigned_teacher.name) for i in p.assigned_sections]


def check(periods):
    for p in periods:
        used_sections = []
        used_teachers = []
        used_classrooms = []
        for s in p.assigned_sections:
            if s in used_sections:
                raise Exception(s.section_id + " section is used twice")
            used_sections.append(s)

            t = s.assigned_teacher
            if t in used_teachers:
                raise Exception(t.name + " teacher is used twice")
            used_teachers.append(t)
            
            c = s.assigned_classroom
            if c in used_classrooms:
                raise Exception(c.name + " classroom is used twice")
            used_classrooms.append(c)
    print("Check passed")


# create classrooms
classroom_types = ["Biology", "Chemistry", "Physics", "PE", "General"] # used for priority in sections->periods
lab = Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"})
gym = Classroom("Gym-A", size=50, purposes={"PE"})
standard = Classroom("Room-203", size=25, purposes={"General"})
classrooms = [lab, gym, standard]

# create classes
class_list = ["Biology", "Math", "PE"] # used for priority in teachers->sections/periods; DIFFERENT from classroom_types
biology = Class("Biology", num_sections=3, required_classroom_type="Biology")
math = Class("Math", num_sections=2, required_classroom_type="General")
pe = Class("PE", num_sections=2, required_classroom_type="PE")

classes = [biology, math, pe]

# create teachers
teacher1 = Teacher("Ms. Smith", subjects={"Biology", "Chemistry"}, max_sections=5, assigned_count=0)
teacher2 = Teacher("Mr. Jones", subjects={"Math", "Physics"}, max_sections=4, assigned_count=0)
teacher3 = Teacher("Mr. Perez", subjects={"PE"}, max_sections=4, assigned_count=0)
teachers = [teacher1, teacher2, teacher3]


sections = []
for cls in classes:
    for section_id in cls.get_sections():
        section = Section(
            section_id=section_id,
            class_name=cls.name,
            required_classroom_type=cls.required_classroom_type
        )
        sections.append(section)

print(f"\nTotal sections to schedule: {len(sections)}")
for section in sections:
    print(f"  {section.section_id} - needs {section.required_classroom_type} classroom")

# create periods
p1 = Period("Period 1")
p2 = Period("Period 2")
p3 = Period("Period 3")
periods = [p1, p2, p3]

# assign sections->periods

period_idx = 0

# prioritize scheduling special classroom types first
for c_type in classroom_types:
    for section in sections:
        if section.required_classroom_type != c_type:
            continue
        periods[period_idx % len(periods)].assigned_sections.append(section)
        period_idx += 1

# assign classrooms->sections/periods
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



# assign teachers->sections/periods
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

for p in periods:
    print(p.get_assigned_sections())

check(periods)
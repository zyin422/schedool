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
        """Generate section names like 'Biology-1', 'Biology-2', etc."""
        return [f"{self.name}-{i+1}" for i in range(self.num_sections)]


@dataclass
class Teacher:
    name: str
    can_teach: Set[str]  # Subject/class names they're qualified for
    max_sections: int
    assigned_sections: List[str] = field(default_factory=list)
    
    def can_take_class(self, section_name: str) -> bool:
        return (section_name in self.can_teach and 
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
        """Check if section has teacher, classroom, and timeslot"""
        return all([self.assigned_teacher, self.assigned_classroom, self.assigned_period])

@dataclass
class Period:
    period_id: str  # e.g., "Monday-Period1", "Tuesday-Period3"
    assigned_sections: List[Section] = field(default_factory=list)  # List of sections


lab = Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"})
gym = Classroom("Gym-A", size=50, purposes={"PE", "Dance"})
standard = Classroom("Room-203", size=25, purposes={"General"})

# Create classes
biology = Class("Biology", num_sections=3, required_classroom_type="Biology")
math = Class("Math", num_sections=2, required_classroom_type="General")

# Create teachers
teacher1 = Teacher("Ms. Smith", can_teach={"Biology", "Chemistry"}, max_sections=5)
teacher2 = Teacher("Mr. Jones", can_teach={"Math", "Physics"}, max_sections=4)

# Check compatibility
#print(teacher1.can_take_class("Biology"))  # True
#print(lab.is_suitable_for("Biology"))      # True
#print(biology.get_sections())              # ['Biology-1', 'Biology-2', 'Biology-3']

classrooms = [lab, gym, standard]
classes = [biology, math]
teachers = [teacher1, teacher2]

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


p1 = Period("Period 1")
p2 = Period("Period 2")
p3 = Period("Period 3")
periods = [p1, p2, p3]
print(p1.assigned_sections)
for section in sections:
    section.assigned_period = p1
    p1.assigned_sections.append(section)
print(p1.assigned_sections)
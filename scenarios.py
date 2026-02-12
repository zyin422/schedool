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
    #assigned_period: Optional[str] = None
    
    def is_fully_assigned(self) -> bool:
        # check if section has teacher, classroom, and timeslot
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

# SCENARIO 1: Balanced School
# Everything should schedule perfectly
def balanced_school():
    classroom_types = ["Biology", "Chemistry", "Physics", "PE", "General"]
    
    classrooms = [
        Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-102", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Gym-A", size=50, purposes={"PE"}),
        Classroom("Room-201", size=25, purposes={"General"}),
        Classroom("Room-202", size=25, purposes={"General"}),
        Classroom("Room-203", size=25, purposes={"General"}),
    ]
    
    class_list = ["Biology", "Math", "PE", "English"]
    classes = [
        Class("Biology", num_sections=2, required_classroom_type="Biology"),
        Class("Math", num_sections=2, required_classroom_type="General"),
        Class("PE", num_sections=1, required_classroom_type="PE"),
        Class("English", num_sections=2, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Ms. Smith", subjects={"Biology"}, max_sections=2, assigned_count=0),
        Teacher("Mr. Jones", subjects={"Math"}, max_sections=2, assigned_count=0),
        Teacher("Mr. Perez", subjects={"PE"}, max_sections=1, assigned_count=0),
        Teacher("Ms. Lee", subjects={"English"}, max_sections=2, assigned_count=0),
    ]
    
    periods = [Period("Period 1"), Period("Period 2"), Period("Period 3")]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods


# SCENARIO 2: Science-Heavy School
# Many science classes competing for limited lab space
def science_heavy_school():
    classroom_types = ["Biology", "Chemistry", "Physics", "PE", "General"]
    
    classrooms = [
        Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-102", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Gym-A", size=50, purposes={"PE"}),
        Classroom("Room-201", size=25, purposes={"General"}),
    ]
    
    class_list = ["Biology", "Chemistry", "Physics", "Math"]
    classes = [
        Class("Biology", num_sections=3, required_classroom_type="Biology"),
        Class("Chemistry", num_sections=3, required_classroom_type="Chemistry"),
        Class("Physics", num_sections=2, required_classroom_type="Physics"),
        Class("Math", num_sections=2, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Ms. Smith", subjects={"Biology", "Chemistry"}, max_sections=6, assigned_count=0),
        Teacher("Mr. Jones", subjects={"Physics", "Math"}, max_sections=6, assigned_count=0),
        Teacher("Dr. Brown", subjects={"Chemistry", "Physics"}, max_sections=4, assigned_count=0),
    ]
    
    periods = [Period("Period 1"), Period("Period 2"), Period("Period 3"), Period("Period 4")]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods


# SCENARIO 3: Understaffed School
# Not enough teachers with right qualifications
def understaffed_school():
    classroom_types = ["Biology", "Chemistry", "Physics", "PE", "General"]
    
    classrooms = [
        Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Gym-A", size=50, purposes={"PE"}),
        Classroom("Room-201", size=25, purposes={"General"}),
        Classroom("Room-202", size=25, purposes={"General"}),
    ]
    
    class_list = ["Biology", "Math", "PE", "English", "Chemistry"]
    classes = [
        Class("Biology", num_sections=3, required_classroom_type="Biology"),
        Class("Math", num_sections=2, required_classroom_type="General"),
        Class("PE", num_sections=2, required_classroom_type="PE"),
        Class("English", num_sections=2, required_classroom_type="General"),
        Class("Chemistry", num_sections=2, required_classroom_type="Chemistry"),
    ]
    
    teachers = [
        Teacher("Ms. Smith", subjects={"Biology"}, max_sections=2, assigned_count=0),  # Can't cover all Biology
        Teacher("Mr. Jones", subjects={"Math", "English"}, max_sections=3, assigned_count=0),  # Can't cover all Math+English
        Teacher("Mr. Perez", subjects={"PE"}, max_sections=2, assigned_count=0),
        # NO CHEMISTRY TEACHER - critical shortage
    ]
    
    periods = [Period("Period 1"), Period("Period 2"), Period("Period 3"), Period("Period 4")]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods

def balanced_school_medium():
    classroom_types = ["Biology", "Chemistry", "Physics", "PE", "Art", "Music", "CompSci", "General"]
    
    # 20 classrooms
    classrooms = [
        # 4 science labs
        Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-102", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-201", size=28, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-202", size=32, purposes={"Biology", "Chemistry", "Physics", "General"}),
        
        # 2 gyms
        Classroom("Gym-A", size=50, purposes={"PE"}),
        Classroom("Gym-B", size=45, purposes={"PE"}),
        
        # 2 art rooms
        Classroom("Art-101", size=25, purposes={"Art"}),
        Classroom("Art-102", size=25, purposes={"Art"}),
        
        # 1 music room
        Classroom("Music-101", size=30, purposes={"Music"}),
        
        # 1 computer lab
        Classroom("CompLab-101", size=30, purposes={"CompSci", "General"}),
        
        # 10 general classrooms
        Classroom("Room-101", size=25, purposes={"General"}),
        Classroom("Room-102", size=25, purposes={"General"}),
        Classroom("Room-103", size=30, purposes={"General"}),
        Classroom("Room-201", size=25, purposes={"General"}),
        Classroom("Room-202", size=25, purposes={"General"}),
        Classroom("Room-203", size=30, purposes={"General"}),
        Classroom("Room-301", size=25, purposes={"General"}),
        Classroom("Room-302", size=25, purposes={"General"}),
        Classroom("Room-303", size=30, purposes={"General"}),
        Classroom("Room-401", size=25, purposes={"General"}),
    ]
    
    class_list = [
        # Sciences
        "Biology", "Chemistry", "Physics",
        # Math
        "Algebra I", "Algebra II", "Geometry", "Pre-Calculus", "Calculus",
        # English
        "English 9", "English 10", "English 11", "English 12",
        # Social Studies
        "World History", "US History", "Government", "Economics",
        # Languages
        "Spanish I", "Spanish II", "French I",
        # Arts
        "Art I", "Art II",
        # Music
        "Band", "Choir",
        # PE
        "PE 9", "PE 10", "Health",
        # CompSci
        "Intro to CS", "AP CompSci A",
        # Electives
        "Drama", "Business"
    ]
    
    classes = [
        # Sciences (2 sections each)
        Class("Biology", num_sections=2, required_classroom_type="Biology"),
        Class("Chemistry", num_sections=2, required_classroom_type="Chemistry"),
        Class("Physics", num_sections=2, required_classroom_type="Physics"),
        
        # Math (2 sections each)
        Class("Algebra I", num_sections=2, required_classroom_type="General"),
        Class("Algebra II", num_sections=2, required_classroom_type="General"),
        Class("Geometry", num_sections=2, required_classroom_type="General"),
        Class("Pre-Calculus", num_sections=1, required_classroom_type="General"),
        Class("Calculus", num_sections=1, required_classroom_type="General"),
        
        # English (2 sections each)
        Class("English 9", num_sections=2, required_classroom_type="General"),
        Class("English 10", num_sections=2, required_classroom_type="General"),
        Class("English 11", num_sections=2, required_classroom_type="General"),
        Class("English 12", num_sections=2, required_classroom_type="General"),
        
        # Social Studies (2 sections for core)
        Class("World History", num_sections=2, required_classroom_type="General"),
        Class("US History", num_sections=2, required_classroom_type="General"),
        Class("Government", num_sections=2, required_classroom_type="General"),
        Class("Economics", num_sections=1, required_classroom_type="General"),
        
        # Languages (2 sections)
        Class("Spanish I", num_sections=2, required_classroom_type="General"),
        Class("Spanish II", num_sections=1, required_classroom_type="General"),
        Class("French I", num_sections=1, required_classroom_type="General"),
        
        # Arts (2 sections)
        Class("Art I", num_sections=2, required_classroom_type="Art"),
        Class("Art II", num_sections=1, required_classroom_type="Art"),
        
        # Music (1 section each)
        Class("Band", num_sections=1, required_classroom_type="Music"),
        Class("Choir", num_sections=1, required_classroom_type="Music"),
        
        # PE (2 sections each)
        Class("PE 9", num_sections=2, required_classroom_type="PE"),
        Class("PE 10", num_sections=2, required_classroom_type="PE"),
        Class("Health", num_sections=1, required_classroom_type="General"),
        
        # CompSci (1 section each)
        Class("Intro to CS", num_sections=1, required_classroom_type="CompSci"),
        Class("AP CompSci A", num_sections=1, required_classroom_type="CompSci"),
        
        # Electives (1 section each)
        Class("Drama", num_sections=1, required_classroom_type="General"),
        Class("Business", num_sections=1, required_classroom_type="General"),
    ]
    
    # 15 teachers
    teachers = [
        # Science (4 teachers)
        Teacher("Dr. Wilson", subjects={"Biology"}, max_sections=3, assigned_count=0),
        Teacher("Dr. Martinez", subjects={"Chemistry"}, max_sections=3, assigned_count=0),
        Teacher("Dr. Anderson", subjects={"Physics"}, max_sections=3, assigned_count=0),
        Teacher("Ms. Green", subjects={"Biology", "Chemistry"}, max_sections=2, assigned_count=0),
        
        # Math (3 teachers)
        Teacher("Ms. Davis", subjects={"Algebra I", "Algebra II", "Geometry"}, max_sections=4, assigned_count=0),
        Teacher("Mr. Lee", subjects={"Algebra I", "Geometry"}, max_sections=3, assigned_count=0),
        Teacher("Ms. Rodriguez", subjects={"Pre-Calculus", "Calculus", "Algebra II"}, max_sections=3, assigned_count=0),
        
        # English (3 teachers)
        Teacher("Ms. Johnson", subjects={"English 9", "English 10"}, max_sections=3, assigned_count=0),
        Teacher("Mr. Smith", subjects={"English 11", "English 12"}, max_sections=3, assigned_count=0),
        Teacher("Ms. Taylor", subjects={"English 9", "English 10", "Drama"}, max_sections=3, assigned_count=0),
        
        # Social Studies (2 teachers)
        Teacher("Mr. Adams", subjects={"World History", "US History"}, max_sections=4, assigned_count=0),
        Teacher("Ms. Clark", subjects={"Government", "Economics", "Business"}, max_sections=4, assigned_count=0),
        
        # Languages (1 teacher)
        Teacher("Sra. Hernandez", subjects={"Spanish I", "Spanish II", "French I"}, max_sections=4, assigned_count=0),
        
        # Arts & Music (2 teachers)
        Teacher("Ms. Rivera", subjects={"Art I", "Art II"}, max_sections=3, assigned_count=0),
        Teacher("Mr. Hall", subjects={"Band", "Choir"}, max_sections=2, assigned_count=0),
        
        # PE (1 teacher)
        Teacher("Coach Davis", subjects={"PE 9", "PE 10", "Health"}, max_sections=5, assigned_count=0),
        
        # CompSci (1 teacher)
        Teacher("Mr. Singh", subjects={"Intro to CS", "AP CompSci A"}, max_sections=2, assigned_count=0),
    ]
    
    # 5 periods
    periods = [
        Period("Period 1"), Period("Period 2"), Period("Period 3"), 
        Period("Period 4"), Period("Period 5")
    ]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods

def balanced_school_large():
    classroom_types = ["Biology", "Chemistry", "Physics", "PE", "Art", "Music", "CompSci", "General"]
    
    # 40+ classrooms
    classrooms = [
        # 8 science labs
        Classroom("Lab-101", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-102", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-103", size=28, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-104", size=32, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-201", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-202", size=30, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-203", size=28, purposes={"Biology", "Chemistry", "Physics", "General"}),
        Classroom("Lab-204", size=32, purposes={"Biology", "Chemistry", "Physics", "General"}),
        
        # 3 gyms
        Classroom("Gym-A", size=50, purposes={"PE"}),
        Classroom("Gym-B", size=50, purposes={"PE"}),
        Classroom("Gym-C", size=45, purposes={"PE"}),
        
        # 3 art rooms
        Classroom("Art-101", size=25, purposes={"Art"}),
        Classroom("Art-102", size=25, purposes={"Art"}),
        Classroom("Art-103", size=28, purposes={"Art"}),
        
        # 3 music rooms
        Classroom("Music-101", size=30, purposes={"Music"}),
        Classroom("Music-102", size=30, purposes={"Music"}),
        Classroom("Music-103", size=25, purposes={"Music"}),
        
        # 3 computer labs
        Classroom("CompLab-101", size=30, purposes={"CompSci", "General"}),
        Classroom("CompLab-102", size=30, purposes={"CompSci", "General"}),
        Classroom("CompLab-103", size=28, purposes={"CompSci", "General"}),
        
        # 20 general classrooms
        Classroom("Room-101", size=25, purposes={"General"}),
        Classroom("Room-102", size=25, purposes={"General"}),
        Classroom("Room-103", size=30, purposes={"General"}),
        Classroom("Room-104", size=28, purposes={"General"}),
        Classroom("Room-105", size=25, purposes={"General"}),
        Classroom("Room-201", size=25, purposes={"General"}),
        Classroom("Room-202", size=25, purposes={"General"}),
        Classroom("Room-203", size=30, purposes={"General"}),
        Classroom("Room-204", size=28, purposes={"General"}),
        Classroom("Room-205", size=25, purposes={"General"}),
        Classroom("Room-301", size=25, purposes={"General"}),
        Classroom("Room-302", size=25, purposes={"General"}),
        Classroom("Room-303", size=30, purposes={"General"}),
        Classroom("Room-304", size=28, purposes={"General"}),
        Classroom("Room-305", size=25, purposes={"General"}),
        Classroom("Room-401", size=25, purposes={"General"}),
        Classroom("Room-402", size=25, purposes={"General"}),
        Classroom("Room-403", size=30, purposes={"General"}),
        Classroom("Room-404", size=28, purposes={"General"}),
        Classroom("Room-405", size=25, purposes={"General"}),
    ]
    
    class_list = [
        # Sciences
        "Biology", "Chemistry", "Physics", "AP Biology", "AP Chemistry", "AP Physics",
        # Math
        "Algebra I", "Algebra II", "Geometry", "Pre-Calculus", "Calculus", "Statistics",
        # English
        "English 9", "English 10", "English 11", "English 12", "Creative Writing", "Journalism",
        # Social Studies
        "World History", "US History", "Government", "Economics", "Psychology", "Sociology",
        # Languages
        "Spanish I", "Spanish II", "Spanish III", "French I", "French II", "German I",
        # Arts
        "Art I", "Art II", "Drawing", "Painting", "Sculpture", "Photography",
        # Music
        "Band", "Choir", "Orchestra", "Music Theory", "Guitar",
        # PE
        "PE 9", "PE 10", "PE 11", "PE 12", "Health",
        # CompSci
        "Intro to CS", "AP CompSci A", "Web Design", "Robotics",
        # Electives
        "Drama", "Debate", "Yearbook", "Business", "Accounting", "Marketing",
        "Environmental Science", "Astronomy", "Anatomy"
    ]
    
    classes = [
        # Sciences (3 sections each for core, 2 for AP)
        Class("Biology", num_sections=3, required_classroom_type="Biology"),
        Class("Chemistry", num_sections=3, required_classroom_type="Chemistry"),
        Class("Physics", num_sections=3, required_classroom_type="Physics"),
        Class("AP Biology", num_sections=2, required_classroom_type="Biology"),
        Class("AP Chemistry", num_sections=2, required_classroom_type="Chemistry"),
        Class("AP Physics", num_sections=2, required_classroom_type="Physics"),
        
        # Math (3 sections each)
        Class("Algebra I", num_sections=3, required_classroom_type="General"),
        Class("Algebra II", num_sections=3, required_classroom_type="General"),
        Class("Geometry", num_sections=3, required_classroom_type="General"),
        Class("Pre-Calculus", num_sections=2, required_classroom_type="General"),
        Class("Calculus", num_sections=2, required_classroom_type="General"),
        Class("Statistics", num_sections=2, required_classroom_type="General"),
        
        # English (3 sections each)
        Class("English 9", num_sections=3, required_classroom_type="General"),
        Class("English 10", num_sections=3, required_classroom_type="General"),
        Class("English 11", num_sections=3, required_classroom_type="General"),
        Class("English 12", num_sections=3, required_classroom_type="General"),
        Class("Creative Writing", num_sections=2, required_classroom_type="General"),
        Class("Journalism", num_sections=1, required_classroom_type="General"),
        
        # Social Studies (3 sections for core, 2 for electives)
        Class("World History", num_sections=3, required_classroom_type="General"),
        Class("US History", num_sections=3, required_classroom_type="General"),
        Class("Government", num_sections=3, required_classroom_type="General"),
        Class("Economics", num_sections=2, required_classroom_type="General"),
        Class("Psychology", num_sections=2, required_classroom_type="General"),
        Class("Sociology", num_sections=1, required_classroom_type="General"),
        
        # Languages (2-3 sections)
        Class("Spanish I", num_sections=3, required_classroom_type="General"),
        Class("Spanish II", num_sections=2, required_classroom_type="General"),
        Class("Spanish III", num_sections=2, required_classroom_type="General"),
        Class("French I", num_sections=2, required_classroom_type="General"),
        Class("French II", num_sections=2, required_classroom_type="General"),
        Class("German I", num_sections=1, required_classroom_type="General"),
        
        # Arts (2 sections each)
        Class("Art I", num_sections=2, required_classroom_type="Art"),
        Class("Art II", num_sections=2, required_classroom_type="Art"),
        Class("Drawing", num_sections=2, required_classroom_type="Art"),
        Class("Painting", num_sections=1, required_classroom_type="Art"),
        Class("Sculpture", num_sections=1, required_classroom_type="Art"),
        Class("Photography", num_sections=2, required_classroom_type="Art"),
        
        # Music (2 sections each)
        Class("Band", num_sections=2, required_classroom_type="Music"),
        Class("Choir", num_sections=2, required_classroom_type="Music"),
        Class("Orchestra", num_sections=2, required_classroom_type="Music"),
        Class("Music Theory", num_sections=1, required_classroom_type="Music"),
        Class("Guitar", num_sections=2, required_classroom_type="Music"),
        
        # PE (3 sections each for grade levels, 2 for health)
        Class("PE 9", num_sections=3, required_classroom_type="PE"),
        Class("PE 10", num_sections=3, required_classroom_type="PE"),
        Class("PE 11", num_sections=2, required_classroom_type="PE"),
        Class("PE 12", num_sections=2, required_classroom_type="PE"),
        Class("Health", num_sections=2, required_classroom_type="General"),
        
        # CompSci (2 sections each)
        Class("Intro to CS", num_sections=2, required_classroom_type="CompSci"),
        Class("AP CompSci A", num_sections=2, required_classroom_type="CompSci"),
        Class("Web Design", num_sections=2, required_classroom_type="CompSci"),
        Class("Robotics", num_sections=1, required_classroom_type="CompSci"),
        
        # Electives (1-2 sections each)
        Class("Drama", num_sections=2, required_classroom_type="General"),
        Class("Debate", num_sections=1, required_classroom_type="General"),
        Class("Yearbook", num_sections=1, required_classroom_type="General"),
        Class("Business", num_sections=2, required_classroom_type="General"),
        Class("Accounting", num_sections=1, required_classroom_type="General"),
        Class("Marketing", num_sections=1, required_classroom_type="General"),
        Class("Environmental Science", num_sections=2, required_classroom_type="Biology"),
        Class("Astronomy", num_sections=1, required_classroom_type="General"),
        Class("Anatomy", num_sections=2, required_classroom_type="Biology"),
    ]
    
    # 30+ teachers with balanced workloads
    teachers = [
        # Science (8 teachers)
        Teacher("Dr. Wilson", subjects={"Biology", "AP Biology", "Environmental Science", "Anatomy"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Chen", subjects={"Biology", "AP Biology"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Martinez", subjects={"Chemistry", "AP Chemistry"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Kumar", subjects={"Chemistry", "AP Chemistry"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Anderson", subjects={"Physics", "AP Physics"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Thompson", subjects={"Physics", "AP Physics"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Green", subjects={"Environmental Science", "Biology"}, max_sections=4, assigned_count=0),
        Teacher("Mr. Stone", subjects={"Anatomy", "Biology"}, max_sections=4, assigned_count=0),
        
        # Math (6 teachers)
        Teacher("Ms. Davis", subjects={"Algebra I", "Algebra II", "Geometry"}, max_sections=5, assigned_count=0),
        Teacher("Mr. Lee", subjects={"Algebra I", "Geometry"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Rodriguez", subjects={"Algebra II", "Pre-Calculus", "Calculus"}, max_sections=5, assigned_count=0),
        Teacher("Mr. White", subjects={"Geometry", "Statistics"}, max_sections=5, assigned_count=0),
        Teacher("Dr. Park", subjects={"Pre-Calculus", "Calculus", "Statistics"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Brown", subjects={"Algebra I", "Statistics"}, max_sections=4, assigned_count=0),
        
        # English (5 teachers)
        Teacher("Ms. Johnson", subjects={"English 9", "English 10"}, max_sections=5, assigned_count=0),
        Teacher("Mr. Smith", subjects={"English 11", "English 12"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Taylor", subjects={"English 9", "Creative Writing", "Journalism"}, max_sections=5, assigned_count=0),
        Teacher("Mr. Garcia", subjects={"English 10", "English 11"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Miller", subjects={"English 12", "Creative Writing"}, max_sections=4, assigned_count=0),
        
        # Social Studies (4 teachers)
        Teacher("Mr. Adams", subjects={"World History", "US History"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Clark", subjects={"Government", "Economics"}, max_sections=5, assigned_count=0),
        Teacher("Mr. Lewis", subjects={"US History", "Government"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Walker", subjects={"Psychology", "Sociology", "World History"}, max_sections=5, assigned_count=0),
        
        # Languages (3 teachers)
        Teacher("Sra. Hernandez", subjects={"Spanish I", "Spanish II", "Spanish III"}, max_sections=5, assigned_count=0),
        Teacher("Mme. Dubois", subjects={"French I", "French II"}, max_sections=5, assigned_count=0),
        Teacher("Herr Schmidt", subjects={"German I", "Spanish I"}, max_sections=4, assigned_count=0),
        
        # Arts (2 teachers)
        Teacher("Ms. Rivera", subjects={"Art I", "Art II", "Drawing", "Painting"}, max_sections=5, assigned_count=0),
        Teacher("Mr. Brooks", subjects={"Sculpture", "Photography", "Art I"}, max_sections=5, assigned_count=0),
        
        # Music (2 teachers)
        Teacher("Mr. Hall", subjects={"Band", "Orchestra", "Music Theory"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Young", subjects={"Choir", "Guitar", "Music Theory"}, max_sections=5, assigned_count=0),
        
        # PE (3 teachers)
        Teacher("Coach Davis", subjects={"PE 9", "PE 10", "PE 11", "PE 12", "Health"}, max_sections=5, assigned_count=0),
        Teacher("Coach Martin", subjects={"PE 9", "PE 10", "PE 11", "PE 12"}, max_sections=5, assigned_count=0),
        Teacher("Coach Allen", subjects={"PE 9", "PE 10", "Health"}, max_sections=4, assigned_count=0),
        
        # CompSci (2 teachers)
        Teacher("Mr. Singh", subjects={"Intro to CS", "AP CompSci A", "Web Design"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Wang", subjects={"Robotics", "Intro to CS", "Web Design"}, max_sections=4, assigned_count=0),
        
        # Electives (2 teachers)
        Teacher("Ms. Foster", subjects={"Drama", "Debate", "English 9"}, max_sections=4, assigned_count=0),
        Teacher("Mr. Cooper", subjects={"Business", "Accounting", "Marketing", "Economics"}, max_sections=5, assigned_count=0),
        Teacher("Ms. Bell", subjects={"Yearbook", "Journalism", "English 10"}, max_sections=3, assigned_count=0),
        Teacher("Dr. Hill", subjects={"Astronomy", "Physics"}, max_sections=3, assigned_count=0),
    ]
    
    # 8 periods to accommodate all sections
    periods = [
        Period("Period 1"), Period("Period 2"), Period("Period 3"), Period("Period 4"),
        Period("Period 5"), Period("Period 6"), Period("Period 7"), Period("Period 8")
    ]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods

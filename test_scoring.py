"""
Test script to verify the scoring system works correctly.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import sys
sys.path.insert(0, '.')

from scheduler import Section, Period, Teacher, Classroom
from constraints import Constraint
from scoring import calculate_score, ScoreResult


def create_test_data():
    """Create test data for scoring evaluation."""
    
    # Create teachers
    teacher1 = Teacher(name="Mr. Smith", subjects={"Math"}, max_sections=5, assigned_count=0)
    teacher2 = Teacher(name="Ms. Johnson", subjects={"English"}, max_sections=5, assigned_count=0)
    teacher3 = Teacher(name="Dr. Brown", subjects={"Science"}, max_sections=5, assigned_count=0)
    
    # Create classrooms
    room1 = Classroom(name="Room 101", size=30, purposes={"Math", "Science"})
    room2 = Classroom(name="Room 102", size=25, purposes={"English"})
    
    # Create sections
    math_section1 = Section(section_id="Math-1", class_name="Math", required_classroom_type="Math", assigned_teacher=teacher1, assigned_classroom=room1)
    math_section2 = Section(section_id="Math-2", class_name="Math", required_classroom_type="Math", assigned_teacher=teacher1, assigned_classroom=room1)
    english_section1 = Section(section_id="English-1", class_name="English", required_classroom_type="English", assigned_teacher=teacher2, assigned_classroom=room2)
    science_section1 = Section(section_id="Science-1", class_name="Science", required_classroom_type="Science", assigned_teacher=teacher3, assigned_classroom=room1)
    
    # Create periods
    period1 = Period(period_id="Period 1", assigned_sections=[math_section1])
    period2 = Period(period_id="Period 2", assigned_sections=[english_section1])
    period3 = Period(period_id="Period 3", assigned_sections=[])
    period4 = Period(period_id="Period 4", assigned_sections=[science_section1])
    period5 = Period(period_id="Period 5", assigned_sections=[math_section2])
    
    periods = [period1, period2, period3, period4, period5]
    sections = [math_section1, math_section2, english_section1, science_section1]
    
    return periods, sections


def test_calculate_score():
    """Test the calculate_score function."""
    print("\n=== Testing calculate_score ===")
    periods, sections = create_test_data()
    
    # Create a mock schedule object
    @dataclass
    class MockSchedule:
        sections: List[Section]
    
    schedule = MockSchedule(sections=sections)
    
    # Create constraints
    constraints = [
        Constraint(constraint_type="teacher_morning_pref", weight=5, applies_to="Mr. Smith", parameters={}),
        Constraint(constraint_type="teacher_morning_pref", weight=5, applies_to="Ms. Johnson", parameters={}),
        Constraint(constraint_type="teacher_morning_pref", weight=5, applies_to="Dr. Brown", parameters={}),
        Constraint(constraint_type="teacher_afternoon_pref", weight=5, applies_to="Mr. Smith", parameters={}),
        Constraint(constraint_type="teacher_afternoon_pref", weight=5, applies_to="Ms. Johnson", parameters={}),
        Constraint(constraint_type="teacher_afternoon_pref", weight=5, applies_to="Dr. Brown", parameters={}),
        Constraint(constraint_type="room_unavailable", weight=5, applies_to="Room 101", parameters={"blocked_period": "Period 3"}),
        Constraint(constraint_type="spread_class_sections", weight=10, applies_to="Math", parameters={}),
    ]
    
    # Calculate score
    total_score, max_possible, satisfied, unsatisfied = calculate_score(schedule, periods, constraints)
    
    print(f"Total score: {total_score}")
    print(f"Max possible: {max_possible}")
    print(f"Number satisfied: {len(satisfied)}")
    print(f"Number unsatisfied: {len(unsatisfied)}")
    
    # Verify results
    # Constraints: 3 morning pref (15) + 3 afternoon pref (15) + 1 room unavailable (5) + 1 spread (10) = 45
    assert max_possible == 45, f"Expected max_possible=45, got {max_possible}"
    # Satisfied: Mr. Smith morning (5), Ms. Johnson morning (5), Mr. Smith afternoon (5), Dr. Brown afternoon (5), room (5), spread (10) = 35
    assert total_score == 35, f"Expected total_score=35, got {total_score}"
    assert len(satisfied) == 6, f"Expected 6 satisfied, got {len(satisfied)}"
    assert len(unsatisfied) == 2, f"Expected 2 unsatisfied, got {len(unsatisfied)}"
    
    print("PASSED: calculate_score basic test!")
    
    # Print detailed breakdown
    print("\n--- Satisfied constraints ---")
    for c in satisfied:
        print(f"  - {c.constraint_type} ({c.applies_to}): {c.weight} pts")
    
    print("\n--- Unsatisfied constraints ---")
    for c in unsatisfied:
        print(f"  - {c.constraint_type} ({c.applies_to}): {c.weight} pts")
    
    return True


def test_calculate_score_empty_constraints():
    """Test calculate_score with no constraints."""
    print("\n=== Testing calculate_score with empty constraints ===")
    
    @dataclass
    class MockSchedule:
        sections: List[Section]
    
    schedule = MockSchedule(sections=[])
    periods = []
    constraints = []
    
    total_score, max_possible, satisfied, unsatisfied = calculate_score(schedule, periods, constraints)
    
    assert total_score == 0
    assert max_possible == 0
    assert len(satisfied) == 0
    assert len(unsatisfied) == 0
    
    print("PASSED: Empty constraints test!")


def test_calculate_score_all_satisfied():
    """Test calculate_score when all constraints are satisfied."""
    print("\n=== Testing calculate_score with all satisfied ===")
    periods, sections = create_test_data()
    
    @dataclass
    class MockSchedule:
        sections: List[Section]
    
    schedule = MockSchedule(sections=sections)
    
    # All constraints should be satisfied
    constraints = [
        Constraint(constraint_type="teacher_morning_pref", weight=5, applies_to="Mr. Smith", parameters={}),
        Constraint(constraint_type="teacher_afternoon_pref", weight=5, applies_to="Mr. Smith", parameters={}),
        Constraint(constraint_type="room_unavailable", weight=5, applies_to="Room 102", parameters={"blocked_period": "Period 1"}),
    ]
    
    total_score, max_possible, satisfied, unsatisfied = calculate_score(schedule, periods, constraints)
    
    assert total_score == 15
    assert max_possible == 15
    assert len(satisfied) == 3
    assert len(unsatisfied) == 0
    
    print("PASSED: All satisfied test!")


def test_calculate_score_all_unsatisfied():
    """Test calculate_score when all constraints are unsatisfied."""
    print("\n=== Testing calculate_score with all unsatisfied ===")
    periods, sections = create_test_data()
    
    @dataclass
    class MockSchedule:
        sections: List[Section]
    
    schedule = MockSchedule(sections=sections)
    
    # Create constraints that will all fail
    constraints = [
        Constraint(constraint_type="teacher_morning_pref", weight=5, applies_to="Dr. Brown", parameters={}),  # Only afternoon
        Constraint(constraint_type="teacher_afternoon_pref", weight=5, applies_to="Ms. Johnson", parameters={}),  # Only morning
        Constraint(constraint_type="room_unavailable", weight=5, applies_to="Room 101", parameters={"blocked_period": "Period 1"}),  # Used
    ]
    
    total_score, max_possible, satisfied, unsatisfied = calculate_score(schedule, periods, constraints)
    
    assert total_score == 0
    assert max_possible == 15
    assert len(satisfied) == 0
    assert len(unsatisfied) == 3
    
    print("PASSED: All unsatisfied test!")


if __name__ == "__main__":
    print("Running scoring tests...")
    
    test_calculate_score_empty_constraints()
    test_calculate_score_all_satisfied()
    test_calculate_score_all_unsatisfied()
    test_calculate_score()
    
    print("\n" + "="*50)
    print("ALL SCORING TESTS PASSED!")
    print("="*50)

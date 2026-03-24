"""
Test script to verify the constraint system works correctly.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import sys
sys.path.insert(0, '.')

from scheduler import Section, Period, Teacher, Classroom
from constraints import (
    Constraint, 
    evaluate_constraint,
    ConstraintType,
    get_constraint_display_name
)


def create_test_data():
    """Create test data for constraint evaluation."""
    
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


def test_teacher_morning_pref():
    """Test teacher_morning_pref constraint."""
    print("\n=== Testing teacher_morning_pref ===")
    periods, sections = create_test_data()
    
    # Test: Mr. Smith has Math-1 in Period 1 (morning) - should be satisfied
    constraint = Constraint(
        constraint_type="teacher_morning_pref",
        weight=5,
        applies_to="Mr. Smith",
        parameters={}
    )
    result = evaluate_constraint(constraint, periods, sections)
    print(f"Mr. Smith has class in Period 1: {result} (expected: True)")
    assert result == True, "Expected True for teacher with morning class"
    
    # Test: Ms. Johnson has English-1 in Period 2 (morning) - should be satisfied
    constraint2 = Constraint(
        constraint_type="teacher_morning_pref",
        weight=5,
        applies_to="Ms. Johnson",
        parameters={}
    )
    result2 = evaluate_constraint(constraint2, periods, sections)
    print(f"Ms. Johnson has class in Period 2: {result2} (expected: True)")
    assert result2 == True, "Expected True for teacher with morning class"
    
    # Test: Dr. Brown only has class in Period 4 (afternoon) - should NOT be satisfied
    constraint3 = Constraint(
        constraint_type="teacher_morning_pref",
        weight=5,
        applies_to="Dr. Brown",
        parameters={}
    )
    result3 = evaluate_constraint(constraint3, periods, sections)
    print(f"Dr. Brown has class in Period 4 only: {result3} (expected: False)")
    assert result3 == False, "Expected False for teacher without morning class"
    
    print("PASSED: teacher_morning_pref tests passed!")


def test_teacher_afternoon_pref():
    """Test teacher_afternoon_pref constraint."""
    print("\n=== Testing teacher_afternoon_pref ===")
    periods, sections = create_test_data()
    
    # Test: Dr. Brown has Science-1 in Period 4 (afternoon) - should be satisfied
    constraint = Constraint(
        constraint_type="teacher_afternoon_pref",
        weight=5,
        applies_to="Dr. Brown",
        parameters={}
    )
    result = evaluate_constraint(constraint, periods, sections)
    print(f"Dr. Brown has class in Period 4: {result} (expected: True)")
    assert result == True, "Expected True for teacher with afternoon class"
    
    # Test: Mr. Smith has Math-2 in Period 5 (afternoon) - should be satisfied
    constraint2 = Constraint(
        constraint_type="teacher_afternoon_pref",
        weight=5,
        applies_to="Mr. Smith",
        parameters={}
    )
    result2 = evaluate_constraint(constraint2, periods, sections)
    print(f"Mr. Smith has class in Period 5: {result2} (expected: True)")
    assert result2 == True, "Expected True for teacher with afternoon class"
    
    # Test: Ms. Johnson only has class in Period 2 (morning) - should NOT be satisfied
    constraint3 = Constraint(
        constraint_type="teacher_afternoon_pref",
        weight=5,
        applies_to="Ms. Johnson",
        parameters={}
    )
    result3 = evaluate_constraint(constraint3, periods, sections)
    print(f"Ms. Johnson has class in Period 2 only: {result3} (expected: False)")
    assert result3 == False, "Expected False for teacher without afternoon class"
    
    print("PASSED: teacher_afternoon_pref tests passed!")


def test_room_unavailable():
    """Test room_unavailable constraint."""
    print("\n=== Testing room_unavailable ===")
    periods, sections = create_test_data()
    
    # Test: Room 101 is used in Period 1 - should NOT be satisfied (blocked_period=1)
    constraint = Constraint(
        constraint_type="room_unavailable",
        weight=5,
        applies_to="Room 101",
        parameters={"blocked_period": "Period 1"}
    )
    result = evaluate_constraint(constraint, periods, sections)
    print(f"Room 101 blocked in Period 1 (but used): {result} (expected: False)")
    assert result == False, "Expected False for room used during blocked period"
    
    # Test: Room 102 is NOT used in Period 3 - should be satisfied
    constraint2 = Constraint(
        constraint_type="room_unavailable",
        weight=5,
        applies_to="Room 102",
        parameters={"blocked_period": "Period 3"}
    )
    result2 = evaluate_constraint(constraint2, periods, sections)
    print(f"Room 102 blocked in Period 3 (free): {result2} (expected: True)")
    assert result2 == True, "Expected True for room free during blocked period"
    
    # Test: Room 101 is NOT used in Period 3 - should be satisfied
    constraint3 = Constraint(
        constraint_type="room_unavailable",
        weight=5,
        applies_to="Room 101",
        parameters={"blocked_period": "Period 3"}
    )
    result3 = evaluate_constraint(constraint3, periods, sections)
    print(f"Room 101 blocked in Period 3 (free): {result3} (expected: True)")
    assert result3 == True, "Expected True for room free during blocked period"
    
    print("PASSED: room_unavailable tests passed!")


def test_max_consecutive():
    """Test max_consecutive constraint."""
    print("\n=== Testing max_consecutive ===")
    periods, sections = create_test_data()
    
    # Mr. Smith has classes in Period 1 and Period 5 (not consecutive)
    constraint = Constraint(
        constraint_type="max_consecutive",
        weight=5,
        applies_to="Mr. Smith",
        parameters={"max_consecutive": 2}
    )
    result = evaluate_constraint(constraint, periods, sections)
    print(f"Mr. Smith max 2 consecutive (Periods 1,5): {result} (expected: True)")
    assert result == True, "Expected True for non-consecutive periods"
    
    # Create test data with consecutive periods
    math_section3 = Section(section_id="Math-3", class_name="Math", required_classroom_type="Math", 
                           assigned_teacher=sections[0].assigned_teacher, assigned_classroom=sections[0].assigned_classroom)
    period3_consecutive = Period(period_id="Period 3", assigned_sections=[math_section3])
    periods_consecutive = [periods[0], periods[1], period3_consecutive, periods[3], periods[4]]
    
    # Mr. Smith now has Period 1 and Period 3 (not consecutive)
    constraint2 = Constraint(
        constraint_type="max_consecutive",
        weight=5,
        applies_to="Mr. Smith",
        parameters={"max_consecutive": 1}
    )
    result2 = evaluate_constraint(constraint2, periods_consecutive, sections)
    print(f"Mr. Smith max 1 consecutive (Periods 1,3): {result2} (expected: True)")
    assert result2 == True, "Expected True for non-consecutive periods"
    
    print("PASSED: max_consecutive tests passed!")


def test_spread_class_sections():
    """Test spread_class_sections constraint."""
    print("\n=== Testing spread_class_sections ===")
    periods, sections = create_test_data()
    
    # Math has 2 sections: Math-1 in Period 1, Math-2 in Period 5 - should be satisfied
    constraint = Constraint(
        constraint_type="spread_class_sections",
        weight=5,
        applies_to="Math",
        parameters={}
    )
    result = evaluate_constraint(constraint, periods, sections)
    print(f"Math sections in different periods (1,5): {result} (expected: True)")
    assert result == True, "Expected True for sections in different periods"
    
    # Create test with sections in same period
    math_section_same = Section(section_id="Math-3", class_name="Math", required_classroom_type="Math",
                                assigned_teacher=sections[0].assigned_teacher, assigned_classroom=sections[0].assigned_classroom)
    period1_with_2 = Period(period_id="Period 1", assigned_sections=[sections[0], math_section_same])
    periods_same = [period1_with_2, periods[1], periods[2], periods[3], periods[4]]
    
    # Now Math has 2 sections in Period 1 - should NOT be satisfied
    constraint2 = Constraint(
        constraint_type="spread_class_sections",
        weight=5,
        applies_to="Math",
        parameters={}
    )
    result2 = evaluate_constraint(constraint2, periods_same, sections + [math_section_same])
    print(f"Math sections in same period (1,1): {result2} (expected: False)")
    assert result2 == False, "Expected False for sections in same period"
    
    print("PASSED: spread_class_sections tests passed!")


def test_constraint_class_is_satisfied():
    """Test the is_satisfied method on Constraint class."""
    print("\n=== Testing Constraint.is_satisfied method ===")
    
    # Create a mock schedule object
    @dataclass
    class MockSchedule:
        sections: List[Section]
    
    periods, sections = create_test_data()
    schedule = MockSchedule(sections=sections)
    
    # Test is_satisfied method
    constraint = Constraint(
        constraint_type="teacher_morning_pref",
        weight=5,
        applies_to="Mr. Smith",
        parameters={}
    )
    result = constraint.is_satisfied(schedule, periods)
    print(f"Constraint.is_satisfied result: {result} (expected: True)")
    assert result == True, "Expected True from is_satisfied method"
    
    print("PASSED: Constraint.is_satisfied tests passed!")


def test_constraint_type_enum():
    """Test ConstraintType enum."""
    print("\n=== Testing ConstraintType enum ===")
    
    assert ConstraintType.TEACHER_MORNING_PREF.value == "teacher_morning_pref"
    assert ConstraintType.TEACHER_AFTERNOON_PREF.value == "teacher_afternoon_pref"
    assert ConstraintType.ROOM_UNAVAILABLE.value == "room_unavailable"
    assert ConstraintType.MAX_CONSECUTIVE.value == "max_consecutive"
    assert ConstraintType.SPREAD_CLASS_SECTIONS.value == "spread_class_sections"
    
    print("PASSED: ConstraintType enum tests passed!")


def test_get_constraint_display_name():
    """Test display name function."""
    print("\n=== Testing get_constraint_display_name ===")
    
    assert get_constraint_display_name("teacher_morning_pref") == "Teacher Morning Preference"
    assert get_constraint_display_name("teacher_afternoon_pref") == "Teacher Afternoon Preference"
    assert get_constraint_display_name("room_unavailable") == "Room Unavailable"
    assert get_constraint_display_name("max_consecutive") == "Max Consecutive Periods"
    assert get_constraint_display_name("spread_class_sections") == "Spread Class Sections"
    
    print("PASSED: get_constraint_display_name tests passed!")


if __name__ == "__main__":
    print("Running constraint tests...")
    
    test_constraint_type_enum()
    test_get_constraint_display_name()
    test_teacher_morning_pref()
    test_teacher_afternoon_pref()
    test_room_unavailable()
    test_max_consecutive()
    test_spread_class_sections()
    test_constraint_class_is_satisfied()
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED! SUCCESS")
    print("="*50)

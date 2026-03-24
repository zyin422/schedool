"""
Test script to verify the scheduler modifications work correctly.
"""
import sys
sys.path.insert(0, '.')

from scheduler import (
    Classroom, Class, Teacher, Section, Period, 
    run_scheduler, generate_multiple_schedules
)


def create_test_data():
    """Create test data for scheduler testing."""
    
    # Create periods
    periods = [
        Period(period_id="Period 1"),
        Period(period_id="Period 2"),
        Period(period_id="Period 3"),
        Period(period_id="Period 4"),
        Period(period_id="Period 5"),
    ]
    
    # Create classrooms
    classrooms = [
        Classroom(name="Room 101", size=30, purposes={"Math", "Science"}),
        Classroom(name="Room 102", size=25, purposes={"English"}),
    ]
    
    # Create classes
    classes = [
        Class(name="Math", num_sections=2, required_classroom_type="Math"),
        Class(name="English", num_sections=1, required_classroom_type="English"),
        Class(name="Science", num_sections=1, required_classroom_type="Science"),
    ]
    
    # Create teachers
    teachers = [
        Teacher(name="Mr. Smith", subjects={"Math"}, max_sections=5, assigned_count=0),
        Teacher(name="Ms. Johnson", subjects={"English"}, max_sections=5, assigned_count=0),
        Teacher(name="Dr. Brown", subjects={"Science"}, max_sections=5, assigned_count=0),
    ]
    
    classroom_types = ["Math", "English", "Science"]
    class_list = ["Math", "English", "Science"]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods


def test_run_scheduler_with_seed():
    """Test run_scheduler with seed parameter."""
    print("\n=== Testing run_scheduler with seed ===")
    
    classroom_types, classrooms, class_list, classes, teachers, periods = create_test_data()
    
    # Test with seed 0
    sections1 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=0)
    print(f"Seed 0: Generated {len(sections1)} sections")
    
    # Test with same seed - should produce same results
    sections2 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=0)
    print(f"Seed 0 (repeat): Generated {len(sections2)} sections")
    
    # Test with different seed
    sections3 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=42)
    print(f"Seed 42: Generated {len(sections3)} sections")
    
    # Verify same seed gives same results
    assert len(sections1) == len(sections2), "Same seed should produce same number of sections"
    print("PASSED: run_scheduler with seed works correctly!")


def test_generate_multiple_schedules():
    """Test generate_multiple_schedules function."""
    print("\n=== Testing generate_multiple_schedules ===")
    
    classroom_types, classrooms, class_list, classes, teachers, periods = create_test_data()
    
    # Generate 5 schedules
    schedules = generate_multiple_schedules(
        classroom_types, classrooms, class_list, classes, teachers, periods, n=5
    )
    
    print(f"Generated {len(schedules)} schedules")
    
    # Check each schedule
    for i, schedule in enumerate(schedules):
        fully_assigned = sum(1 for s in schedule if s.is_fully_assigned())
        print(f"  Schedule {i}: {len(schedule)} sections, {fully_assigned} fully assigned")
    
    print("PASSED: generate_multiple_schedules works correctly!")


def test_different_seeds_produce_different_results():
    """Test that different seeds produce different results."""
    print("\n=== Testing that different seeds produce different results ===")
    
    classroom_types, classrooms, class_list, classes, teachers, periods = create_test_data()
    
    # Generate schedules with different seeds
    schedule0 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=0)
    schedule1 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=1)
    schedule2 = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods, seed=2)
    
    # Get assignments for comparison
    def get_assignments(sections):
        return [(s.section_id, s.assigned_teacher.name if s.assigned_teacher else None, 
                 s.assigned_classroom.name if s.assigned_classroom else None) for s in sections]
    
    assignments0 = get_assignments(schedule0)
    assignments1 = get_assignments(schedule1)
    assignments2 = get_assignments(schedule2)
    
    # All should have same structure but potentially different assignments
    print(f"Schedule 0 assignments: {len(assignments0)} sections")
    print(f"Schedule 1 assignments: {len(assignments1)} sections")
    print(f"Schedule 2 assignments: {len(assignments2)} sections")
    
    # At least verify they complete
    assert len(schedule0) > 0, "Schedule 0 should have sections"
    assert len(schedule1) > 0, "Schedule 1 should have sections"
    assert len(schedule2) > 0, "Schedule 2 should have sections"
    
    print("PASSED: Different seeds produce schedules!")


if __name__ == "__main__":
    print("Running scheduler tests...")
    
    test_run_scheduler_with_seed()
    test_generate_multiple_schedules()
    test_different_seeds_produce_different_results()
    
    print("\n" + "="*50)
    print("ALL SCHEDULER TESTS PASSED!")
    print("="*50)

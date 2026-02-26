"""
Test scenarios for the scheduler - small datasets for validation
"""

from scheduler import (
    Classroom, Class, Teacher, Section, Period,
    generate_sections, build_scheduling_context, prioritize_sections,
    solve_recursive_full
)


def test_simple_valid():
    """
    Simple valid case: 2 teachers, 2 classrooms, 2 periods
    Should find a complete solution
    """
    print("\n" + "="*60)
    print("TEST: Simple Valid Case")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
        Classroom("Room-102", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=2, required_classroom_type="General"),
        Class("English", num_sections=2, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math", "English"}, max_sections=2, assigned_count=0),
        Teacher("Ms. Jones", subjects={"Math", "English"}, max_sections=2, assigned_count=0),
    ]
    
    periods = [Period("P1"), Period("P2")]
    
    # Run scheduler
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    print(f"Sections assigned: {sum(1 for s in ctx.all_sections if s.is_fully_assigned())}/{len(ctx.all_sections)}")
    return success and sum(1 for s in ctx.all_sections if s.is_fully_assigned()) == len(ctx.all_sections)


def test_single_teacher_multiple_sections():
    """
    Edge case: 1 teacher, 4 sections, 2 periods
    Teacher can only teach 2 sections max - should be IMPOSSIBLE
    """
    print("\n" + "="*60)
    print("TEST: Single Teacher - Impossible (teacher capacity)")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=4, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math"}, max_sections=2, assigned_count=0),  # Can only teach 2, but need 4
    ]
    
    periods = [Period("P1"), Period("P2")]
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    # The best partial solution should have 2 sections
    best_assigned = ctx.best_section_index
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Best partial solution: {best_assigned}/{len(ctx.all_sections)} sections")
    print(f"Expected: Partial solution (2 sections - teacher capacity)")
    return not success and best_assigned == 2


def test_single_room_multiple_subjects():
    """
    Edge case: 1 room, multiple subjects that all need General
    Should work if teacher capacity allows
    """
    print("\n" + "="*60)
    print("TEST: Single Room - Multiple Subjects")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=1, required_classroom_type="General"),
        Class("English", num_sections=1, required_classroom_type="General"),
        Class("History", num_sections=1, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math", "English", "History"}, max_sections=3, assigned_count=0),
    ]
    
    periods = [Period("P1"), Period("P2"), Period("P3")]
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Sections assigned: {assigned}/{len(ctx.all_sections)}")
    return success and assigned == len(ctx.all_sections)


def test_teacher_subject_mismatch():
    """
    Edge case: Teacher doesn't have required subject
    Should still work if other teachers can cover
    """
    print("\n" + "="*60)
    print("TEST: Teacher Subject Mismatch")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=1, required_classroom_type="General"),
        Class("English", num_sections=1, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math"}, max_sections=1, assigned_count=0),  # Only Math
        Teacher("Ms. Jones", subjects={"English"}, max_sections=1, assigned_count=0),  # Only English
    ]
    
    periods = [Period("P1"), Period("P2")]
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Sections assigned: {assigned}/{len(ctx.all_sections)}")
    return success and assigned == len(ctx.all_sections)


def test_classroom_type_mismatch():
    """
    Edge case: Need Science Lab for Biology but only General room available
    But we have both Science AND General rooms, so it should work!
    """
    print("\n" + "="*60)
    print("TEST: Classroom Type Mismatch")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
        Classroom("Lab-101", size=30, purposes={"Science"}),
    ]
    
    classes = [
        Class("Math", num_sections=1, required_classroom_type="General"),
        Class("Biology", num_sections=1, required_classroom_type="Science"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math", "Biology"}, max_sections=2, assigned_count=0),
    ]
    
    periods = [Period("P1"), Period("P2")]
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Sections assigned: {assigned}/{len(ctx.all_sections)}")
    # With both Room (General) and Lab (Science), this SHOULD work
    return success and assigned == 2


def test_exact_capacity():
    """
    Edge case: Teacher has exactly enough capacity for all sections
    Should work perfectly
    """
    print("\n" + "="*60)
    print("TEST: Exact Teacher Capacity")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=2, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math"}, max_sections=2, assigned_count=0),  # Exact match
    ]
    
    periods = [Period("P1"), Period("P2")]
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Sections assigned: {assigned}/{len(ctx.all_sections)}")
    return success and assigned == len(ctx.all_sections)


def test_no_teachers_for_subject():
    """
    Edge case: No teacher available for a subject
    Should fail completely
    """
    print("\n" + "="*60)
    print("TEST: No Teacher for Subject")
    print("="*60)
    
    classrooms = [
        Classroom("Room-101", size=30, purposes={"General"}),
    ]
    
    classes = [
        Class("Math", num_sections=1, required_classroom_type="General"),
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"English"}, max_sections=1, assigned_count=0),  # No Math!
    ]
    
    periods = [Period("P1")]
    
    try:
        sections = generate_sections(classes)
        ctx = build_scheduling_context(sections, teachers, classrooms, periods)
        print("ERROR: Should have raised exception")
        return False
    except ValueError as e:
        print(f"Correctly raised error: {e}")
        return True


def test_overloaded_periods():
    """
    Edge case: More sections than periods can hold
    Should produce partial solution
    """
    print("\n" + "="*60)
    print("TEST: Overloaded Periods (More sections than slots)")
    print("="*60)
    
    classrooms = [
        Classroom(f"Room-{i}", size=30, purposes={"General"}) 
        for i in range(10)  # 10 rooms
    ]
    
    classes = [
        Class("Math", num_sections=6, required_classroom_type="General"),  # 6 sections
    ]
    
    teachers = [
        Teacher("Mr. Smith", subjects={"Math"}, max_sections=6, assigned_count=0),
    ]
    
    periods = [Period(f"P{i}") for i in range(3)]  # Only 3 periods
    
    sections = generate_sections(classes)
    ctx = build_scheduling_context(sections, teachers, classrooms, periods)
    prioritize_sections(ctx)
    success = solve_recursive_full(ctx)
    
    # The best partial solution should have 3 sections (one per period)
    best_assigned = ctx.best_section_index
    print(f"Result: {'SUCCESS' if success else 'PARTIAL/FAILED'}")
    print(f"Best partial solution: {best_assigned}/{len(ctx.all_sections)} sections")
    print(f"Max possible: 3 (one per period)")
    # Should assign 3 (one per period), not 6
    return not success and best_assigned == 3


def run_all_tests():
    """Run all test cases"""
    results = []
    
    results.append(("Simple Valid", test_simple_valid()))
    results.append(("Single Teacher - Impossible", test_single_teacher_multiple_sections()))
    results.append(("Single Room - Multiple Subjects", test_single_room_multiple_subjects()))
    results.append(("Teacher Subject Mismatch", test_teacher_subject_mismatch()))
    results.append(("Classroom Type Mismatch", test_classroom_type_mismatch()))
    results.append(("Exact Capacity", test_exact_capacity()))
    results.append(("No Teacher for Subject", test_no_teachers_for_subject()))
    results.append(("Overloaded Periods", test_overloaded_periods()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    run_all_tests()

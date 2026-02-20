from scheduler import (
    Classroom, Class, Teacher, Period,
    run_scheduler, check
)

def main():
    # Single period to force same-period conflicts
    periods = [Period(period_id="P1")]

    # One room that fits all classes
    classrooms = [Classroom(name="R1", size=30, purposes={"r"})]

    # Classes: A, B, C (one section each)
    # Order matters for prioritization tie-breaking: A then B then C
    classes = [
        Class(name="A", num_sections=1, required_classroom_type="r"),
        Class(name="B", num_sections=1, required_classroom_type="r"),
        Class(name="C", num_sections=1, required_classroom_type="r"),
    ]

    # Teachers designed to force a single-level swap:
    # T1 can teach A and C (max 1)
    # T2 can teach B and C (max 1)
    # T3 can only teach A (max 1) — alternate for A
    teachers = [
        Teacher(name="T1", subjects={"A", "C"}, max_sections=1, assigned_count=0),
        Teacher(name="T2", subjects={"B", "C"}, max_sections=1, assigned_count=0),
        Teacher(name="T3", subjects={"A"},     max_sections=1, assigned_count=0),
    ]

    classroom_types = ["r"]

    ctx_sections = run_scheduler(classroom_types, classrooms, [], classes, teachers, periods)

    print("\nSchedule (period -> (section, room, teacher))")
    for p in periods:
        for sec_id, room, teacher in p.get_assigned_sections():
            print(f"{p.period_id}: {sec_id} | {room} | {teacher}")

    # Validate
    check(periods)

if __name__ == "__main__":
    main()
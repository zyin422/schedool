from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict


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
    assigned_teacher: Optional[Teacher] = None
    assigned_classroom: Optional[Classroom] = None
    
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


@dataclass
class SchedulingContext:
    # Immutable / read-only data for the solver
    all_sections: List[Section]
    periods: List[Period]
    teachers: List[Teacher]
    classrooms: List[Classroom]

    # Precomputed domains
    valid_teachers: Dict[str, List[Teacher]] = field(default_factory=dict)
    valid_rooms: Dict[str, List[Classroom]] = field(default_factory=dict)

    # Mutable state (scoreboard)
    teacher_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict)
    room_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict)
    teacher_load: Dict[str, int] = field(default_factory=dict)


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


def build_scheduling_context(sections, teachers, classrooms, periods) -> SchedulingContext:
    # 1. Use provided Sections (Phase 1: sections must be flattened before calling)
    ctx = SchedulingContext(
        all_sections=sections,
        periods=periods,
        teachers=teachers,
        classrooms=classrooms
    )

    # 2. Build Domains (precompute valid teachers/rooms per section)
    for section in sections:
        ctx.valid_teachers[section.section_id] = [
            t for t in teachers if section.class_name in t.subjects and t.max_sections > 0
        ]

        ctx.valid_rooms[section.section_id] = [
            r for r in classrooms if section.required_classroom_type in r.purposes
        ]

        # Fail fast if impossible
        if not ctx.valid_teachers[section.section_id]:
            raise ValueError(f"CRITICAL: Section {section.section_id} has NO qualified teachers.")
        if not ctx.valid_rooms[section.section_id]:
            raise ValueError(f"CRITICAL: Section {section.section_id} has NO compatible rooms.")

    # 3. Initialize state matrices (scoreboard)
    for t in teachers:
        ctx.teacher_schedule[t.name] = {p.period_id: None for p in periods}
        ctx.teacher_load[t.name] = 0

    for r in classrooms:
        ctx.room_schedule[r.name] = {p.period_id: None for p in periods}

    return ctx


def prioritize_sections(ctx: SchedulingContext):
    """
    Phase 2: sort ctx.all_sections in-place by difficulty:
      1) fewest qualified teachers (primary)
      2) fewest compatible rooms (secondary)
    """
    def difficulty(section: Section):
        num_teachers = len(ctx.valid_teachers.get(section.section_id, []))
        num_rooms = len(ctx.valid_rooms.get(section.section_id, []))
        return (num_teachers, num_rooms)

    ctx.all_sections.sort(key=difficulty)
    print("✅ Phase 2: Sections sorted by difficulty (most constrained first).")


def assign_sections_to_periods(sections, periods, classroom_types):
    # assign sections to periods (round-robin by classroom type priority)
    period_idx = 0
    for c_type in classroom_types:
        for section in sections:
            if section.required_classroom_type != c_type:
                continue
            periods[period_idx % len(periods)].assigned_sections.append(section)
            period_idx += 1


def assign_classrooms_to_sections(periods, classrooms, classroom_types, ctx: SchedulingContext):
    """
    Assign rooms using precomputed ctx.valid_rooms and update ctx.room_schedule
    so room availability is tracked in the SchedulingContext scoreboard.
    """
    for p in periods:
        used_room_names = set()
        for section in p.assigned_sections:
            # iterate only over rooms known to be compatible for this section
            for room in ctx.valid_rooms.get(section.section_id, []):
                # skip if this room already used in this period
                if room.name in used_room_names:
                    continue
                # respect scoreboard (should be None if free)
                if ctx.room_schedule.get(room.name, {}).get(p.period_id) is not None:
                    used_room_names.add(room.name)
                    continue
                # assign
                section.assigned_classroom = room
                ctx.room_schedule[room.name][p.period_id] = section
                used_room_names.add(room.name)
                break


def assign_teachers_to_sections(ctx: SchedulingContext):
    # assign teachers using precomputed domains and the scoreboard
    for p in ctx.periods:
        for section in p.assigned_sections:
            # skip if already assigned
            if section.assigned_teacher:
                # ensure scoreboard reflects this pre-assignment if necessary
                teacher = section.assigned_teacher
                if isinstance(teacher, Teacher):
                    ctx.teacher_schedule[teacher.name][p.period_id] = section
                    ctx.teacher_load[teacher.name] += 1
                continue

            # 1) Try to assign any qualified teacher who is free in this period and below max load
            for t in ctx.valid_teachers[section.section_id]:
                if ctx.teacher_schedule[t.name][p.period_id] is None and ctx.teacher_load[t.name] < t.max_sections:
                    section.assigned_teacher = t
                    ctx.teacher_schedule[t.name][p.period_id] = section
                    ctx.teacher_load[t.name] += 1
                    break

            if section.assigned_teacher:
                continue

            # 2) Swap logic (single-level): for each qualified teacher who is busy in this period,
            #    inspect their conflicting section and try to find an alternate who is free this period.
            for qt in ctx.valid_teachers[section.section_id]:
                # only consider teachers who are actually busy in this period
                conflicting_section = ctx.teacher_schedule[qt.name][p.period_id]
                if conflicting_section is None:
                    continue

                # look for an alternate for the conflicting_section
                for alt in ctx.valid_teachers[conflicting_section.section_id]:
                    if alt.name == qt.name:
                        continue
                    # alternate must be free in this period and below max load
                    if ctx.teacher_schedule[alt.name][p.period_id] is None and ctx.teacher_load[alt.name] < alt.max_sections:
                        # perform swap:
                        # assign alt -> conflicting_section
                        conflicting_section.assigned_teacher = alt
                        ctx.teacher_schedule[alt.name][p.period_id] = conflicting_section
                        ctx.teacher_load[alt.name] += 1

                        # free qt for this period (remove their assignment)
                        ctx.teacher_schedule[qt.name][p.period_id] = None
                        ctx.teacher_load[qt.name] -= 1

                        # assign qt -> blocked section
                        section.assigned_teacher = qt
                        ctx.teacher_schedule[qt.name][p.period_id] = section
                        ctx.teacher_load[qt.name] += 1

                        # stop after first successful single-level swap
                        break

                if section.assigned_teacher:
                    break

            if not section.assigned_teacher:
                # Could not assign or swap — leave unassigned and warn
                print(f"⚠️ Unassigned after swap attempts: {section.section_id} in period {p.period_id}")


def solve_recursive(ctx: SchedulingContext, section_index: int = 0) -> bool:
    """
    Phase 3: Recursive backtracking solver over ctx.all_sections (already prioritized).
    This assigns teachers only (rooms are assumed assigned and recorded in ctx.room_schedule).
    Returns True if a full assignment is found, False if unsolvable with current domains.
    """
    # BASE CASE: all sections processed
    if section_index >= len(ctx.all_sections):
        return True

    section = ctx.all_sections[section_index]
    # locate the period this section was assigned to
    period = next((p for p in ctx.periods if section in p.assigned_sections), None)
    if period is None:
        # section has no period assigned -> cannot proceed
        return False
    p_id = period.period_id

    # Try every valid teacher for this section (order from precomputed domain)
    for teacher in ctx.valid_teachers.get(section.section_id, []):
        # teacher must be free in this period and below max load
        if ctx.teacher_schedule[teacher.name][p_id] is None and ctx.teacher_load[teacher.name] < teacher.max_sections:
            # Choose
            section.assigned_teacher = teacher
            ctx.teacher_schedule[teacher.name][p_id] = section
            ctx.teacher_load[teacher.name] += 1

            # Recurse
            if solve_recursive(ctx, section_index + 1):
                return True

            # Backtrack
            section.assigned_teacher = None
            ctx.teacher_schedule[teacher.name][p_id] = None
            ctx.teacher_load[teacher.name] -= 1

    # No teacher led to a solution for this section -> fail
    return False


def solve_recursive_full(ctx: SchedulingContext, section_index: int = 0) -> bool:
    """
    Phase 3 (full): Recursive backtracking over Period x Room x Teacher choices.
    Places each section into a (period, room, teacher) triple or backtracks.
    """
    # BASE CASE: all sections placed
    if section_index >= len(ctx.all_sections):
        return True

    section = ctx.all_sections[section_index]

    # Try every period (time)
    for period in ctx.periods:
        p_id = period.period_id

        # Try every compatible room (space) for this section
        for room in ctx.valid_rooms.get(section.section_id, []):
            # room must be free in this period
            if ctx.room_schedule[room.name][p_id] is not None:
                continue

            # Try every qualified teacher (human resource)
            for teacher in ctx.valid_teachers.get(section.section_id, []):
                # teacher must be free in this period and below max load
                if ctx.teacher_schedule[teacher.name][p_id] is not None:
                    continue
                if ctx.teacher_load[teacher.name] >= teacher.max_sections:
                    continue

                # --- CHOOSE ---
                section.assigned_classroom = room
                section.assigned_teacher = teacher
                period.assigned_sections.append(section)

                ctx.room_schedule[room.name][p_id] = section
                ctx.teacher_schedule[teacher.name][p_id] = section
                ctx.teacher_load[teacher.name] += 1

                # --- RECURSE ---
                if solve_recursive_full(ctx, section_index + 1):
                    return True

                # --- BACKTRACK ---
                ctx.teacher_load[teacher.name] -= 1
                ctx.teacher_schedule[teacher.name][p_id] = None
                ctx.room_schedule[room.name][p_id] = None

                # remove section from period list and clear assignments
                try:
                    period.assigned_sections.remove(section)
                except ValueError:
                    pass
                section.assigned_teacher = None
                section.assigned_classroom = None

    # No valid placement found for this section
    return False


def run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods):
    # main scheduling algorithm - Phase 1 & 2 remain (flatten + context + prioritize)
    sections = generate_sections(classes)

    ctx = build_scheduling_context(sections, teachers, classrooms, periods)

    prioritize_sections(ctx)

    # Attempt full recursive search (Period x Room x Teacher)
    success = solve_recursive_full(ctx)

    if success:
        print("✨ SUCCESS: Fully valid schedule found by recursive solver.")
    else:
        print("❌ CRITICAL: No valid full assignment found by recursive solver!")
        print("⚠️ Falling back to greedy pipeline to produce a partial schedule for inspection.")

        # Reset any partial state produced by the failed recursive attempt
        for p in ctx.periods:
            p.assigned_sections.clear()
        for s in ctx.all_sections:
            s.assigned_teacher = None
            s.assigned_classroom = None

        # Reset scoreboard matrices
        for t in ctx.teachers:
            ctx.teacher_schedule[t.name] = {p.period_id: None for p in ctx.periods}
            ctx.teacher_load[t.name] = 0
        for r in ctx.classrooms:
            ctx.room_schedule[r.name] = {p.period_id: None for p in ctx.periods}

        # Run greedy fallback (periods -> rooms -> teachers with swaps)
        assign_sections_to_periods(ctx.all_sections, periods, classroom_types)
        assign_classrooms_to_sections(periods, classrooms, classroom_types, ctx)
        assign_teachers_to_sections(ctx)

    total = len(ctx.all_sections)
    fully_assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    unassigned_count = total - fully_assigned

    if success and unassigned_count == 0:
        # already printed success above
        pass
    elif not success and fully_assigned == total:
        print("✨ Greedy fallback produced a full assignment (unexpected).")
    elif unassigned_count == 0:
        print("✨ SUCCESS: All sections are fully assigned (rooms + teachers).")
    else:
        print("⚠️ PARTIAL: Some sections remain unassigned after fallback.")
        print(f"  ✓ Fully assigned: {fully_assigned}/{total}")
        print(f"  ✗ Unassigned: {unassigned_count}/{total}")

    # final sanity check (may raise)
    try:
        check(periods)
    except Exception as e:
        print(f"❌ Schedule validation failed: {e}")

    return ctx.all_sections


def check(periods):
    # validate schedule for conflicts
    for p in periods:
        used_section_ids = set()
        used_teacher_names = set()
        used_classroom_names = set()
        
        for s in p.assigned_sections:
            # Check for duplicate sections (by section_id string)
            if s.section_id in used_section_ids:
                raise Exception(
                    f"CONFLICT in {p.period_id}: Section '{s.section_id}' is scheduled twice in the same period. "
                    f"This section appears multiple times when it should only appear once."
                )
            used_section_ids.add(s.section_id)

            # Check for teacher conflicts using teacher.name for robustness
            t = s.assigned_teacher
            if t is not None:
                if t.name in used_teacher_names:
                    conflicting_sections = [sec.section_id for sec in p.assigned_sections
                                            if sec.assigned_teacher and sec.assigned_teacher.name == t.name]
                    raise Exception(
                        f"CONFLICT in {p.period_id}: Teacher '{t.name}' is assigned to multiple sections simultaneously. "
                        f"Conflicting sections: {', '.join(conflicting_sections)}. "
                        f"A teacher cannot teach multiple classes at the same time."
                    )
                used_teacher_names.add(t.name)
            
            # Check for classroom conflicts using classroom.name for robustness
            c = s.assigned_classroom
            if c is not None:
                if c.name in used_classroom_names:
                    conflicting_sections = [sec.section_id for sec in p.assigned_sections
                                            if sec.assigned_classroom and sec.assigned_classroom.name == c.name]
                    raise Exception(
                        f"CONFLICT in {p.period_id}: Classroom '{c.name}' is assigned to multiple sections simultaneously. "
                        f"Conflicting sections: {', '.join(conflicting_sections)}. "
                        f"A classroom cannot host multiple classes at the same time."
                    )
                used_classroom_names.add(c.name)
    
    print("✅ Check passed - No scheduling conflicts detected")
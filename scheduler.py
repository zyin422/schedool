from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict
import time


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
    teacher_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict) # [teacher_name][period_id] = assigned Section or None
    room_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict) # [room_name][period_id] = assigned Section or None
    teacher_load: Dict[str, int] = field(default_factory=dict)

    # --- instrumentation for recursion/search ---
    search_nodes: int = 0                # number of search nodes visited
    search_start_time: float = 0.0      # time.time() when search started
    search_last_report: int = 0         # last node count we reported at
    search_max_nodes: int = 10_000_000   # bail-out node budget (tune as needed)
    search_max_seconds: int = 5        # bail-out time budget (seconds)

    # --- tracking best partial solution ---
    best_section_index: int = -1         # deepest section index reached (-1 = not initialized)
    best_teacher_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict)
    best_room_schedule: Dict[str, Dict[str, Optional[Section]]] = field(default_factory=dict)
    best_teacher_load: Dict[str, int] = field(default_factory=dict)
    best_period_assignments: Dict[str, List[Section]] = field(default_factory=dict)


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

    # instrumentation start time
    ctx.search_start_time = time.time()
    ctx.search_nodes = 0
    ctx.search_last_report = 0

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


def forward_check(ctx: SchedulingContext, section_index: int, period_id: str, room, teacher) -> bool:
    """
    Forward Checking: After making an assignment (period, room, teacher), 
    quickly peek ahead at unassigned sections to see if they still have 
    viable options remaining.
    
    Returns True if all remaining sections still have at least one valid option.
    Returns False if any section's domain is now empty (causing immediate backtrack).
    
    This is a more sophisticated check that considers:
    1. For each unassigned section, counts available rooms across ALL periods
    2. For each unassigned section, counts available teachers across ALL periods  
    3. Special handling for single-teacher subjects: ensures enough capacity remains
    """
    # For each unassigned section, check if it still has viable options
    for i in range(section_index + 1, len(ctx.all_sections)):
        future_section = ctx.all_sections[i]
        
        # Count available (period, room) pairs for this section
        available_room_periods = 0
        for p in ctx.periods:
            p_id = p.period_id
            for room_opt in ctx.valid_rooms.get(future_section.section_id, []):
                if ctx.room_schedule[room_opt.name][p_id] is None:
                    available_room_periods += 1
        
        if available_room_periods == 0:
            # No room available for this section in any period
            return False
        
        # Count available teachers for this section across all periods
        # A teacher is available if they're free in at least one period AND have capacity
        available_teachers = []
        for teacher_opt in ctx.valid_teachers.get(future_section.section_id, []):
            # Check if teacher has any free period
            for p in ctx.periods:
                p_id = p.period_id
                if ctx.teacher_schedule[teacher_opt.name][p_id] is None and ctx.teacher_load[teacher_opt.name] < teacher_opt.max_sections:
                    available_teachers.append(teacher_opt)
                    break  # Teacher has at least one slot
        
        if len(available_teachers) == 0:
            # No teacher available for this section in any period
            return False
        
        # SPECIAL CHECK: If only ONE teacher is available for this section,
        # verify they have enough remaining capacity for ALL remaining sections 
        # that ONLY this teacher can teach
        if len(available_teachers) == 1:
            sole_teacher = available_teachers[0]
            # Count how many remaining sections (from this point forward) 
            # are ONLY teachable by this teacher
            sole_teacher_sections = 0
            for j in range(i, len(ctx.all_sections)):
                other_section = ctx.all_sections[j]
                if other_section.section_id == future_section.section_id:
                    continue
                # Check if this other section also only has this one teacher
                other_teachers = ctx.valid_teachers.get(other_section.section_id, [])
                if len(other_teachers) == 1 and other_teachers[0].name == sole_teacher.name:
                    sole_teacher_sections += 1
            
            # Calculate remaining capacity for this teacher
            remaining_capacity = sole_teacher.max_sections - ctx.teacher_load[sole_teacher.name]
            # We need capacity for: current section + all other sole-teacher sections
            needed_capacity = 1 + sole_teacher_sections
            if remaining_capacity < needed_capacity:
                # Not enough capacity - will cause dead end later
                return False
    
    return True


def solve_recursive_full(ctx: SchedulingContext, section_index: int = 0) -> bool:
    """
    Phase 3 (full): Recursive backtracking over Period x Room x Teacher choices.
    Places each section into a (period, room, teacher) triple or skips it.
    Instrumented to report progress and support early bail-out.
    
    Key improvement: When a section cannot be placed, SKIP it and continue
    to the next section rather than backtracking endlessly. This allows
    the solver to find partial solutions even when constraints are impossible.
    
    Tracks the deepest partial solution for use when no full solution is found.
    """
    # Helper to count how many sections are currently assigned
    def count_assigned():
        count = 0
        for s in ctx.all_sections:
            if s.assigned_teacher and s.assigned_classroom:
                count += 1
        return count

    # Initialize best solution tracking on first call
    if ctx.best_section_index == -1 and section_index == 0:
        # Initialize best_teacher_schedule with proper structure
        for t in ctx.teachers:
            ctx.best_teacher_schedule[t.name] = {p.period_id: None for p in ctx.periods}
        ctx.best_teacher_load = {t.name: 0 for t in ctx.teachers}
        for r in ctx.classrooms:
            ctx.best_room_schedule[r.name] = {p.period_id: None for p in ctx.periods}
        for p in ctx.periods:
            ctx.best_period_assignments[p.period_id] = []

    # BASE CASE: all sections processed
    if section_index >= len(ctx.all_sections):
        # Check if ALL sections are actually assigned (not just reached end)
        current_assigned = count_assigned()
        if current_assigned == len(ctx.all_sections):
            # This is a truly full solution - save it
            ctx.best_section_index = len(ctx.all_sections)
            for t in ctx.teachers:
                ctx.best_teacher_schedule[t.name] = dict(ctx.teacher_schedule[t.name])
            ctx.best_teacher_load = dict(ctx.teacher_load)
            for r in ctx.classrooms:
                ctx.best_room_schedule[r.name] = dict(ctx.room_schedule[r.name])
            for p in ctx.periods:
                ctx.best_period_assignments[p.period_id] = list(p.assigned_sections)
            return True
        else:
            # Reached end but some sections were skipped - not a full solution
            # Save as best partial if better
            if current_assigned > ctx.best_section_index:
                ctx.best_section_index = current_assigned
                for t in ctx.teachers:
                    ctx.best_teacher_schedule[t.name] = dict(ctx.teacher_schedule[t.name])
                ctx.best_teacher_load = dict(ctx.teacher_load)
                for r in ctx.classrooms:
                    ctx.best_room_schedule[r.name] = dict(ctx.room_schedule[r.name])
                for p in ctx.periods:
                    ctx.best_period_assignments[p.period_id] = list(p.assigned_sections)
            return False

    # instrumentation: count node
    ctx.search_nodes += 1

    # periodic progress report
    if ctx.search_nodes - ctx.search_last_report >= 10000:
        elapsed = time.time() - ctx.search_start_time
        current_assigned = count_assigned()
        print(f"[search] nodes={ctx.search_nodes:,} section_index={section_index} assigned={current_assigned} elapsed={elapsed:.1f}s")
        ctx.search_last_report = ctx.search_nodes

    # bail-out conditions
    if ctx.search_nodes >= ctx.search_max_nodes:
        print(f"[search] ABORT: reached node budget ({ctx.search_nodes} >= {ctx.search_max_nodes})")
        return False
    if (time.time() - ctx.search_start_time) >= ctx.search_max_seconds:
        print(f"[search] ABORT: reached time budget ({ctx.search_max_seconds}s)")
        return False

    section = ctx.all_sections[section_index]

    # ensure this section is not already sitting in any period (prevent duplicates)
    for p_clean in ctx.periods:
        if section in p_clean.assigned_sections:
            p_clean.assigned_sections.remove(section)
    section.assigned_teacher = None
    section.assigned_classroom = None

    # Try every period (time)
    section_placed = False
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

                # place the section in this period (ensure no duplicate)
                if section not in period.assigned_sections:
                    period.assigned_sections.append(section)

                ctx.room_schedule[room.name][p_id] = section
                ctx.teacher_schedule[teacher.name][p_id] = section
                ctx.teacher_load[teacher.name] += 1

                section_placed = True

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
                section_placed = False

    # KEY FIX: After trying ALL options for this section, decide what to do
    # Count how many sections are currently assigned
    current_assigned = count_assigned()
    
    # Save as best if we have more assigned sections than previous best
    # This is better than just tracking depth - we track actual progress
    if current_assigned > ctx.best_section_index:
        ctx.best_section_index = current_assigned
        for t in ctx.teachers:
            ctx.best_teacher_schedule[t.name] = dict(ctx.teacher_schedule[t.name])
        ctx.best_teacher_load = dict(ctx.teacher_load)
        for r in ctx.classrooms:
            ctx.best_room_schedule[r.name] = dict(ctx.room_schedule[r.name])
        for p in ctx.periods:
            ctx.best_period_assignments[p.period_id] = list(p.assigned_sections)
        print(f"[search] NEW BEST: {current_assigned} sections assigned at section_index={section_index}")

    # If we couldn't place this section, SKIP it and continue to next
    # This is the key difference - we don't get stuck in permutations
    if not section_placed:
        # Just continue to next section without this one
        return solve_recursive_full(ctx, section_index + 1)

    return False


def run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods):
    # main scheduling algorithm - Phase 1 & 2 remain (flatten + context + prioritize)
    sections = generate_sections(classes)

    ctx = build_scheduling_context(sections, teachers, classrooms, periods)

    prioritize_sections(ctx)

    # === DIAGNOSTIC: Analyze section_index=18 before search begins ===
    # Uncomment the following line to run diagnostics:
    # diagnose_section(ctx, 17)
    
    # Attempt full recursive search (Period x Room x Teacher)
    success = solve_recursive_full(ctx)

    if success:
        print("SUCCESS: Fully valid schedule found by recursive solver.")
    else:
        print("CRITICAL: No valid full assignment found by recursive solver!")
        print(f"⚠️ Restoring deepest partial solution from recursion: {ctx.best_section_index}/{len(ctx.all_sections)} sections placed.")

        # Restore the best partial solution from recursion
        for t in ctx.teachers:
            ctx.teacher_schedule[t.name] = dict(ctx.best_teacher_schedule[t.name])
        ctx.teacher_load = dict(ctx.best_teacher_load)
        for r in ctx.classrooms:
            ctx.room_schedule[r.name] = dict(ctx.best_room_schedule[r.name])
        for p in ctx.periods:
            p.assigned_sections = list(ctx.best_period_assignments[p.period_id])

        # Restore section assignments based on room schedule
        for r in ctx.classrooms:
            for p_id, section in ctx.room_schedule[r.name].items():
                if section is not None:
                    section.assigned_classroom = r
                    # Find the period
                    for p in ctx.periods:
                        if p.period_id == p_id:
                            if section not in p.assigned_sections:
                                p.assigned_sections.append(section)
                            break

        # Restore teacher assignments
        for t in ctx.teachers:
            for p_id, section in ctx.teacher_schedule[t.name].items():
                if section is not None:
                    section.assigned_teacher = t

        # NOTE: Greedy fallback is disabled - using deepest recursive solution instead
        # # Reset any partial state produced by the failed recursive attempt
        # for p in ctx.periods:
        #     p.assigned_sections.clear()
        # for s in ctx.all_sections:
        #     s.assigned_teacher = None
        #     s.assigned_classroom = None

        # # Reset scoreboard matrices
        # for t in ctx.teachers:
        #     ctx.teacher_schedule[t.name] = {p.period_id: None for p in ctx.periods}
        #     ctx.teacher_load[t.name] = 0
        # for r in ctx.classrooms:
        #     ctx.room_schedule[r.name] = {p.period_id: None for p in ctx.periods}

        # # Run greedy fallback (periods -> rooms -> teachers with swaps)
        # assign_sections_to_periods(ctx.all_sections, periods, classroom_types)
        # assign_classrooms_to_sections(periods, classrooms, classroom_types, ctx)
        # assign_teachers_to_sections(ctx)

    total = len(ctx.all_sections)
    fully_assigned = sum(1 for s in ctx.all_sections if s.is_fully_assigned())
    unassigned_count = total - fully_assigned

    if success and unassigned_count == 0:
        # already printed success above
        pass
    elif not success and fully_assigned == total:
        print("Deepest recursive solution produced a full assignment (unexpected).")
    elif unassigned_count == 0:
        print("SUCCESS: All sections are fully assigned (rooms + teachers).")
    else:
        print("⚠️ PARTIAL: Using deepest solution from recursive solver.")
        print(f"  ✓ Fully assigned: {fully_assigned}/{total}")
        print(f"  ✗ Unassigned: {unassigned_count}/{total}")

    # final sanity check (may raise)
    try:
        check(periods)
    except Exception as e:
        print(f"!! Schedule validation failed: {e}")

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


def diagnose_section(ctx: SchedulingContext, section_index: int):
    """
    Diagnostic function to analyze a specific section and the dataset.
    Call this right before the search begins to understand why the solver gets stuck.
    
    This will help identify:
    1. If the dataset is mathematically impossible (e.g., more Lab sections than Lab slots)
    2. If section_index is particularly constrained
    3. Global resource availability analysis
    """
    print("\n" + "="*70)
    print(f"DIAGNOSTIC ANALYSIS for section_index={section_index}")
    print("="*70)
    
    # --- 1. Analyze the specific problematic section ---
    if section_index < len(ctx.all_sections):
        section = ctx.all_sections[section_index]
        print(f"\nPROBLEMATIC SECTION: {section.section_id}")
        print(f"   Class: {section.class_name}")
        print(f"   Required room type: {section.required_classroom_type}")
        
        # Count valid teachers and rooms
        valid_teachers = ctx.valid_teachers.get(section.section_id, [])
        valid_rooms = ctx.valid_rooms.get(section.section_id, [])
        
        print(f"   Valid teachers: {len(valid_teachers)} - {[t.name for t in valid_teachers]}")
        print(f"   Valid rooms: {len(valid_rooms)} - {[r.name for r in valid_rooms]}")
        
        # Calculate available (period, room, teacher) triples
        available_triples = 0
        for period in ctx.periods:
            p_id = period.period_id
            for room in valid_rooms:
                # Check if room is free in this period
                if ctx.room_schedule[room.name][p_id] is not None:
                    continue
                for teacher in valid_teachers:
                    # Check if teacher is free in this period and has capacity
                    if ctx.teacher_schedule[teacher.name][p_id] is not None:
                        continue
                    if ctx.teacher_load[teacher.name] >= teacher.max_sections:
                        continue
                    available_triples += 1
        print(f"   Available (Period, Room, Teacher) triples: {available_triples}")
    else:
        print(f"\n⚠️ section_index={section_index} is out of range (total sections: {len(ctx.all_sections)})")
    
    # --- 2. Global resource availability ---
    print("\nGLOBAL RESOURCE ANALYSIS:")
    
    # Count sections by classroom type
    sections_by_type = {}
    for section in ctx.all_sections:
        rtype = section.required_classroom_type
        sections_by_type[rtype] = sections_by_type.get(rtype, 0) + 1
    
    print("\n   Sections by required classroom type:")
    for rtype, count in sorted(sections_by_type.items()):
        # Count compatible rooms
        compatible_rooms = [r for r in ctx.classrooms if rtype in r.purposes]
        # Total slots = compatible_rooms * periods
        total_slots = len(compatible_rooms) * len(ctx.periods)
        print(f"      {rtype}: {count} sections, {len(compatible_rooms)} rooms, {total_slots} total slots")
        if count > total_slots:
            print(f"         ⚠️ IMPOSSIBLE: {count} sections > {total_slots} slots!")
    
    # Count teacher capacity by subject
    print("\n   Teacher capacity by subject:")
    teacher_capacity = {}
    for teacher in ctx.teachers:
        for subject in teacher.subjects:
            teacher_capacity[subject] = teacher_capacity.get(subject, 0) + teacher.max_sections
    
    # Count sections needing each subject
    sections_by_subject = {}
    for section in ctx.all_sections:
        subject = section.class_name
        sections_by_subject[subject] = sections_by_subject.get(subject, 0) + 1
    
    for subject, section_count in sorted(sections_by_subject.items()):
        capacity = teacher_capacity.get(subject, 0)
        print(f"      {subject}: {section_count} sections, {capacity} teacher slots")
        if section_count > capacity:
            print(f"         ⚠️ IMPOSSIBLE: {section_count} sections > {capacity} teacher slots!")
    
    # --- 3. Domain size summary for all sections (after prioritization) ---
    print("\nSECTION DOMAIN SIZES (after prioritization):")
    for i, section in enumerate(ctx.all_sections):
        valid_teachers = ctx.valid_teachers.get(section.section_id, [])
        valid_rooms = ctx.valid_rooms.get(section.section_id, [])
        
        # Calculate theoretical max options (periods * rooms * teachers)
        max_options = len(valid_rooms) * len(valid_teachers) * len(ctx.periods)
        
        marker = " <-- PROBLEM" if i == section_index else ""
        print(f"   [{i:2d}] {section.section_id}: {len(valid_teachers)} teachers, {len(valid_rooms)} rooms, {max_options} theoretical options{marker}")
    
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")
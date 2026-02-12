import scenarios
from scheduler import run_scheduler, check
from visualizer import visualize_schedule


def test_scenario(name, scenario_func):
    print(f"\n{'='*60}")
    print(f"TESTING: {name}")
    print(f"{'='*60}")
    
    # load scenario data
    classroom_types, classrooms, class_list, classes, teachers, periods = scenario_func()
    
    print(f"Sections: {sum(c.num_sections for c in classes)}, Classrooms: {len(classrooms)}, Teachers: {len(teachers)}, Periods: {len(periods)}")
    
    # run scheduler
    sections = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods)
    
    # visualize results
    visualize_schedule(periods, sections, teachers)
    
    # validate
    try:
        check(periods)
    except Exception as e:
        print(f"SCHEDULING CONFLICT: {e}")


test_scenario("Balanced Medium School", scenarios.balanced_school_medium)
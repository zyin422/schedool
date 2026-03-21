import os
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, flash
from scheduler import (
    Classroom, Class, Teacher, Section, Period,
    run_scheduler
)
from visualizer import visualize_schedule

app = Flask(__name__)
app.secret_key = 'schedool-secret-key-change-in-production'

# Store last schedule result in memory
last_schedule_result = {
    'output': '',
    'success': False
}


def parse_csv_file(file_content):
    """Parse CSV content and return list of dictionaries"""
    reader = csv.DictReader(io.StringIO(file_content))
    data = []
    for row in reader:
        # Clean up the row - strip whitespace from keys and values
        cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
        data.append(cleaned_row)
    return data


def load_data_from_csv(classrooms_csv, classes_csv, teachers_csv, periods_csv):
    """Load scheduler data from CSV file contents"""
    # Parse classrooms
    classrooms = []
    classroom_data = parse_csv_file(classrooms_csv)
    for row in classroom_data:
        purposes = set(p.strip() for p in row['purposes'].split(','))
        classrooms.append(Classroom(
            name=row['name'],
            size=int(row['size']),
            purposes=purposes
        ))
    
    # Parse classes
    classes = []
    class_data = parse_csv_file(classes_csv)
    for row in class_data:
        classes.append(Class(
            name=row['name'],
            num_sections=int(row['num_sections']),
            required_classroom_type=row['required_classroom_type']
        ))
    
    # Parse teachers
    teachers = []
    teacher_data = parse_csv_file(teachers_csv)
    for row in teacher_data:
        subjects = set(s.strip() for s in row['subjects'].split(','))
        teachers.append(Teacher(
            name=row['name'],
            subjects=subjects,
            max_sections=int(row['max_sections']),
            assigned_count=0
        ))
    
    # Parse periods
    periods = []
    period_data = parse_csv_file(periods_csv)
    for row in period_data:
        periods.append(Period(period_id=row['period_id']))
    
    # classroom_types is derived from unique purposes
    classroom_types = set()
    for c in classrooms:
        classroom_types.update(c.purposes)
    
    # class_list is just a list of class names
    class_list = [c.name for c in classes]
    
    return classroom_types, classrooms, class_list, classes, teachers, periods


def run_scheduler_and_capture_output(classroom_types, classrooms, class_list, classes, teachers, periods):
    """Run the scheduler and capture the output"""
    import sys
    from io import StringIO
    
    # Capture stdout
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Run scheduler - this modifies periods in place and returns sections
        sections = run_scheduler(classroom_types, classrooms, class_list, classes, teachers, periods)
        
        # Visualize results - this also uses periods (which have assigned_sections now)
        visualize_schedule(periods, sections, teachers)
        
    finally:
        sys.stdout = old_stdout
    
    output = captured_output.getvalue()
    
    # Determine success
    fully_assigned = sum(1 for s in sections if s.is_fully_assigned())
    success = fully_assigned == len(sections)
    
    return output, success


@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')


@app.route('/run', methods=['POST'])
def run_scheduler_web():
    """Run the scheduler with uploaded CSV files"""
    global last_schedule_result
    
    # Check if files were uploaded
    if 'classrooms' not in request.files or 'classes' not in request.files:
        flash('Please upload both classrooms and classes CSV files', 'error')
        return redirect(url_for('index'))
    
    classrooms_file = request.files['classrooms']
    classes_file = request.files['classes']
    teachers_file = request.files.get('teachers')
    periods_file = request.files.get('periods')
    
    # Use default data if not provided
    default_teachers = """name,subjects,max_sections
Teacher-Math,Math,5
Teacher-English,English,5
Teacher-Science,Science,5
Teacher-Art,Art,5"""
    
    default_periods = """period_id
P1
P2
P3
P4
P5"""
    
    try:
        # Load data
        classroom_types, classrooms, class_list, classes, teachers, periods = load_data_from_csv(
            classrooms_file.read().decode('utf-8'),
            classes_file.read().decode('utf-8'),
            teachers_file.read().decode('utf-8') if teachers_file and teachers_file.filename else default_teachers,
            periods_file.read().decode('utf-8') if periods_file and periods_file.filename else default_periods
        )
        
        # Run scheduler and capture output
        output, success = run_scheduler_and_capture_output(
            classroom_types, classrooms, class_list, classes, teachers, periods
        )
        
        # Store result
        last_schedule_result['output'] = output
        last_schedule_result['success'] = success
        
        return redirect(url_for('results'))
        
    except Exception as e:
        flash(f'Error running scheduler: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/results')
def results():
    """Display the scheduler results"""
    return render_template('results.html', 
                          output=last_schedule_result['output'],
                          success=last_schedule_result['success'])


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)

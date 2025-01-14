import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# Instrument Flask with OpenTelemetry
FlaskInstrumentor().instrument_app(app)

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
console_exporter = ConsoleSpanExporter()
span_processor = BatchSpanProcessor(console_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Create the tracer instance
tracer = trace.get_tracer(__name__)

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)


# Routes
@app.route('/')
def index():
    with tracer.start_as_current_span("render_index_page") as span:
        span.set_attribute("route", "index")
        span.set_attribute("request_method", request.method)
        span.set_attribute("user_ip", request.remote_addr)
        return render_template('index.html')


@app.route('/catalog')
def course_catalog():
    with tracer.start_as_current_span("render_course_catalog") as span:
        span.set_attribute("route", "course_catalog")
        span.set_attribute("request_method", request.method)
        span.set_attribute("user_ip", request.remote_addr)

        courses = load_courses()
        span.set_attribute("course_count", len(courses))  # Metadata about courses
        return render_template('course_catalog.html', courses=courses)


@app.route("/add_course", methods=["GET", "POST"])
def add_course():
    with tracer.start_as_current_span("add_new_course") as span:
        span.set_attribute("route", "add_course")
        span.set_attribute("request_method", request.method)
        span.set_attribute("user_ip", request.remote_addr)

        if request.method == "POST":
            # Extract form data
            course = {
                "code": request.form.get("code"),
                "name": request.form.get("name"),
                "instructor": request.form.get("instructor"),
                "semester": request.form.get("semester"),
                "schedule": request.form.get("schedule"),
                "classroom": request.form.get("classroom"),
                "prerequisites": request.form.get("prerequisites"),
                "grading": request.form.get("grading"),
                "description": request.form.get("description"),
            }

            # Validate mandatory fields
            if all(course.values()):  # Checks all fields are filled
                courses = load_courses()  # Load courses from JSON file

                # Check if course code already exists
                if any(existing_course["code"] == course["code"] for existing_course in courses):
                    flash("A course with this code already exists!", "danger")
                    span.set_attribute("course_code_exists", True)
                else:
                    # Add the new course to the list and save
                    courses.append(course)
                    save_courses(courses)
                    flash("Course added successfully!", "success")
                    span.set_attribute("course_added", True)
                    return redirect(url_for("course_catalog"))
            else:
                flash("All fields are required!", "danger")
                span.set_attribute("all_fields_required", True)

        return render_template("add_course.html")


@app.route('/course/<code>')
def course_details(code):
    with tracer.start_as_current_span("view_course_details") as span:
        span.set_attribute("route", "course_details")
        span.set_attribute("request_method", request.method)
        span.set_attribute("user_ip", request.remote_addr)
        span.set_attribute("course_code", code)

        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)

        if not course:
            flash(f"No course found with code '{code}'.", "error")
            span.set_attribute("course_found", False)
            return redirect(url_for('course_catalog'))
        
        span.set_attribute("course_found", True)
        return render_template('course_details.html', course=course)

if __name__ == '__main__':
    app.run(debug=True)
    

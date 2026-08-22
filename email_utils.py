from flask import render_template


def generate_assignment_email(assignment, class_obj, student):
    """Generates email content for a student. Returns (subject, body)."""
    link = assignment.resource_url(external=True)
    due = assignment.due_date.strftime("%A, %B %d at %I:%M %p") if assignment.due_date else "No due date"

    context = f" ({class_obj.name})" if class_obj else ""
    subject = f"New reading assigned: {assignment.title or assignment.page_id}{context}"
    body = render_template(
        "email/assignment_notice.txt",
        student=student, assignment=assignment, class_obj=class_obj, link=link, due=due,
    )
    return subject, body

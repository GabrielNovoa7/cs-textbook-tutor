"""Saved lesson activities with deterministic grading or explicit self-review."""

import json

from fastapi import HTTPException

from backend.database import get_connection, get_section_context, get_section_progress


def ensure_activity(connection, row, context):
    if row["activity_json"]:
        return json.loads(row["activity_json"])
    payload = json.loads(row["response_json"]) if row["response_json"] else {}
    if "activity" in json.loads(payload.get("output_text", "{}")):
        return None  # Creation explicitly determined no application task is needed.
    # Legacy quizzes remain usable without another generation request.
    question = json.loads(row["questions_json"])[0]
    activity = {
        "activity_type": "explain", "title": "Teach it back",
        "prompt": f"Explain the idea behind this question in your own words: {question['prompt']}\nInclude one example from your section reading.",
        "items": [], "correct_order": [], "accepted_answers": [],
        "starter_code": "", "language": "plaintext",
        "checklist": ["I explained the concept in my own words.",
                      "I included an example supported by this section.",
                      "I checked my explanation against the textbook."],
        "source_type": "generated", "evidence_page": question["source"]["source_page"],
    }
    connection.execute("UPDATE concept_checks SET activity_json=? WHERE section_id=?",
                       (json.dumps(activity), context["section_id"]))
    return activity


def load_activity(section_id):
    context = get_section_context(section_id)
    if not context:
        raise HTTPException(404, "Section was not found.")
    if not get_section_progress(section_id)["concept_check_completed"]:
        raise HTTPException(409, "Pass the section questions to open the activity.")
    connection = get_connection()
    try:
        row = connection.execute("SELECT * FROM concept_checks WHERE section_id=? AND status='ready'", (section_id,)).fetchone()
        if not row:
            raise HTTPException(409, "Create this section's questions first.")
        activity = ensure_activity(connection, row, context)
        if activity is None:
            connection.execute("UPDATE section_progress SET activity_completed=1, mastery_completed=1, completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP) WHERE section_id=?", (section_id,))
        saved = connection.execute("SELECT * FROM activity_submissions WHERE section_id=?", (section_id,)).fetchone()
        connection.commit()
        public = {key: activity.get(key) for key in
                  ("activity_type", "title", "prompt", "items", "starter_code", "language", "checklist", "source_type", "evidence_page")} if activity else None
        progress = get_section_progress(section_id)
        return {"activity": public, "submission": json.loads(saved["response_json"]) if saved else None,
                "completed": bool(progress["activity_completed"]) or activity is None,
                "progress": progress}
    finally:
        connection.close()


def save_activity(section_id, response, order, reviewed, complete):
    public = load_activity(section_id)
    if not public["activity"]:
        return public
    connection = get_connection()
    try:
        row = connection.execute("SELECT activity_json FROM concept_checks WHERE section_id=?", (section_id,)).fetchone()
        activity = json.loads(row["activity_json"])
        passed = False
        feedback = "Draft saved."
        if complete:
            kind = activity["activity_type"]
            if kind == "ordering":
                if sorted(order) != list(range(len(activity["items"]))):
                    raise HTTPException(422, "Place every item exactly once.")
                passed = order == activity["correct_order"]
                feedback = "Correct sequence." if passed else "Review the sequence in your textbook and try again."
            elif kind == "predict_output":
                passed = response.strip().replace("\r\n", "\n") in [answer.strip().replace("\r\n", "\n") for answer in activity["accepted_answers"]]
                feedback = "Correct output." if passed else "Trace each step again and check the textbook example."
            else:
                if len(response.strip()) < 20 or reviewed != list(range(len(activity["checklist"]))):
                    raise HTTPException(422, "Write your solution and complete every self-review item.")
                passed = True
                feedback = "Completed through self-review. This is not an automatically graded solution."
        submission = {"response": response, "order": order, "reviewed": reviewed, "feedback": feedback}
        connection.execute("""INSERT INTO activity_submissions(section_id,response_json,completed) VALUES (?,?,?)
            ON CONFLICT(section_id) DO UPDATE SET response_json=excluded.response_json,
            completed=MAX(activity_submissions.completed,excluded.completed), updated_at=CURRENT_TIMESTAMP""",
                           (section_id, json.dumps(submission), int(passed)))
        if passed:
            connection.execute("""UPDATE section_progress SET activity_completed=1, mastery_completed=1,
                updated_at=CURRENT_TIMESTAMP, completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP) WHERE section_id=?""", (section_id,))
        connection.commit()
        return {"completed": passed or public["completed"], "feedback": feedback,
                "progress": get_section_progress(section_id)}
    finally:
        connection.close()

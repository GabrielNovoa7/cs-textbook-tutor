"""Persistent study tools. Reviews reuse cached questions; no generation calls."""
import json
import math
from contextlib import closing
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StrictInt
from backend.database import get_connection, get_section_context, get_learning_path

router = APIRouter()

def init_learning_tools():
    with closing(get_connection()) as c, c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS study_notes (
          section_id INTEGER PRIMARY KEY REFERENCES sections(id) ON DELETE CASCADE,
          note TEXT NOT NULL DEFAULT '', bookmarks_json TEXT NOT NULL DEFAULT '[]',
          visited_at TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chapter_reviews (
          id INTEGER PRIMARY KEY, chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
          score INTEGER, total INTEGER, passed INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chapter_assignments (
          chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id) ON DELETE CASCADE,
          response TEXT NOT NULL, completed INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        ''')

def section_exists(sid):
    if not get_section_context(sid):
        raise HTTPException(404, 'Section was not found.')

class Notes(BaseModel):
    note: str = Field(default='', max_length=20000)
    bookmarks: list[StrictInt] = Field(default_factory=list, max_length=100)

@router.post('/sections/{sid}/visit')
def visit(sid: int):
    section_exists(sid)
    with closing(get_connection()) as c, c:
        c.execute('INSERT INTO study_notes(section_id,visited_at) VALUES (?,?) ON CONFLICT(section_id) DO UPDATE SET visited_at=excluded.visited_at', (sid,datetime.now(timezone.utc).isoformat()))
    return {'saved': True}

@router.get('/sections/{sid}/notes')
def notes(sid: int):
    section_exists(sid)
    with closing(get_connection()) as c:
        row = c.execute('SELECT * FROM study_notes WHERE section_id=?', (sid,)).fetchone()
    return {'note': row['note'] if row else '', 'bookmarks': json.loads(row['bookmarks_json']) if row else []}

@router.put('/sections/{sid}/notes')
def save_notes(sid: int, body: Notes):
    section_exists(sid)
    with closing(get_connection()) as c, c:
        maximum = c.execute('SELECT t.page_count FROM textbooks t JOIN chapters ch ON ch.textbook_id=t.id JOIN sections s ON s.chapter_id=ch.id WHERE s.id=?', (sid,)).fetchone()[0]
        if any(not 1 <= p <= maximum for p in body.bookmarks):
            raise HTTPException(422, 'Bookmark page is outside the PDF.')
        c.execute('INSERT INTO study_notes(section_id,note,bookmarks_json) VALUES (?,?,?) ON CONFLICT(section_id) DO UPDATE SET note=excluded.note,bookmarks_json=excluded.bookmarks_json,updated_at=CURRENT_TIMESTAMP', (sid,body.note,json.dumps(sorted(set(body.bookmarks)))))
    return notes(sid)

@router.get('/study-dashboard')
def dashboard():
    with closing(get_connection()) as c:
        books = [dict(row) for row in c.execute('SELECT id,filename FROM textbooks ORDER BY uploaded_at DESC')]
        for book in books:
            book['chapter_reviews'] = c.execute('SELECT count(DISTINCT r.chapter_id) FROM chapter_reviews r JOIN chapters ch ON ch.id=r.chapter_id WHERE ch.textbook_id=? AND r.passed=1',(book['id'],)).fetchone()[0]
            book['assignments'] = c.execute('SELECT count(*) FROM chapter_assignments a JOIN chapters ch ON ch.id=a.chapter_id WHERE ch.textbook_id=? AND a.completed=1',(book['id'],)).fetchone()[0]
        resume = c.execute('SELECT s.id section_id,ch.textbook_id,s.section_number,s.title FROM study_notes n JOIN sections s ON s.id=n.section_id JOIN chapters ch ON ch.id=s.chapter_id WHERE n.visited_at IS NOT NULL ORDER BY n.visited_at DESC,n.rowid DESC LIMIT 1').fetchone()
        attempts = c.execute('SELECT COALESCE(sum(score),0),COALESCE(sum(total_questions),0),count(*) FROM concept_check_attempts').fetchone()
        missed = []
        for row in c.execute('''SELECT a.section_id,a.feedback_json,q.questions_json,s.section_number,s.title,ch.textbook_id,t.filename
          FROM concept_check_attempts a JOIN concept_checks q ON q.section_id=a.section_id
          JOIN sections s ON s.id=a.section_id JOIN chapters ch ON ch.id=s.chapter_id JOIN textbooks t ON t.id=ch.textbook_id
          WHERE a.id=(SELECT max(b.id) FROM concept_check_attempts b WHERE b.section_id=a.section_id)'''):
            questions = {q['id']: q for q in json.loads(row['questions_json'])}
            for f in json.loads(row['feedback_json']):
                if not f['correct']:
                    missed.append({'section_id':row['section_id'],'textbook_id':row['textbook_id'],'filename':row['filename'],
                      'section_number':row['section_number'],'prompt':questions[f['question_id']]['prompt'],
                      'hint':f['feedback'],'pdf_page':f['source']['evidence_page']})
    for book in books:
        sections = [s for ch in get_learning_path(book['id']) for s in ch['sections']]
        book.update(total=len(sections), completed=sum(bool(s['mastery_completed']) for s in sections),
          reading=sum(bool(s['reading_completed']) for s in sections),
          pending_activities=sum(bool(s['concept_check_completed']) and not s['mastery_completed'] for s in sections))
    return {'books':books,'resume':dict(resume) if resume else None,'missed':missed,
      'quiz_score':attempts[0],'quiz_total':attempts[1],'attempts':attempts[2]}

def chapter_pool(cid):
    with closing(get_connection()) as c:
        chapter = c.execute('SELECT * FROM chapters WHERE id=?',(cid,)).fetchone()
        if not chapter: raise HTTPException(404,'Chapter was not found.')
        rows = c.execute('''SELECT s.id,s.section_number,s.title,q.questions_json,p.mastery_completed
          FROM sections s LEFT JOIN concept_checks q ON q.section_id=s.id AND q.status='ready'
          LEFT JOIN section_progress p ON p.section_id=s.id WHERE s.chapter_id=?
          ORDER BY COALESCE(s.book_page,s.toc_pdf_page),s.id''',(cid,)).fetchall()
    pool = []
    for row in rows:
        if not row['mastery_completed'] or not row['questions_json']:
            raise HTTPException(409,'Complete every section in this chapter to unlock its review and assignment.')
        for q in json.loads(row['questions_json'])[:2]:
            pool.append({**q,'key':f"{row['id']}:{q['id']}",'section_number':row['section_number']})
    if not pool: raise HTTPException(409,'This chapter has no saved quizzes yet.')
    if len(pool)>12: pool=[pool[round(i*(len(pool)-1)/11)] for i in range(12)]
    return dict(chapter), rows, pool

@router.get('/chapters/{cid}/review')
def chapter_review(cid: int):
    chapter, sections, pool = chapter_pool(cid)
    with closing(get_connection()) as c:
        history=[dict(r) for r in c.execute('SELECT score,total,passed,created_at FROM chapter_reviews WHERE chapter_id=? ORDER BY id DESC',(cid,))]
        assignment=c.execute('SELECT * FROM chapter_assignments WHERE chapter_id=?',(cid,)).fetchone()
    return {'title':chapter['title'],'questions':[{'key':q['key'],'prompt':q['prompt'],'options':q['options'],'section_number':q['section_number']} for q in pool],
      'passing_score':math.ceil(len(pool)*.75),'history':history,
      'assignment_prompt':'Build a worked case study connecting these chapter concepts: '+ '; '.join(s['title'] for s in sections)+'. Explain your approach, include a worked example (code when appropriate), and cite the textbook pages supporting your decisions.',
      'assignment':dict(assignment) if assignment else None}

class Answers(BaseModel):
    answers: dict[str,StrictInt]

@router.post('/chapters/{cid}/review')
def grade_review(cid: int, body: Answers):
    _,_,pool=chapter_pool(cid)
    if set(body.answers)!={q['key'] for q in pool}: raise HTTPException(422,'Answer every review question.')
    feedback=[]
    for q in pool:
        answer=body.answers[q['key']]
        if not 0<=answer<len(q['options']): raise HTTPException(422,'Invalid answer option.')
        correct=answer==q['grading']['correct_index']
        feedback.append({'key':q['key'],'correct':correct,'feedback':q['explanation'] if correct else q['review_hint']})
    score=sum(f['correct'] for f in feedback); passed=score>=math.ceil(len(pool)*.75)
    with closing(get_connection()) as c,c:
        c.execute('INSERT INTO chapter_reviews(chapter_id,score,total,passed) VALUES (?,?,?,?)',(cid,score,len(pool),int(passed)))
    return {'score':score,'total':len(pool),'passed':passed,'feedback':feedback}

class Assignment(BaseModel):
    response: str = Field(max_length=20000)
    complete: bool=False
    reviewed: bool=False

@router.put('/chapters/{cid}/assignment')
def save_assignment(cid: int, body: Assignment):
    chapter_pool(cid)
    if body.complete and (not body.reviewed or len(body.response.strip())<100):
        raise HTTPException(422,'Write your case study and confirm the self-review checklist.')
    with closing(get_connection()) as c,c:
        if body.complete and not c.execute('SELECT 1 FROM chapter_reviews WHERE chapter_id=? AND passed=1',(cid,)).fetchone():
            raise HTTPException(409,'Pass the chapter review before completing its assignment.')
        c.execute('INSERT INTO chapter_assignments(chapter_id,response,completed) VALUES (?,?,?) ON CONFLICT(chapter_id) DO UPDATE SET response=excluded.response,completed=max(completed,excluded.completed),updated_at=CURRENT_TIMESTAMP',(cid,body.response,int(body.complete)))
    return {'saved':True,'completed':body.complete}

import json
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from fastapi import HTTPException
from backend import database as db, learning_tools as tools
from backend.code_runner import run_code_language

class StudyToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        p=patch.object(db,'DB_PATH',Path(self.temp.name)/'test.db'); p.start(); self.addCleanup(p.stop)
        db.init_db(); tools.init_learning_tools()
        self.book=db.save_textbook('book.pdf','book.pdf','hash',10,1000,[])
        db.save_learning_path(self.book,[{'number':'1','title':'Basics','sections':[{'number':'1.1','title':'Objects','toc_pdf_page':1},{'number':'1.2','title':'Methods','toc_pdf_page':5}]}])
        ch=db.get_learning_path(self.book)[0]; self.chapter=ch['id']; self.sections=[s['id'] for s in ch['sections']]

    def prepare(self):
        for sid in self.sections:
            db.mark_reading_complete(sid)
        with closing(db.get_connection()) as c,c:
            for sid in self.sections:
                questions=[{'id':i,'prompt':f'Question {i}', 'options':['A','B','C','D'],'grading':{'correct_index':0},'explanation':'Correct','review_hint':'Read the section','source':{'evidence_page':1}} for i in (1,2)]
                c.execute("INSERT INTO concept_checks(section_id,status,questions_json) VALUES (?,'ready',?)",(sid,json.dumps(questions)))
                c.execute('UPDATE section_progress SET concept_check_completed=1,mastery_completed=1 WHERE section_id=?',(sid,))

    def test_notes_bookmark_validation_resume_and_delete(self):
        sid=self.sections[0]; tools.visit(sid)
        tools.save_notes(sid,tools.Notes(note='My notes',bookmarks=[2,2,4]))
        self.assertEqual(tools.notes(sid),{'note':'My notes','bookmarks':[2,4]})
        self.assertEqual(tools.dashboard()['resume']['section_id'],sid)
        with self.assertRaises(HTTPException): tools.save_notes(sid,tools.Notes(bookmarks=[11]))
        with self.assertRaises(ValueError):
            db.save_learning_path(self.book,[{'number':'1','title':'Basics','sections':[{'number':'1.2','title':'Methods','toc_pdf_page':5}]}])
        self.assertEqual(tools.notes(sid)['note'],'My notes')
        tools.visit(self.sections[1]); self.assertEqual(tools.dashboard()['resume']['section_id'],self.sections[1])
        with closing(db.get_connection()) as c,c: c.execute('DELETE FROM textbooks WHERE id=?',(self.book,))
        self.assertIsNone(tools.dashboard()['resume'])

    def test_chapter_unlock_private_answers_grading_and_assignment(self):
        with self.assertRaises(HTTPException): tools.chapter_review(self.chapter)
        self.prepare(); data=tools.chapter_review(self.chapter)
        self.assertNotIn('correct_index',json.dumps(data))
        tools.save_assignment(self.chapter,tools.Assignment(response='Draft'))
        with self.assertRaises(HTTPException): tools.save_assignment(self.chapter,tools.Assignment(response='x'*120,complete=True,reviewed=True))
        answers={q['key']:0 for q in data['questions']}
        bad=tools.grade_review(self.chapter,tools.Answers(answers={k:1 for k in answers})); self.assertFalse(bad['passed'])
        result=tools.grade_review(self.chapter,tools.Answers(answers=answers)); self.assertTrue(result['passed'])
        self.assertEqual(result['score'],4)
        tools.save_assignment(self.chapter,tools.Assignment(response='x'*120,complete=True,reviewed=True))
        self.assertTrue(tools.chapter_review(self.chapter)['assignment']['completed'])
        self.assertEqual(tools.dashboard()['books'][0]['chapter_reviews'],1)
        self.assertEqual(tools.dashboard()['books'][0]['assignments'],1)
        with self.assertRaises(HTTPException): tools.grade_review(self.chapter,tools.Answers(answers={}))

    def test_dashboard_uses_latest_attempt_and_persisted_progress(self):
        self.prepare(); sid=self.sections[0]
        with closing(db.get_connection()) as c,c:
            for correct in (False,True):
                feedback=[{'question_id':1,'correct':correct,'feedback':'Review hint','source':{'evidence_page':1}}]
                c.execute('INSERT INTO concept_check_attempts(section_id,answers_json,feedback_json,score,passed,total_questions) VALUES (?,?,?,?,?,2)',(sid,'{}',json.dumps(feedback),int(correct),int(correct)))
        d=tools.dashboard(); self.assertEqual(d['missed'],[]); self.assertEqual(d['books'][0]['completed'],2)
        self.assertEqual(d['attempts'],2)

    def test_python_execution_errors_and_missing_cpp(self):
        self.assertEqual(run_code_language('print(6*7)','python')['output'].strip(),'42')
        self.assertEqual(run_code_language('raise ValueError("example")','python')['status'],'runtime_error')
        with patch('backend.code_runner.shutil.which',return_value=None), patch('backend.code_runner.Path.exists',return_value=False):
            self.assertEqual(run_code_language('int main(){}','cpp')['status'],'unavailable')

    def test_program_timeout_is_reported_without_cleanup_failure(self):
        result=run_code_language('while True: pass','python')
        self.assertEqual(result['status'],'timeout')

if __name__=='__main__': unittest.main()

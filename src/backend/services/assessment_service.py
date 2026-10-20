"""Grades stored quizzes and updates one local learner's progress."""
import json
from datetime import datetime, timezone

from src.backend import storage
from src.backend.config import settings
from src.backend.schemas import DifficultyLevel, QuizHistoryEntry, QuizQuestion, QuizSubmissionRequest, QuizSubmissionResponse, QuestionFeedback
from src.backend.services.student_service import get_student_service


class AssessmentService:
    def evaluate_quiz(self, submission: QuizSubmissionRequest) -> QuizSubmissionResponse:
        stored_student = get_student_service().get_student(submission.student_id)
        student = stored_student.model_copy(deep=True) if stored_student else None
        if not student:
            raise ValueError("Profile not found.")
        with storage.database() as db:
            row = db.execute("SELECT questions FROM quizzes WHERE id = ? AND profile_id = ? AND topic_id = ?",
                             (submission.quiz_id, submission.student_id, submission.topic_id)).fetchone()
        if not row:
            raise ValueError("Quiz not found.")
        questions = [QuizQuestion.model_validate(item) for item in json.loads(row[0])]
        expected = {question.question_id for question in questions}
        submitted = [answer.question_id for answer in submission.answers]
        if len(submitted) != len(expected) or set(submitted) != expected:
            raise ValueError("Submit one answer for every quiz question.")
        if any(not 0 <= answer.selected_option_index < 4 for answer in submission.answers):
            raise ValueError("Each question needs a valid answer.")
        if student.current_difficulty != questions[0].difficulty:
            raise ValueError("Difficulty changed. Start a new quiz.")

        answers = {answer.question_id: answer.selected_option_index for answer in submission.answers}
        feedback = []
        correct_count = 0
        for question in questions:
            selected_index = answers[question.question_id]
            is_correct = selected_index == question.correct_option_index
            correct_count += is_correct
            feedback.append(QuestionFeedback(
                question_id=question.question_id, prompt=question.prompt,
                selected_option_index=selected_index, selected_option_text=question.options[selected_index],
                correct_option_index=question.correct_option_index,
                correct_option_text=question.options[question.correct_option_index],
                is_correct=is_correct, explanation=question.explanation,
                diagnosis="Correct answer." if is_correct else question.misconception_diagnoses.get(str(selected_index), "Review the cited source."),
                source_chunk_id=question.source_chunk_id))

        score = round(100 * correct_count / len(questions), 1)
        previous = student.current_difficulty
        next_difficulty, action, advice = self._transition(previous, score)
        old_mastery = student.topic_mastery.get(submission.topic_id, 50.0)
        student.current_difficulty = next_difficulty
        student.quiz_history.insert(0, QuizHistoryEntry(
            quiz_id=submission.quiz_id, topic_id=submission.topic_id,
            difficulty=previous, score=score, total_questions=len(questions),
            correct_answers=correct_count, timestamp=datetime.now(timezone.utc).isoformat()))
        new_mastery = round(0.65 * old_mastery + 0.35 * score, 1)
        student.topic_mastery[submission.topic_id] = new_mastery
        student.overall_mastery = round(sum(student.topic_mastery.values()) / len(student.topic_mastery), 1)
        student.weak_topics = [topic for topic, mastery in student.topic_mastery.items() if mastery < 55]
        student.strong_topics = [topic for topic, mastery in student.topic_mastery.items() if mastery >= 75]
        result = QuizSubmissionResponse(
            quiz_id=submission.quiz_id, student_id=submission.student_id,
            topic_id=submission.topic_id, topic_name=submission.topic_id.replace("_", " ").title(),
            score_percentage=score, total_questions=len(questions), correct_count=correct_count,
            feedback=feedback, previous_difficulty=previous, new_difficulty=next_difficulty,
            difficulty_action=action, mastery_delta=round(new_mastery - old_mastery, 1),
            updated_mastery=new_mastery, pedagogical_advice=advice)
        return result, student

    @staticmethod
    def _transition(level: DifficultyLevel, score: float):
        levels: list[DifficultyLevel] = ["Easy", "Medium", "Hard"]
        index = levels.index(level)
        if score < settings.step_down_threshold:
            return levels[max(0, index - 1)], "SUPPORT_STEP_DOWN", "Review the source and retry at a more supportive level."
        if score >= settings.step_up_threshold:
            return levels[min(2, index + 1)], "PROMOTED", "Strong result. Your next quiz will use a higher level."
        return level, "RETAINED", "Keep practicing at this level to build consistency."


_instance = AssessmentService()


def get_assessment_service():
    return _instance

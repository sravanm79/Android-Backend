import os
import shutil
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from database import init_db, get_db
from models import Student, ReadingRecord, WritingRecord, Comment
from schemas import (
    StudentCreate,
    StudentRead,
    StudentLogin,
    StudentSync,
    ReadingRecordCreate,
    WritingRecordCreate,
    StudentWithHistory,
    MasterReportItem,
    CommentCreate,
    CommentRead
)

app = FastAPI(title="Vocab Master Teacher Server")

# ✅ 1. SETUP BASE PATH
BASE_UPLOAD_PATH = r"C:\Vocab\student_data"
if not os.path.exists(BASE_UPLOAD_PATH):
    os.makedirs(BASE_UPLOAD_PATH, exist_ok=True)

# ✅ 2. ENABLE CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 3. INITIALIZE DATABASE
init_db()


def get_student_storage_dir(fullName, studentClass, section, language, folder):
    """
    Get or create the storage directory for a student's files.
    """
    path = os.path.join(BASE_UPLOAD_PATH, fullName, studentClass, section, language, folder)
    os.makedirs(path, exist_ok=True)
    return path


# --- STUDENT AUTHENTICATION ENDPOINTS ---

@app.post("/student/register", response_model=StudentRead)
async def register_student(student_data: StudentCreate, db: Session = Depends(get_db)):
    """
    Register a new student account.
    """
    # Check if student_id already exists
    existing_student = db.query(Student).filter(Student.student_id == student_data.student_id).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="Student ID already registered")

    if not student_data.password:
        raise HTTPException(status_code=400, detail="Password is required for registration")

    # Create new student (password stored as plain text for simplicity)
    new_student = Student(
        student_id=student_data.student_id,
        password_hash=student_data.password,  # In production, hash the password
        fullName=student_data.fullName,
        studentClass=student_data.studentClass,
        section=student_data.section
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


@app.post("/student/login", response_model=StudentRead)
async def login_student(login_data: StudentLogin, db: Session = Depends(get_db)):
    """
    Login a student.
    """
    student = db.query(Student).filter(Student.student_id == login_data.student_id).first()
    if not student or student.password_hash != login_data.password:
        raise HTTPException(status_code=401, detail="Invalid student ID or password")

    return student


# --- STUDENT ENDPOINTS ---

@app.get("/student/my_report", response_model=StudentWithHistory)
async def get_my_report(student_id: str, db: Session = Depends(get_db)):
    """
    Get detailed report for the logged-in student including reading and writing history.
    Pass student_id as query parameter.
    """
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get reading history
        reading_history = db.query(ReadingRecord).filter(
            ReadingRecord.student_id == student.id
        ).order_by(ReadingRecord.timestamp.desc()).all()

        # Get writing history
        writing_history = db.query(WritingRecord).filter(
            WritingRecord.student_id == student.id
        ).order_by(WritingRecord.timestamp.desc()).all()

        # Get comments
        comments = db.query(Comment).filter(
            Comment.student_id == student.id
        ).order_by(Comment.timestamp.desc()).all()

        return StudentWithHistory(
            id=student.id,
            student_id=student.student_id,
            fullName=student.fullName,
            studentClass=student.studentClass,
            section=student.section,
            reading_history=reading_history,
            writing_history=writing_history,
            comments=comments
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- SYNC ENDPOINTS ---

@app.post("/sync/reading")
async def sync_reading(
        student_id: str = Form(...),
        reading_data: str = Form(...),
        audio_file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Submit a new reading practice record with audio file.

    Expects multipart form data with:
    - student_id: student ID string
    - reading_data: JSON string of reading metrics
    - audio_file: MP3/WAV audio recording
    """
    try:
        # Parse JSON strings
        reading_dict = json.loads(reading_data)
        
        # Validate with Pydantic
        student_parsed = StudentSync(student_id=student_id)
        reading_parsed = ReadingRecordCreate(**reading_dict)

        # ✅ Find student by student_id
        student = db.query(Student).filter(Student.student_id == student_parsed.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not registered. Please register first.")

        # ✅ Extract reading data
        language = reading_parsed.language
        level = reading_parsed.level
        wpm = reading_parsed.wpm
        accuracy = reading_parsed.accuracy
        mistakes = reading_parsed.mistakes
        pace = reading_parsed.pace
        practice_words = reading_parsed.practice_words
        omitted_words = reading_parsed.omitted_words
        referenceText = reading_parsed.referenceText
        transcript = reading_parsed.transcript
        timestamp = reading_parsed.timestamp

        storage_dir = get_student_storage_dir(student.fullName, student.studentClass, student.section, language, "audios")

        # ✅ Save audio file
        new_filename = f"{timestamp}_{audio_file.filename}"
        file_path = os.path.join(storage_dir, new_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # ✅ Create reading record
        reading_record = ReadingRecord(
            student_id=student.id,
            language=language,
            level=level,
            wpm=wpm,
            accuracy=accuracy,
            mistakes=mistakes,
            pace=pace,
            practice_words=practice_words,
            omitted_words=omitted_words,
            referenceText=referenceText,
            transcript=transcript,
            timestamp=timestamp
        )
        db.add(reading_record)
        db.commit()

        return {"status": "success", "file_saved_at": file_path}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in form data")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/writing")
async def sync_writing(
        student_id: str = Form(...),
        writing_data: str = Form(...),
        document_file: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db)
):
    """
    Submit a new writing assessment record with optional document.

    Expects multipart form data with:
    - student_id: student ID string
    - writing_data: JSON string of writing metrics
    - document_file: optional PDF/document
    """
    try:
        # Parse JSON strings
        writing_dict = json.loads(writing_data)
        
        # Validate with Pydantic
        student_parsed = StudentSync(student_id=student_id)
        writing_parsed = WritingRecordCreate(**writing_dict)

        # ✅ Find student by student_id
        student = db.query(Student).filter(Student.student_id == student_parsed.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not registered. Please register first.")

        # ✅ Extract writing data
        language = writing_parsed.language
        mistakes = writing_parsed.mistakes
        accuracy = writing_parsed.accuracy
        originalText = writing_parsed.originalText
        correctedText = writing_parsed.correctedText
        feedback = writing_parsed.feedback
        timestamp = writing_parsed.timestamp

        file_save_path = "None"
        if document_file:
            storage_dir = get_student_storage_dir(student.fullName, student.studentClass, student.section, language, "pdf_images")

            # ✅ Save document file
            new_filename = f"{timestamp}_{document_file.filename}"
            file_path = os.path.join(storage_dir, new_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(document_file.file, buffer)

            file_save_path = file_path

        # ✅ Create writing record
        writing_record = WritingRecord(
            student_id=student.id,
            language=language,
            mistakes=mistakes,
            accuracy=accuracy,
            originalText=originalText,
            correctedText=correctedText,
            feedback=feedback,
            timestamp=timestamp
        )
        db.add(writing_record)
        db.commit()

        return {"status": "success", "file_saved_at": file_save_path}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in form data")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



# --- COMMENT ENDPOINTS ---

@app.post("/teacher/comments", response_model=CommentRead)
async def add_comment(
        comment_data: CommentCreate,
        db: Session = Depends(get_db)
):
    """
    Add a comment about a student.
    """
    # Get the student by student_id string
    student = db.query(Student).filter(Student.student_id == comment_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Create the comment
    comment = Comment(
        student_id=student.id,
        comment_text=comment_data.comment_text,
        timestamp=comment_data.timestamp
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@app.get("/teacher/comments/{student_id}", response_model=list[CommentRead])
async def get_student_comments(
        student_id: str,
        db: Session = Depends(get_db)
):
    """
    Get all comments for a specific student.
    """
    # Get the student by student_id string
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get comments
    comments = db.query(Comment).filter(
        Comment.student_id == student.id
    ).order_by(Comment.timestamp.desc()).all()

    return comments


# --- TEACHER REPORTING ENDPOINTS ---

@app.get("/teacher/master_report", response_model=list[MasterReportItem])
async def master_report(
        db: Session = Depends(get_db)
):
    """
    Get combined report of all reading and writing records.
    Returns all student records sorted by timestamp (most recent first).
    """
    try:
        reading_query = db.query(
            Student.fullName,
            Student.studentClass,
            Student.section,
            ReadingRecord
        ).join(ReadingRecord, Student.id == ReadingRecord.student_id)
        writing_query = db.query(
            Student.fullName,
            Student.studentClass,
            Student.section,
            WritingRecord
        ).join(WritingRecord, Student.id == WritingRecord.student_id)

        reading_records = reading_query.all()
        writing_records = writing_query.all()

        # Format reading records
        result = []
        for fullName, studentClass, section, record in reading_records:
            result.append(MasterReportItem(
                fullName=fullName,
                studentClass=studentClass,
                section=section,
                Task="Reading",
                language=record.language,
                level=record.level,
                accuracy=record.accuracy,
                wpm=record.wpm,
                mistakes=record.mistakes,
                pace=record.pace,
                practice_words=record.practice_words,
                omitted_words=record.omitted_words,
                referenceText=record.referenceText,
                transcript=record.transcript,
                originalText=None,
                correctedText=None,
                feedback=None,
                timestamp=record.timestamp
            ))

        # Format writing records
        for fullName, studentClass, section, record in writing_records:
            result.append(MasterReportItem(
                fullName=fullName,
                studentClass=studentClass,
                section=section,
                Task="Writing",
                language=record.language,
                accuracy=record.accuracy,
                wpm=None,
                mistakes=record.mistakes,
                pace=None,
                practice_words=None,
                omitted_words=None,
                referenceText=None,
                transcript=None,
                originalText=record.originalText,
                correctedText=record.correctedText,
                feedback=record.feedback,
                timestamp=record.timestamp
            ))

        # Sort by timestamp (descending)
        result.sort(key=lambda x: x.timestamp, reverse=True)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/teacher/student_report/{student_id}", response_model=StudentWithHistory)
async def get_student_report(
        student_id: str,
        db: Session = Depends(get_db)
):
    """
    Get detailed report for a specific student including reading and writing history.
    """
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get reading history
        reading_history = db.query(ReadingRecord).filter(
            ReadingRecord.student_id == student.id
        ).order_by(ReadingRecord.timestamp.desc()).all()

        # Get writing history
        writing_history = db.query(WritingRecord).filter(
            WritingRecord.student_id == student.id
        ).order_by(WritingRecord.timestamp.desc()).all()

        # Get comments
        comments = db.query(Comment).filter(
            Comment.student_id == student.id
        ).order_by(Comment.timestamp.desc()).all()


        return StudentWithHistory(
            id=student.id,
            student_id=student.student_id,
            fullName=student.fullName,
            studentClass=student.studentClass,
            section=student.section,
            reading_history=reading_history,
            writing_history=writing_history,
            comments=comments
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/teacher/list_students", response_model=list[StudentRead])
async def list_students(
        db: Session = Depends(get_db)
):
    """
    List students in the system.
    Returns list of students sorted by fullName.
    """
    try:
        students = db.query(Student).order_by(Student.fullName.asc()).all()
        return students
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7070)

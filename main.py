import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from database import init_db, get_db
from models import Student, ReadingRecord, WritingRecord
from schemas import (
    StudentCreate, 
    ReadingRecordCreate, 
    WritingRecordCreate,
    StudentRead,
    StudentWithHistory,
    MasterReportItem
)

app = FastAPI(title="Vocab Master Teacher Server")

# ✅ 1. SETUP BASE PATH
BASE_UPLOAD_PATH = "/home/vocab-server6/sravan/data_upload"
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

# ✅ HELPER: Multi-level folder logic
def get_student_storage_dir(full_name: str, student_class: str, section: str, language: str, subfolder: str):
    clean_name = full_name.replace(" ", "_")
    lang_folder = "Kannada" if language.upper() == "KN" or language.lower() == "kan" else "English"
    student_folder_name = f"{clean_name}_{student_class}_{section}"
    target_dir = os.path.join(BASE_UPLOAD_PATH, student_folder_name, lang_folder, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

# --- SYNC ENDPOINTS ---

@app.post("/sync/reading")
async def sync_reading(
    student_data: StudentCreate,
    reading_data: ReadingRecordCreate,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Submit a new reading practice record with audio file.
    
    Expects multipart form data with:
    - Student info (fullName, studentClass, section)
    - Reading metrics (language, wpm, accuracy, mistakes, pace, etc.)
    - audio_file (MP3/WAV audio recording)
    """
    try:
        # ✅ Extract student data (validated by Pydantic)
        fullName = student_data.fullName
        studentClass = student_data.studentClass
        section = student_data.section
        
        # ✅ Extract reading data (validated by Pydantic)
        language = reading_data.language
        wpm = reading_data.wpm
        accuracy = reading_data.accuracy
        mistakes = reading_data.mistakes
        pace = reading_data.pace
        practice_words = reading_data.practice_words
        omitted_words = reading_data.omitted_words
        referenceText = reading_data.referenceText
        transcript = reading_data.transcript
        timestamp = reading_data.timestamp
        
        storage_dir = get_student_storage_dir(fullName, studentClass, section, language, "audios")
        
        # ✅ Save audio file
        new_filename = f"{timestamp}_{audio_file.filename}"
        file_path = os.path.join(storage_dir, new_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # ✅ Get or create student
        student = db.query(Student).filter(
            Student.fullName == fullName,
            Student.studentClass == studentClass,
            Student.section == section
        ).first()
        
        if not student:
            student = Student(
                fullName=fullName,
                studentClass=studentClass,
                section=section
            )
            db.add(student)
            db.flush()
        
        # ✅ Create reading record
        reading_record = ReadingRecord(
            student_id=student.id,
            language=language,
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync/writing")
async def sync_writing(
    student_data: StudentCreate,
    writing_data: WritingRecordCreate,
    document_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Submit a new writing assessment record with optional document.
    
    Expects multipart form data with:
    - Student info (fullName, studentClass, section)
    - Writing metrics (language, mistakes, accuracy, originalText, etc.)
    - document_file (optional PDF/document)
    """
    try:
        # ✅ Extract student data (validated by Pydantic)
        fullName = student_data.fullName
        studentClass = student_data.studentClass
        section = student_data.section
        
        # ✅ Extract writing data (validated by Pydantic)
        language = writing_data.language
        mistakes = writing_data.mistakes
        accuracy = writing_data.accuracy
        originalText = writing_data.originalText
        correctedText = writing_data.correctedText
        feedback = writing_data.feedback
        timestamp = writing_data.timestamp
        
        file_save_path = "None"
        if document_file:
            storage_dir = get_student_storage_dir(fullName, studentClass, section, language, "pdf_images")
            
            # ✅ Save document file
            new_filename = f"{timestamp}_{document_file.filename}"
            file_save_path = os.path.join(storage_dir, new_filename)

            with open(file_save_path, "wb") as buffer:
                shutil.copyfileobj(document_file.file, buffer)

        # ✅ Get or create student
        student = db.query(Student).filter(
            Student.fullName == fullName,
            Student.studentClass == studentClass,
            Student.section == section
        ).first()
        
        if not student:
            student = Student(
                fullName=fullName,
                studentClass=studentClass,
                section=section
            )
            db.add(student)
            db.flush()

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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- TEACHER REPORTING ENDPOINTS ---

@app.get("/teacher/master_report", response_model=list[MasterReportItem])
async def master_report(db: Session = Depends(get_db)):
    """
    Get combined report of all reading and writing records.
    Returns all student records sorted by timestamp (most recent first).
    """
    try:
        # Get all reading records with student info
        reading_records = db.query(
            Student.fullName,
            Student.studentClass,
            Student.section,
            ReadingRecord
        ).join(ReadingRecord, Student.id == ReadingRecord.student_id).all()
        
        # Get all writing records with student info
        writing_records = db.query(
            Student.fullName,
            Student.studentClass,
            Student.section,
            WritingRecord
        ).join(WritingRecord, Student.id == WritingRecord.student_id).all()
        
        # Format reading records
        result = []
        for fullName, studentClass, section, record in reading_records:
            result.append(MasterReportItem(
                fullName=fullName,
                studentClass=studentClass,
                section=section,
                Task="Reading",
                language=record.language,
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

@app.get("/teacher/student_report/{fullName}", response_model=StudentWithHistory)
async def get_student_report(fullName: str, db: Session = Depends(get_db)):
    """
    Get detailed report for a specific student including reading and writing history.
    """
    try:
        student = db.query(Student).filter(Student.fullName == fullName).first()
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
        
        return StudentWithHistory(
            id=student.id,
            fullName=student.fullName,
            studentClass=student.studentClass,
            section=student.section,
            reading_history=reading_history,
            writing_history=writing_history
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teacher/list_students", response_model=list[StudentRead])
async def list_students(db: Session = Depends(get_db)):
    """
    List all students in the system.
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
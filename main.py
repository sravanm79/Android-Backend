import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from database import init_db, get_db
from models import Student, ReadingRecord, WritingRecord, User, Comment
from schemas import (
    StudentCreate, 
    ReadingRecordCreate, 
    WritingRecordCreate,
    StudentRead,
    StudentWithHistory,
    MasterReportItem,
    UserCreate,
    UserRead,
    LoginRequest,
    TokenResponse,
    CommentCreate,
    CommentRead
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

# ✅ 4. AUTHENTICATION SETUP
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def check_teacher_access(user: User, student_class: str = None, section: str = None):
    """Check if teacher has access to the specified class/section."""
    if user.role == "principal":
        return True  # Principals can access everything
    if user.role == "teacher":
        if student_class and user.assigned_class != student_class:
            return False
        if section and user.assigned_section != section:
            return False
        return True
    return False

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

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/create_user", response_model=UserRead)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account. (For admin use only - in production, add authentication)
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role=user_data.role,
        assigned_class=user_data.assigned_class,
        assigned_section=user_data.assigned_section
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- COMMENT ENDPOINTS ---

@app.post("/teacher/comments", response_model=CommentRead)
async def add_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a comment about a student. Only teachers can add comments for students in their assigned class.
    """
    # Get the student to check access
    student = db.query(Student).filter(Student.id == comment_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if teacher has access to this student's class/section
    if not check_teacher_access(current_user, student.studentClass, student.section):
        raise HTTPException(status_code=403, detail="Access denied: You can only comment on students in your assigned class")
    
    # Create the comment
    comment = Comment(
        student_id=comment_data.student_id,
        teacher_id=current_user.id,
        comment_text=comment_data.comment_text,
        timestamp=comment_data.timestamp
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Add teacher username to response
    comment.teacher_username = current_user.username
    return comment

@app.get("/teacher/comments/{student_id}", response_model=list[CommentRead])
async def get_student_comments(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all comments for a specific student. Teachers can only see comments for students in their class.
    """
    # Get the student to check access
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if teacher has access to this student's class/section
    if not check_teacher_access(current_user, student.studentClass, student.section):
        raise HTTPException(status_code=403, detail="Access denied: You can only view comments for students in your assigned class")
    
    # Get comments with teacher usernames
    comments = db.query(Comment, User.username).join(User, Comment.teacher_id == User.id).filter(
        Comment.student_id == student_id
    ).order_by(Comment.timestamp.desc()).all()
    
    # Format response
    result = []
    for comment, teacher_username in comments:
        result.append(CommentRead(
            id=comment.id,
            student_id=comment.student_id,
            teacher_id=comment.teacher_id,
            comment_text=comment.comment_text,
            timestamp=comment.timestamp,
            teacher_username=teacher_username
        ))
    return result

# --- TEACHER REPORTING ENDPOINTS ---

@app.get("/teacher/master_report", response_model=list[MasterReportItem])
async def master_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get combined report of all reading and writing records.
    Teachers see only their assigned class, principals see all.
    Returns all student records sorted by timestamp (most recent first).
    """
    try:
        # Build query based on user role
        if current_user.role == "teacher":
            # Filter by assigned class and section
            reading_query = db.query(
                Student.fullName,
                Student.studentClass,
                Student.section,
                ReadingRecord
            ).join(ReadingRecord, Student.id == ReadingRecord.student_id).filter(
                Student.studentClass == current_user.assigned_class,
                Student.section == current_user.assigned_section
            )
            writing_query = db.query(
                Student.fullName,
                Student.studentClass,
                Student.section,
                WritingRecord
            ).join(WritingRecord, Student.id == WritingRecord.student_id).filter(
                Student.studentClass == current_user.assigned_class,
                Student.section == current_user.assigned_section
            )
        else:  # principal
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
async def get_student_report(
    fullName: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed report for a specific student including reading and writing history.
    Teachers can only access students in their assigned class.
    """
    try:
        student = db.query(Student).filter(Student.fullName == fullName).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Check access
        if not check_teacher_access(current_user, student.studentClass, student.section):
            raise HTTPException(status_code=403, detail="Access denied: You can only view students in your assigned class")
        
        # Get reading history
        reading_history = db.query(ReadingRecord).filter(
            ReadingRecord.student_id == student.id
        ).order_by(ReadingRecord.timestamp.desc()).all()
        
        # Get writing history
        writing_history = db.query(WritingRecord).filter(
            WritingRecord.student_id == student.id
        ).order_by(WritingRecord.timestamp.desc()).all()
        
        # Get comments with teacher usernames
        comments_query = db.query(Comment, User.username).join(User, Comment.teacher_id == User.id).filter(
            Comment.student_id == student.id
        ).order_by(Comment.timestamp.desc()).all()
        
        comments = []
        for comment, teacher_username in comments_query:
            comments.append(CommentRead(
                id=comment.id,
                student_id=comment.student_id,
                teacher_id=comment.teacher_id,
                comment_text=comment.comment_text,
                timestamp=comment.timestamp,
                teacher_username=teacher_username
            ))
        
        return StudentWithHistory(
            id=student.id,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List students in the system.
    Teachers see only students in their assigned class, principals see all.
    Returns list of students sorted by fullName.
    """
    try:
        if current_user.role == "teacher":
            students = db.query(Student).filter(
                Student.studentClass == current_user.assigned_class,
                Student.section == current_user.assigned_section
            ).order_by(Student.fullName.asc()).all()
        else:  # principal
            students = db.query(Student).order_by(Student.fullName.asc()).all()
        return students
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7070)
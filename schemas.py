from pydantic import BaseModel
from typing import Optional, List


# ============= STUDENT SCHEMAS =============

class StudentBase(BaseModel):
    student_id: str
    fullName: str
    studentClass: str
    section: str


class StudentCreate(StudentBase):
    password: Optional[str] = None


class StudentRead(StudentBase):
    id: int

    class Config:
        from_attributes = True


class StudentLogin(BaseModel):
    student_id: str
    password: str


class StudentSync(BaseModel):
    student_id: str


# ============= READING RECORD SCHEMAS =============

class ReadingRecordBase(BaseModel):
    language: str
    wpm: int
    accuracy: int
    mistakes: int
    pace: str
    practice_words: str = ""
    omitted_words: str = ""
    referenceText: str = ""
    transcript: str = ""
    timestamp: int


class ReadingRecordCreate(ReadingRecordBase):
    pass


class ReadingRecordRead(ReadingRecordBase):
    id: int
    student_id: int

    class Config:
        from_attributes = True


# ============= WRITING RECORD SCHEMAS =============

class WritingRecordBase(BaseModel):
    language: str
    mistakes: int
    accuracy: int
    originalText: str = ""
    correctedText: str = ""
    feedback: str = ""
    timestamp: int


class WritingRecordCreate(WritingRecordBase):
    pass


class WritingRecordRead(WritingRecordBase):
    id: int
    student_id: int

    class Config:
        from_attributes = True


# ============= USER SCHEMAS =============

class UserBase(BaseModel):
    username: str
    role: str  # 'teacher' or 'principal'
    assigned_class: Optional[str] = None
    assigned_section: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True


# ============= COMMENT SCHEMAS =============

class CommentBase(BaseModel):
    comment_text: str
    timestamp: int


class CommentCreate(CommentBase):
    student_id: str


class CommentRead(CommentBase):
    id: int
    student_id: int

    class Config:
        from_attributes = True


# ============= STUDENT WITH HISTORY =============

class StudentWithHistory(StudentRead):
    reading_history: List[ReadingRecordRead] = []
    writing_history: List[WritingRecordRead] = []
    comments: List[CommentRead] = []

    class Config:
        from_attributes = True


# ============= MASTER REPORT =============

class MasterReportItem(BaseModel):
    fullName: str
    studentClass: str
    section: str
    Task: str
    language: str
    accuracy: int
    wpm: Optional[int] = None
    mistakes: int
    pace: Optional[str] = None
    practice_words: Optional[str] = None
    omitted_words: Optional[str] = None
    referenceText: Optional[str] = None
    transcript: Optional[str] = None
    originalText: Optional[str] = None
    correctedText: Optional[str] = None
    feedback: Optional[str] = None
    timestamp: int

    class Config:
        from_attributes = True


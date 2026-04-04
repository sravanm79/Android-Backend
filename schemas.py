from pydantic import BaseModel
from typing import Optional, List


# ============= STUDENT SCHEMAS =============

class StudentBase(BaseModel):
    fullName: str
    studentClass: str
    section: str


class StudentCreate(StudentBase):
    pass


class StudentRead(StudentBase):
    id: int

    class Config:
        from_attributes = True


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
    student_id: int


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
    student_id: int


class WritingRecordRead(WritingRecordBase):
    id: int
    student_id: int

    class Config:
        from_attributes = True


# ============= STUDENT WITH HISTORY =============

class StudentWithHistory(StudentRead):
    reading_history: List[ReadingRecordRead] = []
    writing_history: List[WritingRecordRead] = []

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


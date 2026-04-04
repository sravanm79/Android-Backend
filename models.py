from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    """Student model - stores student information."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    fullName = Column(String, nullable=False)
    studentClass = Column(String, nullable=False)
    section = Column(String, nullable=False)

    # Relationships
    reading_records = relationship("ReadingRecord", back_populates="student", cascade="all, delete-orphan")
    writing_records = relationship("WritingRecord", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    class Config:
        from_attributes = True


class ReadingRecord(Base):
    """ReadingRecord model - stores reading practice data."""
    __tablename__ = "reading_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    language = Column(String, nullable=False)
    wpm = Column(Integer)
    accuracy = Column(Integer)
    mistakes = Column(Integer)
    pace = Column(String)
    practice_words = Column(String, default="")
    omitted_words = Column(String, default="")
    referenceText = Column(String, default="")
    transcript = Column(String, default="")
    timestamp = Column(Integer, nullable=False)

    # Relationship back to Student
    student = relationship("Student", back_populates="reading_records")

    class Config:
        from_attributes = True


class WritingRecord(Base):
    """WritingRecord model - stores writing assessment data."""
    __tablename__ = "writing_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    language = Column(String, nullable=False)
    mistakes = Column(Integer)
    accuracy = Column(Integer)
    originalText = Column(String, default="")
    correctedText = Column(String, default="")
    feedback = Column(String, default="")
    timestamp = Column(Integer, nullable=False)

    # Relationship back to Student
    student = relationship("Student", back_populates="writing_records")

    class Config:
        from_attributes = True


from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    """Student model - stores student information."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, nullable=False)  # Unique student ID for login
    password_hash = Column(String, nullable=False)
    fullName = Column(String, nullable=False)
    studentClass = Column(String, nullable=False)
    section = Column(String, nullable=False)

    # Relationships
    reading_records = relationship("ReadingRecord", back_populates="student", cascade="all, delete-orphan")
    writing_records = relationship("WritingRecord", back_populates="student", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="student", cascade="all, delete-orphan")

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


class User(Base):
    """User model - stores teacher and principal accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'teacher' or 'principal'
    assigned_class = Column(String, nullable=True)  # For teachers: class they can access
    assigned_section = Column(String, nullable=True)  # For teachers: section they can access

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    class Config:
        from_attributes = True


class Comment(Base):
    """Comment model - stores teacher comments about students."""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    timestamp = Column(Integer, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="comments")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    class Config:
        from_attributes = True


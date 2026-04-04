# Vocab Master Teacher Server

A production-ready **FastAPI REST API** backend for managing student reading and writing practice records with audio and document file uploads.

## 🎯 Features

✅ **Student Management**
- Track students by class and section
- Manage student information
- Organize students by groups

✅ **Reading Practice Tracking**
- Record words-per-minute (WPM)
- Track accuracy and mistakes
- Store audio recordings (MP3/WAV)
- Support for English and Kannada languages
- Save practice details and transcripts

✅ **Writing Assessment Tracking**
- Record writing accuracy and mistakes
- Store original and corrected text
- Include teacher feedback
- Support PDF and document uploads
- Track writing improvements

✅ **Reporting & Analytics**
- Master report combining all records
- Individual student history reports
- Detailed student listing
- Sortable and filterable results
- Comprehensive metrics per activity

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.104.1 |
| **ORM** | SQLAlchemy | 2.0.23 |
| **Validation** | Pydantic | Latest |
| **Server** | Uvicorn | 0.24.0 |
| **Database** | SQLite | Built-in |

## 📁 Project Structure

```
backend_app/
├── main.py              # FastAPI application and 5 REST endpoints
├── models.py            # SQLAlchemy ORM models (Student, ReadingRecord, WritingRecord)
├── database.py          # Database configuration and session management
├── schemas.py           # Pydantic request/response validation schemas
├── requirements.txt     # Python package dependencies
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
└── README.md           # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation & Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/vocab-master-server.git
cd vocab-master-server
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python main.py
```

Server starts on: **http://0.0.0.0:7070**

## 📚 API Documentation

Once running, access interactive documentation at:
- **Swagger UI:** http://localhost:7070/docs
- **ReDoc:** http://localhost:7070/redoc

Both are **auto-generated from Pydantic schemas**.

## 🔌 API Endpoints

### Reading Practice
```http
POST /sync/reading
```
Submit reading practice with audio file. Validates student info and reading metrics.

**Request:** StudentCreate + ReadingRecordCreate + audio_file  
**Response:** `{"status": "success", "file_saved_at": "path"}`

### Writing Assessment
```http
POST /sync/writing
```
Submit writing assessment with optional document. Validates student info and writing metrics.

**Request:** StudentCreate + WritingRecordCreate + optional document_file  
**Response:** `{"status": "success", "file_saved_at": "path"}`

### Reports
```http
GET /teacher/master_report
```
Get combined report of all student records (reading + writing).  
**Response:** `[MasterReportItem, ...]` (sorted by timestamp)

```http
GET /teacher/student_report/{fullName}
```
Get detailed history for a specific student including reading and writing records.  
**Response:** `StudentWithHistory` (student info + history lists)

```http
GET /teacher/list_students
```
Get list of all students in the system.  
**Response:** `[StudentRead, ...]` (sorted by name)

## 🗄️ Database Schema

### Students Table
```
id (PK)          - Auto-incrementing integer
fullName         - Student's full name
studentClass     - Class number
section          - Section letter
```

### Reading Records Table
```
id (PK)          - Auto-incrementing integer
student_id (FK)  - Reference to student
language         - EN or KN
wpm              - Words per minute
accuracy         - Accuracy percentage
mistakes         - Number of mistakes
pace             - Reading pace
practice_words   - Words practiced (optional)
omitted_words    - Words omitted (optional)
referenceText    - Original text (optional)
transcript       - Student's reading (optional)
timestamp        - Unix timestamp
```

### Writing Records Table
```
id (PK)          - Auto-incrementing integer
student_id (FK)  - Reference to student
language         - EN or KN
mistakes         - Number of mistakes
accuracy         - Accuracy percentage
originalText     - Original writing (optional)
correctedText    - Corrected version (optional)
feedback         - Teacher feedback (optional)
timestamp        - Unix timestamp
```

## ⚙️ Configuration

### Database
- **Type:** SQLite (default)
- **Location:** `teacher_database.db` (auto-created in project root)
- **Auto-initialization:** Tables created on first run

### File Upload Path
Files are uploaded to: `/home/vocab-server6/sravan/data_upload/`

Directory structure created automatically:
```
/data_upload/
  {StudentName}_{Class}_{Section}/
    English/
      audios/          # Audio files for reading
      pdf_images/      # Documents for writing
    Kannada/
      audios/          # Audio files for reading
      pdf_images/      # Documents for writing
```

### Environment Variables
Create `.env` (optional):
```
DATABASE_URL=sqlite:///./teacher_database.db
LOG_LEVEL=info
CORS_ORIGINS=["*"]
```

## 🧪 Testing

### Using curl

```bash
# List all students
curl http://localhost:7070/teacher/list_students

# Get master report
curl http://localhost:7070/teacher/master_report

# Get student report
curl "http://localhost:7070/teacher/student_report/John%20Doe"
```

### Using Swagger UI
1. Go to http://localhost:7070/docs
2. Click on any endpoint
3. Click "Try it out"
4. Enter parameters
5. Click "Execute"

## 🏗️ Architecture

### Separation of Concerns

- **models.py** - Defines database schema (SQLAlchemy ORM)
- **database.py** - Manages database connections and sessions
- **schemas.py** - Validates request/response data (Pydantic)
- **main.py** - Handles API logic and routing (FastAPI)

### Validation Flow

```
Request
  ↓
Pydantic Schema Validation (schemas.py)
  ↓
FastAPI Endpoint (main.py)
  ↓
SQLAlchemy ORM Query (models.py)
  ↓
Database (database.py)
  ↓
Response Validation (schemas.py)
  ↓
Client
```

## 🚢 Deployment

### Production Setup

1. **Install Gunicorn**
```bash
pip install gunicorn
```

2. **Run with Gunicorn**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:7070
```

3. **Enable SQL Logging** (optional)
Edit `database.py`: Change `echo=False` to `echo=True`

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t vocab-master .
docker run -p 7070:7070 vocab-master
```

## 🐛 Troubleshooting

### Port 7070 Already in Use
Edit `main.py` and change the port:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Database Locked
Restart the application or remove `teacher_database.db` and restart.

### Upload Path Not Found
Ensure `/home/vocab-server6/sravan/data_upload/` exists with write permissions:
```bash
mkdir -p /home/vocab-server6/sravan/data_upload
chmod 755 /home/vocab-server6/sravan/data_upload
```

### Import Errors
Ensure all imports are correct:
```bash
python -m py_compile main.py models.py database.py schemas.py
```

## 📝 Git Commands to Push to GitHub

```bash
# Initialize git (first time only)
git init

# Configure git (first time only)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Vocab Master Teacher Server"

# Create repo on GitHub at https://github.com/new

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/vocab-master-server.git
git branch -M main
git push -u origin main
```

## 🔄 Making Changes and Pushing

```bash
# Make your changes to the code

# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Description of changes"

# Push to GitHub
git push
```

## 👥 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m "Add amazing feature"`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review code in respective files
3. Check console logs for errors
4. Create an issue on GitHub

## 📊 Project Statistics

- **Total Files:** 7
- **Total Lines of Code:** ~930
- **Python Files:** 4 (main, models, database, schemas)
- **Configuration Files:** 2 (requirements.txt, .gitignore)
- **Documentation:** 1 (README)
- **License:** 1 (MIT)

## 🎓 What You're Using

✅ **FastAPI** - Modern async web framework  
✅ **SQLAlchemy ORM** - Database abstraction layer  
✅ **Pydantic** - Data validation with type hints  
✅ **Uvicorn** - Lightning-fast ASGI server  
✅ **SQLite** - Lightweight database  

All with **zero external configuration** - just `pip install -r requirements.txt` and `python main.py`!

## 🚀 Version History

- **v1.0.0** (April 4, 2026) - Initial release
  - Complete FastAPI application
  - SQLAlchemy ORM integration
  - Pydantic validation on all endpoints
  - 5 fully functional REST endpoints
  - Auto-generated API documentation
  - SQLite database with auto-initialization

---

**Built with ❤️ using FastAPI + SQLAlchemy + Pydantic**

**Ready for production. Ready for GitHub. Ready to scale.** 🚀


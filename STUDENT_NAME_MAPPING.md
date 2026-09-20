# Student Name Mapping (GDPR-Compliant Local Storage)

## Overview

Teachers can now write in the **actual names of students** while the system stores aliases in the database for GDPR compliance. Real names are **stored only locally on your device** and never sent to the server.

## How It Works

### Storage Architecture

- **Database**: Stores student aliases (e.g., "Student1", "S001")
- **Local JSON Files**: Each teacher has a private JSON file (`teacher_names/teacher_{id}_names.json`) that maps:
  ```
  {
    "mappings": {
      "1": "John Smith",
      "5": "Sarah Johnson"
    }
  }
  ```

### Privacy & Security

✓ **Real names never leave your device**  
✓ **Local files are Git-ignored** (never committed to version control)  
✓ **Only loaded in your teacher account** - other teachers don't see your mappings  
✓ **GDPR compliant** - full separation of anonymized data and personal information  

## Using the Feature

### Setting a Student's Real Name

1. Go to **Admin → Students**
2. Click the **✎ Edit** button next to any student's name
3. Enter the real name in the modal
4. Click **Save**

The real name will now display in the table, with the alias shown in smaller text below.

### Clearing a Name Mapping

1. Open the edit modal for a student
2. Click the **Clear** button to remove the real name mapping
3. The student's alias will be displayed again

## Technical Details

### Backend Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/api/student-names` | GET | Fetch all name mappings for current teacher |
| `/admin/api/student-names/<id>` | POST | Set/update a student's real name |
| `/admin/api/student-names/<id>` | DELETE | Clear a student's real name mapping |

### Frontend Display

The admin students page:
- Loads all name mappings on page load via `loadNameMappings()`
- Displays real names where available
- Shows aliases in smaller text below real names
- Provides inline edit buttons for easy name management

### File Organization

```
webscraper/
├── local_name_mapping.py          # Core name mapping logic
├── admin_routes.py                # API endpoints (lines ~1435+)
├── teacher_names/                 # Local storage (Git-ignored)
│   ├── teacher_1_names.json
│   ├── teacher_2_names.json
│   └── ...
└── templates/admin_students.html  # UI with name editing
```

## Important Notes

⚠️ **Backup Considerations**  
Your name mappings are stored in `teacher_names/` directory. If you need to:
- **Switch computers**: Copy the entire `teacher_names/` folder to preserve mappings
- **Backup data**: Include `teacher_names/` in your backups
- **Share instance**: Each teacher's mappings are completely isolated

⚠️ **Clearing Mappings**  
If you delete a student account or manually edit JSON files, the mappings won't auto-cleanup. The system safely handles stale entries (they're just ignored).

## API Example

```javascript
// Get all name mappings
fetch('/admin/api/student-names')
  .then(r => r.json())
  .then(data => console.log(data.mappings));

// Set a real name
fetch('/admin/api/student-names/5', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ real_name: 'Jane Doe' })
});

// Clear a mapping
fetch('/admin/api/student-names/5', { method: 'DELETE' });
```

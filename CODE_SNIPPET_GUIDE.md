# Code Snippet Component Guide

## Overview
The code snippet component allows you to add formatted code examples to your content with syntax highlighting, copy functionality, and Online Python (online-python.com) integration.

## Features
- **Syntax Highlighting**: VS Code-style color-coded syntax highlighting using Highlight.js
- **Dark Theme Styling**: Carbon.sh-inspired design with VS Code color scheme (#1e1e1e)
- **Language Support**: Python, JavaScript, HTML, CSS, SQL, Bash, Java
- **Edit Mode**: Inline editor with language selector and filename field
- **Read Mode**: Beautiful read-only display with syntax highlighting and action buttons
- **Copy to Clipboard**: One-click copy button with confirmation
- **Fullscreen View**: View code in a separate window with syntax highlighting
- **Online Python Integration**: Direct link to https://www.online-python.com/ to run Python code

## JSON Structure

```json
{
  "type": "code",
  "language": "python",
  "title": "Example: Reading a CSV File",
  "filename": "read_csv.py",
  "code": "import pandas as pd\n\n# Load CSV file\ndf = pd.read_csv('data.csv')\n\n# Display first few rows\nprint(df.head())"
}
```

### Field Descriptions
- **type**: Must be `"code"`
- **language**: Programming language (`"python"`, `"javascript"`, `"html"`, `"css"`, `"sql"`, `"bash"`, `"java"`)
- **title**: Display title for the code block (optional)
- **filename**: Filename to display (e.g., `"script.py"`) (optional)
- **code**: The actual code content (supports multiline with `\n`)

## Adding Code Snippets in the Editor

### Method 1: Using the Palette (Recommended)
1. In edit mode, click the **💻 Code Snippet** button in the right sidebar
2. A new code block will be added
3. Select the programming language from the dropdown
4. Enter optional filename and title
5. Paste or type your code in the textarea

### Method 2: Manual JSON Entry
Add the JSON structure directly to your `content.json` file in the `blocks` array:

```json
{
  "url": "...",
  "title": "...",
  "blocks": [
    {
      "type": "heading",
      "text": "Python Basics"
    },
    {
      "type": "code",
      "language": "python",
      "title": "Hello World",
      "filename": "hello.py",
      "code": "print('Hello, World!')"
    }
  ]
}
```

## Viewing Code Snippets

### In Edit Mode
- Dark editor with language dropdown
- Textarea for editing code
- Real-time updates as you type
- Filename and title fields

### In Read Mode
- Carbon-style display with dark background
- Language badge showing selected language
- Action buttons:
  - **Copy**: Copies code to clipboard (shows confirmation)
  - **Fullscreen**: Opens code in new window
  - **Run** (Python only): Opens Online Python (online-python.com) for execution

## Example: Different Languages

### JavaScript
```json
{
  "type": "code",
  "language": "javascript",
  "title": "DOM Manipulation",
  "filename": "script.js",
  "code": "const element = document.getElementById('myDiv');\nelement.innerHTML = 'Hello, World!';"
}
```

### SQL
```json
{
  "type": "code",
  "language": "sql",
  "title": "Query All Students",
  "filename": "query.sql",
  "code": "SELECT * FROM students\nWHERE grade > 80\nORDER BY name ASC;"
}
```

### HTML
```json
{
  "type": "code",
  "language": "html",
  "title": "Basic HTML Structure",
  "filename": "index.html",
  "code": "<!DOCTYPE html>\n<html>\n<head>\n  <title>My Page</title>\n</head>\n<body>\n  <h1>Welcome</h1>\n</body>\n</html>"
}
```

## Syntax Highlighting

The code blocks use **Highlight.js** with the **Atom One Dark** theme, matching VS Code's default dark theme. Here's what gets highlighted:

### Syntax Colors (Atom One Dark Theme)
- **Keywords**: `#61afef` (blue) - e.g., `def`, `class`, `if`, `import`
- **Strings**: `#98c379` (green) - e.g., `"text"`, `'value'`
- **Numbers**: `#d19a66` (orange) - e.g., `42`, `3.14`
- **Functions**: `#61afef` (blue) - function names and calls
- **Comments**: `#5c6370` (gray) - `# comment`, `// comment`, `/* */`
- **Operators**: `#abb2bf` (light gray) - `+`, `-`, `=`, `etc.`

All major languages are automatically highlighted:
- **Python**: Keywords, imports, decorators, f-strings
- **JavaScript**: ES6 syntax, async/await, arrow functions
- **HTML**: Tags, attributes, entities
- **CSS**: Selectors, properties, values, pseudo-classes
- **SQL**: Keywords, functions, table names
- **Bash**: Commands, variables, pipes, redirects
- **Java**: Classes, methods, annotations

## Styling Notes

### Edit Mode Colors
- Background: `#1e1e1e` (VS Code dark)
- Text: `#d4d4d4`
- Input fields: Dark with light text
- Border: `#3e3e42`

### Read Mode Colors
- Header: `#2d2d30`
- Code background: `#1e1e1e`
- Text: `#d4d4d4`
- Filename color: `#9cdcfe` (blue)
- Language text: `#6a9955` (green)

## Tips & Best Practices

1. **Use Meaningful Titles**: Help students understand the code's purpose
2. **Include Filenames**: Especially useful when teaching file operations
3. **Break Up Long Code**: For readability, use multiple blocks for long examples
4. **Add Comments**: Include comments in the code itself for clarity
5. **Test Before Adding**: Verify code works before adding it to content

## Keyboard Shortcuts
- In edit mode, press Tab to indent (if focus is in the textarea)
- Ctrl+A to select all text in code editor
- Ctrl+C to copy (works with Copy button)

## Troubleshooting

**Code not saving?**
- Check that autosave is enabled (💾 status indicator)
- Verify no syntax errors in surrounding JSON

**Language not supported?**
- Currently supported: Python, JavaScript, HTML, CSS, SQL, Bash, Java
- More languages can be added by editing the language dropdown in `app.js`

**Copy button not working?**
- Check browser permissions for clipboard access
- Try using Ctrl+A then Ctrl+C manually

**Online Python (online-python.com) link not opening?**
- Verify JavaScript popups are allowed
- Check that you have Online Python (online-python.com) account access

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate the complete educational book structure for Python Basics."""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Base directory setup
BASE_DIR = Path(r"C:\Users\Colin\webscraper\data")
BOOK_FOLDER_NAME = "Book_python_basics"
BOOK_DIR = BASE_DIR / BOOK_FOLDER_NAME

def get_pages_data():
    pages = []
    
    # ----------------------------------------------------
    # Page 1: 6840 - Introduction to Python
    # ----------------------------------------------------
    p1_html = """
<h2>Welcome to Python Basics</h2>
<p>Python is one of the most popular, versatile, and beginner-friendly programming languages in the world today. Whether you aspire to build dynamic web applications, analyze vast datasets, develop artificial intelligence models, or automate tedious daily tasks, Python provides the foundational tools required to turn your ideas into working software.</p>

<h2>A Brief History and Philosophy</h2>
<p>Python was created by <strong>Guido van Rossum</strong> in the late 1980s and first released in 1991. The language was named after the British comedy troupe <em>Monty Python's Flying Circus</em>, reflecting the creator's belief that programming should be enjoyable, straightforward, and accessible.</p>
<p>At the core of Python's design philosophy is the emphasis on code readability and simplicity. This philosophy is encapsulated in <strong>The Zen of Python</strong> (PEP 20), which includes guiding principles such as:</p>
<ul>
  <li><em>Beautiful is better than ugly.</em></li>
  <li><em>Explicit is better than implicit.</em></li>
  <li><em>Simple is better than complex.</em></li>
  <li><em>Readability counts.</em></li>
</ul>

<h2>Why Choose Python?</h2>
<p>Beginners and seasoned professionals alike choose Python for several key reasons:</p>
<ol>
  <li><strong>Clean and Readable Syntax:</strong> Python code reads almost like everyday English, which dramatically reduces the cognitive load required to understand and maintain code structures.</li>
  <li><strong>Interpreted and Dynamically Typed:</strong> Unlike compiled languages like C++ or Java, Python executes line by line via the Python interpreter. You do not need to explicitly declare variable types, allowing for rapid experimentation and faster development cycles.</li>
  <li><strong>Extensive Standard Library:</strong> Often described as having "batteries included," Python comes equipped with a massive collection of pre-built modules for file system manipulation, network communication, mathematical operations, and more.</li>
  <li><strong>Thriving Global Community:</strong> With millions of active developers worldwide, finding solutions to common problems, comprehensive documentation, and open-source packages on the Python Package Index (PyPI) is practically effortless.</li>
</ol>

<h2>Your First Python Program</h2>
<p>In the tradition of computer science, your journey begins with the classic "Hello, World!" program. In Python, displaying text to the screen requires just a single line using the built-in <code>print()</code> function.</p>

<pre><code class="language-python">
# This is a single-line comment in Python
# Comments start with a hash (#) symbol and are ignored by the interpreter

print("Hello, World!")
print("Welcome to the exciting world of Python programming!")
</code></pre>

<p>When you execute this script, the Python interpreter reads the commands inside the parentheses and outputs the string literal directly to your terminal or console window.</p>

<h2>Key Takeaways</h2>
<ul>
  <li>Python is a high-level, interpreted programming language designed with readability and simplicity at its forefront.</li>
  <li>It is widely utilized across diverse domains, including Web Development, Data Science, Artificial Intelligence, and System Automation.</li>
  <li>The <code>print()</code> function is used to output data and messages to the screen.</li>
  <li>Comments in Python begin with the <code>#</code> character and serve as helpful documentation for developers.</li>
</ul>
""".strip()

    pages.append({
        "id": "6840",
        "title": "Introduction to Python",
        "topic_number": "P1.1.1",
        "section_title": "Section 1.1: Fundamentals & Setup",
        "unit_title": "Unit 1: Getting Started & Core Data",
        "content_html": p1_html
    })

    # ----------------------------------------------------
    # Page 2: 6841 - Setting Up Python Environment
    # ----------------------------------------------------
    p2_html = """
<h2>Configuring Your Development Environment</h2>
<p>Before writing and executing complex applications, you need a properly configured Python development environment on your machine. This module guides you through installing the Python interpreter, selecting a code editor, and understanding isolated virtual environments.</p>

<h2>1. Installing Python</h2>
<p>Python works seamlessly across Windows, macOS, and Linux operating systems. To install or upgrade Python:</p>
<ol>
  <li>Visit the official website at <strong>python.org/downloads</strong> and download the latest stable release of Python 3.x.</li>
  <li>Run the installer. <strong>CRITICAL FOR WINDOWS USERS:</strong> Ensure you check the box that says <em>"Add Python to PATH"</em> at the bottom of the installation dialog before clicking "Install Now". This registers Python globally across your command prompt.</li>
  <li>Verify the installation by opening your terminal (or Command Prompt) and running the following command:</li>
</ol>

<pre><code class="language-python">
# Type this into your terminal/command prompt to check Python version
python --version
</code></pre>

<h2>2. Interactive Shell vs. Script Files</h2>
<p>Python offers two primary modes for executing code:</p>
<ul>
  <li><strong>The Interactive REPL (Read-Eval-Print Loop):</strong> Typing <code>python</code> directly into your terminal opens an interactive shell where you can execute one line of code at a time. It is ideal for quick mathematical checks and exploring language behavior.</li>
  <li><strong>Script Execution:</strong> For full applications, you write and save code inside text files with the <code>.py</code> extension (e.g., <code>main.py</code>) and execute them via terminal using <code>python main.py</code>.</li>
</ul>

<h2>3. Selecting an Integrated Development Environment (IDE)</h2>
<p>While you can write Python code in any plain text editor, utilizing a specialized code editor or IDE significantly enhances productivity through syntax highlighting, code auto-completion, and integrated debugging tools. Highly recommended options include:</p>
<ul>
  <li><strong>Visual Studio Code (VS Code):</strong> A lightweight, powerful, and free code editor by Microsoft with an exceptional Python extension ecosystem.</li>
  <li><strong>PyCharm:</strong> A robust, feature-rich IDE specifically tailored for professional Python developers by JetBrains.</li>
  <li><strong>Jupyter Notebooks:</strong> An interactive web-based notebook interface favored heavily by data scientists and researchers for combining executable code with visualizations and markdown text.</li>
</ul>

<h2>4. Virtual Environments and Package Management</h2>
<p>As you build projects, you will rely on third-party libraries using Python's package manager, <code>pip</code>. To prevent dependency conflicts between different projects on the same computer, Python provides <strong>Virtual Environments (venv)</strong>.</p>
<p>A virtual environment creates a self-contained directory containing its own isolated Python interpreter and library packages.</p>

<pre><code class="language-python">
# Step 1: Create a new virtual environment named 'myenv'
python -m venv myenv

# Step 2: Activate the virtual environment (Windows Command Prompt)
myenv\\Scripts\\activate

# Step 2 (Alternative): Activate on macOS/Linux
source myenv/bin/activate

# Step 3: Install third-party packages into the isolated environment
pip install requests
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Always ensure Python is added to your system <code>PATH</code> during installation on Windows.</li>
  <li>Use <code>python --version</code> to confirm that Python 3.x is correctly installed and accessible from your command line.</li>
  <li>Adopt a modern editor like VS Code or PyCharm to leverage intelligent code completion and debugging assistance.</li>
  <li>Use virtual environments (<code>python -m venv</code>) to isolate dependencies and maintain clean project structures.</li>
</ul>
""".strip()

    pages.append({
        "id": "6841",
        "title": "Setting Up Python Environment",
        "topic_number": "P1.1.2",
        "section_title": "Section 1.1: Fundamentals & Setup",
        "unit_title": "Unit 1: Getting Started & Core Data",
        "content_html": p2_html
    })

    # ----------------------------------------------------
    # Page 3: 6842 - Variables and Data Types
    # ----------------------------------------------------
    p3_html = """
<h2>Understanding Variables in Python</h2>
<p>In programming, a <strong>variable</strong> acts as a symbolic container used to store data values in computer memory. Whenever you assign a value to a variable, you are creating a named label or pointer that allows you to retrieve, manipulate, and reference that specific information throughout your code.</p>

<p>Python uses the assignment operator (<code>=</code>) to bind a value to a variable name. Unlike static languages where variable types must be declared upfront, Python is <strong>dynamically typed</strong>. This means the Python interpreter automatically infers the data type based on the value assigned.</p>

<h2>Variable Naming Rules and Conventions</h2>
<p>To ensure code clarity and prevent syntax errors, adhere to Python's strict variable naming regulations and industry standard conventions:</p>
<ul>
  <li>Names can only contain letters (A-Z, a-z), numbers (0-9), and underscores (<code>_</code>).</li>
  <li>A variable name <strong>cannot</strong> begin with a number (e.g., <code>1st_user</code> is invalid; <code>user_1</code> is valid).</li>
  <li>Python is strictly case-sensitive (<code>score</code>, <code>Score</code>, and <code>SCORE</code> are three entirely separate variables).</li>
  <li>Avoid using reserved keywords such as <code>def</code>, <code>class</code>, <code>if</code>, <code>else</code>, <code>return</code>, or <code>import</code>.</li>
  <li><strong>Convention:</strong> Use <code>snake_case</code> (lowercase letters separated by underscores) for standard variables and function names (e.g., <code>total_amount</code>, <code>user_first_name</code>).</li>
</ul>

<h2>Core Built-in Primitive Data Types</h2>
<p>Every value in Python is an object belonging to a specific data type. Understanding primitive types is essential for performing accurate calculations and logic:</p>
<ol>
  <li><strong>Integers (<code>int</code>):</strong> Whole numbers without decimal points, both positive and negative (e.g., <code>42</code>, <code>-100</code>, <code>0</code>).</li>
  <li><strong>Floating-Point Numbers (<code>float</code>):</strong> Real numbers containing decimal points or exponential notation (e.g., <code>3.14159</code>, <code>-0.5</code>, <code>2.5e-3</code>).</li>
  <li><strong>Strings (<code>str</code>):</strong> Sequences of Unicode characters wrapped within single (<code>'</code>) or double (<code>"</code>) quotation marks (e.g., <code>"Python"</code>, <code>'Hello'</code>).</li>
  <li><strong>Booleans (<code>bool</code>):</strong> Logical binary values representing truthiness: exactly either <code>True</code> or <code>False</code> (capitalized).</li>
  <li><strong>NoneType (<code>None</code>):</strong> A special singleton object representing the absence of a value or a null pointer.</li>
</ol>

<h2>Inspecting and Converting Types (Type Casting)</h2>
<p>You can dynamically check the type of any variable at runtime using the built-in <code>type()</code> function. When you need to convert data between differing types, Python provides explicit casting functions such as <code>int()</code>, <code>float()</code>, and <code>str()</code>.</p>

<pre><code class="language-python">
# Creating variables of different primitive types
user_age = 25               # int
account_balance = 1450.75   # float
user_name = 'Alice'         # str
is_active = True            # bool
profile_data = None         # NoneType

# Inspecting variable data types at runtime
print(type(user_age))        # Output: <class 'int'>
print(type(account_balance)) # Output: <class 'float'>

# Explicit Type Casting (Conversion)
age_string = str(user_age)   # Converts integer 25 into string '25'
balance_int = int(account_balance) # Truncates float 1450.75 into integer 1450

print(age_string + " years old")   # Output: 25 years old
print(balance_int)                 # Output: 1450
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Variables are created automatically upon value assignment using the <code>=</code> operator.</li>
  <li>Use descriptive <code>snake_case</code> names and respect Python's case sensitivity.</li>
  <li>Python dynamically handles core types including <code>int</code>, <code>float</code>, <code>str</code>, <code>bool</code>, and <code>NoneType</code>.</li>
  <li>Use <code>type()</code> to inspect object classes and functions like <code>int()</code>, <code>float()</code>, and <code>str()</code> for type conversions.</li>
</ul>
""".strip()

    pages.append({
        "id": "6842",
        "title": "Variables and Data Types",
        "topic_number": "P1.2.1",
        "section_title": "Section 1.2: Variables & Basic Operations",
        "unit_title": "Unit 1: Getting Started & Core Data",
        "content_html": p3_html
    })

    # ----------------------------------------------------
    # Page 4: 6843 - Numbers and Arithmetic
    # ----------------------------------------------------
    p4_html = """
<h2>Working with Numbers in Python</h2>
<p>Numerical computation is foundational to software engineering, scientific data analysis, financial modeling, and game development. Python provides comprehensive built-in support for mathematical operations on integer and floating-point numbers without requiring complex type configurations.</p>

<h2>Arithmetic Operators</h2>
<p>Python includes seven standard arithmetic operators that allow you to perform basic and advanced mathematical calculations cleanly:</p>
<ul>
  <li><strong>Addition (<code>+</code>):</strong> Adds two operands together (<code>10 + 5</code> results in <code>15</code>).</li>
  <li><strong>Subtraction (<code>-</code>):</strong> Subtracts the second operand from the first (<code>10 - 5</code> results in <code>5</code>).</li>
  <li><strong>Multiplication (<code>*</code>):</strong> Multiplies two operands (<code>10 * 5</code> results in <code>50</code>).</li>
  <li><strong>True Division (<code>/</code>):</strong> Divides the first operand by the second, <em>always</em> returning a floating-point result (<code>10 / 4</code> results in <code>2.5</code>).</li>
  <li><strong>Floor Division / Integer Division (<code>//</code>):</strong> Divides operands and rounds the result down to the nearest whole integer (<code>10 // 4</code> results in <code>2</code>).</li>
  <li><strong>Modulo / Remainder (<code>%</code>):</strong> Returns the remainder after integer division (<code>10 % 3</code> results in <code>1</code>). This is especially useful for checking even/odd numbers.</li>
  <li><strong>Exponentiation (<code>**</code>):</strong> Raises the first operand to the power of the second (<code>2 ** 3</code> results in <code>8</code>).</li>
</ul>

<h2>Operator Precedence (PEMDAS)</h2>
<p>When evaluating complex expressions containing multiple operators, Python strictly follows the standard mathematical order of operations, commonly memorized via the acronym <strong>PEMDAS</strong>:</p>
<ol>
  <li><strong>P</strong>arentheses <code>()</code> (Expressions grouped in parentheses are evaluated first)</li>
  <li><strong>E</strong>xponents <code>**</code></li>
  <li><strong>M</strong>ultiplication <code>*</code>, <strong>D</strong>ivision <code>/</code>, Floor Division <code>//</code>, and Modulo <code>%</code> (Evaluated left-to-right)</li>
  <li><strong>A</strong>ddition <code>+</code> and <strong>S</strong>ubtraction <code>-</code> (Evaluated left-to-right)</li>
</ol>

<h2>Built-in Math Functions and the Math Module</h2>
<p>In addition to basic operators, Python provides powerful built-in mathematical functions such as <code>abs()</code> (absolute value), <code>round()</code> (rounding to decimal places), <code>min()</code>, and <code>max()</code>. For advanced scientific functions like logarithms, trigonometry, and constants, you import the standard <code>math</code> module.</p>

<pre><code class="language-python">
import math

# Demonstrating Arithmetic Operators
x = 17
y = 5

print("True Division:", x / y)      # Output: 3.4
print("Floor Division:", x // y)    # Output: 3
print("Remainder (Modulo):", x % y) # Output: 2
print("Exponentiation:", 2 ** 8)    # Output: 256

# Operator Precedence Demonstration
result = (10 + 2) * 3 ** 2 - 8 / 2
# Evaluation step-by-step: 12 * 9 - 4.0 = 108 - 4.0 = 104.0
print("Precedence Result:", result)  # Output: 104.0

# Built-in and Math Module Functions
print("Absolute Value:", abs(-42.5))          # Output: 42.5
print("Rounded to 2 decimals:", round(3.14159, 2)) # Output: 3.14
print("Square Root:", math.sqrt(144))         # Output: 12.0
print("Ceiling (round up):", math.ceil(4.1))  # Output: 5
print("Floor (round down):", math.floor(4.9)) # Output: 4
print("Value of Pi:", math.pi)                # Output: 3.141592653589793
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Use true division (<code>/</code>) when you require exact decimal floats, and floor division (<code>//</code>) for integer results.</li>
  <li>The modulo operator (<code>%</code>) is invaluable for calculating remainders, wrapping indices, and determining divisibility.</li>
  <li>Always use parentheses <code>()</code> to make complex mathematical precedence explicit and readable.</li>
  <li>Import the built-in <code>math</code> module to access advanced functions like <code>math.sqrt()</code>, <code>math.ceil()</code>, and constants like <code>math.pi</code>.</li>
</ul>
""".strip()

    pages.append({
        "id": "6843",
        "title": "Numbers and Arithmetic",
        "topic_number": "P1.2.2",
        "section_title": "Section 1.2: Variables & Basic Operations",
        "unit_title": "Unit 1: Getting Started & Core Data",
        "content_html": p4_html
    })

    # ----------------------------------------------------
    # Page 5: 6844 - Strings and Text Operations
    # ----------------------------------------------------
    p5_html = """
<h2>Mastering Strings and Text Manipulation</h2>
<p>A <strong>string</strong> (<code>str</code>) in Python represents an immutable sequence of Unicode characters used to store and manipulate textual data. Whether parsing user input, formatting web pages, processing files, or cleaning data, string manipulation is one of the most frequent operations in daily programming.</p>

<h2>Creating Strings and Escape Sequences</h2>
<p>Strings can be enclosed in either single quotes (<code>'...'</code>) or double quotes (<code>"..."</code>) with identical behavior. For multi-line text blocks or docstrings, you use triple quotes (<code>'''...'''</code> or <code>\"\"\"...\"\"\"</code>). When strings contain special formatting characters or quotes inside them, you utilize <strong>escape sequences</strong> preceded by a backslash (<code>\\</code>):</p>
<ul>
  <li><code>\\n</code> : Inserts a new line character.</li>
  <li><code>\\t</code> : Inserts a horizontal tab.</li>
  <li><code>\\'</code> or <code>\\"</code> : Escapes single/double quotation marks inside a string.</li>
  <li><code>\\\\</code> : Escapes a literal backslash character.</li>
</ul>

<h2>String Indexing and Slicing</h2>
<p>Because strings are ordered sequences, every character occupies a specific position called an index. Python employs zero-based indexing, where the first character resides at index <code>0</code>. Additionally, Python supports negative indexing, where index <code>-1</code> represents the very last character.</p>
<p><strong>String Slicing</strong> allows you to extract substrings using the colon syntax: <code>string[start:stop:step]</code>. Note that the <code>start</code> index is inclusive, while the <code>stop</code> index is exclusive.</p>

<h2>Essential String Methods</h2>
<p>Since strings are immutable (their underlying characters cannot be changed after creation), string methods always return a new, modified copy of the string without altering the original:</p>
<ul>
  <li><code>.upper()</code> and <code>.lower()</code> : Convert characters to uppercase or lowercase.</li>
  <li><code>.strip()</code> : Removes leading and trailing whitespace (or specified characters).</li>
  <li><code>.split(delimiter)</code> : Splits a string into a list of substrings based on a delimiter.</li>
  <li><code>.replace(old, new)</code> : Replaces occurrences of a substring with a new string.</li>
  <li><code>.find(substring)</code> : Returns the lowest index where the substring is found (-1 if missing).</li>
</ul>

<h2>Modern String Formatting with f-Strings</h2>
<p>Introduced in Python 3.6, <strong>Formatted String Literals (f-strings)</strong> represent the cleanest and most efficient way to embed Python variables and expressions directly inside string literals by prefixing the string with the letter <code>f</code> and enclosing expressions inside curly braces <code>{}</code>.</p>

<pre><code class="language-python">
# String Creation and Multiline Strings
course_name = "Python Programming"
raw_quote = 'Guido said, "Readability counts."'

# Indexing and Slicing Demonstrations
text = "Hello, World!"
print("First character:", text[0])       # Output: H
print("Last character:", text[-1])       # Output: !
print("Slice [0:5]:", text[0:5])         # Output: Hello
print("Slice with step [::2]:", text[::2]) # Output: Hlo ol!

# String Methods
dirty_string = "   PYTHON basics course   "
clean_string = dirty_string.strip().upper()
print("Cleaned String:", clean_string)   # Output: PYTHON BASICS COURSE

words = "apple,banana,cherry".split(",")
print("Split into list:", words)         # Output: ['apple', 'banana', 'cherry']

# Modern f-String Formatting
student = "Colin"
score = 95.876
formatted_msg = f"Student {student} achieved a final score of {score:.1f}%!"
print(formatted_msg) # Output: Student Colin achieved a final score of 95.9%!
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Strings are immutable sequences indexed from <code>0</code> (left-to-right) and <code>-1</code> (right-to-left).</li>
  <li>Use slicing syntax <code>[start:stop:step]</code> to extract specific substrings efficiently.</li>
  <li>Methods like <code>.strip()</code>, <code>.upper()</code>, <code>.split()</code>, and <code>.replace()</code> return new string copies.</li>
  <li>Prefer modern <code>f-strings</code> (<code>f"..."</code>) for clean, readable interpolation of variables and expressions.</li>
</ul>
""".strip()

    pages.append({
        "id": "6844",
        "title": "Strings and Text Operations",
        "topic_number": "P1.2.3",
        "section_title": "Section 1.2: Variables & Basic Operations",
        "unit_title": "Unit 1: Getting Started & Core Data",
        "content_html": p5_html
    })

    # ----------------------------------------------------
    # Page 6: 6845 - Lists and Collections
    # ----------------------------------------------------
    p6_html = """
<h2>Introduction to Lists in Python</h2>
<p>When building software, you rarely work with isolated single values. Instead, you manage groups of related items—such as a list of registered users, items in a shopping cart, or sensory readings. In Python, the <strong>List</strong> is the most fundamental and versatile sequence collection.</p>
<p>A list is an <strong>ordered, mutable sequence</strong> of items enclosed within square brackets <code>[...]</code>, with individual elements separated by commas. Lists can store elements of mixed primitive data types (integers, strings, floats, and even nested sub-lists).</p>

<h2>Accessing and Modifying List Elements</h2>
<p>Because lists maintain strict ordering, you can access items via zero-based indexing and slicing exactly like strings. Crucially, unlike strings, lists are <strong>mutable</strong>—you can modify, replace, or re-assign elements in place at a specific index without creating an entirely new list object.</p>

<h2>Key List Methods for Adding and Removing Items</h2>
<p>Python equips list objects with a rich suite of built-in methods for dynamic collection manipulation:</p>
<ul>
  <li><code>.append(item)</code> : Adds a single item to the very end of the list.</li>
  <li><code>.insert(index, item)</code> : Inserts an item at a specific target index position.</li>
  <li><code>.extend(iterable)</code> : Appends all items from another sequence to the end of the list.</li>
  <li><code>.remove(item)</code> : Removes the first matching value encountered in the list (raises ValueError if absent).</li>
  <li><code>.pop(index)</code> : Removes and returns the item at the specified index (defaults to popping the last item `index -1`).</li>
  <li><code>.clear()</code> : Empties the list entirely, leaving an empty bracket `[]`.</li>
</ul>

<h2>Sorting, Reversing, and List Comprehensions</h2>
<p>You can sort elements in place using <code>.sort()</code> or generate a newly sorted list copy using the built-in <code>sorted(list)</code> function. To reverse order, use <code>.reverse()</code>.</p>
<p>One of Python's most powerful, elegant features is the <strong>List Comprehension</strong>. It provides a concise, one-line syntax for generating new lists by applying expressions and filtering criteria across existing iterables.</p>

<pre><code class="language-python">
# Creating and modifying lists
fruits = ["apple", "banana", "cherry", "date"]
print("Original List:", fruits)

# Indexing and Mutable Reassignment
fruits[1] = "blueberry"           # Modifying item at index 1
print("After Modification:", fruits) # Output: ['apple', 'blueberry', 'cherry', 'date']

# Dynamic Additions and Removals
fruits.append("elderberry")       # Adds to the end
fruits.insert(0, "apricot")       # Inserts at the very beginning
popped_item = fruits.pop()        # Removes and returns 'elderberry'
fruits.remove("cherry")           # Removes first occurrence of 'cherry'

print("Modified Fruits:", fruits) # Output: ['apricot', 'apple', 'blueberry', 'date']

# Sorting
numbers = [42, 12, 89, 3, 27]
numbers.sort()                    # Sorts numbers in-place in ascending order
print("Sorted Numbers:", numbers) # Output: [3, 12, 27, 42, 89]

# Concise List Comprehension: Square all even numbers between 0 and 9
squares = [x ** 2 for x in range(10) if x % 2 == 0]
print("List Comprehension Squares:", squares) # Output: [0, 4, 16, 36, 64]
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Lists are ordered, mutable collections enclosed in square brackets <code>[...]</code> capable of holding mixed data types.</li>
  <li>Use methods like <code>.append()</code>, <code>.insert()</code>, <code>.pop()</code>, and <code>.remove()</code> to dynamically manage elements.</li>
  <li>Differentiate between in-place modification (<code>my_list.sort()</code>) and copy generation (<code>sorted(my_list)</code>).</li>
  <li>Leverage list comprehensions (<code>[expr for x in seq if cond]</code>) for clean, readable, high-performance sequence filtering.</li>
</ul>
""".strip()

    pages.append({
        "id": "6845",
        "title": "Lists and Collections",
        "topic_number": "P2.1.1",
        "section_title": "Section 2.1: Collections",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p6_html
    })

    # ----------------------------------------------------
    # Page 7: 6846 - Tuples and Dictionaries
    # ----------------------------------------------------
    p7_html = """
<h2>Beyond Lists: Tuples and Dictionaries</h2>
<p>While lists excel at managing ordered sequences of items that need frequent modification, Python offers specialized collection structures optimized for immutability and fast key-based lookups: <strong>Tuples</strong> and <strong>Dictionaries</strong>.</p>

<h2>1. Tuples: Immutable Sequences</h2>
<p>A <strong>Tuple</strong> is an ordered sequence of elements enclosed in parentheses <code>(...)</code>. The defining characteristic of a tuple is its <strong>immutability</strong>—once a tuple is created, its elements cannot be added, removed, or changed. Why use tuples instead of lists?</p>
<ul>
  <li><strong>Performance and Safety:</strong> Tuples consume slightly less memory and iterate faster than lists while protecting constant data against accidental modification.</li>
  <li><strong>Dictionary Keys:</strong> Because tuples are immutable and hashable, they can be used as keys inside dictionaries (unlike lists).</li>
  <li><strong>Tuple Unpacking:</strong> Python allows you to cleanly assign multiple tuple elements across individual variable names in a single line.</li>
</ul>

<h2>2. Dictionaries: Key-Value Mapping</h2>
<p>A <strong>Dictionary</strong> (<code>dict</code>) is an unordered (insertion-ordered in Python 3.7+), mutable collection of structured <strong>key-value pairs</strong> enclosed within curly braces <code>{...}</code>. Instead of searching by numerical index, you access dictionary values instantly using unique keys (such as strings or numbers).</p>

<h2>Core Dictionary Operations and Methods</h2>
<p>Dictionaries provide ultra-fast hash table lookups and versatile methods for data inspection:</p>
<ul>
  <li><strong>Accessing Values:</strong> Bracket notation <code>user["name"]</code> retrieves the value but raises a <code>KeyError</code> if the key is missing. The safe alternative, <code>user.get("name", default)</code>, gracefully returns a default value if the key does not exist.</li>
  <li><code>.keys()</code>, <code>.values()</code>, and <code>.items()</code> : Return iterable views of the dictionary's keys, values, and `(key, value)` tuple pairs respectively.</li>
  <li><code>.update(other_dict)</code> : Merges another dictionary or key-value iterable into the existing dictionary.</li>
</ul>

<pre><code class="language-python">
# Tuple Creation and Unpacking
dimensions = (1920, 1080)
width, height = dimensions        # Clean Tuple Unpacking
print(f"Screen Resolution: {width}x{height}")

# Creating and Working with Dictionaries
user_profile = {
    "username": "coder_colin",
    "email": "colin@example.com",
    "access_level": "admin",
    "login_count": 42
}

# Safe Value Retrieval using .get()
print("Username:", user_profile.get("username"))
print("Phone:", user_profile.get("phone", "Not Provided")) # Graceful fallback

# Adding and Modifying Key-Value Pairs
user_profile["login_count"] += 1   # Modifying existing key
user_profile["is_verified"] = True # dynamically adding new key-value pair

# Iterating over Dictionary Items (Key-Value Pairs)
for key, value in user_profile.items():
    print(f"  -> {key}: {value}")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Tuples <code>(...)</code> are immutable sequences optimized for constant data integrity, multiple return values, and unpacking.</li>
  <li>Dictionaries <code>{key: value}</code> map unique hashable keys to arbitrary objects, providing near-instant lookup speeds.</li>
  <li>Use <code>dict.get(key, default)</code> to safely access dictionary properties without crashing on missing keys.</li>
  <li>Use <code>.items()</code> to cleanly iterate over both keys and values within a dictionary simultaneously.</li>
</ul>
""".strip()

    pages.append({
        "id": "6846",
        "title": "Tuples and Dictionaries",
        "topic_number": "P2.1.2",
        "section_title": "Section 2.1: Collections",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p7_html
    })

    # ----------------------------------------------------
    # Page 8: 6847 - Boolean Logic and Comparisons
    # ----------------------------------------------------
    p8_html = """
<h2>Boolean Logic and Comparison Operators</h2>
<p>To write dynamic, intelligent programs, software must evaluate conditions and make automated decisions. In Python, decision-making is underpinned by boolean algebra, comparison operators, and logical operators that evaluate expressions down to either <code>True</code> or <code>False</code>.</p>

<h2>1. Comparison (Relational) Operators</h2>
<p>Comparison operators compare two values and produce a boolean result. Python supports all standard relational comparisons, and uniquely allows clean chaining of mathematical comparisons:</p>
<ul>
  <li><code>==</code> : Equal to (checks equality of values, do not confuse with assignment <code>=</code>).</li>
  <li><code>!=</code> : Not equal to.</li>
  <li><code><</code> and <code>></code> : Less than and Greater than.</li>
  <li><code><=</code> and <code>>=</code> : Less than or equal to, and Greater than or equal to.</li>
  <li><strong>Chained Syntax:</strong> You can write clean ranges such as <code>0 <= age <= 120</code> directly.</li>
</ul>

<h2>2. Logical Operators and Short-Circuit Evaluation</h2>
<p>Python provides three English-keyword logical operators to combine multiple boolean expressions:</p>
<ol>
  <li><code>and</code> : Returns <code>True</code> only if <strong>both</strong> operands evaluate to True.</li>
  <li><code>or</code> : Returns <code>True</code> if <strong>at least one</strong> operand evaluates to True.</li>
  <li><code>not</code> : Unary operator that inverts the boolean state (`not True` becomes `False`).</li>
</ol>
<p><strong>Short-Circuit Evaluation:</strong> For performance and safety, Python evaluates logical expressions from left to right and stops as soon as the outcome is determined. In an <code>and</code> expression, if the left operand is False, Python skips evaluating the right operand completely.</p>

<h2>3. Identity and Membership Operators</h2>
<p>Python includes two specialized operator pairs for object validation and collection inspection:</p>
<ul>
  <li><strong>Identity (`is`, `is not`):</strong> Checks whether two variables point to the exact same object in physical computer memory (`id(a) == id(b)`). Always use <code>is None</code> when checking for singleton null objects.</li>
  <li><strong>Membership (`in`, `not in`):</strong> Checks whether a value exists inside an iterable container (such as a string, list, tuple, or dictionary keys).</li>
</ul>

<h2>4. Truthy and Falsy Values</h2>
<p>In Python, every object has an inherent boolean truth value when evaluated inside conditional statements. The following objects inherently evaluate to <strong>False</strong> (termed <em>Falsy</em>):</p>
<ul>
  <li>The boolean constant <code>False</code> and singleton <code>None</code>.</li>
  <li>Any numerical zero: <code>0</code>, <code>0.0</code>.</li>
  <li>Any empty sequence or collection: empty string <code>""</code>, empty list <code>[]</code>, empty tuple <code>()</code>, or empty dict <code>{}</code>.</li>
</ul>
<p>Almost all other objects containing data or non-zero numbers evaluate to <strong>True</strong> (termed <em>Truthy</em>).</p>

<pre><code class="language-python">
# Comparison Chaining
score = 85
is_valid_grade = 0 <= score <= 100
print("Is valid grade range?", is_valid_grade) # Output: True

# Logical Short-Circuit Evaluation and Membership
user_role = "editor"
permissions = ["admin", "editor", "moderator"]

has_access = (user_role in permissions) and (score > 80)
print("Has access granted?", has_access)       # Output: True

# Identity Testing vs Equality
data_list = [1, 2, 3]
copy_list = [1, 2, 3]

print("Value Equality (==):", data_list == copy_list) # Output: True
print("Memory Identity (is):", data_list is copy_list) # Output: False (different objects in memory)

# Truthy and Falsy Check
user_input = "" # Empty string is inherently Falsy
if not user_input:
    print("Warning: User provided no input text!")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Differentiate clearly between value comparison (<code>==</code>) and variable assignment (<code>=</code>).</li>
  <li>Logical keywords <code>and</code>, <code>or</code>, and <code>not</code> utilize short-circuiting to optimize performance and prevent errors.</li>
  <li>Use identity operator <code>is</code> when checking against singletons like <code>None</code>, and <code>==</code> for value equality.</li>
  <li>Leverage Python's natural Truthy/Falsy rules to write clean, pythonic conditional checks on containers.</li>
</ul>
""".strip()

    pages.append({
        "id": "6847",
        "title": "Boolean Logic and Comparisons",
        "topic_number": "P2.2.1",
        "section_title": "Section 2.2: Logic & Conditionals",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p8_html
    })

    # ----------------------------------------------------
    # Page 9: 6848 - Conditional Statements (if/else)
    # ----------------------------------------------------
    p9_html = """
<h2>Controlling Flow with Conditional Statements</h2>
<p>While scripts normally execute sequentially from top to bottom, real-world software requires branching paths that adapt behavior based on dynamic data, user inputs, and environmental constraints. Python implements branching through <strong>Conditional Statements (if / elif / else)</strong>.</p>

<h2>The Syntax and the Indentation Rule</h2>
<p>Unlike languages that use curly braces <code>{...}</code> to group blocks of code, Python enforces structure via <strong>whitespace indentation</strong>. When creating a conditional block, the header line must end with a colon (<code>:</code>), and every line inside the subordinate block must be indented uniformly (the industry standard is <strong>4 spaces</strong> per indentation level).</p>

<h2>Building Branching Logic (if / elif / else)</h2>
<p>A complete conditional structure can contain three interconnected components:</p>
<ol>
  <li><code>if condition:</code> : The primary check. If this boolean expression evaluates to True, its indented code block executes and the rest of the conditional chain is skipped entirely.</li>
  <li><code>elif condition:</code> : Short for "else if". If previous checks were False, Python evaluates this branch. You can include as many <code>elif</code> blocks as needed.</li>
  <li><code>else:</code> : The final fallback block. If every single preceding check evaluated to False, the code inside the <code>else</code> block guarantees execution.</li>
</ol>

<h2>Ternary Conditional Expressions</h2>
<p>For simple, single-line variable assignments dependent on a condition, Python provides an elegant inline construct known as a <strong>Ternary Conditional Expression</strong>:</p>
<p><code>variable = value_if_true if condition else value_if_false</code></p>

<h2>Match-Case (Structural Pattern Matching)</h2>
<p>Introduced in Python 3.10, the <code>match-case</code> statement provides a clean, highly expressive structural pattern matching syntax analogous to switch/case statements in other languages, excellent for comparing a variable against numerous discrete literal values or data structures.</p>

<pre><code class="language-python">
# Standard Multi-branch Conditional Structure
temperature = 22

if temperature >= 30:
    print("Status: It is a hot summer day. Stay hydrated!")
elif 18 <= temperature < 30:
    print("Status: The weather is pleasant and comfortable.")
elif 0 <= temperature < 18:
    print("Status: It is cool outside. Grab a light jacket.")
else:
    print("Status: Freezing temperatures detected!")

# Nested Conditionals and Validation
is_authenticated = True
has_subscription = False

if is_authenticated:
    if has_subscription:
        print("Access granted: Welcome to the premium dashboard.")
    else:
        print("Notice: Please upgrade your account to access paid features.")
else:
    print("Redirect: Please log in to continue.")

# Concise Inline Ternary Conditional Expression
age = 20
status_label = "Adult" if age >= 18 else "Minor"
print("User classification:", status_label) # Output: Adult

# Python 3.10+ Structural Pattern Matching (match-case)
command = "save"
match command:
    case "start":
        print("System starting up...")
    case "stop" | "exit":
        print("Shutting down processes...")
    case "save":
        print("Data successfully committed to disk.")
    case _: # Wildcard underscore matches anything else (default case)
        print("Error: Unrecognized command keyword.")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Python relies strictly on colons (<code>:</code>) and uniform 4-space indentation to define conditional code blocks.</li>
  <li>Use <code>elif</code> to chain mutually exclusive alternatives and <code>else</code> to catch all remaining fallback scenarios.</li>
  <li>Use inline ternary expressions (<code>val = x if cond else y</code>) to keep simple conditional variable assignments concise.</li>
  <li>Adopt Python 3.10+ <code>match-case</code> syntax when checking a single variable against multiple exact literal values.</li>
</ul>
""".strip()

    pages.append({
        "id": "6848",
        "title": "Conditional Statements (if/else)",
        "topic_number": "P2.2.2",
        "section_title": "Section 2.2: Logic & Conditionals",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p9_html
    })

    # ----------------------------------------------------
    # Page 10: 6849 - Loops - For Loops
    # ----------------------------------------------------
    p10_html = """
<h2>Definite Iteration with For Loops</h2>
<p>One of the immense strengths of computers is their ability to perform repetitive operations thousands of times per second without fatigue or error. In Python, the primary mechanism for executing repetitive tasks across a known sequence of items is the <strong>For Loop</strong>.</p>
<p>Unlike C-style languages that require indexing counters (`for i=0; i<n; i++`), Python's <code>for item in iterable:</code> syntax acts as a direct collection iterator. It automatically extracts each successive element from an iterable (like a list, tuple, string, or dictionary) and assigns it to the loop variable.</p>

<h2>Generating Number Sequences with range()</h2>
<p>When you need to loop a specific number of times or generate a sequence of integers, you use the built-in <code>range()</code> function. The function accepts up to three arguments: <code>range(start, stop, step)</code>:</p>
<ul>
  <li><code>start</code> : The starting integer (defaults to <code>0</code> if omitted).</li>
  <li><code>stop</code> : The target boundary integer (strictly <strong>exclusive</strong>).</li>
  <li><code>step</code> : The increment between numbers (defaults to <code>1</code>; can be negative for countdowns).</li>
</ul>

<h2>Looping over Dictionaries and Advanced Utilities</h2>
<p>Iterating directly over a dictionary defaults to looping through its keys. To iterate over both keys and values simultaneously, call the <code>.items()</code> method.</p>
<p>Python also provides two indispensable helper utilities for clean loop engineering:</p>
<ol>
  <li><code>enumerate(iterable, start=0)</code> : Yields pairs containing the numerical index count alongside the actual item value, eliminating the need to manually track index variables.</li>
  <li><code>zip(iter1, iter2, ...)</code> : Combines two or more iterables in parallel, yielding tuples containing one element from each sequence per iteration step.</li>
</ol>

<pre><code class="language-python">
# 1. Basic Iteration over a List of Strings
technologies = ["Python", "JavaScript", "SQL", "Docker"]
for tech in technologies:
    print("Mastering skill:", tech)

# 2. Using range() for Numerical Iteration and Countdowns
print("\\nCountdown Sequence:")
for count in range(5, 0, -1): # Start at 5, stop before 0, decrement by -1
    print(f"  T-minus {count}...")
print("Launch!")

# 3. Iterating over Dictionary Key-Value Pairs
employee_roles = {"Alice": "Backend Developer", "Bob": "Data Scientist", "Eve": "DevOps Engineer"}
print("\\nTeam Roster:")
for name, role in employee_roles.items():
    print(f"  - {name} serves as the {role}")

# 4. Using enumerate() to get Automatic Index Numbers
print("\\nNumbered Task Queue:")
tasks = ["Download raw data", "Clean dataframes", "Train ML model"]
for index, task in enumerate(tasks, start=1):
    print(f"  Step #{index}: {task}")

# 5. Using zip() to Iterate Multiple Lists in Parallel
names = ["Alice", "Bob", "Charlie"]
scores = [98, 85, 91]
for name, score in zip(names, scores):
    print(f"  Result -> {name}: {score} points")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Python's <code>for item in iterable:</code> loop directly traverses items in lists, tuples, strings, and sets.</li>
  <li>Use <code>range(start, stop, step)</code> to generate controlled numerical sequences and counter loops.</li>
  <li>Always use <code>enumerate(collection)</code> when your logic requires both the item's index position and value.</li>
  <li>Use <code>zip()</code> to cleanly and safely traverse multiple parallel sequences together in lockstep.</li>
</ul>
""".strip()

    pages.append({
        "id": "6849",
        "title": "Loops - For Loops",
        "topic_number": "P2.3.1",
        "section_title": "Section 2.3: Iteration & Loops",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p10_html
    })

    # ----------------------------------------------------
    # Page 11: 6850 - Loops - While Loops
    # ----------------------------------------------------
    p11_html = """
<h2>Indefinite Iteration with While Loops</h2>
<p>While <code>for</code> loops excel when the exact number of iterations or container size is known in advance, many programming scenarios require looping until a dynamic condition changes or an external event occurs. For these <strong>indefinite iteration</strong> workflows, Python provides the <strong>While Loop</strong>.</p>
<p>The syntax <code>while condition:</code> continuously re-evaluates the boolean condition at the start of every iteration. As long as the expression evaluates to <code>True</code>, the indented block executes. Once the condition evaluates to <code>False</code>, the loop terminates immediately.</p>

<h2>Preventing Infinite Loops</h2>
<p>Because while loops depend on dynamic conditions, failing to update the variables tested in the loop header will cause an <strong>Infinite Loop</strong> that freezes your program. Always ensure that the internal logic progresses toward making the condition <code>False</code> (or encounters an explicit exit statement).</p>

<h2>Loop Control Statements: break, continue, and pass</h2>
<p>Python provides three specialized control keywords that allow you to modify the natural execution flow inside any loop structure (both <code>while</code> and <code>for</code> loops):</p>
<ul>
  <li><code>break</code> : Instantly terminates the entire loop and jumps execution to the first statement outside the loop block.</li>
  <li><code>continue</code> : Skips the remainder of the current iteration block and immediately jumps back up to re-evaluate the loop header condition.</li>
  <li><code>pass</code> : A null placeholder statement that does nothing. Used when syntax rules require an indented code block (such as inside TODO stubs or empty exception handlers).</li>
</ul>

<h2>The Unique while-else Construct</h2>
<p>Python features a unique <code>else</code> clause that can be attached to loop structures. The indented block under `else:` executes exactly once when the loop completes normally—specifically, when the while condition becomes False. Crucially, if the loop is aborted prematurely via a <code>break</code> statement, the <code>else</code> block is skipped entirely.</p>

<pre><code class="language-python">
# 1. Standard While Loop with Variable Progression
attempt_count = 1
max_attempts = 4

while attempt_count <= max_attempts:
    print(f"Connecting to server... (Attempt {attempt_count}/{max_attempts})")
    attempt_count += 1
print("Connection sequence completed.\\n")

# 2. Interactive Menu / Event Loop using 'break' and 'continue'
simulated_user_inputs = ["invalid_command", "status", "quit", "extra_input"]
input_index = 0

while True: # Infinite loop header controlled internally via break
    # Simulate retrieving user input
    current_input = simulated_user_inputs[input_index]
    input_index += 1
    
    if current_input == "quit":
        print("System: 'quit' command received. Exiting application loop.")
        break # Aborts loop immediately
        
    if current_input == "invalid_command":
        print("System: Unrecognized input. Skipping to next cycle...")
        continue # Skips below code, starts next iteration
        
    print(f"System: Processing valid command -> '{current_input}'")

# 3. Demonstrating the while-else Construct for Search Operations
search_target = 99
numbers_pool = [12, 45, 67, 88, 23]
idx = 0

while idx < len(numbers_pool):
    if numbers_pool[idx] == search_target:
        print(f"Success: Target {search_target} found at index {idx}!")
        break
    idx += 1
else:
    # This block executes ONLY because the loop finished without hitting 'break'
    print(f"Search Complete: Target {search_target} does not exist in pool.")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Use <code>while condition:</code> for indefinite iteration where loops depend on user input, game ticks, or external state.</li>
  <li>Always verify internal loop variables update reliably to prevent application-freezing infinite loops.</li>
  <li>Use <code>break</code> to abort loops early and <code>continue</code> to skip directly to the next loop iteration check.</li>
  <li>The loop <code>else</code> block executes only upon natural completion when no <code>break</code> statement triggered.</li>
</ul>
""".strip()

    pages.append({
        "id": "6850",
        "title": "Loops - While Loops",
        "topic_number": "P2.3.2",
        "section_title": "Section 2.3: Iteration & Loops",
        "unit_title": "Unit 2: Data Structures & Control Flow",
        "content_html": p11_html
    })

    # ----------------------------------------------------
    # Page 12: 6851 - Functions and Parameters
    # ----------------------------------------------------
    p12_html = """
<h2>Introduction to Modular Functions</h2>
<p>As applications grow in complexity, writing thousands of lines of sequential code becomes unmaintainable. To organize code effectively, software engineers rely on the core principle of <strong>DRY (Don't Repeat Yourself)</strong> by bundling reusable blocks of logic into self-contained modules called <strong>Functions</strong>.</p>
<p>In Python, you define a custom function using the <code>def</code> keyword followed by the function name, parentheses containing optional parameters, and a colon (<code>:</code>). The subordinate block contains the executable statements alongside an optional docstring explaining the function's purpose.</p>

<h2>Parameters and Argument Passing Styles</h2>
<p>When defining a function, placeholders named <strong>parameters</strong> are declared inside the header. When calling the function, actual concrete values called <strong>arguments</strong> are passed inside the parentheses. Python supports multiple versatile argument passing styles:</p>
<ol>
  <li><strong>Positional Arguments:</strong> Arguments are matched to parameters strictly based on their sequential order from left to right.</li>
  <li><strong>Keyword Arguments:</strong> You explicitly specify the target parameter name (`key=value`) during the function call, making ordering irrelevant and enhancing call-site readability.</li>
  <li><strong>Default Parameter Values:</strong> You can assign default fallback values (`param=default`) directly in the function definition, making those arguments optional when invoked.</li>
</ol>

<h2>CRITICAL WARNING: The Mutable Default Argument Trap</h2>
<p>In Python, default parameter values are evaluated and created exactly <strong>once</strong> when the function is defined by the interpreter—not each time the function is called. If you assign a mutable object (like a list `[]` or dict `{}`) as a default value, every subsequent call to that function will share and mutate that exact same memory object! Always use <code>None</code> as the default placeholder for mutable types.</p>

<h2>Arbitrary Arguments (*args and **kwargs)</h2>
<p>When designing flexible functions that must accept an arbitrary, unknown number of inputs (such as Python's built-in `print()` function), you use special unpacking operators:</p>
<ul>
  <li><code>*args</code> : Collects any extra positional arguments into an iterable <strong>Tuple</strong>.</li>
  <li><code>**kwargs</code> : Collects any extra keyword arguments (`key=val`) into a key-value <strong>Dictionary</strong>.</li>
</ul>

<pre><code class="language-python">
# 1. Standard Function with Type Hints, Docstring, and Default Parameter
def calculate_invoice_total(amount: float, tax_rate: float = 0.08) -> float:
    \"\"\"Calculates the final invoice total including sales tax.\"\"\"
    total = amount + (amount * tax_rate)
    return round(total, 2)

# Calling with Positional vs Keyword Arguments
print("Positional call:", calculate_invoice_total(100.0, 0.10)) # Output: 110.0
print("Keyword call (using default tax):", calculate_invoice_total(amount=250.0)) # Output: 270.0

# 2. Correct Handling of Mutable Default Parameters
def append_user_log(message: str, log_list: list = None) -> list:
    \"\"\"Safely appends a message to a log list without sharing state across calls.\"\"\"
    if log_list is None:
        log_list = [] # Create a fresh list instance every time!
    log_list.append(message)
    return log_list

print("Safe Log Call 1:", append_user_log("System Boot")) # Output: ['System Boot']
print("Safe Log Call 2:", append_user_log("User Login"))  # Output: ['User Login']

# 3. Flexible Arbitrary Arguments (*args and **kwargs)
def log_event(event_name: str, *args, **kwargs):
    print(f"\\nEvent Header: {event_name}")
    print("  Positional Context (*args as tuple):", args)
    print("  Metadata Payload (**kwargs as dict):", kwargs)

log_event("HTTP_REQUEST", "GET", "/api/v1/users", status=200, latency_ms=45)
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Functions (<code>def name():</code>) encapsulate reusable logic, enforce abstraction, and make codebases modular.</li>
  <li>Combine positional arguments, keyword arguments, and default values to create flexible, self-documenting APIs.</li>
  <li><strong>Never</strong> use mutable objects (`[]` or `{}`) as default parameters; always default to `None` and initialize inside the block.</li>
  <li>Use <code>*args</code> (tuple) and <code>**kwargs</code> (dict) to accept arbitrary, variable-length argument lists cleanly.</li>
</ul>
""".strip()

    pages.append({
        "id": "6851",
        "title": "Functions and Parameters",
        "topic_number": "P3.1.1",
        "section_title": "Section 3.1: Functions & Scope",
        "unit_title": "Unit 3: Functions & Modular Programming",
        "content_html": p12_html
    })

    # ----------------------------------------------------
    # Page 13: 6852 - Functions - Return Values and Scope
    # ----------------------------------------------------
    p13_html = """
<h2>Return Values and Variable Scope Hierarchy</h2>
<p>A function acts as an isolated data processing pipeline: it receives inputs via parameters, executes internal logic, and sends results back to the calling scope using the <code>return</code> statement. Understanding how return values work alongside Python's strict variable visibility rules is essential for writing bug-free modular code.</p>

<h2>Returning Single and Multiple Values</h2>
<p>When Python encounters a <code>return</code> statement, execution of the function halts instantly, and the specified expression is passed back to the caller. If a function completes execution without encountering a explicit <code>return</code> statement, Python automatically returns the singleton object <code>None</code>.</p>
<p>Uniquely, Python allows functions to cleanly return <strong>multiple values simultaneously</strong> by separating expressions with commas. Under the hood, Python packs these return values into an immutable tuple, which the caller can immediately unpack into separate variables.</p>

<h2>Variable Scope and the LEGB Rule</h2>
<p><strong>Scope</strong> determines where in your program a particular variable name is visible and accessible. Python resolves variable names using a strict four-level hierarchical lookup order known as the <strong>LEGB Rule</strong>:</p>
<ol>
  <li><strong>L - Local Scope:</strong> Names created inside the currently executing function block (including parameters). Accessible only inside that function.</li>
  <li><strong>E - Enclosing Scope:</strong> Names defined inside any outer enclosing function (relevant when creating nested functions / closures).</li>
  <li><strong>G - Global Scope:</strong> Names defined at the top level of a module script or explicitly declared using the <code>global</code> keyword.</li>
  <li><strong>B - Built-in Scope:</strong> Python's pre-loaded standard namespace containing built-in functions (`len()`, `print()`, `range()`, `int()`).</li>
</ol>

<h2>Modifying Global State: global and nonlocal</h2>
<p>By default, assigning a value to a variable inside a function creates a brand new Local variable, shadowing (hiding) any global variable of the exact same name. If you explicitly need to reassign a top-level global variable from inside a function block, you must declare it first using the <code>global</code> keyword (though mutating global state is generally discouraged in professional software design).</p>

<h2>Anonymous Inline Functions (Lambda Expressions)</h2>
<p>For simple, single-expression operations that do not require formal multi-line definitions or docstrings, Python provides <strong>Lambda Functions</strong>. Written using the syntax <code>lambda parameters: expression</code>, lambdas return their evaluated expression automatically and are heavily used as quick callbacks for sorting or functional operations like <code>map()</code> and <code>filter()</code>.</p>

<pre><code class="language-python">
# 1. Returning Multiple Values and Tuple Unpacking
def analyze_numbers(numbers: list) -> tuple:
    \"\"\"Calculates and returns minimum, maximum, and average values.\"\"\"
    min_val = min(numbers)
    max_val = max(numbers)
    avg_val = sum(numbers) / len(numbers)
    return min_val, max_val, round(avg_val, 2) # Returned packed as a tuple

low, high, average = analyze_numbers([12, 45, 88, 23, 67])
print(f"Analysis Results -> Low: {low}, High: {high}, Average: {average}")

# 2. Demonstrating Variable Scope and the 'global' Keyword
system_status = "ONLINE" # Global variable

def trigger_maintenance_mode():
    global system_status   # Explicitly reference the global variable
    system_status = "MAINTENANCE"
    local_timer = 300      # Local variable (inaccessible outside this function)
    print(f"Inside Function: Status updated to {system_status}")

trigger_maintenance_mode()
print(f"Outside Function: Global status is now {system_status}")

# 3. Using Concise Lambda Expressions for Sorting
users = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 22},
    {"name": "Charlie", "age": 35}
]

# Sort list of dictionaries by the 'age' key using an inline lambda callback
users.sort(key=lambda user: user["age"])
print("\\nUsers sorted by age ascending:", users)
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Functions return <code>None</code> by default unless an explicit <code>return</code> statement sends data back to the caller.</li>
  <li>Return multiple values cleanly separated by commas (`return a, b`) and unpack them at call sites (`x, y = func()`).</li>
  <li>Python resolves variable names following the strict <strong>LEGB</strong> hierarchy: Local, Enclosing, Global, then Built-in.</li>
  <li>Use concise inline <code>lambda params: expression</code> syntax when passing quick functional callbacks to methods like <code>.sort()</code>.</li>
</ul>
""".strip()

    pages.append({
        "id": "6852",
        "title": "Functions - Return Values and Scope",
        "topic_number": "P3.1.2",
        "section_title": "Section 3.1: Functions & Scope",
        "unit_title": "Unit 3: Functions & Modular Programming",
        "content_html": p13_html
    })

    # ----------------------------------------------------
    # Page 14: 6853 - File Operations and Input/Output
    # ----------------------------------------------------
    p14_html = """
<h2>File Operations and Standard I/O</h2>
<p>Real-world software applications must persist data beyond a single runtime session. Whether reading configuration files, parsing massive CSV datasets, saving system logs, or exporting JSON payloads, file input/output (I/O) is a mandatory skill for Python engineers.</p>

<h2>1. Standard User Input with input()</h2>
<p>To capture interactive input from a user via the console, Python provides the built-in <code>input("prompt")</code> function. <strong>CRITICAL RULE:</strong> The <code>input()</code> function <em>always</em> returns the user's response as a primitive <strong>String (<code>str</code>)</strong>. If you expect numerical input for calculations, you must explicitly cast the returned string using <code>int()</code> or <code>float()</code>.</p>

<h2>2. Opening and Closing Files</h2>
<p>Python interacts with the operating system's filesystem using the built-in <code>open(filepath, mode)</code> function. The second argument specifies the explicit file access mode:</p>
<ul>
  <li><code>'r'</code> : Read mode (Default). Opens file for reading; raises <code>FileNotFoundError</code> if missing.</li>
  <li><code>'w'</code> : Write mode. Creates a new file or <strong>completely overwrites</strong> existing file contents from scratch.</li>
  <li><code>'a'</code> : Append mode. Creates a new file or appends new data to the very end of existing contents without overwriting.</li>
  <li><code>'b'</code> : Binary mode modifier (e.g., `'rb'`, `'wb'`), essential when processing non-text binary files like images, PDFs, or audio tracks.</li>
</ul>

<h2>3. Context Managers (The 'with' Statement)</h2>
<p>Whenever you open a file, your operating system allocates finite file descriptor handles. If your program encounters an error before reaching a manual <code>file.close()</code> statement, the file remains locked and memory leaks occur.</p>
<p>The industry standard best practice is to always wrap file operations inside a <strong>Context Manager (`with open(...) as file:`)</strong>. When execution exits the indented `with` block—whether normally or via an unhandled crash—Python guarantees the file is safely flushed and closed instantly.</p>

<h2>4. Reading and Writing Text and JSON Files</h2>
<p>When reading text files, you can read everything into one string using <code>.read()</code>, read line by line using a `for` loop over the file object (high memory efficiency for huge files), or load all lines into a list via <code>.readlines()</code>. For structured data exchange across web APIs, Python provides the built-in <code>json</code> module to serialize (`json.dump()`) and deserialize (`json.load()`) dictionary payloads directly to/from disk.</p>

<pre><code class="language-python">
import json
import os

# 1. Standard Interactive Console Input with Type Casting
# user_age_str = input("Enter your age: ")
# age = int(user_age_str) # Explicitly cast string to integer for math

# 2. Safe File Writing using Context Managers (with statement)
log_filepath = "application_activity.log"
with open(log_filepath, mode="w", encoding="utf-8") as file:
    file.write("INFO: Application booted successfully at 10:00 AM\\n")
    file.write("DEBUG: Loaded configuration tokens.\\n")

# Appending additional data without overwriting existing lines
with open(log_filepath, mode="a", encoding="utf-8") as file:
    file.write("INFO: User session authenticated cleanly.\\n")

# 3. Memory-Efficient Line-by-Line Reading
print("--- Reading Log File Contents ---")
if os.path.exists(log_filepath):
    with open(log_filepath, mode="r", encoding="utf-8") as file:
        for line_num, line in enumerate(file, start=1):
            print(f"Line {line_num}: {line.strip()}")

# 4. Serializing Python Dictionaries to JSON Files
app_config = {
    "app_name": "GrowHall Learning Hub",
    "version": 2.4,
    "supported_themes": ["dark", "light", "blue"],
    "is_production": True
}

json_filepath = "config.json"
with open(json_filepath, mode="w", encoding="utf-8") as json_file:
    # json.dump automatically converts Python dicts to formatted JSON syntax
    json.dump(app_config, json_file, indent=4)
print(f"\\nSuccessfully exported structured configuration to {json_filepath}")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>The <code>input()</code> function always captures console input as a string; explicitly cast via <code>int()</code> for numerical operations.</li>
  <li>Always open files using the context manager syntax <code>with open(...) as f:</code> to guarantee automatic resource cleanup.</li>
  <li>Use explicit access modes: <code>'r'</code> for reading, <code>'w'</code> for clean overwriting, and <code>'a'</code> for safe appending.</li>
  <li>Import the built-in <code>json</code> module (`json.dump()` / `json.load()`) to seamlessly handle structured data files.</li>
</ul>
""".strip()

    pages.append({
        "id": "6853",
        "title": "File Operations and Input/Output",
        "topic_number": "P3.2.1",
        "section_title": "Section 3.2: I/O & Error Handling",
        "unit_title": "Unit 3: Functions & Modular Programming",
        "content_html": p14_html
    })

    # ----------------------------------------------------
    # Page 15: 6854 - Error Handling and Exceptions (Refined to <5000 chars)
    # ----------------------------------------------------
    p15_html = """
<h2>Error Handling and Exception Management</h2>
<p>No matter how meticulously software is engineered, runtime errors will occur. Files get deleted, network requests time out, and users submit malformed data. In Python, operational failures are represented as <strong>Exceptions</strong>.</p>
<p>If an exception is raised and not explicitly caught by your code, the Python interpreter halts program execution immediately and outputs a detailed traceback error. To build resilient applications that recover gracefully from failures, you utilize <strong>Exception Handling (`try / except / else / finally`)</strong>.</p>

<h2>Syntax Errors vs. Runtime Exceptions</h2>
<p>It is crucial to distinguish between two main error categories:</p>
<ol>
  <li><strong>Syntax Errors (`SyntaxError`):</strong> Occur when code violates the grammar rules of Python (e.g., missing a colon or unclosed parenthesis). Caught during compilation before execution starts; cannot be handled dynamically via try-except blocks.</li>
  <li><strong>Runtime Exceptions:</strong> Occur during execution when syntactically valid code encounters an illegal operational state. Common classes include:
    <ul>
      <li><code>ValueError</code> : Function receives correct type but invalid value (`int("abc")`).</li>
      <li><code>TypeError</code> : Operation applied to incompatible object type (`"Age: " + 25`).</li>
      <li><code>KeyError</code> / <code>IndexError</code> : Looking up missing dict keys or out-of-bounds list indices.</li>
      <li><code>FileNotFoundError</code> : Attempting to open a missing file path in read mode.</li>
      <li><code>ZeroDivisionError</code> : Attempting to divide any number by zero.</li>
    </ul>
  </li>
</ol>

<h2>Anatomy of try / except / else / finally</h2>
<p>A comprehensive exception handling structure provides granular control over error recovery and cleanup:</p>
<ul>
  <li><code>try:</code> : Encloses specific risky code operations that might trigger an exception.</li>
  <li><code>except SpecificError as e:</code> : Catches and handles the specified exception class cleanly. You can chain multiple `except` blocks to handle differing error types specifically.</li>
  <li><code>else:</code> : Executes ONLY if the `try` block completed successfully without raising any exceptions.</li>
  <li><code>finally:</code> : Guarantees execution under <em>all</em> circumstances—whether exceptions occurred or not. Essential for mandatory cleanup tasks like closing file handles or sockets.</li>
</ul>

<h2>Raising Custom Exceptions</h2>
<p>You can proactively trigger exceptions using the <code>raise</code> keyword. Furthermore, you can define domain-specific exception classes by creating classes that inherit from Python's base <code>Exception</code> class.</p>

<pre><code class="language-python">
# 1. Comprehensive try-except-else-finally Flow
def calculate_unit_price(total_cost_str: str, unit_count_str: str) -> float:
    try:
        total_cost = float(total_cost_str)
        unit_count = int(unit_count_str)
        price_per_unit = total_cost / unit_count
    except ValueError as val_err:
        print(f"[ERROR] Must provide valid numbers: {val_err}")
        return 0.0
    except ZeroDivisionError:
        print("[ERROR] Unit count cannot be zero!")
        return 0.0
    except Exception as unexpected_err: # Catch-all safety net
        print(f"[CRITICAL] System error: {type(unexpected_err).__name__}")
        return 0.0
    else:
        print("[SUCCESS] Calculation finished safely.")
        return round(price_per_unit, 2)
    finally:
        print("[CLEANUP] Audit log entry recorded.\\n")

print("Test 1 (Valid):", calculate_unit_price("150.0", "10"))
print("Test 2 (Invalid text):", calculate_unit_price("one_hundred", "10"))

# 2. Defining and Raising Custom Exceptions
class InsufficientFundsError(Exception):
    \"\"\"Custom domain exception for overdrafts.\"\"\"
    pass

def withdraw_funds(balance: float, amount: float) -> float:
    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")
    if amount > balance:
        raise InsufficientFundsError(f"Cannot withdraw ${amount}. Balance: ${balance}")
    return balance - amount

try:
    new_balance = withdraw_funds(100.00, 250.00)
except InsufficientFundsError as domain_err:
    print(f"Transaction Blocked: {domain_err}")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Wrap risky operations inside <code>try:</code> blocks and catch specific failure types via <code>except:</code> blocks.</li>
  <li>Avoid bare <code>except:</code> clauses; always catch explicit exception classes to prevent hiding bugs.</li>
  <li>Use the <code>else:</code> clause for code that should only run when the <code>try</code> block succeeds cleanly.</li>
  <li>Use <code>finally:</code> for guaranteed, mandatory cleanup actions like closing database connections.</li>
</ul>
""".strip()

    pages.append({
        "id": "6854",
        "title": "Error Handling and Exceptions",
        "topic_number": "P3.2.2",
        "section_title": "Section 3.2: I/O & Error Handling",
        "unit_title": "Unit 3: Functions & Modular Programming",
        "content_html": p15_html
    })

    # ----------------------------------------------------
    # Page 16: 6855 - Libraries and Modules (Refined to <5000 chars)
    # ----------------------------------------------------
    p16_html = """
<h2>Python Ecosystem: Modules and Libraries</h2>
<p>Instead of building complex algorithms from scratch, Python developers architect clean applications by importing reusable code organized across <strong>Modules</strong>, <strong>Packages</strong>, and third-party <strong>Libraries</strong>.</p>

<h2>Understanding Modules and Packages</h2>
<p>To keep projects structured and maintainable across large software teams, Python uses a simple file-based organizational hierarchy:</p>
<ul>
  <li><strong>Module:</strong> Any single file ending with the <code>.py</code> extension containing Python definitions and statements (`utils.py`). Imported using the <code>import</code> keyword.</li>
  <li><strong>Package:</strong> A directory containing multiple related `.py` module files alongside a special file named <code>__init__.py</code>, which informs the Python interpreter that the folder is an importable package hierarchy.</li>
</ul>

<h2>Importing Syntax Styles</h2>
<p>Python offers flexible syntax variations for bringing external namespaces into your script:</p>
<ol>
  <li><code>import math</code> : Imports the entire module namespace. Access functions using dot notation (`math.sqrt(16)`).</li>
  <li><code>from math import sqrt, pi</code> : Directly imports specific target functions into your local namespace (`sqrt(16)`).</li>
  <li><code>import numpy as np</code> : Imports the module and assigns a clean alias (`np`) to reduce typing across complex codebases.</li>
</ol>

<h2>The Python Standard Library ("Batteries Included")</h2>
<p>Python ships with a massive, battle-tested collection of pre-installed modules known as the <strong>Standard Library</strong>. Essential modules include:</p>
<ul>
  <li><code>os</code> and <code>sys</code> : Interacting with OS paths, environment variables, and command-line arguments.</li>
  <li><code>datetime</code> : Parsing, formatting, and arithmetic for dates and timestamps.</li>
  <li><code>random</code> : Generating pseudo-random numbers, picking random elements, and shuffling sequences.</li>
  <li><code>collections</code> : High-performance specialized data structures (`Counter`, `defaultdict`).</li>
  <li><code>re</code> : Powerful regular expression matching and string pattern searching.</li>
</ul>

<h2>Third-Party Packages and PyPI (pip)</h2>
<p>Beyond the standard library lies the <strong>Python Package Index (PyPI)</strong>, hosting hundreds of thousands of open-source packages. You install and manage these external libraries right from your terminal using Python's official package installer, <code>pip</code> (`pip install requests`).</p>

<h2>The Special if __name__ == "__main__": Idiom</h2>
<p>Whenever a `.py` file is run or imported, the interpreter defines a special variable named <code>__name__</code>. If the file is executed directly from the terminal, `__name__` is set to <code>"__main__"</code>. If imported by another script, `__name__` is set to the module's filename.</p>
<p>Wrapping execution code inside <code>if __name__ == "__main__":</code> ensures that test code runs only when the file is launched directly—never when imported cleanly as a module!</p>

<pre><code class="language-python">
# 1. Using Standard Library Modules: datetime and random
import datetime
import random
from collections import Counter

current_time = datetime.datetime.now()
print("System Time:", current_time.strftime("%Y-%m-%d %H:%M:%S"))

lottery_pool = list(range(1, 51))
winning_numbers = random.sample(lottery_pool, 5) # Pick 5 unique randoms
print("Lottery Numbers:", sorted(winning_numbers))

# Frequency counting with collections.Counter
responses = ["python", "java", "python", "javascript", "python"]
counts = Counter(responses)
print("Top language:", counts.most_common(1)) # Output: [('python', 3)]

# 2. Demonstrating the Script vs Module Execution Idiom
def calculate_circle_area(radius: float) -> float:
    import math
    return round(math.pi * (radius ** 2), 2)

# Runs ONLY when executed directly (`python script.py`)
if __name__ == "__main__":
    print("\\n--- Running Direct Module Validation ---")
    test_area = calculate_circle_area(10.0)
    print(f"Validation: Area for radius 10 is {test_area}")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>A module is a single `.py` file, while a package is a folder hierarchy of modules structured with <code>__init__.py</code>.</li>
  <li>Leverage Python's rich Standard Library (`datetime`, `os`, `random`, `collections`) before writing custom tools.</li>
  <li>Use explicit import syntax (`from module import item` or `import module as alias`) to maintain clean namespaces.</li>
  <li>Always guard executable test code inside <code>if __name__ == "__main__":</code> to allow safe module importing.</li>
</ul>
""".strip()

    pages.append({
        "id": "6855",
        "title": "Libraries and Modules",
        "topic_number": "P3.3.1",
        "section_title": "Section 3.3: Ecosystem & Packages",
        "unit_title": "Unit 3: Functions & Modular Programming",
        "content_html": p16_html
    })

    # ----------------------------------------------------
    # Page 17: 6856 - Introduction to Object-Oriented Programming
    # ----------------------------------------------------
    p17_html = """
<h2>Introduction to Object-Oriented Programming (OOP)</h2>
<p>As software systems scale to thousands or millions of lines of code, managing complex data structures via disconnected procedural functions becomes increasingly difficult and prone to state synchronization bugs. To solve these architectural challenges, professional engineering adopts <strong>Object-Oriented Programming (OOP)</strong>.</p>
<p>In Python—where literally every number, string, list, and function is fundamentally an object under the hood—OOP is a design paradigm that structures software by bundling related data (attributes) and behaviors (methods) together into cohesive, self-contained blueprints called <strong>Classes</strong>.</p>

<h2>The Four Core Pillars of Object-Oriented Programming</h2>
<p>Object-Oriented design is anchored by four fundamental architectural concepts that enable modularity, code reuse, and clean software maintenance:</p>
<ol>
  <li><strong>Encapsulation:</strong> The bundling of internal state data alongside the methods that operate on that data inside a single class unit, restricting direct external tampering and enforcing clean interface contracts.</li>
  <li><strong>Abstraction:</strong> Hiding internal implementation complexity behind simple, clean public interfaces. Consumers of an object only need to know <em>what</em> a method does, not <em>how</em> the complex internal machinery works.</li>
  <li><strong>Inheritance:</strong> A mechanism allowing child classes to inherit attributes and methods from parent base classes, establishing hierarchical relationships and dramatically eliminating redundant boilerplate code across projects.</li>
  <li><strong>Polymorphism:</strong> Literally meaning "many forms," polymorphism allows differing object classes to share a common method interface (`.render()`, `.calculate_pay()`), enabling uniform processing across heterogeneous object collections without rigid type checking.</li>
</ol>

<h2>Classes vs. Objects (Instances)</h2>
<p>It is crucial to understand the conceptual difference between a class and an instance object:</p>
<ul>
  <li><strong>The Class (Blueprint):</strong> A class is an abstract architectural template or definition. For example, a `Car` class defines that all cars possess a `brand`, `color`, and a `.drive()` behavior, but the class itself is not a physical vehicle on the road.</li>
  <li><strong>The Object (Instance):</strong> An object is a concrete, physical manifestation created directly from the class blueprint occupying real computer memory. You can instantiate dozens of unique `Car` objects (`my_car`, `police_car`), each possessing distinct individual color and mileage states while sharing the blueprint's behaviors.</li>
</ul>

<h2>Procedural vs. Object-Oriented Comparison</h2>
<p>Examine how moving from disconnected procedural data dictionaries to structured Object-Oriented classes transforms clarity and data safety:</p>

<pre><code class="language-python">
# --- PROCEDURAL APPROACH (Disconnected data and functions) ---
procedural_account = {"holder": "Alice", "balance": 1000.0}

def procedural_deposit(account_dict: dict, amount: float):
    # Risk: External code can directly alter balance without validation checks!
    account_dict["balance"] += amount

procedural_deposit(procedural_account, 250.0)
print("Procedural Balance:", procedural_account["balance"])

# --- OBJECT-ORIENTED APPROACH (Cohesive bundling via Classes) ---
class BankAccount:
    \"\"\"Encapsulates account state data directly with transaction behaviors.\"\"\"
    
    def __init__(self, holder_name: str, initial_balance: float):
        self.holder = holder_name
        self.balance = initial_balance # Encapsulated instance state
        
    def deposit(self, amount: float) -> float:
        \"\"\"Safe behavior method with internal validation logic.\"\"\"
        if amount > 0:
            self.balance += amount
            print(f"OOP Transaction: Deposited ${amount:.2f} for {self.holder}")
        return self.balance

# Instantiating a concrete Object instance from our Class blueprint
my_account = BankAccount("Colin", 1500.00)
my_account.deposit(350.00)
print(f"OOP Final Balance: ${my_account.balance:.2f}")
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>OOP structures complex software by bundling data attributes and operational behaviors into cohesive <strong>Classes</strong>.</li>
  <li>A <strong>Class</strong> serves as an architectural blueprint, while an <strong>Object</strong> is a concrete memory instance of that blueprint.</li>
  <li>Master the four pillars of OOP: Encapsulation, Abstraction, Inheritance, and Polymorphism.</li>
  <li>Python is inherently object-oriented—understanding class design unlocks the true power and elegance of the language.</li>
</ul>
""".strip()

    pages.append({
        "id": "6856",
        "title": "Introduction to Object-Oriented Programming",
        "topic_number": "P4.1.1",
        "section_title": "Section 4.1: Object-Oriented Programming",
        "unit_title": "Unit 4: Advanced Concepts & Real-World Applications",
        "content_html": p17_html
    })

    # ----------------------------------------------------
    # Page 18: 6857 - Classes and Objects (Refined to <5000 chars)
    # ----------------------------------------------------
    p18_html = """
<h2>Implementing Classes and Objects in Python</h2>
<p>Now that you understand the theory behind Object-Oriented Programming, this module dives into the concrete Python syntax required to define custom classes, manage constructors, establish inheritance hierarchies, and leverage magic methods.</p>

<h2>Class Syntax and the __init__() Constructor</h2>
<p>You define a class using the <code>class ClassName:</code> keyword (using <strong>PascalCase</strong> naming where every word is capitalized). Inside the class, you declare the constructor method named strictly <code>__init__(self, ...)</code>.</p>
<p><strong>What is <code>self</code>?</strong> In Python, `self` explicitly represents the specific instance object being manipulated right now in memory. Whenever you call an instance method (`my_obj.method()`), Python automatically passes the instance itself as the first `self` argument under the hood, allowing methods to read and modify that specific object's attributes (`self.attr = value`).</p>

<h2>Instance Attributes vs. Class Attributes</h2>
<p>It is vital to distinguish where data is stored across class hierarchies:</p>
<ul>
  <li><strong>Instance Attributes (`self.name = ...`):</strong> Declared inside `__init__()`. Every individual object instance maintains its own unique copy of these values.</li>
  <li><strong>Class Attributes:</strong> Declared directly inside the class body above `__init__()`. These variables are shared globally across <em>all</em> instantiated objects of that class (`company_name = "Tech Corp"`).</li>
</ul>

<h2>Inheritance and super()</h2>
<p>To establish an inheritance relationship where a child class inherits all attributes and methods of a parent base class, pass the parent class name inside parentheses during class definition: <code>class ChildClass(ParentClass):</code>.</p>
<p>Inside the child's `__init__()` constructor, call <code>super().__init__(...)</code> to execute the parent class's initialization logic before adding child-specific attributes.</p>

<h2>Dunder (Double Underscore) Magic Methods</h2>
<p>Python provides special built-in methods surrounded by double underscores (termed <strong>Dunder methods</strong>) that allow your custom classes to integrate seamlessly with built-in syntax (`print()`, `len()`):</p>
<ul>
  <li><code>__str__(self)</code> : Returns a clean, user-friendly string representation of the object when passed to `print(obj)`.</li>
  <li><code>__repr__(self)</code> : Returns an unambiguous, technical string representation used during debugging inside IDEs.</li>
  <li><code>__len__(self)</code> : Allows your custom object to respond cleanly to `len(obj)`.</li>
</ul>

<pre><code class="language-python">
# 1. Base Class Definition with Class Attributes, Constructor, and Dunder Methods
class Employee:
    company_name = "GrowHall Tech Corp" # Class Attribute
    
    def __init__(self, name: str, emp_id: int, base_salary: float):
        self.name = name                 # Instance Attribute
        self.emp_id = emp_id
        self.salary = base_salary
        
    def calculate_bonus(self) -> float:
        return round(self.salary * 0.05, 2)
        
    def __str__(self) -> str:
        return f"Employee[ID={self.emp_id}, Name='{self.name}', Salary=${self.salary:,}]"

# 2. Child Class Demonstrating Inheritance and super()
class SoftwareEngineer(Employee):
    def __init__(self, name: str, emp_id: int, base_salary: float, language: str):
        super().__init__(name, emp_id, base_salary) # Call parent constructor
        self.language = language
        
    # Polymorphic Method Overriding
    def calculate_bonus(self) -> float:
        return super().calculate_bonus() + 2500.00 # Extra tech incentive

# Instantiating Objects and Demonstrating Behaviors
general_staff = Employee("Alice Smith", 101, 60000.0)
engineer_colin = SoftwareEngineer("Colin Patton", 202, 110000.0, "Python")

print(general_staff) # Triggers __str__
print("Staff Bonus:", general_staff.calculate_bonus()) # Output: 3000.0

print(engineer_colin)
print("Engineer Bonus:", engineer_colin.calculate_bonus()) # Output: 8000.0
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>Use <code>class ClassName:</code> and strictly name your initializer method <code>__init__(self, ...)</code>.</li>
  <li>The <code>self</code> parameter explicitly binds data and methods to the specific object instance in memory.</li>
  <li>Use <code>class Child(Parent):</code> and <code>super().__init__()</code> to inherit and extend existing parent classes.</li>
  <li>Implement magic dunder methods like <code>__str__(self)</code> to give custom classes readable representations.</li>
</ul>
""".strip()

    pages.append({
        "id": "6857",
        "title": "Classes and Objects",
        "topic_number": "P4.1.2",
        "section_title": "Section 4.1: Object-Oriented Programming",
        "unit_title": "Unit 4: Advanced Concepts & Real-World Applications",
        "content_html": p18_html
    })

    # ----------------------------------------------------
    # Page 19: 6858 - Working with APIs (Refined to <5000 chars)
    # ----------------------------------------------------
    p19_html = """
<h2>Connecting Python to the World: Working with APIs</h2>
<p>Modern applications do not operate in isolation. Whether building weather dashboards, automated trading bots, or AI agents, software must continuously communicate across the internet with external servers through <strong>APIs (Application Programming Interfaces)</strong>.</p>
<p>Specifically, most modern web services communicate using <strong>RESTful APIs</strong> over HTTP, exchanging structured data packets formatted as <strong>JSON (JavaScript Object Notation)</strong>—which maps almost identically to Python dictionaries and lists!</p>

<h2>HTTP Request Methods and Status Codes</h2>
<p>When your Python script communicates with a remote API endpoint, it sends an HTTP request using standard action verbs:</p>
<ul>
  <li><code>GET</code> : Retrieves data from the server (e.g., fetching a user profile or weather forecast).</li>
  <li><code>POST</code> : Submits new data to the server to create a resource (e.g., submitting a registration form).</li>
  <li><code>PUT</code> / <code>PATCH</code> : Updates or modifies an existing record on the server.</li>
  <li><code>DELETE</code> : Requests the removal of a specific resource from the database.</li>
</ul>
<p>The server responds with a 3-digit <strong>HTTP Status Code</strong>: <strong>200 OK</strong> (Success), <strong>201 Created</strong>, <strong>400 Bad Request</strong>, <strong>401 Unauthorized</strong>, <strong>404 Not Found</strong>, and <strong>500 Internal Server Error</strong>.</p>

<h2>The Requests Library: Python's HTTP Standard</h2>
<p>While Python ships with a built-in `urllib` module, the industry standard for web communication is the third-party <code>requests</code> library. It provides an exceptionally clean, human-readable API for sending requests, managing headers, and parsing JSON responses (`pip install requests`).</p>

<h2>Passing Query Parameters, Headers, and Error Handling</h2>
<p>When consuming professional APIs, you frequently need to pass authentication keys or search filters:</p>
<ul>
  <li><strong>Query Parameters (`params={...}`):</strong> Attached cleanly to the URL query string (`?city=London&units=metric`).</li>
  <li><strong>HTTP Headers (`headers={...}`):</strong> Passed inside HTTP request headers (`Authorization: Bearer <token>`).</li>
  <li><strong>Safe Error Verification (`response.raise_for_status()`):</strong> Automatically raises an `HTTPError` exception if the server returns a 4xx or 5xx failure status code!</li>
</ul>

<pre><code class="language-python">
import requests
import json

def fetch_github_user(username: str) -> dict:
    \"\"\"Fetches public profile metadata from the GitHub REST API safely.\"\"\"
    api_url = f"https://api.github.com/users/{username}"
    custom_headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GrowHall-Python-Basics-Client"
    }
    
    try:
        print(f"Sending GET request to {api_url}...")
        response = requests.get(api_url, headers=custom_headers, timeout=5.0)
        
        # Proactively raise HTTPError if status code is 4xx or 5xx
        response.raise_for_status()
        
        # Parse the raw JSON response directly into a Python Dictionary
        return response.json()
        
    except requests.exceptions.HTTPError as http_err:
        print(f"[API ERROR] HTTP Request failed ({response.status_code}): {http_err}")
        return {}
    except requests.exceptions.Timeout:
        print("[API ERROR] Request timed out. Remote server unresponsive.")
        return {}
    except requests.exceptions.RequestException as net_err:
        print(f"[API ERROR] Network communication failure: {net_err}")
        return {}

if __name__ == "__main__":
    profile = fetch_github_user("python")
    if profile:
        print("\\n--- GitHub Organization Profile ---")
        print("Name:", profile.get("name"))
        print("Public Repos:", profile.get("public_repos"))
        print("Followers:", profile.get("followers", 0))
        print("Profile URL:", profile.get("html_url"))
</code></pre>

<h2>Key Takeaways</h2>
<ul>
  <li>REST APIs allow systems to exchange structured JSON data over the internet using HTTP verbs (`GET`, `POST`).</li>
  <li>Install and utilize the industry-standard <code>requests</code> library (`requests.get()`) for clean web communication.</li>
  <li>Always pass strict network timeouts (`timeout=5.0`) to prevent scripts from freezing indefinitely.</li>
  <li>Call <code>response.raise_for_status()</code> inside `try-except` blocks to handle 4xx and 5xx API failures cleanly.</li>
</ul>
""".strip()

    pages.append({
        "id": "6858",
        "title": "Working with APIs",
        "topic_number": "P4.2.1",
        "section_title": "Section 4.2: External Integrations & Best Practices",
        "unit_title": "Unit 4: Advanced Concepts & Real-World Applications",
        "content_html": p19_html
    })

    # ----------------------------------------------------
    # Page 20: 6859 - Best Practices and Debugging (Refined to <5000 chars)
    # ----------------------------------------------------
    p20_html = """
<h2>Professional Best Practices and Debugging Mastery</h2>
<p>Writing code that runs without crashing is only the first milestone. True professional engineering requires writing clean, maintainable, self-documenting code that teammates can collaborate on effortlessly, alongside mastering systematic debugging techniques to diagnose and eradicate bugs.</p>

<h2>1. Adhering to PEP 8 Style Guidelines</h2>
<p>Python's official style guide, known as <strong>PEP 8</strong>, defines standard formatting conventions observed across the entire global Python community. Adhering to PEP 8 ensures your code looks professional instantly:</p>
<ul>
  <li><strong>Indentation:</strong> Use exactly <strong>4 spaces</strong> per indentation level—never mix tabs and spaces.</li>
  <li><strong>Line Length:</strong> Limit lines to 79 characters for code to allow clean side-by-side diff comparisons.</li>
  <li><strong>Naming Conventions:</strong> Use <code>snake_case</code> for variables/functions, <code>PascalCase</code> for class names, and <code>UPPER_SNAKE_CASE</code> for module constants (`MAX_CONNECTIONS = 100`).</li>
  <li><strong>Imports:</strong> Place all `import` statements at the top of the script, ordered cleanly: standard library first, third-party (`requests`) second, and local project imports last.</li>
  <li><strong>Automated Formatting:</strong> Utilize automated tools like <code>black</code> and <code>flake8</code> to enforce clean styling automatically.</li>
</ul>

<h2>2. Beyond print(): The Built-in pdb Debugger</h2>
<p>While scattering `print()` statements across code is a common early debugging reflex, it is tedious and clutters files. Professional developers utilize interactive debugging tools. Python ships built-in with the <strong>Python Debugger (`pdb`)</strong>.</p>
<p>By inserting the built-in <code>breakpoint()</code> function at any suspicious line of code, execution pauses instantly right at that exact line inside your terminal! You can then type debugger commands:</p>
<ul>
  <li><code>n</code> (next) : Executes the next single line of code.</li>
  <li><code>s</code> (step) : Steps directly inside a function call being executed.</li>
  <li><code>c</code> (continue) : Resumes normal execution until the next breakpoint.</li>
  <li><code>p var_name</code> : Prints the real-time evaluated state of any variable currently in memory.</li>
</ul>

<h2>3. Automated Testing and Professional Logging</h2>
<p>To ensure code modifications never break existing functionality, engineers write automated verification scripts called <strong>Unit Tests</strong> using Python's built-in <code>unittest</code> module (`assert` statements verify expected outputs).</p>
<p>Furthermore, in production environments, never use `print()` for application tracking. Instead, import Python's built-in <code>logging</code> module (`logging.info()`, `logging.error()`) to categorize output by severity and attach timestamps.</p>

<pre><code class="language-python">
import logging
import unittest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def process_transaction(user_id: int, amount: float) -> bool:
    logging.info(f"Processing transaction for User ID {user_id}...")
    if amount <= 0:
        logging.warning(f"Invalid amount (${amount}) from User {user_id}.")
        return False
    # Drop an interactive breakpoint() here during debugging sessions:
    # breakpoint() 
    logging.info(f"Transaction of ${amount:.2f} finalized for User {user_id}.")
    return True

class TestTransactionLogic(unittest.TestCase):
    def test_valid_transaction(self):
        self.assertTrue(process_transaction(101, 150.00))
    def test_negative_transaction(self):
        self.assertFalse(process_transaction(102, -50.00))

if __name__ == "__main__":
    process_transaction(101, 250.0)
    process_transaction(102, -10.0)
    unittest.main(exit=False)
</code></pre>

<h2>Congratulations!</h2>
<p>You have mastered the curriculum of <strong>Python Basics</strong>! From configuring your environment and manipulating core data types to engineering modular functions, handling exceptions, designing OOP class hierarchies, and integrating REST APIs, you now possess the core toolkit of a Python engineer.</p>

<h2>Key Takeaways</h2>
<ul>
  <li>Strictly adhere to PEP 8 styling rules (4-space indentation, `snake_case` naming) for clean code.</li>
  <li>Use the built-in <code>breakpoint()</code> function to pause execution and inspect variables interactively with `pdb`.</li>
  <li>Replace ad-hoc `print()` statements with Python's professional <code>logging</code> module (`logging.info()`).</li>
  <li>Validate your functions continuously using automated testing (`unittest` / `pytest`) to guarantee reliability.</li>
</ul>
""".strip()

    pages.append({
        "id": "6859",
        "title": "Best Practices and Debugging",
        "topic_number": "P4.2.2",
        "section_title": "Section 4.2: External Integrations & Best Practices",
        "unit_title": "Unit 4: Advanced Concepts & Real-World Applications",
        "content_html": p20_html
    })

    return pages

VOCAB_DICT = {
    "6840": "<strong>Interpreter:</strong> A program that directly executes instructions written in a high-level programming language line by line.<br><br><strong>PEP 20 (The Zen of Python):</strong> A collection of 19 guiding principles for writing clean, readable Python code.<br><br><strong>Syntax:</strong> The grammar and structural rules governing how programming instructions must be written.",
    "6841": "<strong>REPL:</strong> Read-Eval-Print Loop; an interactive command-line environment that reads Python expressions, evaluates them, and prints results immediately.<br><br><strong>IDE:</strong> Integrated Development Environment; a comprehensive software suite (like VS Code or PyCharm) providing a code editor, debugger, and terminal.<br><br><strong>Virtual Environment (venv):</strong> An isolated workspace directory that keeps package dependencies for one project separate from global system packages.",
    "6842": "<strong>Variable:</strong> A symbolic name pointing to an object stored in computer memory.<br><br><strong>Primitive Data Types:</strong> The foundational built-in types: `int` (integers), `float` (decimals), `str` (strings), and `bool` (booleans).<br><br><strong>Type Casting:</strong> Explicitly converting a value from one data type to another (e.g., `int('42')` or `str(100)`).",
    "6843": "<strong>Floor Division (//):</strong> Division that rounds down to the nearest whole integer, discarding any fractional remainder.<br><br><strong>Modulo (%):</strong> An arithmetic operator that returns the remainder of a division operation (`10 % 3` returns `1`).<br><br><strong>PEMDAS / Operator Precedence:</strong> The strict evaluation order: Parentheses, Exponentiation (`**`), Multiplication/Division, and Addition/Subtraction.",
    "6844": "<strong>f-string:</strong> Formatted string literals prefixed with `f` allowing embedded expressions inside curly braces `{}` (`f'Hello {name}'`).<br><br><strong>Zero-based Indexing:</strong> Accessing string characters where the first position begins at index `0` and negative indices (`-1`) count backwards from the end.<br><br><strong>Immutability:</strong> The property where an object (like a `str` or `tuple`) cannot have its individual characters or elements altered after creation.",
    "6845": "<strong>List:</strong> A mutable, ordered sequence of elements enclosed in square brackets `[]`.<br><br><strong>Append vs. Extend:</strong> `.append(item)` adds a single element to the end, while `.extend(iterable)` merges all items from another collection.<br><br><strong>List Comprehension:</strong> A concise, single-line syntax for generating lists (`[x**2 for x in range(5)]`).",
    "6846": "<strong>Tuple:</strong> An immutable, ordered collection of elements enclosed in parentheses `()`, useful for fixed data structures.<br><br><strong>Dictionary (`dict`):</strong> A mutable mapping of unique keys to values enclosed in curly braces `{key: value}`.<br><br><strong>Hashable:</strong> An object whose hash value never changes during its lifetime (required for dictionary keys and set elements; immutable tuples are hashable, while mutable lists are not).",
    "6847": "<strong>Boolean (`bool`):</strong> A binary data type having only two possible values: `True` or `False`.<br><br><strong>Short-Circuit Evaluation:</strong> Logical operators (`and`, `or`) stop evaluating expressions as soon as the overall truth value is definitively known.<br><br><strong>Falsy Values:</strong> Objects that evaluate to `False` in boolean contexts (`0`, `0.0`, `''`, `[]`, `{}`, `None`, and `False`).",
    "6848": "<strong>Conditional Statement:</strong> Control flow structures (`if`, `elif`, `else`) that execute specific code blocks based on boolean evaluations.<br><br><strong>Indentation:</strong> The mandatory whitespace (4 spaces per level) used by Python to define code block boundaries.<br><br><strong>Ternary Operator:</strong> A concise conditional expression written on one line: `value_if_true if condition else value_if_false`.",
    "6849": "<strong>Definite Iteration:</strong> Looping over a known sequence or collection where the exact number of iterations is determined before starting (`for item in collection:`).<br><br><strong>`range(start, stop, step)`:</strong> A built-in generator function that yields an immutable sequence of integers.<br><br><strong>`enumerate(iterable)`:</strong> A built-in function yielding pairs of `(index, item)` when iterating over a collection.",
    "6850": "<strong>Indefinite Iteration:</strong> Looping continuously as long as a boolean condition remains `True` (`while condition:`).<br><br><strong>`break` vs. `continue`:</strong> `break` terminates and exits the loop immediately, while `continue` skips the rest of the current iteration and jumps to the top condition check.<br><br><strong>Infinite Loop:</strong> A loop whose terminating condition is never met (`while True:`), running endlessly unless interrupted or broken explicitly.",
    "6851": "<strong>Function (`def`):</strong> A named, reusable block of code that performs a specific task when called.<br><br><strong>Positional vs. Keyword Arguments:</strong> Positional arguments are matched by order, while keyword arguments are explicitly named during the call (`func(name='Alice', age=30)`).<br><br><strong>Default Parameters:</strong> Parameters assigned a fallback value (`def greet(name='Guest'):`), making them optional when calling the function.",
    "6852": "<strong>Return Statement (`return`):</strong> Exits a function and passes the computed output object back to the caller (if omitted, Python returns `None`).<br><br><strong>LEGB Rule:</strong> The strict order Python searches for variable names: Local, Enclosing function, Global, and Built-in scope.<br><br><strong>Global Scope:</strong> Variables defined at the top level of a script module, accessible anywhere within that file.",
    "6853": "<strong>Context Manager (`with` statement):</strong> Automatically manages resource acquisition and release (`with open(...) as f:` ensures files close even if exceptions occur).<br><br><strong>File Modes (`r`, `w`, `a`):</strong> `r` opens for reading, `w` truncates and overwrites, and `a` appends new content to the end without deleting existing data.<br><br><strong>JSON (`json` module):</strong> JavaScript Object Notation; the universal text format for storing and exchanging structured dictionary/list data across systems.",
    "6854": "<strong>Exception (`Exception`):</strong> Runtime errors (like `ValueError` or `FileNotFoundError`) that interrupt normal execution flow when unexpected states arise.<br><br><strong>`try / except / else / finally`:</strong> The complete exception handling structure: `try` runs risky code, `except` catches errors, `else` runs if no errors occurred, and `finally` always runs for cleanup.<br><br><strong>`raise` Statement:</strong> Explicitly triggering an exception in code (`raise ValueError('Invalid input')`) when validation rules fail.",
    "6855": "<strong>Module:</strong> A single `.py` file containing reusable Python code, functions, and classes imported via the `import` statement.<br><br><strong>Package:</strong> A directory containing multiple modules along with an `__init__.py` marker file, organizing large codebases cleanly.<br><br><strong>PyPI / `pip`:</strong> Python Package Index (the global repository of third-party open-source libraries) and `pip`, the terminal package manager used to install them (`pip install requests`).",
    "6856": "<strong>Class (`class`):</strong> A user-defined architectural blueprint or template defining data attributes and methods for objects.<br><br><strong>Object / Instance:</strong> A concrete realization of a class created in system memory (`car = Car('Red')`).<br><br><strong>Encapsulation:</strong> Bundling internal state data and methods within a class, restricting unauthorized external access using private prefixes (`_attribute`).",
    "6857": "<strong>`__init__(self, ...)` Constructor:</strong> The special initialization method called automatically whenever a new class instance is instantiated.<br><br><strong>`self` Parameter:</strong> The mandatory first parameter in instance methods representing the specific individual object instance calling the method.<br><br><strong>Instance vs. Class Attributes:</strong> Instance attributes belong to individual objects (`self.name`), whereas class attributes are shared globally across all instances of that class.",
    "6858": "<strong>REST API:</strong> Representational State Transfer Application Programming Interface; standard HTTP endpoints allowing software applications to communicate over the internet.<br><br><strong>HTTP Status Codes:</strong> Numerical codes returned by servers: `200 OK` (success), `404 Not Found` (missing resource), and `500 Internal Error` (server crash).<br><br><strong>`requests` Library:</strong> The industry-standard third-party HTTP client library in Python used to send GET and POST requests cleanly (`requests.get(url)`).",
    "6859": "<strong>PEP 8:</strong> Python Enhancement Proposal 8; the official style guide defining standard indentation (4 spaces), line limits (79 characters), and naming conventions (`snake_case`).<br><br><strong>`breakpoint()` / `pdb`:</strong> The built-in interactive debugger (`pdb`) triggered by calling `breakpoint()`, pausing execution in the terminal to inspect variables line by line (`n` for next, `c` for continue).<br><br><strong>`logging` vs `print()`:</strong> Professional application tracking (`logging.info()`, `logging.error()`) that includes timestamps and severity levels instead of ad-hoc `print()` statements."
}

QUESTIONS_DICT = {
    "6840": [
        ("[2] Why is Python considered an interpreted and dynamically typed language?", "Because the Python interpreter executes code line by line without prior compilation, and variable types are checked at runtime during value assignment rather than declared in advance."),
        ("[2] What is the purpose of the print() function and comments (#) in Python?", "The print() function outputs strings or values to the console screen, while comments prefixed with # provide human-readable documentation ignored by the interpreter.")
    ],
    "6841": [
        ("[2] How do you create and activate a virtual environment using python -m venv in the terminal?", "Run 'python -m venv venv' to create the folder, then activate it using 'venv\\Scripts\\activate' on Windows or 'source venv/bin/activate' on macOS/Linux."),
        ("[2] What is the difference between running interactive code in the REPL versus running a saved .py file?", "The REPL evaluates individual expressions line-by-line in real time for testing, whereas running 'python script.py' executes an entire saved source file from top to bottom.")
    ],
    "6842": [
        ("[2] What happens if you try to perform mathematical addition between a string and an integer (e.g., 'Age: ' + 25)?", "Python raises a TypeError because it does not implicitly convert numbers to strings; you must explicitly cast the integer using str(25)."),
        ("[2] How does the type() function help in debugging variable assignments?", "The type() function returns the exact type class of an object (e.g., <class 'float'>), verifying how Python interpreted the stored value.")
    ],
    "6843": [
        ("[2] What is the exact difference between standard division (/) and floor division (//)?", "Standard division (/) always returns a floating-point decimal (e.g., 10 / 2 returns 5.0), whereas floor division (//) truncates decimals to return an integer (10 // 3 returns 3)."),
        ("[2] How can you use the modulo operator (%) to check if an integer n is even or odd?", "By checking 'n % 2 == 0'. If the remainder is 0 when divided by 2, the number is even; if the remainder is 1, it is odd.")
    ],
    "6844": [
        ("[2] Explain what string slicing s[start:end:step] returns when s = 'PYTHON' and we evaluate s[1:4].", "It returns 'YTH'. Slicing starts inclusive at index 1 ('Y') and stops exclusive at index 4 ('O')."),
        ("[2] Why does executing text[0] = 'p' raise a TypeError on a string?", "Because strings in Python are immutable objects; you must construct and reassign a new string rather than modifying individual characters in place.")
    ],
    "6845": [
        ("[2] What is the difference between list methods .pop() and .remove(value)?", ".pop(index) removes and returns the item at a specific index (defaulting to the last item), whereas .remove(value) searches for and removes the first occurrence of that exact value."),
        ("[2] How does a list comprehension transform code readability and conciseness compared to a standard for loop?", "It replaces multi-line loop structures with a declarative, functional single line that filters and maps items simultaneously.")
    ],
    "6846": [
        ("[2] Why would a software engineer choose to use a tuple instead of a list for returning multiple values from a function?", "Tuples guarantee data immutability preventing accidental modification, require slightly less memory, and can be used as dictionary keys."),
        ("[2] What is the advantage of accessing dictionary values using .get(key, default) instead of direct indexing dict[key]?", ".get() safely returns a fallback default value (or None) if the key is missing, whereas dict[key] immediately crashes the application with a KeyError.")
    ],
    "6847": [
        ("[2] What is the difference between the equality check (==) and the identity check (is)?", "The == operator checks if two objects have equal values, whereas the is operator checks if both variables point to the exact same memory address."),
        ("[2] How does short-circuit evaluation optimize the expression: (x != 0) and (10 / x > 2)?", "If x is 0, the first condition (x != 0) evaluates to False. Python immediately stops (short-circuits) without evaluating (10 / x > 2), preventing a ZeroDivisionError.")
    ],
    "6848": [
        ("[2] Why must elif branches be ordered from most specific to least specific condition?", "Because Python evaluates top-to-bottom and executes only the first matching branch; if a broad condition comes first, subsequent specific conditions are permanently skipped."),
        ("[2] What happens if an if statement is missing the trailing colon (:) or has inconsistent indentation?", "The Python interpreter catches this during syntax parsing before execution and raises a SyntaxError or IndentationError.")
    ],
    "6849": [
        ("[2] When iterating through a list, why is using enumerate(items) superior to iterating over range(len(items))?", "enumerate() provides both the numerical index and the element directly in each step without requiring manual bracket indexing inside the loop."),
        ("[2] What numbers are printed when executing for i in range(2, 10, 3): print(i)?", "It prints 2, 5, and 8. The loop starts at 2, increments by step 3 each time, and stops strictly before reaching 10.")
    ],
    "6850": [
        ("[2] How does the break statement alter execution inside an interactive while True: loop?", "When encountered, break instantly halts loop iteration and transfers program control to the first line of code right outside the loop structure."),
        ("[2] Why is it dangerous to write a while loop without modifying the loop condition variable inside the block?", "Without updating the condition variable (like incrementing a counter or reading user input), the condition remains True forever, locking up the CPU in an infinite loop.")
    ],
    "6851": [
        ("[2] Why must default parameters always be placed AFTER non-default parameters in a function definition?", "To prevent syntactic ambiguity when parsing arguments; Python needs to unambiguously assign positional inputs to non-default parameters first before filling optional defaults."),
        ("[2] Why is it considered a severe anti-pattern to use a mutable default parameter like def append_item(val, lst=[]):?", "Because default parameter values are evaluated only once when the function is defined; the exact same list instance is reused across all subsequent calls, causing data leakage.")
    ],
    "6852": [
        ("[2] What is the difference between printing a value inside a function versus returning a value?", "print() only outputs text to the screen for human viewing (None is returned), whereas return passes actual data objects back into the calling code for further computation."),
        ("[2] Explain why attempting to modify a global variable inside a local function without the 'global' keyword raises an UnboundLocalError.", "When Python sees an assignment inside a function, it treats that variable as purely local by default; if you reference it before assigning it locally, Python throws an UnboundLocalError.")
    ],
    "6853": [
        ("[2] Why is opening files using the 'with open(filename) as file:' statement strongly preferred over manual file.open() and file.close()?", "The context manager guarantees that the operating system file handle is automatically and safely closed as soon as the block exits, even if an unhandled crash or exception occurs inside the block."),
        ("[2] What happens if you open an existing file in 'w' (write) mode versus 'a' (append) mode?", "'w' mode immediately wipes and truncates the entire existing file contents to zero length before writing, whereas 'a' mode preserves existing data and appends new content right at the end.")
    ],
    "6854": [
        ("[2] Why should professional code catch specific exceptions like ValueError rather than using a bare 'except:' clause?", "A bare except catches everything, including system exits and keyboard interrupts (Ctrl+C), hiding critical bugs and making debugging extremely difficult."),
        ("[2] What is the exact purpose of the 'finally:' block in an exception handling structure?", "The finally block executes unconditionally regardless of whether an exception was raised, caught, or ignored, making it essential for releasing system resources and closing database connections.")
    ],
    "6855": [
        ("[2] What is the difference between 'import math' and 'from math import sqrt'?", "'import math' brings in the module namespace requiring dot notation ('math.sqrt(16)'), whereas 'from math import sqrt' imports the specific function directly into the local namespace ('sqrt(16)')."),
        ("[2] What is the purpose of the requirements.txt file in a professional Python project?", "It lists every third-party package dependency along with exact version numbers, allowing teammates or production servers to replicate the exact environment instantly using 'pip install -r requirements.txt'.")
    ],
    "6856": [
        ("[2] What is the fundamental difference between a Class and an Instance Object in Object-Oriented Programming?", "A Class is an abstract design blueprint defining structure and behavior, while an Instance Object is a concrete, individual entity created from that blueprint residing in system memory."),
        ("[2] Why is Encapsulation considered a core pillar of reliable software engineering?", "It hides internal complexity and protects object state from invalid external modification, enforcing that data changes occur only through validated class methods.")
    ],
    "6857": [
        ("[2] What is the role of the self parameter inside Python class methods and the __init__ constructor?", "self explicitly references the individual object instance currently being created or acted upon, allowing methods to assign and read unique attributes on that specific instance."),
        ("[2] Why does changing a Class Attribute affect all instances unless overridden locally?", "Because class attributes live in the shared class memory namespace rather than individual instance dictionaries; modifying the class attribute updates the lookup value for all instances.")
    ],
    "6858": [
        ("[2] What is the purpose of response.raise_for_status() when making HTTP API calls with the requests library?", "It checks the HTTP response code and automatically raises an HTTPError exception if the server returned a 4xx client error or 5xx server error, preventing silent failures."),
        ("[2] Why do web APIs exchange data formatted as JSON rather than raw internal Python dictionaries or objects?", "JSON is a universal, language-independent text format supported across all programming languages, enabling Python servers to communicate seamlessly with JavaScript frontends or Java microservices.")
    ],
    "6859": [
        ("[2] Why is using Python's logging module ('logging.info()') superior to using print() statements in production software?", "Logging categorizes messages by severity levels (INFO, WARNING, ERROR), attaches precise timestamps, and can write output directly to monitoring log files without cluttering console output."),
        ("[2] How does inserting breakpoint() inside a function streamline the debugging process compared to scattering print() statements?", "It pauses execution instantly at the exact suspicious line, opening an interactive debugger session where developers can step through code line-by-line and inspect live memory states.")
    ]
}

FILENAME_DICT = {
    "6840": "hello_python.py",
    "6841": "setup_env.sh",
    "6842": "variables_demo.py",
    "6843": "arithmetic_calc.py",
    "6844": "string_ops.py",
    "6845": "lists_and_comprehensions.py",
    "6846": "tuples_and_dicts.py",
    "6847": "boolean_comparisons.py",
    "6848": "conditionals_check.py",
    "6849": "for_loops_demo.py",
    "6850": "while_loop_game.py",
    "6851": "functions_params.py",
    "6852": "return_and_scope.py",
    "6853": "file_io_manager.py",
    "6854": "exception_handler.py",
    "6855": "module_importer.py",
    "6856": "oop_car_class.py",
    "6857": "bank_account.py",
    "6858": "api_fetch_weather.py",
    "6859": "professional_logging.py"
}

def process_chunk_for_blocks(blocks, chunk_html, page_id, section_title):
    code_matches = list(re.finditer(r'<pre><code class="language-([a-zA-Z0-9_-]+)">(.*?)</code></pre>', chunk_html, flags=re.DOTALL))
    if not code_matches:
        if chunk_html.strip():
            blocks.append({
                "type": "text",
                "text": chunk_html.strip()
            })
        return
        
    last_idx = 0
    code_idx = 1
    for match in code_matches:
        start, end = match.span()
        before_text = chunk_html[last_idx:start].strip()
        if before_text:
            blocks.append({
                "type": "text",
                "text": before_text
            })
        lang = match.group(1)
        raw_code = match.group(2)
        clean_code = raw_code.strip().replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#039;', "'")
        
        fname = FILENAME_DICT.get(page_id, "script.py")
        if code_idx > 1:
            if "." in fname:
                base, ext = fname.rsplit(".", 1)
                fname = f"{base}_{code_idx}.{ext}"
            else:
                fname = f"{fname}_{code_idx}"
                
        blocks.append({
            "type": "code",
            "language": lang,
            "title": f"Code Example: {section_title}" if code_idx == 1 else f"Code Example ({code_idx}): {section_title}",
            "filename": fname,
            "code": clean_code
        })
        last_idx = end
        code_idx += 1
        
    after_text = chunk_html[last_idx:].strip()
    if after_text:
        blocks.append({
            "type": "text",
            "text": after_text
        })

def build_rich_blocks(page_id, title, topic_number, content_html):
    blocks = []
    # 1. Main Page Title
    blocks.append({
        "type": "heading",
        "level": 1,
        "text": title
    })
    
    # 2. Vocabulary & Key Terms Sidebox
    if page_id in VOCAB_DICT:
        blocks.append({
            "type": "sidebox",
            "style": "vocab",
            "title": "Vocabulary & Key Terms",
            "text": VOCAB_DICT[page_id]
        })
        
    # 3. Parse HTML into sections by <h2> tags
    parts = re.split(r'<h2>(.*?)</h2>', content_html, flags=re.DOTALL)
    
    first_chunk = parts[0].strip()
    if first_chunk:
        process_chunk_for_blocks(blocks, first_chunk, page_id, "Introduction")
        
    for i in range(1, len(parts), 2):
        h2_title = parts[i].strip()
        body_chunk = parts[i+1].strip() if i+1 < len(parts) else ""
        
        if "Key Takeaways" in h2_title:
            blocks.append({
                "type": "sidebox",
                "style": "study",
                "title": "Key Takeaways",
                "text": body_chunk
            })
        elif "Congratulations" in h2_title:
            blocks.append({
                "type": "heading",
                "level": 2,
                "text": h2_title
            })
            if body_chunk:
                blocks.append({
                    "type": "text",
                    "text": body_chunk
                })
        else:
            blocks.append({
                "type": "heading",
                "level": 2,
                "text": h2_title
            })
            process_chunk_for_blocks(blocks, body_chunk, page_id, h2_title)
            
    # 4. Add Practice Questions
    if page_id in QUESTIONS_DICT:
        for q_text, q_ans in QUESTIONS_DICT[page_id]:
            blocks.append({
                "type": "question",
                "text": q_text,
                "answer": q_ans
            })
            
    return blocks

def trim_blocks_to_limit(blocks, max_chars=4950):
    while True:
        total = sum(
            len(b.get("text", "")) + len(b.get("code", "")) + len(b.get("answer", ""))
            for b in blocks
        )
        if total <= max_chars:
            break
            
        # Find the longest text block that is > 200 chars
        text_blocks = [(i, b) for i, b in enumerate(blocks) if b.get("type") == "text"]
        if not text_blocks:
            break
        text_blocks.sort(key=lambda x: len(x[1].get("text", "")), reverse=True)
        longest_idx, longest_b = text_blocks[0]
        txt = longest_b["text"]
        if len(txt) <= 200:
            break
            
        if txt.endswith("</p>"):
            inner = txt[:-4].rstrip()
            last_period = inner.rfind('.', 0, len(inner) - 10)
            if last_period != -1 and last_period > 100:
                longest_b["text"] = inner[:last_period + 1] + "</p>"
            else:
                longest_b["text"] = inner[:len(inner)-100].rstrip() + "...</p>"
        else:
            last_period = txt.rfind('.', 0, len(txt) - 10)
            if last_period != -1 and last_period > 100:
                longest_b["text"] = txt[:last_period + 1]
            else:
                longest_b["text"] = txt[:len(txt)-100].rstrip() + "..."

def block_to_html(b):
    btype = b.get("type")
    if btype == "heading":
        lvl = b.get("level", 2)
        return f"<h{lvl}>{b.get('text', '')}</h{lvl}>"
    elif btype == "text":
        return b.get("text", "")
    elif btype == "code":
        lang = b.get("language", "python")
        code = b.get("code", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<pre><code class="language-{lang}">{code}</code></pre>'
    elif btype == "sidebox":
        title = b.get("title", "Sidebox")
        text = b.get("text", "")
        return f'<div class="sidebox {b.get("style", "study")}"><h4>{title}</h4> {text}</div>'
    elif btype == "question":
        return f'<div class="question"><strong>{b.get("text", "")}</strong> <p><em>Answer:</em> {b.get("answer", "")}</p></div>'
    return ""

def main():
    pages = get_pages_data()
    print(f"Loaded {len(pages)} pages data.")
    
    # 1. Ensure master book directory exists
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    
    book_pages_list = []
    
    for page in pages:
        page_id = page["id"]
        title = page["title"]
        topic_number = page["topic_number"]
        section_title = page["section_title"]
        unit_title = page["unit_title"]
        content_html = page["content_html"]
        
        blocks = build_rich_blocks(page_id, title, topic_number, content_html)
        trim_blocks_to_limit(blocks, max_chars=4950)
        content_html = "\n\n".join(block_to_html(b) for b in blocks)
        
        # Calculate character count across all blocks (text + code + sideboxes + questions)
        char_count = sum(
            len(b.get("text", "")) + len(b.get("code", "")) + len(b.get("answer", ""))
            for b in blocks
        )
        reading_time = max(1, round(char_count / 650))
        
        # Build Navigation Array
        navigation = [
            {
                "href": "https://app.growhall.com/books/python_basics",
                "level": 1,
                "text": "Python Basics"
            },
            {
                "href": f"https://app.growhall.com/books/python_basics/{page_id}",
                "level": 2,
                "text": unit_title
            },
            {
                "href": f"https://app.growhall.com/books/python_basics/{page_id}",
                "level": 3,
                "text": section_title
            },
            {
                "href": f"https://app.growhall.com/books/python_basics/{page_id}",
                "level": 4,
                "text": f"{topic_number} {title}"
            }
        ]
        
        content_data = {
            "url": f"https://app.growhall.com/books/python_basics/{page_id}",
            "scraped_at": "2026-07-12T00:00:00.000000",
            "title": title,
            "topic_number": topic_number,
            "section_title": section_title,
            "main_heading": title,
            "navigation": navigation,
            "content_html": content_html,
            "blocks": blocks
        }
        
        # Create page directory and write content.json
        page_dir = BOOK_DIR / page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        content_json_path = page_dir / "content.json"
        
        with open(content_json_path, "w", encoding="utf-8") as f:
            json.dump(content_data, f, indent=2, ensure_ascii=False)
            
        print(f"Created page {page_id} ({topic_number} {title}): {char_count} chars, {reading_time} min")
        
        # Append entry for book.json
        book_pages_list.append({
            "id": page_id,
            "title": f"{topic_number} {title}",
            "url": f"https://app.growhall.com/books/python_basics/{page_id}",
            "folder": page_id,
            "reading_time_minutes": reading_time,
            "character_count": char_count
        })
        
    # 2. Write master book.json
    book_json_data = {
        "id": "python_basics",
        "title": "Python Basics",
        "url": "https://app.growhall.com/books/python_basics",
        "updated_at": "2026-07-12",
        "created_at": "2026-07-12T00:00:00.000000",
        "pages": book_pages_list
    }
    
    book_json_path = BOOK_DIR / "book.json"
    with open(book_json_path, "w", encoding="utf-8") as f:
        json.dump(book_json_data, f, indent=2, ensure_ascii=False)
    print(f"Created {book_json_path} with {len(book_pages_list)} pages.")
    
    # 3. Update data/books.json
    books_json_path = BASE_DIR / "books.json"
    if books_json_path.exists():
        with open(books_json_path, "r", encoding="utf-8") as f:
            books_data = json.load(f)
    else:
        books_data = {"books": [], "last_updated": "2026-07-12T00:00:00.000000"}
        
    # Check if python_basics is already in books array
    existing_entry = None
    for b in books_data.get("books", []):
        if b.get("id") == "python_basics":
            existing_entry = b
            break
            
    new_book_entry = {
        "id": "python_basics",
        "title": "Python Basics",
        "url": "https://app.growhall.com/books/python_basics",
        "pages_count": 20,
        "folder": "Book_python_basics",
        "created_at": "2026-07-12T00:00:00.000000",
        "cover_image": None,
        "color_from": "#3776ab",
        "color_to": "#1e5cb8"
    }
    
    if existing_entry:
        existing_entry.update(new_book_entry)
        print("Updated existing python_basics entry in books.json.")
    else:
        books_data["books"].append(new_book_entry)
        print("Added new python_basics entry to books.json.")
        
    books_data["last_updated"] = "2026-07-12T00:00:00.000000"
    
    with open(books_json_path, "w", encoding="utf-8") as f:
        json.dump(books_data, f, indent=2, ensure_ascii=False)
    print("Updated data/books.json completely.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate the complete educational book structure for Advanced Python: Object-Oriented Programming (OOP)."""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Base directory setup
BASE_DIR = Path(r"C:\Users\Colin\webscraper\data")
BOOK_FOLDER_NAME = "Book_python_advanced_oop"
BOOK_DIR = BASE_DIR / BOOK_FOLDER_NAME

VOCAB_DICT = {
    "6860": "<strong>Class vs. Instance:</strong> A class is an abstract architectural blueprint defining data structure and behavior, while an instance is a concrete realization of that blueprint residing at a specific memory address.<br><br><strong>Encapsulation & State:</strong> Encapsulation binds state (`attributes`) and behavior (`methods`) together within a unified boundary, protecting object integrity from unauthorized external mutation.<br><br><strong>Message Passing:</strong> The mechanism by which objects interact; rather than directly altering another object's internal state, an object invokes a method on target instances.",
    "6861": "<strong>`__new__(cls, ...)`:</strong> The static allocation hook called before `__init__` responsible for instantiating and returning a new object from memory (`super().__new__(cls)`).<br><br><strong>`__init__(self, ...)`:</strong> The initializer method invoked immediately after allocation to populate instance attributes on the newly created object.<br><br><strong>Two-Phase Instantiation:</strong> Python's object creation pipeline where `__new__` allocates memory and `__init__` initializes state.",
    "6862": "<strong>Instance Method:</strong> A regular class method taking `self` as its first parameter, capable of reading or modifying both instance and class state.<br><br><strong>`@classmethod`:</strong> A method decorated with `@classmethod` taking `cls` as its first parameter, widely used for alternative factory constructors and mutating class-level attributes.<br><br><strong>`@staticmethod`:</strong> A self-contained utility function housed inside a class namespace that receives neither `self` nor `cls` implicit binding.",
    "6863": "<strong>`__dict__`:</strong> The internal hash table (dictionary) stored on every standard object instance where attributes and values are dynamically tracked.<br><br><strong>`__slots__`:</strong> A tuple attribute defined at class level (`__slots__ = ('name', 'age')`) that eliminates per-instance dictionaries, allocating fixed memory slots to drastically reduce RAM consumption.<br><br><strong>Attribute Lookup Chain:</strong> Python's search sequence when resolving `obj.attr`: instance `__dict__`, class namespace, and Method Resolution Order (MRO) hierarchy.",
    "6864": "<strong>Protected Convention (`_attr`):</strong> A single leading underscore signaling to developers that an attribute is intended for internal use only by the class and its subclasses.<br><br><strong>Private Name Mangling (`__attr`):</strong> Double leading underscores causing Python's compiler to internally rewrite the attribute name to `_ClassName__attr`, preventing accidental collisions in inheritance trees.<br><br><strong>Access Modifiers:</strong> Python relies on developer consensus and name mangling rather than strict compiler-enforced access restrictions (`public`, `private`, `protected`).",
    "6865": "<strong>`@property`:</strong> A built-in decorator transforming a getter method into an attribute lookup, enabling computed values and access validation without altering client syntax (`obj.attr`).<br><br><strong>`@attr.setter`:</strong> A decorator paired with `@property` intercepting assignment (`obj.attr = val`), enforcing validation rules, type checking, or triggering notifications.<br><br><strong>Read-Only Property:</strong> A property defining only a getter method without a corresponding `@attr.setter`, preventing external modification after instantiation.",
    "6866": "<strong>Descriptor Protocol:</strong> Classes implementing any combination of `__get__(self, instance, owner)`, `__set__(self, instance, value)`, or `__delete__(self, instance)` to govern attribute access.<br><br><strong>Data vs. Non-Data Descriptors:</strong> Data descriptors define both `__get__` and `__set__` (taking precedence over instance `__dict__`), whereas non-data descriptors define only `__get__` (used by standard functions and methods).<br><br><strong>Attribute Interception:</strong> The low-level engine empowering `@property`, `@classmethod`, and ORM field mappings across advanced Python frameworks.",
    "6867": "<strong>`__repr__(self)`:</strong> The unambiguous developer representation intended for debugging and logging, which should ideally evaluate back to an identical object when passed to `eval()`.<br><br><strong>`__str__(self)`:</strong> The human-readable string display used when calling `print()` or `str()`, prioritizing clean presentation over technical precision.<br><br><strong>`__format__(self, format_spec)`:</strong> The hook invoked during f-string evaluations (`f'{obj:spec}'`) and `format()` calls, enabling custom formatting specifications.",
    "6868": "<strong>Operator Overloading:</strong> Implementing magic dunder methods (`__add__`, `__sub__`, `__mul__`) allowing user-defined objects to respond natively to standard mathematical and logical operators.<br><br><strong>Rich Comparisons (`__eq__`, `__lt__`):</strong> Methods defining object equality and ordering (`<`, `<=`, `>`, `>=`), often streamlined using `@functools.total_ordering`.<br><br><strong>Reverse Arithmetic (`__radd__`):</strong> Fallback methods triggered when the left operand does not support the operation with the right operand's type (`2 + obj`).",
    "6869": "<strong>Container Protocols:</strong> Implementing `__len__` and `__getitem__` so objects behave like native sequences or mappings accessible via square brackets (`obj[key]`).<br><br><strong>`__iter__` & `__next__`:</strong> The Iterator protocol requiring `__iter__` to return the iterator object and `__next__` to yield consecutive values until raising `StopIteration`.<br><br><strong>`__contains__(self, item)`:</strong> The membership testing hook powering the `in` operator (`if item in container:`).",
    "6870": "<strong>Inheritance (`class Child(Parent):`):</strong> A structural relationship where a derived subclass acquires all attributes and methods of a parent base class.<br><br><strong>Method Overriding:</strong> Defining a method in a subclass with the exact same name as a superclass method, replacing or extending parental behavior.<br><br><strong>`super().__init__(...)`:</strong> The proxy function `super()` delegating method calls up to the next parent class in the inheritance hierarchy without hardcoding class names.",
    "6871": "<strong>Multiple Inheritance:</strong> A subclass deriving directly from two or more distinct base classes (`class Sub(Base1, Base2):`).<br><br><strong>C3 Linearization Algorithm:</strong> Python's deterministic algorithm calculating the Method Resolution Order (MRO), ensuring monotonic inheritance traversal without ambiguity.<br><br><strong>Mixin Class:</strong> A specialized parent class designed solely to provide discrete utility methods across multiple unrelated hierarchies without instantiating independently.",
    "6872": "<strong>Abstract Base Class (`abc.ABC`):</strong> A class that cannot be instantiated directly, serving as a formal structural interface for concrete subclasses.<br><br><strong>`@abstractmethod`:</strong> A decorator requiring any derived subclass to explicitly implement the marked method before instantiation is permitted.<br><br><strong>Virtual Subclass Registration:</strong> Using `ABCMeta.register(ConcreteClass)` to formally recognize an external class as implementing an ABC without structural inheritance.",
    "6873": "<strong>Nominal vs. Structural Typing:</strong> Nominal typing verifies type compatibility via explicit class inheritance trees, whereas structural typing checks if an object implements required methods (`Duck Typing`).<br><br><strong>`typing.Protocol`:</strong> PEP 544 static type checking definitions where classes satisfy type contracts simply by possessing matching method signatures.<br><br><strong>`@runtime_checkable`:</strong> A decorator allowing `isinstance(obj, MyProtocol)` evaluations at runtime based on structural method existence.",
    "6874": "<strong>Composition (`Has-A` Relationship):</strong> Building complex classes by assembling private instance attributes containing references to other distinct, self-contained objects.<br><br><strong>Inheritance (`Is-A` Relationship):</strong> Deriving specialization hierarchies where child classes are conceptual subtypes of their parent (`Dog` is an `Animal`).<br><br><strong>Delegation & Forwarding:</strong> Intercepting unknown attribute requests via `__getattr__` and forwarding method executions to internal composed objects.",
    "6875": "<strong>`@dataclass`:</strong> A built-in class decorator automatically generating standard dunders (`__init__`, `__repr__`, `__eq__`) based on annotated type declarations.<br><br><strong>`field(default_factory=...)`:</strong> A helper function specifying mutable default values (`list`, `dict`) or customizing attribute comparisons inside dataclasses.<br><br><strong>`__post_init__(self)`:</strong> A lifecycle hook executed automatically at the end of the generated `__init__` constructor for validation and computed field assignments.",
    "6876": "<strong>`enum.Enum`:</strong> A class representing a fixed set of immutable, symbolically named constant members (`Status.PENDING`), eliminating magic string errors.<br><br><strong>`enum.Flag`:</strong> An enumeration supporting bitwise operations (`|`, `&`, `~`), allowing multiple combined flags to be stored within a single value.<br><br><strong>`enum.auto()`:</strong> A helper automatically assigning distinct incremental integer values (`1, 2, 3...`) to sequential enum members.",
    "6877": "<strong>Metaclass (`type`):</strong> The class of a class; the factory object that creates, configures, and instantiates class objects in system memory (`class MyClass(metaclass=Meta):`).<br><br><strong>`type(name, bases, dict)`:</strong> The dynamic three-argument constructor used by Python to instantiate new class objects programmatically.<br><br><strong>`__init_subclass__(cls, **kwargs)`:</strong> A modern class hook executed whenever a subclass is defined, enabling clean class registration without metaclass complexity.",
    "6878": "<strong>Singleton Pattern:</strong> Ensuring a class has only one instantiated instance globally across the application lifecycle (`MetaSingleton` or module cache).<br><br><strong>Factory Pattern:</strong> Decoupling object creation from client usage by delegating instantiation logic to specialized factory classes or `@classmethod` constructors.<br><br><strong>Strategy & Observer Patterns:</strong> Behavior patterns encapsulating interchangeable algorithms into distinct classes or notifying registered subscribers when object state mutates.",
    "6879": "<strong>Reference Cycles:</strong> Circular memory references where two objects reference each other (`A -> B -> A`), preventing immediate reference-counted cleanup (`gc.collect()`).<br><br><strong>`weakref.ref(obj)`:</strong> A non-owning reference to an object that does not increment its reference count, allowing garbage collection to reclaim the object when no strong references remain.<br><br><strong>`WeakKeyDictionary`:</strong> A specialized mapping that automatically removes entries when key objects are garbage collected, ideal for caching instance metadata without memory leaks."
}

QUESTIONS_DICT = {
    "6860": [
        ("[2] Explain the fundamental architectural distinction between a Class and an Instance Object in Python.", "A Class is an abstract design blueprint defining structure, attributes, and behavior, whereas an Instance is a concrete realization of that class residing at a specific memory address with unique state."),
        ("[2] How does encapsulation protect object state integrity inside complex software systems?", "Encapsulation bundles data and methods together within a single boundary, restricting direct unauthorized external modification and enforcing that state changes occur only through validated methods.")
    ],
    "6861": [
        ("[2] Why does Python separate object instantiation into two distinct phases (`__new__` and `__init__`)?", "Because `__new__` is responsible for allocating and creating the raw memory instance from `type`, while `__init__` is invoked afterward to populate initial state attributes on that allocated instance."),
        ("[2] Under what specific circumstances must a developer explicitly override the static `__new__` method?", "When subclassing immutable built-in types (`str`, `int`, `tuple`) whose values cannot be changed after allocation, or when implementing singleton/metaclass caching architectures.")
    ],
    "6862": [
        ("[2] What is the exact difference between how `@classmethod` and `@staticmethod` bind to class namespaces?", "`@classmethod` receives the class object (`cls`) as its implicit first argument and can access class attributes, whereas `@staticmethod` receives no implicit binding and acts as a pure utility function inside the class namespace."),
        ("[2] Why is `@classmethod` widely considered the idiomatic approach for creating alternative constructors in Python?", "Because `cls` is passed dynamically; if a subclass calls the class method, `cls` evaluates to the subclass, ensuring alternative constructors instantiate the correct derived class type.")
    ],
    "6863": [
        ("[2] How does defining `__slots__ = ('name', 'age')` dramatically reduce RAM overhead for millions of instances?", "By instructing Python not to allocate a dynamic per-instance `__dict__` hash table for each object, instead storing attributes inside fixed-size memory array slots similar to C structs."),
        ("[2] What trade-offs or restrictions occur when a class adopts `__slots__`?", "Instances cannot dynamically acquire new attributes at runtime outside the pre-declared tuple, and multiple inheritance with conflicting `__slots__` can lead to complex layout errors.")
    ],
    "6864": [
        ("[2] What happens internally during bytecode compilation when a developer defines an attribute starting with double underscores (e.g., `__secret`)?", "Python's compiler performs name mangling, transforming the internal symbol name to `_ClassName__secret` to prevent accidental overwrites by derived subclasses in inheritance hierarchies."),
        ("[2] Why is relying on single leading underscores (`_internal`) preferred over double underscores (`__private`) for general encapsulation?", "Single leading underscores clearly communicate developer intent that an attribute is protected without complicating debugging or preventing legitimate subclass extensions through name mangling.")
    ],
    "6865": [
        ("[2] How does Python's `@property` decorator allow developers to evolve public attributes into validated getter/setter methods without breaking API contracts?", "By intercepting standard attribute access syntax (`obj.attr`), allowing internal validation or computation hooks to run while clients continue using clean dot-notation instead of calling explicit methods (`obj.get_attr()`)."),
        ("[2] How do you create a read-only property using decorators in Python?", "Define the getter method with `@property` and deliberately omit defining any corresponding `@attr.setter` method; any assignment attempt (`obj.attr = val`) will raise an `AttributeError`.")
    ],
    "6866": [
        ("[2] What distinguishes a Data Descriptor from a Non-Data Descriptor in Python's attribute lookup rules?", "A Data Descriptor defines `__set__` or `__delete__` alongside `__get__` and takes priority over an instance's `__dict__`, whereas a Non-Data Descriptor defines only `__get__` and is overridden by instance `__dict__` attributes."),
        ("[2] How does the Descriptor Protocol power Python's built-in `property` and `classmethod` decorators under the hood?", "`property` and `classmethod` are classes implementing the `__get__` descriptor method; when accessed from an instance or class, their `__get__` hook intercepts the lookup and returns the bound function or computed value.")
    ],
    "6867": [
        ("[2] Why should the string returned by `__repr__(self)` ideally evaluate (`eval()`) back to an identical object whenever feasible?", "To maintain an unambiguous developer contract where debugging logs and REPL outputs provide the exact constructor syntax required to recreate the object's precise state."),
        ("[2] When a class defines both `__repr__` and `__str__`, which method is executed when an object is passed to `print()` or an f-string?", "`print()` and standard f-strings (`f'{obj}'`) invoke `__str__(self)`; if `__str__` is not explicitly defined, Python falls back to executing `__repr__(self)` automatically.")
    ],
    "6868": [
        ("[2] Why must `__eq__` and comparison dunder methods (`__lt__`) return the special singleton `NotImplemented` instead of raising a `TypeError` when dealing with unrecognized types?", "Returning `NotImplemented` signals Python's evaluation engine to fall back and check if the right operand implements the reflected comparison (`__gt__` or `__eq__`) before raising an exception."),
        ("[2] When is the reverse arithmetic dunder method (`__radd__(self, other)`) invoked during evaluation of `a + b`?", "When the left operand (`a`) does not support addition with `b`'s type (`a.__add__(b)` returns `NotImplemented`) and `b` is not a direct subclass of `a`.")
    ],
    "6869": [
        ("[2] How do the `__len__` and `__getitem__` methods enable user-defined classes to behave seamlessly like native Python lists or dictionaries?", "`__len__` allows `len(obj)` to report item count, while `__getitem__(self, key)` intercepts square bracket indexing (`obj[key]`), enabling iteration and slicing operations natively."),
        ("[2] What is the difference between an Iterable (`__iter__`) and an Iterator (`__iter__` plus `__next__`)?", "An Iterable defines `__iter__` which returns a fresh Iterator object, while an Iterator defines `__next__` yielding consecutive items on each call until raising `StopIteration`.")
    ],
    "6870": [
        ("[2] Why is using `super().__init__(...)` inside a subclass constructor superior to explicitly calling `Parent.__init__(self, ...)`?", "`super()` dynamically computes method resolution based on the hierarchy, correctly handling cooperative multiple inheritance and preventing hardcoded base class dependencies."),
        ("[2] According to the Liskov Substitution Principle (LSP), what condition must hold true when overriding parent methods in a derived subclass?", "A subclass must be fully substitutable for its superclass without breaking client functionality; overridden methods must accept compatible parameters and return expected contract types.")
    ],
    "6871": [
        ("[2] What is the Diamond Problem in multiple inheritance, and how does Python's C3 Linearization Algorithm resolve it?", "The Diamond Problem occurs when a class inherits from two parents sharing a common base class; C3 Linearization computes a deterministic, monotonic Method Resolution Order (`__mro__`) ensuring each class is visited exactly once in right-to-left order."),
        ("[2] What makes a class qualify as a Mixin inside a multiple inheritance architecture?", "A Mixin is a self-contained utility class designed specifically to provide discrete methods (`ToDictMixin`, `JsonSerializerMixin`) to subclasses without having independent state or being instantiated on its own.")
    ],
    "6872": [
        ("[2] What happens if a developer attempts to instantiate a subclass inheriting from `abc.ABC` that fails to implement an `@abstractmethod`?", "Python intercepts the instantiation during `__new__` allocation and immediately raises a `TypeError`, stating that abstract methods have not been implemented."),
        ("[2] How does `ABCMeta.register(ConcreteClass)` allow external third-party classes to satisfy abstract interfaces without direct inheritance?", "Registration adds the external class to the ABC's virtual subclass registry, causing `isinstance(obj, MyABC)` and `issubclass(ConcreteClass, MyABC)` to return `True` at runtime without modifying class definitions.")
    ],
    "6873": [
        ("[2] Explain the difference between Nominal Typing (via `abc.ABC`) and Structural Typing (via `typing.Protocol`).", "Nominal typing requires explicit class inheritance (`class Dog(Animal):`), whereas structural typing (`Protocol`) verifies only that the object possesses matching method signatures and attributes regardless of inheritance."),
        ("[2] What does applying the `@runtime_checkable` decorator to a `typing.Protocol` enable during program execution?", "It allows developers to perform `isinstance(obj, MyProtocol)` evaluations at runtime, where Python verifies that the instance possesses attributes matching the protocol's declared methods.")
    ],
    "6874": [
        ("[2] Why is the architectural principle 'Favor Composition over Inheritance' widely recommended in modern object-oriented system design?", "Composition (`Has-A`) couples objects loosely via interchangeable internal references rather than locking classes into rigid, fragile multi-level inheritance (`Is-A`) hierarchies that resist future refactoring."),
        ("[2] How can a composed class use `__getattr__(self, name)` to cleanly delegate method executions to an internal component?", "When an attribute or method lookup fails on the outer class, `__getattr__` intercepts the request and dynamically forwards `getattr(self._internal_component, name)` to the composed inner object.")
    ],
    "6875": [
        ("[2] What dunder methods does the `@dataclass` decorator automatically synthesize on a class based on its type hints?", "It automatically generates a comprehensive `__init__` constructor, an informative `__repr__` display string, and `__eq__` equality testing methods by default."),
        ("[2] Why must mutable default attributes (such as lists or dictionaries) inside a `@dataclass` be assigned using `field(default_factory=list)` instead of `items: list = []`?", "To ensure every instantiated object receives a unique, independent mutable collection instance; assigning `items: list = []` would share a single global list object across all class instances.")
    ],
    "6876": [
        ("[2] What advantage does `enum.Enum` provide over using plain integers (`STATUS_READY = 1`) or strings inside application code?", "Enums provide immutable, self-documenting constant members (`Status.READY`) that prevent accidental invalid value assignments, support clean iterations, and ensure type safety."),
        ("[2] How does `enum.Flag` allow multiple distinct status options to be combined and checked within a single enumeration variable?", "By assigning powers-of-two bitwise values (`1, 2, 4, 8...`), allowing bitwise OR (`Flag.A | Flag.B`) to combine options and bitwise AND (`if val & Flag.A:`) to verify membership cleanly.")
    ],
    "6877": [
        ("[2] What is the difference between `type` when called with one argument vs. three arguments (`type(name, bases, dict)`)?", "With one argument (`type(obj)`), it returns the class type of the object; with three arguments (`type('Car', (object,), {...})`), it acts as a dynamic factory instantiating and returning a brand new class object."),
        ("[2] How does the `__init_subclass__(cls, **kwargs)` hook simplify class registration patterns compared to writing custom Metaclasses?", "`__init_subclass__` is defined directly inside a base class and runs automatically whenever any child subclass is defined, eliminating the need to write complex `metaclass=` boilerplate or override `type.__new__`.")
    ],
    "6878": [
        ("[2] How does implementing the Strategy Pattern via Python first-class functions or classes make software more adaptable and maintainable?", "It encapsulates interchangeable algorithms into separate classes or function objects that can be dynamically injected into context objects at runtime, eliminating massive `if/elif` conditional chains."),
        ("[2] What is the core mechanism of the Observer (Pub/Sub) Design Pattern in Pythonic OOP?", "A Subject class maintains a registry of Observer instances or callback functions and automatically invokes a notification method (`observer.update()`) across all subscribers whenever the Subject's internal state changes.")
    ],
    "6879": [
        ("[2] How do circular references (`A._parent = B` and `B._child = A`) prevent immediate reference-counted memory deallocation (`gc.collect()`)?", "Because each object's reference count remains at least `1` due to the mutual link, Python's immediate reference-counting collector cannot free them; they must wait for the cyclic garbage collection sweep."),
        ("[2] Why is storing large cached instance metadata inside a `weakref.WeakKeyDictionary` superior to using a standard Python `dict`?", "A `WeakKeyDictionary` holds weak references to its keys; when all external strong references to an instance drop to zero, the dictionary automatically deletes the cached entry, preventing catastrophic memory leaks.")
    ]
}

FILENAME_DICT = {
    "6860": "oop_paradigm_intro.py",
    "6861": "class_lifecycle_new.py",
    "6862": "method_types_demo.py",
    "6863": "slots_vs_dict.py",
    "6864": "encapsulation_mangling.py",
    "6865": "property_descriptors.py",
    "6866": "custom_validator_descriptor.py",
    "6867": "repr_vs_str_dunders.py",
    "6868": "operator_overloading_vector.py",
    "6869": "custom_sequence_iterator.py",
    "6870": "super_inheritance.py",
    "6871": "multiple_inheritance_mro.py",
    "6872": "abstract_base_classes.py",
    "6873": "typing_protocols.py",
    "6874": "composition_delegation.py",
    "6875": "dataclasses_advanced.py",
    "6876": "enum_flags_demo.py",
    "6877": "metaclasses_and_hooks.py",
    "6878": "strategy_observer_patterns.py",
    "6879": "weakref_memory_management.py"
}

def get_pages_data():
    pages = []
    
    # Page 1: 6860 - The Object-Oriented Paradigm
    p1_html = '''
<h2>Welcome to Advanced Python OOP</h2>
<p>In modern software engineering, mastering syntax is only the first step. As systems grow from hundreds of lines of code into complex, distributed architectures of hundreds of thousands of lines, procedural scripts inevitably buckle under their own weight. This is where <strong>Object-Oriented Programming (OOP)</strong> becomes indispensable.</p>
<p>At its absolute core, OOP is a paradigm that models software systems around state and behavior. Instead of passing passive dictionaries and lists through labyrinthine chains of disjointed functions, OOP unifies data (`attributes`) and the functions that manipulate that data (`methods`) into cohesive, self-contained entities called **objects**.</p>

<h2>Classes vs. Instances: The Memory Blueprint</h2>
<p>To write advanced Python code, you must maintain a crystal-clear distinction between a **Class** and an **Instance**:
<ul>
  <li><strong>The Class (`type` object):</strong> A class is a living blueprint residing in memory. When Python executes a `class Car:` definition, it creates a single, global `type` object containing shared methods, docstrings, and class-level attributes.</li>
  <li><strong>The Instance (`Car()` object):</strong> An instance is a concrete allocation of memory created from the class blueprint. Instantiating `Car()` ten times creates ten distinct memory instances, each possessing an independent hash table (`__dict__`) to store its unique state.</li>
</ul></p>

<h2>The Four Pillars of Pythonic OOP</h2>
<p>While traditional OOP languages like Java or C++ enforce rigid, compiler-checked rules, Python embraces a flexible, dynamic design anchored by four universal pillars:</p>
<ol>
  <li><strong>Encapsulation:</strong> Grouping state and behavior together while concealing internal implementation details from external actors.</li>
  <li><strong>Abstraction:</strong> Exposing clean, high-level interfaces (`device.turn_on()`) while hiding complex low-level mechanics (`voltage calibration`, `circuit handshakes`).</li>
  <li><strong>Inheritance:</strong> Creating specialized derived classes that extend, refine, or override parental behavior without duplicating code across hierarchies.</li>
  <li><strong>Polymorphism:</strong> Designing objects of distinct types that respond seamlessly to identical method signatures (`Duck Typing`), allowing polymorphic processing pipelines.</li>
</ol>

<pre><code class="language-python"># Demonstrating Class vs Instance State and Behavior
class ServerNode:
    # Class Attribute: Shared across every instantiated node in system memory
    active_nodes = 0

    def __init__(self, node_id: str, ip_address: str):
        # Instance Attributes: Unique state bound to this specific instance
        self.node_id = node_id
        self.ip_address = ip_address
        self.is_online = False
        
        # Increment shared class counter upon instantiation
        ServerNode.active_nodes += 1

    def boot(self) -> str:
        """Instance method altering object state via self binding."""
        self.is_online = True
        return f"Node [{self.node_id}] at {self.ip_address} successfully booted."

    def shutdown(self) -> str:
        self.is_online = False
        return f"Node [{self.node_id}] safely powered down."

# Instantiating distinct objects from the shared ServerNode blueprint
node_alpha = ServerNode("US-East-1A", "192.168.1.101")
node_beta = ServerNode("EU-West-2B", "10.0.4.205")

print(node_alpha.boot())
print(node_beta.boot())
print(f"Total Active Server Nodes Housed in Cluster: {ServerNode.active_nodes}")
</code></pre>

<h2>Message Passing and State Integrity</h2>
<p>In advanced architectural design, objects should interact exclusively via **Message Passing**. Rather than external code directly modifying an object's internal state (`node.is_online = True`), the calling code sends a message by invoking a method (`node.boot()`). This guarantees that internal invariants, audit logging, and state validation hooks always run predictably.</p>
'''
    pages.append({
        "id": "6860",
        "title": "The Object-Oriented Paradigm",
        "topic_number": "OOP1.1.1",
        "section_title": "Section 1.1: Foundations of Classes & Instances",
        "unit_title": "Unit 1: OOP Foundations & Anatomy of Classes",
        "content_html": p1_html.strip()
    })

    # Page 2: 6861 - Deep Dive into Class & Instance Creation (__new__ vs __init__)
    p2_html = '''
<h2>The Two-Phase Instantiation Pipeline</h2>
<p>When a beginner writes `obj = MyClass()`, they often assume `__init__` is the constructor. In professional Python development, understanding the exact instantiation lifecycle is crucial. Python creates objects in a strict **Two-Phase Instantiation Pipeline**:
<ol>
  <li><strong>Memory Allocation (`__new__`):</strong> Python first invokes the static class method `MyClass.__new__(cls, *args, **kwargs)`. This method is responsible for allocating raw memory and returning a newly constructed instance object.</li>
  <li><strong>State Initialization (`__init__`):</strong> Immediately after `__new__` returns the allocated object, Python passes that object as `self` into `__init__(self, *args, **kwargs)` to populate initial attributes and state.</li>
</ol></p>

<h2>When and Why to Override `__new__`</h2>
<p>Because `__init__` receives an already allocated object (`self`) and returns `None`, you cannot change the object's fundamental memory type or prevent allocation inside `__init__`. You must override `__new__(cls, ...)` under three advanced scenarios:</p>
<ul>
  <li><strong>Subclassing Immutable Types:</strong> Built-in types like `tuple`, `str`, `int`, and `frozenset` are immutable. Their internal state is frozen in C memory at the exact moment of allocation. If you want to create a custom uppercase string (`class UpperStr(str):`), you must modify the string argument inside `__new__` before the immutable memory is locked.</li>
  <li><strong>Implementing Singleton Caching:</strong> Ensuring a class has exactly one memory instance across the entire application by checking and returning a cached instance inside `__new__`.</li>
  <li><strong>Metaclass Instance Manipulation:</strong> Intercepting class allocation during dynamic framework generation (such as ORM models or custom API serializers).</li>
</ul>

<pre><code class="language-python"># Advanced Demonstration: Custom Immutable Subclass & Singleton via __new__

class ImmutableUpperStr(str):
    """An immutable string subclass that automatically converts inputs to uppercase during allocation."""
    def __new__(cls, content: str):
        # Modify the raw string data before delegating allocation to base str.__new__
        transformed = content.upper().strip()
        return super().__new__(cls, transformed)

class DatabasePoolSingleton:
    """A thread-safe Singleton ensuring only one pool instance exists across memory."""
    _cached_instance = None

    def __new__(cls, connection_uri: str):
        if cls._cached_instance is None:
            print("Allocating new DatabasePoolSingleton instance...")
            cls._cached_instance = super().__new__(cls)
            # Flag to ensure __init__ only runs state setup once
            cls._cached_instance._initialized = False
        return cls._cached_instance

    def __init__(self, connection_uri: str):
        if not self._initialized:
            self.connection_uri = connection_uri
            self.connections = ["conn_1", "conn_2", "conn_3"]
            self._initialized = True
            print(f"Initialized Pool connected to: {self.connection_uri}")

# Testing Immutable UpperStr
header = ImmutableUpperStr("   welcome to advanced python   ")
print(f"Allocated Immutable String: '{header}' (Type: {type(header).__name__})")

# Testing Singleton Allocation
pool_a = DatabasePoolSingleton("postgres://admin:secret@db.prod:5432")
pool_b = DatabasePoolSingleton("postgres://admin:secret@db.prod:5432")
print(f"Are pool_a and pool_b identical memory objects? {pool_a is pool_b}")
</code></pre>

<h2>Lifecycle Best Practices</h2>
<p>When implementing `__new__`, always return the allocated object via `super().__new__(cls)`. If `__new__` returns an instance of a different class, Python will silently skip running `__init__` entirely on that object. Understanding this two-phase hook is the foundation for writing high-performance metaclasses and custom data structures.</p>
'''
    pages.append({
        "id": "6861",
        "title": "Deep Dive into Class & Instance Creation (__new__ vs __init__)",
        "topic_number": "OOP1.1.2",
        "section_title": "Section 1.1: Foundations of Classes & Instances",
        "unit_title": "Unit 1: OOP Foundations & Anatomy of Classes",
        "content_html": p2_html.strip()
    })

    # Page 3: 6862 - Instance, Class, and Static Methods (@classmethod, @staticmethod)
    p3_html = '''
<h2>The Three Method Paradigms</h2>
<p>In Python object-oriented architecture, methods housed inside a class namespace fall into three distinct functional categories based on how they bind to the underlying class hierarchy: **Instance Methods**, **Class Methods (`@classmethod`)**, and **Static Methods (`@staticmethod`)**.</p>

<h2>Instance Methods (`self` Binding)</h2>
<p>Instance methods are the standard default method type in Python. When invoked via `obj.method()`, Python automatically binds the calling instance as the first argument, universally named `self`. Through `self`, instance methods can freely read or mutate individual object state (`self.__dict__`) as well as access shared class attributes (`self.__class__.attr`).</p>

<h2>Class Methods (`@classmethod` and `cls` Binding)</h2>
<p>Decorating a method with `@classmethod` instructs Python's descriptor engine to bind the **class object (`cls`)** as the first argument instead of an instance. Class methods cannot access individual instance attributes because no instance exists when they are called. Instead, `@classmethod` serves two primary enterprise purposes:</p>
<ul>
  <li><strong>Alternative Factory Constructors:</strong> Python classes only support a single `__init__` method. If you need to construct an object from JSON, CSV, or raw binary payloads, you write specialized `@classmethod` factory methods (`from_json()`, `from_config()`) that parse data and instantiate `cls(...)`.</li>
  <li><strong>Mutating Class-Level State:</strong> Updating shared configuration settings across an entire inheritance tree cleanly and reliably.</li>
</ul>

<h2>Static Methods (`@staticmethod`)</h2>
<p>Decorating a method with `@staticmethod` creates a pure utility function residing inside the class namespace. A static method receives **neither `self` nor `cls`** implicit binding. It behaves exactly like a standalone module-level function, but is grouped inside the class because its logic is conceptually tied to the object's domain (`e.g., IMEI validation on a Smartphone class`).</p>

<pre><code class="language-python">import json
from datetime import datetime

class FinancialTransaction:
    # Shared Class Attribute: Base currency code for all transactions
    base_currency = "USD"

    def __init__(self, transaction_id: str, amount: float, timestamp: str):
        # Instance Attributes
        self.transaction_id = transaction_id
        self.amount = amount
        self.timestamp = timestamp

    # 1. Instance Method: Operates directly on individual object state
    def apply_service_fee(self, percentage: float) -> float:
        fee = self.amount * (percentage / 100.0)
        self.amount += fee
        return self.amount

    # 2. Class Method: Alternative factory constructor receiving 'cls'
    @classmethod
    def from_json_payload(cls, raw_json: str) -> "FinancialTransaction":
        """Instantiates and returns a new FinancialTransaction cleanly from JSON."""
        data = json.loads(raw_json)
        # Using 'cls' ensures subclasses (e.g. AuditedTransaction) instantiate properly
        return cls(
            transaction_id=data["tx_id"],
            amount=float(data["total"]),
            timestamp=datetime.utcnow().isoformat()
        )

    # 3. Static Method: Self-contained validation logic requiring neither self nor cls
    @staticmethod
    def is_valid_transaction_id(tx_id: str) -> bool:
        """Verifies if the transaction ID conforms to standard hexadecimal structure."""
        if not tx_id or len(tx_id) != 12:
            return False
        return all(char in "0123456789ABCDEFabcdef" for char in tx_id)

# Testing Static Method Validation
tx_hex = "A1B2C3D4E5F6"
print(f"Is '{tx_hex}' valid? {FinancialTransaction.is_valid_transaction_id(tx_hex)}")

# Testing Class Method Factory Construction
payload = '{"tx_id": "89AB01234567", "total": 1250.75}'
tx_obj = FinancialTransaction.from_json_payload(payload)
tx_obj.apply_service_fee(2.5)
print(f"Transaction [{tx_obj.transaction_id}] Final Amount: ${tx_obj.amount:.2f} {tx_obj.base_currency}")
</code></pre>

<h2>Choosing the Right Method Type</h2>
<p>As a rule of thumb: if your method needs to access or alter `self.attr`, make it an **Instance Method**. If it instantiates objects or modifies shared class attributes (`cls.attr`), make it a **Class Method (`@classmethod`)**. If it requires neither `self` nor `cls` and performs pure computation or validation, encapsulate it cleanly as a **Static Method (`@staticmethod`)**.</p>
'''
    pages.append({
        "id": "6862",
        "title": "Instance, Class, and Static Methods (@classmethod, @staticmethod)",
        "topic_number": "OOP1.2.1",
        "section_title": "Section 1.2: Methods, Attributes & State Architecture",
        "unit_title": "Unit 1: OOP Foundations & Anatomy of Classes",
        "content_html": p3_html.strip()
    })

    # Page 4: 6863 - Attribute Management (__dict__, __slots__)
    p4_html = '''
<h2>How Python Storing Instance Attributes (`__dict__`)</h2>
<p>In standard Python classes, object instances are highly dynamic. You can attach arbitrary attributes to any instance at runtime (`obj.custom_field = 42`). Python achieves this dynamic flexibility by storing every instance's attributes inside an internal hash table dictionary named **`__dict__`**.</p>
<p>When you evaluate `obj.name`, Python performs a multi-step dictionary lookup across the attribute resolution chain:
<ol>
  <li>Check the instance dictionary (`obj.__dict__`).</li>
  <li>If missing, check the class namespace (`type(obj).__dict__`).</li>
  <li>If still missing, traverse the Method Resolution Order (MRO) hierarchy of base classes up to `object`.</li>
</ol></p>

<h2>The Memory Overhead of `__dict__`</h2>
<p>While `__dict__` provides immense flexibility, hash table dictionaries consume substantial memory overhead. A single empty dictionary in Python 64-bit takes roughly 240+ bytes. If your high-throughput financial system instantiates 5,000,000 `Order` objects, storing five million individual `__dict__` structures consumes gigabytes of RAM purely for dictionary overhead!</p>

<h2>Memory Optimization via `__slots__`</h2>
<p>To eliminate dictionary overhead in high-density classes, Python provides **`__slots__`**. By defining `__slots__ = ('attr1', 'attr2')` at class level, you instruct Python's C-engine to skip allocating a per-instance `__dict__` dictionary entirely. Instead, attributes are stored in fixed, compact C array slots accessible via direct memory offsets.</p>
<ul>
  <li><strong>Massive RAM Savings:</strong> Adopting `__slots__` typically reduces per-instance RAM consumption by **60% to 75%** for small data-heavy objects.</li>
  <li><strong>Faster Attribute Access:</strong> Direct slot lookup is measurably faster than hashing string keys inside `__dict__`.</li>
  <li><strong>Strict Attribute Locking:</strong> Instances cannot dynamically acquire new attributes outside the pre-declared `__slots__` tuple, preventing accidental attribute typos (`order.amunt = 10` raises an explicit `AttributeError`).</li>
</ul>

<pre><code class="language-python">import sys

# Standard Class utilizing dynamic __dict__
class StandardPoint:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

# High-Density Class utilizing fixed __slots__ memory allocation
class SlottedPoint:
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

# Instantiating objects
std_obj = StandardPoint(10.5, 20.8, -5.2)
slotted_obj = SlottedPoint(10.5, 20.8, -5.2)

# Checking internal __dict__ presence
print(f"Does StandardPoint possess __dict__? {hasattr(std_obj, '__dict__')} (Dict contents: {std_obj.__dict__})")
print(f"Does SlottedPoint possess __dict__? {hasattr(slotted_obj, '__dict__')}")

# Comparing approximate RAM allocation size (excluding underlying float object weights)
std_size = sys.getsizeof(std_obj) + sys.getsizeof(std_obj.__dict__)
slotted_size = sys.getsizeof(slotted_obj)

print(f"Approximate RAM consumed by StandardPoint instance + dict: {std_size} bytes")
print(f"Approximate RAM consumed by SlottedPoint instance: {slotted_size} bytes")
print(f"Memory reduction ratio achieved via slots: {((std_size - slotted_size) / std_size)*100:.1f}%")
</code></pre>

<h2>When to Avoid `__slots__`</h2>
<p>While `__slots__` is powerful, do not use it blindly on every class. Avoid `__slots__` when objects require dynamic attribute attachment at runtime, when working with complex multiple inheritance (multiple classes defining conflicting `__slots__` can crash MRO layout), or when classes require `__weakref__` support without explicitly including `'__weakref__'` in the slots tuple.</p>
'''
    pages.append({
        "id": "6863",
        "title": "Attribute Management (__dict__, __slots__)",
        "topic_number": "OOP1.2.2",
        "section_title": "Section 1.2: Methods, Attributes & State Architecture",
        "unit_title": "Unit 1: OOP Foundations & Anatomy of Classes",
        "content_html": p4_html.strip()
    })

    # Page 5: 6864 - Encapsulation, Name Mangling (_protected, __private)
    p5_html = '''
<h2>Encapsulation and Python's Open Philosophy</h2>
<p>In languages like C++ or Java, encapsulation is enforced rigidly by the compiler using access modifier keywords (`public`, `protected`, `private`). If a method tries to touch `private int balance;`, compilation aborts. Python operates on a vastly different philosophy famously summarized as: **"We are all consenting adults here."**</p>
<p>Python does not provide hard compiler restrictions against accessing object attributes. Instead, encapsulation in Python relies on clean naming conventions, explicit developer discipline, and internal compiler transformations designed to prevent accidental state corruption rather than malicious hacking.</p>

<h2>Single Leading Underscore (`_protected`)</h2>
<p>Prefixing an instance attribute or method with a **single leading underscore** (e.g., `self._balance` or `self._calculate_tax()`) is Python's universal convention for **Protected** or internal members. This tells fellow developers and IDE linters: *"This attribute is part of internal implementation details. Do not access or mutate it directly from outside the class or its subclasses."*</p>
<p>Note that `_protected` members can still be read directly (`obj._balance`), but doing so violates professional API contracts and risks breaking code if internal architectures evolve.</p>

<h2>Double Leading Underscore (`__private` and Name Mangling)</h2>
<p>When you prefix an attribute or method with **double leading underscores** (and at most one trailing underscore, e.g., `self.__secret_key`), the Python compiler triggers an automatic mechanism called **Name Mangling** during bytecode generation.</p>
<p>Python automatically rewrites `__secret_key` inside the class `SecureAccount` to **`_SecureAccount__secret_key`**. Why?
<ul>
  <li><strong>Preventing Subclass Collisions:</strong> If a parent class and a child subclass both define an internal attribute named `__cache`, name mangling transforms them into `_Parent__cache` and `_Child__cache`. Both attributes coexist safely inside `__dict__` without overwriting each other!</li>
  <li><strong>Accidental External Modification:</strong> Attempting to access `account.__secret_key` from external code raises an `AttributeError` because that exact symbol string does not exist in `__dict__`.</li>
</ul></p>

<pre><code class="language-python">class BankAccount:
    def __init__(self, owner: str, initial_deposit: float, pin_code: int):
        # Public attribute: Safely accessible and modifiable by external callers
        self.owner = owner
        
        # Protected attribute (_): Internal state meant for class and subclass usage
        self._balance = initial_deposit
        
        # Private attribute (__): Triggers automatic Name Mangling during compilation
        self.__pin_code = pin_code

    def verify_pin(self, entered_pin: int) -> bool:
        """Public method interacting with private mangled state safely."""
        return self.__pin_code == entered_pin

    def deposit(self, amount: float) -> str:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self._balance += amount
        return f"Deposited ${amount:.2f}. New Balance: ${self._balance:.2f}"

# Instantiating Account
acct = BankAccount("Dr. Robert Ford", 5000.00, 8492)

# 1. Public access works normally
print(f"Account Owner: {acct.owner}")

# 2. Protected access works but triggers developer caution
print(f"Protected Balance Access: ${acct._balance:.2f}")

# 3. Direct access to private __pin_code raises AttributeError!
try:
    print(acct.__pin_code)
except AttributeError as err:
    print(f"Blocked Private Access Attempt: {err}")

# 4. Inspecting actual mangled names inside object __dict__
print("Actual internal __dict__ keys:", list(acct.__dict__.keys()))
# Accessing via mangled symbol string (_BankAccount__pin_code)
print(f"Mangled Private Pin Access: {acct._BankAccount__pin_code}")
</code></pre>

<h2>Professional Encapsulation Rules</h2>
<p>In production Python codebases, use **single leading underscores (`_attr`)** for almost all internal protected attributes and helper methods. Only reserve **double leading underscores (`__attr`)** when designing base classes intended for widespread subclassing where preventing attribute name collisions across complex inheritance trees is absolutely critical.</p>
'''
    pages.append({
        "id": "6864",
        "title": "Encapsulation, Name Mangling (_protected, __private)",
        "topic_number": "OOP1.3.1",
        "section_title": "Section 1.3: Access Control & Data Encapsulation",
        "unit_title": "Unit 1: OOP Foundations & Anatomy of Classes",
        "content_html": p5_html.strip()
    })

    # Page 6: 6865 - Pythonic Getters & Setters (@property)
    p6_html = '''
<h2>The Problem with Explicit Getters and Setters</h2>
<p>In Java and C++, standard object design requires writing explicit getter and setter methods (`obj.getTemperature()` and `obj.setTemperature(val)`). While this enables validation, it pollutes codebase readability with repetitive boilerplate. Worse, if you start with a simple public attribute (`obj.temp = 25`) and later need to add validation rules, converting `temp` to explicit `get/set` methods forces you to break existing syntax across every single client file!</p>

<h2>The Pythonic Solution: `@property` Descriptors</h2>
<p>Python solves this architectural dilemma using the **`@property`** decorator. A property allows you to expose what looks like a simple public attribute (`obj.temperature`) while executing custom getter, setter, and deleter methods under the hood!</p>
<p>This enables **Uniform Access**: you can start by deploying clean, simple public attributes (`self.temperature = temp`). If business rules later require range verification or logging upon assignment, you simply wrap the attribute in `@property` and `@temperature.setter` without altering a single line of client calling syntax!</p>

<h2>Anatomy of `@property` and `@attr.setter`</h2>
<ul>
  <li><strong>`@property` (The Getter):</strong> Decorating a method with `@property` transforms it into a descriptor getter. When `obj.attr` is accessed, the method executes and returns the computed value.</li>
  <li><strong>`@attr.setter` (The Setter):</strong> Decorating a second method with `@attr.setter` intercepts assignments (`obj.attr = value`). This is where you enforce type checking, boundary limits, and audit notifications.</li>
  <li><strong>Read-Only Properties:</strong> If you define `@property` without any corresponding `@attr.setter`, the attribute becomes strictly read-only after object initialization.</li>
</ul>

<pre><code class="language-python">class ThermodynamicSensor:
    def __init__(self, sensor_id: str, celsius_value: float):
        self.sensor_id = sensor_id
        # We assign directly to the property setter to enforce initial boundary checks!
        self.temperature_celsius = celsius_value

    # 1. The Getter (@property): Intercepts reading sensor.temperature_celsius
    @property
    def temperature_celsius(self) -> float:
        """Returns the current internal Celsius reading cleanly."""
        return self._temp_celsius

    # 2. The Setter (@attr.setter): Intercepts assignment sensor.temperature_celsius = val
    @temperature_celsius.setter
    def temperature_celsius(self, new_val: float) -> None:
        if not isinstance(new_val, (int, float)):
            raise TypeError("Temperature must be a valid numerical value.")
        if new_val < -273.15:
            raise ValueError(f"Invalid temperature [{new_val}°C]: Cannot fall below Absolute Zero (-273.15°C).")
        self._temp_celsius = float(new_val)

    # 3. Computed Read-Only Property: Dynamically converts Celsius to Fahrenheit
    @property
    def temperature_fahrenheit(self) -> float:
        """Computed property returning Fahrenheit equivalent. No setter defined = Read-Only."""
        return (self._temp_celsius * 9.0 / 5.0) + 32.0

# Testing Property Validation and Computed Access
sensor = ThermodynamicSensor("LAB-ALPHA-01", 25.0)

# Clean dot-notation read access
print(f"Sensor [{sensor.sensor_id}] Celsius: {sensor.temperature_celsius}°C")
print(f"Sensor [{sensor.sensor_id}] Fahrenheit: {sensor.temperature_fahrenheit}°F")

# Valid update intercepted by setter cleanly
sensor.temperature_celsius = 100.0
print(f"Updated Boiling Reading: {sensor.temperature_fahrenheit}°F")

# Invalid assignment triggers boundary exception safely
try:
    sensor.temperature_celsius = -300.0
except ValueError as err:
    print(f"Validation Intercepted: {err}")
</code></pre>

<h2>Properties vs. Methods</h2>
<p>Use `@property` when accessing the attribute is fast, deterministic, and conceptually represents object state (`obj.full_name`, `obj.is_active`, `obj.area`). If computing the value requires slow network requests, heavy database queries, or alters external system state, expose it explicitly as a standard method (`obj.fetch_latest_report()`) to make computational weight obvious to clients.</p>
'''
    pages.append({
        "id": "6865",
        "title": "Pythonic Getters & Setters (@property)",
        "topic_number": "OOP2.1.1",
        "section_title": "Section 2.1: Properties & The Descriptor Protocol",
        "unit_title": "Unit 2: Properties, Descriptors & Data Models",
        "content_html": p6_html.strip()
    })

    # Page 7: 6866 - The Descriptor Protocol (__get__, __set__, __delete__)
    p7_html = '''
<h2>What lies Beneath `@property`: The Descriptor Protocol</h2>
<p>While `@property` is elegant, it has a limitation: you must write separate getter and setter methods for every single property on a class. What if you are building an ORM (like SQLAlchemy or Django Models) where fifty distinct attributes all require standardized type validation, range restrictions, and SQL field mapping? Writing fifty properties would be a maintenance nightmare!</p>
<p>To encapsulate reusable attribute behavior across multiple classes, you dive down into Python's low-level engine: **The Descriptor Protocol**.</p>

<h2>The Three Descriptor Hooks</h2>
<p>A **Descriptor** is any class that implements one or more of the following dunder methods to govern attribute access:
<ul>
  <li><strong>`__get__(self, instance, owner_class)`:</strong> Intercepts reading `instance.attr` or `owner_class.attr`.</li>
  <li><strong>`__set__(self, instance, value)`:</strong> Intercepts assigning `instance.attr = value`.</li>
  <li><strong>`__delete__(self, instance)`:</strong> Intercepts deleting `del instance.attr`.</li>
</ul></p>

<h2>Data vs. Non-Data Descriptors</h2>
<p>Understanding descriptor precedence against the instance `__dict__` is vital for advanced metaprogramming:
<ol>
  <li><strong>Data Descriptors:</strong> Classes defining both `__get__` and `__set__` (or `__delete__`). When you access `obj.attr`, if `attr` is a Data Descriptor on the class, **the descriptor takes absolute priority over any value stored inside `obj.__dict__`**. This prevents instances from bypassing validation by assigning directly to `__dict__`.</li>
  <li><strong>Non-Data Descriptors:</strong> Classes defining only `__get__`. Standard methods and `@staticmethod` are non-data descriptors. If an instance has an attribute in its `__dict__` with the exact same name as a non-data descriptor on the class, the instance `__dict__` value wins!</li>
</ol></p>

<pre><code class="language-python"># Building a Reusable Range-Validated Integer Data Descriptor

class BoundedInteger:
    """A Data Descriptor enforcing type validation and numerical boundary checks automatically."""
    def __init__(self, min_val: int, max_val: int):
        self.min_val = min_val
        self.max_val = max_val

    def __set_name__(self, owner_class, attribute_name: str):
        # Modern Python 3.6+ hook: automatically captures the name of the assigned class attribute
        self.public_name = attribute_name
        self.private_name = f"_{attribute_name}"

    def __get__(self, instance, owner_class):
        if instance is None:
            # When accessed directly on the class (Character.level), return the descriptor itself
            return self
        return getattr(instance, self.private_name, None)

    def __set__(self, instance, value: int):
        if not isinstance(value, int):
            raise TypeError(f"Attribute '{self.public_name}' requires an integer value.")
        if not (self.min_val <= value <= self.max_val):
            raise ValueError(f"Attribute '{self.public_name}' value [{value}] outside allowed bounds ({self.min_val}-{self.max_val}).")
        setattr(instance, self.private_name, value)

# Using our reusable descriptor cleanly across multiple attributes on a Domain Model
class GameCharacter:
    # Descriptors instantiated once at class definition level
    level = BoundedInteger(min_val=1, max_val=100)
    health = BoundedInteger(min_val=0, max_val=9999)
    mana = BoundedInteger(min_val=0, max_val=500)

    def __init__(self, name: str, level: int, health: int, mana: int):
        self.name = name
        # Assignments trigger BoundedInteger.__set__ validation automatically!
        self.level = level
        self.health = health
        self.mana = mana

# Instantiating character cleanly
hero = GameCharacter("Paladin-Geralt", level=50, health=2500, mana=300)
print(f"Hero [{hero.name}] Stats - Level: {hero.level}, Health: {hero.health}, Mana: {hero.mana}")

# Testing boundary enforcement intercepted by BoundedInteger descriptor
try:
    hero.level = 150
except ValueError as err:
    print(f"Descriptor Intercepted Level Error: {err}")
</code></pre>

<h2>Why Descriptors Matter</h2>
<p>Every time you call a method (`obj.method()`), use a `@classmethod`, define a `@property`, or define database columns in an ORM (`name = Column(String(50))`), you are interacting directly with the Descriptor Protocol. Mastering `__get__` and `__set__` allows you to write enterprise-grade, highly reusable validation architecture that keeps domain models pristine.</p>
'''
    pages.append({
        "id": "6866",
        "title": "The Descriptor Protocol (__get__, __set__, __delete__)",
        "topic_number": "OOP2.1.2",
        "section_title": "Section 2.1: Properties & The Descriptor Protocol",
        "unit_title": "Unit 2: Properties, Descriptors & Data Models",
        "content_html": p7_html.strip()
    })

    # Page 8: 6867 - Core Magic/Dunder Methods (__repr__, __str__, __format__)
    p8_html = '''
<h2>Python's Data Model: Dunder (Magic) Methods</h2>
<p>Python's elegance comes from its **Data Model**: a standardized set of double-underscore methods—affectionately called **Dunder Methods** or **Magic Methods** (`__dunder__`). Instead of forcing developers to call arbitrary syntax (`obj.toString()` vs `obj.as_string()`), Python intercepts top-level built-in functions (`str()`, `len()`, `print()`) and delegates them directly to your class's corresponding dunder methods!</p>

<h2>String Representation: `__repr__` vs. `__str__`</h2>
<p>When displaying objects, developers frequently confuse `__repr__` and `__str__`. Python defines two strict, complementary philosophies for object presentation:
<ul>
  <li><strong>`__repr__(self)` (The Developer's Contract):</strong> Unambiguous representation intended for debugging, logging, and terminal REPL inspection. As a golden rule, `__repr__` should ideally return a valid Python expression string that, when passed to `eval()`, constructs an identical object instance (`f"Point(x={self.x}, y={self.y})"`).</li>
  <li><strong>`__str__(self)` (The User's Display):</strong> Human-readable string representation triggered whenever an object is passed to `print(obj)`, `str(obj)`, or interpolated in standard f-strings (`f"{obj}"`). It prioritizes clean aesthetics over technical construction precision (`f"Point at ({self.x}, {self.y})"`).</li>
</ul></p>
<p>If a class defines only `__repr__(self)` without `__str__(self)`, Python intelligently falls back to calling `__repr__` during `print()` operations. Therefore, **always implement `__repr__` first** on every professional class!</p>

<h2>Custom Formatting: `__format__`</h2>
<p>When you use format specifiers inside f-strings or `format()` calls (`f"{obj:spec}"`), Python invokes `obj.__format__(format_spec)`. Implementing `__format__` allows your objects to support custom presentation specifications (such as displaying timestamps in ISO format vs short date, or formatting vectors in polar vs Cartesian coordinates).</p>

<pre><code class="language-python">import math

class SpatialVector2D:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    # 1. Developer Debugging Contract (__repr__)
    def __repr__(self) -> str:
        """Must return exact construction syntax for REPL and logs."""
        return f"SpatialVector2D(x={self.x!r}, y={self.y!r})"

    # 2. Human-Readable Display Contract (__str__)
    def __str__(self) -> str:
        """Clean string presentation when calling print()."""
        return f"Vector⟨{self.x:.2f}, {self.y:.2f}⟩"

    # 3. Custom Format Specification Hook (__format__)
    def __format__(self, format_spec: str) -> str:
        """Supports custom formatting codes: 'p' for Polar coordinates, 'c' for Cartesian."""
        if format_spec.endswith('p'):
            # Calculate polar magnitude (r) and angle theta in degrees
            magnitude = math.hypot(self.x, self.y)
            angle_deg = math.degrees(math.atan2(self.y, self.x))
            return f"Polar(r={magnitude:.2f}, θ={angle_deg:.1f}°)"
        elif format_spec.endswith('c') or not format_spec:
            return str(self)
        else:
            raise ValueError(f"Invalid format specifier '{format_spec}' for SpatialVector2D.")

# Instantiating vector
vec = SpatialVector2D(3.0, 4.0)

# Testing __repr__ (invoked explicitly or via REPL)
print("Explicit __repr__ inspection:", repr(vec))

# Testing __str__ (invoked automatically via print or f-string interpolation)
print("Standard print() output:", vec)

# Testing custom __format__ specifiers via f-strings
print(f"Formatted as Cartesian: {vec:c}")
print(f"Formatted as Polar Coordinates: {vec:p}")
</code></pre>

<h2>Summary of String Dunders</h2>
<p>Implement `__repr__` on every class to make debugging transparent. Add `__str__` when your domain objects will be displayed directly to end-users on dashboards or terminal interfaces. Use `__format__` when building domain-specific data types requiring versatile string formatting options.</p>
'''
    pages.append({
        "id": "6867",
        "title": "Core Magic/Dunder Methods (__repr__, __str__, __format__)",
        "topic_number": "OOP2.2.1",
        "section_title": "Section 2.2: Dunder Methods & Operator Overloading",
        "unit_title": "Unit 2: Properties, Descriptors & Data Models",
        "content_html": p8_html.strip()
    })

    # Page 9: 6868 - Operator Overloading & Math Dunders (__add__, __eq__, __lt__)
    p9_html = '''
<h2>Making Objects Behave Like Native Data Types</h2>
<p>One of Python's most powerful capabilities is **Operator Overloading**. By defining specific mathematical and comparison dunder methods, your custom domain objects can respond naturally to standard arithmetic symbols (`+`, `-`, `*`), logical comparisons (`==`, `<`, `>=`), and compound assignments (`+=`).</p>

<h2>Arithmetic and Reverse Dunders (`__add__`, `__radd__`)</h2>
<p>When Python evaluates `a + b`, it first checks if `a` implements `a.__add__(b)`. If `a` returns a valid result, computation succeeds. But what happens when you evaluate `2 + vec` where `2` is an integer?
<ul>
  <li>Python first calls `int.__add__(2, vec)`. Because `int` knows nothing about your custom `Vector` class, it returns the special singleton **`NotImplemented`**.</li>
  <li>Seeing `NotImplemented`, Python automatically reverses the operands and calls the right operand's **Reverse Dunder Method**: `vec.__radd__(2)`. If `__radd__` is defined, the addition succeeds gracefully!</li>
</ul></p>

<h2>Rich Comparison Ordering (`__eq__`, `__lt__`, `@total_ordering`)</h2>
<p>Python breaks object comparisons into six distinct Rich Comparison dunders: `__eq__` (`==`), `__ne__` (`!=`), `__lt__` (`<`), `__le__` (`<=`), `__gt__` (`>`), and `__ge__` (`>=`).</p>
<p>Writing all six methods manually is repetitive. Instead, Python provides the **`@functools.total_ordering`** class decorator. If you explicitly implement `__eq__(self, other)` and just **one** sorting method (`__lt__(self, other)`), `@total_ordering` automatically synthesizes all four remaining comparison operators (`<=`, `>`, `>=`) for your class at compile time!</p>

<pre><code class="language-python">from functools import total_ordering
import math

@total_ordering
class Money:
    """An ordered currency object supporting operator overloading and total comparison ordering."""
    def __init__(self, amount: float, currency: str = "USD"):
        self.amount = round(float(amount), 2)
        self.currency = currency.upper()

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"

    def __str__(self) -> str:
        return f"${self.amount:.2f} {self.currency}"

    # 1. Rich Equality Comparison (__eq__)
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return (self.amount == other.amount) and (self.currency == other.currency)

    # 2. Rich Less-Than Ordering (__lt__), used by @total_ordering to build <=, >, >=
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money) or self.currency != other.currency:
            return NotImplemented
        return self.amount < other.amount

    # 3. Arithmetic Addition (__add__)
    def __add__(self, other: object) -> "Money":
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot add mismatched currencies: {self.currency} and {other.currency}")
            return Money(self.amount + other.amount, self.currency)
        elif isinstance(other, (int, float)):
            return Money(self.amount + other, self.currency)
        return NotImplemented

    # 4. Reverse Addition (__radd__) to support: 100.0 + Money(50.0)
    def __radd__(self, other: object) -> "Money":
        return self.__add__(other)

# Instantiating Money objects
wallet_a = Money(150.50, "USD")
wallet_b = Money(49.50, "USD")
wallet_c = Money(200.00, "USD")

# Testing Arithmetic Overloading (+ and reverse +)
total_wallet = wallet_a + wallet_b
bonus_wallet = 25.0 + wallet_a
print(f"wallet_a + wallet_b = {total_wallet}")
print(f"25.0 + wallet_a (Reverse add) = {bonus_wallet}")

# Testing Rich Comparisons synthesized via @total_ordering
print(f"Is wallet_a == wallet_b? {wallet_a == wallet_b}")
print(f"Is wallet_a < wallet_c? {wallet_a < wallet_c}")
print(f"Is wallet_c >= total_wallet? {wallet_c >= total_wallet}")
</code></pre>

<h2>The Golden Rule of Dunder Returns</h2>
<p>Never raise a `TypeError` inside mathematical or comparison dunders when encountering an unfamiliar operand type. **Always return `NotImplemented`**. This preserves cooperative operand evaluation, giving the other object a fair opportunity to handle the operation via its reverse dunders before Python raises a final `TypeError`.</p>
'''
    pages.append({
        "id": "6868",
        "title": "Operator Overloading & Math Dunders (__add__, __eq__, __lt__)",
        "topic_number": "OOP2.2.2",
        "section_title": "Section 2.2: Dunder Methods & Operator Overloading",
        "unit_title": "Unit 2: Properties, Descriptors & Data Models",
        "content_html": p9_html.strip()
    })

    # Page 10: 6869 - Container & Iterable Dunders (__len__, __getitem__, __iter__)
    p10_html = '''
<h2>Custom Container Protocols</h2>
<p>Python collections (`list`, `dict`, `tuple`, `set`) are celebrated for their expressive, intuitive syntax (`len(items)`, `items[index]`, `if x in items:`). By implementing **Container and Iterable Dunder Methods**, your custom domain objects can integrate seamlessly into these exact built-in collection workflows.</p>

<h2>Sequence and Mapping Hooks (`__len__`, `__getitem__`, `__setitem__`)</h2>
<ul>
  <li><strong>`__len__(self)`:</strong> Intercepts `len(obj)` and truthiness checks (`if not obj:`). Must return a non-negative integer representing total item count.</li>
  <li><strong>`__getitem__(self, key)`:</strong> Intercepts square bracket indexing (`obj[index]` or `obj["key"]`) and slicing (`obj[1:4]`). If integer indices exceed container limits, it must raise an `IndexError` (which allows standard `for` loops to iterate over objects lacking `__iter__`!).</li>
  <li><strong>`__contains__(self, item)`:</strong> Intercepts membership checks via the `in` operator (`if item in obj:`).</li>
</ul>

<h2>The Iterator Protocol (`__iter__` vs `__next__`)</h2>
<p>To make a class explicitly iterable across `for` loops, comprehensions, and unpacking operations, you implement Python's two-part **Iterator Protocol**:
<ol>
  <li><strong>Iterable (`__iter__`):</strong> Intercepted when a loop begins (`for item in collection:`). Must return an **Iterator** object. Idiomatically, this is implemented as a generator method yielding consecutive elements via `yield`.</li>
  <li><strong>Iterator (`__next__`):</strong> Returns the next element in the sequence on each iteration. When items are exhausted, it must raise the **`StopIteration`** exception to signal loop completion safely.</li>
</ol></p>

<pre><code class="language-python"># Building a Custom High-Performance Playlist Container

class MusicPlaylist:
    """A custom container supporting indexing, slicing, membership testing, and iteration."""
    def __init__(self, playlist_name: str, tracks: list = None):
        self.playlist_name = playlist_name
        self._tracks = list(tracks) if tracks else []

    def add_track(self, title: str) -> None:
        self._tracks.append(title)

    # 1. Container Size (__len__)
    def __len__(self) -> int:
        return len(self._tracks)

    # 2. Indexing & Slicing Interception (__getitem__)
    def __getitem__(self, index):
        # Support both single integer indices and slice objects (`playlist[1:3]`)
        if isinstance(index, slice):
            return MusicPlaylist(f"{self.playlist_name} (Subset)", self._tracks[index])
        return self._tracks[index]

    # 3. Membership Testing (__contains__) for 'in' operator
    def __contains__(self, track_title: str) -> bool:
        return track_title in self._tracks

    # 4. Iterable Protocol (__iter__) implemented cleanly as a generator
    def __iter__(self):
        for track in self._tracks:
            yield track

# Instantiating and populating Playlist
rock_playlist = MusicPlaylist("Classic Rock Gold", [
    "Bohemian Rhapsody - Queen",
    "Stairway to Heaven - Led Zeppelin",
    "Hotel California - Eagles",
    "Comfortably Numb - Pink Floyd"
])

# Testing __len__
print(f"Playlist '{rock_playlist.playlist_name}' Track Count: {len(rock_playlist)}")

# Testing __getitem__ Indexing & Slicing
print(f"First Track (Index 0): {rock_playlist[0]}")
subset = rock_playlist[1:3]
print(f"Sliced Subset Tracks ({len(subset)} items): {[t for t in subset]}")

# Testing __contains__ Membership
print(f"Is 'Hotel California - Eagles' in playlist? {'Hotel California - Eagles' in rock_playlist}")

# Testing __iter__ via clean for loop iteration
print("\\nIterating through Playlist Tracks:")
for idx, song in enumerate(rock_playlist, start=1):
    print(f"  {idx}. {song}")
</code></pre>

<h2>Why Container Dunders Matter</h2>
<p>By implementing container protocols, your objects work natively with built-in functions like `sorted()`, `reversed()`, `zip()`, `max()`, and list comprehensions without requiring specialized conversion methods or leaking internal array representations.</p>
'''
    pages.append({
        "id": "6869",
        "title": "Container & Iterable Dunders (__len__, __getitem__, __iter__)",
        "topic_number": "OOP2.3.1",
        "section_title": "Section 2.3: Container & Iterable Data Models",
        "unit_title": "Unit 2: Properties, Descriptors & Data Models",
        "content_html": p10_html.strip()
    })

    # Page 11: 6870 - Single & Multi-Level Inheritance (super())
    p11_html = '''
<h2>The Mechanics of Class Inheritance</h2>
<p>**Inheritance** is the structural OOP mechanism allowing a derived **Subclass (Child)** to acquire, extend, or override the data attributes and methods of an existing **Superclass (Parent)**. Inheritance organizes code into conceptual hierarchies where subclasses represent specialized subtypes of their superclass (`class ElectricCar(Car):`).</p>

<h2>Method Overriding and Extension</h2>
<p>When a subclass defines a method with the exact same name as a superclass method, the subclass method **overrides** the parent's implementation during attribute resolution. However, overriding often requires *extending* rather than completely destroying parental logic. This is where **`super()`** is essential.</p>

<h2>Why `super().__init__()` is Mandatory</h2>
<p>A common beginner mistake is overriding `__init__` in a child class without calling `super().__init__(...)`. When a child class defines its own `__init__`, Python **does not automatically execute the parent's `__init__`**. If you omit calling `super().__init__(...)`, any critical instance attributes established in the parent class are never initialized, leading to fatal `AttributeError` crashes when parent methods are called!</p>
<p>Furthermore, never hardcode parent class names inside `__init__` (`ParentClass.__init__(self, ...)`). Always use **`super().__init__(...)`** because `super()` calculates the dynamic Method Resolution Order at runtime, ensuring cooperative inheritance across complex class hierarchies.</p>

<h2>The Liskov Substitution Principle (LSP)</h2>
<p>When designing inheritance trees, you must respect the **Liskov Substitution Principle (LSP)**: *Any function expecting an instance of a Superclass must work correctly when passed an instance of any Subclass without knowing the difference.*
If `ElectricCar` inherits from `Car`, overriding `car.refuel()` to raise a crash exception violates LSP! Subclasses must fulfill the behavioral contracts established by their base classes.</p>

<pre><code class="language-python"># Single and Multi-Level Inheritance utilizing super()

class NetworkDevice:
    """Base Superclass representing any network-connected hardware."""
    def __init__(self, hostname: str, mac_address: str):
        self.hostname = hostname
        self.mac_address = mac_address
        self.is_connected = False

    def connect(self) -> str:
        self.is_connected = True
        return f"Device [{self.hostname}] connected to backbone network."

    def get_device_info(self) -> str:
        return f"Device: {self.hostname} | MAC: {self.mac_address} | Connected: {self.is_connected}"


# 1. Single-Level Child Subclass extending NetworkDevice
class Router(NetworkDevice):
    def __init__(self, hostname: str, mac_address: str, routing_protocol: str):
        # Mandatory: Delegate core attribute setup up to NetworkDevice.__init__
        super().__init__(hostname, mac_address)
        self.routing_protocol = routing_protocol
        self.routing_table = {}

    # Method Overriding: Extending parental get_device_info cleanly
    def get_device_info(self) -> str:
        base_info = super().get_device_info()
        return f"{base_info} | Protocol: {self.routing_protocol} | Routes: {len(self.routing_table)}"

    def add_route(self, destination_ip: str, gateway: str) -> None:
        self.routing_table[destination_ip] = gateway


# 2. Multi-Level Subclass inheriting from Router (NetworkDevice -> Router -> FirewallRouter)
class FirewallRouter(Router):
    def __init__(self, hostname: str, mac_address: str, routing_protocol: str, security_policy: str):
        # Delegate routing and base setup to Router.__init__ via super()
        super().__init__(hostname, mac_address, routing_protocol)
        self.security_policy = security_policy
        self.blocked_ips = set()

    def block_ip(self, ip_address: str) -> str:
        self.blocked_ips.add(ip_address)
        return f"Firewall [{self.hostname}]: IP {ip_address} added to blacklist."

# Instantiating Multi-Level Hierarchy
fw_router = FirewallRouter("EDGE-FW-01", "00:1A:2B:3C:4D:5E", "OSPFv3", "STRICT_ZeroTrust")
fw_router.connect()
fw_router.add_route("0.0.0.0/0", "192.168.1.1")
fw_router.block_ip("45.33.22.11")

print(fw_router.get_device_info())
print(f"Blocked Security Threats Count: {len(fw_router.blocked_ips)}")
</code></pre>

<h2>Inheritance Architecture Rule</h2>
<p>Use inheritance exclusively when a strict **"Is-A"** relationship exists between classes (`FirewallRouter is a Router`). If the relationship is merely sharing code or holding references (`Router uses a Logger`), use composition instead to prevent brittle, overly deep inheritance trees.</p>
'''
    pages.append({
        "id": "6870",
        "title": "Single & Multi-Level Inheritance (super())",
        "topic_number": "OOP3.1.1",
        "section_title": "Section 3.1: Inheritance Hierarchies & MRO Mechanics",
        "unit_title": "Unit 3: Inheritance, Polymorphism & Composition",
        "content_html": p11_html.strip()
    })

    # Page 12: 6871 - Multiple Inheritance & The C3 Linearization Algorithm (MRO)
    p12_html = '''
<h2>Multiple Inheritance and The Diamond Problem</h2>
<p>Python allows **Multiple Inheritance**: a derived subclass can inherit directly from two or more independent base classes (`class AmphibiousVehicle(Car, Boat):`). While multiple inheritance provides immense design flexibility, it introduces the infamous **Diamond Problem**.</p>
<p>Suppose class `D` inherits from both `B` and `C`, and both `B` and `C` inherit from class `A`. If `A`, `B`, and `C` all define a method named `process()`, when an instance of `D` calls `d.process()`, which parent method does Python execute first? And if `super()` is used across classes, how does Python prevent executing class `A`'s method twice?</p>

<h2>The C3 Linearization Algorithm and `__mro__`</h2>
<p>Python resolves the Diamond Problem deterministically using the **C3 Linearization Algorithm**. When a class is compiled, Python computes a monotonic, unambiguous lookup order across every class in the inheritance tree called the **Method Resolution Order (`__mro__`)**.</p>
<p>C3 Linearization guarantees three non-negotiable architectural invariants:
<ol>
  <li><strong>Subclass Precedence:</strong> A child subclass is always inspected *before* any of its parent superclasses (`D` comes before `B` or `C`).</li>
  <li><strong>Declaration Order:</strong> If class `D` inherits from `(B, C)`, parent `B` is always inspected *before* parent `C` based on the left-to-right syntax order in `D`'s class declaration.</li>
  <li><strong>Monotonicity:</strong> If class `X` precedes class `Y` in the MRO of one parent, `X` will never appear *after* `Y` in the MRO of any child subclass. (If C3 detects an impossible contradictory hierarchy, Python immediately raises a compilation `TypeError`).</li>
</ol></p>

<h2>Cooperative Multiple Inheritance and Mixins</h2>
<p>To ensure `super()` traverses the exact C3 MRO chain smoothly without skipping classes, every `__init__` in a multiple inheritance hierarchy must be **Cooperative**: every class must accept `**kwargs` and invoke `super().__init__(**kwargs)` even if it doesn't inherit from a custom base class (`object.__init__` terminates the chain cleanly).</p>
<p>A primary real-world application of multiple inheritance is **Mixin Classes**. A Mixin is a modular, self-contained parent class (`JsonSerializerMixin`, `AuditLogMixin`) designed solely to inject discrete utility methods into subclasses across unrelated domains without being instantiated on its own.</p>

<pre><code class="language-python"># Demonstrating Multiple Inheritance, Mixin Architecture & C3 MRO

class BaseDocument:
    """Core base class for all domain documents."""
    def __init__(self, doc_id: str, title: str, **kwargs):
        super().__init__(**kwargs)  # Cooperative MRO forwarding
        self.doc_id = doc_id
        self.title = title

    def render(self) -> str:
        return f"Doc [{self.doc_id}]: {self.title}"


# 1. Utility Mixin Class: Injects JSON serialization capability
class JsonSerializerMixin:
    def to_json(self) -> str:
        """Serializes object __dict__ directly into formatted JSON string."""
        import json
        return json.dumps(self.__dict__, indent=2)


# 2. Utility Mixin Class: Injects audit tracking capability
class AuditTrailMixin:
    def __init__(self, created_by: str = "System", **kwargs):
        super().__init__(**kwargs)  # Cooperative forwarding up the MRO chain
        self.created_by = created_by
        self.is_audited = True


# 3. Multiple Inheritance Subclass assembling Base + Two Mixins cleanly
class ConfidentialInvoice(BaseDocument, JsonSerializerMixin, AuditTrailMixin):
    def __init__(self, doc_id: str, title: str, amount: float, created_by: str):
        # Keyword arguments forwarded cooperatively across MRO chain
        super().__init__(doc_id=doc_id, title=title, created_by=created_by)
        self.amount = amount

# Instantiating Multi-Inherited Object
invoice = ConfidentialInvoice("INV-2026-991", "Q3 Quantum Server Order", 45000.00, "Colin")

print("Rendered Invoice Output:", invoice.render())
print(f"Created By Audit Check: {invoice.created_by} (Audited: {invoice.is_audited})")
print("\\nSerialized JSON Output via Mixin:")
print(invoice.to_json())

# Inspecting the exact C3 Method Resolution Order (__mro__)
print("\\nExact C3 Method Resolution Order (__mro__):")
for idx, cls in enumerate(ConfidentialInvoice.__mro__, start=1):
    print(f"  {idx}. {cls.__name__}")
</code></pre>

<h2>Inspecting `__mro__`</h2>
<p>Whenever you design complex multi-inherited architectures or debug unexpected method overrides, inspect the class's `__mro__` tuple directly (`ConfidentialInvoice.__mro__`). Understanding the exact right-to-left, depth-first linearization sequence gives you complete control over how Python resolves method calls across complex class networks.</p>
'''
    pages.append({
        "id": "6871",
        "title": "Multiple Inheritance & The C3 Linearization Algorithm (MRO)",
        "topic_number": "OOP3.1.2",
        "section_title": "Section 3.1: Inheritance Hierarchies & MRO Mechanics",
        "unit_title": "Unit 3: Inheritance, Polymorphism & Composition",
        "content_html": p12_html.strip()
    })

    # Page 13: 6872 - Abstract Base Classes & Interfaces (abc.ABC, @abstractmethod)
    p13_html = '''
<h2>The Need for Formal Interfaces</h2>
<p>In collaborative software teams, when you design a plugin architecture or database connector (`PaymentGateway`, `StorageDriver`), you need to guarantee that every concrete subclass implemented by teammates possesses specific methods (`charge()`, `refund()`, `connect()`). If a developer forgets to implement `charge()`, standard Python raises no error until the exact moment `gateway.charge()` is invoked in production!</p>
<p>To enforce structural contracts at **instantiation time** before code runs, you use **Abstract Base Classes (ABCs)** from Python's built-in `abc` module.</p>

<h2>Anatomy of `abc.ABC` and `@abstractmethod`</h2>
<p>An Abstract Base Class inherits from `abc.ABC` and marks essential contract methods using the **`@abstractmethod`** decorator.
<ul>
  <li><strong>Instantiation Enforcement:</strong> If a class inherits from `ABC` and possesses even one unimplemented `@abstractmethod`, **Python strictly blocks instantiating that class**, raising a `TypeError` immediately when `MyClass()` is called.</li>
  <li><strong>Forcing Subclass Implementation:</strong> Any concrete subclass *must* explicitly implement all abstract methods and properties defined on its parent ABC before Python permits instantiating the subclass.</li>
  <li><strong>Abstract Properties:</strong> You can combine `@property` with `@abstractmethod` (`@property` first, `@abstractmethod` second) to force subclasses to implement specific attributes or getters!</li>
</ul></p>

<h2>Virtual Subclass Registration (`ABCMeta.register`)</h2>
<p>Occasionally, you want a third-party class (`ThirdPartyRedisDriver`) to be recognized as implementing your ABC (`StorageInterface`) so `isinstance(obj, StorageInterface)` returns `True`, even though you cannot modify the third-party source code to make it explicitly inherit from your ABC.</p>
<p>Python allows **Virtual Subclass Registration** using `StorageInterface.register(ThirdPartyRedisDriver)`. This registers the external class inside the ABC's virtual registry, enabling `isinstance()` and `issubclass()` checks without structural inheritance!</p>

<pre><code class="language-python">from abc import ABC, abstractmethod
import math

# 1. Defining Formal Abstract Base Class Interface
class GeometricShape(ABC):
    """Formal interface contract for all 2D geometric shapes."""
    
    def __init__(self, shape_name: str):
        self.shape_name = shape_name

    @property
    @abstractmethod
    def area(self) -> float:
        """Subclasses MUST implement computed area property."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """Subclasses MUST implement perimeter calculation method."""
        pass

    def describe(self) -> str:
        """Concrete method: Inherited cleanly by all subclasses without requiring override."""
        return f"Shape [{self.shape_name}] | Area: {self.area:.2f} | Perimeter: {self.perimeter:.2f}"


# 2. Concrete Subclass implementing all abstract contracts perfectly
class Circle(GeometricShape):
    def __init__(self, radius: float):
        super().__init__("Circle")
        self.radius = float(radius)

    @property
    def area(self) -> float:
        return math.pi * (self.radius ** 2)

    def perimeter(self) -> float:
        return 2.0 * math.pi * self.radius


# 3. Incomplete Subclass deliberately missing perimeter() implementation
class IncompleteTriangle(GeometricShape):
    def __init__(self, base: float, height: float):
        super().__init__("Triangle")
        self.base = base
        self.height = height

    @property
    def area(self) -> float:
        return 0.5 * self.base * self.height
    # Missing perimeter()!

# Testing Concrete Circle Instantiation
my_circle = Circle(radius=5.0)
print(my_circle.describe())

# Testing Instantiation Enforcement on Incomplete Subclass
try:
    bad_shape = IncompleteTriangle(4.0, 3.0)
except TypeError as err:
    print(f"\\nABC Instantiation Intercepted Safely: {err}")
</code></pre>

<h2>Why Use Abstract Base Classes</h2>
<p>Use ABCs when building SDKs, plugin architectures, or complex domain layers where multiple programmers must implement interchangeable concrete classes adhering strictly to uniform method contracts. ABCs catch missing implementations instantly upon instantiation rather than failing silently inside deep production workflows.</p>
'''
    pages.append({
        "id": "6872",
        "title": "Abstract Base Classes & Interfaces (abc.ABC, @abstractmethod)",
        "topic_number": "OOP3.2.1",
        "section_title": "Section 3.2: Interfaces, Typing Protocols & Contracts",
        "unit_title": "Unit 3: Inheritance, Polymorphism & Composition",
        "content_html": p13_html.strip()
    })

    # Page 14: 6873 - Structural vs Nominal Typing (typing.Protocol)
    p14_html = '''
<h2>Nominal vs. Structural Typing (`Duck Typing`)</h2>
<p>Python's traditional polymorphism relies on **Duck Typing** (*"If it walks like a duck and quacks like a duck, it's a duck"*). If a function `render_report(obj)` calls `obj.to_pdf()`, Duck Typing doesn't care what class `obj` inherits from; as long as `obj` possesses a `to_pdf()` method at runtime, the call succeeds!</p>
<p>While Duck Typing is highly flexible, static type checkers (`mypy`, `pyright`) struggle with it. If you annotate `def render_report(obj: PdfDocument):`, static checkers enforce **Nominal Typing**: they reject any object that does not explicitly inherit from `PdfDocument`, even if that object implements `to_pdf()` perfectly!</p>

<h2>Static Duck Typing via `typing.Protocol` (PEP 544)</h2>
<p>To unite the flexibility of Duck Typing with the precision of static type checking, Python introduced **`typing.Protocol`** (PEP 544). A Protocol defines a formal **Structural Interface**.</p>
<p>When you define a class inheriting from `typing.Protocol`, you specify required method signatures and attributes. Any concrete class in your codebase that implements those matching methods automatically satisfies the Protocol contract during static analysis (**without needing to inherit from the Protocol directly!**).</p>

<h2>Runtime Checkable Protocols (`@runtime_checkable`)</h2>
<p>By default, Protocols exist purely for static type checking at compile/lint time. If you apply the **`@runtime_checkable`** decorator to your `Protocol` definition, Python enables runtime structural checking via `isinstance(obj, MyProtocol)` and `issubclass(cls, MyProtocol)`. Python dynamically inspects `obj.__class__.__dict__` to verify that matching method signatures exist!</p>

<pre><code class="language-python">from typing import Protocol, runtime_checkable

# 1. Defining a Structural Protocol Interface with @runtime_checkable
@runtime_checkable
class Renderable(Protocol):
    """Any class possessing a render_content() -> str method satisfies this structural contract."""
    def render_content(self) -> str:
        ...

# 2. Concrete Class A: Does NOT inherit from Renderable, but matches signature!
class HtmlArticle:
    def __init__(self, heading: str, body: str):
        self.heading = heading
        self.body = body

    def render_content(self) -> str:
        return f"<article><h1>{self.heading}</h1><p>{self.body}</p></article>"

# 3. Concrete Class B: Unrelated class matching the exact structural contract
class TerminalProgressBar:
    def __init__(self, percent: int):
        self.percent = percent

    def render_content(self) -> str:
        bar = "█" * (self.percent // 10) + "-" * (10 - (self.percent // 10))
        return f"[{bar}] {self.percent}%"

# 4. Unrelated Class C: Lacks render_content()
class RawDatabaseRecord:
    def __init__(self, row_id: int):
        self.row_id = row_id

# Polymorphic processing pipeline accepting ANY object satisfying the Renderable Protocol
def broadcast_render(item: Renderable) -> None:
    # Runtime verification made possible via @runtime_checkable
    if not isinstance(item, Renderable):
        raise TypeError(f"Object {type(item).__name__} does not satisfy the Renderable Protocol!")
    print("Broadcasting:", item.render_content())

# Instantiating objects across distinct, unrelated class hierarchies
article = HtmlArticle("Advanced Protocols", "PEP 544 brings static structural typing to Python.")
progress = TerminalProgressBar(70)
db_row = RawDatabaseRecord(1001)

# Both unrelated classes satisfy the structural contract flawlessly
broadcast_render(article)
broadcast_render(progress)

# Verification check intercepted safely at runtime
print(f"\\nIs HtmlArticle a Renderable? {isinstance(article, Renderable)}")
print(f"Is RawDatabaseRecord a Renderable? {isinstance(db_row, Renderable)}")
</code></pre>

<h2>Protocols vs. Abstract Base Classes</h2>
<p>Use **`abc.ABC`** when you control the class hierarchy and want to share concrete helper methods (`describe()`) alongside enforcing explicit inheritance contracts (`Is-A`). Use **`typing.Protocol`** when writing flexible libraries, decoupled APIs, or integrating third-party objects where strict structural compatibility (`Duck Typing`) takes precedence over rigid inheritance trees.</p>
'''
    pages.append({
        "id": "6873",
        "title": "Structural vs Nominal Typing (typing.Protocol)",
        "topic_number": "OOP3.2.2",
        "section_title": "Section 3.2: Interfaces, Typing Protocols & Contracts",
        "unit_title": "Unit 3: Inheritance, Polymorphism & Composition",
        "content_html": p14_html.strip()
    })

    # Page 15: 6874 - Composition vs Inheritance (has-a vs is-a)
    p15_html = '''
<h2>The Pitfalls of Deep Inheritance (`Is-A`)</h2>
<p>One of the most famous architectural tenets in software engineering is: **"Favor Composition over Inheritance."**
While inheritance is excellent for representing strict **Is-A** relationships (`Dog is an Animal`), developers frequently misuse inheritance to share arbitrary code across classes (`class UserController(DatabasePool, Logger, AuthHandler):`).</p>
<p>As inheritance trees grow deeper than three levels, they become **fragile and tightly coupled**:
<ul>
  <li><strong>Fragile Base Class Problem:</strong> Altering a method inside a top-level base class can inadvertently break or mutate behavior across dozens of derived child classes.</li>
  <li><strong>Rigid Hierarchy Lock:</strong> A subclass is permanently locked to its superclass at compile time; you cannot swap a parent class's behavior dynamically at runtime during execution.</li>
  <li><strong>Attribute Namespace Pollution:</strong> Subclasses inherit every single attribute and helper method from every parent, leading to bloated objects with confusing method autocomplete suggestions.</li>
</ul></p>

<h2>The Power of Composition (`Has-A`)</h2>
<p>**Composition** constructs complex classes by assembling private instance attributes containing references to distinct, self-contained component objects (**Has-A** relationship: `Order has a PaymentGateway and has an InvoicePrinter`).</p>
<p>Instead of inheriting `Logger` methods directly, an `OrderService` class holds `self._logger = Logger()`. When logging is needed, it delegates the task to its composed component: `self._logger.log(...)`.</p>
<ul>
  <li><strong>Loose Coupling & Interchangeability:</strong> Composed objects interact solely through public interfaces. You can instantly swap `self._payment_gateway = StripeGateway()` for `self._payment_gateway = PayPalGateway()` at runtime without changing the outer class!</li>
  <li><strong>Clean Namespace Separation:</strong> Composed component attributes stay cleanly isolated inside `self._component`, preventing attribute name collisions across the main object.</li>
</ul>

<h2>Automatic Delegation via `__getattr__`</h2>
<p>To eliminate repetitive forwarding boilerplate (`def log(self, msg): return self._logger.log(msg)`), Python allows **Dynamic Delegation** using **`__getattr__(self, name)`**. When an attribute or method lookup fails on the outer composite class, Python invokes `__getattr__`, allowing you to forward the request directly to the internal composed object cleanly!</p>

<pre><code class="language-python"># Demonstrating Clean Composition & Dynamic Delegation via __getattr__

# 1. Self-contained Composed Component: Logging Engine
class StructuredLogger:
    def __init__(self, source_name: str):
        self.source_name = source_name

    def log_info(self, message: str) -> str:
        return f"[INFO] [{self.source_name}]: {message}"

    def log_error(self, message: str) -> str:
        return f"[ERROR] [{self.source_name}]: {message}"


# 2. Self-contained Composed Component: Database Connector
class PostgresConnector:
    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self.is_connected = False

    def connect(self) -> str:
        self.is_connected = True
        return f"Connected securely to database: {self.db_uri}"

    def execute_query(self, sql: str) -> str:
        if not self.is_connected:
            raise RuntimeError("Database not connected!")
        return f"Executed SQL [{sql}] on {self.db_uri}"


# 3. Composite Service Class: Assembles Components via Composition (HAS-A)
class CustomerOrderService:
    def __init__(self, service_name: str, db_uri: str):
        self.service_name = service_name
        # HAS-A relationships established inside __init__
        self._logger = StructuredLogger(source_name=service_name)
        self._db = PostgresConnector(db_uri=db_uri)

    def process_order(self, order_id: str, amount: float) -> str:
        """Main service logic leveraging composed components cleanly."""
        print(self._logger.log_info(f"Initiating processing for Order #{order_id} (${amount})"))
        if not self._db.is_connected:
            print(self._db.connect())
        result = self._db.execute_query(f"INSERT INTO orders VALUES ('{order_id}', {amount})")
        print(self._logger.log_info(f"Order #{order_id} committed successfully."))
        return result

    # 4. Dynamic Delegation Hook (__getattr__)
    def __getattr__(self, attribute_name: str):
        """If a method isn't found on CustomerOrderService, forward lookup to the Logger or DB!"""
        if hasattr(self._logger, attribute_name):
            return getattr(self._logger, attribute_name)
        elif hasattr(self._db, attribute_name):
            return getattr(self._db, attribute_name)
        raise AttributeError(f"'{type(self).__name__}' and its components possess no attribute '{attribute_name}'")

# Instantiating Composite Service
service = CustomerOrderService("OrderProcessingEngine", "postgres://db.internal:5432/shop")

# Executing composite workflow
service.process_order("ORD-88192", 1499.99)

# Testing Dynamic Delegation intercepted by __getattr__
print("\\nTesting Delegated Method Calls via __getattr__:")
# Calling log_error directly on service forwards to self._logger.log_error!
print(service.log_error("Simulated payment timeout intercepted."))
# Calling execute_query directly on service forwards to self._db.execute_query!
print(service.execute_query("SELECT count(*) FROM orders;"))
</code></pre>

<h2>Architectural Rule of Thumb</h2>
<p>Default to **Composition (`Has-A`)** when designing new service architectures, data processing pipelines, and business logic controllers. Reserve **Inheritance (`Is-A`)** strictly for domain models that share a genuine, unbreakable conceptual taxonomy (`Circle is a GeometricShape`), or when extending abstract base classes and framework plugins.</p>
'''
    pages.append({
        "id": "6874",
        "title": "Composition vs Inheritance (has-a vs is-a)",
        "topic_number": "OOP3.3.1",
        "section_title": "Section 3.3: Composition & Architectural Design Patterns",
        "unit_title": "Unit 3: Inheritance, Polymorphism & Composition",
        "content_html": p15_html.strip()
    })

    # Page 16: 6875 - Data Classes (@dataclass) & attrs
    p16_html = '''
<h2>Eliminating Boilerplate with `@dataclass`</h2>
<p>When creating classes whose primary responsibility is storing structured data (`UserAccount`, `ProductCatalogItem`, `NetworkConfig`), writing standard dunder methods (`__init__`, `__repr__`, `__eq__`) by hand is tedious and error-prone. If a class has ten attributes, manual `self.attr = attr` assignments inside `__init__` take dozens of lines.</p>
<p>Python's built-in **`@dataclass`** decorator automates this exact domain model boilerplate! By decorating a class with `@dataclass` and declaring type-hinted class attributes, Python automatically inspects the annotations and synthesizes optimized C-speed `__init__`, `__repr__`, and `__eq__` dunders at compile time!</p>

<h2>Key `@dataclass` Configuration Options</h2>
<ul>
  <li><strong>`@dataclass(frozen=True)`:</strong> Makes the entire object **Immutable** after initialization. Attempting to assign `obj.attr = val` after creation raises a `FrozenInstanceError`. Frozen dataclasses also automatically synthesize `__hash__()`, allowing instances to be stored cleanly inside sets or used as dictionary keys!</li>
  <li><strong>`@dataclass(order=True)`:</strong> Automatically generates rich comparison ordering dunders (`__lt__`, `__le__`, `__gt__`, `__ge__`) based on the sequential declaration order of the class attributes.</li>
  <li><strong>`@dataclass(slots=True)`:</strong> (Python 3.10+) Automatically synthesizes `__slots__` on the dataclass, granting massive memory optimization instantly without writing `__slots__ = (...)` manually!</li>
</ul>

<h2>Handling Mutable Defaults (`field`) & Validation (`__post_init__`)</h2>
<p>In Python, assigning a mutable object (`list`, `dict`, `set`) as a default attribute value (`items: list = []`) is a severe anti-pattern because all instances share the exact same global list in memory! Inside `@dataclass`, Python blocks `items: list = []` with a syntax error. To assign mutable defaults safely, use **`field(default_factory=list)`**, which calls the factory function to generate a unique list for every instantiated object.</p>
<p>If you need custom validation, calculated fields, or cross-attribute checks after `__init__` completes, define the **`__post_init__(self)`** method. Python automatically executes `__post_init__` at the exact conclusion of the generated `__init__` constructor!</p>

<pre><code class="language-python">from dataclasses import dataclass, field
from typing import List, Dict

@dataclass(order=True, frozen=True)
class StockPortfolioPosition:
    """An immutable, sortable dataclass representing a stock holding."""
    # Exclude ticker from sort comparison (`compare=False`) so sorting compares total valuation first!
    ticker_symbol: str = field(compare=False)
    shares_count: int
    purchase_price_usd: float
    
    # Safe mutable default collection generated uniquely per instance via default_factory
    tags: List[str] = field(default_factory=list, compare=False)
    
    # Computed attribute initialized inside __post_init__ (excluded from __init__ constructor args)
    total_valuation_usd: float = field(init=False, compare=True)

    def __post_init__(self):
        # Calculate valuation at end of instantiation
        valuation = round(self.shares_count * self.purchase_price_usd, 2)
        # Because frozen=True is enabled, standard self.total_valuation = val raises an error!
        # We must use object.__setattr__ inside __post_init__ to set computed fields on frozen objects.
        object.__setattr__(self, 'total_valuation_usd', valuation)

# Instantiating positions
pos_apple = StockPortfolioPosition("AAPL", shares_count=150, purchase_price_usd=180.50, tags=["Tech", "Growth"])
pos_nvidia = StockPortfolioPosition("NVDA", shares_count=80, purchase_price_usd=450.00, tags=["AI", "Semiconductors"])
pos_microsoft = StockPortfolioPosition("MSFT", shares_count=120, purchase_price_usd=400.00, tags=["Tech", "Cloud"])

# 1. Inspecting synthesized __repr__
print("Synthesized __repr__:", pos_apple)

# 2. Inspecting synthesized __eq__ and ordering (`order=True`) based on total_valuation_usd
print(f"Is AAPL == NVDA? {pos_apple == pos_nvidia}")
print(f"Is AAPL valuation (${pos_apple.total_valuation_usd}) < NVDA valuation (${pos_nvidia.total_valuation_usd})? {pos_apple < pos_nvidia}")

# 3. Sorting portfolio positions natively using built-in sorted()
portfolio = [pos_apple, pos_nvidia, pos_microsoft]
sorted_portfolio = sorted(portfolio, reverse=True)
print("\\nPortfolio Positions Sorted by Total Valuation (Highest to Lowest):")
for rank, pos in enumerate(sorted_portfolio, start=1):
    print(f"  {rank}. [{pos.ticker_symbol}] Valuation: ${pos.total_valuation_usd:,.2f} ({pos.shares_count} shares)")

# 4. Verifying Frozen Immutability Interception
try:
    pos_apple.shares_count = 200
except Exception as err:
    print(f"\\nFrozen Immutability Intercepted Safely: {type(err).__name__} ({err})")
</code></pre>

<h2>Dataclasses vs. `attrs` vs. `Pydantic`</h2>
<p>Use standard **`@dataclass`** for all internal domain models, data structures, and memory-conscious classes. If your project requires advanced pre-Python 3.7 support or complex converters, use the foundational **`attrs`** library. When handling raw JSON web payloads requiring automatic type coercion and deep validation (such as FastAPI endpoints), use **`Pydantic`** `BaseModel`.</p>
'''
    pages.append({
        "id": "6875",
        "title": "Data Classes (@dataclass) & attrs",
        "topic_number": "OOP4.1.1",
        "section_title": "Section 4.1: Modern Data Models & Enumerations",
        "unit_title": "Unit 4: Advanced Architectural Patterns & Metaprogramming",
        "content_html": p16_html.strip()
    })

    # Page 17: 6876 - Enumerations & Flag Types (enum.Enum, enum.Flag)
    p17_html = '''
<h2>The Hazard of Magic Constants</h2>
<p>Across legacy codebases, developers frequently represent state options using raw integers or string literals (`status = 1` or `if order.state == "PENDING":`). This practice—known as **Magic Constants**—invites subtle bugs. String typos (`"PENDING"` vs `"PNDING"`) go undetected until runtime, integers carry no self-documenting meaning, and arbitrary values can be assigned without boundary checking (`order.status = 999`).</p>
<p>To eliminate magic constants and enforce type safety, Python provides the **`enum`** module containing **`Enum`**, **`IntEnum`**, and **`Flag`** classes.</p>

<h2>Anatomy of `enum.Enum`</h2>
<p>An Enumeration (`class OrderStatus(Enum):`) is a class representing a fixed, immutable collection of symbolically named constant members.
<ul>
  <li><strong>Immutability & Unique Identity:</strong> Enum members (`OrderStatus.SHIPPED`) are singleton objects; their values (`.value`) and symbolic names (`.name`) cannot be reassigned or mutated after class definition.</li>
  <li><strong>Self-Documenting Iteration:</strong> You can iterate directly over the enum class (`for status in OrderStatus:`) or check membership cleanly (`OrderStatus.SHIPPED in active_statuses`).</li>
  <li><strong>`enum.auto()` Helper:</strong> When precise member values don't matter (`RED = 1, GREEN = 2`), use `enum.auto()` to let Python automatically assign distinct sequential integer IDs (`1, 2, 3...`) to members at compile time.</li>
</ul></p>

<h2>Combining States via Bitwise `enum.Flag`</h2>
<p>When an object can simultaneously possess multiple combined states (`FilePermissions.READ | FilePermissions.WRITE`), using a standard `Enum` forces you to create separate `set()` collections. Instead, Python provides **`enum.Flag`**.</p>
<p>By assigning powers-of-two bitwise integer values (`1, 2, 4, 8, 16...` or `auto()`), `Flag` members can be combined using bitwise OR (`|`), intersected via bitwise AND (`&`), or inverted (`~`) cleanly within a single integer representation!</p>

<pre><code class="language-python">from enum import Enum, Flag, auto

# 1. Standard Enumeration using auto() and Custom Method Behavior
class ServerState(Enum):
    OFFLINE = auto()
    BOOTING = auto()
    RUNNING = auto()
    MAINTENANCE = auto()
    CRASHED = auto()

    def is_operational(self) -> bool:
        """Custom method housed directly on the Enum class!"""
        return self in (ServerState.RUNNING, ServerState.MAINTENANCE)


# 2. Bitwise Flag Enumeration representing multi-state security permissions
class AccessPermission(Flag):
    NONE = 0
    READ = auto()       # Bit value: 1 (2^0)
    WRITE = auto()      # Bit value: 2 (2^1)
    EXECUTE = auto()    # Bit value: 4 (2^2)
    ADMIN = auto()      # Bit value: 8 (2^3)
    
    # Combined alias flags defined right inside the Enum!
    FULL_CONTROL = READ | WRITE | EXECUTE | ADMIN

# Testing Standard Enum Access and Custom Methods
current_state = ServerState.RUNNING
print(f"Server State Member: {current_state} (Name: '{current_state.name}', Value: {current_state.value})")
print(f"Is Server Operational? {current_state.is_operational()}")

# Testing Bitwise Flag Combinations (`|`) and Verification (`&` or `in`)
user_perms = AccessPermission.READ | AccessPermission.WRITE
print(f"\\nAssigned Combined Permissions: {user_perms}")
print(f"Does User possess READ access? {bool(user_perms & AccessPermission.READ)}")
print(f"Does User possess ADMIN access? {AccessPermission.ADMIN in user_perms}")

# Adding EXECUTE permission dynamically via bitwise OR (`|=`)
user_perms |= AccessPermission.EXECUTE
print(f"Upgraded Permissions: {user_perms}")
</code></pre>

<h2>Why Enums Belong in Modern OOP</h2>
<p>Enums elevate code quality by transforming fragile string and integer parameters into robust, self-documenting domain objects. Use `Enum` for distinct categorical choices (`PaymentStatus`, `UserRole`) and `Flag` whenever an entity can hold multiple simultaneous options (`SystemCapabilities`, `AccessRights`).</p>
'''
    pages.append({
        "id": "6876",
        "title": "Enumerations & Flag Types (enum.Enum, enum.Flag)",
        "topic_number": "OOP4.1.2",
        "section_title": "Section 4.1: Modern Data Models & Enumerations",
        "unit_title": "Unit 4: Advanced Architectural Patterns & Metaprogramming",
        "content_html": p17_html.strip()
    })

    # Page 18: 6877 - Metaclasses & Class Creation Mechanics (type, __init_subclass__)
    p18_html = '''
<h2>Classes as Objects (`type` as the Metaclass)</h2>
<p>In most programming languages, classes are static source-code constructs parsed by the compiler. In Python, **a class is itself an object living in memory!** Because a class is an object, it can be passed as an argument to functions, modified dynamically, and instantiated programmatically at runtime.</p>
<p>If `car = Car()` is an object whose class is `Car`, what is the class of `Car` itself? The answer is **`type`**. Just as `Car` is a class that creates instance objects (`car`), **`type` is the Metaclass that creates class objects (`Car`)**.</p>
<p>You can instantiate new class objects dynamically without writing `class Foo:` by using `type`'s three-argument constructor: **`type(class_name, bases_tuple, namespace_dict)`**.</p>

<h2>What is a Custom Metaclass?</h2>
<p>A **Metaclass** is a factory class that inherits from `type` (`class Meta(type):`) and intercepts the creation of class objects across an inheritance tree. When Python compiles a class (`class MyClass(metaclass=Meta):`), it invokes `Meta.__new__` and `Meta.__init__` before the class object (`MyClass`) is finalized in memory!</p>
<p>Metaclasses allow you to perform powerful metaprogramming across entire class hierarchies:
<ul>
  <li>Automatically registering all defined subclasses into global plugin registries (`ORM Model Registries`).</li>
  <li>Enforcing mandatory naming conventions (`ensuring all method names are snake_case`).</li>
  <li>Dynamically injecting descriptors, attributes, or docstrings onto classes at creation time.</li>
</ul></p>

<h2>The Modern Alternative: `__init_subclass__` Hook</h2>
<p>While custom metaclasses (`metaclass=...`) are immensely powerful, they introduce complexity and can cause metaclass conflicts when combining multiple third-party libraries. Python 3.6 introduced a much cleaner, more elegant class creation hook: **`__init_subclass__(cls, **kwargs)`**.</p>
<p>Defined directly on a parent base class, `__init_subclass__` executes automatically whenever any derived child class subclassing that base class is defined! This provides **90% of the power of metaclasses with zero metaclass complexity**.</p>

<pre><code class="language-python"># Demonstrating Metaclasses vs Modern __init_subclass__ Hooks

# 1. Advanced Custom Metaclass: Enforces attribute rules during class definition
class StrictDocstringMeta(type):
    """Metaclass verifying that every created class possesses an explicit docstring."""
    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        if "__doc__" not in namespace or not namespace["__doc__"]:
            # Intercept class compilation instantly before class object is created!
            raise TypeError(f"Class creation failed: Class '{name}' MUST define a valid docstring.")
        print(f"Metaclass [{mcs.__name__}] successfully validated and compiled class: {name}")
        return super().__new__(mcs, name, bases, namespace)


# 2. Modern __init_subclass__ Hook: Automatic Plugin Registration Architecture
class PluginRegistryBase:
    """Base class utilizing __init_subclass__ to register plugins dynamically without Metaclasses."""
    registered_plugins = {}

    def __init_subclass__(cls, plugin_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__
        PluginRegistryBase.registered_plugins[name] = cls
        print(f"Hook __init_subclass__ registered plugin: '{name}' -> {cls.__name__}")


# 3. Testing Class created via Metaclass
class AuditedService(metaclass=StrictDocstringMeta):
    """An audited service model satisfying the metaclass docstring requirement."""
    def run_service(self):
        return "Service Active"


# 4. Testing Subclasses auto-registering via __init_subclass__
class EmailNotificationPlugin(PluginRegistryBase, plugin_name="email_sender"):
    def send(self, msg: str):
        return f"Email Sent: {msg}"

class SlackAlertPlugin(PluginRegistryBase, plugin_name="slack_webhook"):
    def alert(self, msg: str):
        return f"Slack Alert: {msg}"

# Inspecting Global Plugin Registry populated automatically upon class compilation
print("\\nGlobal Registered Plugins Table:")
for name, cls_obj in PluginRegistryBase.registered_plugins.items():
    print(f"  Plugin Key '{name}' -> Class Object {cls_obj}")

# Verifying Metaclass Interception on Class missing docstring
try:
    # Attempting to define a class dynamically without a docstring
    type("BadClassWithoutDocstring", (), {"__module__": __name__}, metaclass=StrictDocstringMeta)
except TypeError as err:
    print(f"\\nMetaclass Interception Confirmed: {err}")
</code></pre>

<h2>When to Use Metaclasses vs `__init_subclass__`</h2>
<p>Always use **`__init_subclass__`** first for class registration, keyword configuration (`plugin_name="..."`), and verifying subclass methods upon definition. Only reach for custom **`type` metaclasses** when you need to modify class dictionaries before allocation, manipulate the method resolution order (`__mro_entries__`), or build complex ORM metaclass engines.</p>
'''
    pages.append({
        "id": "6877",
        "title": "Metaclasses & Class Creation Mechanics (type, __init_subclass__)",
        "topic_number": "OOP4.2.1",
        "section_title": "Section 4.2: Metaprogramming & Architectural Design Patterns",
        "unit_title": "Unit 4: Advanced Architectural Patterns & Metaprogramming",
        "content_html": p18_html.strip()
    })

    # Page 19: 6878 - Gang of Four Design Patterns in Pythonic OOP
    p19_html = '''
<h2>Adapting Classic Design Patterns to Python</h2>
<p>The **Gang of Four (GoF)** design patterns (`Gamma, Helm, Johnson, Vlissides, 1994`) established architectural blueprints for object-oriented systems. However, because GoF patterns were designed for static, verbose languages like C++ and Java, blindly porting them line-by-line into Python results in clumsy, unpythonic code.</p>
<p>Because Python treats **functions and classes as first-class objects**, classic design patterns can be implemented in vastly simpler, more elegant ways!</p>

<h2>The Strategy Pattern (First-Class Functions & Classes)</h2>
<p>The **Strategy Pattern** encapsulates a family of interchangeable algorithms into distinct objects, allowing the client (`OrderProcessor`) to swap processing algorithms at runtime without altering conditional chains (`if/elif/else`).</p>
<p>In Java, implementing Strategy requires defining an `AlgorithmInterface` and multiple verbose concrete classes (`StandardShippingStrategy`, `ExpressShippingStrategy`). In Python, because functions and callable objects (`__call__`) are first-class citizens, you can pass function objects or clean classes directly into the context object!</p>

<h2>The Observer Pattern (Pub/Sub Event Notification)</h2>
<p>The **Observer Pattern** defines a one-to-many subscription relationship between a central **Subject (`EventBroker`)** and multiple registered **Observers (`Subscribers`)**. Whenever the Subject's internal state changes (`stock price spike`, `database commit`), it iterates through its registry and automatically invokes an update hook across all registered observers (`observer.on_event()`).</p>
<p>This achieves strict **Decoupling**: the central `Subject` does not need to know the specific class identities or concrete mechanics of the subscribed observers; it merely broadcasts the event notification cleanly across the registry.</p>

<pre><code class="language-python">from typing import Callable, List

# --- 1. PYTHONIC STRATEGY PATTERN (First-Class Functions as Strategies) ---

# Strategy functions matching identical callable signature: (float) -> float
def standard_shipping_strategy(order_amount: float) -> float:
    return 15.00 if order_amount < 100.0 else 0.00

def express_air_strategy(order_amount: float) -> float:
    return 35.00 + (order_amount * 0.05)

class ECommerceOrder:
    """Context object accepting dynamic Strategy function objects at runtime."""
    def __init__(self, order_id: str, subtotal: float, shipping_strategy: Callable[[float], float]):
        self.order_id = order_id
        self.subtotal = subtotal
        self.shipping_strategy = shipping_strategy

    def calculate_total(self) -> float:
        # Execute injected strategy function cleanly
        shipping_cost = self.shipping_strategy(self.subtotal)
        return round(self.subtotal + shipping_cost, 2)


# --- 2. PYTHONIC OBSERVER PATTERN (Pub/Sub Event Broker Architecture) ---

class EventSubscriber:
    """Base Observer interface."""
    def __init__(self, name: str):
        self.name = name

    def on_event(self, event_type: str, payload: dict) -> None:
        print(f"  [Observer: {self.name}] Received Event '{event_type}' -> Payload: {payload}")

class CentralEventBroker:
    """Subject/Broker managing observer subscriptions and event broadcasts."""
    def __init__(self):
        self._subscribers: List[EventSubscriber] = []

    def subscribe(self, observer: EventSubscriber) -> None:
        if observer not in self._subscribers:
            self._subscribers.append(observer)

    def unsubscribe(self, observer: EventSubscriber) -> None:
        if observer in self._subscribers:
            self._subscribers.remove(observer)

    def broadcast_event(self, event_type: str, payload: dict) -> None:
        print(f"\\nBroadcasting Central Event: [{event_type}] across {len(self._subscribers)} subscribers...")
        for observer in self._subscribers:
            observer.on_event(event_type, payload)

# Testing Strategy Pattern Swapping
order = ECommerceOrder("ORD-101", subtotal=80.00, shipping_strategy=standard_shipping_strategy)
print(f"Order [{order.order_id}] Total with Standard Shipping: ${order.calculate_total():.2f}")

# Dynamically swapping strategy at runtime without recreating the order object!
order.shipping_strategy = express_air_strategy
print(f"Order [{order.order_id}] Total after swapping to Express Air Strategy: ${order.calculate_total():.2f}")

# Testing Observer Pattern Event Broadcasting
broker = CentralEventBroker()
logger_sub = EventSubscriber("SystemLogWriter")
email_sub = EventSubscriber("ClientEmailNotifier")
analytics_sub = EventSubscriber("RealTimeDashboard")

broker.subscribe(logger_sub)
broker.subscribe(email_sub)
broker.subscribe(analytics_sub)

# Broadcasting event notifies all subscribed observers automatically
broker.broadcast_event("ORDER_COMPLETED", {"order_id": order.order_id, "total_usd": order.calculate_total()})
</code></pre>

<h2>Pattern Mastery Rule</h2>
<p>Always adapt classic design patterns to Python's dynamic strengths. Use first-class functions and callable classes (`__call__`) for Strategy and Command patterns, use `@property` descriptors instead of verbose Proxy/Decorator wrappers, and use `__init_subclass__` instead of cumbersome abstract factory boilerplate.</p>
'''
    pages.append({
        "id": "6878",
        "title": "Gang of Four Design Patterns in Pythonic OOP",
        "topic_number": "OOP4.2.2",
        "section_title": "Section 4.2: Metaprogramming & Architectural Design Patterns",
        "unit_title": "Unit 4: Advanced Architectural Patterns & Metaprogramming",
        "content_html": p19_html.strip()
    })

    # Page 20: 6879 - OOP Performance, Weak References & Memory Management (weakref)
    p20_html = '''
<h2>Python's Memory Engine: Reference Counting vs. Garbage Collection</h2>
<p>To architect high-performance, long-running Python systems (`web servers`, `data processing daemons`), you must understand how Python deallocates objects from memory. Python employs two complementary memory reclamation mechanisms:
<ol>
  <li><strong>Reference Counting (Immediate Deallocation):</strong> Every object in system memory maintains an internal integer counter tracking how many active variables or collections reference it (`sys.getrefcount(obj)`). When an object's reference count drops to `0`, Python deallocates the object immediately!</li>
  <li><strong>Cyclic Garbage Collector (`gc` module):</strong> Reference counting has a fatal flaw: **Circular References** (`Parent._child = Child` and `Child._parent = Parent`). Because both objects reference each other, their counts never reach `0`, preventing immediate reference-counted deallocation. Python's cyclic `gc` collector periodically sweeps memory to detect and clean up these isolated circular islands.</li>
</ol></p>

<h2>Breaking Cycles with Weak References (`weakref`)</h2>
<p>While the cyclic `gc` collector eventually sweeps circular references, waiting for `gc` sweeps in high-throughput applications causes massive RAM spikes and unpredictable latency pauses. To build clean parent-child relationships and instance caches without memory leaks, use the **`weakref`** module.</p>
<p>A **Weak Reference (`weakref.ref(obj)`)** creates a non-owning link to a target object **without incrementing its reference count**! If no strong references (`standard assignments`) remain pointing to the object, garbage collection immediately reclaims the object, and any active weak references gracefully evaluate to `None`.</p>

<h2>Specialized Weak Maps (`WeakKeyDictionary` / `WeakValueDictionary`)</h2>
<p>When caching object metadata (`tracking active database models` or `memoizing heavy object computations`), storing object instances inside a standard Python `dict` creates strong references, locking those objects in memory forever!</p>
<p>Using **`weakref.WeakKeyDictionary`** or **`WeakValueDictionary`** solves this cleanly. When a key (or value) object inside a weak map is garbage collected elsewhere in the application, the weak dictionary automatically removes the cached entry without developer intervention!</p>

<pre><code class="language-python">import weakref
import gc

# 1. Demonstrating Circular Reference Leaks vs Weak References inside Parent-Child trees

class Node:
    def __init__(self, name: str):
        self.name = name
        self.parent = None
        self.children = []

    def add_child_strong(self, child: "Node"):
        """Strong circular reference: Parent -> Child and Child -> Parent."""
        self.children.append(child)
        child.parent = self  # Increments Parent's reference count!

    def add_child_weak(self, child: "Node"):
        """Weak reference: Child points to Parent via weakref without incrementing reference count!"""
        self.children.append(child)
        child.parent = weakref.ref(self)  # Non-owning weak link!

    def get_parent(self):
        if self.parent is None:
            return None
        # If parent is a weak reference, call it () to retrieve target object or None
        return self.parent() if isinstance(self.parent, weakref.ReferenceType) else self.parent

    def __del__(self):
        print(f"  [Memory Deallocation Hook (__del__)]: Node '{self.name}' reclaimed from RAM.")


# 2. Testing Weak Reference Cleanup vs Caching
print("Testing Weak References inside Parent-Child Hierarchy:")
root_parent = Node("Root-Directory")
child_leaf = Node("Leaf-File")

root_parent.add_child_weak(child_leaf)
print(f"Child successfully resolved Parent via weakref: {child_leaf.get_parent().name}")

# Deleting root_parent immediately drops its strong reference count to 0!
print("Deleting strong reference to root_parent...")
del root_parent

# Checking if weak reference inside child gracefully returns None after parent deallocation
print(f"Child get_parent() result after deallocation: {child_leaf.get_parent()}")

# 3. Testing Automatic Metadata Cleanup via WeakKeyDictionary
print("\\nTesting Automatic Cache Cleanup via WeakKeyDictionary:")
cache_map = weakref.WeakKeyDictionary()

session_obj = Node("UserSession-Active")
cache_map[session_obj] = {"login_ip": "10.0.0.42", "auth_token": "JWT_SECRET"}
print(f"Cache size with active session object: {len(cache_map)} item(s)")

# Deleting session_obj allows WeakKeyDictionary to automatically evict the cached metadata entry!
print("Deleting session_obj from memory...")
del session_obj
gc.collect()  # Force quick check
print(f"Cache size after session object deallocation: {len(cache_map)} item(s)")
</code></pre>

<h2>Congratulations! Your Mastery of Advanced Python OOP</h2>
<p>By completing this comprehensive 20-module journey through Advanced Python Object-Oriented Programming, you have transitioned from procedural coding to enterprise architectural mastery. You now understand how Python allocates memory (`__new__` vs `__init__`), how descriptors intercept and validate attributes under the hood, how the C3 Linearization MRO traverses multiple inheritance, and how to decouple massive systems cleanly using Composition (`Has-A`), structural typing (`Protocol`), and Pythonic design patterns.</p>
<p>Use this deep foundational knowledge to build high-performance, maintainable, and elegant object-oriented software architectures across the Python ecosystem!</p>
'''
    pages.append({
        "id": "6879",
        "title": "OOP Performance, Weak References & Memory Management (weakref)",
        "topic_number": "OOP4.3.1",
        "section_title": "Section 4.3: Memory Management & Performance Optimization",
        "unit_title": "Unit 4: Advanced Architectural Patterns & Metaprogramming",
        "content_html": p20_html.strip()
    })

    return pages

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
        
        fname = FILENAME_DICT.get(page_id, "advanced_oop.py")
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

def trim_blocks_to_limit(blocks, max_chars=4850):
    while True:
        total = sum(
            len(b.get("text", "")) + len(b.get("code", "")) + len(b.get("answer", ""))
            for b in blocks
        )
        if total <= max_chars:
            break
            
        # Find the longest text block that is > 180 chars
        text_blocks = [(i, b) for i, b in enumerate(blocks) if b.get("type") == "text"]
        if not text_blocks:
            break
        text_blocks.sort(key=lambda x: len(x[1].get("text", "")), reverse=True)
        longest_idx, longest_b = text_blocks[0]
        txt = longest_b["text"]
        if len(txt) <= 180:
            break
            
        if txt.endswith("</p>"):
            inner = txt[:-4].rstrip()
            last_period = inner.rfind('.', 0, len(inner) - 100)
            if last_period != -1 and last_period > 120:
                longest_b["text"] = inner[:last_period + 1] + "</p>"
            else:
                longest_b["text"] = inner[:len(inner)-100].rstrip() + "...</p>"
        else:
            last_period = txt.rfind('.', 0, len(txt) - 100)
            if last_period != -1 and last_period > 120:
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
        trim_blocks_to_limit(blocks, max_chars=4850)
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
                "href": "https://app.growhall.com/books/python_advanced_oop",
                "level": 1,
                "text": "Advanced Python OOP"
            },
            {
                "href": f"https://app.growhall.com/books/python_advanced_oop/{page_id}",
                "level": 2,
                "text": unit_title
            },
            {
                "href": f"https://app.growhall.com/books/python_advanced_oop/{page_id}",
                "level": 3,
                "text": section_title
            },
            {
                "href": f"https://app.growhall.com/books/python_advanced_oop/{page_id}",
                "level": 4,
                "text": f"{topic_number} {title}"
            }
        ]
        
        content_data = {
            "url": f"https://app.growhall.com/books/python_advanced_oop/{page_id}",
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
            "url": f"https://app.growhall.com/books/python_advanced_oop/{page_id}",
            "folder": page_id,
            "reading_time_minutes": reading_time,
            "character_count": char_count
        })
        
    # 2. Write master book.json
    book_json_data = {
        "id": "python_advanced_oop",
        "title": "Advanced Python: Object-Oriented Programming",
        "url": "https://app.growhall.com/books/python_advanced_oop",
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
        
    # Check if python_advanced_oop is already in books array
    existing_entry = None
    for b in books_data.get("books", []):
        if b.get("id") == "python_advanced_oop":
            existing_entry = b
            break
            
    new_book_entry = {
        "id": "python_advanced_oop",
        "title": "Advanced Python: Object-Oriented Programming",
        "url": "https://app.growhall.com/books/python_advanced_oop",
        "pages_count": 20,
        "folder": "Book_python_advanced_oop",
        "created_at": "2026-07-12T00:00:00.000000",
        "cover_image": None,
        "color_from": "#8b5cf6",
        "color_to": "#4c1d95"
    }
    
    if existing_entry:
        existing_entry.update(new_book_entry)
        print("Updated existing python_advanced_oop entry in books.json.")
    else:
        books_data["books"].append(new_book_entry)
        print("Added new python_advanced_oop entry to books.json.")
        
    books_data["last_updated"] = "2026-07-12T00:00:00.000000"
    
    with open(books_json_path, "w", encoding="utf-8") as f:
        json.dump(books_data, f, indent=2, ensure_ascii=False)
    print("Updated data/books.json completely.")

if __name__ == "__main__":
    main()

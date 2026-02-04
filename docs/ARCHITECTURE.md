# RustyAML Architecture & Flow Diagrams

This document visualizes the architecture and data flow of RustyAML compared to PyYAML.

## Table of Contents

1. [High-Level Architecture Comparison](#high-level-architecture-comparison)
2. [Parsing Flow](#parsing-flow)
3. [Safety Check Flow](#safety-check-flow)
4. [Batch Processing Flow](#batch-processing-flow)
5. [Memory & Performance](#memory--performance)
6. [Component Diagrams](#component-diagrams)

---

## High-Level Architecture Comparison

### PyYAML Architecture

```mermaid
flowchart TB
    subgraph Python["Python Runtime"]
        subgraph PyYAML["PyYAML Library"]
            Scanner["Scanner<br/>(Python)"]
            Parser["Parser<br/>(Python)"]
            Composer["Composer<br/>(Python)"]
            Constructor["Constructor<br/>(Python)"]
        end
        
        subgraph Optional["Optional C Extension"]
            LibYAML["LibYAML<br/>(C Library)"]
            CLoader["CSafeLoader"]
        end
        
        PythonObjects["Python Objects<br/>(dict, list, str, int, ...)"]
    end
    
    YAML["YAML String"] --> Scanner
    Scanner --> Parser
    Parser --> Composer
    Composer --> Constructor
    Constructor --> PythonObjects
    
    YAML -.->|"With C Extension"| LibYAML
    LibYAML -.-> CLoader
    CLoader -.-> PythonObjects
    
    style Python fill:#3776ab,color:#fff
    style PyYAML fill:#ffd43b,color:#000
    style Optional fill:#f0f0f0,color:#000,stroke-dasharray: 5 5
```

### RustyAML Architecture

```mermaid
flowchart TB
    subgraph Python["Python Runtime"]
        PyWrapper["Python Wrapper<br/>(rustyaml/__init__.py)"]
        PythonObjects["Python Objects<br/>(dict, list, str, int, ...)"]
    end
    
    subgraph Rust["Rust Core (Native Code)"]
        subgraph PyO3["PyO3 Bindings"]
            Bridge["Python ↔ Rust Bridge"]
        end
        
        subgraph Parser["serde_yaml Parser"]
            Lexer["Lexer"]
            YAMLParser["YAML Parser"]
            Deserializer["Deserializer"]
        end
        
        subgraph Safety["Safety Layer"]
            QuickScan["Quick Tag Scanner"]
            DeepCheck["Deep Safety Check"]
        end
        
        subgraph Converter["Type Converter"]
            YamlToPy["yaml_to_python()"]
            StringIntern["String Interning"]
        end
        
        subgraph Batch["Batch Processor"]
            Rayon["Rayon Thread Pool"]
            GILRelease["GIL Release"]
        end
    end
    
    YAML["YAML String"] --> PyWrapper
    PyWrapper --> Bridge
    Bridge --> QuickScan
    QuickScan --> Lexer
    Lexer --> YAMLParser
    YAMLParser --> Deserializer
    Deserializer --> DeepCheck
    DeepCheck --> YamlToPy
    YamlToPy --> StringIntern
    StringIntern --> Bridge
    Bridge --> PythonObjects
    
    style Python fill:#3776ab,color:#fff
    style Rust fill:#dea584,color:#000
    style PyO3 fill:#f9d71c,color:#000
    style Safety fill:#90EE90,color:#000
```

---

## Parsing Flow

### PyYAML Parsing Flow (Pure Python)

```mermaid
sequenceDiagram
    participant User as User Code
    participant API as yaml.safe_load()
    participant Scanner as Scanner
    participant Parser as Parser
    participant Composer as Composer
    participant Constructor as Constructor
    participant GIL as Python GIL
    
    User->>API: yaml.safe_load(yaml_str)
    
    Note over GIL: GIL held throughout
    
    API->>Scanner: scan(yaml_str)
    loop For each character
        Scanner->>Scanner: Tokenize (Python)
    end
    Scanner-->>Parser: Token stream
    
    Parser->>Parser: Build event stream
    Parser-->>Composer: Events
    
    Composer->>Composer: Build node graph
    Composer-->>Constructor: Nodes
    
    Constructor->>Constructor: Construct Python objects
    Note over Constructor: Creates dict, list, str, etc.
    
    Constructor-->>API: Python object
    API-->>User: Result (dict/list)
```

### RustyAML Parsing Flow

```mermaid
sequenceDiagram
    participant User as User Code
    participant Wrapper as rustyaml.safe_load()
    participant PyO3 as PyO3 Bridge
    participant Safety as Safety Check
    participant Serde as serde_yaml
    participant Conv as Type Converter
    participant GIL as Python GIL
    
    User->>Wrapper: rustyaml.safe_load(yaml_str)
    Wrapper->>PyO3: Call Rust function
    
    Note over GIL: GIL released for parsing
    
    PyO3->>Safety: quick_safety_check(yaml_str)
    Safety->>Safety: Scan for dangerous tags
    
    alt Dangerous tags found
        Safety-->>PyO3: Error
        PyO3-->>User: ValueError
    end
    
    PyO3->>Serde: parse(yaml_str)
    Note over Serde: Native Rust parsing<br/>(Very fast!)
    
    Serde->>Serde: Lexing + Parsing + Deserialize
    Serde-->>PyO3: serde_yaml::Value
    
    PyO3->>Safety: check_safety(value)
    Safety->>Safety: Recursive tag check
    
    Note over GIL: GIL re-acquired
    
    PyO3->>Conv: yaml_to_python(value)
    Conv->>Conv: Convert to Python types
    Note over Conv: String interning for small strings
    
    Conv-->>PyO3: PyObject
    PyO3-->>Wrapper: Python dict/list
    Wrapper-->>User: Result
```

---

## Safety Check Flow

### PyYAML Safety Model

```mermaid
flowchart TD
    Input["YAML Input"] --> Loader{"Which Loader?"}
    
    Loader -->|"yaml.load()"| Unsafe["⚠️ UNSAFE<br/>Executes arbitrary code"]
    Loader -->|"yaml.safe_load()"| Safe["SafeLoader"]
    Loader -->|"yaml.unsafe_load()"| Unsafe
    
    Safe --> Construct["Limited Constructors"]
    Construct --> BasicTypes["Only basic types:<br/>dict, list, str, int, float, bool, None"]
    
    Unsafe --> AllConstructors["All Constructors"]
    AllConstructors --> Danger["!!python/object<br/>!!python/module<br/>!!python/apply<br/>etc."]
    Danger --> RCE["🔴 Remote Code Execution"]
    
    style Unsafe fill:#ff6b6b,color:#fff
    style RCE fill:#ff0000,color:#fff
    style Safe fill:#51cf66,color:#fff
    style BasicTypes fill:#90EE90,color:#000
```

### RustyAML Safety Model

```mermaid
flowchart TD
    Input["YAML Input"] --> QuickScan["Quick Safety Scan<br/>(Before parsing)"]
    
    QuickScan -->|"Check raw string"| Patterns{"Contains dangerous<br/>patterns?"}
    
    Patterns -->|"!!python/object<br/>!!python/module<br/>!!python/apply<br/>etc."| Reject1["❌ Reject Immediately"]
    
    Patterns -->|"Safe"| Parse["Parse with serde_yaml"]
    
    Parse --> DeepCheck["Deep Safety Check<br/>(After parsing)"]
    
    DeepCheck --> Walk["Walk AST recursively"]
    Walk --> Tagged{"Tagged values?"}
    
    Tagged -->|"Dangerous tags"| Reject2["❌ Reject"]
    Tagged -->|"No tags"| Convert["Convert to Python"]
    
    Convert --> Result["✅ Safe Python Objects"]
    
    subgraph TwoPhase["Two-Phase Safety"]
        QuickScan
        DeepCheck
    end
    
    style Reject1 fill:#ff6b6b,color:#fff
    style Reject2 fill:#ff6b6b,color:#fff
    style Result fill:#51cf66,color:#fff
    style TwoPhase fill:#e8f5e9,color:#000
```

### Safety Check Details

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: Quick Scan"]
        Raw["Raw YAML String"]
        Regex["Pattern Matching"]
        Tags["Dangerous Tags:<br/>!!python/object<br/>!!python/object/apply<br/>!!python/module<br/>!!python/name<br/>!!python/object/new"]
    end
    
    subgraph Phase2["Phase 2: Deep Check"]
        AST["Parsed AST"]
        Recurse["Recursive Walk"]
        TagCheck["Check serde_yaml::Value::Tagged"]
    end
    
    Raw --> Regex
    Regex --> Tags
    Tags -->|"Found"| Block1["🛑 Block"]
    Tags -->|"Not found"| AST
    AST --> Recurse
    Recurse --> TagCheck
    TagCheck -->|"Dangerous"| Block2["🛑 Block"]
    TagCheck -->|"Safe"| Allow["✅ Allow"]
    
    style Block1 fill:#ff6b6b,color:#fff
    style Block2 fill:#ff6b6b,color:#fff
    style Allow fill:#51cf66,color:#fff
```

---

## Batch Processing Flow

### PyYAML Batch Processing (Sequential)

```mermaid
sequenceDiagram
    participant User as User Code
    participant GIL as Python GIL
    participant PyYAML as PyYAML
    
    User->>PyYAML: Process 100 YAML files
    
    Note over GIL: GIL held entire time
    
    loop For each file (sequential)
        PyYAML->>PyYAML: Parse file 1
        PyYAML->>PyYAML: Parse file 2
        PyYAML->>PyYAML: Parse file 3
        Note over PyYAML: ... (one at a time)
        PyYAML->>PyYAML: Parse file 100
    end
    
    PyYAML-->>User: List of 100 results
    
    Note over User,PyYAML: Total time = sum of all parse times
```

### RustyAML Batch Processing (Parallel)

```mermaid
sequenceDiagram
    participant User as User Code
    participant Wrapper as rustyaml
    participant GIL as Python GIL
    participant Rayon as Rayon Thread Pool
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant T3 as Thread 3
    participant T4 as Thread 4
    
    User->>Wrapper: safe_load_many(100 yamls)
    Wrapper->>GIL: Release GIL
    
    Note over GIL: GIL released!
    
    Wrapper->>Rayon: par_iter(yamls)
    
    par [Parallel Parsing]
        Rayon->>T1: Parse files 1-25
        Rayon->>T2: Parse files 26-50
        Rayon->>T3: Parse files 51-75
        Rayon->>T4: Parse files 76-100
        
        T1-->>Rayon: Results 1-25
        T2-->>Rayon: Results 26-50
        T3-->>Rayon: Results 51-75
        T4-->>Rayon: Results 76-100
    end
    
    Rayon-->>Wrapper: All parsed values
    
    Wrapper->>GIL: Re-acquire GIL
    Note over GIL: GIL re-acquired
    
    Wrapper->>Wrapper: Convert all to Python
    Wrapper-->>User: List of 100 results
    
    Note over User,T4: Total time ≈ max(thread times) + conversion
```

### Parallel Processing Visualization

```mermaid
gantt
    title Batch Processing: 100 YAML Files
    dateFormat X
    axisFormat %s
    
    section PyYAML
    File 1-25    :a1, 0, 25
    File 26-50   :a2, after a1, 25
    File 51-75   :a3, after a2, 25
    File 76-100  :a4, after a3, 25
    
    section RustyAML
    Thread 1 (1-25)   :b1, 0, 7
    Thread 2 (26-50)  :b2, 0, 7
    Thread 3 (51-75)  :b3, 0, 7
    Thread 4 (76-100) :b4, 0, 7
    Convert to Python :b5, after b4, 3
```

---

## Memory & Performance

### Memory Model Comparison

```mermaid
flowchart TB
    subgraph PyYAML_Mem["PyYAML Memory Usage"]
        PY_Input["Input String<br/>(Python str)"]
        PY_Tokens["Token Objects<br/>(Python objects)"]
        PY_Events["Event Objects<br/>(Python objects)"]
        PY_Nodes["Node Graph<br/>(Python objects)"]
        PY_Result["Result Objects<br/>(Python dicts/lists)"]
        
        PY_Input --> PY_Tokens
        PY_Tokens --> PY_Events
        PY_Events --> PY_Nodes
        PY_Nodes --> PY_Result
        
        PY_Note["All intermediate objects<br/>on Python heap"]
    end
    
    subgraph Rusty_Mem["RustyAML Memory Usage"]
        R_Input["Input String<br/>(Python → Rust)"]
        R_Parse["serde_yaml Value<br/>(Rust heap)"]
        R_Result["Result Objects<br/>(Python dicts/lists)"]
        
        R_Input --> R_Parse
        R_Parse --> R_Result
        
        R_Note["Only result on Python heap<br/>Intermediates in Rust (faster alloc)"]
    end
    
    style PyYAML_Mem fill:#ffd43b,color:#000
    style Rusty_Mem fill:#dea584,color:#000
```

### Performance Comparison

```mermaid
xychart-beta
    title "Parse Time by YAML Size (lower is better)"
    x-axis ["1 key", "50 keys", "200 keys", "500 keys", "2000 keys", "10000 keys"]
    y-axis "Time (μs)" 0 --> 50000
    bar [15, 150, 500, 1500, 5000, 25000]
    bar [5, 40, 120, 350, 1200, 6000]
```

```mermaid
pie showData
    title "Where Time is Spent - PyYAML"
    "Scanning/Tokenizing" : 25
    "Parsing" : 30
    "Node Construction" : 20
    "Python Object Creation" : 25
```

```mermaid
pie showData
    title "Where Time is Spent - RustyAML"
    "Rust Parsing (serde_yaml)" : 35
    "Safety Checks" : 10
    "Python Object Creation" : 45
    "PyO3 Bridge Overhead" : 10
```

---

## Component Diagrams

### RustyAML Module Structure

```mermaid
classDiagram
    class rustyaml {
        +safe_load(yaml: str) → Any
        +safe_load_all(yaml: str) → List
        +unsafe_load(yaml: str) → Any
        +safe_load_many(yamls: List[str]) → List
        +safe_load_file(path: Path) → Any
        +load_directory(path: Path) → Dict
    }
    
    class lib_rs {
        <<PyO3 Module>>
        +rustyaml_module(m: PyModule)
        -parse_yaml(py: Python, yaml: str) → PyObject
        -parse_yaml_all(py: Python, yaml: str) → PyList
        -parse_yaml_many(py: Python, yamls: Vec) → PyList
    }
    
    class parser_rs {
        +parse_safe(yaml: &str) → Result~Value~
        +parse_unsafe(yaml: &str) → Result~Value~
        +parse_all(yaml: &str) → Result~Vec~Value~~
        +parse_with_context(yaml: &str) → Result~Value~
    }
    
    class types_rs {
        +yaml_to_python(py: Python, value: Value) → PyResult~PyObject~
        -convert_mapping(py: Python, map: Mapping) → PyDict
        -convert_sequence(py: Python, seq: Sequence) → PyList
        -convert_scalar(py: Python, value: Value) → PyObject
    }
    
    class safe_rs {
        +check_safety(value: &Value) → Result~()~
        +quick_safety_check(yaml: &str) → Result~()~
        -is_dangerous_tag(tag: &str) → bool
        -UNSAFE_PATTERNS: [&str]
    }
    
    class batch_rs {
        +safe_load_many(yamls: Vec~String~) → Vec~Value~
        +load_directory(path: &Path) → HashMap~String, Value~
        -parse_parallel(yamls: &[String]) → Vec~Result~Value~~
    }
    
    class error_rs {
        <<enum>> YAMLError
        +ParseError
        +SafetyError
        +IOError
        +to_py_err() → PyErr
    }
    
    rustyaml --> lib_rs : FFI calls
    lib_rs --> parser_rs : uses
    lib_rs --> types_rs : uses
    lib_rs --> batch_rs : uses
    parser_rs --> safe_rs : uses
    batch_rs --> parser_rs : uses
    parser_rs --> error_rs : returns
    safe_rs --> error_rs : returns
```

### Data Flow Through Components

```mermaid
flowchart LR
    subgraph Python["Python Layer"]
        Input["YAML String"]
        Output["Python Objects"]
    end
    
    subgraph FFI["PyO3 FFI Layer"]
        FromPy["FromPyObject"]
        ToPy["IntoPy"]
    end
    
    subgraph Rust["Rust Core"]
        subgraph Parsing["Parsing"]
            SerdeYAML["serde_yaml::from_str()"]
            Value["serde_yaml::Value"]
        end
        
        subgraph Safety["Safety"]
            QuickCheck["quick_safety_check()"]
            DeepCheck["check_safety()"]
        end
        
        subgraph Convert["Conversion"]
            YamlToPy["yaml_to_python()"]
        end
    end
    
    Input --> FromPy
    FromPy --> QuickCheck
    QuickCheck --> SerdeYAML
    SerdeYAML --> Value
    Value --> DeepCheck
    DeepCheck --> YamlToPy
    YamlToPy --> ToPy
    ToPy --> Output
    
    style Python fill:#3776ab,color:#fff
    style FFI fill:#f9d71c,color:#000
    style Rust fill:#dea584,color:#000
```

---

## Error Handling Flow

```mermaid
flowchart TD
    Input["YAML Input"] --> Parse["Attempt Parse"]
    
    Parse --> SyntaxCheck{"Syntax Valid?"}
    SyntaxCheck -->|"No"| SyntaxError["ParseError<br/>with line/column info"]
    
    SyntaxCheck -->|"Yes"| SafetyCheck{"Safety Check"}
    SafetyCheck -->|"Dangerous tags"| SafetyError["SafetyError<br/>with tag location"]
    
    SafetyCheck -->|"Safe"| Convert["Convert to Python"]
    Convert --> TypeCheck{"Type Conversion OK?"}
    
    TypeCheck -->|"No"| ConvError["ConversionError"]
    TypeCheck -->|"Yes"| Success["✅ Return Result"]
    
    SyntaxError --> PyError["Python ValueError"]
    SafetyError --> PyError
    ConvError --> PyError
    
    PyError --> UserCode["User's try/except"]
    
    style SyntaxError fill:#ff6b6b,color:#fff
    style SafetyError fill:#ff6b6b,color:#fff
    style ConvError fill:#ff6b6b,color:#fff
    style Success fill:#51cf66,color:#fff
```

---

## Summary: Key Differences

```mermaid
mindmap
    root((RustyAML vs PyYAML))
        Performance
            PyYAML: Pure Python parsing
            RustyAML: Native Rust parsing
            Result: 2-10x faster
        
        Safety
            PyYAML: Single-phase check
            RustyAML: Two-phase check
            ::icon(fa fa-shield)
        
        Parallelism
            PyYAML: GIL-bound sequential
            RustyAML: GIL-free parallel
            ::icon(fa fa-bolt)
        
        Memory
            PyYAML: Python heap intermediates
            RustyAML: Rust heap intermediates
            ::icon(fa fa-memory)
        
        API
            Compatible drop-in replacement
            ::icon(fa fa-check)
```

---

## Viewing These Diagrams

These diagrams are written in [Mermaid](https://mermaid.js.org/) syntax. To view them:

1. **GitHub**: GitHub automatically renders Mermaid in markdown files
2. **VS Code**: Install the "Markdown Preview Mermaid Support" extension
3. **Online**: Paste into [Mermaid Live Editor](https://mermaid.live/)
4. **Documentation**: Most modern doc tools (MkDocs, Docusaurus) support Mermaid

---

*Generated for RustyAML v0.1.0*
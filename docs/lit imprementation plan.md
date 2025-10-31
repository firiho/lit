# Git Implementation Plan - "Lit" Version Control System

## Project Overview
A simplified Git implementation in Python using Object-Oriented Programming principles, supporting core version control features including distributed operations, hashing, commits, branches, merging, and remote operations.

---

## Table of Contents
1. [Core Architecture](#core-architecture)
2. [Data Structures](#data-structures)
3. [Core Components](#core-components)
4. [Implementation Phases](#implementation-phases)
5. [File Structure](#file-structure)
6. [Detailed Implementation Steps](#detailed-implementation-steps)

---

## Core Architecture

### Design Principles
- **Object-Oriented Design**: Clean separation of concerns with dedicated classes
- **Content-Addressable Storage**: SHA-1 hashing like Git for object identification
- **Immutable Objects**: All stored objects are immutable
- **CLI-First**: Command-line interface as primary interaction method
- **Distributed**: Full support for remote repositories and collaboration

### Key Concepts
```
Working Directory → Staging Area (Index) → Repository (.lit)
```

---

## Data Structures

### 1. Git Objects
All objects stored in `.lit/objects/` directory, identified by SHA-1 hash.

#### Blob Object
- Represents file content
- Stores raw file data
- Identified by content hash

#### Tree Object
- Represents directory structure
- Contains references to blobs and other trees
- Stores file permissions and names

#### Commit Object
- Represents a snapshot in time
- Contains:
  - Tree hash (root directory snapshot)
  - Parent commit hash(es)
  - Author information
  - Committer information
  - Timestamp
  - Commit message

#### Tag Object (Optional)
- Named reference to a specific commit
- Can be lightweight or annotated

### 2. References
- **Branches**: Files in `.lit/refs/heads/` pointing to commit hashes
- **Tags**: Files in `.lit/refs/tags/` pointing to commit hashes
- **HEAD**: Special reference pointing to current branch or commit
- **Remote References**: Files in `.lit/refs/remotes/` tracking remote branches

### 3. Index (Staging Area)
- Binary file storing staged changes
- Maps file paths to blob hashes
- Includes file metadata (permissions, timestamps)

---

## Core Components

### 1. Object Store (`objects.py`)
```python
class GitObject:
    - Base class for all Git objects
    - Serialization/deserialization
    - Hash computation
    
class Blob(GitObject):
    - File content storage
    
class Tree(GitObject):
    - Directory structure
    - Tree entries (mode, type, hash, name)
    
class Commit(GitObject):
    - Snapshot with metadata
    - Parent tracking
```

### 2. Repository (`repository.py`)
```python
class Repository:
    - Initialize repository (.lit directory structure)
    - Read/write objects
    - Manage references
    - Handle configuration
```

### 3. Index Manager (`index.py`)
```python
class Index:
    - Stage files
    - Unstage files
    - Read/write index file
    - Compare working directory vs index vs HEAD
```

### 4. Reference Manager (`refs.py`)
```python
class RefManager:
    - Create/update/delete branches
    - Resolve references (HEAD, branch names)
    - Manage symbolic references
```

### 5. Diff Engine (`diff.py`)
```python
class DiffEngine:
    - Compare blobs
    - Compare trees
    - Generate unified diff format
    - Handle binary files
```

### 6. Merge Engine (`merge.py`)
```python
class MergeEngine:
    - Three-way merge algorithm
    - Conflict detection
    - Fast-forward merge
    - Merge commit creation
```

### 7. Remote Manager (`remote.py`)
```python
class Remote:
    - Add/remove remotes
    - Fetch objects from remote
    - Push objects to remote
    - Handle remote references
```

### 8. Network Protocol (`network.py`)
```python
class NetworkProtocol:
    - Smart HTTP protocol
    - Pack/unpack objects
    - Negotiate capabilities
    - Transfer objects efficiently
```

### 9. CLI Interface (`cli.py`)
```python
class CLI:
    - Command parsing
    - User-friendly output
    - Error handling
    - Help system
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Basic repository structure and object storage

1. **Setup Project Structure**
   - Create directory layout
   - Setup virtual environment
   - Install dependencies (minimal)

2. **Implement Object Store**
   - `GitObject` base class
   - SHA-1 hashing utility
   - Object serialization/deserialization
   - `Blob` class implementation
   - Object reading/writing to filesystem

3. **Repository Initialization**
   - `lit init` command
   - Create `.lit` directory structure
   - Initialize HEAD reference
   - Create initial configuration

4. **Basic Testing**
   - Unit tests for hashing
   - Unit tests for blob storage
   - Repository initialization tests

**Deliverables**:
- Working `lit init`
- Blob objects can be created and stored
- Unit test suite

---

### Phase 2: Staging and Committing (Week 3-4)
**Goal**: Stage files and create commits

1. **Implement Tree Objects**
   - `Tree` class
   - Tree entry structure
   - Tree building from directory
   - Tree serialization

2. **Implement Commit Objects**
   - `Commit` class
   - Author/committer info
   - Timestamp handling
   - Parent commit tracking

3. **Index Implementation**
   - `Index` class
   - Stage files (`lit add`)
   - Read/write index file
   - Index file format (binary)

4. **Commit Creation**
   - `lit commit` command
   - Build tree from index
   - Create commit object
   - Update branch reference
   - Update HEAD

5. **Status Command**
   - `lit status`
   - Compare working dir vs index vs HEAD
   - Show staged/unstaged/untracked files

**Deliverables**:
- Working `lit add`
- Working `lit commit`
- Working `lit status`
- Commit history stored correctly

---

### Phase 3: History and Branches (Week 5-6)
**Goal**: Navigate history and manage branches

1. **Log Command**
   - `lit log`
   - Walk commit history
   - Format commit information
   - Graph visualization (ASCII)

2. **Branch Management**
   - `lit branch` (list/create/delete)
   - `lit checkout` (switch branches)
   - `lit switch` (modern alternative)
   - Branch creation from commits

3. **Reference Management**
   - `RefManager` class
   - Resolve references
   - Symbolic references (HEAD)
   - Detached HEAD state

4. **Show Command**
   - `lit show` (commit details)
   - Display diff for commit

**Deliverables**:
- Working `lit log`
- Working `lit branch`
- Working `lit checkout`
- Branch management functional

---

### Phase 4: Diffing (Week 7)
**Goal**: Compare changes

1. **Diff Engine**
   - `DiffEngine` class
   - Blob diffing (Myers algorithm or similar)
   - Tree diffing (recursive comparison)
   - Unified diff format

2. **Diff Command**
   - `lit diff` (working dir vs index)
   - `lit diff --staged` (index vs HEAD)
   - `lit diff <commit>` (working dir vs commit)
   - `lit diff <commit1> <commit2>`

3. **Patch Generation**
   - Generate patch files
   - Apply patches (optional)

**Deliverables**:
- Working `lit diff`
- Accurate change detection
- Readable diff output

---

### Phase 5: Merging (Week 8-9)
**Goal**: Merge branches and handle conflicts

1. **Merge Algorithm**
   - `MergeEngine` class
   - Find merge base (common ancestor)
   - Three-way merge
   - Fast-forward detection

2. **Conflict Handling**
   - Detect conflicts
   - Generate conflict markers
   - Track conflicted files
   - Conflict resolution workflow

3. **Merge Command**
   - `lit merge <branch>`
   - Fast-forward merge
   - Merge commit creation
   - Abort merge

**Deliverables**:
- Working `lit merge`
- Conflict detection and markers

---

### Phase 6: Remote Operations (Week 10-12)
**Goal**: Distributed functionality

1. **Remote Management**
   - `Remote` class
   - `lit remote add/remove/list`
   - Store remote configuration
   - Remote URL parsing

2. **Clone Command**
   - `lit clone <url>`
   - Create new repository
   - Fetch all objects
   - Setup remote tracking
   - Checkout default branch

3. **Pull Command**
   - `lit pull`
   - Fetch + merge
   - Handle conflicts

4. **Push Command**
   - `lit push`
   - Check fast-forward
   - Upload missing objects
   - Update remote references
   - Handle rejection

**Deliverables**:
- Working `lit remote`
- Working `lit clone`
- Working `lit pull`
- Working `lit push`

---

### Phase 7: Advanced Features (Week 13-14)
**Goal**: Additional useful features

2. **Fetch Command**
   - `lit fetch`
   - Connect to remote
   - Discover remote references
   - Download missing objects
   - Update remote-tracking branches

3. **Network Protocol**
   - Simple HTTP-based protocol
   - Pack file format (efficiency)
   - Object compression
   - Capability negotiation

4. **Stash**
   - `lit stash` (save/list/apply/pop)
   - Store working directory changes
   - Apply stashed changes

5. **Cherry-pick**
   - `lit cherry-pick <commit>`
   - Apply specific commit

6. **Rebase** (Basic)
   - `lit rebase <branch>`
   - Replay commits

7. **Reset Command**
   - `lit reset` (soft/mixed/hard)
   - Move HEAD and branch
   - Update index and working directory

8. **Tags**
   - `lit tag` (lightweight/annotated)
   - Tag management

9. **Ignore Files**
   - `.litignore` support
   - Pattern matching
   - Global ignore

**Deliverables**:
- Working `lit remote`
- Working `lit fetch`
- Working `lit stash`
- Working `lit cherry-pick`
- Working `lit rebase`
- Working `lit reset`
- Working `lit tag`
- Working `.litignore`

---

### Phase 8: Polish and Optimization (Week 15-16)
**Goal**: Production-ready system

1. **Performance Optimization**
   - Pack files for efficiency
   - Index caching
   - Object caching
   - Lazy loading

2. **Error Handling**
   - Comprehensive error messages
   - Validation
   - Recovery mechanisms

3. **Documentation**
   - User manual
   - API documentation
   - Examples

4. **Testing**
   - Integration tests
   - End-to-end tests
   - Performance tests
   - Edge case coverage

5. **CLI Enhancements**
   - Colors and formatting
   - Progress indicators
   - Autocomplete support

**Deliverables**:
- Optimized performance
- Complete documentation
- Comprehensive test suite
- Polished user experience

---

## File Structure

```
lit/
├── .git/                      # Regular git for the project itself
├── .gitignore
├── README.md
├── GIT_IMPLEMENTATION_PLAN.md # This file
├── requirements.txt
├── setup.py
├── pyproject.toml
│
├── lit/                       # Main package
│   ├── __init__.py
│   ├── __main__.py           # Entry point for CLI
│   │
│   ├── core/                 # Core functionality
│   │   ├── __init__.py
│   │   ├── objects.py        # GitObject, Blob, Tree, Commit
│   │   ├── repository.py     # Repository class
│   │   ├── index.py          # Index/staging area
│   │   ├── refs.py           # Reference management
│   │   ├── hash.py           # Hashing utilities
│   │   └── config.py         # Configuration management
│   │
│   ├── operations/           # High-level operations
│   │   ├── __init__.py
│   │   ├── diff.py           # Diff engine
│   │   ├── merge.py          # Merge engine
│   │   ├── checkout.py       # Checkout logic
│   │   ├── status.py         # Status computation
│   │   └── log.py            # History traversal
│   │
│   ├── remote/               # Remote operations
│   │   ├── __init__.py
│   │   ├── remote.py         # Remote management
│   │   ├── fetch.py          # Fetch logic
│   │   ├── push.py           # Push logic
│   │   ├── clone.py          # Clone logic
│   │   ├── protocol.py       # Network protocol
│   │   └── pack.py           # Pack file handling
│   │
│   ├── cli/                  # CLI interface
│   │   ├── __init__.py
│   │   ├── main.py           # Main CLI entry
│   │   ├── commands/         # Command implementations
│   │   │   ├── __init__.py
│   │   │   ├── init.py
│   │   │   ├── add.py
│   │   │   ├── commit.py
│   │   │   ├── status.py
│   │   │   ├── log.py
│   │   │   ├── branch.py
│   │   │   ├── checkout.py
│   │   │   ├── diff.py
│   │   │   ├── merge.py
│   │   │   ├── remote.py
│   │   │   ├── fetch.py
│   │   │   ├── pull.py
│   │   │   ├── push.py
│   │   │   ├── clone.py
│   │   │   ├── stash.py
│   │   │   ├── tag.py
│   │   │   └── reset.py
│   │   ├── parser.py         # Argument parsing
│   │   └── output.py         # Formatted output
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── fs.py             # Filesystem utilities
│       ├── path.py           # Path manipulation
│       ├── ignore.py         # .litignore handling
│       └── compression.py    # Compression utilities
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_objects.py
│   ├── test_repository.py
│   ├── test_index.py
│   ├── test_diff.py
│   ├── test_merge.py
│   ├── test_remote.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_basic_workflow.py
│   │   ├── test_branching.py
│   │   ├── test_merging.py
│   │   └── test_remote_workflow.py
│   └── fixtures/             # Test fixtures
│
└── docs/                     # Documentation
    ├── architecture.md
    ├── user_guide.md
    ├── api_reference.md
    └── examples/
```

---

## Detailed Implementation Steps

### Step 1: Project Setup

#### 1.1 Create Directory Structure
```bash
mkdir -p lit/core lit/operations lit/remote lit/cli/commands lit/utils tests/integration docs
touch lit/__init__.py lit/__main__.py
touch lit/core/__init__.py lit/operations/__init__.py
touch lit/remote/__init__.py lit/cli/__init__.py lit/utils/__init__.py
```

#### 1.2 Create setup.py
```python
from setuptools import setup, find_packages

setup(
    name='lit-vcs',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'lit=lit.cli.main:main',
        ],
    },
    install_requires=[
        'click>=8.0.0',      # CLI framework
        'colorama>=0.4.0',   # Cross-platform colored terminal output
        'requests>=2.28.0',  # HTTP for remote operations
    ],
    python_requires='>=3.8',
)
```

#### 1.3 Create requirements.txt
```
click>=8.0.0
colorama>=0.4.0
requests>=2.28.0
pytest>=7.0.0
pytest-cov>=3.0.0
```

---

### Step 2: Core Object Implementation

#### 2.1 Hash Utilities (`lit/core/hash.py`)
```python
import hashlib
from typing import bytes

def hash_object(data: bytes) -> str:
    """Compute SHA-1 hash of data."""
    return hashlib.sha1(data).hexdigest()

def hash_file(filepath: str) -> str:
    """Compute SHA-1 hash of file."""
    with open(filepath, 'rb') as f:
        return hash_object(f.read())
```

#### 2.2 Base GitObject (`lit/core/objects.py`)
```python
from abc import ABC, abstractmethod
from typing import bytes
from .hash import hash_object

class GitObject(ABC):
    """Base class for all Git objects."""
    
    def __init__(self):
        self._hash = None
    
    @abstractmethod
    def serialize(self) -> bytes:
        """Serialize object to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes):
        """Deserialize object from bytes."""
        pass
    
    @property
    def type(self) -> str:
        """Return object type."""
        return self.__class__.__name__.lower()
    
    def compute_hash(self) -> str:
        """Compute and cache object hash."""
        if self._hash is None:
            data = self.serialize()
            header = f"{self.type} {len(data)}\0".encode()
            self._hash = hash_object(header + data)
        return self._hash
    
    @property
    def hash(self) -> str:
        """Get object hash."""
        return self.compute_hash()
```

#### 2.3 Blob Object
```python
class Blob(GitObject):
    """Represents file content."""
    
    def __init__(self, data: bytes = None):
        super().__init__()
        self.data = data or b''
    
    def serialize(self) -> bytes:
        return self.data
    
    def deserialize(self, data: bytes):
        self.data = data
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Blob':
        """Create blob from file."""
        with open(filepath, 'rb') as f:
            return cls(f.read())
```

#### 2.4 Tree Object
```python
from dataclasses import dataclass
from typing import List

@dataclass
class TreeEntry:
    mode: str      # File mode (e.g., '100644', '040000')
    type: str      # 'blob' or 'tree'
    hash: str      # Object hash
    name: str      # Filename or directory name

class Tree(GitObject):
    """Represents directory structure."""
    
    def __init__(self, entries: List[TreeEntry] = None):
        super().__init__()
        self.entries = entries or []
    
    def add_entry(self, mode: str, type: str, hash: str, name: str):
        self.entries.append(TreeEntry(mode, type, hash, name))
    
    def serialize(self) -> bytes:
        """
        Format: <mode> <type> <hash> <name>\n
        Entries are sorted by name.
        """
        self.entries.sort(key=lambda e: e.name)
        lines = []
        for entry in self.entries:
            line = f"{entry.mode} {entry.type} {entry.hash} {entry.name}"
            lines.append(line)
        return '\n'.join(lines).encode()
    
    def deserialize(self, data: bytes):
        self.entries = []
        for line in data.decode().strip().split('\n'):
            if line:
                mode, type, hash, name = line.split(' ', 3)
                self.entries.append(TreeEntry(mode, type, hash, name))
```

#### 2.5 Commit Object
```python
from datetime import datetime
from typing import List, Optional

class Commit(GitObject):
    """Represents a commit."""
    
    def __init__(
        self,
        tree: str,
        parents: List[str] = None,
        author: str = '',
        committer: str = '',
        timestamp: datetime = None,
        message: str = ''
    ):
        super().__init__()
        self.tree = tree
        self.parents = parents or []
        self.author = author
        self.committer = committer
        self.timestamp = timestamp or datetime.now()
        self.message = message
    
    def serialize(self) -> bytes:
        lines = [f"tree {self.tree}"]
        
        for parent in self.parents:
            lines.append(f"parent {parent}")
        
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"author {self.author} {timestamp_str}")
        lines.append(f"committer {self.committer} {timestamp_str}")
        lines.append("")  # Blank line
        lines.append(self.message)
        
        return '\n'.join(lines).encode()
    
    def deserialize(self, data: bytes):
        lines = data.decode().split('\n')
        i = 0
        
        # Parse header
        while i < len(lines) and lines[i]:
            if lines[i].startswith('tree '):
                self.tree = lines[i].split(' ', 1)[1]
            elif lines[i].startswith('parent '):
                self.parents.append(lines[i].split(' ', 1)[1])
            elif lines[i].startswith('author '):
                parts = lines[i].split(' ', 1)[1]
                self.author = parts.rsplit(' ', 2)[0]
            elif lines[i].startswith('committer '):
                parts = lines[i].split(' ', 1)[1]
                self.committer = parts.rsplit(' ', 2)[0]
            i += 1
        
        # Skip blank line
        i += 1
        
        # Rest is message
        self.message = '\n'.join(lines[i:])
```

---

### Step 3: Repository Implementation

#### 3.1 Repository Class (`lit/core/repository.py`)
```python
import os
import zlib
from pathlib import Path
from typing import Optional
from .objects import GitObject, Blob, Tree, Commit

class Repository:
    """Represents a Lit repository."""
    
    def __init__(self, path: str = '.'):
        self.work_tree = Path(path).resolve()
        self.lit_dir = self.work_tree / '.lit'
        self.objects_dir = self.lit_dir / 'objects'
        self.refs_dir = self.lit_dir / 'refs'
        self.heads_dir = self.refs_dir / 'heads'
        self.tags_dir = self.refs_dir / 'tags'
        self.remotes_dir = self.refs_dir / 'remotes'
        self.head_file = self.lit_dir / 'HEAD'
        self.index_file = self.lit_dir / 'index'
        self.config_file = self.lit_dir / 'config'
    
    def init(self):
        """Initialize a new repository."""
        if self.lit_dir.exists():
            raise Exception("Repository already exists")
        
        # Create directory structure
        self.lit_dir.mkdir()
        self.objects_dir.mkdir()
        self.refs_dir.mkdir()
        self.heads_dir.mkdir()
        self.tags_dir.mkdir()
        self.remotes_dir.mkdir()
        
        # Initialize HEAD
        self.head_file.write_text('ref: refs/heads/main\n')
        
        # Initialize config
        self.config_file.write_text('[core]\n\trepositoryformatversion = 0\n')
        
        return self
    
    @classmethod
    def find_repository(cls, path: str = '.') -> Optional['Repository']:
        """Find repository by searching up the directory tree."""
        current = Path(path).resolve()
        
        while True:
            lit_dir = current / '.lit'
            if lit_dir.is_dir():
                return cls(str(current))
            
            if current == current.parent:
                return None
            
            current = current.parent
    
    def object_path(self, hash: str) -> Path:
        """Get path to object file."""
        return self.objects_dir / hash[:2] / hash[2:]
    
    def write_object(self, obj: GitObject) -> str:
        """Write object to repository."""
        hash = obj.hash
        path = self.object_path(hash)
        
        if path.exists():
            return hash  # Object already exists
        
        # Prepare data
        data = obj.serialize()
        header = f"{obj.type} {len(data)}\0".encode()
        content = header + data
        
        # Compress and write
        compressed = zlib.compress(content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(compressed)
        
        return hash
    
    def read_object(self, hash: str) -> GitObject:
        """Read object from repository."""
        path = self.object_path(hash)
        
        if not path.exists():
            raise Exception(f"Object {hash} not found")
        
        # Read and decompress
        compressed = path.read_bytes()
        content = zlib.decompress(compressed)
        
        # Parse header
        null_idx = content.index(b'\0')
        header = content[:null_idx].decode()
        data = content[null_idx + 1:]
        
        obj_type, size = header.split(' ')
        
        # Create appropriate object
        if obj_type == 'blob':
            obj = Blob()
        elif obj_type == 'tree':
            obj = Tree()
        elif obj_type == 'commit':
            obj = Commit('', [])
        else:
            raise Exception(f"Unknown object type: {obj_type}")
        
        obj.deserialize(data)
        return obj
```

---

### Step 4: Index Implementation

#### 4.1 Index Class (`lit/core/index.py`)
```python
import os
import struct
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from .hash import hash_file

@dataclass
class IndexEntry:
    """Represents a file in the index."""
    mode: int
    hash: str
    path: str
    size: int
    mtime: float

class Index:
    """Staging area for commits."""
    
    def __init__(self, repo):
        self.repo = repo
        self.entries: Dict[str, IndexEntry] = {}
        self._load()
    
    def _load(self):
        """Load index from file."""
        if not self.repo.index_file.exists():
            return
        
        with open(self.repo.index_file, 'rb') as f:
            # Simple format: JSON for now (can be optimized later)
            import json
            try:
                data = json.loads(f.read().decode())
                for path, entry_data in data.items():
                    self.entries[path] = IndexEntry(**entry_data)
            except:
                pass
    
    def _save(self):
        """Save index to file."""
        import json
        data = {
            path: {
                'mode': entry.mode,
                'hash': entry.hash,
                'path': entry.path,
                'size': entry.size,
                'mtime': entry.mtime
            }
            for path, entry in self.entries.items()
        }
        
        with open(self.repo.index_file, 'wb') as f:
            f.write(json.dumps(data, indent=2).encode())
    
    def add(self, filepath: str):
        """Add file to index."""
        full_path = self.repo.work_tree / filepath
        
        if not full_path.exists():
            raise Exception(f"File not found: {filepath}")
        
        # Get file info
        stat = full_path.stat()
        mode = stat.st_mode
        size = stat.st_size
        mtime = stat.st_mtime
        
        # Hash file content
        hash = hash_file(str(full_path))
        
        # Create blob and store
        from .objects import Blob
        blob = Blob.from_file(str(full_path))
        self.repo.write_object(blob)
        
        # Add to index
        self.entries[filepath] = IndexEntry(
            mode=mode,
            hash=hash,
            path=filepath,
            size=size,
            mtime=mtime
        )
        
        self._save()
    
    def remove(self, filepath: str):
        """Remove file from index."""
        if filepath in self.entries:
            del self.entries[filepath]
            self._save()
    
    def get_entry(self, filepath: str) -> Optional[IndexEntry]:
        """Get index entry for file."""
        return self.entries.get(filepath)
    
    def clear(self):
        """Clear all entries."""
        self.entries.clear()
        self._save()
```

---

### Step 5: Reference Management

#### 5.1 RefManager Class (`lit/core/refs.py`)
```python
from pathlib import Path
from typing import Optional

class RefManager:
    """Manage branches and references."""
    
    def __init__(self, repo):
        self.repo = repo
    
    def resolve_ref(self, ref: str) -> Optional[str]:
        """Resolve reference to commit hash."""
        # Try direct hash
        if len(ref) == 40 and all(c in '0123456789abcdef' for c in ref):
            return ref
        
        # Try HEAD
        if ref == 'HEAD':
            return self.resolve_head()
        
        # Try branch
        branch_path = self.repo.heads_dir / ref
        if branch_path.exists():
            return branch_path.read_text().strip()
        
        # Try refs/heads/
        if not ref.startswith('refs/'):
            ref = f'refs/heads/{ref}'
        
        ref_path = self.repo.lit_dir / ref
        if ref_path.exists():
            return ref_path.read_text().strip()
        
        return None
    
    def resolve_head(self) -> Optional[str]:
        """Resolve HEAD to commit hash."""
        head_content = self.repo.head_file.read_text().strip()
        
        # Symbolic reference
        if head_content.startswith('ref: '):
            ref = head_content[5:]
            ref_path = self.repo.lit_dir / ref
            if ref_path.exists():
                return ref_path.read_text().strip()
            return None
        
        # Direct hash (detached HEAD)
        return head_content
    
    def get_current_branch(self) -> Optional[str]:
        """Get name of current branch."""
        head_content = self.repo.head_file.read_text().strip()
        
        if head_content.startswith('ref: refs/heads/'):
            return head_content[16:]
        
        return None  # Detached HEAD
    
    def create_branch(self, name: str, commit_hash: str):
        """Create a new branch."""
        branch_path = self.repo.heads_dir / name
        if branch_path.exists():
            raise Exception(f"Branch {name} already exists")
        
        branch_path.write_text(f"{commit_hash}\n")
    
    def delete_branch(self, name: str):
        """Delete a branch."""
        branch_path = self.repo.heads_dir / name
        if not branch_path.exists():
            raise Exception(f"Branch {name} not found")
        
        current_branch = self.get_current_branch()
        if current_branch == name:
            raise Exception(f"Cannot delete current branch")
        
        branch_path.unlink()
    
    def list_branches(self):
        """List all branches."""
        return [f.name for f in self.repo.heads_dir.iterdir()]
    
    def update_ref(self, ref: str, commit_hash: str):
        """Update reference to point to commit."""
        if ref == 'HEAD':
            # Update current branch
            branch = self.get_current_branch()
            if branch:
                ref_path = self.repo.heads_dir / branch
                ref_path.write_text(f"{commit_hash}\n")
            else:
                # Detached HEAD
                self.repo.head_file.write_text(f"{commit_hash}\n")
        else:
            # Update specific branch
            if not ref.startswith('refs/'):
                ref = f'refs/heads/{ref}'
            ref_path = self.repo.lit_dir / ref
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(f"{commit_hash}\n")
    
    def set_head(self, target: str):
        """Set HEAD to branch or commit."""
        # Check if it's a branch
        branch_path = self.repo.heads_dir / target
        if branch_path.exists():
            self.repo.head_file.write_text(f"ref: refs/heads/{target}\n")
        else:
            # Assume it's a commit hash
            self.repo.head_file.write_text(f"{target}\n")
```

---

### Step 6: CLI Implementation

#### 6.1 Main CLI Entry (`lit/cli/main.py`)
```python
import click
from pathlib import Path

@click.group()
def cli():
    """Lit - A Git-like version control system."""
    pass

# Import commands
from .commands import (
    init, add, commit, status, log, branch, 
    checkout, diff, merge, remote, fetch, 
    pull, push, clone
)

# Register commands
cli.add_command(init.init_cmd)
cli.add_command(add.add_cmd)
cli.add_command(commit.commit_cmd)
cli.add_command(status.status_cmd)
cli.add_command(log.log_cmd)
cli.add_command(branch.branch_cmd)
cli.add_command(checkout.checkout_cmd)
cli.add_command(diff.diff_cmd)
cli.add_command(merge.merge_cmd)
cli.add_command(remote.remote_cmd)
cli.add_command(fetch.fetch_cmd)
cli.add_command(pull.pull_cmd)
cli.add_command(push.push_cmd)
cli.add_command(clone.clone_cmd)

def main():
    cli()

if __name__ == '__main__':
    main()
```

#### 6.2 Init Command (`lit/cli/commands/init.py`)
```python
import click
from lit.core.repository import Repository

@click.command('init')
@click.argument('path', default='.')
def init_cmd(path):
    """Initialize a new repository."""
    try:
        repo = Repository(path)
        repo.init()
        click.echo(f"Initialized empty Lit repository in {repo.lit_dir}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
```

#### 6.3 Add Command (`lit/cli/commands/add.py`)
```python
import click
from lit.core.repository import Repository
from lit.core.index import Index

@click.command('add')
@click.argument('files', nargs=-1, required=True)
def add_cmd(files):
    """Add files to the staging area."""
    repo = Repository.find_repository()
    if not repo:
        click.echo("Not a lit repository", err=True)
        raise click.Abort()
    
    index = Index(repo)
    
    for file in files:
        try:
            index.add(file)
            click.echo(f"Added {file}")
        except Exception as e:
            click.echo(f"Error adding {file}: {e}", err=True)
```

---

### Step 7: Building Tree from Index

#### 7.1 Tree Builder (`lit/operations/tree_builder.py`)
```python
from pathlib import Path
from typing import Dict
from lit.core.objects import Tree, TreeEntry
from lit.core.index import Index

class TreeBuilder:
    """Build tree objects from index."""
    
    def __init__(self, repo):
        self.repo = repo
    
    def build_tree_from_index(self, index: Index) -> str:
        """Build tree from current index state."""
        # Group entries by directory
        tree_data = {}
        
        for path, entry in index.entries.items():
            parts = Path(path).parts
            current = tree_data
            
            # Navigate/create tree structure
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file entry
            current[parts[-1]] = entry
        
        # Build trees recursively
        return self._build_tree_recursive(tree_data)
    
    def _build_tree_recursive(self, tree_data: Dict) -> str:
        """Recursively build tree objects."""
        tree = Tree()
        
        for name, item in sorted(tree_data.items()):
            if isinstance(item, dict):
                # Subdirectory - recurse
                subtree_hash = self._build_tree_recursive(item)
                tree.add_entry('040000', 'tree', subtree_hash, name)
            else:
                # File
                mode = '100644'  # Regular file
                if item.mode & 0o111:  # Executable
                    mode = '100755'
                tree.add_entry(mode, 'blob', item.hash, name)
        
        # Write tree object
        return self.repo.write_object(tree)
```

---

### Step 8: Commit Creation

#### 8.1 Commit Command (`lit/cli/commands/commit.py`)
```python
import click
from datetime import datetime
from lit.core.repository import Repository
from lit.core.index import Index
from lit.core.objects import Commit
from lit.core.refs import RefManager
from lit.operations.tree_builder import TreeBuilder

@click.command('commit')
@click.option('-m', '--message', required=True, help='Commit message')
def commit_cmd(message):
    """Create a new commit."""
    repo = Repository.find_repository()
    if not repo:
        click.echo("Not a lit repository", err=True)
        raise click.Abort()
    
    index = Index(repo)
    
    if not index.entries:
        click.echo("Nothing to commit", err=True)
        raise click.Abort()
    
    # Build tree from index
    builder = TreeBuilder(repo)
    tree_hash = builder.build_tree_from_index(index)
    
    # Get parent commit
    refs = RefManager(repo)
    parent_hash = refs.resolve_head()
    parents = [parent_hash] if parent_hash else []
    
    # Create commit
    # TODO: Get author from config
    author = "User <user@example.com>"
    
    commit = Commit(
        tree=tree_hash,
        parents=parents,
        author=author,
        committer=author,
        timestamp=datetime.now(),
        message=message
    )
    
    commit_hash = repo.write_object(commit)
    
    # Update HEAD
    refs.update_ref('HEAD', commit_hash)
    
    click.echo(f"[{refs.get_current_branch() or 'detached'} {commit_hash[:7]}] {message}")
```

---

## Testing Strategy

### Unit Tests
- Test each class in isolation
- Mock dependencies
- Test edge cases

### Integration Tests
- Test complete workflows
- Test inter-component communication
- Test error scenarios

### End-to-End Tests
- Test full user workflows
- Test distributed scenarios
- Test conflict resolution

### Performance Tests
- Large repository handling
- Many file handling
- Network efficiency

---

## Key Algorithms

### 1. Myers Diff Algorithm
For computing line-by-line diffs between files.

### 2. Three-Way Merge
For merging branches with a common ancestor.

### 3. Lowest Common Ancestor (LCA)
For finding merge base between commits.

### 4. Topological Sort
For git log with correct ordering.

### 5. Pack File Algorithm
For efficient object storage and transfer.

---

## Security Considerations

1. **Input Validation**: Validate all user inputs
2. **Path Traversal**: Prevent directory traversal attacks
3. **Hash Collisions**: Handle SHA-1 collisions gracefully
4. **Remote URLs**: Validate and sanitize remote URLs
5. **File Permissions**: Respect and preserve file permissions

---

## Performance Optimizations

1. **Object Caching**: Cache frequently accessed objects
2. **Index Caching**: Keep index in memory when possible
3. **Pack Files**: Group objects for efficient storage
4. **Lazy Loading**: Load objects only when needed
5. **Delta Compression**: Store object deltas for efficiency

---

## Extension Points

1. **Custom Merge Strategies**: Plugin architecture for merge algorithms
2. **Hooks**: Pre/post commit, pre/post push hooks
3. **Custom Diff Tools**: External diff tool integration
4. **Remote Protocols**: Additional transport protocols
5. **Storage Backends**: Alternative object storage

---

## Future Enhancements

1. **Git LFS Support**: Large file storage
2. **Submodules**: Repository nesting
3. **Worktrees**: Multiple working directories
4. **Bisect**: Binary search for bugs
5. **Reflog**: Reference change history
6. **Garbage Collection**: Remove unreachable objects
7. **Sparse Checkout**: Partial working directory
8. **Shallow Clone**: Limited history clone

---

## Development Workflow

### Phase 1-2 (Weeks 1-4)
Focus: Core functionality
- Daily commits
- Unit tests for each component
- Documentation as you go

### Phase 3-4 (Weeks 5-7)
Focus: Branch and diff features
- Integration tests
- User testing with basic workflows

### Phase 5-6 (Weeks 8-12)
Focus: Merge and remote operations
- End-to-end tests
- Network protocol testing

### Phase 7-8 (Weeks 13-16)
Focus: Advanced features and polish
- Performance testing
- Documentation finalization
- Beta testing

---

## Success Criteria

1. ✅ Can initialize a repository
2. ✅ Can stage and commit files
3. ✅ Can view commit history
4. ✅ Can create and switch branches
5. ✅ Can merge branches (fast-forward and 3-way)
6. ✅ Can handle merge conflicts
7. ✅ Can clone remote repositories
8. ✅ Can push and pull changes
9. ✅ Can handle binary files
10. ✅ Performance acceptable for typical use cases
11. ✅ Comprehensive test coverage (>80%)
12. ✅ Complete user documentation

---

## Resources and References

### Git Internals
- [Pro Git Book - Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain)
- Git source code

### Algorithms
- Myers diff algorithm paper
- Three-way merge algorithm
- Pack file format specification

### Python Libraries
- `click` - CLI framework
- `pytest` - Testing framework
- `zlib` - Compression
- `hashlib` - Hashing

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building a Git-like version control system in Python. By following the phased approach and focusing on core features first, you'll build a solid foundation that can be extended with advanced features.

The key to success is:
1. **Start simple** - Get basic functionality working first
2. **Test thoroughly** - Write tests as you develop
3. **Iterate** - Refine and optimize as you go
4. **Document** - Keep documentation up to date
5. **Use it** - Dog-food your own tool to find issues

Good luck with the implementation!
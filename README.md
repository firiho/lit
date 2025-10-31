# Lit - A Git-Like Version Control System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-187%20passed-brightgreen.svg)](tests/)

**Lit** is a functional implementation of Git's core version control features in Python, built with clean object-oriented design principles. It provides distributed version control capabilities including branching, merging, diffing, and remote repository operations.

## Features

### Core Version Control
- ✅ **Content-Addressable Storage** - SHA-1 based object database with zlib compression
- ✅ **Repository Management** - Initialize, configure, and manage `.lit` repositories
- ✅ **Staging Area** - Git-compatible index (DIRC format) for selective commits
- ✅ **Commit History** - Full DAG-based commit graph with parent tracking
- ✅ **Branch Operations** - Create, delete, switch, and list branches
- ✅ **Symbolic References** - HEAD support with detached HEAD mode

### Comparison & Merging
- ✅ **Diff Engine** - Unified diff format for files, trees, and commits
- ✅ **Three-Way Merge** - Automatic merge with common ancestor detection
- ✅ **Fast-Forward Detection** - Optimized merges when possible
- ✅ **Conflict Detection** - Identifies merge conflicts with conflict markers

### Distributed Operations
- ✅ **Clone** - Full repository cloning (local file:// protocol)
- ✅ **Remote Management** - Add, remove, and list remote repositories
- ✅ **Push** - Upload commits and objects to remote repositories
- ✅ **Pull** - Fetch and merge changes from remote repositories
- ✅ **Bare Repositories** - Server-side repositories without working tree

### Current Limitations
- ⏳ **Conflict Resolution** - Conflicts detected but auto-aborted (Phase 7)
- ⏳ **Network Protocols** - Only local file:// supported (HTTP/SSH planned)
- ⏳ **Advanced Commands** - fetch, stash, reset, rebase, tag (Phase 7-8)
- ⏳ **Ignore Files** - .litignore support not yet implemented

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager
- Virtual environment (recommended)

### From Source

```bash
# Clone the repository
git clone https://github.com/firiho/lit.git
cd lit

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
lit --version
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=lit --cov-report=html

# Run specific test suites
python -m pytest tests/unit/
python -m pytest tests/integration/
```

## Quick Start

```bash
# Configure user information
lit config user.name "Your Name"
lit config user.email "your.email@example.com"

# Initialize a new repository
lit init my-project
cd my-project

# Create and stage files
echo "# My Project" > README.md
lit add README.md
lit commit -m "Initial commit"

# View status and history
lit status
lit log
```

## Comprehensive Example: Team Collaboration Workflow

This example demonstrates Lit's distributed capabilities with a central bare repository and multiple developers.

### Setup: Create Central Repository

```bash
# Developer creates initial project
mkdir demo
cd demo
lit init
lit config user.name "Project Creator"
lit config user.email "creator@example.com"

# Create initial project structure
echo "# Demo Project" > README.md
echo "print('Hello, Lit!')" > app.py
lit add README.md app.py
lit commit -m "Initial project structure"

# Create bare repository (central server)
cd ..
lit clone --bare demo demo.lit
```

### Developer A: Clone and Add Features

```bash
# Clone from central repository
lit clone demo.lit devA
cd devA

# Configure developer identity
lit config user.name "Alice"
lit config user.email "alice@example.com"

# Create feature branch
lit branch feature-auth
lit checkout feature-auth

# Develop authentication feature
echo "def login(user, password):\n    return True" > auth.py
lit add auth.py
lit commit -m "Add authentication module"

# Add more functionality
echo "def logout(user):\n    return True" >> auth.py
lit add auth.py
lit commit -m "Add logout function"

# View commit history
lit log --oneline

# Push feature branch to central repository
lit push origin feature-auth

# Merge into main and push
lit checkout main
lit merge feature-auth
lit push origin main
```

### Developer B: Clone, Branch, and Collaborate

```bash
# Clone from central repository
cd ../
lit clone demo.lit devB
cd devB

# Configure developer identity  
lit config user.name "Bob"
lit config user.email "bob@example.com"

# Pull latest changes from Developer A
lit pull origin main

# Create feature branch for database
lit branch feature-database
lit checkout feature-database

# Develop database feature
echo "class Database:\n    def __init__(self):\n        self.data = {}" > database.py
lit add database.py
lit commit -m "Add database class"

# Check differences
lit diff main

# Integrate app with database
echo "from database import Database\ndb = Database()" >> app.py
lit add app.py
lit commit -m "Integrate database with app"

# View branch history
lit log --graph

# Push feature to central repo
lit push origin feature-database

# Merge into main
lit checkout main
lit merge feature-database
lit push origin main
```

### Developer A: Pull Updates and View Changes

```bash
cd ../devA

# Pull Developer B's changes
lit pull origin main

# View combined history
lit log --graph --all

# Check differences between branches
lit diff feature-auth main

# View specific commit details
lit show HEAD

# Check current repository status
lit status
```

### Key Operations Demonstrated

This workflow showcases:
- ✅ **Bare repository creation** with `clone --bare`
- ✅ **Multiple developers** with different identities
- ✅ **Branch-based development** with feature branches
- ✅ **Distributed collaboration** via push/pull
- ✅ **Merge operations** combining features
- ✅ **History tracking** with log and diff
- ✅ **Remote synchronization** with central repository

## Command Reference

### Repository Operations
| Command | Description |
|---------|-------------|
| `lit init [path]` | Initialize a new repository |
| `lit clone <url> [path]` | Clone a repository (add `--bare` for bare repo) |
| `lit config <key> [value]` | Get or set configuration options |
| `lit status` | Show working tree and staging status |

### Basic Workflow
| Command | Description |
|---------|-------------|
| `lit add <files...>` | Stage files for commit |
| `lit commit -m <message>` | Create a commit with staged changes |
| `lit log [--oneline] [--graph] [--all]` | Show commit history |
| `lit show <commit>` | Display commit details and diff |
| `lit diff [options]` | Show changes (working/staged/commits) |

### Branching & Merging
| Command | Description |
|---------|-------------|
| `lit branch [name]` | List, create, or delete branches |
| `lit branch -d <name>` | Delete a branch |
| `lit checkout [-b] <branch>` | Switch branches (or create with `-b`) |
| `lit switch <branch>` | Modern branch switching command |
| `lit merge <branch>` | Merge branch into current branch |
| `lit merge --abort` | Abort current merge operation |

### Remote Operations
| Command | Description |
|---------|-------------|
| `lit remote` | List remote repositories |
| `lit remote add <name> <url>` | Add a remote repository |
| `lit remote remove <name>` | Remove a remote |
| `lit push [remote] [branch]` | Push commits to remote |
| `lit pull [remote] [branch]` | Fetch and merge from remote |

### Advanced
| Command | Description |
|---------|-------------|
| `lit show-ref [--heads] [--tags]` | Display all references |
| `lit symbolic-ref <name> [ref]` | Read or modify symbolic references |
| `lit diff --staged` | Show staged changes |
| `lit log --graph` | Show commit graph (ASCII) |

## Architecture

### Project Structure
```
lit/
├── core/                   # Core VCS functionality
│   ├── objects.py         # Git objects (Blob, Tree, Commit)
│   ├── repository.py      # Repository management
│   ├── index.py           # Staging area implementation
│   ├── refs.py            # Reference management (branches, HEAD)
│   ├── diff.py            # Diff engine with unified format
│   ├── merge.py           # Merge algorithms and conflict detection
│   ├── remote.py          # Remote repository operations
│   └── hash.py            # SHA-1 hashing utilities
├── cli/                   # Command-line interface
│   ├── main.py            # CLI entry point and routing
│   ├── output.py          # Formatted output with colors
│   └── commands/          # Individual command implementations (17 commands)
└── tests/                 # Comprehensive test suite
    ├── unit/              # Unit tests (9 modules)
    └── integration/       # Integration tests (4 workflows)
```

### Technical Implementation
- **Object Model** - Immutable Blob, Tree, and Commit objects with content-addressable storage
- **Storage Format** - Git-compatible object format with zlib compression
- **Index Format** - Binary DIRC format compatible with Git
- **Diff Algorithm** - Line-based diffing with unified diff output
- **Merge Algorithm** - Three-way merge with lowest common ancestor (LCA) detection
- **References** - Symbolic and direct references with full HEAD support

## Development Status

| Phase | Description | Status | Completeness |
|-------|-------------|--------|--------------|
| **Phase 1** | Foundation & Object Storage | ✅ Complete | 100% |
| **Phase 2** | Staging & Committing | ✅ Complete | 100% |
| **Phase 3** | History & Branches | ✅ Complete | 100% |
| **Phase 4** | Diffing | ✅ Complete | 100% |
| **Phase 5** | Merging | ✅ Complete | 85% |
| **Phase 6** | Remote Operations | ✅ Complete | 70% |
| **Phase 7** | Advanced Features | ⏳ Planned | 0% |
| **Phase 8** | Polish & Optimization | ⏳ Planned | 0% |

**Overall Progress:** ~75% Complete (6/8 phases)

See [progress.md](progress.md) for detailed progress report.

## Testing

**Test Coverage:** 187 tests passing (40% code coverage)

```bash
# Run specific test categories
python -m pytest tests/unit/test_merge.py -v
python -m pytest tests/integration/ -v
python -m pytest -k conflict  # Run conflict-related tests

# Generate coverage report
python -m pytest --cov=lit --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Contributing

Contributions are welcome! This project is built as an educational implementation of Git internals.

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests before committing
make test

# Format code
make format

# Clean build artifacts
make clean
```

### Areas for Contribution
- 🔧 Phase 7 features (fetch, stash, reset, rebase, tags)
- 🌐 Network protocol implementation (HTTP/HTTPS)
- 🔀 Enhanced conflict resolution workflow
- 📚 Documentation improvements
- 🧪 Additional test coverage
- ⚡ Performance optimizations

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Author

**Flambeau Iriho**
- GitHub: [@firiho](https://github.com/firiho)
- Email: irihoflambeau@gmail.com

## Acknowledgments

Built as an educational project to deeply understand Git internals and version control system design. Inspired by:
- Git's elegant content-addressable storage model
- [Pro Git Book](https://git-scm.com/book/en/v2) by Scott Chacon and Ben Straub
- [Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain) documentation

## Further Reading

- [Implementation Plan](docs/lit%20imprementation%20plan.md) - Complete phase-by-phase development plan
- [Progress Report](progress.md) - Detailed progress and feature status
- [Architecture](docs/architecture.md) - System design and technical details

---

**Note:** Lit is a functional Git implementation suitable for learning and experimentation. For production use, please use [Git](https://git-scm.com/).

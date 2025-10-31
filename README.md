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

# Upgrade pip
pip install --upgrade pip

# Install lit package
pip install . # You might need updated pip version

# Install development dependencies
pip install -r requirements.txt

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

## Quick Example: Team Workflow

```bash
# Setup: Create central repo
mkdir project && cd project
lit init
create app.py
Write "Hello World" in app.py
lit add app.py
lit commit -m "Initial commit"
cd .. && lit clone --bare project server.lit

# DevA: Feature branch workflow
lit clone server.lit devA && cd devA
lit config set user.name "Dev A"
lit config set user.email "devA@example.com"
lit checkout -b feature-auth
Write login() in auth.py
lit add auth.py && lit commit -m "Add auth"
lit push origin feature-auth
lit checkout main && lit merge feature-auth
lit push origin main

# DevB: Parallel development
cd .. && lit clone server.lit devB && cd devB
lit pull origin main
lit checkout -b feature-db
Write Database class in db.py
lit add db.py && lit commit -m "Add database" --author "Dev B <devB@example.com>"
lit push origin feature-db && lit checkout main
lit merge feature-db && lit push origin main

# DevA: Sync changes
cd ../devA && lit pull origin main
lit log --graph --all
lit diff HEAD~2 HEAD
```

**Demonstrates:** Bare repos • Branching • Push/Pull • Merging • Distributed collaboration

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

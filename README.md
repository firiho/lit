# Lit - A Git-Like Version Control System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-358%20passed-brightgreen.svg)](tests/)

**Lit** is a complete implementation of Git's core version control features in Python, built with clean object-oriented design principles. It provides fully functional distributed version control capabilities including branching, merging, rebasing, stashing, cherry-picking, and remote repository operations.

## Features

### Core Version Control
- ✅ **Content-Addressable Storage** - SHA-1 based object database with zlib compression
- ✅ **Repository Management** - Initialize, configure, and manage `.lit` repositories
- ✅ **Staging Area** - Git-compatible index (DIRC format) for selective commits
- ✅ **Commit History** - Full DAG-based commit graph with parent tracking
- ✅ **Branch Operations** - Create, delete, switch, and list branches
- ✅ **Symbolic References** - HEAD support with detached HEAD mode
- ✅ **Tag Support** - Lightweight and annotated tags with messages

### Comparison & Merging
- ✅ **Diff Engine** - Unified diff format for files, trees, and commits
- ✅ **Three-Way Merge** - Automatic merge with common ancestor detection
- ✅ **Auto-Merge** - Automatic conflict resolution with configurable strategies
- ✅ **Fast-Forward Detection** - Optimized merges when possible
- ✅ **Conflict Detection** - Identifies merge conflicts with conflict markers
- ✅ **Cherry-Pick** - Apply specific commits to current branch
- ✅ **Rebase** - Reapply commits on top of another base tip

### Distributed Operations
- ✅ **Clone** - Full repository cloning (local file:// protocol)
- ✅ **Remote Management** - Add, remove, and list remote repositories
- ✅ **Fetch** - Download objects and refs from remote repositories
- ✅ **Push** - Upload commits and objects to remote repositories
- ✅ **Pull** - Fetch and merge changes from remote repositories
- ✅ **Bare Repositories** - Server-side repositories without working tree

### Advanced Features
- ✅ **Stash** - Save and restore uncommitted changes
- ✅ **Reset** - Reset HEAD to specified state (soft/mixed/hard modes)
- ✅ **Cherry-Pick** - Apply commits from other branches
- ✅ **Rebase** - Reapply commits with --continue/--abort support
- ✅ **Ignore Files** - .litignore support with glob patterns
- ✅ **Tree Inspection** - ls-tree, cat-file, count-objects commands

### Current Limitations
- ⏳ **Network Protocols** - Only local file:// supported (HTTP/SSH planned)
- ⏳ **Submodules** - Not yet implemented
- ⏳ **Worktrees** - Multiple working trees not supported

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

## Quick Example: Merge Conflict & Auto-Resolution

```bash
# ============================================================
# Setup: Create a clean workspace in tmp folder
# ============================================================
mkdir tmp && cd tmp

# Create and initialize the "origin" project repository
mkdir project && cd project
lit init
lit config set user.name "Project Owner"
lit config set user.email "owner@example.com"
echo "print('Hello')" > app.py
lit add app.py
lit commit -m "Initial commit"

# Create a bare "server" repository (simulates GitHub/remote)
cd ..
lit clone --bare project server.lit

# ============================================================
# DevA: Clone and create a feature branch
# ============================================================
lit clone server.lit devA && cd devA
lit config set user.name "Dev A"
lit config set user.email "devA@example.com"

# DevA modifies app.py on a feature branch
lit checkout -b feature-greeting
echo "print('Hello from DevA!')" > app.py
lit add app.py && lit commit -m "Update greeting - DevA version"
lit push origin feature-greeting

# ============================================================
# DevB: Clone and create a different feature branch
# ============================================================
cd ..
lit clone server.lit devB && cd devB
lit config set user.name "Dev B"
lit config set user.email "devB@example.com"

# DevB modifies the SAME line differently (conflict incoming!)
lit checkout -b feature-greeting-alt
echo "print('Hello from DevB!')" > app.py
lit add app.py && lit commit -m "Update greeting - DevB version"
lit push origin feature-greeting-alt

# ============================================================
# DevA: Merge their feature into main and push
# ============================================================
cd ../devA
lit checkout main
lit merge feature-greeting    # Fast-forward merge
lit push origin main

# ============================================================
# DevA: Try to merge DevB's changes - CONFLICT!
# ============================================================
lit fetch origin
lit merge origin/feature-greeting-alt
# Output: CONFLICT (content): Merge conflict in app.py

# Inspect the conflict markers
cat app.py
# <<<<<<< HEAD
# print('Hello from DevA!')
# =======
# print('Hello from DevB!')
# >>>>>>> origin/feature-greeting-alt

# ============================================================
# Resolve conflict using auto-merge (You can also use normal IDE resolution and then do `lit add app.py` and commit the merge)
# ============================================================
lit merge --abort
lit merge origin/feature-greeting-alt --auto
# Auto-merge successful!

cat app.py
# print('Hello from DevB!')  (--auto uses 'recent' strategy by default)

# Complete the merge and push
lit commit -m "Merge feature-greeting-alt with auto-resolution"
lit push origin main

# Go back to devB
cd ../DevB
lit checkout main
lit pull

# ============================================================
# View the final result
# ============================================================
lit log --graph --all --oneline
lit show HEAD

# Cleanup when done (optional)
make clean
```

**Demonstrates:** Bare repos • Branching • Push/Pull • Merge conflicts • Conflict markers • Auto-merge resolution • Distributed collaboration

## Command Reference

### Repository Operations
| Command | Description |
|---------|-------------|
| `lit init [path]` | Initialize a new repository |
| `lit clone <url> [path]` | Clone a repository (add `--bare` for bare repo) |
| `lit config <action> <key> [value]` | Get/set/list configuration options |
| `lit status` | Show working tree and staging status |

### Basic Workflow
| Command | Description |
|---------|-------------|
| `lit add <files...>` | Stage files for commit |
| `lit commit -m <message>` | Create a commit with staged changes |
| `lit log [--oneline] [--graph] [--all]` | Show commit history |
| `lit show [commit]` | Display commit details and diff |
| `lit diff [options]` | Show changes (working/staged/commits) |

### Branching & Merging
| Command | Description |
|---------|-------------|
| `lit branch [name]` | List, create, or delete branches |
| `lit branch -d <name>` | Delete a branch |
| `lit checkout [-b] <branch>` | Switch branches (or create with `-b`) |
| `lit switch [-c] <branch>` | Modern branch switching command |
| `lit merge <branch>` | Merge branch into current branch |
| `lit merge <branch> --auto` | Auto-resolve conflicts (uses 'recent' strategy) |
| `lit merge <branch> --auto=ours` | Auto-resolve keeping current branch version |
| `lit merge <branch> --auto=theirs` | Auto-resolve taking incoming branch version |
| `lit merge <branch> --auto=union` | Auto-resolve by combining both versions |
| `lit merge --abort` | Abort current merge operation |
| `lit cherry-pick <commit>` | Apply a specific commit to current branch |
| `lit rebase <branch>` | Rebase current branch onto another |
| `lit rebase --continue/--abort` | Continue or abort in-progress rebase |

### Remote Operations
| Command | Description |
|---------|-------------|
| `lit remote` | List remote repositories |
| `lit remote add <name> <url>` | Add a remote repository |
| `lit remote remove <name>` | Remove a remote |
| `lit fetch [remote]` | Download objects and refs from remote |
| `lit push [remote] [branch]` | Push commits to remote |
| `lit pull [remote] [branch]` | Fetch and merge from remote |

### Stash Operations
| Command | Description |
|---------|-------------|
| `lit stash` | Save changes to stash (alias for push) |
| `lit stash push [-m <msg>]` | Save changes with optional message |
| `lit stash pop [stash]` | Apply and remove stash |
| `lit stash apply [stash]` | Apply stash without removing |
| `lit stash list` | List all stashed changes |
| `lit stash drop [stash]` | Remove a stash entry |
| `lit stash clear` | Remove all stash entries |
| `lit stash show [stash]` | Show stash contents |

### Tag Operations
| Command | Description |
|---------|-------------|
| `lit tag` | List all tags |
| `lit tag <name> [commit]` | Create lightweight tag |
| `lit tag -a <name> -m <msg>` | Create annotated tag |
| `lit tag -d <name>` | Delete a tag |
| `lit tag -l` | List all tags |

### Reset Operations
| Command | Description |
|---------|-------------|
| `lit reset [commit]` | Reset HEAD (default: mixed mode) |
| `lit reset --soft <commit>` | Reset HEAD only, keep staged and working |
| `lit reset --mixed <commit>` | Reset HEAD and index, keep working |
| `lit reset --hard <commit>` | Reset HEAD, index, and working directory |
| `lit reset <file>` | Unstage a file |

### Inspection Commands
| Command | Description |
|---------|-------------|
| `lit show-ref [--heads] [--tags]` | Display all references |
| `lit symbolic-ref <name> [ref]` | Read or modify symbolic references |
| `lit ls-tree [-r] <treeish>` | List contents of a tree object |
| `lit cat-file <type> <object>` | Display object content |
| `lit count-objects` | Count unpacked objects |
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
│   ├── config.py          # Configuration management
│   └── hash.py            # SHA-1 hashing utilities
├── operations/            # High-level operations
│   ├── diff.py            # Diff operations
│   ├── merge.py           # Merge engine with three-way merge
│   └── stash.py           # Stash management
├── remote/                # Remote repository operations
│   └── remote.py          # Remote fetch/push/pull operations
├── utils/                 # Utility modules
│   └── ignore.py          # .litignore pattern matching
├── cli/                   # Command-line interface
│   ├── main.py            # CLI entry point and routing
│   ├── output.py          # Formatted output with colors
│   └── commands/          # Individual command implementations (27 commands)
│       ├── add.py         ├── merge.py
│       ├── branch.py      ├── pull.py
│       ├── checkout.py    ├── push.py
│       ├── cherry_pick.py ├── rebase.py
│       ├── clone.py       ├── refs.py
│       ├── commit.py      ├── remote.py
│       ├── config.py      ├── reset.py
│       ├── diff.py        ├── show.py
│       ├── fetch.py       ├── stash.py
│       ├── init.py        ├── status.py
│       ├── log.py         ├── switch.py
│       ├── ls_tree.py     └── tag.py
└── tests/                 # Comprehensive test suite
    ├── unit/              # Unit tests (14 modules)
    └── integration/       # Integration tests (16 workflows)
```

### Technical Implementation
- **Object Model** - Immutable Blob, Tree, and Commit objects with content-addressable storage
- **Storage Format** - Git-compatible object format with zlib compression
- **Index Format** - Binary DIRC format compatible with Git
- **Diff Algorithm** - Line-based diffing with unified diff output
- **Merge Algorithm** - Three-way merge with lowest common ancestor (LCA) detection
- **References** - Symbolic and direct references with full HEAD support
- **Ignore Patterns** - Gitignore-compatible glob patterns with negation support

### Implemented Commands (27 total)
`init` `clone` `add` `commit` `status` `log` `show` `diff` `branch` `checkout` `switch` `merge` `cherry-pick` `rebase` `fetch` `pull` `push` `remote` `stash` `reset` `tag` `config` `show-ref` `symbolic-ref` `ls-tree` `cat-file` `count-objects`

## Testing

**Test Coverage:** 358 tests passing across 30 test modules

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/ -v          # Unit tests (14 modules)
python -m pytest tests/integration/ -v   # Integration tests (16 workflows)

# Run specific test files
python -m pytest tests/unit/test_merge.py -v
python -m pytest tests/integration/test_rebase_workflow.py -v

# Run tests matching a pattern
python -m pytest -k "stash"              # Run stash-related tests
python -m pytest -k "conflict"           # Run conflict-related tests

# Generate coverage report
python -m pytest --cov=lit --cov-report=html
open htmlcov/index.html                  # View coverage report
```

### Test Modules
**Unit Tests:** `test_checkout` `test_commit` `test_diff` `test_fetch` `test_hash` `test_ignore` `test_index` `test_merge` `test_objects` `test_refs` `test_remote` `test_repository` `test_tree`

**Integration Tests:** `test_branch_workflow` `test_cherry_pick_workflow` `test_commit_workflow` `test_config_command` `test_conflict_workflow` `test_diff_command` `test_diff_workflow` `test_init_workflow` `test_merge_command` `test_rebase_workflow` `test_refs_command` `test_reset_workflow` `test_show_command` `test_stash_workflow` `test_tag_workflow`

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
- 🌐 Network protocol implementation (HTTP/HTTPS/SSH)
- 🔧 Submodule support
- 📦 Multiple worktrees
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
- [Architecture](docs/architecture.md) - System design and technical details

---

**Note:** Lit is a fully functional Git implementation suitable for learning, experimentation, and understanding version control internals. For production use, please use [Git](https://git-scm.com/).

# Lit - A Git-like Version Control System

Lit is a simplified implementation of Git in Python, featuring core version control functionality including distributed operations, branching, merging, and remote repositories.

## Features

- ✅ Repository initialization
- ✅ File staging and committing
- ✅ Branch management
- ✅ Commit history
- ✅ Diff viewing
- ✅ Merge operations (including conflict resolution)
- ✅ Remote operations (clone, fetch, pull, push)
- ✅ Content-addressable storage with SHA-1 hashing
- ✅ Distributed architecture

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/lit.git
cd lit

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Using pip -- not available yet (There is another lit :( )

```bash
pip install lit
```

## Quick Start

```bash
# Initialize a new repository
lit init

# Add files to staging area
lit add file.txt

# Commit changes
lit commit -m "Initial commit"

# Create a new branch
lit branch feature-branch

# Switch to the branch
lit checkout feature-branch

# View commit history
lit log

# View status
lit status
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=lit --cov-report=html

# Format code
black lit/ tests/

# Lint code
flake8 lit/ tests/

# Type check
mypy lit/
```

## Usage Examples

### Basic Workflow

```bash
# Initialize repository
lit init my-project
cd my-project

# Create a file
echo "Hello, Lit!" > hello.txt

# Stage and commit
lit add hello.txt
lit commit -m "Add hello.txt"

# View history
lit log
```

### Branching and Merging

```bash
# Create and switch to new branch
lit branch feature
lit checkout feature

# Make changes and commit
echo "New feature" > feature.txt
lit add feature.txt
lit commit -m "Add feature"

# Switch back to main and merge
lit checkout main
lit merge feature
```

### Working with Remotes

```bash
# Clone a repository
lit clone /path/to/remote/repo my-clone

# Add a remote
lit remote add origin /path/to/remote/repo

# Fetch changes
lit fetch origin

# Pull changes
lit pull origin main

# Push changes
lit push origin main
```

## Commands

| Command | Description |
|---------|-------------|
| `lit init [path]` | Initialize a new repository |
| `lit add <files>` | Add files to staging area |
| `lit commit -m <msg>` | Create a new commit |
| `lit status` | Show working tree status |
| `lit log` | Show commit history |
| `lit branch [name]` | List, create, or delete branches |
| `lit checkout <branch>` | Switch branches |
| `lit diff [options]` | Show changes |
| `lit merge <branch>` | Merge branches |
| `lit remote <command>` | Manage remotes |
| `lit fetch [remote]` | Download objects from remote |
| `lit pull [remote] [branch]` | Fetch and merge |
| `lit push [remote] [branch]` | Upload objects to remote |
| `lit clone <url> [path]` | Clone a repository |

## Implementation Status

- [x] Phase 1: Foundation (Object storage, repository structure)
- [x] Phase 2: Staging and Committing
- [x] Phase 3: History and Branches
- [x] Phase 4: Diffing
- [x] Phase 5: Merging
- [ ] Phase 6: Remote Operations
- [ ] Phase 7: Advanced Features
- [ ] Phase 8: Polish and Optimization

See [GIT_IMPLEMENTATION_PLAN.md](GIT_IMPLEMENTATION_PLAN.md) for detailed implementation plan.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Git and its elegant design
- Built as an educational project to understand version control internals
- Thanks to the Git community and documentation

## Resources

- [Pro Git Book](https://git-scm.com/book/en/v2)
- [Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain)
- [Implementation Plan](docs/lit%20implementation%20plan.md)

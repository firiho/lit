# Lit VCS Architecture

## Overview

Lit is a simplified Git implementation in Python that follows Git's core design principles:

1. **Content-addressable storage**: All objects are stored by their SHA-1 hash
2. **Immutable objects**: Once created, objects never change
3. **Directed Acyclic Graph (DAG)**: Commits form a DAG structure
4. **Distributed design**: Each repository is a complete copy

## Core Components

### 1. Object Store

The object store manages four types of objects:

- **Blob**: Raw file content
- **Tree**: Directory structure (references to blobs and other trees)
- **Commit**: Snapshot with metadata (tree, parents, author, message)
- **Tag**: Named reference to a commit (optional)

All objects are:
- Stored in `.lit/objects/`
- Named by their SHA-1 hash
- Compressed with zlib
- Immutable once created

### 2. Repository

The repository manages:
- `.lit` directory structure
- Object reading/writing
- Configuration
- Reference management

### 3. Index (Staging Area)

The index tracks:
- Files staged for commit
- File metadata (permissions, timestamps)
- Blob hashes for staged content

### 4. References

References are pointers to commits:
- **Branches**: Mutable pointers in `.lit/refs/heads/`
- **Tags**: Immutable pointers in `.lit/refs/tags/`
- **HEAD**: Special pointer to current branch or commit
- **Remote refs**: Track remote branches in `.lit/refs/remotes/`

## Data Flow

### Adding Files
```
Working Directory → (lit add) → Index → (lit commit) → Repository
```

### Committing
```
Index → Build Tree → Create Commit → Write Objects → Update References
```

### Branching
```
Create Reference → Point to Commit
```

### Merging
```
Find Common Ancestor → Three-way Merge → Resolve Conflicts → Create Merge Commit
```

## File System Layout

```
.lit/
├── objects/           # Object database
│   ├── ab/           # First 2 chars of hash
│   │   └── cdef...   # Rest of hash
│   └── ...
├── refs/             # References
│   ├── heads/        # Branches
│   │   ├── main
│   │   └── feature
│   ├── tags/         # Tags
│   └── remotes/      # Remote tracking branches
│       └── origin/
│           └── main
├── HEAD              # Current branch pointer
├── index             # Staging area
└── config            # Repository configuration
```

## Object Format

### Blob
```
blob <size>\0<content>
```

### Tree
```
tree <size>\0
<mode> <type> <hash> <name>
<mode> <type> <hash> <name>
...
```

### Commit
```
commit <size>\0
tree <tree-hash>
parent <parent-hash>
author <name> <timestamp>
committer <name> <timestamp>

<commit message>
```

## Design Decisions

### Why SHA-1?
- Standard in Git
- Good distribution
- 40-character hex representation
- Collision probability negligible for our use case

### Why Compression?
- Reduces storage space
- Fast compression/decompression with zlib
- Standard in Git

### Why Immutable Objects?
- Simplifies reasoning
- Enables caching
- Ensures integrity
- Enables distributed operation

### Why Index?
- Allows partial commits
- Enables atomic operations
- Improves performance
- Matches Git workflow

## Extension Points

The architecture supports:
- Custom merge strategies
- Hooks (pre-commit, post-commit, etc.)
- Alternative storage backends
- Additional object types
- Custom protocols

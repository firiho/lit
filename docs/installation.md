# Lit Installation Guide for End Users

## 🚀 Quick Install

### Option 1: Install from PyPI (Recommended - When Published)

Once Lit is published to PyPI, installation is simple:

```bash
# Install Lit globally
pip install lit -- Yes I know lit is taken! I'll prolly change it to lit-vcs

# Verify installation
lit --version

# Start using it!
cd my-project
lit init
```

That's it! No need to clone the repository or see any code.

---

### Option 2: Install from Source (Current Method)

If you want the latest development version:

```bash
# Clone the repository
git clone https://github.com/firiho/lit.git

# Install
cd lit
pip install .

# You can now delete the lit folder - the command is installed!
cd ..
rm -rf lit

# Use lit anywhere
cd ~/my-project
lit init
```

---

### Option 3: Install in Virtual Environment (Isolated)

If you don't want to install globally:

```bash
# Create a virtual environment
python -m venv lit-env

# Activate it
source lit-env/bin/activate  # On Windows: lit-env\Scripts\activate

# Install lit
pip install lit

# Use lit (only while virtual environment is active)
lit init
```

---

## 🎯 Basic Usage (Just Like Git!)

```bash
# Initialize a repository
lit init

# Add files to staging
lit add file.txt
lit add .

# Commit changes
lit commit -m "My first commit"

# View status
lit status

# View history
lit log

# Create a branch
lit branch feature

# Switch branches
lit checkout feature

# Merge branches
lit merge main

# Work with remotes
lit remote add origin /path/to/remote
lit push origin main
lit pull origin main
```

---

## 📦 Uninstall

```bash
# Uninstall Lit
pip uninstall lit
```

---

## 🔧 Updating

```bash
# Update to latest version
pip install --upgrade lit
```

---

## 💡 Important Notes

1. **No coding required** - Just install and use like any CLI tool
2. **Works anywhere** - Once installed, `lit` command is available globally
3. **No repository access needed** - After installation, you never need to see the source code
4. **Just like Git** - Use it the same way you use Git commands

---

## 🆘 Troubleshooting

### Command not found after installation

If `lit` command is not found after installation:

```bash
# Check if pip bin directory is in PATH
python -m pip show lit

# Or use it via Python module
python -m lit init
```

### Permission denied

```bash
# Install with --user flag
pip install --user lit
```

### Multiple Python versions

```bash
# Use specific Python version
python3 -m pip install lit
python3 -m lit init
```

---

## 📚 Next Steps

- Read the [User Guide](user_guide.md) for detailed command reference
- Check [Examples](examples/) for common workflows
- Visit the [GitHub repository](https://github.com/firiho/lit) for issues/contributions

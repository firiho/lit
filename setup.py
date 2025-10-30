"""Setup configuration for Lit."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='lit',
    version='0.1.0',
    author='Flambeau Iriho',
    author_email='irihoflambeau@gmail.com',
    description='A Git-like version control system implemented in Python',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/firiho/lit',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Version Control',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    install_requires=[
        'click>=8.0.0',
        'colorama>=0.4.0',
        'requests>=2.28.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
    },
    entry_points={
        'console_scripts': [
            'lit=lit.cli.main:main',
        ],
    },
)

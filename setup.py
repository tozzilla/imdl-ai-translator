"""
Setup script per Translate IDML
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leggi il README per la descrizione lunga
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Leggi i requirements
requirements = []
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="translate-idml",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Traduce automaticamente file InDesign IDML usando OpenAI API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/translate-idml",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=5.0.0',
            'black>=22.0.0',
            'mypy>=1.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'translate-idml=src.main:cli',
        ],
    },
    keywords='indesign idml translation openai localization',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/translate-idml/issues',
        'Source': 'https://github.com/yourusername/translate-idml',
        'Documentation': 'https://github.com/yourusername/translate-idml#readme',
    },
)
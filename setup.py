from setuptools import setup, find_packages

setup(
    name="claude-book-reader",
    version="0.1.0",
    description="PDF book manager & reader with Claude Code integration",
    author="xgy",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PyQt6>=6.5.0",
        "PyMuPDF>=1.23.0",
        "networkx>=3.0",
        "markdown2>=2.4.0",
        "pygments>=2.15.0",
        "Pillow>=10.0.0",
        "PyYAML>=6.0",
        "Jinja2>=3.1.0",
        "Whoosh>=2.7.0",
    ],
    entry_points={
        "console_scripts": [
            "claude-book-reader=main:main",
        ],
    },
)

from setuptools import setup, find_packages

setup(
    name="mrr-forecast",
    version="0.1.0",
    description="A modular framework for forecasting Monthly Recurring Revenue using cohort-based modeling",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/mrr-forecast",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "spark": ["pyspark>=3.0.0"],
        "dev": ["pytest>=7.0.0", "black", "flake8"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

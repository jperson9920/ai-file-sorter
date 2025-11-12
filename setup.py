from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-image-tagger",
    version="1.0.0",
    author="AI File Sorter Team",
    description="Automated image tagging using booru databases and AI content analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jperson9920/ai-file-sorter",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pyyaml>=6.0",
        "pillow>=10.0.0",
        "requests>=2.31.0",
        "saucenao-api>=2.4.0",
        "pybooru>=4.2.2",
        "PicImageSearch>=3.0.0",
        "pyexiftool>=0.5.6",
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "transformers>=4.30.0",
        "numpy>=1.24.0",
        "jsonschema>=4.17.0",
        "tqdm>=4.65.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "image-tagger=src.main:main",
        ],
    },
)

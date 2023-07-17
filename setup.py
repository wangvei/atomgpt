import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="atomgpt",
    version="2023.7.1",
    author="Kamal Choudhary",
    author_email="kamal.choudhary@nist.gov",
    description="chemnlp",
    install_requires=[
        "numpy>=1.22.0",
        "scipy>=1.6.3",
        "jarvis-tools>=2021.07.19",

    ],
    # scripts=["chemnlp/utils/run_chemnlp.py"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/usnistgov/atomgpt",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)

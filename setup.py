import setuptools  # type: ignore

version = {}
with open("mutwo/clock_version/__init__.py") as fp:
    exec(fp.read(), version)

VERSION = version["VERSION"]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

extras_require = {"testing": ["pytest>=7.1.1"]}

setuptools.setup(
    name="mutwo.clock",
    version=VERSION,
    license="GPL",
    description="clock extension for event based framework for generative art",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Levin Eric Zimmermann",
    author_email="levin.eric.zimmermann@posteo.eu",
    url="https://github.com/mutwo-org/mutwo.clock",
    project_urls={"Documentation": "https://mutwo.readthedocs.io/en/latest/"},
    packages=[
        package
        for package in setuptools.find_namespace_packages(
            include=["mutwo.*", "mutwo_third_party.*"]
        )
        if package[:5] != "tests"
    ],
    setup_requires=[],
    install_requires=[
        "mutwo.core>=1.2.0, <2.0.0",
        "mutwo.music>=0.20.0, <1.0.0",
        "mutwo.timeline>=0.3.0, <0.5.0",
        "mutwo.abjad>=0.15.0, <1.0.0",
        "mutwo.common>=0.11.0, <1.0.0",
        "numpy>=1.18, <2.00",
        "jinja2>=3.1.2, <4.0.0",
    ],
    include_package_data=True,
    extras_require=extras_require,
    python_requires=">=3.10, <4",
)

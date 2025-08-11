import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="MignonFramework",

    version="0.1.5.0",

    author="Mignon Rex",
    author_email="rexdpbm@gmail.com",

    description="一个为爬虫设计的强大Python工具集",

    long_description=long_description,
    long_description_content_type="text/markdown",

    url="https://github.com/RexMignon/MignonFramework",

    packages=setuptools.find_packages(),

    # 项目依赖的第三方库
    install_requires=[
        "requests",
        "pymysql"
    ],

    classifiers=[
        "Development Status :: 3 - Alpha",

        "License :: OSI Approved :: MIT License",

        "Operating System :: OS Independent",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",

        "Intended Audience :: Developers",

        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: System :: Networking",
    ],

    python_requires='>=3.8',
)

# python setup.py sdist bdist_wheel
# python -m twine upload dist/*
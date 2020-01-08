import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(

    name='monopolpy_companion.py.py',

    version='1.3',

    scripts=['monopolpy_companion.py'],

    author="Taylor-Jayde Blackstone",

    author_email="t.blackstone@inspyre.tech",

    description="The ultimate app that manages your Monopoly Board Game sessions for you",

    long_description=long_description,

    long_description_content_type="text/markdown",

    url="https://github.com/tayjaybabee/monopolpy_companion",

    packages=setuptools.find_packages(),

    classifiers=[

        "Programming Language :: Python :: 3",

        "License :: OSI Approved :: MIT License",

        "Operating System :: OS Independent",

        ],

    )

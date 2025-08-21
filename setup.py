from setuptools import setup, find_packages

# README.md 파일을 읽어 long_description으로 사용
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='pynorma',
    version='1.0.0', # 정식 1.0 버전 명시
    author='nash-dir', # 작성자 이름
    description="A smart tool for preprocessing messy tabular data.", # 짧은 설명
    long_description=long_description, # README.md 내용
    long_description_content_type="text/markdown", # 마크다운 형식 명시
    url='https://github.com/nash-dir/PyNorma', # GitHub 주소
    packages=find_packages(),
    install_requires=[
        'pandas>=1.3.0',
        'openpyxl>=3.0.10',
        'chardet>=5.0.0',
        # 필요한 다른 라이브러리들...
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.8',
)
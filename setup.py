from setuptools import setup
from os.path import join, dirname

requirements = [
    "aiohttp>=3.8.1",
    "selenium>=4.1.5",
]

setup(
    name='async-hcaptcha',
    version='1.0.0b3',
    packages=["async_hcaptcha"],
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    long_description_content_type="text/markdown",
    description='Unofficial async wrapper for interacting with hCaptcha',
    url='https://github.com/RuslanUC/aio-hcaptcha',
    repository='https://github.com/RuslanUC/aio-hcaptcha',
    author='RuslanUC',
    install_requires=requirements,
    python_requires='>=3.7',
    license='MIT',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
      ]
)

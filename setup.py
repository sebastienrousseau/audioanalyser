from setuptools import setup, find_packages

# Read the contents of your README file
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='audioanalyser',
    version='0.0.2',
    author='Your Name',
    author_email='your.email@example.com',
    description='A Python application for Azure AI Speech to Text service',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://audioanalyser.pro',
    packages=find_packages(),
    install_requires=[
        'azure-cognitiveservices-speech>=1.34.0',
        'python-dotenv>=0.15.0',
        'requests>=2.25.1',
        'cherrypy>=18.6.0',
    ],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',  # Change as appropriate
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',  # Replace with your license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    # Optional: Add entry points if you have any scripts or command-line tools
    entry_points={
        'console_scripts': [
            'your_script=your_package.your_module:main_function',
        ],
    },
)

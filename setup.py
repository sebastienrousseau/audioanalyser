from setuptools import setup, find_packages

setup(
    name='AzureSpeechToText',
    version='1.0.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='A Python application for Azure AI Speech to Text service',
    packages=find_packages(),
    install_requires=[
        'azure-cognitiveservices-speech>=1.15.0',
        'python-dotenv>=0.15.0',
        'requests>=2.25.1'
    ],
    python_requires='>=3.6',  # Specify your Python version requirement
)

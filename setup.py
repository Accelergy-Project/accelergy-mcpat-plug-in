from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='accelergy-mcpat-plug-in',
    version='0.1',
    description='An energy estimation plug-in for Accelergy framework using McPat',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
    ],
    keywords='accelerator hardware energy estimation McPat',
    author='Matthew Woicik',
    author_email='mwoicik@mit.edu',
    license='MIT',
    install_requires=['pyYAML'],
    python_requires='>=3.6',
    data_files=[
        ('share/accelergy/estimation_plug_ins/accelergy-mcpat-plug-in',
         ['mcpat.estimator.yaml',
          'mcpat_wrapper.py',
          'properties.xml'])
    ],
    include_package_data=True,
    entry_points={},
    zip_safe=False,
)

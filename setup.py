# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="rpanel",
    version="1.6.10",
    description="Professional Web Hosting Control Panel for Frappe",
    author="Rokct Holdings",
    author_email="admin@rokct.ai",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)

.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/memaldi/ckanext-welive_utils.svg?branch=master
    :target: https://travis-ci.org/memaldi/ckanext-welive_utils

.. image:: https://coveralls.io/repos/memaldi/ckanext-welive_utils/badge.png?branch=master
  :target: https://coveralls.io/r/memaldi/ckanext-welive_utils?branch=master

=============
ckanext-welive_utils
=============

Some utility methods required for WeLive's Open Data Stack.

------------
Requirements
------------

* CKAN 2.4.1

------------------------
Development Installation
------------------------

To install ckanext-welive_utils for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/memaldi/ckanext-welive_utils.git
    cd ckanext-welive_utils
    python setup.py develop
    pip install -r dev-requirements.txt

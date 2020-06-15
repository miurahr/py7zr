:tocdepth: 2

.. _filters:


Possible filters to create archive
==================================


Here is a list of examples for possible filters values.
You can use it when creating SevenZipFile object.

.. code-block::

    from py7zr import FILTER_LZMA, SevenZipFile

    filters = [{'id': FILTER_LZMA}]
    archive = SevenZipFile('target.7z', mode='w', filters=filters)



LZMA2 + Delta
    ``[{'id': FILTER_DELTA}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA2 + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA2 + ARM
    ``[{'id': FILTER_ARM}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA}]``

LZMA2
    ``[{'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}]``

LZMA
    ``[{'id': FILTER_LZMA}]``

BZip2
    ``[{'id': FILTER_BZIP2}]``

Deflate
    ``[{'id': FILTER_DEFLATE}]``

ZStandard
    ``[{'id': FILTER_ZSTD}]``

7zAES + LZMA2 + Delta
    ``[{'id': FILTER_DELTA}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + LZMA2 + BCJ
    ``[{'id': FILTER_X86}, {'id': FILTER_LZMA2, 'preset': PRESET_DEFAULT}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + LZMA
    ``[{'id': FILTER_LZMA}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + Deflate
    ``[{'id': FILTER_DEFLATE}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + BZip2
    ``[{'id': FILTER_BZIP2}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

7zAES + ZStandard
    ``[{'id': FILTER_ZSTD}, {'id': FILTER_CRYPTO_AES256_SHA256}]``

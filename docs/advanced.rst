.. _advanced_usage:

**************
Advanced usage
**************

Stream 7z content
-----------------

The py7zr provide a way to stream archive content with ``extract`` and ``extractall`` methods.
The methods accept an object which implement ``py7zr.io.WriterFactory`` interface as ``factory`` arugment.
Your custom class which implements ``WriterFactory`` interface should have ``create`` method.
The ``create`` method should return your custom class object which implements ``Py7zIO`` interface.
The ``Py7zIO`` interface is as similar as Python Standard ``BinaryIO`` but it also have ``size`` method.

When the py7zr extract the archive contents, it calls the factory object with filename and ask creating the io object.
The py7zr write the io object with ``write`` method, which is as similar as an object returned by the standard ``open`` method.

You can process ``write`` in your custom class. The method is called on-the-fly when the py7zr move to extract the target
archive file.

Note: Because the py7zr may run in multi-threaded, your custom class should be thread-safe.

The py7zr provide the way to stream content without buffering all the archive content in a memory.

Example to extract into network storage
---------------------------------------

Here is a pseudo code to demonstrate a way to extract contents into cloud storage.
To simplify things in an example code, all the authentication, bucket operation,
all the mandatory headers are omitted.


.. code-block::

    def extract_stream():
        factory = StreamIOFactory()
        with py7zr.SevenZipFile("target.7z") as archive:
            archive.extractall(factory=factory)


    class StreamIO(py7zr.io.Py7zIO):
        """Example network storage writer."""

        def __init__(self, fname: str):
            self.fname = fname
            self.length = 0

        def write(self, data: [bytes, bytearray]):
            self.length += len(data)
            # the py7zr will call write multiple time, so you need to append data
            requests.put("https://your.custom.network.storage.example.com/append/to/file/command/", data=data)

        def read(self, size: Optional[int] = None) -> bytes:
            return b''

        def seek(self, offset: int, whence: int = 0) -> int:
            return offset

        def flush(self) -> None:
            pass

        def size(self) -> int:
            return self.length


    class StreamIOFactory(py7zr.io.WriterFactory):
        """Factory class to return StreamWriter object."""

        def __init__(self):
            self.products = {}

        def create(self, filename: str) -> Py7zIO:
            product = StreamIO(filename)
            self.products[filename] = product
            return product

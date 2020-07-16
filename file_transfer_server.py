from rdts import RDTSocket
from sys import exit

sock = RDTSocket()
sock.initialize()
sock.bind("127.0.0.1", 0)
print("{}:{}".format(*sock.get_source_endpoint()))

with open("f1.txt", "r") as content_file:
    data = content_file.read().strip()
    content_file.close()

try:
    sock.connect(*input().split(':'))
except TimeoutError:
    print("Heavy network congestion detected")
    exit(0)

sock.write(data)
sock.close()
print("server application terminating")
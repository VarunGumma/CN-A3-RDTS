from rdts import RDTSocket
from sys import exit

sock = RDTSocket()
sock.initialize()
sock.bind("127.0.0.1", 0)
print("{}:{}".format(*sock.get_source_endpoint()))

try:
    sock.connect(*input().split(':'))
except TimeoutError:
    print("Heavy network congestion detected")
    exit(0)

sock.write("10"*8192)
sock.close()
print("server application terminating")
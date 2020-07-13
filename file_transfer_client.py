from rdts import RDTSocket
from time import time
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

t0 = time()
try:
    while sock.connected():
        sock.read()
except TimeoutError:
    print("TIME OUT!")

print(time() - t0)
data = sock.get_data()

print("client application terminating")
# print("received data: " + data)

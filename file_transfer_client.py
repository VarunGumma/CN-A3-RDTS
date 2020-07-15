from rdts import RDTSocket
from time import time
from sys import exit
from re import findall

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
data = "\n".join([line.decode("ascii") for line in findall(rb"[^\x00-\x1f\x7f-\xff]+", sock.get_data())])

with open("f2.txt", "w") as content_file:
    content_file.write(data)
    content_file.close()

print("client application terminating")

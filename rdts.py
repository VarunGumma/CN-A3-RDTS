import socket
from hashlib import blake2b
from time import sleep, time
from threading import Thread
from random import randint


class RDTSocket:

    _MOD = 1 << 16
    _to_int = lambda self, s: int.from_bytes(s, 'big')
    _to_bytes = lambda self, x, b: x.to_bytes(b, 'big')
    _PACKET_SIZE = 1024

    def __init__(self):
    	
        self._socket = None
        self._bound = False
        self._connected = False
        self._connection_closed = False
        self._source_endpoint = None
        self._target_endpoint = None
        self._seq = randint(-1, 65536)
        self._ack = self._seq + 1
        self._read_buffer = dict()
        self._write_buffer = dict()

    def _get_ip():

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]
        sock.close()
        return ip

    def initialize(self):

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def bind(self, ip, port):

        if not self._socket:
            raise Exception("Initialize the socket before binding.")

        try:
            port = int(port)
            if port < 0 or port > 65535:
                raise ValueError("Invalid port number.")
        except ValueError:
            raise ValueError("Invalid port number.")
            return

        try:
            self._socket.bind((ip, port))
            self._bound = True
            self._source_endpoint = self._socket.getsockname()
        except socket.gaierror:
            raise OSError("Invalid IP address.")
        except PermissionError:
            raise PermissionError("Permission denied. Try using another port.")
        except OSError:
            raise OSError("Port already in use.")

    def get_source_endpoint(self):

        if not self._bound:
            raise Exception("Socket not bound.")
        return self._source_endpoint

    def connect(self, ip, port):

        try:
            socket.inet_aton(ip)
        except OSError:
            raise OSError("Invalid IP address.")

        try:
            port = int(port)
            if port < 0 or port > 65535:
                raise ValueError("Invalid port number.")
        except ValueError:
            raise ValueError("Invalid port number.")

        self._target_endpoint = (ip, port)
        print("sending SYN")
        packet = self._make_packet(packet_type="SYN")

        def async_read():

            for _ in range(10):
                self._socket.settimeout(60)
                try:
                    data, endpoint = self._socket.recvfrom(self._PACKET_SIZE)
                except socket.timeout:
                    raise TimeoutError("1000: timed out")
                if endpoint != self._target_endpoint:
                    continue
                typ = self._rectify(data[:4])
                hsh = self._rectify(data[-32:], 8)
                if typ and hsh and blake2b(data[:-32]).digest()[:8] == hsh:
                    self._connected = True
                    break

        read_conn_thread = Thread(target=async_read)
        read_conn_thread.start()

        for _ in range(20):
            if self._connected:
                break
            self._socket.sendto(packet, self._target_endpoint)
            sleep(0.5)

        if not self._connected:
            self._target_endpoint = None
            raise TimeoutError("1001: timed out")

        read_thread = Thread(target=self._read)
        read_thread.setDaemon(True)
        read_thread.start()

    def _read(self):

        syn_received = False
        while True:
            try:
                data, addr = self._socket.recvfrom(self._PACKET_SIZE)
            except socket.timeout:
                raise TimeoutError("1002: timed out")

            if addr != self._target_endpoint:
                continue

            typ = self._rectify(data[:4])
            if not typ:
                continue
            hsh = self._rectify(data[-32:], 8)
            if not hsh or blake2b(data[:-32]).digest()[:8] != hsh:
                continue

            if ord(typ) == 0:
                seq = self._to_int(self._rectify(data[4:12], 2))
                if bool(self._read_buffer.get(seq)):
                    # if a duplicate data packet is received
                    # don't overwrite
                    # just send an ACK for it
                    print("received duplicate seq: {}".format(seq))
                else:
                    self._read_buffer[seq] = data[12:-32]
                    print("received seq: {}".format(seq))
                packet = self._make_packet(seqno=seq, packet_type="ACK")
                self._socket.sendto(packet, self._target_endpoint)

            if ord(typ) == 1:
                ack = self._to_int(self._rectify(data[4:12], 2))
                print("received ack: {}".format(ack))
                try: 
                    self._write_buffer.pop(ack)
                except KeyError:
                    print("received duplicate ack: {}".format(ack))
            
            if ord(typ) == 2:
                # if more than one syn packets reach
                # just consider the first one
                # rest can be discarded
                if not syn_received:
                    print("received SYN")
                    syn_received = True

            if ord(typ) == 3:
                print("received FIN")
                self._connection_closed = True
                self.close()

    def _rectify(self, s, z=1):

        c = 0
        n = len(s)
        if n % z:
            return None
        m = None
        for i in range(0, n, z):
            x = s[i:i + z]
            if c == 0:
                m = x
                c += 1
            elif m == x:
                c += 1
            else:
                c -= 1
        c = 0
        for i in range(0, n, z):
            x = s[i:i + z]
            if x == m:
                c += 1
        if 2 * c > n // z:
            return m
        return None

    def read(self):

        if not self._connected:
            raise Exception("Establish a connection before calling `read`.")
        if self._connection_closed:
            return None
        for _ in range(100):
            if self._connection_closed:
                return None
            if self._ack in self._read_buffer:
                data = self._read_buffer.pop(self._ack).rstrip(bytes([255]))
                self._ack += 1
                return data
            sleep(0.25)

    def _write(self):

        while self._write_buffer:
            if not self.connected():
                print("Other party has closed the connection.")
                break
            seq = next(iter(self._write_buffer))
            packet, t0 = self._write_buffer.pop(seq)
            if t0 - t0 != 0:
                t0 = time()
            if time() - t0 > 60:
                raise TimeoutError("1004: timed out")
            print("sent seq: {}".format(seq))
            self._socket.sendto(packet, self._target_endpoint)
            self._write_buffer[seq] = (packet, t0)
            sleep(0.1)

    def write(self, data):

        data_length = len(data)
        CHUNK_SIZE = self._PACKET_SIZE - 44
        for i in range(0, data_length, CHUNK_SIZE):
            chunk = data[i:i + CHUNK_SIZE].encode()
            chunk += bytes([255] * (CHUNK_SIZE - len(chunk)))
            self._seq += 1
            if self._seq == self._MOD:
                self._seq = 0
            packet = self._make_packet(
                data=chunk, seqno=self._seq, packet_type="DATA")
            if self._seq in self._write_buffer:
                for _ in range(10):
                    if self._seq not in self._write_buffer:
                        break
                    sleep(0.1)
                if self._seq in self._write_buffer:
                    raise TimeoutError("1005: timed out")
            self._write_buffer[self._seq] = (packet, float('inf'))
        self._write()

    def _make_packet(self, packet_type, data=None, seqno=None):

        packet = b''
        if packet_type == "SYN":
            packet += bytes([2] * 4)
            packet += bytes(self._PACKET_SIZE - 36)
        elif packet_type == "FIN":
            packet += bytes([3] * 4)
            packet += bytes(self._PACKET_SIZE - 36)
        elif packet_type == "ACK":
            packet += bytes([1] * 4)
            packet += self._to_bytes(seqno, 2) * 4
            packet += bytes(self._PACKET_SIZE - 44)
        elif packet_type == "DATA":
            packet += bytes(4)
            packet += self._to_bytes(seqno, 2) * 4
            packet += data
        packet += blake2b(packet).digest()[:8] * 4
        return packet

    def get_data(self):
        data = b''
        for key in self._read_buffer.keys():
            data += self._read_buffer[key]
        return data

    def close(self):

        print("sending FIN")
        if not self._connected:
            raise Exception("No connection to close.")
        packet = self._make_packet(packet_type="FIN")
        for _ in range(10):
            self._socket.sendto(packet, self._target_endpoint)
            sleep(0.1)
            if self._connection_closed:
                return

    def connected(self):
        return self._connected and not self._connection_closed

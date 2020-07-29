import socket
import random
import threading

UDP_IP = "127.0.0.1"
UDP_PORT = 69 # TFTP Protocol Port (69)

# header opcode is 2 bytes
TFTP_OPCODES = {
    1: 'RRQ',
    2: 'WRQ',
    3: 'DATA',
    4: 'ACK',
    5: 'ERROR'
}
TRANSFER_MODES = ['netascii', 'octet', 'mail']
SESSIONS = dict()


def create_data_packet(block, filename, mode):
    data = bytearray()
    # append data opcode (03)
    data.append(0)
    data.append(3)

    # append block number (2 bytes)
    b = f'{block:02}'
    data.append(int(b[0]))
    data.append(int(b[1]))

    # append data (512 bytes max)
    f = open(filename, 'rb') # ensure file exists
    offset = (block - 1) * 512
    f.seek(offset, 0)
    content = f.read(512)
    f.close()
    data += content

    return data


def create_ack_packet(block):
    ack = bytearray()
    #append acknowledgement opcode (04)
    ack.append(0)
    ack.append(4)

    # appen block number (2 bytes)
    b = f'{block:02}'
    ack.append(int(b[0]))
    ack.append(int(b[1]))

    return ack


def send_packet(packet, socket, addr):
    socket.sendto(packet, addr)


# Get opcode from TFTP header
def get_opcode(bytes):
    opcode = int.from_bytes(bytes[0:2], byteorder='big')
    if opcode not in TFTP_OPCODES.keys():
            # send error packet
            pass
    return TFTP_OPCODES[opcode]


# Return filename and mode from decoded RRQ/WRQ header
def decode_request_header(data):
    header = data[2:].split(b'\x00')
    filename = header[0].decode('utf-8');
    mode = header[1].decode('utf-8').lower()

    if mode not in TRANSFER_MODES:
        # send error packet
        pass
    return filename, mode


# Find a random port between 1025 and 65535 that is not in use
# by this service
def get_random_port():
    while True:
        port = random.randint(1025, 65536)
        if(port not in SESSIONS.keys()):
            return port


def create_udp_socket(ip=UDP_IP, port=UDP_PORT):
    sock = socket.socket(socket.AF_INET,   # Internet
                        socket.SOCK_DGRAM) # UDP
    sock.bind((ip, port))
    return sock


def listen(sock, filename, mode):
    (ip, port) = sock.getsockname()
    print(f'listening on port: {port}')
    try:
        while True:
            data, addr = sock.recvfrom(1024) # buffer size is 2014 bytes
            print(f'thread data: {data}')
            print(f'thread addr: {addr}')

            opcode = get_opcode(data)
            if opcode == 'ACK':
                block = int.from_bytes(data[2:4], byteorder='big') + 1 # next block
                packet = create_data_packet(block, filename, mode)
                SESSIONS[port]['packet'] = packet
                send_packet(packet, sock, addr)
            elif opcode == 'DATA':
                block = int.from_bytes(data[2:4], byteorder='big')
                content = data[4:]
                # todo: write data to file
                packet = create_ack_packet(block)
                SESSIONS[port]['packet'] = packet
                send_packet(packet, sock, addr)

                if len(content) < 512:
                    # todo: clean up SESSIONS
                    # close socket and end thread
                    sock.close()
                    return False
    except:
        # todo: clean up SESSIONS
        # close socket and end thread
        sock.close()
        return False # returning from the thread's run() method ends the thread



def main():
    sock = create_udp_socket()
    
    while True:
        data, addr = sock.recvfrom(1024)
        print(f'data: {data}')
        print(f'addr: {addr}')

        opcode = get_opcode(data)
        if opcode == 'RRQ' or opcode == 'WRQ':
            filename, mode = decode_request_header(data)

            if opcode == 'RRQ':
                packet = create_data_packet(1, filename, mode)
            else:
                packet = create_ack_packet(0)
            
            port = get_random_port()
            SESSIONS[port] = {
                'client': addr, 
                'packet': packet,
                'consec_timeouts': 0
            }

            client_socket = create_udp_socket(port=port)
            send_packet(packet, client_socket, addr)
            threading.Thread(target=listen, args=(client_socket, filename, mode)).start()


if __name__ == '__main__':
    main()

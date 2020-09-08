import socket


def netcat(hostname, port, content, timeout=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout is not None:
        s.settimeout(timeout)
    s.connect((hostname, port))
    s.sendall(content)
    reply = ''
    while 1:
        data = s.recv(1024)
        if data == '':
            break
        reply += data
    s.close()
    return reply

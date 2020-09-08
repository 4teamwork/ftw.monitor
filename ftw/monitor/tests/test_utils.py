from ftw.monitor.utils import netcat
from unittest import TestCase
import socket
import SocketServer
import threading
import time


class TCPEchoHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        response = "Received: %s" % data
        if data == 'DELAY':
            time.sleep(1)
        self.request.sendall(response)


class TestNetcatHelper(TestCase):

    def setUp(self):
        self.server = SocketServer.ThreadingTCPServer(
            ('localhost', 0), TCPEchoHandler)
        self.ip, self.port = self.server.server_address

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)

    def test_returns_reply(self):
        msg = 'hello'
        reply = netcat(self.ip, self.port, msg)
        self.assertEqual('Received: %s' % msg, reply)

    def test_accepts_timeout(self):
        msg = 'DELAY'
        with self.assertRaises(socket.timeout):
            netcat(self.ip, self.port, msg, timeout=0.5)

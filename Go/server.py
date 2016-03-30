from .board import board
import asynchat
import asyncore
import socket
import pickle

chat_room = {}

sep_sequence = "\x1c\x1d\x1e\x1f"
end_sequence = sep_sequence[::-1]

class server():
    def __init__(self, x, y, komi=6.5, port=44444):
        self.chat = ChatServer("0.0.0.0", port, self)
        self.board = board(x, y, komi)
        self.state = "SETUP"
        self.black = None
        self.white = None
        self.spectator = None

    def start(self):
        if self.state == "SETUP":
            self.state = "LIVE"
            asyncore.loop(map=chat_room)
            return True
        return False

    def color(self, player):
        if player == self.white:
            return "white"
        elif player == self.black:
            return "black"
        else:
            return False

    def make_move(self, color, x, y):
        try:
            return str(self.board.place(color, x, y))
        except Exception as e:
            return str(e.args[0])

    def process_player_request(self, player, req):
        if req[0] == 'move':
            move = self.make_move(self.color(player), int(req[1]), int(req[2]))
            player.snd(req[0] + sep_sequence + str(move))
            if move == 'True':
                board = pickle.dumps(self.board.move_history, 0)
                self.white.snd("history" + sep_sequence + board)
                self.black.snd("history" + sep_sequence + board)
        else:
            self.process_spectator_request(player, req)

    def process_spectator_request(self, handler, req):
        if req[0] == "score":
            handler.snd(req[0] + sep_sequence + str(self.board.score(False)))
        elif req[0] == "territorial_score":
            handler.snd(req[0] + sep_sequence + str(self.board.score(True)))
        elif req[0] == "board":
            print(self.board)
            handler.snd(req[0] + sep_sequence + str(self.board))
        elif req[0] == "history":
            handler.snd(req[0] + sep_sequence + pickle.dumps(self.board.move_history, 0))
        elif req[0] == "be_player":
            if not self.black:
                self.black = handler
                handler.snd(req[0] + sep_sequence + "black")
                print("Assigned black player")
            elif not self.white and handler != self.black:
                self.white = handler
                handler.snd(req[0] + sep_sequence + "white")
                print("Assigned white player")
            else:
                handler.snd(req[0] + sep_sequence + "no")
                print("Rejected player")
        else:
            handler.snd(req[0] + sep_sequence + "Unknown request")

    def handle_request(self, msg, handler):
        if handler in [self.black, self.white]:
            self.process_player_request(handler, msg.split(sep_sequence))
        else:
            self.process_spectator_request(handler, msg.split(sep_sequence))
 
class ChatHandler(asynchat.async_chat):
    def __init__(self, sock, server):
        asynchat.async_chat.__init__(self, sock=sock, map=chat_room)
        self.set_terminator(end_sequence)
        self.buffer = []
        self.server = server
 
    def collect_incoming_data(self, data):
        self.buffer.append(data)
 
    def found_terminator(self):
        msg = ''.join(self.buffer)
        print('Received:', msg)
        self.buffer = []
        self.server.handle_request(msg, self)

    def snd(self, msg):
        print(str(msg) + end_sequence)
        self.push(str(msg) + end_sequence)
 
class ChatServer(asyncore.dispatcher):
    def __init__(self, host, port, server):
        asyncore.dispatcher.__init__(self, map=chat_room)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((host, port))
        self.listen(5)
        self.server = server
 
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = ChatHandler(sock, self.server)

# -*- coding: utf-8 -*-
import os, sys, socket, select, threading, thread, time, datetime

HELLO_STATUS = False
JOIN_STATUS  = False
LOBY_LEADER_STATUS = False
BUSY_CONDITION = False

class Chat_Server(threading.Thread):                                # CHAT SERVER THREAD
    SOCKET_LIST = []

    def __init__(self):
        threading.Thread.__init__(self)
        self.HOST = self.findMyIpAdress()
        self.PORT = 0           # otomatik 1024-65535 arasinda uygun bir porta atama yapar.
        self.server_socket = None
        self.conn = None
        self.serverTextStart = True
        self.running = 1

    # findMyIpAdress
    def findMyIpAdress(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        s.close()
        return host

    def run(self):                                                 # Starts 'CHAT SERVER THREAD'
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(10)
        self.PORT = self.server_socket.getsockname()[1]

        # add server socket object to the list of readable connections
        self.SOCKET_LIST.append(self.server_socket)

        print ("Chat server started on port " + str(self.PORT))

        while self.running == 1:

            if JOIN_STATUS == True:                                 # JOIN_STATUS control
                # get the list sockets which are ready to be read through select
                # 4th arg, time_out  = 0 : poll and never block
                try:
                    ready_to_read, ready_to_write, in_error = select.select(self.SOCKET_LIST, [], [], 0)

                    for sock in ready_to_read:
                        # a new connection request recieved
                        if sock == self.server_socket:
                            self.conn, self.addr = self.server_socket.accept()
                            self.SOCKET_LIST.append(self.conn)

                            time.sleep(0.5)
                            self.otherUserName = getUserName(self.addr[0], self.addr[1], 'clientPort')

                            if(self.otherUserName != "No_User"):
                                print "Client ('%s') connected\n" % self.otherUserName
                                writeToLogFile(chat_centralClient.userName, "Client ('%s') connected" % self.otherUserName + "\n")

                            if self.serverTextStart and LOBY_LEADER_STATUS:
                                # chat_centralClient.kill()
                                text_input.start()
                                self.serverTextStart = False

                            if (self.otherUserName != "No_User"):
                                self.broadcast(self.server_socket, self.conn, "['%s'] entered our chatting room\n" % self.otherUserName)

                        # a message from a client, not a new connection
                        else:
                            global BUSY_CONDITION
                            # process data recieved from client,
                            try:
                                # receiving data from the socket.
                                data = sock.recv(1024)
                                if data:
                                    if data == "CHAT_REQUEST":
                                        if BUSY_CONDITION == True:
                                            self.conn.send("BUSY")
                                            time.sleep(0.2)
                                        else:
                                            print (str(self.addr) + " sent you a chat request. \n")
                                            writeToLogFile(chat_centralClient.userName, (str(self.addr) + " sent you a chat request. \n"))
                                            while True:
                                                chatChoice = str(raw_input("Use 'OK' or 'REJECT' to reply: "))
                                                if chatChoice == "OK":
                                                    BUSY_CONDITION = True
                                                    self.conn.send("OK")
                                                    # self.broadcast(self.server_socket, sock, "OK")
                                                    serverData = str(sock.recv(1024))
                                                    host, port = serverData.split(",")
                                                    chat_client.HOST = str(host)
                                                    chat_client.PORT = int(port)
                                                    chat_client.ConnectionType = "LobyParticipant"

                                                    chat_client.start()

                                                    userName = getUserName(chat_server.server_socket.getsockname()[0],chat_server.server_socket.getsockname()[1], 'serverPort')
                                                    clientPort = chat_client.client_socket.getsockname()[1]
                                                    chat_centralClient.central_client_socket.sendall("clientPortUpdate")
                                                    time.sleep(0.3)
                                                    data = str(userName) + "," + str(clientPort)
                                                    chat_centralClient.central_client_socket.sendall(data)
                                                    text_input.start()
                                                    break
                                                elif chatChoice == "REJECT":
                                                    #self.broadcast(self.server_socket, sock, "REJECT")
                                                    self.conn.send("REJECT")
                                                    break
                                                else:
                                                    print ("Wrong input choice. You have to enter only 'OK' or 'REJECT' \n")
                                    else:
                                        # there is something in the socket
                                        userName = getUserName(str(sock.getpeername()[0]), str(sock.getpeername()[1]), 'clientPort')
                                        print '\r' + '[' + str(userName) + '] ' + data + '\r'
                                        self.broadcast(self.server_socket, sock, "\r" + '[' + str(userName) + '] ' + data)
                                        writeToLogFile(chat_centralClient.userName, '[' + str(userName) + '] ' + data + '\r')
                                else:
                                    # peer is offline
                                    if (self.otherUserName != "No_User"):
                                        #print "Offline1 \n"
                                        self.otherUserName = getUserName(str(sock.getpeername()[0]), str(sock.getpeername()[1]), 'clientPort')
                                        self.offlineMessage(sock, self.otherUserName)
                            except:
                                # peer is offline
                                if (self.otherUserName != "No_User"):
                                    #print "Offline2 \n"
                                    self.otherUserName = getUserName(str(sock.getpeername()[0]), str(sock.getpeername()[1]), 'clientPort')
                                    self.offlineMessage(sock, self.otherUserName)
                                continue
                except:
                    continue
            #self.server_socket.close()                             -> Server socket kapatilmasinin duzenlenmesi lazim !!!

    # peer is offline
    def offlineMessage(self, sock, otherUserName):
        # remove the socket that's broken
        if sock in self.SOCKET_LIST:
            self.SOCKET_LIST.remove(sock)

        # at this stage, no data means probably the connection has been broken
        print "Peer ('%s') is offline\n" % otherUserName
        self.broadcast(self.server_socket, sock, "Peer ('%s') is offline\n" % otherUserName)
        writeToLogFile(chat_centralClient.userName, "Peer ('%s') is offline\n" % otherUserName)

    # broadcast chat messages to all connected clients
    def broadcast(self, server_socket, sock, message):
        for socket in self.SOCKET_LIST:
            # send the message only to peer
            if socket != server_socket and socket != sock:
                try:
                    socket.send(message)
                except:
                    # broken socket connection
                    socket.close()
                    # broken socket, remove it
                    if socket in self.SOCKET_LIST:
                        self.SOCKET_LIST.remove(socket)

    def kill(self):
        self.running = 0

class Chat_Client(threading.Thread):                                    # CHAT CLIENT THREAD
    def __init__(self, HOST, PORT, ConnectionType="LobyParticipant"):
        threading.Thread.__init__(self)
        self.HOST = str(HOST)
        self.PORT = int(PORT)            # baglanilacak server port
        self.ConnectionType = ConnectionType
        self.client_socket = None
        self.running = 1

    def run(self):                                                      # Starts 'CHAT SERVER THREAD'
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(2)
        # connect to remote host
        try:
            self.client_socket.connect((self.HOST, self.PORT))
        except:
            print 'Unable to connect'
            sys.exit()

        if(self.ConnectionType == "LobyLeader"):
            try:
                self.client_socket.sendall("CHAT_REQUEST")
            except:
                print "Chat request error ! \n"
                Exception

            response = ""
            while True:
                try:
                    response = self.client_socket.recv(1024)
                    break
                    #print "Response : " + str(response) + "\n"
                except:
                    continue

            if(response == "OK"):                   # Response is 'OK'
                global BUSY_CONDITION
                BUSY_CONDITION = True
                print ("OK -> " + str(self.client_socket.getpeername()))
                #writeToLogFile(chat_centralClient.userName, "\nOK -> " + str(self.client_socket.getpeername()) + "\n")
                serverData = str(chat_server.HOST) + "," + str(chat_server.PORT)
                self.client_socket.sendall(serverData)
            elif(response == "REJECT"):             # Response is 'REJECT'
                print ("REJECT -> " + str(self.client_socket.getpeername()))
                #writeToLogFile(chat_centralClient.userName, "\nREJECT -> " + str(self.client_socket.getpeername()) + "\n")
            elif(response == "BUSY"):               # Response is 'BUSY'
                print ("BUSY -> " + str(self.client_socket.getpeername()))
                #writeToLogFile(chat_centralClient.userName, "\nBUSY -> " + str(self.client_socket.getpeername()) + "\n")
            else:
                print "Incorrect response data !!! \n"

        else:
            #print "[Me] "
            print "\rConnected to 'loby'. You can start sending messages\n"
            #writeToLogFile(chat_centralClient.userName, 'Connected to remote host. You can start sending messages\n')
            while self.running == True:
                # Get the list sockets which are readable
                try:
                    read_sockets, write_sockets, error_sockets = select.select([self.client_socket], [], [], 0)
                    for sock in read_sockets:
                        try:
                            # incoming message from remote server, s
                            data = sock.recv(1024)
                            if not data:
                                print '\nDisconnected from chat server'
                                sys.exit()
                            else:
                                print data
                                writeToLogFile(chat_centralClient.userName, str(data) + "\n")

                        except:
                            # peer is offline
                            self.lobyOfflineMessage(sock)
                            sys.exit()
                except:
                    continue
                time.sleep(0)

    # lobyLeader is offline
    def lobyOfflineMessage(self, sock):
        lobyLeaderIp, lobyLeaderPort = sock.getpeername()
        # at this stage, no data means probably the connection has been broken
        lobyLeaderName = getUserName(lobyLeaderIp, lobyLeaderPort, 'serverPort')
        print "LobyLeader ('%s') is offline\n" % lobyLeaderName
        writeToLogFile(chat_centralClient.userName, "LobyLeader ('%s') is offline\n" % lobyLeaderName + "\n")
        time.sleep(3)
        sys.exit()

    def kill(self):
        self.running = 0


class Text_Input(threading.Thread):                     # TEXT_INPUT THREAD
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = 1

    def run(self):                                      # Starts 'TEXT_INPUT THREAD'
        chat_centralClient.isAlive()
        while self.running == True:
            text = raw_input('')
            try:
                chat_client.client_socket.sendall(text)
                writeToLogFile(chat_centralClient.userName, "Me: " + str(text) + "\n")
            except:
                Exception
            try:
                userName = getUserName(chat_server.HOST, chat_server.PORT, 'serverPort')
                chat_server.broadcast(chat_server.server_socket, chat_server.server_socket, "\r" + '[' + userName + '] ' + text)
                writeToLogFile(chat_centralClient.userName, '[' + userName + '] ' + text + "\n")
            except:
                Exception
            time.sleep(0)

    def kill(self):
        self.running = 0


class Chat_CentralClient(threading.Thread):                 # CENTRAL_CLIENT THREAD
    LOBY_USER_LIST = []


    def __init__(self):
        threading.Thread.__init__(self)
        self.HOST = 'localhost'
        self.PORT_TCP = 4004           # central tcp_port
        self.PORT_UDP = 4008           # central udp_port
        self.central_client_socket = None
        self.CONDITION = True
        self.startTime = 0
        self.endTime = 0
        self.running = 1

    def run(self):                                          # Starts 'CENTRAL_CLIENT THREAD'
        self.central_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.central_client_socket.settimeout(2)

        # connect to central_client_socket_tcp
        try:
            self.central_client_socket.connect((self.HOST, self.PORT_TCP))
        except:
            print 'Unable connection to central server unit'
            sys.exit()

        thread.start_new_thread(self._sayHello, ("helloThread",))

        while self.running == 1:

            while self.CONDITION:
                print ("\n---------------------------------------------------")
                choice = str(raw_input("\rPlease, press '1' for registration, '2' for join: "))
                print ("---------------------------------------------------\n")
                if choice == "1":
                    self._registry()
                    break
                elif choice == "2":
                    self._join()
                    self.CONDITION = False
                    self.startTime = time.time()
                    self.kill()
                    break
                else:
                    print "You entered a wrong choice ! \n "
            time.sleep(0)

    def _registry(self):                                                        # REGISTER OPERATION
        chat_centralClient.central_client_socket.sendall("register")
        print "Please enter your user name and password to register. \n"
        while True:
            self.userName = str(raw_input("UserName: "))
            self.password = str(raw_input("Password: "))

            if( (self.userName != "") and (self.password != "") ):          # daha fazla kontrol eklenebilir
                data = str(self.userName + "," + self.password)
                try:
                    chat_centralClient.central_client_socket.sendall(data)
                    processStatus = chat_centralClient.central_client_socket.recv(1024)

                    if processStatus == "Failure1":
                        print ("There is already a record for this username. Please, enter a new user. \n")
                        continue
                    elif processStatus == "Failure2":
                        print ("Registration failed. Please try again. \n")     # database kayit ekleme sorunu
                        continue
                    elif processStatus == "Success":
                        print ("The registration process is successful. You can 'join' \n")
                        break
                    else:
                        print "Incorrect data for 'register' \n"
                except:
                    print "Data sending error for 'register' \n"
                    Exception

            else:
                print "User Name or password can not be empty. Please try again. \n"

    def _join(self):                                                            # JOIN OPERATION
        chat_centralClient.central_client_socket.sendall("join")
        print "Please enter your user name and password to join. \n"
        while True:
            self.userName = str(raw_input("UserName: "))
            self.password = str(raw_input("Password: "))

            if( (self.userName != "") and (self.password != "") ):          # daha fazla kontrol eklenebilir
                data = str(self.userName + "," + self.password + "," + chat_server.HOST + "," + str(chat_server.PORT))

                try:
                    chat_centralClient.central_client_socket.sendall(data)
                    processStatus = chat_centralClient.central_client_socket.recv(1024)

                    if processStatus == "Failure3":
                        print ("User name or password is incorrect. Please, try again. \n")
                        continue
                    elif processStatus == "Failure4":
                        print ("Join failed. Please try again. \n")         # database kayit ekleme sorunu
                        continue
                    elif processStatus == "Success":
                        global JOIN_STATUS
                        print ("\nThe 'join' process is successful. You can 'search' \n")
                        JOIN_STATUS = True
                        self.PEER_CONDITION = False

                        #data = str(chat_centralClient.central_client_socket.recv(4096))
                        #onlineUserList = data[1:-1].replace("(", "").replace(",),", "").replace(",)", "").replace("'", "").split(" ")
                        generateLogFileDirectory(self.userName)

                        global HELLO_STATUS
                        HELLO_STATUS = True
                        while True:
                            print ("\n-----------------------------------------------------------------------------")
                            onlineUserListChoice = str(raw_input("\rPress '1' for 'Online User List', '2' for search, '3' for starting to chat: "))
                            print ("-----------------------------------------------------------------------------\n")
                            if (onlineUserListChoice == "1"):
                                chat_centralClient.central_client_socket.sendall("onlineUserList")
                                time.sleep(0.2)
                                data = str(chat_centralClient.central_client_socket.recv(4096))

                                onlineUserList = data[1:-1].replace("(", "").replace(")", "").replace(",", "").replace("'", "").split(" ")

                                print ("\t\t<<< ONLINE USER LIST >>>\r")
                                print ("----------------------------------------\n")
                                print ("\t UserName    IpAddress    Port\n")

                                iteration = 1
                                userAllInfo = ""
                                for userInfo in onlineUserList:
                                    if (iteration%3) == 0:
                                        userAllInfo = userAllInfo + userInfo + ",   "
                                        print "\t" + userAllInfo
                                        userAllInfo = ""
                                    else:
                                        userAllInfo = userAllInfo + userInfo + ",   "
                                    iteration += 1
                                continue

                            elif (onlineUserListChoice == "2"):
                                otherUserIpAddressAndPortList = self._search()
                                while True:
                                    lobyUserListAddChoice = str(raw_input("Do you want to add the user to your conversation list? ['Yes', 'No'] "))
                                    if(lobyUserListAddChoice == "Yes"):
                                        self.LOBY_USER_LIST.append(otherUserIpAddressAndPortList)
                                        self.PEER_CONDITION = True
                                        break
                                    elif(lobyUserListAddChoice == "No"):
                                        break
                                    else:
                                        print("Wrong input choice. You have to enter only 'Yes' or 'No' \n")
                                continue
                            elif (onlineUserListChoice == "3"):
                                if(not self.PEER_CONDITION):
                                    break

                                if( len(self.LOBY_USER_LIST) == 0):
                                    print("The number of selected users can not be 'zero'. \n")
                                else:
                                    global LOBY_LEADER_STATUS
                                    LOBY_LEADER_STATUS = True
                                    # Kullanici chat lesme islemini baslat... Bagşanmak istedigi peer lara istek yolla
                                    for otherUserIpAndPort in self.LOBY_USER_LIST:
                                        chat_client = Chat_Client(str(otherUserIpAndPort[0]), int(otherUserIpAndPort[1]), "LobyLeader")
                                        chat_client.start()
                                    break
                            else:
                                print("Wrong input choice. You have to enter only '1' or '2' \n")

                        break
                    else:
                        print "Incorrect data for 'join' \n"

                except:
                    print "Data sending error for 'join' \n"
                    Exception
            else:
                print "User Name or password can not be empty. Please try again. \n"

    def _search(self):                                                      # SEARCH OPERATION
        chat_centralClient.central_client_socket.sendall("search")
        print "Please enter a user name to search. \n"

        otherUserIpAddressAndPortList = []

        while True:
            self.otherUserName = str(raw_input("UserName: "))

            if( self.otherUserName != "" ):          # daha fazla kontrol eklenebilir
                try:
                    chat_centralClient.central_client_socket.sendall(self.otherUserName)
                    processStatus = chat_centralClient.central_client_socket.recv(1024)

                    if processStatus == "Failure5":
                        print ("A user record with this name could NOT be FOUND. Please, enter a other 'userName' \n")
                        continue
                    elif processStatus == "Failure6":
                        print ("'" + self.otherUserName + "' is offline. Please, enter a other 'userName' \n")         # database kayit ekleme sorunu
                        continue
                    elif processStatus == "Success":
                        otherUserIpAddressAndPortData = chat_centralClient.central_client_socket.recv(1024)
                        otherUserIpAddress, otherUserPort = otherUserIpAddressAndPortData.split(',')
                        otherUserIpAddressAndPortList = [otherUserIpAddress, otherUserPort]
                        print ("\nUserIp: " + otherUserIpAddress + "\t Port: " + otherUserPort)
                        break
                    else:
                        print "Incorrect data for 'search' \n"
                except:
                    print "Data sending error for 'search \n'"
                    Exception
            else:
                print "User Name or password can not be empty. Please try again. \n"

        return otherUserIpAddressAndPortList

    def _sayHello(self, threadName):                                        # HELLO OPERATION FOR 'CENTRAL SERVER' [UDP]
        # connect to central_client_socket_udp
        self.central_client_socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            if(HELLO_STATUS):
                self.endTime = time.time()
                elapsedTime = int(self.endTime - self.startTime)

                if (elapsedTime % 10) == 0:
                    #print "Hello diyomm \n"
                    #userName = getUserName(chat_server.HOST, chat_server.PORT, 'serverPort')
                    data = str(self.userName) + "," + "Hello"
                    self.central_client_socket_udp.sendto(data, (self.HOST, self.PORT_UDP))
                    time.sleep(2)
            time.sleep(0.1)

    def clearLobyUserList(self):
        self.LOBY_USER_LIST = []

    def kill(self):
        self.running = 0

# getUserName from 'CENTRAL SERVER'
def getUserName(userIpAddr, userPort, type):    # type='serverPort' type='clientPort'
    chat_centralClient.central_client_socket.sendall("userName")
    data = str(userIpAddr) + "," + str(userPort) + "," + str(type)
    time.sleep(0.3)
    chat_centralClient.central_client_socket.sendall(data)
    userName = chat_centralClient.central_client_socket.recv(1024)

    if userName == "Failure7":
        return "No_User"
    else:
        return userName

# generateLogFileDirectory into 'LOCAL'
def generateLogFileDirectory(userName):
    directoryName = "LogFile_" + str(userName)
    try:
        if (not os.path.isdir(directoryName)):
            os.mkdir(directoryName)
    except:
        print "Log file generation error ! \n"

    writeToLogFile(chat_centralClient.userName, "\n\n----------------------------------------------------------------------\n")
    writeToLogFile(chat_centralClient.userName, "\t\t" + getDateTime())
    writeToLogFile(chat_centralClient.userName, "\n----------------------------------------------------------------------\n")

# writeToLogFile into 'LOCAL_FILE'   ->> LOGGING OPERATION
def writeToLogFile(userName, data):
    fileName = "LogFile_" + str(userName) + "\\" + str(userName) + ".txt"

    with open(fileName, "a") as f:
        f.write(data)

# getDateTime ->> realTime
def getDateTime():
    _date = datetime.datetime.now()
    date = datetime.datetime.ctime(_date)
    return str(date)

if __name__ == "__main__":                                      # PEER THREAD SERVICES
    chat_centralClient = Chat_CentralClient()
    chat_server = Chat_Server()
    chat_client = Chat_Client("", 0, "LobyParticipant")
    text_input = Text_Input()

    chat_server.start()  # baglanma isteklerini dinler            ** ** ** ** **
    chat_centralClient.start()      # merkezi server ile iletisimi saglar
from sys import argv, stdout
from threading import Thread
from PolicyBasedClient import PolicyBasedClient
import json
from os.path import exists
import socket
from constants import *

if len(argv) < 4:
    print("Invalid arguments, using default ones")
    playerName = "Test"
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])


client = PolicyBasedClient()
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    if client.registerToGame(s, ip, port, playerName):
        print("Waiting command (ready or exit)")
        validCommand = False
        closePlayer = False
        dataOk = False
        while not validCommand:
            stdout.flush()
            command = input()
            if command == "ready":
                print("Waiting server response...")
                dataOk, nPlayers = client.ready(s)
                validCommand = True
            elif command == "exit":
                closePlayer = True
                validCommand = True

        if dataOk:
            if exists(f"bestParams_{nPlayers}"):
                f = open(f"bestParams_{nPlayers}", "r")
                params = f.readline().split("#")
                playTh = json.loads(params[0])
                thReducer = json.loads(params[1])
                bonusKnownCard = float(params[2])
                nTurns = int(params[3])

                client.PLAY_THRESHOLD = playTh
                client.TH_REDUCER = thReducer
                client.BONUS_KNOWN_CARD = bonusKnownCard
                client.N_TURNS = nTurns

                f.close()

            print(f"Using {client.toString()}")
            Thread(target=client.start, args=[s]).start()
            print("Player is running, press any key to stop")
            command = input()
            exit(0)
        else:
            if closePlayer:
                exit(0)
            else:
                print("Error during ready")
                exit(-1)
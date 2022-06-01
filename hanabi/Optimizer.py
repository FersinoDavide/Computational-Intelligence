from asyncio import constants
from multiprocessing import Semaphore
from sys import argv
import random
import subprocess
import socket
from threading import Thread
from threading import Lock
from time import sleep
from constants import *
from PolicyBasedClient import PolicyBasedClient


if len(argv) != 2:
    print("Usage Optimizer.py [NUM_PLAYERS]")
    exit(-1)
else:
    N_PLAYERS = int(argv[1])

TOURNAMENT_WINNERS = 10
MUTATION_FACTOR = 0.2
MUTATION_CHANCE = 0.8
MUTATION_CHANCE_N_TURNS = 0.5
MUTATION_DIRECTION_CHANCE = 0.5

GAMES_PER_CLIENT = 100
MAX_GAMES_IN_PARALLEL = 10

MIN_IMPROVEMENT = 0.1
MAX_GENERATIONS_WO_INCREMENT = 5
MAX_MUTATION_FACTOR_CHANGE = 3

def getFreePort(serversPorts):
    for p in serversPorts:
        if p['busy'] == False:
            return p
    return None

def generateChildren(parent):
    children = []

    #   MUTATION ON PLAY TH
    oldPlayTh = list(parent.PLAY_THRESHOLD)

    #   MUTATION ON FIRST PLAY TH
    newPlayTh = list(oldPlayTh)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newPlayTh[0] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newPlayTh[0] += mutationValue
        newPlayTh[0] = max(0, newPlayTh[0])
        newPlayTh[0] = min(1, newPlayTh[0])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.PLAY_THRESHOLD = newPlayTh
    children.append(c)

    #   MUTATION ON SECOND PLAY TH
    newPlayTh = list(oldPlayTh)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newPlayTh[1] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newPlayTh[1] += mutationValue
        newPlayTh[1] = max(0, newPlayTh[1])
        newPlayTh[1] = min(1, newPlayTh[1])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.PLAY_THRESHOLD = newPlayTh
    children.append(c)

    #   MUTATION ON THIRD PLAY TH
    newPlayTh = list(oldPlayTh)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newPlayTh[2] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newPlayTh[2] += mutationValue
        newPlayTh[2] = max(0, newPlayTh[2])
        newPlayTh[2] = min(1, newPlayTh[2])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.PLAY_THRESHOLD = newPlayTh
    children.append(c)

    #   MUTATION ON TH REDUCER
    oldThReducer = list(parent.TH_REDUCER)

    #   MUTATION ON FIRST TH REDUCER
    newThReducer = list(oldThReducer)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newThReducer[0] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newThReducer[0] += mutationValue
        newThReducer[0] = max(0, newThReducer[0])
        newThReducer[0] = min(1, newThReducer[0])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.TH_REDUCER = newThReducer
    children.append(c)

    #   MUTATION ON SECOND TH REDUCER
    newThReducer = list(oldThReducer)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newThReducer[1] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newThReducer[1] += mutationValue
        newThReducer[1] = max(0, newThReducer[1])
        newThReducer[1] = min(1, newThReducer[1])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.TH_REDUCER = newThReducer
    children.append(c)

    #   MUTATION ON THIRD TH REDUCER
    newThReducer = list(oldThReducer)
    if random.random() < MUTATION_CHANCE:
        mutationModule = newThReducer[2] * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newThReducer[2] += mutationValue
        newThReducer[2] = max(0, newThReducer[2])
        newThReducer[2] = min(1, newThReducer[2])

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.TH_REDUCER = newThReducer
    children.append(c)

    #   MUTATION ON BONUS KNOWN CARD
    newBonusKnownCard = parent.BONUS_KNOWN_CARD
    if random.random() < MUTATION_CHANCE:
        mutationModule = newBonusKnownCard * MUTATION_FACTOR
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newBonusKnownCard += mutationValue
        newBonusKnownCard = max(0, newBonusKnownCard)
        newBonusKnownCard = min(1, newBonusKnownCard)

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.BONUS_KNOWN_CARD = newBonusKnownCard
    children.append(c)

    #   MUTATION ON N_TURNS
    newNTurns = parent.N_TURNS
    if random.random() < MUTATION_CHANCE_N_TURNS:
        mutationModule = 1
        if random.random() < MUTATION_DIRECTION_CHANCE:
            mutationValue = mutationModule 
        else:
            mutationValue = -mutationModule
        
        newNTurns += mutationValue
        newNTurns = max(0, newNTurns)
        newNTurns = min(8, newNTurns)

    c = PolicyBasedClient(maxGames=GAMES_PER_CLIENT)
    c.N_TURNS = newNTurns
    children.append(c)

    return children

def startNewGame(client, clientsMarks, clientIndex, gameLock, gamesSemaphore, logFile):
    gamesSemaphore.acquire()

    gameLock.acquire()
    logFile.write(f"Starting client {clientIndex}\n")
    logFile.flush()
    p = getFreePort(serversPorts)
    if p is None:
        logFile.write("Fatal error, no free port found\n")
        logFile.flush()
        exit(-1)

    p['busy'] = True
    gameLock.release()

    server = subprocess.Popen(['python', 'server.py', HOST, str(p['port'])])
    sleep(1)

    clientsInGame = []
    threads = []

    for i in range(N_PLAYERS):
        clientsInGame.append(client.clone())

    sockets = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in range(len(clientsInGame))]
    results = [None for _ in range(len(clientsInGame))]
    for i, c in enumerate(clientsInGame):
        s = sockets[i]
        c.registerToGame(s, HOST, p['port'], "client" + str(i))

    for i, c in enumerate(clientsInGame):
        s = sockets[i]
        t = Thread(target=c.ready, args=[s])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    threads.clear()
    for i, c in enumerate(clientsInGame):
        s = sockets[i]
        t = Thread(target=c.start, args=[s, results, i])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    clientScores = results[0]
    mark = sum(clientScores) / len(clientScores)
    
    server.kill()
    sleep(1)

    gameLock.acquire()
    p['busy'] = False
    clientsMarks[clientIndex] = mark
    logFile.write(f"End client {clientIndex} mark {mark}\n")
    logFile.flush()
    gameLock.release()

    gamesSemaphore.release()

def popBest(clientsInTournament, clientsMarks):
    bestClientIndex = clientsMarks.index(max(clientsMarks))
    bestMark = clientsMarks.pop(bestClientIndex)
    bestClient = clientsInTournament.pop(bestClientIndex)

    return bestClient, bestMark

f = open(f"report_{N_PLAYERS}.txt", "w")
resultReport = open(f"bestParamsReport_{N_PLAYERS}.txt", "w")

startingPort = PORT
serversPorts = [None for _ in range(MAX_GAMES_IN_PARALLEL)]
for i in range(MAX_GAMES_IN_PARALLEL):
    serversPorts[i] = {"port" : startingPort + i, "busy" : False}


gameLock = Lock()
gamesSemaphore = Semaphore(MAX_GAMES_IN_PARALLEL)

generationsWoIncrements = 0
mutationFactorChange = 0

generationsCount = 0

bestMark = 0
bestClient = PolicyBasedClient()

while mutationFactorChange < MAX_MUTATION_FACTOR_CHANGE:
    tournamentWinners = [bestClient for _ in range(TOURNAMENT_WINNERS)]
    generationsWoIncrements = 0
    clientsInTournament = []
    while generationsWoIncrements < MAX_GENERATIONS_WO_INCREMENT:
        generationsCount += 1
        for i in range(TOURNAMENT_WINNERS):
            clientsInTournament += generateChildren(tournamentWinners[i])

        clientsMarks = [None for _ in range(len(clientsInTournament))]
        games = []
        for clientNumber, client in enumerate(clientsInTournament):
            t = Thread(target=startNewGame, args=[client, clientsMarks, clientNumber, gameLock, gamesSemaphore, f])
            games.append(t)
            t.start()

        for game in games:
            game.join()

        tournamentWinners.clear()
        generationBestClient, generationBestMark = popBest(clientsInTournament, clientsMarks)
        tournamentWinners.append(generationBestClient)
        for _ in range(TOURNAMENT_WINNERS - 1):
            client, mark = popBest(clientsInTournament, clientsMarks)
            tournamentWinners.append(client)

        improvementValue = generationBestMark - bestMark
        if improvementValue > MIN_IMPROVEMENT:
            bestMark = generationBestMark
            bestClient = generationBestClient
            resultReport.write(f"\nGeneration {generationsCount}: " + bestClient.paramsToString())
            resultReport.flush()
            generationsWoIncrements = 0
        else:
            generationsWoIncrements += 1

    MUTATION_FACTOR = MUTATION_FACTOR / 2
    MUTATION_CHANCE_N_TURNS = MUTATION_CHANCE_N_TURNS / 2
    mutationFactorChange += 1

f.close()
resultReport.close()

resultFile = open(f"bestParams_{N_PLAYERS}.txt", "w")
resultFile.write(bestClient.paramsToString())
resultFile.close()
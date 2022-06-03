from copy import deepcopy
import GameData
from constants import *
from game import Card

STATUSES = ["Lobby", "Game", "GameHint"]

class Client:
    def __init__(self, maxGames=None):
        self.run = True
        self.status = STATUSES[0]
        self.run = True

        self.isMyTurn = False
        self.waitingResponse = False

        self.board = dict()
        self.board['playedCards'] = []
        self.board['discardedCards'] = []
        self.board['usedNoteTokens'] = 8
        self.board['usedStormTokens'] = 0

        self.cardsDrawn = 0
        
        self.gameCount = 0
        self.maxGames = maxGames
        self.gameScores = []

    def registerToGame(self, socket, ip, port, playerName):
        self.myIP = ip
        self.myPORT = port
        self.myName = playerName

        request = GameData.ClientPlayerAddData(playerName)
        socket.connect((ip, port))
        socket.send(request.serialize())
        data = socket.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)

        return type(data) is GameData.ServerPlayerConnectionOk

    def ready(self, socket):
        socket.send(GameData.ClientPlayerStartRequest(self.myName).serialize())
        dataOk, invalidAction = self.listen(socket)
        return dataOk, len(self.allPlayersName)

    def initHand(self, players):
        self.myHand = []
        
        cardsInHand = 5
        if len(players) >= 4:
            cardsInHand = 4

        for _ in players:
            for _ in range(cardsInHand):
                self.cardsDrawn += 1
            
        for _ in range(cardsInHand):
            self.myHand.append(Card(None, None, None))

        self.othersCardsKnowledge = dict()
        for player in players:
            playerHand = []
            for _ in range(cardsInHand):
                playerHand.append(Card(None, None, None))
            self.othersCardsKnowledge[player] = playerHand

    def buildDiscardCommand(self, idx=None):
        return f"discard {idx}"

    def buildPlayCommand(self, idx=None):
        return f"play {idx}"

    def buildHintCommand(self, player, type, value):
        # TODO some checks on fields
        return f"hint {type} {player} {value}"

    def elaborateCommand(self, command, socket):
        err = False

        if command.split(" ")[0] == "discard" and self.status == STATUSES[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                socket.send(GameData.ClientPlayerDiscardCardRequest(self.myName, cardOrder).serialize())
            except:
                err = True

        elif command.split(" ")[0] == "play" and self.status == STATUSES[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                socket.send(GameData.ClientPlayerPlayCardRequest(self.myName, cardOrder).serialize())
            except:
                err = True

        elif command.split(" ")[0] == "hint" and self.status == STATUSES[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    err = True

                if not err:
                    value = command.split(" ")[3].lower()
                    if t == "value":
                        value = int(value)
                        if int(value) > 5 or int(value) < 1:
                            err = True
                    else:
                        if value not in ["green", "red", "blue", "yellow", "white"]:
                            err = True
                    
                    if not err:
                        socket.send(GameData.ClientHintData(self.myName, destination, t, value).serialize())
            except:
                err = True

        return err

    def refreshGameInfo(self, socket):
        socket.send(GameData.ClientGetGameStateRequest(self.myName).serialize())

    def listen(self, socket):
        dataOk = False
        invalidAction = None
        needRefresh = False

        data = socket.recv(DATASIZE)
        if not data:
            return dataOk, invalidAction

        data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            data = socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            socket.send(GameData.ClientPlayerReadyData(self.myName).serialize())
            self.status = STATUSES[1]
            self.allPlayersName = data.players
            self.initHand(data.players)
            needRefresh = True

        if type(data) is GameData.ServerGameStateData:
            dataOk = True

            if not self.waitingResponse:
                if data.currentPlayer == self.myName:
                    self.isMyTurn = True

                self.allPlayers = data.players
                self.board['usedNoteTokens'] = data.usedNoteTokens
                self.board['usedStormTokens'] = data.usedStormTokens
                self.board['playedCards'] = deepcopy(data.tableCards)
                self.board['discardedCards'] = deepcopy(data.discardPile)

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            invalidAction = data.message
            needRefresh = True
            self.waitingResponse = False

        if type(data) is GameData.ServerActionValid:
            #discard
            dataOk = True
            self.waitingResponse = False

            if data.player == self.myName:
                needRefresh = True

            if data.lastPlayer == self.myName:
                self.myHand.pop(data.cardHandIndex)
                if len(self.myHand) < data.handLength:
                    self.myHand.append(Card(None, None, None))
                    self.cardsDrawn += 1
            else:
                self.othersCardsKnowledge[data.lastPlayer].pop(data.cardHandIndex)
                if len(self.othersCardsKnowledge[data.lastPlayer]) < data.handLength:
                    self.othersCardsKnowledge[data.lastPlayer].append(Card(None, None, None))
                    self.cardsDrawn += 1
        if type(data) is GameData.ServerPlayerMoveOk:
            #play
            dataOk = True
            self.waitingResponse = False

            if data.player == self.myName:
                needRefresh = True

            if data.lastPlayer == self.myName:
                self.myHand.pop(data.cardHandIndex)
                if len(self.myHand) < data.handLength:
                    self.myHand.append(Card(None, None, None))
                    self.cardsDrawn += 1
            else:
                self.othersCardsKnowledge[data.lastPlayer].pop(data.cardHandIndex)
                if len(self.othersCardsKnowledge[data.lastPlayer]) < data.handLength:
                    self.othersCardsKnowledge[data.lastPlayer].append(Card(None, None, None))
                    self.cardsDrawn += 1
        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            self.waitingResponse = False
            #print("Strike")
            if data.player == self.myName:
                needRefresh = True

            if data.lastPlayer == self.myName:
                self.myHand.pop(data.cardHandIndex)
                if len(self.myHand) < data.handLength:
                    self.myHand.append(Card(None, None, None))
                    self.cardsDrawn += 1
            else:
                self.othersCardsKnowledge[data.lastPlayer].pop(data.cardHandIndex)
                if len(self.othersCardsKnowledge[data.lastPlayer]) < data.handLength:
                    self.othersCardsKnowledge[data.lastPlayer].append(Card(None, None, None))
                    self.cardsDrawn += 1
        if type(data) is GameData.ServerHintData:
            dataOk = True
            self.waitingResponse = False

            if data.player == self.myName:
                needRefresh = True

            if data.destination == self.myName:
                for cardIndex in data.positions:
                    if data.type == 'value':
                        self.myHand[cardIndex].value = data.value
                    else:
                        self.myHand[cardIndex].color = data.value
            else:
                for cardIndex in data.positions:
                    if data.type == 'value':
                        self.othersCardsKnowledge[data.destination][cardIndex].value = data.value
                    else:
                        self.othersCardsKnowledge[data.destination][cardIndex].color = data.value

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            invalidAction = data.data
            needRefresh = True
            self.waitingResponse = False

        if type(data) is GameData.ServerGameOver:
            dataOk = True
            needRefresh = True
            self.waitingResponse = False
            self.cardsDrawn = 0
            self.initHand(self.allPlayersName)

            self.gameCount += 1
            print(f"Game {self.gameCount}, score: {data.score}")
            self.gameScores.append(data.score)
            if self.maxGames is not None and self.gameCount >= self.maxGames:
                needRefresh = False
                self.run = False

        if needRefresh:
            self.refreshGameInfo(socket)

        return dataOk, invalidAction
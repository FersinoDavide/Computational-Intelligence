from socket import gaierror
from numpy import result_type
from Client import STATUSES
from Client import Client
import Policy

class PolicyBasedClient(Client):
    def __init__(self, executionOrder=Policy.DEFAULT_ORDER, maxGames=None):
        super().__init__(maxGames)
        self.executionOrder = executionOrder

        self.PLAY_THRESHOLD = [0.5, 0.7, 0.9]
        self.TH_REDUCER = [0.5, 0.75, 1]
        self.BONUS_KNOWN_CARD = 0.1
        self.N_TURNS = 1
        #self.DISCARD_THRESHOLD = 0.5

    def start(self, socket, results=None, i=None):
        if self.status != STATUSES[1]:
            return
        
        while self.run:
            dataOk, invalidAction = self.listen(socket)
            if invalidAction is not None:
                print(f"Last action is invalid: {invalidAction}")
            if dataOk and self.isMyTurn:
                for policyIndex in self.executionOrder:
                    command = Policy.POLICIES[policyIndex](self)
                    if command is not None:
                        #print(command)
                        self.elaborateCommand(command, socket)
                        self.isMyTurn = False
                        self.waitingResponse = True
                        break

        if results is not None:
            results[i] = self.gameScores

    def clone(self):
        myClone = PolicyBasedClient(maxGames=self.maxGames)
        myClone.PLAY_THRESHOLD = self.PLAY_THRESHOLD
        myClone.TH_REDUCER = self.TH_REDUCER
        myClone.BONUS_KNOWN_CARD = self.BONUS_KNOWN_CARD
        myClone.N_TURNS = self.N_TURNS

        return myClone

    def toString(self):
        return f"Client: {self.PLAY_THRESHOLD} {self.TH_REDUCER} {self.BONUS_KNOWN_CARD} {self.N_TURNS}"

    def paramsToString(self):
        return f"{self.PLAY_THRESHOLD}#{self.TH_REDUCER}#{self.BONUS_KNOWN_CARD}#{self.N_TURNS}"

from Client import STATUSES
from Client import Client
import Policy

class PolicyBasedClient(Client):
    def __init__(self, executionOrder=Policy.DEFAULT_ORDER):
        super().__init__()
        self.executionOrder = executionOrder

    def start(self, socket):
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

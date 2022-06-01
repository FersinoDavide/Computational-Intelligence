import random
from copy import deepcopy

from matplotlib.style import available


N_CARDS = {1 : 15, 2 : 10, 3 : 10, 4 : 10, 5 : 5}
COLORS = ["green", "red", "blue", "yellow", "white"]
N_COLORS = 5
MAX_NOTE_TOKENS = 8
POSSIBLE_HINTS = {1 : "value", 2 : "value", 3 : "value", 4 : "value", 5 : "value", "red" : "color", "blue" : "color", "green" : "color", "white" : "color", "yellow" : "color"}

def isKnown(card):
    return card.value is not None and card.color is not None

def isFullyUnknown(card):
    return card.value is None and card.color is None

def isPlayable(card, playedCards):
    if not isKnown(card):
        return False

    if len(playedCards[card.color]) == 0:
        return card.value == 1

    stackMaxCard = max((playedCards[card.color]), key=(lambda c: c.value), default=None)
    
    return (card.value - 1) == stackMaxCard.value

def isUseless(card, discardedCards, playedCards):
    canBePlayedInFuture = True
    if isKnown(card):
        stackMaxCard = max((playedCards[card.color]), key=(lambda c: c.value), default=None)
        if stackMaxCard is None:
            stackCardValue = 0
        else:
            stackCardValue = stackMaxCard.value

        if stackCardValue >= card.value:
            canBePlayedInFuture = False
        else:
            positionDiff = card.value - stackCardValue
            for offset in range(positionDiff):
                soughtValue = stackCardValue + offset + 1
                counter = 0
                for discardedCard in discardedCards:
                    if discardedCard.color == card.color and discardedCard.value == soughtValue:
                        counter += 1
                
                if N_CARDS[soughtValue] / N_COLORS == counter:
                    canBePlayedInFuture = False
    else:
        if not isFullyUnknown(card):
            valueCanBeUseful = False
            if card.value is not None:
                for color in playedCards:
                    stackMaxCard = max((playedCards[color]), key=(lambda c: c.value), default=None)
                    if stackMaxCard:
                        if stackMaxCard.value < card.value:
                            valueCanBeUseful = True
                    else:
                        valueCanBeUseful = True

            colorCanBeUseful = False
            if card.color is not None:
                if len(playedCards[card.color]) < 5:
                    colorCanBeUseful = True

            canBePlayedInFuture = valueCanBeUseful or colorCanBeUseful
    
    return not canBePlayedInFuture

def playIfSure(client):
    for i, card in enumerate(client.myHand):
        if isPlayable(card, client.board['playedCards']):
            #print("Sure Play " + card.toClientString())
            return client.buildPlayCommand(i)

    return None

def discardIfSure(client):
    if canDiscard(client.board['usedNoteTokens']):
        for i, card in enumerate(client.myHand):
            if isUseless(card, client.board['discardedCards'], client.board['playedCards']):
                #print("Sure Discard " + card.toClientString())
                return client.buildDiscardCommand(i)

    return None

def canDiscard(usedNoteTokens):
    return not usedNoteTokens == 0

def canHint(usedNoteTokens):
    return not usedNoteTokens == MAX_NOTE_TOKENS

def getPlayerAbsolutePosition(allPlayers, myName, posDiff):
    playerPos = None
    for i, player in enumerate(allPlayers):
        if player.name == myName:
            playerPos = i

    if playerPos is None:
        return None
    hintPos = (playerPos + posDiff) % len(allPlayers)
    return hintPos

def generateHint(posDiff, type, value):
    def fun(client):
        if canHint(client.board['usedNoteTokens']):
            hintPos = getPlayerAbsolutePosition(client.allPlayers, client.myName, posDiff)
            hintPlayer = client.allPlayers[hintPos].name

            if hintPlayer == client.myName:
                return None

            hintPlayerCardsKnowledge = client.othersCardsKnowledge[hintPlayer]
            validHint = False
            usefulHint = False
            
            if type == 'value':
                intValue = int(value)

                knownCardsNumber = 0
                for x in filter(cardValueFilter(intValue), hintPlayerCardsKnowledge):
                    knownCardsNumber += 1
                
                cardsNumber = 0
                for card in client.allPlayers[hintPos].hand:
                    if card.value == intValue:
                        cardsNumber += 1
                        validHint = True

                if knownCardsNumber < cardsNumber:
                    usefulHint = True

            else:
                knownCardsNumber = 0
                for x in filter(cardColorFilter(value), hintPlayerCardsKnowledge):
                    knownCardsNumber += 1

                cardsNumber = 0
                for card in client.allPlayers[hintPos].hand:
                    if card.color == value:
                        cardsNumber += 1
                        validHint = True

                if knownCardsNumber < cardsNumber:
                    usefulHint = True

            if validHint and usefulHint:
                return client.buildHintCommand(hintPlayer, type, value)

        return None
    
    return fun

def cardValueFilter(value):
    def fun(card):
        return card.value == value
    return fun

def cardColorFilter(color):
    def fun(card):
        return card.color == color
    return fun

def discardRandom(client):
    if canDiscard(client.board['usedNoteTokens']):
        candidateCard = -1
        for i, card in enumerate(client.myHand):
            if isFullyUnknown(card):
                return client.buildDiscardCommand(i)
            
            if candidateCard == -1 or candidateKnowledge == True:
                candidateCard = i
                candidateKnowledge = isKnown(card)

        return client.buildDiscardCommand(candidateCard)
    return None

def playRandom(client):
    randIndex = random.randrange(0, len(client.myHand))
    #print("Random Play")
    return client.buildPlayCommand(randIndex)

def getHandValue(hand, client, hintPlayerName):
    handValue = 0
    for card in hand:
        cardValue = 0
        if isPlayable(card, client.board['playedCards']):
            cardValue = 1
        elif isUseless(card, client.board['discardedCards'], client.board['playedCards']):
            cardValue = 1
        else:
            playTh = getPlayThreshold(client, card, hintPlayerName)
            discardTh = getDiscardThreshold(client, card, hintPlayerName)

            cardValue = (playTh + discardTh) / 2
            if isKnown(card):
                cardValue += client.BONUS_KNOWN_CARD
            cardValue = min(1, cardValue)

        handValue += cardValue

    return handValue

def generateUsefulHint(client):
    if canHint(client.board['usedNoteTokens']):
        hintPosition = getPlayerAbsolutePosition(client.allPlayers, client.myName, 1)
        hintPlayerHand = client.allPlayers[hintPosition].hand
        hintPlayerHandKnowledge = client.othersCardsKnowledge[client.allPlayers[hintPosition].name]
        hintPlayerName = client.allPlayers[hintPosition].name

        handValueBeforeHint = getHandValue(hintPlayerHandKnowledge, client, hintPlayerName)

        availableNoteTokens = MAX_NOTE_TOKENS - client.board['usedNoteTokens']
        nTurns = min(client.N_TURNS, availableNoteTokens)
        handValueAfterHint, hintType, hintValue = getHintForHandMaxValue(hintPlayerHand, hintPlayerHandKnowledge, client, hintPlayerName, nTurns)

        if handValueAfterHint > handValueBeforeHint and hintType is not None and hintValue is not None:
            #print(f"Hint {hintPlayerName}: {hintType} {hintValue}")
            return client.buildHintCommand(hintPlayerName, hintType, hintValue)
    
    return None

def getHintForHandMaxValue(hand, handKnowledge, client, hintPlayerName, nTurns):
    if nTurns == 0:
        return getHandValue(handKnowledge, client, hintPlayerName), None, None

    bestHandValueAfterHint = 0
    bestHintValue = None
    bestHintType = None
    for hintValue in POSSIBLE_HINTS:
        hintType = POSSIBLE_HINTS[hintValue]
        validHint = False

        handKnowledgeAfterHint = deepcopy(handKnowledge)
        if hintType == "value":
            for i, card in enumerate(hand):
                if card.value == hintValue:
                    handKnowledgeAfterHint[i].value = card.value
                    validHint = True
        else:
            for i, card in enumerate(hand):
                if card.color == hintValue:
                    handKnowledgeAfterHint[i].color = card.color
                    validHint = True
        
        if validHint:
            handValueAfterHint, _, _ = getHintForHandMaxValue(hand, handKnowledgeAfterHint, client, hintPlayerName, nTurns - 1)
            if handValueAfterHint > bestHandValueAfterHint:
                bestHandValueAfterHint = handValueAfterHint
                bestHintValue = hintValue
                bestHintType = hintType

    return bestHandValueAfterHint, bestHintType, bestHintValue

def getDiscardThreshold(client, card, hintPlayer=None):
    discardTh = 0
    if isKnown(card):
        availableCardOfThisType = N_CARDS[card.value] / len(COLORS)

        discardedCount = 0
        for x in filter(lambda c: c.value == card.value and c.color == card.color, client.board['discardedCards']):
            discardedCount += 1

        discardTh = (availableCardOfThisType - discardedCount - 1) / availableCardOfThisType
    elif not isFullyUnknown(card):
        if card.value is not None:
            maxCardsPerColor = N_CARDS[card.value] / len(COLORS)
            availableCardsPerColor = {"green" : maxCardsPerColor, "red" : maxCardsPerColor, "blue" : maxCardsPerColor, "yellow" : maxCardsPerColor, "white" : maxCardsPerColor}
            for discardedCard in client.board['discardedCards']:
                if discardedCard.value == card.value:
                    availableCardsPerColor[discardedCard.color] -= 1

            availableSlotsProb = dict()
            for color in client.board['playedCards']:
                stackMaxCard = max((client.board['playedCards'][color]), key=(lambda c: c.value), default=None)
                if stackMaxCard is not None and stackMaxCard.value >= card.value:
                    availableSlotsProb[color] = 1
                else:
                    slotProb = (availableCardsPerColor[color] - 1) / maxCardsPerColor
                    availableSlotsProb[color] = slotProb
                
            discardTh = sum(availableSlotsProb.values()) / len(availableSlotsProb)
        elif card.color is not None:
            stackMaxCard = max((client.board['playedCards'][card.color]), key=(lambda c: c.value), default=None)
            if stackMaxCard is None:
                stackMaxCardValue = 0
            else:
                stackMaxCardValue = stackMaxCard.value

            availableCardsPerValue = dict()
            for key in N_CARDS:
                availableCardsPerValue[key] = N_CARDS[key] / len(COLORS)

            for discardedCard in client.board['discardedCards']:
                if discardedCard.color == card.color:
                    availableCardsPerValue[discardedCard.value] -= 1

            if hintPlayer is None:
                for player in client.allPlayers:
                    for playerCard in player.hand:
                        if playerCard.color == card.color:
                            availableCardsPerValue[playerCard.value] -= 1
            else:
                for player in client.allPlayers:
                    if player.name != hintPlayer:
                        for playerCard in player.hand:
                            if playerCard.color == card.color:
                                availableCardsPerValue[playerCard.value] -= 1
                for myCard in client.myHand:
                    if isKnown(myCard) and myCard.color == card.color:
                        availableCardsPerValue[myCard.value] -= 1

            for c in client.board['playedCards'][card.color]:
                availableCardsPerValue[c.value] -= 1

            availableSlotsProb = dict()
            for value in availableCardsPerValue:
                allCards = sum(availableCardsPerValue.values())
                availableSlotsProb[value] = availableCardsPerValue[value] / allCards

            usefulProb = 0
            for value in availableSlotsProb:
                if value > stackMaxCardValue:
                    usefulProb += availableSlotsProb[value]

            discardTh = 1 - usefulProb

    return discardTh
        

def getPlayThreshold(client, card, hintPlayer=None):
    playProb = 0
    if card.value is not None:
        maxCardsPerColor = N_CARDS[card.value] / len(COLORS)
        availableCardsPerColor = {"green" : maxCardsPerColor, "red" : maxCardsPerColor, "blue" : maxCardsPerColor, "yellow" : maxCardsPerColor, "white" : maxCardsPerColor}
        for discardedCard in client.board['discardedCards']:
            if discardedCard.value == card.value:
                availableCardsPerColor[discardedCard.color] -= 1

        if hintPlayer is None:
            for player in client.allPlayers:
                for playerCard in player.hand:
                    if playerCard.value == card.value:
                        availableCardsPerColor[playerCard.color] -= 1
        else:
            for player in client.allPlayers:
                if player.name != hintPlayer:
                    for playerCard in player.hand:
                        if playerCard.value == card.value:
                            availableCardsPerColor[playerCard.color] -= 1
            for myCard in client.myHand:
                if isKnown(myCard) and myCard.value == card.value:
                    availableCardsPerColor[myCard.color] -= 1

        availableSlotsProb = dict()
        for color in client.board['playedCards']:
            stackMaxCard = max((client.board['playedCards'][color]), key=(lambda c: c.value), default=None)
            if stackMaxCard is not None:
                if stackMaxCard.value + 1 == card.value:
                    allCards = sum(availableCardsPerColor.values())

                    slotProb = availableCardsPerColor[color] / allCards
                    availableSlotsProb[color] = slotProb
                else:
                    availableSlotsProb[color] = 0
            else:
                if card.value == 1:
                    allCards = sum(availableCardsPerColor.values())

                    slotProb = availableCardsPerColor[color] / allCards
                    availableSlotsProb[color] = slotProb
                else:
                    availableSlotsProb[color] = 0
            
        playProb = sum(availableSlotsProb.values())
    elif card.color is not None:
        stackMaxCard = max((client.board['playedCards'][card.color]), key=(lambda c: c.value), default=None)
        if stackMaxCard is None:
            stackMaxCardValue = 0
        else:
            stackMaxCardValue = stackMaxCard.value

        availableCardsPerValue = dict()
        for key in N_CARDS:
            availableCardsPerValue[key] = N_CARDS[key] / len(COLORS)

        for discardedCard in client.board['discardedCards']:
            if discardedCard.color == card.color:
                availableCardsPerValue[discardedCard.value] -= 1

        if hintPlayer is None:
            for player in client.allPlayers:
                for playerCard in player.hand:
                    if playerCard.color == card.color:
                        availableCardsPerValue[playerCard.value] -= 1
        else:
            for player in client.allPlayers:
                if player.name != hintPlayer:
                    for playerCard in player.hand:
                        if playerCard.color == card.color:
                            availableCardsPerValue[playerCard.value] -= 1
            for myCard in client.myHand:
                if isKnown(myCard) and myCard.color == card.color:
                    availableCardsPerValue[myCard.value] -= 1

        for c in client.board['playedCards'][card.color]:
            availableCardsPerValue[c.value] -= 1

        availableSlotsProb = dict()
        for value in availableCardsPerValue:
            allCards = sum(availableCardsPerValue.values())
            availableSlotsProb[value] = availableCardsPerValue[value] / allCards
        
        if stackMaxCardValue != 5:
            playProb = availableSlotsProb[stackMaxCardValue + 1]
        else:
            playProb = 0

    return playProb
        

def playIfOverThreshold(client):
    usedStormTokens = client.board['usedStormTokens']
    thresholdVett = []
    for card in client.myHand:
        t = getPlayThreshold(client, card)
        thresholdVett.append(t)

    th = client.PLAY_THRESHOLD[usedStormTokens]
    if client.cardsDrawn == sum(N_CARDS.values()):
        th = th * client.TH_REDUCER[usedStormTokens]

    if max(thresholdVett) >= client.PLAY_THRESHOLD[usedStormTokens]:
        cardIndex = thresholdVett.index(max(thresholdVett))
        #print(f"Play Over TH {PLAY_THRESHOLD[usedStormTokens]} " + client.myHand[cardIndex].toClientString())
        return client.buildPlayCommand(cardIndex)

    return None

def playTheBest(client):
    thresholdVett = []
    for card in client.myHand:
        t = getPlayThreshold(client, card)
        thresholdVett.append(t)

    cardIndex = thresholdVett.index(max(thresholdVett))
    #print(f"Play Best " + client.myHand[cardIndex].toClientString())
    return client.buildPlayCommand(cardIndex)

def discardTheWorst(client):
    if canDiscard(client.board['usedNoteTokens']):
        thresholdVett = []
        for i, card in enumerate(client.myHand):
            t = getDiscardThreshold(client, card)
            thresholdVett.append(t)

        cardIndex = thresholdVett.index(max(thresholdVett))
        #print(f"Discard Worst " + client.myHand[cardIndex].toClientString())
        return client.buildDiscardCommand(cardIndex)
    return None

def discardIfOverThreshold(threshold):
    def fun(client):
        for i, card in enumerate(client.myHand):
            if getDiscardThreshold(client, card) >= threshold:
                #print(f"Discard Over TH {threshold} " + card.toClientString())
                return client.buildDiscardCommand(i)
        return None

    return fun

POLICIES =  [playIfSure,
            discardIfSure,
            playIfOverThreshold,
            generateUsefulHint,
            #discardIfOverThreshold(DISCARD_THRESHOLD),
            discardTheWorst,
            playTheBest]

DEFAULT_ORDER = range(len(POLICIES))
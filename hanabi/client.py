#!/usr/bin/env python3
import enum
import random
import threading
import numpy as np
from sys import argv, stdout
from threading import Thread
import GameData
import socket
from constants import *
import os
import json

if len(argv) < 4:
    print("You need the player name to start the game.")
    # exit(-1)
    playerName = "Test"  # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])

run = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

command = "ready"

hintState = ("", "")

wait_response = threading.Condition()

CARDS_IN_A_HAND = 5
my_hand = []
training_matches = 5  # TODO steady state
status_decision_map = dict()


class Card(object):
    def __init__(self, value, color) -> None:
        super().__init__()
        self.value = value
        self.color = color

    def toClientString(self):
        return "Card " + str(self.value) + " - " + str(self.color)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value == other.value and self.color == other.color


class CardKnowledge(enum.Enum):
    NONE = 0
    VALUE_NOT_PLAYABLE = 1
    VALUE_PLAYABLE = 2
    COLOR_NOT_PLAYABLE = 4
    COLOR_PLAYABLE = 8


class ActionList(enum.Enum):
    PLAY = 0
    DISCARD = 1
    HINT = 2


class Action(object):
    def __init__(self, cs) -> None:
        super().__init__()
        self.my_hand_dict = cs.cards_status['my_cards']
        self.others_hands_dict = cs.cards_status['others_cards']
        self.actions_value = np.ones(len(ActionList), dtype=int)
        self.dict_entry_values = []
        self.dict_entry_values[ActionList.PLAY.value] = np.ones(CARDS_IN_A_HAND, dtype=int)
        self.dict_entry_values[ActionList.DISCARD.value] = np.ones(CARDS_IN_A_HAND, dtype=int)

    def reward(self, action):
        if self.actions_value[action] != 3:
            self.actions_value[action] += 1

    def penalize(self, action):
        self.actions_value[action] -= 1
        if np.sum(self.actions_value) == 0:
            self.reset_actions()

    def get_action(self):
        all_eq = True
        for i in range(len(ActionList) - 1):
            if self.actions_value[i] != self.actions_value[i + 1]:
                all_eq = False
        if all_eq:
            choice = random.randrange(len(ActionList))
        else:
            choice = self.actions_value.argmax()

        if choice == ActionList.HINT.value:
            a=1
            # TODO manage hint
        else:
            for i in range(CARDS_IN_A_HAND - 1):
                if self.dict_entry_values[choice][i] != self.actions_value[choice][i + 1]:
                    all_eq = False
            if all_eq:
                extra_data = random.randrange(CARDS_IN_A_HAND)
            else:
                extra_data = self.dict_entry_values[choice].argmax()

        return choice, extra_data

    def reset_actions(self):
        self.actions_value = np.ones(len(ActionList), dtype=int)


class CardsStatus(object):
    def __init__(self, my_cs, others_cs) -> None:
        super().__init__()
        self.cards_status = dict()
        self.cards_status['my_cards'] = my_cs
        self.cards_status['others_cards'] = others_cs

    def to_standard_view(self):
        return json.dumps(self.cards_status, sort_keys=True)

    def __hash__(self):
        return self.to_standard_view().__hash__()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.to_standard_view() == other.to_standard_view()


def init_hand():
    global my_hand
    my_hand.append(Card('none', 'none'))
    my_hand.append(Card('none', 'none'))
    my_hand.append(Card('none', 'none'))
    my_hand.append(Card('none', 'none'))
    my_hand.append(Card('none', 'none'))


def what_i_know(card, game_status):
    global card_decision_map

    card_knowledge = CardKnowledge.NONE.value
    if card.color != 'none':
        if len(game_status.tableCards[card.color]) != 0:
            card_knowledge = card_knowledge | CardKnowledge.COLOR_PLAYABLE.value
        else:
            card_knowledge = card_knowledge | CardKnowledge.COLOR_NOT_PLAYABLE.value

    if card.value != 'none':
        value_playable = False
        for color in game_status.tableCards:
            color_cards = len(game_status.tableCards[color])
            if game_status.tableCards[color][color_cards-1] == card.value - 1:
                value_playable = True

        if value_playable:
            card_knowledge = card_knowledge | CardKnowledge.VALUE_PLAYABLE.value
        else:
            card_knowledge = card_knowledge | CardKnowledge.VALUE_NOT_PLAYABLE.value

    return card_knowledge


def compute_cards_status(cards_knowledge):
    cards_status = dict()
    for card_knowledge in cards_knowledge:
        if cards_status.__contains__(card_knowledge):
            cards_status[card_knowledge] += 1
        else:
            cards_status[card_knowledge] = 1

    return cards_status


def make_decision(game_status):
    global command
    global my_hand

    my_cards_knowledge = []
    others_cards_knowledge = []

    for ci, card in enumerate(my_hand):
        my_cards_knowledge[ci] = what_i_know(card, game_status)

    for pi, player in enumerate(game_status.players):
        for ci, card in enumerate(player.hand):
            others_cards_knowledge[pi * CARDS_IN_A_HAND + ci] = what_i_know(card, game_status)

    cards_status = CardsStatus(compute_cards_status(my_cards_knowledge), compute_cards_status(others_cards_knowledge))
    if not status_decision_map.__contains__(cards_status):
        status_decision_map[cards_status] = Action(cards_status)

    selected_action, extra_data = status_decision_map[cards_status].get_action()
    return cards_status, selected_action, extra_data


def command_manager():
    global run
    global status
    global command
    global wait_response

    command = "ready"
    while run:
        wait_response.acquire()
        print("Executing: " + command)
        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)
        elif command == "ready" and status == statuses[0]:
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        elif command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                card_str = command.split(" ")
                card_order = int(card_str[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, card_order).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                card_str = command.split(" ")
                card_order = int(card_str[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, card_order).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        else:
            print("Unknown command: " + command)
            continue

        wait_response.wait()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")
    Thread(target=command_manager).start()
    refresh_status = False
    exiting = False

    while run:
        refresh_status = False
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue

        wait_response.acquire()
        data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/" + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
            init_hand()
            refresh_status = True

        if type(data) is GameData.ServerGameStateData:
            dataOk = True
            if data.currentPlayer == playerName:
                make_decision(data)
                wait_response.notify()

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)
            if data.player == playerName:
                refresh_status = True

        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
            if data.player == playerName:
                refresh_status = True

        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")
            if data.player == playerName:
                refresh_status = True

        if type(data) is GameData.ServerHintData:
            dataOk = True
            if data.destination == playerName:
                if data.type == "value":
                    for i in data.positions:
                        my_hand[i].value = data.value
                else:
                    for i in data.positions:
                        my_hand[i].color = data.value

                print("My Hand:")
                for c in my_hand:
                    print(c.toClientString())
                refresh_status = True

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)

        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            print("Ready for a new game!")
            init_hand()
            if training_matches > 0:
                training_matches -= 1
            else:
                print("Training end")
                exiting = True

            refresh_status = True

        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))

        print("[" + playerName + " - " + status + "]: ", end="")

        if refresh_status:
            if exiting:
                command = "exit"
            else:
                command = "show"
            wait_response.notify()

        wait_response.release()
        stdout.flush()

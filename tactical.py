import imp
import random
from typing import Tuple, List


import tactical_api
import strategic_api
import common_types

COST = {"tank": 8, "airplane": 20, "artillery": 8, "helicopter": 16, "antitank": 10, "irondome": 32, "bunker": 10, "spy": 20, "tower": 16, "satellite": 64, "builder": 20}
from strategic_api import CommandStatus, StrategicApi, StrategicPiece

tank_to_coordinate_to_attack = {}
tank_to_attacking_command = {}
commands = []


class TurnContext(object):
    """Contains all the context of this turn.

    Some useful fields:
    * tiles: Maps coordinates (int, int) to a Tile object.
    * my_pieces: Maps piece IDs to the actual piece, for pieces owned by our
                 country.
    * all_pieces: Same as my_pieces, but for all pieces known by this country.
    * game_width: The width of the game.
    * game_height: The height of the game.
    * my_country: The name of my country.
    * all_countries: The names of all countries in the game.
    """

    def __init__(self, turn_data, logger):
        super(TurnContext, self).__init__()
        self._turn_data = turn_data
        self._logger = logger
        self._commands = []
        self.tiles = {(tile["coordinate"]["x"], tile["coordinate"]["y"]): Tile(self, tile) for tile in turn_data["tiles"]}
        self.my_pieces = {}
        self.all_pieces = {}
        self.game_width = turn_data["width"]
        self.game_height = turn_data["height"]
        self.my_country = turn_data["country"]
        self.all_countries = turn_data["all_countries"]
        for tile in self.tiles.values():
            for piece in tile.pieces:
                if piece.country == self.my_country:
                    self.my_pieces[piece.id] = piece
                self.all_pieces[piece.id] = piece

    def get_tiles_of_country(self, country_name):
        """Returns the set of tile coordinates owned by the given country name.

        If country_name is None, the returned coordinates are of tiles that do not
        belong to any country.
        """
        return {tile.coordinates for tile in self.tiles.values() if tile.country == country_name}

    def get_sighings_of_piece(self, piece_id):
        """Returns the sightings of the given piece.

        This method returns a set of sighted pieces and their locations, as seen by
        the given piece.

        Note that the given piece MUST belong to my country in order for this
        method to work.
        """
        piece = self.my_pieces[piece_id]
        if isinstance(piece, Tower):
            sighting_distance = constants.TOWER_SIGHTING_RANGE
        elif isinstance(piece, Satellite):
            sighting_distance = constants.SATELLITE_SIGHTING_RANGE
        else:
            sighting_distance = 1
        result = set()
        piece_coordinates = piece.tile.coordinates
        for x in range(piece_coordinates.x - sighting_distance, piece_coordinates.x + sighting_distance):
            for y in range(piece_coordinates.y + sighting_distance, piece_coordinates.y + sighting_distance):
                tile = self.tiles.get((x, y))
                if tile is None or distance(piece_coordinates, tile.coordinates) > sighting_distance:
                    continue
                result.update(tile.pieces)
        return result

    def get_commands_of_piece(self, piece_id):
        """Returns the list of ordered commands given to the given piece.

        Note that if the piece did not receive any command in this turn, or is not
        owned by my country, or does not exist, an empty list is returned.
        """
        return [command for command in self._commands if command.piece_id == piece_id]

    def log(self, log_entry):
        """Logs the given log entry to the main log of this country.

        log_entry is expected to be a string, without a trailing new line character.
        """
        self._logger.log(log_entry)

    def get_result(self):
        return [command.to_dict() for command in self._commands]


def move_tank_to_destination(tank, dest):
    """Returns True if the tank's mission is complete."""
    command_id = tank_to_attacking_command[tank.id]
    if dest is None:
        commands[int(command_id)] = CommandStatus.failed(command_id)
        return
    tank_coordinate = tank.tile.coordinates
    if dest.x < tank_coordinate.x:
        new_coordinate = common_types.Coordinates(tank_coordinate.x - 1, tank_coordinate.y)
    elif dest.x > tank_coordinate.x:
        new_coordinate = common_types.Coordinates(tank_coordinate.x + 1, tank_coordinate.y)
    elif dest.y < tank_coordinate.y:
        new_coordinate = common_types.Coordinates(tank_coordinate.x, tank_coordinate.y - 1)
    elif dest.y > tank_coordinate.y:
        new_coordinate = common_types.Coordinates(tank_coordinate.x, tank_coordinate.y + 1)
    else:
        tank.attack()
        commands[int(command_id)] = CommandStatus.success(command_id)
        del tank_to_attacking_command[tank.id]
        return True
    tank.move(new_coordinate)
    prev_command = commands[int(command_id)]
    commands[int(command_id)] = CommandStatus.in_progress(command_id, prev_command.elapsed_turns + 1, prev_command.estimated_turns - 1)
    return False


class MyStrategicApi(strategic_api.StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)
        self.context: TurnContext = self.context
        to_remove = set()
        for tank_id, destination in tank_to_coordinate_to_attack.items():
            tank = self.context.my_pieces.get(tank_id)
            if tank is None:
                to_remove.add(tank_id)
                continue
            if move_tank_to_destination(tank, destination):
                to_remove.add(tank_id)
        for tank_id in to_remove:
            del tank_to_coordinate_to_attack[tank_id]

    def attack(self, piece, destination, radius):
        tank = self.context.my_pieces[piece.id]
        if not tank or tank.type != "tank":
            return None

        if piece.id in tank_to_attacking_command:
            old_command_id = int(tank_to_attacking_command[piece.id])
            commands[old_command_id] = CommandStatus.failed(old_command_id)

        command_id = str(len(commands))
        attacking_command = CommandStatus.in_progress(command_id, 0, common_types.distance(tank.tile.coordinates, destination))
        tank_to_coordinate_to_attack[piece.id] = destination
        tank_to_attacking_command[piece.id] = command_id
        commands.append(attacking_command)

        return command_id

    def report_attacking_pieces(self):
        return {StrategicPiece(piece_id, piece.type): tank_to_attacking_command.get(piece_id) for piece_id, piece in self.context.my_pieces.items() if piece.type == "tank"}

    def get_piece_of_type(self, type_):
        for piece in self.context.my_pieces.values():
            if piece.type == type_:
                return piece
        return None

    def report_builders(self):
        # self.context.log("[*] report_builders: enter")
        builders = {}
        for piece in self.context.all_pieces.values():
            if piece.type == "builder":
                command = self.context.get_commands_of_piece(piece.id)

                builders[piece] = (command[0] if command else None, piece.money)
        # self.context.log("[*] report_builders: return")
        return builders

    def get_power(self, piece) -> float:
        # self.context.log("[*] get_power: enter")
        if piece.type == "tank":
            # self.context.log("[*] get_power: return")
            return 10
        if piece.type == "airplane" or piece.type == "helicopter":
            if piece.flying == True:
                # self.context.log("[*] get_power: return")
                return 500 / piece.time_in_air
            else:
                # self.context.log("[*] get_power: return")
                return 4
        if piece.type == "antitank":
            # self.context.log("[*] get_power: return")
            return 100
        if piece.type == "artillery":
            # self.context.log("[*] get_power: return")
            return 30
        else:
            # self.context.log("[*] get_power: return")
            return 15

    def estimate_tile_danger(self, destination) -> float:
        # self.context.log("[*] estimate_tile_danger: enter")
        # self.context.log(str(destination))
        tile = self.context.tiles[(destination.x, destination.y)]
        if tile.country is None:
            # self.context.log("[*] estimate_tile_danger: return")
            return 0
        if tile.country == self.get_my_country():
            danger = 0
            for piece in self.context.all_pieces.values():
                if piece.country == self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            # self.context.log("[*] estimate_tile_danger: return")
            return 0 - danger
        else:
            danger = 0
            for piece in self.context.all_pieces.values():
                if piece.country != self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            if danger == 0:
                pass
            else:
                # self.context.log("[*] estimate_tile_danger: return")
                self.context.log("danger = " + str(danger))
                return danger

    def gather_intelligence(self, pieces, destination, radius=2):
        # self.context.log("[*] gather_intelligence: enter")
        """Get intelligence of the area around the destination, using `pieces`.
        This method should return a command identifier.
        """
        danger = 0
        for x in range(self.get_game_width()):
            for y in range(self.get_game_height()):
                coor = common_types.Coordinates(x, y)
                dis = tactical_api.distance(coor, destination)
                if dis <= radius:
                    danger += self.estimate_tile_danger(coor) / float(dis)
        # self.context.log("[*] gather_intelligence: return")
        return danger

    def move_builder(self, piece, dest):
        # self.context.log("[*] move_builder: enter")
        coor = piece.tile.coordinates
        for i in range(5):
            if dest.x < coor.x:
                new_coordinate = common_types.Coordinates(coor.x - 1, coor.y)
            elif dest.x > coor.x:
                new_coordinate = common_types.Coordinates(coor.x + 1, coor.y)
            elif dest.y < coor.y:
                new_coordinate = common_types.Coordinates(coor.x, coor.y - 1)
            elif dest.y > coor.y:
                new_coordinate = common_types.Coordinates(coor.x, coor.y + 1)
            else:
                break
            self.context.log("new coordinates = " + str(new_coordinate))
            piece.move(new_coordinate)
            if dest.y < coor.y:
                new_coordinate = common_types.Coordinates(coor.x, coor.y - 1)
            elif dest.y > coor.y:
                new_coordinate = common_types.Coordinates(coor.x, coor.y + 1)
            elif dest.x < coor.x:
                new_coordinate = common_types.Coordinates(coor.x - 1, coor.y)
            elif dest.x > coor.x:
                new_coordinate = common_types.Coordinates(coor.x + 1, coor.y)
            else:
                break
            self.context.log("new coordinates = " + str(new_coordinate))
            piece.move(new_coordinate)
        # self.context.log("[*] move_builder: return")

    def build_piece(self, builder, piece_type):
        # self.context.log("[*] build_piece: enter")
        if piece_type == "airplane":
            if builder.money >= COST[piece_type]:
                builder.build_airplane()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "antitank":
            if builder.money >= COST[piece_type]:
                builder.build_antitank()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "artillery":
            if builder.money >= COST[piece_type]:
                builder.build_artillery()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "builder":
            if builder.money >= COST[piece_type]:
                builder.build_builder()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "bunker":
            if builder.money >= COST[piece_type]:
                builder.build_bunker()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "helicopter":
            if builder.money >= COST[piece_type]:
                builder.build_helicopter()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "iron_dome":
            if builder.money >= COST[piece_type]:
                builder.build_iron_dome()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "satellite":
            if builder.money >= COST[piece_type]:
                builder.build_satellite()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "spy":
            if builder.money >= COST[piece_type]:
                builder.build_spy()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "tank":
            if builder.money >= COST[piece_type]:
                builder.build_tank()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        elif piece_type == "tower":
            if builder.money >= COST[piece_type]:
                builder.build_tower()
            else:
                self.collect_money(builder, builder.money - COST[piece_type])
        # self.context.log("[*] build_piece: return")

    def is_in_board(self, loc: Tuple[int, int]):
        return loc[0] >= 0 and loc[1] >= 0 and loc[0] < self.get_game_width() and loc[1] < self.get_game_height()

    def collect_money(self, builder, amount):
        """Collect a certain amount of money by the given `builder`.
        `builder` should be a `StrategicPiece` object. `amount` should be an `int`.
        This method should return a command ID.
        """
        # self.context.log("[*] collect_money: enter")
        curr_money = builder.money
        # pick a direction where there is the most money and go there
        loc = builder.tile.coordinates
        tile = self.context.tiles[(loc.x, loc.y)]
        if tile.money == 0:
            self.context.log("no money in current tile")
            # All possible directions, even ones outside the board
            DIRECTIONS_UNFILTERED = [(loc.x + a[0], loc.y + a[1]) for a in [(0, 1), (0, -1), (1, 0), (-1, 0)]]
            # filter
            self.context.log(str(DIRECTIONS_UNFILTERED))

            DIRECTIONS = [a for a in DIRECTIONS_UNFILTERED if self.is_in_board(a)]
            # money for every destinaion
            self.context.log("2")

            MONEY = [self.context.tiles[a].money for a in DIRECTIONS]
            self.context.log("moneys: " + str(MONEY))

            best_i = -1
            best_money = -1
            # find the spot with the most money
            for a in range(len(MONEY)):
                if MONEY[a] > best_money:
                    best_i = a
                    best_money = MONEY[a]
            # destination with the most money (still possible that it is 0)
            dest = DIRECTIONS[best_i]
            self.context.log("best available tile" + str(dest))
            if best_money == 0:
                self.context.log("not near money")

                # If there is no money in a neighbour spot, reach for the middle spot
                # If the builder is in the middle,
                if False:  # builder.tile.coordinates.x == self.get_game_width() // 2 and builder.tile.coordinates.y == self.get_game_height() // 2:
                    coor = common_types.Coordinates(random.randint(0, self.get_game_width()), random.randint(0, self.get_game_height()))
                    while self.gather_intelligence([], coor, 2) > 0:
                        coor = common_types.Coordinates(random.randint(0, self.get_game_width()), random.randint(0, self.get_game_height()))
                    self.move_builder(builder, coor)
                else:
                    self.move_builder(builder, common_types.Coordinates(self.get_game_width() // 2, self.get_game_height() // 2))
                self.context.log("[*] collect_money: return")
                return
            else:
                builder.move(common_types.Coordinates(dest[0], dest[1]))
        else:
            n_tile = self.context.tiles[(loc.x, loc.y)]
            m = n_tile.money
            self.context.log("curr money: " + str(curr_money))
            builder.collect_money(min(m, 5))
            curr_money += min(m, 5)
            self.context.log("after collection: " + str(curr_money))

            # self.context.log("[*] collect_money: return")
        return curr_money >= amount

    def get_game_width(self):
        return self.context.game_width

    def get_game_height(self):
        return self.context.game_height

    def get_my_country(self):
        return self.context.my_country

    def list_all_countries(self):
        return self.context.all_countries

    def get_piece_of_type(self, type_):
        for piece in self.context.my_pieces.values():
            if piece.type == type_:
                return piece
        return None


# log = tactical_api.Logger(None)


def get_strategic_implementation(context):
    return MyStrategicApi(context)

import random

import tactical_api
import strategic_api

COST = {'tank' : 8, 'airplane' : 20, 'artillery' : 8, 'helicopter' : 16,
                'antitank' : 10, 'irondome' : 32, 'bunker' : 10, 'spy' : 20,
                'tower' : 16, 'satellite' : 64, 'builder' : 20}

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
        self.tiles = {(tile['coordinate']['x'], tile['coordinate']['y']): Tile(self, tile)
                      for tile in turn_data['tiles']}
        self.my_pieces = {}
        self.all_pieces = {}
        self.game_width = turn_data['width']
        self.game_height = turn_data['height']
        self.my_country = turn_data['country']
        self.all_countries = turn_data['all_countries']
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
        return {tile.coordinates for tile in self.tiles.values()
                if tile.country == country_name}

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
        return [command for command in self._commands
                if command.piece_id == piece_id]

    def log(self, log_entry):
        """Logs the given log entry to the main log of this country.

        log_entry is expected to be a string, without a trailing new line character.
        """
        self._logger.log(log_entry)

    def get_result(self):
        return [command.to_dict() for command in self._commands]


class StrategicApi(object):
    def __init__(self, context):
        """Constructor. context allows us to use the tactical API."""
        self.context: TurnContext = context

    # ----------------------------------------------------------------------------
    # Attacking military commands.
    # ----------------------------------------------------------------------------

    def attack(self, pieces, destination, radius):
        """Attack the area around the destination, using the given pieces.

        This command should be interepreted as attacking a tile, whose distance of
        `destination` is at most `radius` using the given set of `pieces` (set of
        `StrategicPiece`s).
        This method should return a command identifier.
        """
        raise NotImplementedError()

    def estimate_attack_time(self, pieces, destination, radius):
        """Estimate the amount of required turns for an attack command.

        This method should return an integer, that is the estimated amount of
        turns required for completing an attack command with the given arguments.
        """
        raise NotImplementedError()

    def report_attack_command_status(self, command_id):
        """Given a command identifier, report its status.

        The returned value must be of type `CommandStatus`.
        """
        raise NotImplementedError()

    def report_attacking_pieces(self):
        """Report the current status of all attacking pieces.

        The returned value should be a dict, mapping from StrategicPiece to its
        current command ID that it is executing. Only attacking pieces should be
        included in this report.
        """
        raise NotImplementedError()

    def estimated_required_attacking_pieces(self, destination, radius):
        """Estimates the amount of required pieces for conquering the destination.

        The return value should be an integer.
        """
        raise NotImplementedError()

    def report_missing_intelligence_for_pending_attacks(self):
        """Return all coordinates in which we are missing intelligence.

        Intelligence from the returned tiles would help in improving pending
        attack commands.

        The returned value should be a set of `Coordinates`s.
        """
        raise NotImplementedError()

    def set_intelligence_for_attacks(self, tiles):
        """Provide the implementation with missing intelligence for attacks.

        `tiles` is a `dict` mapping a `Coordinates` object into an `int`,
        representing the danger level of this tile.

        This function does not return any value.
        """
        raise NotImplementedError()

    def report_required_pieces_for_attacks(self):
        """Returns a list of pieces, where they are needed and their priority.

        This method returns a list of tuples, each containing the following values
        (in this order):
        0. Piece type (as `str`).
        1. Destination tile (as `Coordinates`).
        2. Improtance (as `int`).
        """
        raise NotImplementedError()

    def report_required_tiles_for_attacks(self):
        """Returns a list of tiles that are required for completing commands.

        This mehtod returns a list of tuples, each containing the following values
        (in this order):
        0. Tile (as `Coordinates`).
        1. Importance (as `int`).
        """
        raise NotImplementedError()

    def esscort_piece_with_attacking_piece(self, piece, pieces):
        """Esscort the given `piece` with the attacking `pieces`.

        When this command is given, each piece in `pieces` should esscort `piece`.
        `piece` is a `StrategicPiece`, and `pieces` is a `set` of
        `StrategicPiece`s.
        This method should return a command ID.
        """
        raise NotImplementedError()

    # ----------------------------------------------------------------------------
    # Defensive military commands.
    # ----------------------------------------------------------------------------

    def defend(self, pieces, destination, radius):
        """Defend the area around the destination, using the given pieces.

        This command should be interepreted as defending a tile, whose distance of
        `destination` is at most `radius` using the given set of `pieces` (set of
        `StrategicPiece`s).
        This method should return a command identifier.
        """
        raise NotImplementedError()

    def estimate_defend_time(self, pieces, destination, radius):
        """Estimate the amount of required turns form a defense.

        This method should return an integer, that is the estimated amount of
        turns required for forming a defense command with the given arguments.
        """
        raise NotImplementedError()

    def report_defense_command_status(self, command_id):
        """Given a command identifier, report its status.

        The returned value must be of type `CommandStatus`.
        """
        raise NotImplementedError()

    def report_defending_pieces(self):
        """Report the current status of all defending pieces.

        The returned value should be a dict, mapping from StrategicPiece to its
        current command ID that it is executing. Only defending pieces should be
        included in this report.
        """
        raise NotImplementedError()

    def estimated_required_defending_pieces(self, destination, radius):
        """Estimates the amount of required pieces for defending the destination.

        The return value should be an integer.
        """
        raise NotImplementedError()

    def report_missing_intelligence_for_pending_defends(self):
        """Return all coordinates in which we are missing intelligence.

        Intelligence from the returned tiles would help in improving pending
        defend commands.

        The returned value should be a set of `Coordinates`s.
        """
        raise NotImplementedError()

    def set_intelligence_for_defends(self, tiles):
        """Provide the implementation with missing intelligence for defends.

        `tiles` is a `dict` mapping a `Coordinates` object into an `int`,
        representing the danger level of this tile.

        This function does not return any value.
        """
        raise NotImplementedError()

    def report_required_pieces_for_defends(self):
        """Returns a list of pieces, where they are needed and their priority.

        This method returns a list of tuples, each containing the following values
        (in this order):
        0. Piece type (as `str`).
        1. Destination tile (as `Coordinates`).
        2. Improtance (as `int`).
        """
        raise NotImplementedError()

    def report_required_tiles_for_defends(self):
        """Returns a list of tiles that are required for completing commands.

        This mehtod returns a list of tuples, each containing the following values
        (in this order):
        0. Tile (as `Coordinates`).
        1. Importance (as `int`).
        """
        raise NotImplementedError()

    def esscort_piece_with_defending_piece(self, piece, pieces):
        """Esscort the given `piece` with the defending `pieces`.

        When this command is given, each piece in `pieces` should esscort `piece`.
        `piece` is a `StrategicPiece`, and `pieces` is a `set` of
        `StrategicPiece`s.
        This method should return a command ID.
        """
        raise NotImplementedError()

    # ----------------------------------------------------------------------------
    # Intelligence commands.
    # ----------------------------------------------------------------------------

    def estimate_tile_danger(self, destination):
        """Estimate the danger level of the given destination.

        `destination` should be a `Coordinates` object.
        The returned value is an `int`.
        """
        raise NotImplementedError()

    def gather_intelligence(self, pieces, destination, radius):
        """Get intelligence of the area around the destination, using `pieces`.

        This method should return a command identifier.
        """
        raise NotImplementedError()

    def estimate_gathering_time(self, pieces, destination, radius):
        """Estimate the amount of required turns for gathering intelligence.

        This method should return an integer, that is the estimated amount of
        turns required for gathering intelligence command with the given arguments.
        """
        raise NotImplementedError()

    def report_gathering_command_status(self, command_id):
        """Given a command identifier, report its status.

        The returned value must be of type `CommandStatus`.
        """
        raise NotImplementedError()

    def report_intelligence_pieces(self):
        """Report the current status of all intelligence pieces.

        The returned value should be a dict, mapping from StrategicPiece to its
        current command ID that it is executing. Only intelligence pieces should be
        included in this report.
        """
        raise NotImplementedError()

    def report_required_pieces_for_intelligence(self):
        """Returns a list of pieces, where they are needed and their priority.

        This method returns a list of tuples, each containing the following values
        (in this order):
        0. Piece type (as `str`).
        1. Destination tile (as `Coordinates`).
        2. Improtance (as `int`).
        """
        raise NotImplementedError()

    def report_required_tiles_for_intelligence(self):
        """Returns a list of tiles that are required for completing commands.

        This mehtod returns a list of tuples, each containing the following values
        (in this order):
        0. Tile (as `Coordinates`).
        1. Importance (as `int`).
        """
        raise NotImplementedError()

    def esscort_piece_with_intelligence_piece(self, piece, pieces):
        """Esscort the given `piece` with the intelligence `pieces`.

        When this command is given, each piece in `pieces` should esscort `piece`.
        `piece` is a `StrategicPiece`, and `pieces` is a `set` of
        `StrategicPiece`s.
        This method should return a command ID.
        """
        raise NotImplementedError()

    # ----------------------------------------------------------------------------
    # Building commands.
    # ----------------------------------------------------------------------------

    def collect_money(self, builder, amount):
        """Collect a certain amount of money by the given `builder`.

        `builder` should be a `StrategicPiece` object. `amount` should be an `int`.
        This method should return a command ID.
        """
        raise NotImplementedError()

    def estimate_collection_time(self, builder, amount):
        """Estimate the required amount of turns for collecting money.

        This method should return an `int`, that is the estimated amount of turns
        required for collecting the given `amount` of money by the given `builder`.
        """
        raise NotImplementedError()

    def build_piece(self, builder, piece_type):
        """Build a new piece of type `piece_type` using `builder`.

        This methos should be interpreted as "Build a new piece using the given
        `builder`". If the given `builder` does not posses the required amount of
        money for building the required new piece, it should collect it first, and
        then build the new piece.

        `builder` should be a `StrategicPiece` object. `piece_type` is a `str`.
        This method returns a command ID.
        """
        raise NotImplementedError()

    def estimate_building_time(self, builder, piece_type):
        """Estimate the amount of required turns for building a new piece.

        This method should return an integer, that is the estimated amount of
        turns required for building a new piece with the given arguments.
        """
        raise NotImplementedError()

    def report_build_command_status(self, command_id):
        """Given a command identifier, report its status.

        The returned value must be of type `CommandStatus`.
        """
        raise NotImplementedError()

    def get_total_builders_money(self):
        """Returns the total amount of money all the country builders have."""
        raise NotImplementedError()

    def get_total_country_tiles_money(self):
        """Returns the total amount of money the country has on its tiles."""
        raise NotImplementedError()

    def report_builders(self):
        """Report the current status of all builders.

        The returned value should be a `dict`, mapping from a `StrategicPiece`
        objects to a tuple, containing the following values in this order:
        0. The current command ID that this builder is executing, if available, or
           `None` otherwise.
        1. The current amount of money of this builder.
        """
        raise NotImplementedError()

    def report_missing_intelligence_for_collecting_money(self):
        """Return all coordinates in which we are missing intelligence.

        Intelligence from the returned tiles would help in collecting more money.

        The returned value should be a set of `Coordinates`s.
        """
        raise NotImplementedError()

    def set_intelligence_for_builders(self, tiles):
        """Provide the implementation with intelligence for collecting money.

        `tiles` is a `dict` mapping a `Coordinates` object into an `int`,
        representing the danger level of this tile.

        This function does not return any value.
        """
        raise NotImplementedError()

    def report_required_tiles_for_collecting_money(self):
        """Returns a list of tiles that are required for completing commands.

        This mehtod returns a list of tuples, each containing the following values
        (in this order):
        0. Tile (as `Coordinates`).
        1. Importance (as `int`).
        """
        raise NotImplementedError()

    # ----------------------------------------------------------------------------
    # Miscellaneous commands.
    # ----------------------------------------------------------------------------

    def get_my_country(self):
        """Returns the name of this country."""
        raise NotImplementedError()

    def get_all_countries(self):
        """Returns the list of all participating countries in the game."""
        raise NotImplementedError()

    def get_game_width(self):
        """Returns the width of the current game board."""
        raise NotImplementedError()

    def get_game_height(self):
        """Returns the height of the current game board."""
        raise NotImplementedError()

    def log(self, log_entry):
        """Logs the given log entry to the main log of this country.

        log_entry is expected to be a string, without a trailing new line character.
        """
        raise NotImplementedError()


class MyStrategicApi(StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)

    def report_builders(self):
        builders = {}
        for piece in self.context.all_pieces:
            if piece.type == "builder":
                command = self.context.get_commands_of_piece(piece.id)

                builders[piece] = (command[0] if command else None,
                                   piece.money
                                   )
        return builders

    def get_power(self, piece) -> float:
        if piece.type == "tank":
            return 10
        if piece.type == "airplane" or piece.type == "helicopter":
            if piece.flying == True:
                return 500 / piece.time_in_air
            else:
                return 4
        if piece.type == "antitank":
            return 100
        if piece.type == "artillery":
            return 30
        else:
            return 15

    def estimate_tile_danger(self, destination) -> float:
        tile = self.context.tiles[(destination.x, destination.y)]
        if tile.country is None:
            return 0
        if tile.country == self.get_my_country():
            danger = 0
            for piece in self.context.all_pieces:
                if piece.country == self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            return 0-danger
        else:
            danger = 0
            for piece in self.context.all_pieces:
                if piece.country != self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            if danger == 0:
                pass
            else:
                return danger

    def gather_intelligence(self, pieces, destination, radius=2):
        """Get intelligence of the area around the destination, using `pieces`.
        This method should return a command identifier.
        """
        danger = 0
        for x in range(self.get_game_width()):
            for y in range(self.get_game_height()):
                coor = tactical_api.Coordinates(x, y)
                dis = tactical_api.distance(coor, destination)
                if dis <= radius:
                    danger += self.estimate_tile_danger(coor) / float(dis)
        return danger

    def move_builder(self, piece, dest):
        coor = piece.tile.coordinates
        for i in range(5):
            if dest.x < coor.x:
                new_coordinate = tactical_api.Coordinates(coor.x - 1, coor.y)
            elif dest.x > coor.x:
                new_coordinate = tactical_api.Coordinates(coor.x + 1, coor.y)
            elif dest.y < coor.y:
                new_coordinate = tactical_api.Coordinates(coor.x, coor.y - 1)
            elif dest.y > coor.y:
                new_coordinate = tactical_api.Coordinates(coor.x, coor.y + 1)
            else:
                break
            piece.move(new_coordinate)
            if dest.y < coor.y:
                new_coordinate = tactical_api.Coordinates(coor.x, coor.y - 1)
            elif dest.y > coor.y:
                new_coordinate = tactical_api.Coordinates(coor.x, coor.y + 1)
            elif dest.x < coor.x:
                new_coordinate = tactical_api.Coordinates(coor.x - 1, coor.y)
            elif dest.x > coor.x:
                new_coordinate = tactical_api.Coordinates(coor.x + 1, coor.y)
            else:
                break
            piece.move(new_coordinate)
    def build_piece(self, builder, piece_type):
        if piece_type == "airplane":
            if builder.money >= COST[piece_type]:
                builder.build_airplane()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "antitank":
            if builder.money >= COST[piece_type]:
                builder.build_antitank()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "artillery":
            if builder.money >= COST[piece_type]:
                builder.build_artillery()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "builder":
            if builder.money >= COST[piece_type]:
                builder.build_builder()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "bunker":
            if builder.money >= COST[piece_type]:
                builder.build_bunker()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "helicopter":
            if builder.money >= COST[piece_type]:
                builder.build_helicopter()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "iron_dome":
            if builder.money >= COST[piece_type]:
                builder.build_iron_dome()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "satellite":
            if builder.money >= COST[piece_type]:
                builder.build_satellite()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "spy":
            if builder.money >= COST[piece_type]:
                builder.build_spy()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "tank":
            if builder.money >= COST[piece_type]:
                builder.build_tank()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])
        elif piece_type == "tower":
            if builder.money >= COST[piece_type]:
                builder.build_tower()
            else:
                self.collect_money(builder, builder.money-COST[piece_type])

    def collect_money(self, builder, amount):
        """Collect a certain amount of money by the given `builder`.
        `builder` should be a `StrategicPiece` object. `amount` should be an `int`.
        This method should return a command ID.
        """
        curr_money = builder.money
        # pick a direction where there is the most money and go there
        loc = builder.tile.coordinates
        tile = self.context.tiles[(loc.x, loc.y)]
        if tile.money < 5:
            tiles_money = {}
            if loc.x > 0:
                n_tile = self.context.tiles[(loc.x - 1, loc.y)]
                tiles_money['L'] = n_tile.money
            if loc.x < self.get_game_width() - 1:
                n_tile = self.context.tiles[(loc.x + 1, loc.y)]
                tiles_money['R'] = n_tile.money
            if loc.y > 0:
                n_tile = self.context.tiles[(loc.x, loc.y - 1)]
                tiles_money['U'] = n_tile.money
            if loc.y < self.get_game_height() - 1:
                n_tile = self.context.tiles[(loc.x, loc.y + 1)]
                tiles_money['D'] = n_tile.money
            if len(tiles_money) == 0:
                log('[!] collect_money: impossible location')
            direction, m = sorted(tiles_money.items(), key=lambda d, m: -m)[0]
            dest = tactical_api.Coordinates(loc.x + 1 * (direction == 'R') - 1 * (direction == 'L'),
                                            loc.y + 1 * (direction == 'D') - 1 * (direction == 'U'))
            if m == 0:
                if builder.tile.coordinates.x == self.get_game_width()//2 and builder.tile.coordinates.y == self.get_game_height()//2:
                    self.move_builder(builder, tactical_api.Coordinates(random.randint(0, self.get_game_width()), random.randint(0, self.get_game_height())))
                else:
                    self.move_builder(builder, tactical_api.Coordinates(self.get_game_width()//2, self.get_game_height()//2))
            else:
                builder.move(dest)
        n_tile = self.context.tiles[(loc.x - 1, loc.y)]
        m = n_tile.money
        builder.collect_money(max(m, 5))
        curr_money += 5
        return curr_money >= amount

log = tactical_api.Logger.log
def get_strategic_implementation(context):
    return MyStrategicApi(context)

import imp
import random

import tactical_api
import strategic_api
import common_types

COST = {"tank": 8, "airplane": 20, "artillery": 8, "helicopter": 16, "antitank": 10, "irondome": 32, "bunker": 10, "spy": 20, "tower": 16, "satellite": 64, "builder": 20}
from strategic_api import CommandStatus, StrategicApi, StrategicPiece

tank_to_coordinate_to_attack = {}
tank_to_attacking_command = {}
commands = []


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
        log.log("[*] report_builders: enter")
        builders = {}
        for piece in self.context.all_pieces:
            if piece.type == "builder":
                command = self.context.get_commands_of_piece(piece.id)

                builders[piece] = (command[0] if command else None, piece.money)
        log.log("[*] report_builders: return")
        return builders

    def get_power(self, piece) -> float:
        log.log("[*] get_power: enter")
        if piece.type == "tank":
            log.log("[*] get_power: return")
            return 10
        if piece.type == "airplane" or piece.type == "helicopter":
            if piece.flying == True:
                log.log("[*] get_power: return")
                return 500 / piece.time_in_air
            else:
                log.log("[*] get_power: return")
                return 4
        if piece.type == "antitank":
            log.log("[*] get_power: return")
            return 100
        if piece.type == "artillery":
            log.log("[*] get_power: return")
            return 30
        else:
            log.log("[*] get_power: return")
            return 15

    def estimate_tile_danger(self, destination) -> float:
        log.log("[*] estimate_tile_danger: enter")
        tile = self.context.tiles[(destination.x, destination.y)]
        if tile.country is None:
            log.log("[*] estimate_tile_danger: return")
            return 0
        if tile.country == self.get_my_country():
            danger = 0
            for piece in self.context.all_pieces:
                if piece.country == self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            log.log("[*] estimate_tile_danger: return")
            return 0 - danger
        else:
            danger = 0
            for piece in self.context.all_pieces:
                if piece.country != self.get_my_country():
                    if tactical_api.distance(piece.tile.coordinates, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            if danger == 0:
                pass
            else:
                log.log("[*] estimate_tile_danger: return")
                return danger

    def gather_intelligence(self, pieces, destination, radius=2):
        log.log("[*] gather_intelligence: enter")
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
        log.log("[*] gather_intelligence: return")
        return danger

    def move_builder(self, piece, dest):
        log.log("[*] move_builder: enter")
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
            piece.move(new_coordinate)
        log.log("[*] move_builder: return")

    def build_piece(self, builder, piece_type):
        log.log("[*] build_piece: enter")
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
        log.log("[*] build_piece: return")

    def collect_money(self, builder, amount):
        """Collect a certain amount of money by the given `builder`.
        `builder` should be a `StrategicPiece` object. `amount` should be an `int`.
        This method should return a command ID.
        """
        log.log("[*] collect_money: enter")
        curr_money = builder.money
        # pick a direction where there is the most money and go there
        loc = builder.tile.coordinates
        tile = self.context.tiles[(loc.x, loc.y)]
        if tile.money < 5:
            tiles_money = {}
            if loc.x > 0:
                n_tile = self.context.tiles[(loc.x - 1, loc.y)]
                tiles_money["L"] = n_tile.money
            if loc.x < self.get_game_width() - 1:
                n_tile = self.context.tiles[(loc.x + 1, loc.y)]
                tiles_money["R"] = n_tile.money
            if loc.y > 0:
                n_tile = self.context.tiles[(loc.x, loc.y - 1)]
                tiles_money["U"] = n_tile.money
            if loc.y < self.get_game_height() - 1:
                n_tile = self.context.tiles[(loc.x, loc.y + 1)]
                tiles_money["D"] = n_tile.money
            if len(tiles_money) == 0:
                log.log("[!] collect_money: impossible location")
            direction, m = sorted(tiles_money.items(), key=lambda d, m: -m)[0]
            dest = common_types.Coordinates(loc.x + 1 * (direction == "R") - 1 * (direction == "L"), loc.y + 1 * (direction == "D") - 1 * (direction == "U"))
            if m == 0:
                if builder.tile.coordinates.x == self.get_game_width() // 2 and builder.tile.coordinates.y == self.get_game_height() // 2:
                    coor = common_types.Coordinates(random.randint(0, self.get_game_width()), random.randint(0, self.get_game_height()))
                    while self.gather_intelligence([], coor, 2) > 0:
                        coor = common_types.Coordinates(random.randint(0, self.get_game_width()), random.randint(0, self.get_game_height()))
                    self.move_builder(builder, coor)
                else:
                    self.move_builder(builder, common_types.Coordinates(self.get_game_width() // 2, self.get_game_height() // 2))
                log.log("[*] collect_money: return")
                return
            else:
                builder.move(dest)
        n_tile = self.context.tiles[(loc.x - 1, loc.y)]
        m = n_tile.money
        builder.collect_money(max(m, 5))
        curr_money += 5
        log.log("[*] collect_money: return")
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


log = tactical_api.Logger(None)


def get_strategic_implementation(context):
    return MyStrategicApi(context)

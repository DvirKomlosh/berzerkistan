import random

import tactical_api
import strategic_api

COST = {'tank' : 8, 'airplane' : 20, 'artillery' : 8, 'helicopter' : 16,
                'antitank' : 10, 'irondome' : 32, 'bunker' : 10, 'spy' : 20,
                'tower' : 16, 'satellite' : 64, 'builder' : 20}

class MyStrategicApi(strategic_api.StrategicApi):
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

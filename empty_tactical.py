import random

import tactical_api
import strategic_api


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
                    if tactical_api.distance(piece.tile, destination) == 0:
                        danger = max(danger, self.get_power(piece))
            return 0-danger
        else:
            danger = 0
            for piece in self.context.all_pieces:
                if piece.country != self.get_my_country():
                    if tactical_api.distance(piece.tile, destination) == 0:
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
                coor = common_types.Coordinates(x, y)
                dis = tactical_api.distance(coor, destination)
                if dis <= radius:
                    danger += self.estimate_tile_danger(coor) / float(dis)
        return danger
    
    def report_builders(self):
        builders = {}
        for piece in self.context.all_pieces:
            if piece.type == "builder":
                command = self.context.get_commands_of_piece(piece.id)

                builders[piece] = (command[0] if command else None,
                                   piece.money
                                   )
        return builders


def get_strategic_implementation(context):
    return MyStrategicApi(context)

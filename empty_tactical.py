import random

import tactical_api
import strategic_api

money_dict = {'tank' : 8, 'airplane' : 20, 'artillery' : 8, 'helicopter' : 16, 
                'antitank' : 10, 'irondome' : 32, 'bunker' : 10, 'spy' : 20, 
                'tower' : 16, 'satellite' : 64, 'builder' : 20}


class MyStrategicApi(strategic_api.StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)

    def build_piece(self, builder, piece_type):
        """Build a new piece of type `piece_type` using `builder`.
        This method should be interpreted as "Build a new piece using the given
        `builder`". If the given `builder` does not posses the required amount of
        money for building the required new piece, returns False."
        """
        price = money_dict[piece_type]
        if builder.money < price:
            return False
        builder._build(piece_type)
        return True

    def collect_money(self, builder, amount):
        """Collect a certain amount of money by the given `builder`.
        `builder` should be a `StrategicPiece` object. `amount` should be an `int`.
        This method should return a command ID.
        """
        curr_money = builder.money
        if curr_money >= amount:
            return True
        # pick a direction where there is the most money and go there
        loc = builder.tile.coordinates
        tiles_money = {}
        if loc.x > 0:
            n_tile = self.context.tiles[(loc.x - 1, loc.y)]
            tiles_money['L'] = n_tile.money
        if loc.x < strategic_api.get_game_width() - 1:
            n_tile = self.context.tiles[(loc.x + 1, loc.y)]
            tiles_money['R'] = n_tile.money
        if loc.y > 0:
            n_tile = self.context.tiles[(loc.x, loc.y - 1)]
            tiles_money['U'] = n_tile.money
        if loc.y < strategic_api.get_game_height() - 1:
            n_tile = self.context.tiles[(loc.x, loc.y + 1)]
            tiles_money['D'] = n_tile.money
        
        direction, m = sorted(tiles_money.items(), key=lambda d, m: -m)[0]
        dest = tactical_api.Coordinates(loc.x + 1*(direction == 'R') - 1*(direction == 'L'), 
                                        loc.y + 1*(direction == 'D') - 1*(direction == 'U'))
        builder.move(dest)
        builder.collect_money(min(100 - curr_money, m))
        curr_money += m
        return curr_money >= amount


def get_strategic_implementation(context):
    return MyStrategicApi(context)

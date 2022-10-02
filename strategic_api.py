#!/usr/bin/env python
# -*- coding: utf-8 -*-
from common_types import Coordinates


class StrategicApi:
    def get_nearby_tiles(self, tile):
        # type: (Coordinates)->list
        return [Coordinates(tile.x+a[0],tile.y+a[1]) for a in ((0,0),(0,1),(1,0),(1,1))]
    def estimate_tile_danger (self, destination):

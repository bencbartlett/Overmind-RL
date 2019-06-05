import json

import h5py
import numpy as np
import screepsapi


class TerrainScraper:

    def __init__(self, filename = 'terrain_data/MMO.hdf5'):

        with open('credentials.json') as json_file:
            credentials = json.load(json_file)

        self.api = screepsapi.API(credentials['username'], credentials['password'])
        self.file = h5py.File(filename, 'a')

    def get_all_rooms(self):
        # world_size = api.worldsize(shard)
        # width = world_size['width']
        # height = world_size['height']
        rooms_en = ["E{}N{}".format(y, x) for y in range(0, 60 + 1) for x in range(0, 60 + 1)]
        rooms_es = ["E{}S{}".format(y, x) for y in range(0, 60 + 1) for x in range(0, 60 + 1)]
        rooms_wn = ["W{}N{}".format(y, x) for y in range(0, 60 + 1) for x in range(0, 60 + 1)]
        rooms_ws = ["W{}S{}".format(y, x) for y in range(0, 60 + 1) for x in range(0, 60 + 1)]
        all_rooms = rooms_en + rooms_es + rooms_wn + rooms_ws
        return all_rooms

    def scrape_room(self, shard, room):
        print("Scraping terrain data from room {} on {}...".format(room, shard))

        terrain_data = self.api.room_terrain(room, shard = shard, encoded = True)
        terrain_string = terrain_data['terrain'][0]['terrain']
        terrain_arr = np.reshape(np.array(list(terrain_string), dtype = np.uint8), (50, 50))

        shard_group = self.file.require_group(shard)
        shard_group.create_dataset(room, data = terrain_arr)

    def already_scraped_room(self, shard, room):
        shard_group = self.file.require_group(shard)
        return room in shard_group

    def scrape_shard(self, shard):
        for room in self.get_all_rooms():
            if self.already_scraped_room(shard, room):
                print("Already scraped terrain data from room {} on {}!".format(room, shard))
            else:
                self.scrape_room(shard, room)

    def scrape_all_shards(self):
        all_shards = self.api.get_shards()
        for shard in all_shards:
            print("Scraping shard {}...".format(shard))
            self.scrape_shard(shard)


if __name__ == '__main__':
    scraper = TerrainScraper()
    scraper.scrape_all_shards()

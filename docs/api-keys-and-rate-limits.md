# API keys and rate limits

## Obtain an API key

To use the Mapzen Terrain Tile service, you should [first obtain a free developer API key](https://mapzen.com/documentation/overview/).

## Rate limits

Mapzen Terrain Tiles are a free data product that is 100% cached.

If you experience slow tile loading in a map area, it's likely because you are a first requester in your region of the world. Subsequent loads of the same map area should be much faster because the tile is now available in the local edge cache.

If you have questions, contact [tiles@mapzen.com](mailto:tiles@mapzen.com). You can also set up your own instance of [Joerd](https://github.com/tilezen/joerd), which has access to the same data used in the Mapzen Terrain Tiles service.

## Caching

You are free to cache Mapzen’s terrain tiles for offline use, but you must give credit to the source data by including [attribution](attribution.md).

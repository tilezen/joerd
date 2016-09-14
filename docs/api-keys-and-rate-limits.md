# API keys and rate limits

## Obtain an API key

To use Mapzen Terrain Tiles, you should first obtain a free developer API key. Sign in at https://mapzen.com/developers to create and manage your API keys.

1. Go to https://mapzen.com/developers.
2. Sign in with your GitHub account. If you have not done this before, you need to agree to the terms first.
3. Create a new key for Mapzen Terrain Tiles, and optionally, give it a name so you can remember the purpose of the project.
4. Copy the key into your code.

## Rate limits

Mapzen Terrain Tiles are a free data product that is 100% cached.

If you experience slow tile loading in a map area, it's likely because you are a first requester in your region of the world. Subsequent loads of the same map area should be much faster because the tile is now available in the local edge cache.

If you have questions, contact [tiles@mapzen.com](mailto:tiles@mapzen.com). You can also set up your own instance of [Joerd](https://github.com/tilezen/joerd), which has access to the same data used in the Mapzen Terrain Tiles service.

## Caching

You are free to cache Mapzen’s terrain tiles for offline use, but you must give credit to the source data by including [attribution](attribution.md).

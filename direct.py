import requests
url = 'https://desustream.com/safelink/link/?id=eXRoOHNYVG9UdnVGOXpQU2dYWmpSYjJGYkxEUnE4V3o4bjUrZFpHeTNDTmIyMytZaTBNNjdIRjNLK2p1d0tpdzBJZ3pvRWU4SUpmY1N1OWI1VkV5SWxRVTJKZWhCN083MlE9PQ=='
response = requests.get(url)
final_url = response.url
print(final_url)

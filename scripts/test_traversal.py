from pyTigerGraph import TigerGraphConnection
from dotenv import load_dotenv
import os

load_dotenv()

conn = TigerGraphConnection(
    host=os.environ["TG_HOST"],
    graphname=os.environ["TG_GRAPHNAME"],
    username=os.environ["TG_USERNAME"],
    password=os.environ["TG_PASSWORD"]
)

# Use conn.gsql with proper GSQL syntax
result = conn.gsql("USE GRAPH HHGoa\nSELECT s FROM Transaction:s LIMIT 5")
print("Sample transactions query:")
print(result)

# Direct API-based vertex retrieval
print("\nFirst 5 transaction IDs:")
ids = conn.getVertexIdsByType("Transaction", limit=5)
print(ids)

# Simple traversal: get customers who own a specific card
card_id = conn.getVertexIdsByType("Card", limit=1)[0]
print(f"\nLooking at card: {card_id}")

# Get neighbors using a simple GSQL query
neighbors = conn.gsql(f'USE GRAPH HHGoa\nSELECT t FROM Card:c -(MADE)-> Transaction:t WHERE c.card_id == "{card_id}" LIMIT 5')
print(f"Transactions made by {card_id}:")
print(neighbors)
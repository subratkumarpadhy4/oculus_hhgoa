"""
run_server.py
-------------
Entry point to run the TigerGraph MCP Server with custom fraud investigation tools.
"""

import sys
import mcp_server.custom_tools
from tigergraph_mcp.main import main

if __name__ == "__main__":
    sys.exit(main())
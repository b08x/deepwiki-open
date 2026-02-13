import sys
import os
import logging

# Add current directory to path
sys.path.append(os.getcwd())

import adalflow as adal
from api.rag import RAG
from api.config import load_embedder_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_rag_unpacking():
    try:
        # Load config
        load_embedder_config()

        # Initialize RAG
        rag = RAG(provider="ollama", model="bge-m3")

        # Mock retriever to return something that might cause unpacking error
        # In AdalFlow, if it returns a Parameter, maybe that's it?

        query = "test query"
        print(f"Calling rag with query: {query}")

        # Simulate what happens in websocket_wiki.py
        result = rag.call(query)
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")

    except Exception as e:
        logger.error(f"Caught error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    test_rag_unpacking()

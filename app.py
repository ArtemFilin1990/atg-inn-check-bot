import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import main

if __name__ == '__main__':
    asyncio.run(main())
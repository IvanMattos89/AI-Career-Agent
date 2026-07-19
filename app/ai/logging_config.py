import logging
from pathlib import Path


Path("app/logs").mkdir(parents=True, exist_ok=True)


logging.basicConfig(

    filename="app/logs/agent.log",

    level=logging.INFO,

    format="%(asctime)s %(levelname)s %(message)s"

)


logger = logging.getLogger("CareerAgent")

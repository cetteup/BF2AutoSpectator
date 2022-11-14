import logging.config
import os.path
import sys
from logging.handlers import RotatingFileHandler

from BF2AutoSpectator.common.config import Config

logger = logging.getLogger('BF2AutoSpectator')
logger.propagate = False

formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s')

sh = logging.StreamHandler(
    stream=sys.stdout
)
sh.setFormatter(formatter)
logger.addHandler(sh)

rfh = RotatingFileHandler(
    filename=os.path.join(Config.PWD, 'BF2AutoSpectator.log'),
    maxBytes=100*1000*1000  # keep 100 megabytes of logs
)
rfh.setFormatter(formatter)
logger.addHandler(rfh)

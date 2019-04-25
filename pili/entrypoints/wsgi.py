import sys

from pili.entrypoints.dispatcher import create_dispatcher

application = create_dispatcher(config_name=sys.argv[1])

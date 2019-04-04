#!/bin/bash

flower -A celery_worker.celery --broker_api=${FLOWER_BROKER_API}

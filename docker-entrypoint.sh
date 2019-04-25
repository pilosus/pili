#!/bin/bash

echo '--> Provision DB'
pili --config=${PILI_CONFIG} provision --db_init --db_migrate --db_upgrade --db_prepopulate

echo '--> Run Server'
pili --config=${PILI_CONFIG} server

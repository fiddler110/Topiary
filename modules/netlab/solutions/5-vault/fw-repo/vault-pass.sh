#!/bin/sh
# No secret in here: it only says where the password is kept.
BAO_NAMESPACE=students/$USER/fw bao kv get -field=password secret/ansible

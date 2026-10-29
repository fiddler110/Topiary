# The reset token's per-student paths (the openbao module's policies/reset.hcl appends this file): delete a
# student's namespace students/<name> and make it again, as 10-tenancy.sh does. Lab 5 puts the fw and sw team
# vaults in child namespaces, which must go first. Nothing else in the root namespace: not the namespace
# students/ itself, no policies, auth methods or identities.

path "students/sys/namespaces"   { capabilities = ["list"] }
path "students/sys/namespaces/*" { capabilities = ["create", "read", "update", "delete"] }
path "students/+/sys/namespaces"   { capabilities = ["list"] }
path "students/+/sys/namespaces/*" { capabilities = ["create", "read", "update", "delete", "list"] }

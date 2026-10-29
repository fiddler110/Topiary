# What this workshop's hook (10-tenancy.sh) needs on each start. The openbao module's setup.sh appends it to the
# module's own provisioner policy. Exact paths only.

# The student policy, the namespace students/ and one child namespace per account.
path "sys/policies/acl/student"  { capabilities = ["create", "read", "update"] }
path "sys/namespaces/students"   { capabilities = ["create", "read", "update"] }
path "students/sys/namespaces/*" { capabilities = ["create", "read", "update"] }

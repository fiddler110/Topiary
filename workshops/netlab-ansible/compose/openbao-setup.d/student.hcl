# Every student's policy, from the netlab-ansible setup hook (10-tenancy.sh). {{identity.entity.name}} is the
# signed-in student's entity name (student01, ...), filled in on every request. The openbao module attaches it to each
# student's entity, so the terminal (CLI login) and the web UI get the same access.

# Lab 5: admin in your own namespace students/<you>, and nowhere else. A path in a root-namespace policy includes the
# namespace. Your fw and sw team vaults are child namespaces you make inside it.
path "students/{{identity.entity.name}}/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list", "sudo"]
}

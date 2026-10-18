# PoC 用: vault から機器ログインを環境変数へ(値は表示しない)。source して使う。
eval "$(.venv/bin/ansible-vault view group_vars/all/vault.yml --vault-password-file <(printf "CCNP\n") 2>/dev/null </dev/null | .venv/bin/python -c "
import sys, yaml, shlex
v = yaml.safe_load(sys.stdin)
print('export NODE_USER=' + shlex.quote(str(v['ansible_user'])))
print('export NODE_PASS=' + shlex.quote(str(v['ansible_ssh_pass'])))
")"

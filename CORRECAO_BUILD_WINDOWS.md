# Correção do build Windows x64 — v1.3.2

## Causa do erro

Os testes falhavam no Windows com `PermissionError [WinError 32]` porque conexões SQLite permaneciam abertas após a validação dos GeoPackages e o uso do inventário local. O gerenciador de contexto nativo de `sqlite3.Connection` confirma ou desfaz a transação, mas não fecha a conexão.

## Arquivos corrigidos

- `bsdgs_verifier/gpkg_validator.py`
- `bsdgs_verifier/inventory.py`
- `.github/workflows/build-windows-x64.yml`

Também foi incluída uma cópia visível do workflow em `build-windows-x64_v1.3.2.yml`, para facilitar a substituição manual pelo editor do GitHub.

## Procedimento no GitHub

1. Substitua `bsdgs_verifier/gpkg_validator.py`.
2. Substitua `bsdgs_verifier/inventory.py`.
3. Abra `.github/workflows/build-windows-x64.yml` no GitHub, clique no lápis e substitua todo o conteúdo pelo arquivo `build-windows-x64_v1.3.2.yml`.
4. Confirme o commit.
5. Execute `Actions > Build Windows x64 > Run workflow`.

O novo job deve concluir os testes antes de gerar o executável.

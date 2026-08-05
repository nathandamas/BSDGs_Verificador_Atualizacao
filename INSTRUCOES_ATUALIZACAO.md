# Atualização da interface para a versão 1.3.1

## Arquivos novos

Copie para o repositório, preservando os caminhos:

- `bsdgs_verifier/enhanced_gui.py`
- `bsdgs_verifier/selection_state.py`
- `tests/test_selection_state.py`
- `tests/test_scheduler_selection.py`

## Arquivos que substituem os existentes

- `main.py`
- `bsdgs_verifier/scheduler.py`
- `bsdgs_verifier/constants.py`
- `pyproject.toml`
- `.github/workflows/build-windows-x64.yml`
- `build_exe_windows_x64.bat`
- `BUILD_X64_GITHUB.md`
- `CHANGELOG.md`

## Comportamento implementado

1. A tabela de BSDGs apresenta uma coluna inicial com `☐` e `☑`.
2. Clicar em qualquer linha torna essa BSDG a seleção atual.
3. A seleção aparece na tela inicial, na tela de agendamento e na aba de resultados.
4. A caixa de escolha das pastas de saída mostra qual BSDG ou conjunto de BSDGs será verificado.
5. O resumo final mostra BSDG, pasta dos relatórios e log.
6. O agendamento do Windows usa `--scan-all-silent --scan-bsdg <id>`, portanto executa somente a BSDG vinculada.
7. O arquivo `%LOCALAPPDATA%\BSDGs_Verificador_Atualizacao\selection_state.json` preserva a seleção atual e a seleção efetivamente agendada.

## Recompilação x64

Após enviar os arquivos:

1. abra **Actions**;
2. selecione **Build Windows x64**;
3. clique em **Run workflow**;
4. baixe o artefato `BSDGs-Verificador-v1.3.1-Windows-x64`.
